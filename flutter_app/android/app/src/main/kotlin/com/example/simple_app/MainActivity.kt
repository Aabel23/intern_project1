package com.example.simple_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var crypto: CloudCrypto? = null
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val cloud=CloudCrypto(this); crypto=cloud
        val store=SessionStore(this)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"flexmix/crypto").setMethodCallHandler { call,result ->
            try {
                @Suppress("UNCHECKED_CAST") val args=call.arguments as? Map<String,Any?> ?: throw NativeFailure("INVALID_ARGUMENT")
                when(call.method) {
                    "sealRequest" -> result.success(cloud.sealRequest(args))
                    "openResponse" -> result.success(cloud.openResponse(args))
                    "clearContext" -> { if(args.keys!=setOf("handle")) throw NativeFailure("INVALID_ARGUMENT"); cloud.clearContext(args["handle"] as? String ?: throw NativeFailure("INVALID_ARGUMENT")); result.success(null) }
                    else -> result.notImplemented()
                }
            } catch(e: NativeFailure) { result.error(e.code,e.code,null) } catch(_: Exception) { result.error("CRYPTO_FAILURE","CRYPTO_FAILURE",null) }
        }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"flexmix/session").setMethodCallHandler { call,result ->
            try {
                when(call.method) {
                    "saveSession" -> { @Suppress("UNCHECKED_CAST") val args=call.arguments as? Map<String,Any?> ?: throw NativeFailure("SESSION_STORAGE_ERROR"); store.saveSession(args); result.success(null) }
                    "loadSession" -> { if(call.arguments!=null) throw NativeFailure("SESSION_STORAGE_ERROR"); result.success(store.loadSession()) }
                    "clearSession" -> { if(call.arguments!=null) throw NativeFailure("SESSION_STORAGE_ERROR"); store.clearSession(); result.success(null) }
                    else -> result.notImplemented()
                }
            } catch(_: Exception) { result.error("SESSION_STORAGE_ERROR","SESSION_STORAGE_ERROR",null) }
        }
    }
    override fun onDestroy() { crypto?.clearAll(); super.onDestroy() }
}
