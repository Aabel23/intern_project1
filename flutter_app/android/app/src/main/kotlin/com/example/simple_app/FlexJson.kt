package com.example.simple_app

import java.security.MessageDigest

/**
 * J(x): compact JSON array, byte-identical to Python json.dumps(separators=(",",":"), ensure_ascii=False).
 * Android's org.json escapes "/" as "\/", which would change AAD bytes for routes like /app/...,
 * so every signed or authenticated array is built here instead.
 */
object FlexJson {
    fun array(vararg values: Any?): ByteArray {
        val out = StringBuilder("[")
        values.forEachIndexed { index, value ->
            if (index > 0) out.append(',')
            when (value) {
                null -> out.append("null")
                is String -> string(out, value)
                is Int, is Long -> out.append(value.toString())
                else -> throw IllegalArgumentException("J() supports only strings, integers and null")
            }
        }
        return out.append(']').toString().toByteArray(Charsets.UTF_8)
    }

    private fun string(out: StringBuilder, value: String) {
        out.append('"')
        for (c in value) {
            when (c) {
                '"' -> out.append("\\\"")
                '\\' -> out.append("\\\\")
                '\n' -> out.append("\\n")
                '\r' -> out.append("\\r")
                '\t' -> out.append("\\t")
                '\b' -> out.append("\\b")
                '\u000C' -> out.append("\\f")
                else -> if (c.code < 0x20) out.append(String.format("\\u%04x", c.code)) else out.append(c)
            }
        }
        out.append('"')
    }

    // Pure Kotlin so the protocol also runs in JVM interop tests (android.util.Base64 does not).
    private const val ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    fun b64u(bytes: ByteArray): String {
        val out = StringBuilder()
        var i = 0
        while (i < bytes.size) {
            val n = minOf(3, bytes.size - i)
            var chunk = 0
            for (k in 0 until 3) chunk = (chunk shl 8) or (if (k < n) bytes[i + k].toInt() and 0xff else 0)
            for (k in 0..n) out.append(ALPHABET[(chunk ushr (18 - 6 * k)) and 0x3f])
            i += 3
        }
        return out.toString()
    }

    fun decodeB64u(value: String, size: Int? = null): ByteArray {
        if (value.length % 4 == 1) throw IllegalArgumentException("b64u")
        val out = java.io.ByteArrayOutputStream()
        var buffer = 0
        var bits = 0
        for (c in value) {
            val v = ALPHABET.indexOf(c)
            if (v < 0) throw IllegalArgumentException("b64u")
            buffer = (buffer shl 6) or v
            bits += 6
            if (bits >= 8) { bits -= 8; out.write((buffer ushr bits) and 0xff) }
        }
        val bytes = out.toByteArray()
        // Canonical form only: re-encoding must give back the same text (no stray low bits).
        if (b64u(bytes) != value || (size != null && bytes.size != size)) throw IllegalArgumentException("b64u")
        return bytes
    }

    fun sha256(vararg parts: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").run { parts.forEach { update(it) }; digest() }

    fun frame(packet: ByteArray): ByteArray =
        byteArrayOf((packet.size ushr 24).toByte(), (packet.size ushr 16).toByte(), (packet.size ushr 8).toByte(), packet.size.toByte()) + packet
}
