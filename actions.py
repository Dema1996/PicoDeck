import time
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

import state
import menus
import display
import wifi_server
import ble_hid

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
consumer_control = ConsumerControl(usb_hid.devices)

SHORTCUT_ACTIONS = {
    "spotlight":        (Keycode.COMMAND, Keycode.SPACE),
    "lock_mac":         (Keycode.CONTROL, Keycode.COMMAND, Keycode.Q),
    "screenshot":       (Keycode.COMMAND, Keycode.SHIFT, Keycode.FIVE),
    "mission_control":  (Keycode.CONTROL, Keycode.UP_ARROW),
    "show_desktop":     (Keycode.F11,),
    "command_palette":  (Keycode.SHIFT, Keycode.COMMAND, Keycode.P),
    "toggle_terminal":  (Keycode.COMMAND, Keycode.J),
    "format_document":  (Keycode.OPTION, Keycode.SHIFT, Keycode.F),
    "app_switcher":     (Keycode.COMMAND, Keycode.TAB),
    "previous_app":     (Keycode.COMMAND, Keycode.SHIFT, Keycode.TAB),
    "new_terminal":     (Keycode.CONTROL, Keycode.GRAVE_ACCENT),
    "split_editor":     (Keycode.COMMAND, Keycode.BACKSLASH),
    "close_window":     (Keycode.COMMAND, Keycode.W),
    "open_whisper":     (Keycode.F5,),
}

MEDIA_ACTIONS = {
    "play_pause":     ConsumerControlCode.PLAY_PAUSE,
    "stop":           ConsumerControlCode.STOP,
    "mute":           ConsumerControlCode.MUTE,
    "next_track":     ConsumerControlCode.SCAN_NEXT_TRACK,
    "previous_track": ConsumerControlCode.SCAN_PREVIOUS_TRACK,
    "volume_up":           ConsumerControlCode.VOLUME_INCREMENT,
    "volume_down":         ConsumerControlCode.VOLUME_DECREMENT,
    "mac_brightness_up":   ConsumerControlCode.BRIGHTNESS_INCREMENT,
    "mac_brightness_down": ConsumerControlCode.BRIGHTNESS_DECREMENT,
}

ENCODER_MODE_ACTIONS = {
    "encoder_navigate":       "navigate",
    "encoder_volume":         "volume",
    "encoder_brightness":     "brightness",
    "encoder_mac_brightness": "mac_brightness",
}


def send_shortcut(*keys):
    keyboard.press(*keys)
    ble_hid.press(*keys)
    time.sleep(0.1)
    keyboard.release_all()
    ble_hid.release_all()


def send_media(consumer_code):
    consumer_control.send(consumer_code)
    ble_hid.send_consumer(consumer_code)


