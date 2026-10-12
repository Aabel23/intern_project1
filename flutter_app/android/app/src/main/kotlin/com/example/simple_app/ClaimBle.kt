package com.example.simple_app

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothGatt
import android.bluetooth.BluetoothGattCallback
import android.bluetooth.BluetoothGattCharacteristic
import android.bluetooth.BluetoothGattDescriptor
import android.bluetooth.BluetoothManager
import android.bluetooth.BluetoothProfile
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Build
import android.os.ParcelUuid
import java.util.UUID
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit

/**
 * BLE GATT client for the claim session: scan by service UUID, one GATT operation at a time,
 * MTU 517 request, indications on TX, writes with response on RX, u32be length framing.
 * Blocking API: call from a worker thread only (ClaimChannel does that).
 */
@SuppressLint("MissingPermission")
class ClaimBle(private val context: Context) {
    companion object {
        val SERVICE: UUID = UUID.fromString("8b9bf000-01f0-4e5e-ae8f-c8a0e70a5100")
        val RX: UUID = UUID.fromString("8b9bf001-01f0-4e5e-ae8f-c8a0e70a5100")
        val TX: UUID = UUID.fromString("8b9bf002-01f0-4e5e-ae8f-c8a0e70a5100")
        val CCCD: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
        const val MAX_PACKET = 8192
        const val OP_TIMEOUT_MS = 10_000L
    }

    private sealed class Event {
        data class Connection(val connected: Boolean, val status: Int) : Event()
        data class Done(val status: Int) : Event()
        data class Mtu(val mtu: Int, val status: Int) : Event()
        data class Notify(val value: ByteArray) : Event()
    }

    private val events = LinkedBlockingQueue<Event>()
    private val packets = LinkedBlockingQueue<ByteArray>()
    private var buffer = ByteArray(0)
    private var gatt: BluetoothGatt? = null
    private var rx: BluetoothGattCharacteristic? = null
    private var mtu = 23

