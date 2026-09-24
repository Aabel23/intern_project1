package com.example.simple_app

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothServerSocket
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
import java.io.OutputStream
import java.util.UUID

// Mỗi gói là một dòng JSON UTF-8 kết thúc bằng \n, tối đa 4096 byte.
// Pairing máy: app là client của máy (SPP). Chia sẻ máy: app chủ là client,
// app nhân viên mở server với SHARE_UUID và chờ.
@SuppressLint("MissingPermission")
class BluetoothPairing(private val activity: MainActivity) {
    companion object {
        private val MACHINE_UUID = UUID.fromString("00001101-0000-1000-8000-00805f9b34fb")
        // UUID riêng của FlexMix cho chia sẻ máy giữa hai app; sandbox dùng cùng giá trị.
        private val SHARE_UUID = UUID.fromString("e53b1694-9a6d-41e7-8b4a-00e228b8164e")
        private const val PERMISSION_CODE = 8201
        private const val DISCOVERABLE_CODE = 8202
        private const val DISCOVERABLE_SECONDS = 120
    }

    private val adapter = (activity.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
    private val main = Handler(Looper.getMainLooper())
    private val devices = linkedMapOf<String, Map<String, String>>()
    private var pending: MethodChannel.Result? = null
    private var receiver: BroadcastReceiver? = null
    private var timeout: Runnable? = null
    // Worker thread gán socket, main thread đóng khi hủy/timeout.
    @Volatile private var socket: BluetoothSocket? = null
    private var serverSocket: BluetoothServerSocket? = null
    private var waitingPermission = false
    private var waitingDiscoverable = false
    private var afterPermission: (() -> Unit)? = null

    private fun permissions(advertise: Boolean): Array<String> = when {
        Build.VERSION.SDK_INT < 31 -> arrayOf(Manifest.permission.ACCESS_FINE_LOCATION)
        advertise -> arrayOf(
            Manifest.permission.BLUETOOTH_SCAN,
            Manifest.permission.BLUETOOTH_CONNECT,
            Manifest.permission.BLUETOOTH_ADVERTISE,
        )
        else -> arrayOf(Manifest.permission.BLUETOOTH_SCAN, Manifest.permission.BLUETOOTH_CONNECT)
    }

    // Giữ result làm "đang bận", xin quyền nếu thiếu rồi mới chạy action.
    private fun start(result: MethodChannel.Result, advertise: Boolean, action: () -> Unit) {
        if (pending != null) {
            result.error("busy", "Bluetooth đang bận.", null)
            return
        }
        pending = result
        val needed = permissions(advertise)
        if (needed.any { activity.checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED }) {
            afterPermission = action
            waitingPermission = true
            activity.requestPermissions(needed, PERMISSION_CODE)
            return
        }
        action()
    }

    fun onPermissions(code: Int, results: IntArray) {
        if (code != PERMISSION_CODE || !waitingPermission) return
        waitingPermission = false
        val result = pending ?: return
        val action = afterPermission
        afterPermission = null
        if (results.isEmpty() || results.any { it != PackageManager.PERMISSION_GRANTED }) {
            finish(result, error = "Cần cấp quyền Bluetooth để tiếp tục.")
            return
        }
        action?.invoke()
    }

    fun scan(result: MethodChannel.Result) = start(result, advertise = false) { startScan(result) }

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
                    // Trả mọi thiết bị có tên; app lọc FlexMix- hay hiện tất cả.
                    devices[device.address] = mapOf("name" to name, "address" to device.address)
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

    // Pairing máy: gửi identify, nhận ready + gói pairing, trả ACK.
    fun connect(address: String, result: MethodChannel.Result) = exchange(address, MACHINE_UUID, result) { reader, writer ->
        writeLine(writer, "{\"type\":\"identify\"}")
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
        writeLine(writer, "{\"type\":\"ack\",\"ok\":true}")
        mapOf("type" to "pairing", "machine_name" to name, "product_key" to key)
    }

    // Chủ máy gửi mã mời: identify -> ready, gửi payload share -> chờ ACK.
    fun sendShare(address: String, payload: String, result: MethodChannel.Result) {
        if (payload.contains('\n') || payload.toByteArray(Charsets.UTF_8).size > 4096) {
            result.error("bluetooth", "Gói chia sẻ không hợp lệ.", null)
            return
        }
        exchange(address, SHARE_UUID, result) { reader, writer ->
            writeLine(writer, "{\"type\":\"identify\"}")
            val ready = readMessage(reader)
            if (ready.optString("type") != "ready" || ready.opt("ok") != true) {
                throw IOException("Thiết bị nhận chưa mở màn hình nhận chia sẻ.")
            }
            writeLine(writer, payload)
            val ack = readMessage(reader)
            if (ack.optString("type") != "ack" || ack.opt("ok") != true) {
                throw IOException("Thiết bị nhận không chấp nhận mã chia sẻ.")
            }
            null
        }
    }

    private fun exchange(
        address: String,
        uuid: UUID,
        result: MethodChannel.Result,
        talk: (BufferedInputStream, OutputStream) -> Any?,
    ) {
        if (pending != null) {
            result.error("busy", "Bluetooth đang bận.", null)
            return
        }
        pending = result
        try {
            if (!devices.containsKey(address)) throw IOException("Hãy chọn thiết bị trong danh sách vừa quét.")
            val bluetooth = adapter ?: throw IOException("Không có Bluetooth.")
            bluetooth.cancelDiscovery()
            // Secure RFCOMM: Android tự hiện hộp thoại bond nếu chưa ghép đôi.
            val connection = bluetooth.getRemoteDevice(address).createRfcommSocketToServiceRecord(uuid)
            socket = connection
            timeout = Runnable { finish(result, error = "Hết thời gian kết nối/nhận gói tin.") }
            main.postDelayed(timeout!!, 60000)
            Thread {
                try {
                    connection.use {
                        connection.connect()
                        val answer = talk(BufferedInputStream(connection.inputStream), connection.outputStream)
                        main.post { finish(result, answer) }
                    }
                } catch (error: Exception) {
                    main.post { finish(result, error = error.message ?: "Kết nối Bluetooth thất bại.") }
                }
            }.start()
        } catch (error: Exception) {
            finish(result, error = error.message ?: "Không kết nối được thiết bị.")
        }
    }

    // Nhân viên: hiện điện thoại cho chủ máy quét thấy rồi chờ kết nối SHARE_UUID.
    fun receiveShare(result: MethodChannel.Result) = start(result, advertise = true) {
        if (adapter == null) {
            finish(result, error = "Điện thoại không hỗ trợ Bluetooth.")
        } else {
            waitingDiscoverable = true
            val intent = Intent(BluetoothAdapter.ACTION_REQUEST_DISCOVERABLE)
                .putExtra(BluetoothAdapter.EXTRA_DISCOVERABLE_DURATION, DISCOVERABLE_SECONDS)
            @Suppress("DEPRECATION")
            activity.startActivityForResult(intent, DISCOVERABLE_CODE)
        }
    }

    fun onActivityResult(code: Int, resultCode: Int) {
        if (code != DISCOVERABLE_CODE || !waitingDiscoverable) return
        waitingDiscoverable = false
        val result = pending ?: return
        // Hệ thống trả số giây được hiện, RESULT_CANCELED khi người dùng từ chối.
        if (resultCode == Activity.RESULT_CANCELED) {
            finish(result, error = "Cần cho phép hiện điện thoại để chủ máy tìm thấy.")
            return
        }
        listenShare(result)
    }

    private fun listenShare(result: MethodChannel.Result) {
        try {
            val bluetooth = adapter ?: throw IOException("Không có Bluetooth.")
            val server = bluetooth.listenUsingRfcommWithServiceRecord("FlexMix Share", SHARE_UUID)
            serverSocket = server
            timeout = Runnable { finish(result, error = "Chưa có chủ máy nào gửi mã. Hãy chờ lại.") }
            main.postDelayed(timeout!!, DISCOVERABLE_SECONDS * 1000L)
            Thread {
                try {
                    val connection = server.accept()
                    try { server.close() } catch (_: IOException) { }
                    socket = connection
                    connection.use {
                        val reader = BufferedInputStream(connection.inputStream)
                        val writer = connection.outputStream
                        if (readMessage(reader).optString("type") != "identify") {
                            throw IOException("Thiết bị gửi không phải app FlexMix.")
                        }
                        writeLine(writer, "{\"type\":\"ready\",\"ok\":true}")
                        val packet = readLine(reader)
                        if (JSONObject(packet).optString("type") != "share") {
                            writeLine(writer, "{\"type\":\"ack\",\"ok\":false}")
                            throw IOException("Gói nhận được không phải mã chia sẻ.")
                        }
                        writeLine(writer, "{\"type\":\"ack\",\"ok\":true}")
                        // Chờ bên gửi đọc xong ACK và đóng trước, tránh mất ACK khi đóng sớm.
                        try { reader.read() } catch (_: IOException) { }
                        main.post { finish(result, packet) }
                    }
                } catch (error: Exception) {
                    main.post { finish(result, error = error.message ?: "Nhận mã chia sẻ thất bại.") }
                }
            }.start()
        } catch (error: Exception) {
            finish(result, error = error.message ?: "Không mở được Bluetooth để nhận.")
        }
    }

    private fun writeLine(writer: OutputStream, line: String) {
        writer.write("$line\n".toByteArray(Charsets.UTF_8))
        writer.flush()
    }

    private fun readLine(reader: BufferedInputStream): String {
        // Cùng một reader cho mọi dòng: không mất byte khi nhiều gói đến cùng lúc.
        val body = ByteArrayOutputStream()
        repeat(4096) {
            val value = reader.read()
            if (value == -1) throw IOException("Thiết bị ngắt kết nối trước khi gửi đủ gói.")
            if (value == 10) return body.toString("UTF-8")
            body.write(value)
        }
        throw IOException("Gói Bluetooth quá lớn.")
    }

    private fun readMessage(reader: BufferedInputStream) = JSONObject(readLine(reader))

    private fun finish(result: MethodChannel.Result, value: Any? = null, error: String? = null) {
        // Bỏ qua kết quả của worker cũ sau khi người dùng hủy hoặc timeout.
        if (pending !== result) return
        pending = null
        waitingPermission = false
        waitingDiscoverable = false
        afterPermission = null
        timeout?.let { main.removeCallbacks(it) }
        timeout = null
        receiver?.let { activity.unregisterReceiver(it) }
        receiver = null
        try { adapter?.cancelDiscovery() } catch (_: SecurityException) { }
        try { serverSocket?.close() } catch (_: IOException) { }
        serverSocket = null
        try { socket?.close() } catch (_: IOException) { }
        socket = null
        if (error == null) result.success(value) else result.error("bluetooth", error, null)
    }

    fun cancel() {
        val result = pending ?: return
        finish(result, error = "Đã hủy Bluetooth.")
    }
}