def execute_action(action):
    display.show_message("Action", menus.format_action_label(action))
    time.sleep(0.2)
    if action in SHORTCUT_ACTIONS:
        send_shortcut(*SHORTCUT_ACTIONS[action])
    elif action == "open_vscode":
        send_shortcut(Keycode.COMMAND, Keycode.SPACE)
        time.sleep(0.5)
        keyboard_layout.write("code\n")
        ble_hid.send_text("code\n")
    elif action in MEDIA_ACTIONS:
        send_media(MEDIA_ACTIONS[action])
    elif action in ENCODER_MODE_ACTIONS:
        state.encoder_mode = ENCODER_MODE_ACTIONS[action]
    elif action == "wifi_status":
        if wifi_server.active:
            mode_str = "STA" if wifi_server.mode == "sta" else "AP"
            display.show_message(mode_str, wifi_server.ip())
        else:
            display.show_message("WiFi", "Aus")
        time.sleep(1.5)
    elif action == "wifi_start_ap":
        if wifi_server.active:
            wifi_server.stop()
        display.show_message("WiFi AP", "Startet...")
        if wifi_server.start_ap():
            state.wifi_active = True
            display.show_message(wifi_server.SSID, wifi_server.ip())
            time.sleep(2.0)
        else:
            display.show_message("AP Fehler", "")
            time.sleep(1.0)
    elif action == "toggle_wifi":
        if wifi_server.active:
            wifi_server.stop()
            state.wifi_active = False
            display.show_message("WiFi", "Gestoppt")
            time.sleep(0.8)
        else:
            display.show_message("WiFi", "Startet...")
            if wifi_server.start():
                state.wifi_active = True
                display.show_message(wifi_server.SSID, wifi_server.ip())
                time.sleep(2.0)
            else:
                display.show_message("WiFi Fehler", "")
                time.sleep(1.0)
    elif action == "toggle_encoder_dir":
        state.encoder_reversed = not state.encoder_reversed
        display.show_message("Enc. Richtung", "Invertiert" if state.encoder_reversed else "Normal")
        time.sleep(0.8)
    elif action == "encoder_speed_slow":
        state.encoder_threshold = 4
        display.show_message("Enc. Speed", "Langsam")
        time.sleep(0.8)
    elif action == "encoder_speed_normal":
        state.encoder_threshold = 2
        display.show_message("Enc. Speed", "Normal")
        time.sleep(0.8)
    elif action == "encoder_speed_fast":
        state.encoder_threshold = 1
        display.show_message("Enc. Speed", "Schnell")
        time.sleep(0.8)
    elif action == "hold_time_05":
        state.button_assign_hold_time = 0.5
        display.show_message("Hold-Zeit", "0.5 Sek")
        time.sleep(0.8)
    elif action == "hold_time_10":
        state.button_assign_hold_time = 1.0
        display.show_message("Hold-Zeit", "1.0 Sek")
        time.sleep(0.8)
    elif action == "hold_time_20":
        state.button_assign_hold_time = 2.0
        display.show_message("Hold-Zeit", "2.0 Sek")
        time.sleep(0.8)
    elif action == "bt_status":
        display.show_message("Bluetooth", ble_hid.status_str())
        time.sleep(1.5)
    elif action == "bt_toggle":
        if ble_hid.active:
            ble_hid.disable()
            display.show_message("Bluetooth", "Deaktiviert")
        else:
            ble_hid.enable()
            display.show_message("Bluetooth", "Aktiviert")
        time.sleep(0.8)
    elif action == "ss_timeout_15":
        state.screensaver_timeout = 15
        display.show_message("Bildschirm", "15 Sek")
        time.sleep(0.8)
    elif action == "ss_timeout_30":
        state.screensaver_timeout = 30
        display.show_message("Bildschirm", "30 Sek")
        time.sleep(0.8)
    elif action == "ss_timeout_60":
        state.screensaver_timeout = 60
        display.show_message("Bildschirm", "1 Minute")
        time.sleep(0.8)
    elif action == "ss_timeout_300":
        state.screensaver_timeout = 300
        display.show_message("Bildschirm", "5 Minuten")
        time.sleep(0.8)
    elif action == "ss_timeout_off":
        state.screensaver_timeout = 9999
        display.show_message("Bildschirm", "Aus")
        time.sleep(0.8)
    elif action.startswith("brightness_"):
        try:
            level = int(action.split("_")[1])
            state.brightness = max(10, min(100, level))
            display.set_brightness(state.brightness)
            display.show_message("Helligkeit", str(state.brightness) + "%")
            time.sleep(0.6)
        except (ValueError, IndexError):
            pass
    elif action == "toggle_inversion":
        display.set_inversion(not state.display_inverted)
        display.show_message("Invertierung", "Ein" if state.display_inverted else "Aus")
        time.sleep(0.6)
    elif action == "menu_timeout_off":
        state.menu_timeout = 0
        display.show_message("Men\xfc-Timeout", "Aus")
        time.sleep(0.6)
    elif action.startswith("menu_timeout_"):
        try:
            state.menu_timeout = int(action.split("_")[2])
            display.show_message("Men\xfc-Timeout", action.split("_")[2] + " Sek")
            time.sleep(0.6)
        except (ValueError, IndexError):
            pass
    time.sleep(0.3)
    display.draw_menu()


def handle_encoder_mode_step(step):
    if state.encoder_mode == "volume":
        send_media(ConsumerControlCode.VOLUME_INCREMENT if step > 0 else ConsumerControlCode.VOLUME_DECREMENT)
    elif state.encoder_mode == "brightness":
        state.brightness = max(10, min(100, state.brightness + step * 10))
        display.set_brightness(state.brightness)
        display.draw_menu()
    elif state.encoder_mode == "mac_brightness":
        send_media(ConsumerControlCode.BRIGHTNESS_INCREMENT if step > 0 else ConsumerControlCode.BRIGHTNESS_DECREMENT)
