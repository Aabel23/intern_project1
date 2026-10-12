package com.example.simple_app

import android.content.Context
import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * MethodChannel "flexmix/pairing". One claim session at a time; S and session keys stay native.
 * Dart sees only: start(serial, seal_code) -> probe -> [wifi] -> claim -> close.
 */
class ClaimChannel(context: Context) : MethodChannel.MethodCallHandler {
    private val ble = ClaimBle(context)
    private val worker = Executors.newSingleThreadExecutor()
    private val main = Handler(Looper.getMainLooper())
    private var protocol: ClaimProtocol? = null

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        @Suppress("UNCHECKED_CAST") val args = (call.arguments as? Map<String, Any?>) ?: emptyMap()
        worker.execute {
            try {
                val value = when (call.method) {
                    "start" -> start(args["serial"] as? String ?: fail(), args["seal_code"] as? String ?: fail())
                    "probe" -> exchange("probe", emptyMap()).let { summary(it) }
                    "wifi" -> exchange("wifi", mapOf("ssid" to (args["ssid"] as? String ?: fail()),
                        "password" to (args["password"] as? String ?: fail()))).let { summary(it) }
                    "claim" -> claim(args)
                    "close" -> { closeSession(); null }
                    else -> { main.post { result.notImplemented() }; return@execute }
                }
                main.post { result.success(value) }
            } catch (e: PairingFailure) {
                if (e.code !in setOf("SERIAL_MISMATCH")) closeSession()
                main.post { result.error(e.code, e.code, null) }
            } catch (_: SecurityException) {
                closeSession(); main.post { result.error("BLUETOOTH_PERMISSION", "BLUETOOTH_PERMISSION", null) }
            } catch (_: Exception) {
                closeSession(); main.post { result.error("PAIRING_FAILED", "PAIRING_FAILED", null) }
            }
        }
    }

    private fun fail(): Nothing = throw PairingFailure("INVALID_ARGUMENT")

    private fun start(serial: String, sealCode: String): Map<String, Any?> {
        closeSession()
        val seal = try { FlexJson.decodeB64u(sealCode, 32) } catch (_: Exception) { fail() }
        try {
            // Several machines may advertise; only the one whose hello serial matches the QR is used.
            for (device in ble.scan()) {
                val candidate = ClaimProtocol(serial, seal)
                try {
                    candidate.acceptHello(ble.connect(device))
                    protocol = candidate
                    return mapOf("serial" to serial)
                } catch (e: PairingFailure) {
                    candidate.close(); ble.close()
                    if (e.code != "SERIAL_MISMATCH" && e.code != "PAIRING_TRANSPORT_ERROR") throw e
                }
            }
            throw PairingFailure("MACHINE_NOT_FOUND")
        } finally {
            seal.fill(0)
        }
    }

    private fun exchange(stage: String, extra: Map<String, Any?>): JSONObject {
        val p = protocol ?: throw PairingFailure("PAIRING_PROTOCOL_ERROR")
        val body = if (stage == "probe") extra else extra + ("session_transcript" to p.transcriptHash)
        ble.send(p.request(stage, body))
        return p.response(ble.receive(if (stage == "wifi") 60_000 else 30_000))
    }

    private fun summary(body: JSONObject): Map<String, Any?> = mapOf(
        "machine_id" to (if (body.isNull("machine_id")) null else body.getString("machine_id")),
        "online" to body.optBoolean("online", false))

    private fun claim(args: Map<String, Any?>): Map<String, Any?> {
        @Suppress("UNCHECKED_CAST") val challenge = args["challenge"] as? Map<String, Any?> ?: fail()
        val signature = args["server_challenge_signature"] as? String ?: fail()
        val body = exchange("claim", mapOf("challenge" to JSONObject(challenge), "server_challenge_signature" to signature))
        closeSession()
        if (body.getString("type") != "claim_proof") throw PairingFailure("PAIRING_PROTOCOL_ERROR")
        return mapOf("claim_id" to body.getString("claim_id"), "local_session_binding" to body.getString("local_session_binding"),
            "machine_proof" to body.getString("machine_proof"))
    }

    private fun closeSession() {
        protocol?.close(); protocol = null
        ble.close()
    }

    fun dispose() { worker.execute { closeSession() }; worker.shutdown() }
}
