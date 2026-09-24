package com.example.simple_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private lateinit var pairing: BluetoothPairing

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        pairing = BluetoothPairing(this)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "flexmix/bluetooth_pairing")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "scan" -> pairing.scan(result)
                    "connect" -> pairing.connect(call.argument<String>("address") ?: "", result)
                    "cancel" -> { pairing.cancel(); result.success(null) }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        pairing.onPermissions(code, results)
    }

    override fun onDestroy() {
        if (::pairing.isInitialized) pairing.cancel()
        super.onDestroy()
    }
}
