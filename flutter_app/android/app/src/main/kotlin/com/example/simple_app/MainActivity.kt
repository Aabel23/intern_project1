package com.example.simple_app

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var crypto: CloudCrypto? = null
    private var pairing: ClaimChannel? = null
    private var permissionResult: MethodChannel.Result? = null
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val cloud=CloudCrypto(this); crypto=cloud
        val store=SessionStore(this)
        val claim=ClaimChannel(this); pairing=claim
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger,"flexmix/pairing").setMethodCallHandler { call,result ->
            // Runtime Bluetooth permission needs the Activity, so it is answered here, not on the worker.
            if(call.method=="ensurePermissions") requestBluetooth(result) else claim.onMethodCall(call,result)
        }
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
    private fun requestBluetooth(result: MethodChannel.Result) {
        val needed = if(Build.VERSION.SDK_INT>=31) arrayOf(Manifest.permission.BLUETOOTH_SCAN,Manifest.permission.BLUETOOTH_CONNECT)
                     else arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        val missing = needed.filter { checkSelfPermission(it)!=PackageManager.PERMISSION_GRANTED }
        if(missing.isEmpty()) { result.success(true); return }
        permissionResult?.success(false)
        permissionResult=result
        requestPermissions(missing.toTypedArray(),7301)
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode,permissions,grantResults)
        if(requestCode!=7301) return
        permissionResult?.success(grantResults.isNotEmpty() && grantResults.all { it==PackageManager.PERMISSION_GRANTED })
        permissionResult=null
    }
    override fun onDestroy() { crypto?.clearAll(); pairing?.dispose(); super.onDestroy() }
}
