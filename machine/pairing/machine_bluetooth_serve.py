"""BlueZ quảng bá dịch vụ SPP và nhận kết nối từ app."""

import socket
import threading

import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib

SPP_UUID = "00001101-0000-1000-8000-00805f9b34fb"
AGENT_PATH = "/flexmix/pairing/agent"
PROFILE_PATH = "/flexmix/pairing/profile"
AGENT_INTERFACE = "org.bluez.Agent1"
PROFILE_INTERFACE = "org.bluez.Profile1"
ADAPTER_INTERFACE = "org.bluez.Adapter1"


# BlueZ gọi method qua D-Bus nên hai lớp dưới đây là phần bắt buộc.
class PairingAgent(dbus.service.Object):
    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        pass

    @dbus.service.method(AGENT_INTERFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        pass

    @dbus.service.method(AGENT_INTERFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        pass

    @dbus.service.method(AGENT_INTERFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        if uuid.lower() != SPP_UUID:
            raise dbus.exceptions.DBusException(
                "Chỉ hỗ trợ FlexMix SPP", name="org.bluez.Error.Rejected"
            )

    @dbus.service.method(AGENT_INTERFACE, in_signature="", out_signature="")
    def Cancel(self):
        pass


class PairingProfile(dbus.service.Object):
    def __init__(self, bus, handler):
        super().__init__(bus, PROFILE_PATH)
        self.handler = handler
        self.connections = {}

    @dbus.service.method(PROFILE_INTERFACE, in_signature="oha{sv}", out_signature="")
    def NewConnection(self, device, fd, properties):
        # BlueZ đã listen/accept và xác thực bond trước khi chuyển socket.
        connection = socket.socket(fileno=fd.take())
        self.connections[device] = connection
        thread = threading.Thread(target=self.serve, args=(device, connection), daemon=True)
        thread.start()

    def serve(self, device, connection):
        try:
            success = self.handler(connection)
            print("Pairing hoàn tất:", success, flush=True)
        except (OSError, ValueError) as error:
            print("Pairing thất bại:", error, flush=True)
        finally:
            connection.close()
            if self.connections.get(device) is connection:
                self.connections.pop(device, None)

    @dbus.service.method(PROFILE_INTERFACE, in_signature="o", out_signature="")
    def RequestDisconnection(self, device):
        connection = self.connections.pop(device, None)
        if connection is not None:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()

    @dbus.service.method(PROFILE_INTERFACE, in_signature="", out_signature="")
    def Release(self):
        for device in list(self.connections):
            self.RequestDisconnection(device)


def run_server(machine_name, handler):
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Tìm adapter Bluetooth của Raspberry Pi.
    root = bus.get_object("org.bluez", "/")
    manager = dbus.Interface(root, "org.freedesktop.DBus.ObjectManager")
    adapter_path = None
    for path, interfaces in manager.GetManagedObjects().items():
        if ADAPTER_INTERFACE in interfaces:
            adapter_path = path
            break
    if adapter_path is None:
        raise RuntimeError("Không tìm thấy adapter Bluetooth")

    adapter = bus.get_object("org.bluez", adapter_path)
    properties = dbus.Interface(adapter, "org.freedesktop.DBus.Properties")
    properties.Set(ADAPTER_INTERFACE, "Powered", dbus.Boolean(True))
    properties.Set(ADAPTER_INTERFACE, "Alias", machine_name)

    # Giữ agent sống trong suốt thời gian app pair.
    bluez = bus.get_object("org.bluez", "/org/bluez")
    agent_manager = dbus.Interface(bluez, "org.bluez.AgentManager1")
    profile_manager = dbus.Interface(bluez, "org.bluez.ProfileManager1")
    agent = PairingAgent(bus, AGENT_PATH)
    profile = PairingProfile(bus, handler)
    agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
    try:
        agent_manager.RequestDefaultAgent(AGENT_PATH)
        profile_manager.RegisterProfile(PROFILE_PATH, SPP_UUID, {
            "Name": "FlexMix Pairing", "Role": "server",
            "Channel": dbus.UInt16(1),
            "RequireAuthentication": dbus.Boolean(True),
            "RequireAuthorization": dbus.Boolean(False),
        })
        try:
            properties.Set(ADAPTER_INTERFACE, "Pairable", dbus.Boolean(True))
            properties.Set(ADAPTER_INTERFACE, "DiscoverableTimeout", dbus.UInt32(120))
            properties.Set(ADAPTER_INTERFACE, "Discoverable", dbus.Boolean(True))
            print("Chờ app kết nối:", machine_name, flush=True)
            GLib.MainLoop().run()
        finally:
            profile.Release()
            profile_manager.UnregisterProfile(PROFILE_PATH)
            properties.Set(ADAPTER_INTERFACE, "Discoverable", dbus.Boolean(False))
    finally:
        agent_manager.UnregisterAgent(AGENT_PATH)