    private val callback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(g: BluetoothGatt, status: Int, newState: Int) {
            events.put(Event.Connection(newState == BluetoothProfile.STATE_CONNECTED, status))
        }
        override fun onServicesDiscovered(g: BluetoothGatt, status: Int) { events.put(Event.Done(status)) }
        override fun onMtuChanged(g: BluetoothGatt, value: Int, status: Int) { events.put(Event.Mtu(value, status)) }
        override fun onDescriptorWrite(g: BluetoothGatt, d: BluetoothGattDescriptor, status: Int) { events.put(Event.Done(status)) }
        override fun onCharacteristicWrite(g: BluetoothGatt, c: BluetoothGattCharacteristic, status: Int) { events.put(Event.Done(status)) }
        @Deprecated("API < 33")
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic) {
            @Suppress("DEPRECATION") onChunk(c.value ?: ByteArray(0))
        }
        override fun onCharacteristicChanged(g: BluetoothGatt, c: BluetoothGattCharacteristic, value: ByteArray) { onChunk(value) }
    }

    // Reassembles u32be length-prefixed packets from indication fragments (callback thread).
    @Synchronized private fun onChunk(chunk: ByteArray) {
        buffer += chunk
        while (buffer.size >= 4) {
            val length = ((buffer[0].toInt() and 0xff) shl 24) or ((buffer[1].toInt() and 0xff) shl 16) or
                ((buffer[2].toInt() and 0xff) shl 8) or (buffer[3].toInt() and 0xff)
            if (length <= 0 || length > MAX_PACKET) { buffer = ByteArray(0); packets.put(ByteArray(0)); return }
            if (buffer.size < 4 + length) return
            packets.put(buffer.copyOfRange(4, 4 + length))
            buffer = buffer.copyOfRange(4 + length, buffer.size)
        }
    }

    private inline fun <reified T : Event> await(timeout: Long = OP_TIMEOUT_MS): T {
        val deadline = System.currentTimeMillis() + timeout
        while (true) {
            val left = deadline - System.currentTimeMillis()
            val e = if (left > 0) events.poll(left, TimeUnit.MILLISECONDS) else null
            when {
                e == null -> throw PairingFailure("PAIRING_TIMEOUT")
                e is Event.Connection && !e.connected -> throw PairingFailure("PAIRING_TRANSPORT_ERROR")
                e is T -> return e
            }
        }
    }

    /** Machines advertising the claim service, strongest first. */
    fun scan(windowMs: Long = 5000): List<BluetoothDevice> {
        val adapter = context.getSystemService(BluetoothManager::class.java)?.adapter
        val scanner = adapter?.bluetoothLeScanner ?: throw PairingFailure("BLUETOOTH_OFF")
        val found = LinkedHashMap<String, Pair<BluetoothDevice, Int>>()
        val cb = object : ScanCallback() {
            override fun onScanResult(type: Int, r: ScanResult) { synchronized(found) { found[r.device.address] = r.device to r.rssi } }
        }
        scanner.startScan(listOf(ScanFilter.Builder().setServiceUuid(ParcelUuid(SERVICE)).build()),
            ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build(), cb)
        Thread.sleep(windowMs)
        scanner.stopScan(cb)
        return synchronized(found) { found.values.sortedByDescending { it.second }.map { it.first } }
    }

    /** Connects, negotiates MTU, subscribes to TX; returns the hello packet the machine sends on subscribe. */
    fun connect(device: BluetoothDevice): ByteArray {
        events.clear(); packets.clear(); buffer = ByteArray(0)
        val g = device.connectGatt(context, false, callback, BluetoothDevice.TRANSPORT_LE)
        gatt = g
        val c = await<Event.Connection>()
        if (c.status != BluetoothGatt.GATT_SUCCESS) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        g.requestMtu(517)
        mtu = await<Event.Mtu>().let { if (it.status == BluetoothGatt.GATT_SUCCESS) it.mtu else 23 }
        g.requestConnectionPriority(BluetoothGatt.CONNECTION_PRIORITY_HIGH)
        if (!g.discoverServices()) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        if (await<Event.Done>().status != BluetoothGatt.GATT_SUCCESS) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        val service = g.getService(SERVICE) ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        rx = service.getCharacteristic(RX) ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        val tx = service.getCharacteristic(TX) ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        g.setCharacteristicNotification(tx, true)
        val cccd = tx.getDescriptor(CCCD) ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        writeDescriptor(g, cccd, BluetoothGattDescriptor.ENABLE_INDICATION_VALUE)
        return receive()
    }

    private fun writeDescriptor(g: BluetoothGatt, d: BluetoothGattDescriptor, value: ByteArray) {
        if (Build.VERSION.SDK_INT >= 33) {
            if (g.writeDescriptor(d, value) != BluetoothGatt.GATT_SUCCESS) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        } else {
            @Suppress("DEPRECATION") run { d.value = value; if (!g.writeDescriptor(d)) throw PairingFailure("PAIRING_TRANSPORT_ERROR") }
        }
        if (await<Event.Done>().status != BluetoothGatt.GATT_SUCCESS) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
    }

    fun send(packet: ByteArray) {
        val g = gatt ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        val c = rx ?: throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        val data = FlexJson.frame(packet)
        val size = maxOf(20, minOf(mtu - 3, 512))
        var offset = 0
        while (offset < data.size) {
            val chunk = data.copyOfRange(offset, minOf(data.size, offset + size))
            // Next fragment only after the write-with-response callback: one GATT op in flight.
            if (Build.VERSION.SDK_INT >= 33) {
                if (g.writeCharacteristic(c, chunk, BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT) != BluetoothGatt.GATT_SUCCESS)
                    throw PairingFailure("PAIRING_TRANSPORT_ERROR")
            } else {
                @Suppress("DEPRECATION") run {
                    c.writeType = BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT; c.value = chunk
                    if (!g.writeCharacteristic(c)) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
                }
            }
            if (await<Event.Done>().status != BluetoothGatt.GATT_SUCCESS) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
            offset += size
        }
    }

    fun receive(timeoutMs: Long = 60_000): ByteArray {
        val packet = packets.poll(timeoutMs, TimeUnit.MILLISECONDS) ?: throw PairingFailure("PAIRING_TIMEOUT")
        if (packet.isEmpty()) throw PairingFailure("PAIRING_TRANSPORT_ERROR")
        return packet
    }

    fun close() {
        gatt?.let { it.disconnect(); it.close() }
        gatt = null; rx = null; buffer = ByteArray(0); packets.clear(); events.clear()
    }
}
