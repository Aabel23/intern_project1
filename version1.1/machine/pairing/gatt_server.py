"""BlueZ GATT server cho phiên nhận máy (theo test/example-gatt-server của BlueZ, dbus-python + GLib).

Một service, RX (write with response) và TX (indicate). Một kết nối tại một thời điểm; kết nối
khác bị bỏ qua. Mảnh TX kế tiếp chỉ gửi sau khi điện thoại xác nhận indication (Confirm).
Không bond, không pairing agent: chứng thực nằm trong phiên HPKE PSK.
"""

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib

from machine.pairing.claim_link import ClaimLink

SERVICE_UUID = "8b9bf000-01f0-4e5e-ae8f-c8a0e70a5100"
RX_UUID = "8b9bf001-01f0-4e5e-ae8f-c8a0e70a5100"
TX_UUID = "8b9bf002-01f0-4e5e-ae8f-c8a0e70a5100"

BLUEZ = "org.bluez"
DBUS_OM = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP = "org.freedesktop.DBus.Properties"
GATT_MANAGER = "org.bluez.GattManager1"
ADV_MANAGER = "org.bluez.LEAdvertisingManager1"
GATT_SERVICE = "org.bluez.GattService1"
GATT_CHRC = "org.bluez.GattCharacteristic1"
LE_ADV = "org.bluez.LEAdvertisement1"
APP_PATH = "/flexmix/claim"


class Failed(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.Failed"


class NotPermitted(dbus.exceptions.DBusException):
    _dbus_error_name = "org.bluez.Error.NotPermitted"


class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = APP_PATH
        self.services = []
        super().__init__(bus, self.path)

    @dbus.service.method(DBUS_OM, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        objects = {}
        for service in self.services:
            objects[service.get_path()] = service.get_properties()
            for chrc in service.characteristics:
                objects[chrc.get_path()] = chrc.get_properties()
        return objects


class Service(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = f"{APP_PATH}/service{index}"
        self.characteristics = []
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {GATT_SERVICE: {"UUID": SERVICE_UUID, "Primary": True,
                               "Characteristics": dbus.Array([c.get_path() for c in self.characteristics], signature="o")}}

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()[GATT_SERVICE]


class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, service, uuid, flags):
        self.path = f"{service.path}/char{index}"
        self.service, self.uuid, self.flags = service, uuid, flags
        super().__init__(bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {GATT_CHRC: {"Service": self.service.get_path(), "UUID": self.uuid, "Flags": self.flags}}

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return self.get_properties()[GATT_CHRC]


class TxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, link):
        super().__init__(bus, index, service, TX_UUID, ["indicate"])
        self.link = link
        self.subscribed = False
        self.value = b""

    @dbus.service.method(GATT_CHRC)
    def StartNotify(self):
        # App đã bật indication (CCCD 0x0002): bắt đầu phiên bằng hello.
        self.subscribed = True
        self.link.subscribed()

    @dbus.service.method(GATT_CHRC)
    def StopNotify(self):
        self.subscribed = False
        self.link.disconnected()

    @dbus.service.method(GATT_CHRC)
    def Confirm(self):
        self.link.confirmed()

    def indicate(self, chunk):
        self.value = chunk
        self.PropertiesChanged(GATT_CHRC, {"Value": dbus.Array(chunk, signature="y")}, [])

    @dbus.service.signal(DBUS_PROP, signature="sa{sv}as")
    def PropertiesChanged(self, interface, changed, invalidated):
        pass


class RxCharacteristic(Characteristic):
    def __init__(self, bus, index, service, link):
        super().__init__(bus, index, service, RX_UUID, ["write"])
        self.link = link

    @dbus.service.method(GATT_CHRC, in_signature="aya{sv}")
    def WriteValue(self, value, options):
        if int(options.get("offset", 0)) != 0 or str(options.get("type", "request")) != "request":
            raise NotPermitted("write type")
        if not self.link.receive(str(options.get("device", "")), bytes(value), int(options.get("mtu", 23))):
            raise Failed("busy")


class Advertisement(dbus.service.Object):
    def __init__(self, bus, name):
        self.path = APP_PATH + "/advertisement0"
        self.name = name
        super().__init__(bus, self.path)

    @dbus.service.method(DBUS_PROP, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        return {"Type": "peripheral", "ServiceUUIDs": dbus.Array([SERVICE_UUID], signature="s"),
                "LocalName": dbus.String(self.name[:20]), "Includes": dbus.Array(["tx-power"], signature="s")}

    @dbus.service.method(LE_ADV)
    def Release(self):
        pass


def adapter_path(bus):
    manager = dbus.Interface(bus.get_object(BLUEZ, "/"), DBUS_OM)
    for path, interfaces in manager.GetManagedObjects().items():
        if GATT_MANAGER in interfaces and ADV_MANAGER in interfaces:
            return path
    raise RuntimeError("Không tìm thấy adapter BLE")


def run(name, new_session, advertise=lambda: True):
    """Chạy vòng GLib; advertise() quyết định có quảng bá không (cửa sổ claim, v2 D2)."""
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    path = adapter_path(bus)
    dbus.Interface(bus.get_object(BLUEZ, path), DBUS_PROP).Set("org.bluez.Adapter1", "Powered", dbus.Boolean(True))
    link = ClaimLink(new_session)
    app = Application(bus)
    service = Service(bus, 0)
    link.tx = TxCharacteristic(bus, 1, service, link)
    service.characteristics = [RxCharacteristic(bus, 0, service, link), link.tx]
    app.services.append(service)
    loop = GLib.MainLoop()
    gatt = dbus.Interface(bus.get_object(BLUEZ, path), GATT_MANAGER)
    adverts = dbus.Interface(bus.get_object(BLUEZ, path), ADV_MANAGER)
    advertisement = Advertisement(bus, name)

    def fail(error):
        print("BlueZ:", error, flush=True)
        loop.quit()

    gatt.RegisterApplication(app.path, {}, reply_handler=lambda: None, error_handler=fail)
    state = {"advertising": False}

    def tick():
        wanted = advertise() and link.session is None
        if wanted and not state["advertising"]:
            adverts.RegisterAdvertisement(advertisement.path, {}, reply_handler=lambda: None, error_handler=fail)
        elif not wanted and state["advertising"]:
            try:
                adverts.UnregisterAdvertisement(advertisement.path)
            except dbus.exceptions.DBusException:
                pass
        state["advertising"] = wanted
        return True

    tick()
    GLib.timeout_add_seconds(5, tick)
    loop.run()
