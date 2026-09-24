package com.example.simple_app

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothSocket
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import io.flutter.plugin.common.MethodChannel
import org.json.JSONObject
import java.io.BufferedInputStream
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.UUID

@SuppressLint("MissingPermission")
class BluetoothPairing(private val activity: MainActivity) {
    private val adapter = (activity.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
    private val main = Handler(Looper.getMainLooper())
    private val devices = linkedMapOf<String, Map<String, String>>()
    private var pending: MethodChannel.Result? = null
    private var receiver: BroadcastReceiver? = null
    private var timeout: Runnable? = null
    private var socket: BluetoothSocket? = null
    private var waitingPermission = false

    private fun permissions(): Array<String> = if (Build.VERSION.SDK_INT >= 31) {
        arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
    } else {
        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    fun scan(result: MethodChannel.Result) {
        if (pending != null) {
            result.error("busy", "Bluetooth đang bận.", null)
            return
        }
        pending = result
        if (permissions().any { activity.checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) {
            waitingPermission = true
            activity.requestPermissions(permissions(), 8201)
            return
        }
        startScan(result)
    }

    fun onPermissions(code: Int, results: IntArray) {
        if (code != 8201 || !waitingPermission) return
        waitingPermission = false
        val result = pending ?: return
        if (results.isEmpty() || results.any { it != PackageManager.PERMISSION_GRANTED }) {
            finish(result, error = "Cần cấp quyền Bluetooth để quét máy.")
            return
        }
        startScan(result)
    }

    private fun startScan(result: MethodChannel.Result) {
        try {
            val bluetooth = adapter ?: throw IOException("Điện thoại không hỗ trợ Bluetooth.")
            if (!bluetooth.isEnabled) throw IOException("Hãy bật Bluetooth rồi quét lại.")
            bluetooth.cancelDiscovery()
            devices.clear()

            // Chỉ lấy thiết bị thực sự thấy trong lần quét này, không lấy lịch sử bond.
            receiver = object : BroadcastReceiver() {
                override fun onReceive(context: Context, intent: Intent) {
                    if (pending !== result) return
                    if (intent.action != BluetoothDevice.ACTION_FOUND) return
                    @Suppress("DEPRECATION")
                    val device = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE) ?: return
                    val name = intent.getStringExtra(BluetoothDevice.EXTRA_NAME) ?: device.name ?: return
                    if (name.startsWith("FlexMix-")) {
                        devices[device.address] = mapOf("name" to name, "address" to device.address)
                    }
                }
            }
            val filter = IntentFilter(BluetoothDevice.ACTION_FOUND)
            if (Build.VERSION.SDK_INT >= 33) {
                activity.registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED)
            } else {
                activity.registerReceiver(receiver, filter)
            }
            timeout = Runnable { finish(result, devices.values.toList()) }
            main.postDelayed(timeout!!, 15000)
            if (!bluetooth.startDiscovery()) throw IOException("Không bắt đầu quét được. Hãy thử lại.")
        } catch (error: Exception) {
            finish(result, error = error.message ?: "Không quét được Bluetooth.")
        }
    }

    fun connect(address: String, result: MethodChannel.Result) {
        if (pending != null) {
            result.error("busy", "Bluetooth đang bận.", null)
            return
        }
        pending = result
        try {
            if (!devices.containsKey(address)) throw IOException("Hãy chọn máy trong danh sách vừa quét.")
            val bluetooth = adapter ?: throw IOException("Không có Bluetooth.")
            bluetooth.cancelDiscovery()
            val device = bluetooth.getRemoteDevice(address)
            val uuid = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
            // Secure RFCOMM: Android tự hiện hộp thoại bond nếu chưa ghép đôi.
            val connection = device.createRfcommSocketToServiceRecord(uuid)
            socket = connection
            timeout = Runnable { finish(result, error = "Hết thời gian kết nối/nhận gói tin.") }
            main.postDelayed(timeout!!, 60000)
            Thread {
                try {
                    connection.use {
                        connection.connect()
                        val reader = BufferedInputStream(connection.inputStream)
                        val writer = connection.outputStream
                        writer.write("{\"type\":\"identify\"}\n".toByteArray(Charsets.UTF_8))
                        writer.flush()

                        val ready = readMessage(reader)
                        if (ready.optString("type") != "ready" || ready.opt("ok") != true) {
                            throw IOException("Máy chưa sẵn sàng pairing.")
                        }
                        val packet = readMessage(reader)
                        val name = packet.opt("machine_name")
                        val key = packet.opt("product_key")
                        if (packet.optString("type") != "pairing" || name !is String || name.isBlank()
                            || key !is String || key.isBlank()) {
                            throw IOException("Gói thông tin máy không hợp lệ.")
                        }

                        writer.write("{\"type\":\"ack\",\"ok\":true}\n".toByteArray(Charsets.UTF_8))
                        writer.flush()
                        val answer = mapOf("type" to "pairing", "machine_name" to name, "product_key" to key)
                        main.post { finish(result, answer) }
                    }
                } catch (error: Exception) {
                    main.post { finish(result, error = error.message ?: "Kết nối Bluetooth thất bại.") }
                }
            }.start()
        } catch (error: Exception) {
            finish(result, error = error.message ?: "Không kết nối được máy.")
        }
    }

    private fun readMessage(reader: BufferedInputStream): JSONObject {
        // Cùng một reader cho cả hai dòng: không mất byte khi chúng đến cùng lúc.
        val body = ByteArrayOutputStream()
        repeat(4096) {
            val value = reader.read()
            if (value == -1) throw IOException("Máy ngắt kết nối trước khi gửi đủ gói.")
            if (value == 10) return JSONObject(body.toString("UTF-8"))
            body.write(value)
        }
        throw IOException("Gói Bluetooth quá lớn.")
    }

    private fun finish(result: MethodChannel.Result, value: Any? = null, error: String? = null) {
        // Bỏ qua kết quả của worker cũ sau khi người dùng hủy hoặc timeout.
        if (pending !== result) return
        pending = null
        waitingPermission = false
        timeout?.let { main.removeCallbacks(it) }
        timeout = null
        receiver?.let { activity.unregisterReceiver(it) }
        receiver = null
        try { adapter?.cancelDiscovery() } catch (_: SecurityException) { }
        try { socket?.close() } catch (_: IOException) { }
        socket = null
        if (error == null) result.success(value) else result.error("bluetooth", error, null)
    }

    fun cancel() {
        val result = pending ?: return
        finish(result, error = "Đã hủy Bluetooth.")
    }
}
