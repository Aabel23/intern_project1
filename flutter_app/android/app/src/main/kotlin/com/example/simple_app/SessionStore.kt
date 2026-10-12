package com.example.simple_app

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.json.JSONObject
import java.io.File
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

class SessionStore(context: Context) {
    private val file=File(context.filesDir,"flexmix-session-v1.bin")
    private val temp=File(context.filesDir,"flexmix-session-v1.bin.tmp")
    private fun key(): SecretKey {
        val store=KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("flexmix-session-v1",null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore").apply { init(KeyGenParameterSpec.Builder("flexmix-session-v1",KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT).setKeySize(256).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build()) }.generateKey()
    }
    private fun validate(m: Map<String,Any?>) {
        if(m.keys!=setOf("access_token","access_expires_at","refresh_token","refresh_expires_at","user") || listOf("access_token","access_expires_at","refresh_token","refresh_expires_at").any { m[it] !is String || (m[it] as String).isEmpty() }) throw NativeFailure("SESSION_STORAGE_ERROR")
        val u=m["user"] as? Map<*,*> ?: throw NativeFailure("SESSION_STORAGE_ERROR")
        if(u.keys!=setOf("id","email") || u["id"] !is String || u["email"] !is String) throw NativeFailure("SESSION_STORAGE_ERROR")
    }
    @Synchronized fun saveSession(m: Map<String,Any?>) {
        try {
            validate(m)
            val c=Cipher.getInstance("AES/GCM/NoPadding"); c.init(Cipher.ENCRYPT_MODE,key()); c.updateAAD("flexmix-session-v1".toByteArray(Charsets.US_ASCII))
            val blob=byteArrayOf(1)+c.iv+c.doFinal(JSONObject(m).toString().toByteArray(Charsets.UTF_8))
            java.io.FileOutputStream(temp).use { it.write(blob); it.fd.sync() }
            if(!temp.renameTo(file)) throw Exception()
        } catch(_: Exception) { temp.delete(); throw NativeFailure("SESSION_STORAGE_ERROR") }
    }
    @Synchronized fun loadSession(): Map<String,Any?>? {
        if(!file.exists()) return null
        return try {
            val blob=file.readBytes(); if(blob.size<29 || blob[0].toInt()!=1) throw Exception()
            val c=Cipher.getInstance("AES/GCM/NoPadding"); c.init(Cipher.DECRYPT_MODE,key(),GCMParameterSpec(128,blob.copyOfRange(1,13))); c.updateAAD("flexmix-session-v1".toByteArray(Charsets.US_ASCII))
            val m=CloudCrypto.jsonMap(JSONObject(c.doFinal(blob.copyOfRange(13,blob.size)).toString(Charsets.UTF_8))); validate(m); m
        } catch(_: Exception) { clearSession(); null }
    }
    @Synchronized fun clearSession() { if(file.exists() && !file.delete()) throw NativeFailure("SESSION_STORAGE_ERROR"); if(temp.exists() && !temp.delete()) throw NativeFailure("SESSION_STORAGE_ERROR") }
}
