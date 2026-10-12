package com.example.simple_app

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.bouncycastle.crypto.hpke.HPKE
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import android.util.Base64
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CloudCryptoTest {
    private fun hex(s: String): ByteArray = s.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
    @Test fun productionSealUsesPinnedKeyAndEncryptedBody() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val fixture=instrumentation.context.assets.open("python-kotlin-account.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }
        val archive=java.io.File(instrumentation.targetContext.cacheDir,"a01-test-trust.zip")
        fun b64(b:ByteArray)=Base64.encodeToString(b,Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
        val publicKey=b64(hex(fixture.getString("test_only_pkRm")))
        val trust=JSONObject().put("v",1).put("hpke",JSONObject().put("kid","server-hpke-1").put("public_key",publicKey)).put("signing",JSONObject().put("kid","server-sign-1").put("public_key",b64(byteArrayOf(4)+ByteArray(64))))
        java.util.zip.ZipOutputStream(java.io.FileOutputStream(archive)).use { zip -> zip.putNextEntry(java.util.zip.ZipEntry("assets/flutter_assets/assets/server-trust.json")); zip.write(trust.toString().toByteArray()); zip.closeEntry() }
        val assets=android.content.res.AssetManager::class.java.getDeclaredConstructor().apply { isAccessible=true }.newInstance()
        android.content.res.AssetManager::class.java.getMethod("addAssetPath",String::class.java).invoke(assets,archive.absolutePath)
        val context=object:android.content.ContextWrapper(instrumentation.targetContext) { override fun getAssets()=assets }
        val cloud=CloudCrypto(context)
        try {
            val result=cloud.sealRequest(mapOf("route" to "/app/user/session/bootstrap","body" to mapOf("v" to 1),"access_token" to null,"sent_at_ms" to 0,"kid" to "server-hpke-1","public_key" to publicKey))
            val e=result["envelope"] as Map<*,*>
            val receiver=HPKE(HPKE.mode_base,HPKE.kem_X25519_SHA256,HPKE.kdf_HKDF_SHA256,HPKE.aead_AES_GCM128)
            val pair=receiver.deserializePrivateKey(hex(fixture.getString("test_only_skRm")),hex(fixture.getString("test_only_pkRm")))
            fun decode(value:Any?)=Base64.decode(value as String,Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
            val recipient=receiver.setupBaseR(decode(e["enc"]),pair,"flexmix-cloud-v1".toByteArray())
            val aad=org.json.JSONArray(listOf(1,e["route"],"POST","server","server-hpke-1",e["send_id"],0,JSONObject.NULL)).toString().toByteArray()
            val body=JSONObject(recipient.open(aad,decode(e["ct"])).toString(Charsets.UTF_8))
            org.junit.Assert.assertTrue(body.isNull("auth")); org.junit.Assert.assertEquals(1,body.getJSONObject("body").getInt("v"))
            cloud.clearContext(result["handle"] as String)
        } finally { cloud.clearAll(); assets.close(); archive.delete() }
    }
    @Test fun productionOpenConsumesPythonResponseAndRejectsReuseAndTamper() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val fixture=InstrumentationRegistry.getInstrumentation().context.assets.open("python-kotlin-account.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }
        val cloud=CloudCrypto(context)
        // Insert the independently generated Python exporter fixture into the private context map;
        // production code keeps its public API and randomness unchanged.
        val pendingType=Class.forName("com.example.simple_app.CloudCrypto\$Pending")
        val constructor=pendingType.getDeclaredConstructor(ByteArray::class.java,String::class.java,String::class.java,java.lang.Long.TYPE).apply { isAccessible=true }
        val mapField=CloudCrypto::class.java.getDeclaredField("pending").apply { isAccessible=true }
        @Suppress("UNCHECKED_CAST") val contexts=mapField.get(cloud) as MutableMap<String,Any>
        fun insert(handle:String,created:Long=android.os.SystemClock.elapsedRealtime()) {
            contexts[handle]=constructor.newInstance(hex(fixture.getString("response_key")),fixture.getJSONObject("request").getString("send_id"),"/app/user/session/bootstrap",created)
        }
        val envelope=CloudCrypto.jsonMap(fixture.getJSONObject("response"))
        insert("python-fixture")
        val result=cloud.openResponse(mapOf("handle" to "python-fixture","http_status" to 200,"envelope" to envelope))
        org.junit.Assert.assertEquals(1791763200000L,(result["data"] as Map<*,*>)["server_time_ms"])
        fun expectFailure(code:String,block:()->Unit) { try { block(); org.junit.Assert.fail("Expected failure") } catch(e:NativeFailure) { org.junit.Assert.assertEquals(code,e.code) } }
        expectFailure("CONTEXT_EXPIRED") { cloud.openResponse(mapOf("handle" to "python-fixture","http_status" to 200,"envelope" to envelope)) }
        insert("tampered")
        expectFailure("INVALID_RESPONSE") { cloud.openResponse(mapOf("handle" to "tampered","http_status" to 401,"envelope" to envelope)) }
        expectFailure("CONTEXT_EXPIRED") { cloud.openResponse(mapOf("handle" to "tampered","http_status" to 200,"envelope" to envelope)) }
        insert("expired",android.os.SystemClock.elapsedRealtime()-30001)
        expectFailure("CONTEXT_EXPIRED") { cloud.openResponse(mapOf("handle" to "expired","http_status" to 200,"envelope" to envelope)) }
        cloud.clearAll()
    }
    @Test fun productionSessionStorePersistsAndClearsCorruptCiphertext() {
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val store=SessionStore(context)
        val data=mapOf("access_token" to "TEST_ONLY_ACCESS","access_expires_at" to "2026-10-12T00:00:00.000000Z","refresh_token" to "TEST_ONLY_REFRESH","refresh_expires_at" to "2026-11-12T00:00:00.000000Z","user" to mapOf("id" to "test-user","email" to "test@example.invalid"))
        store.clearSession()
        try {
            store.saveSession(data)
            org.junit.Assert.assertEquals(data,SessionStore(context).loadSession())
            val file=java.io.File(context.filesDir,"flexmix-session-v1.bin")
            val blob=file.readBytes()
            org.junit.Assert.assertFalse(String(blob,Charsets.ISO_8859_1).contains("TEST_ONLY_REFRESH"))
            blob[blob.lastIndex]=(blob.last().toInt() xor 1).toByte(); file.writeBytes(blob)
            org.junit.Assert.assertNull(store.loadSession())
            org.junit.Assert.assertFalse(file.exists())
            store.saveSession(data); store.clearSession(); org.junit.Assert.assertNull(store.loadSession())
        } finally { store.clearSession() }
    }
    @Test fun pythonKotlinRequestResponseFixture() {
        val assets=InstrumentationRegistry.getInstrumentation().context.assets
        val v=assets.open("python-kotlin-account.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)) }
        val h=HPKE(HPKE.mode_base,HPKE.kem_X25519_SHA256,HPKE.kdf_HKDF_SHA256,HPKE.aead_AES_GCM128)
        val pair=h.deserializePrivateKey(hex(v.getString("test_only_skEm")),hex(v.getString("test_only_pkEm")))
        val sender=h.setupBaseS(h.deserializePublicKey(hex(v.getString("test_only_pkRm"))),"flexmix-cloud-v1".toByteArray(Charsets.US_ASCII),pair)
        fun decode(s: String)=Base64.decode(s,Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP)
        val request=v.getJSONObject("request")
        assertArrayEquals(decode(request.getString("enc")),sender.encapsulation)
        val plain="{\"auth\":null,\"body\":{\"v\":1}}".toByteArray(Charsets.UTF_8)
        assertArrayEquals(decode(request.getString("ct")),sender.seal(hex(v.getString("aad")),plain))
        val key=sender.export("flexmix-response-v1".toByteArray(Charsets.US_ASCII),16)
        assertArrayEquals(hex(v.getString("response_key")),key)
        val response=v.getJSONObject("response")
        val cipher=Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE,SecretKeySpec(key,"AES"),GCMParameterSpec(128,decode(response.getString("nonce"))))
        val aad="[\"flexmix-response-v1\",\"${request.getString("send_id")}\",200,\"/app/user/session/bootstrap\"]".toByteArray(Charsets.UTF_8)
        cipher.updateAAD(aad)
        assertArrayEquals("{\"v\":1,\"ok\":true,\"data\":{\"server_time_ms\":1791763200000}}".toByteArray(Charsets.UTF_8),cipher.doFinal(decode(response.getString("ct"))))
    }
    @Test fun officialRfc9180BaseVector() {
        val assets=InstrumentationRegistry.getInstrumentation().context.assets
        val v=assets.open("rfc9180-base.json").use { JSONObject(it.readBytes().toString(Charsets.UTF_8)).getJSONObject("vector") }
        val hpke=HPKE(HPKE.mode_base,HPKE.kem_X25519_SHA256,HPKE.kdf_HKDF_SHA256,HPKE.aead_AES_GCM128)
        val pair=hpke.deserializePrivateKey(hex(v.getString("skEm")),hex(v.getString("pkEm")))
        val sender=hpke.setupBaseS(hpke.deserializePublicKey(hex(v.getString("pkRm"))),hex(v.getString("info")),pair)
        assertArrayEquals(hex(v.getString("enc")),sender.encapsulation)
        val encryptions=v.getJSONArray("encryptions")
        for(i in 0 until encryptions.length()) {
            val e=encryptions.getJSONObject(i)
            assertArrayEquals(hex(e.getString("ct")),sender.seal(hex(e.getString("aad")),hex(e.getString("pt"))))
        }
        val exports=v.getJSONArray("exports")
        for(i in 0 until exports.length()) {
            val e=exports.getJSONObject(i)
            assertArrayEquals(hex(e.getString("exported_value")),sender.export(hex(e.getString("exporter_context")),e.getInt("L")))
        }
    }
}
