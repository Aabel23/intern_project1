package com.example.simple_app

import android.content.Context
import android.os.SystemClock
import android.util.Base64
import org.bouncycastle.crypto.hpke.HPKE
import org.json.JSONArray
import org.json.JSONObject
import java.util.UUID
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

class NativeFailure(val code: String) : Exception(code)
class CloudCrypto(private val context: Context) {
    private data class Pending(val key: ByteArray, val sendId: String, val route: String, val created: Long)
    private val pending = mutableMapOf<String, Pending>()
    private fun prune() { val now = SystemClock.elapsedRealtime(); pending.entries.removeAll { if(now-it.value.created >= 30000) { it.value.key.fill(0); true } else false } }
    private fun b64(b: ByteArray) = Base64.encodeToString(b, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
    private fun decode(s: String, size: Int? = null): ByteArray { val b = try { Base64.decode(s, Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP) } catch(_: Exception) { throw NativeFailure("INVALID_RESPONSE") }; if(b64(b)!=s || (size!=null && b.size!=size)) throw NativeFailure("INVALID_RESPONSE"); return b }
    // J() must match the server byte for byte; org.json would escape "/" in routes.
    private fun array(vararg values: Any?): ByteArray = FlexJson.array(*values)
    private fun hpke() = HPKE(HPKE.mode_base, HPKE.kem_X25519_SHA256, HPKE.kdf_HKDF_SHA256, HPKE.aead_AES_GCM128)
    private fun trust(): JSONObject {
        try {
            val t = context.assets.open("flutter_assets/assets/server-trust.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }
            if(t.keys().asSequence().toSet()!=setOf("v","hpke","signing") || t.getInt("v")!=1) throw Exception()
            for((name,kid,size) in listOf(Triple("hpke","server-hpke-1",32),Triple("signing","server-sign-1",65))) {
                val p=t.getJSONObject(name)
                if(p.keys().asSequence().toSet()!=setOf("kid","public_key") || p.getString("kid")!=kid) throw Exception()
                val bytes=decode(p.getString("public_key"),size)
                if(name=="signing" && bytes[0].toInt()!=4) throw Exception()
            }
            return t
        } catch(_: Exception) { throw NativeFailure("INVALID_TRUST") }
    }
    @Synchronized fun sealRequest(args: Map<String, Any?>): Map<String, Any?> {
        prune()
        if(args.keys!=setOf("route","body","access_token","sent_at_ms","kid","public_key")) throw NativeFailure("INVALID_ARGUMENT")
        val route=args["route"] as? String ?: throw NativeFailure("INVALID_ARGUMENT")
        val body=args["body"] as? Map<*,*> ?: throw NativeFailure("INVALID_ARGUMENT")
        val time=args["sent_at_ms"]
        if(time !is Int && time !is Long) throw NativeFailure("INVALID_ARGUMENT")
        val sent=(time as Number).toLong()
        if(!route.startsWith("/app/") || route.any { it.code>127 } || body["v"]!=1 || sent<0 || sent>9007199254740991L || (args["access_token"]!=null && args["access_token"] !is String)) throw NativeFailure("INVALID_ARGUMENT")
        val pin=trust().getJSONObject("hpke")
        if(args["kid"]!=pin.getString("kid") || args["public_key"]!=pin.getString("public_key")) throw NativeFailure("INVALID_TRUST")
        if(pending.size>=64) throw NativeFailure("CONTEXT_LIMIT")
        try {
            val id=UUID.randomUUID().toString()
            val kid=pin.getString("kid")
            val aad=array(1,route,"POST","server",kid,id,sent,null)
            val plain=JSONObject().put("auth", if(args["access_token"]==null) JSONObject.NULL else JSONObject().put("access_token",args["access_token"])).put("body",JSONObject(body)).toString().toByteArray(Charsets.UTF_8)
            if(plain.size>16384) throw NativeFailure("INVALID_ARGUMENT")
            val h=hpke()
            val sender=h.setupBaseS(h.deserializePublicKey(decode(pin.getString("public_key"),32)),"flexmix-cloud-v1".toByteArray(Charsets.US_ASCII))
            val ciphertext=sender.seal(aad,plain)
            val handle=UUID.randomUUID().toString()
            pending[handle]=Pending(sender.export("flexmix-response-v1".toByteArray(Charsets.US_ASCII),16),id,route,SystemClock.elapsedRealtime())
            return mapOf("handle" to handle,"envelope" to mapOf("pv" to 1,"route" to route,"method" to "POST","receiver" to "server","kid" to kid,"send_id" to id,"sent_at_ms" to sent,"machine_key_id" to null,"enc" to b64(sender.encapsulation),"ct" to b64(ciphertext),"sig" to null))
        } catch(e: NativeFailure) { throw e } catch(_: Exception) { throw NativeFailure("CRYPTO_FAILURE") }
    }
    @Synchronized fun openResponse(args: Map<String, Any?>): Map<String, Any?> {
        prune()
        val handle=args["handle"] as? String ?: throw NativeFailure("INVALID_ARGUMENT")
        val p=pending.remove(handle) ?: throw NativeFailure("CONTEXT_EXPIRED")
        try {
            if(args.keys!=setOf("handle","http_status","envelope")) throw NativeFailure("INVALID_ARGUMENT")
            val statusValue=args["http_status"]
            if(statusValue !is Int && statusValue !is Long) throw NativeFailure("INVALID_ARGUMENT")
            val status=(statusValue as Number).toInt()
            val e=args["envelope"] as? Map<*,*> ?: throw NativeFailure("INVALID_RESPONSE")
            if(e.keys!=setOf("pv","send_id","status","nonce","ct") || e["pv"]!=1 || e["send_id"]!=p.sendId || e["status"]!=status || status !in 100..599) throw NativeFailure("INVALID_RESPONSE")
            val nonce=decode(e["nonce"] as? String ?: throw NativeFailure("INVALID_RESPONSE"),12)
            val ct=decode(e["ct"] as? String ?: throw NativeFailure("INVALID_RESPONSE"))
            if(ct.size<16 || ct.size>16400) throw NativeFailure("INVALID_RESPONSE")
            val cipher=Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE,SecretKeySpec(p.key,"AES"),GCMParameterSpec(128,nonce))
            cipher.updateAAD(array("flexmix-response-v1",p.sendId,status,p.route))
            val plain=cipher.doFinal(ct)
            val text=Charsets.UTF_8.newDecoder().decode(java.nio.ByteBuffer.wrap(plain)).toString()
            return jsonMap(JSONObject(text))
        } catch(e: NativeFailure) { throw e } catch(_: Exception) { throw NativeFailure("INVALID_RESPONSE") } finally { p.key.fill(0) }
    }
    @Synchronized fun clearContext(handle: String) { prune(); pending.remove(handle)?.key?.fill(0) }
    @Synchronized fun clearAll() { pending.values.forEach { it.key.fill(0) }; pending.clear() }
    companion object {
        fun jsonMap(obj: JSONObject): Map<String,Any?> = obj.keys().asSequence().associateWith { convert(obj.get(it)) }
        private fun convert(value: Any?): Any? = when(value) { JSONObject.NULL -> null; is JSONObject -> jsonMap(value); is JSONArray -> (0 until value.length()).map { convert(value.get(it)) }; else -> value }
    }
}
