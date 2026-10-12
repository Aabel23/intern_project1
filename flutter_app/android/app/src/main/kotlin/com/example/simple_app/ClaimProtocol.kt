package com.example.simple_app

import org.bouncycastle.crypto.hpke.HPKE
import org.bouncycastle.crypto.modes.GCMBlockCipher
import org.bouncycastle.crypto.engines.AESEngine
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.KeyParameter
import org.json.JSONObject
import java.security.SecureRandom
import java.util.UUID

class PairingFailure(val code: String) : Exception(code)

/**
 * App side of the BLE claim session v2 (contracts/messages/v2-decisions.md D3/D4).
 * Pure Kotlin + Bouncy Castle lightweight HPKE: no radio, no Android APIs, so the JVM interop
 * test runs it against the Python machine implementation. Keys never leave this object.
 */
class ClaimProtocol(private val serial: String, seal: ByteArray, private val random: SecureRandom = SecureRandom()) {
    private val seal = seal.copyOf()
    private val clientNonce = FlexJson.b64u(ByteArray(32).also { random.nextBytes(it) })
    private var transcript = ByteArray(0)
    private lateinit var sessionId: String
    private lateinit var machineNonce: String
    private lateinit var machineKey: ByteArray
    private lateinit var h0: String
    lateinit var machinePublicKey: ByteArray
        private set
    private var pending: Pending? = null
    private var closed = false

    private class Pending(val packet: ByteArray, val stage: String, val sendId: String, val key: ByteArray)

    init {
        if (!Regex("[0-9a-f]{16}").matches(serial) || seal.size != 32) throw PairingFailure("PAIRING_FAILED")
    }

    private fun hpke() = HPKE(HPKE.mode_psk, HPKE.kem_X25519_SHA256, HPKE.kdf_HKDF_SHA256, HPKE.aead_AES_GCM128)

    val transcriptHash: String get() = FlexJson.b64u(FlexJson.sha256(transcript))

    fun acceptHello(packet: ByteArray) {
        val hello = parseObject(packet)
        require(hello.keySet() == setOf("pv", "type", "serial", "session_id", "machine_nonce", "public_key", "machine_public_key"))
        require(hello.getInt("pv") == 2 && hello.getString("type") == "hello")
        // A different machine nearby: never send anything sealed with this QR's secret to it.
        if (hello.getString("serial") != serial) throw PairingFailure("SERIAL_MISMATCH")
        sessionId = hello.getString("session_id")
        require(UUID.fromString(sessionId).toString() == sessionId)
        machineNonce = hello.getString("machine_nonce")
        machineKey = FlexJson.decodeB64u(hello.getString("public_key"), 32)
        machinePublicKey = FlexJson.decodeB64u(hello.getString("machine_public_key"), 65)
        transcript = FlexJson.frame(packet)
        h0 = transcriptHash
    }

    private fun common(type: String) = JSONObject()
        .put("type", type).put("serial", serial).put("session_id", sessionId)
        .put("machine_nonce", machineNonce).put("client_nonce", clientNonce)

    fun request(stage: String, extra: Map<String, Any?> = emptyMap()): ByteArray {
        if (closed || pending != null) throw PairingFailure("PAIRING_PROTOCOL_ERROR")
        val body = common(stage)
        extra.forEach { (k, v) -> body.put(k, v ?: JSONObject.NULL) }
        val sendId = UUID.randomUUID().toString()
        val h = hpke()
        val info = FlexJson.array("flexmix-bt-claim-v2", "app", "machine", serial, sessionId, h0)
        val sender = h.SetupPSKS(h.deserializePublicKey(machineKey), info, seal, "flexmix-seal-v1:$serial".toByteArray(Charsets.US_ASCII))
        val aad = FlexJson.array(2, "flexmix-bt-claim-v2", "app", "machine", serial, sessionId, h0, sendId, stage)
        val ct = sender.seal(aad, body.toString().toByteArray(Charsets.UTF_8))
        val packet = JSONObject().put("pv", 2).put("type", "request").put("session_id", sessionId).put("send_id", sendId)
            .put("stage", stage).put("enc", FlexJson.b64u(sender.encapsulation)).put("ct", FlexJson.b64u(ct))
            .toString().toByteArray(Charsets.UTF_8)
        pending = Pending(packet, stage, sendId, sender.export("flexmix-bt-response-v2".toByteArray(Charsets.US_ASCII), 16))
        return packet
    }

    /** Opens the single response to the pending request; machine error bodies become PairingFailure(code). */
    fun response(packet: ByteArray): JSONObject {
        val p = pending ?: throw PairingFailure("PAIRING_PROTOCOL_ERROR")
        pending = null
        try {
            val outer = parseObject(packet)
            require(outer.keySet() == setOf("pv", "type", "session_id", "send_id", "stage", "nonce", "ct"))
            require(outer.getInt("pv") == 2 && outer.getString("type") == "response" && outer.getString("session_id") == sessionId)
            require(outer.getString("send_id") == p.sendId && outer.getString("stage") == p.stage)
            val aad = FlexJson.array(2, "flexmix-bt-response-v2", "machine", "app", serial, sessionId, h0, p.sendId, p.stage,
                FlexJson.b64u(FlexJson.sha256(FlexJson.frame(p.packet))))
            val cipher = GCMBlockCipher.newInstance(AESEngine.newInstance())
            cipher.init(false, AEADParameters(KeyParameter(p.key), 128, FlexJson.decodeB64u(outer.getString("nonce"), 12), aad))
            val ct = FlexJson.decodeB64u(outer.getString("ct"))
            val plain = ByteArray(cipher.getOutputSize(ct.size))
            val n = cipher.processBytes(ct, 0, ct.size, plain, 0)
            cipher.doFinal(plain, n)
            val body = parseObject(plain)
            val expected = common(body.getString("type"))
            for (key in expected.keys()) require(body.get(key) == expected.get(key))
            when (body.getString("type")) {
                "error" -> { close(); throw PairingFailure(body.getString("code")) }
                "authenticated" -> require(FlexJson.decodeB64u(body.getString("machine_public_key"), 65).contentEquals(machinePublicKey))
            }
            if (body.getString("type") == "authenticated" || body.getString("type") == "wifi_result") {
                transcript += FlexJson.frame(p.packet) + FlexJson.frame(packet)
            }
            return body
        } catch (e: PairingFailure) {
            throw e
        } catch (_: Exception) {
            close()
            throw PairingFailure("PAIRING_FAILED")
        } finally {
            p.key.fill(0)
        }
    }

    fun close() {
        closed = true
        seal.fill(0)
        pending?.key?.fill(0)
        pending = null
    }

    private fun parseObject(bytes: ByteArray): JSONObject {
        val text = Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(bytes)).toString()
        return JSONObject(text)
    }
}
