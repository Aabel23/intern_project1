package com.example.simple_app

/**
 * Line protocol with the Python test: each line is "<verb> <b64u>" .
 * stdin:  seal <S> / serial <hex> / hello <P> / response <P> / challenge <json>
 * stdout: request <P> / body <json> / failure <code>
 */
fun main() {
    val input = generateSequence(::readLine).iterator()
    fun next(verb: String): String {
        val line = input.next()
        require(line.startsWith("$verb ")) { "expected $verb, got $line" }
        return line.substring(verb.length + 1)
    }
    val serial = next("serial")
    val protocol = ClaimProtocol(serial, FlexJson.decodeB64u(next("seal")))
    try {
        protocol.acceptHello(FlexJson.decodeB64u(next("hello")))
        while (true) {
            val line = input.next()
            if (line == "end") break
            val (verb, arg) = line.split(" ", limit = 2)
            when (verb) {
                "probe" -> println("request " + FlexJson.b64u(protocol.request("probe")))
                "wifi" -> println("request " + FlexJson.b64u(protocol.request("wifi", mapOf(
                    "session_transcript" to protocol.transcriptHash, "ssid" to "Cafe/Shop", "password" to arg))))
                "claim" -> {
                    val c = org.json.JSONObject(String(FlexJson.decodeB64u(arg)))
                    println("request " + FlexJson.b64u(protocol.request("claim", mapOf(
                        "session_transcript" to protocol.transcriptHash, "challenge" to c.getJSONObject("challenge"),
                        "server_challenge_signature" to c.getString("signature")))))
                }
                "response" -> println("body " + FlexJson.b64u(protocol.response(FlexJson.decodeB64u(arg)).toString().toByteArray()))
                "aad" -> println("aad " + FlexJson.b64u(FlexJson.array(1, "/app/user/session/login", "POST", "server", "server-hpke-1", "x", 0L, null)))
            }
            System.out.flush()
        }
    } catch (e: PairingFailure) {
        println("failure " + e.code)
    }
}
