from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
from adafruit_ble.services.standard.hid import HIDService
from adafruit_ble.services.standard.device_info import DeviceInfoService
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.consumer_control import ConsumerControl

_ble    = None
_kbd    = None
_layout = None
_cc     = None
_adv    = None

_setup_ok      = False  # hardware init succeeded
active         = False  # _setup_ok AND user-enabled
connected      = False
_prev_connected = False


def setup():
    global _ble, _kbd, _layout, _cc, _adv, _setup_ok, active
    try:
        _ble = BLERadio()
        _ble.name = "PicoDeck"
        hid = HIDService()
        DeviceInfoService(software_revision="1.0", manufacturer="PicoDeck")
        _adv = ProvideServicesAdvertisement(hid)
        _adv.appearance = 961  # HID keyboard
        _kbd    = Keyboard(hid.devices)
        _layout = KeyboardLayoutUS(_kbd)
        _cc     = ConsumerControl(hid.devices)
        _setup_ok = True
        active    = True
        print("BLE ready")
    except Exception as e:
        print("BLE setup failed:", e)
        _setup_ok = False
        active    = False


def disable():
    global active
    if not _setup_ok:
        return
    active = False
    try:
        if _ble.advertising:
            _ble.stop_advertising()
    except Exception:
        pass
    print("BLE disabled")


def enable():
    global active
    if not _setup_ok:
        return
    active = True
    start_advertising()
    print("BLE enabled")


def status_str():
    if not _setup_ok:
        return "Nicht verfügbar"
    if not active:
        return "Deaktiviert"
    if connected:
        return "Verbunden"
    return "Bereit"


def start_advertising():
    if not active:
        return
    try:
        if not _ble.advertising:
            _ble.start_advertising(_adv)
    except Exception as e:
        print("BLE adv:", e)


def press(*keycodes):
    if not active or not _ble.connected:
        return
    try:
        _kbd.press(*keycodes)
    except Exception:
        pass


def release_all():
    if not active or not _ble.connected:
        return
    try:
        _kbd.release_all()
    except Exception:
        pass


def send_consumer(code):
    if not active or not _ble.connected:
        return
    try:
        _cc.send(code)
    except Exception:
        pass


def send_text(text):
    if not active or not _ble.connected:
        return
    try:
        _layout.write(text)
    except Exception:
        pass


def poll():
    global connected, _prev_connected
    if not active:
        return
    connected = _ble.connected
    if connected and not _prev_connected:
        _ble.stop_advertising()
        print("BLE connected")
    elif not connected and _prev_connected:
        start_advertising()
        print("BLE reconnecting...")
    _prev_connected = connected
