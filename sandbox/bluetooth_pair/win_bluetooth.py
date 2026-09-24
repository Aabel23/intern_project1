"""Phần Bluetooth Windows dùng chung cho các sandbox: RFCOMM server, SDP, log gói tin."""

import ctypes
import json
import socket
import sys
import time
import uuid
from ctypes import wintypes

BT_PORT_ANY = -1
NS_BTH = 16
RNRSERVICE_REGISTER = 0
RNRSERVICE_DELETE = 2


def log(direction, raw):
    stamp = time.strftime("%H:%M:%S")
    text = raw.decode("utf-8", errors="replace").rstrip("\n")
    try:
        text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    except ValueError:
        pass
    print(f"[{stamp}] {direction} {len(raw)} byte", flush=True)
    print(text, flush=True)


class LoggedReader:
    def __init__(self, reader, direction):
        self.reader = reader
        self.direction = direction

    def readline(self, size=-1):
        line = self.reader.readline(size)
        log(self.direction, line)
        return line

    def read(self, size=-1):
        return self.reader.read(size)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.reader.close()


class LoggedConnection:
    """Bọc socket để in mọi gói tin mà handler gửi/nhận."""

    def __init__(self, connection, peer, me):
        self.connection = connection
        self.incoming = f"{peer} -> {me}"
        self.outgoing = f"{me} -> {peer}"

    def settimeout(self, seconds):
        self.connection.settimeout(seconds)

    def makefile(self, mode):
        return LoggedReader(self.connection.makefile(mode), self.incoming)

    def sendall(self, data):
        log(self.outgoing, data)
        self.connection.sendall(data)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        self.connection.close()


# Python không có API quảng bá SDP trên Windows nên gọi WSASetServiceW qua ctypes.
class GUID(ctypes.Structure):
    _fields_ = [("data", ctypes.c_ubyte * 16)]


class SOCKADDR_BTH(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("addressFamily", ctypes.c_ushort),
        ("btAddr", ctypes.c_ulonglong),
        ("serviceClassId", GUID),
        ("port", ctypes.c_ulong),
    ]


class SOCKET_ADDRESS(ctypes.Structure):
    _fields_ = [("lpSockaddr", ctypes.c_void_p), ("iSockaddrLength", ctypes.c_int)]


class CSADDR_INFO(ctypes.Structure):
    _fields_ = [
        ("LocalAddr", SOCKET_ADDRESS),
        ("RemoteAddr", SOCKET_ADDRESS),
        ("iSocketType", ctypes.c_int),
        ("iProtocol", ctypes.c_int),
    ]


class WSAQUERYSETW(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("lpszServiceInstanceName", wintypes.LPWSTR),
        ("lpServiceClassId", ctypes.POINTER(GUID)),
        ("lpVersion", ctypes.c_void_p),
        ("lpszComment", wintypes.LPWSTR),
        ("dwNameSpace", wintypes.DWORD),
        ("lpNSProviderId", ctypes.c_void_p),
        ("lpszContext", wintypes.LPWSTR),
        ("dwNumberOfProtocols", wintypes.DWORD),
        ("lpafpProtocols", ctypes.c_void_p),
        ("lpszQueryString", wintypes.LPWSTR),
        ("dwNumberOfCsAddrs", wintypes.DWORD),
        ("lpcsaBuffer", ctypes.POINTER(CSADDR_INFO)),
        ("dwOutputFlags", wintypes.DWORD),
        ("lpBlob", ctypes.c_void_p),
    ]


class ServiceRecord:
    """Bản ghi SDP để Android tìm thấy service UUID trên đúng channel RFCOMM."""

    def __init__(self, service_uuid, name, channel):
        self.guid = GUID((ctypes.c_ubyte * 16)(*uuid.UUID(service_uuid).bytes_le))
        self.address = SOCKADDR_BTH(socket.AF_BLUETOOTH, 0, self.guid, channel)
        self.info = CSADDR_INFO(
            SOCKET_ADDRESS(ctypes.cast(ctypes.pointer(self.address), ctypes.c_void_p),
                           ctypes.sizeof(self.address)),
            SOCKET_ADDRESS(None, 0),
            socket.SOCK_STREAM,
            socket.BTPROTO_RFCOMM,
        )
        self.query = WSAQUERYSETW()
        self.query.dwSize = ctypes.sizeof(WSAQUERYSETW)
        self.query.lpszServiceInstanceName = name
        self.query.lpServiceClassId = ctypes.pointer(self.guid)
        self.query.dwNameSpace = NS_BTH
        self.query.dwNumberOfCsAddrs = 1
        self.query.lpcsaBuffer = ctypes.pointer(self.info)

    def set(self, operation):
        result = ctypes.windll.ws2_32.WSASetServiceW(ctypes.byref(self.query), operation, 0)
        if result != 0:
            code = ctypes.windll.ws2_32.WSAGetLastError()
            raise OSError(f"WSASetServiceW lỗi {code}")


def set_discoverable(enabled):
    """Windows chỉ cho quét thấy khi mở trang Bluetooth; bật thẳng qua bthprops."""
    bthprops = ctypes.WinDLL("bthprops.cpl")
    if enabled:
        bthprops.BluetoothEnableIncomingConnections(None, True)
    bthprops.BluetoothEnableDiscovery(None, enabled)
    return bool(bthprops.BluetoothIsDiscoverable(None))


def serve(service_uuid, name, handler, peer, me, once=False):
    """Mở RFCOMM + SDP, cho quét thấy rồi gọi handler cho từng kết nối.

    once=True: dừng sau lần handler chạy xong không lỗi và trả kết quả đó.
    """
    if sys.platform != "win32":
        sys.exit("Sandbox này dành cho Windows.")
    print(f"Tên Bluetooth của laptop: {socket.gethostname()}", flush=True)
    server = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
    server.bind(("00:00:00:00:00:00", BT_PORT_ANY))
    server.listen(1)
    address, channel = server.getsockname()
    record = ServiceRecord(service_uuid, name, channel)
    record.set(RNRSERVICE_REGISTER)
    if not set_discoverable(True):
        print("CẢNH BÁO: không bật được chế độ cho quét thấy; mở Settings > Bluetooth.", flush=True)
    # accept có timeout để Ctrl+C dừng được trên Windows.
    server.settimeout(1)
    print(f"{me} chờ {peer} kết nối: {address}, RFCOMM channel {channel}", flush=True)
    try:
        while True:
            try:
                connection, remote = server.accept()
            except socket.timeout:
                # Windows có thể tự tắt chế độ quét thấy, bật lại liên tục.
                set_discoverable(True)
                continue
            connection.settimeout(None)
            print(f"\n=== {peer} kết nối từ {remote[0]} ===", flush=True)
            try:
                result = handler(LoggedConnection(connection, peer, me))
                print("=== Hoàn tất:", bool(result), "===", flush=True)
                if once and result:
                    return result
            except (OSError, ValueError) as error:
                print("=== Thất bại:", error, "===", flush=True)
    except KeyboardInterrupt:
        return None
    finally:
        set_discoverable(False)
        record.set(RNRSERVICE_DELETE)
        server.close()
        print(f"Đã dừng {me}.", flush=True)
