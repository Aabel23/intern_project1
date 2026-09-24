package com.example.simple_app

import android.content.Intent
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
                    "sendShare" -> pairing.sendShare(
                        call.argument<String>("address") ?: "",
                        call.argument<String>("payload") ?: "",
                        result,
                    )
                    "receiveShare" -> pairing.receiveShare(result)
                    "cancel" -> { pairing.cancel(); result.success(null) }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onRequestPermissionsResult(code: Int, permissions: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code, permissions, results)
        pairing.onPermissions(code, results)
    }

    // Kết quả hộp thoại "cho phép hiện điện thoại" khi nhận chia sẻ máy.
    override fun onActivityResult(code: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(code, resultCode, data)
        if (::pairing.isInitialized) pairing.onActivityResult(code, resultCode)
    }

    override fun onDestroy() {
        if (::pairing.isInitialized) pairing.cancel()
        super.onDestroy()
    }
}
