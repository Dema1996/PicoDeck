import time
import os
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

import state
import menus
import display
import touch
import wifi_server
import ble_hid
import sdcard
import screensaver
import storage

keyboard = Keyboard(usb_hid.devices)
keyboard_layout = KeyboardLayoutUS(keyboard)
consumer_control = ConsumerControl(usb_hid.devices)

SHORTCUT_ACTIONS = {
    # macOS system
    "spotlight":        (Keycode.COMMAND, Keycode.SPACE),
    "lock_mac":         (Keycode.CONTROL, Keycode.COMMAND, Keycode.Q),
    "screenshot":       (Keycode.COMMAND, Keycode.SHIFT, Keycode.FIVE),
    "mission_control":  (Keycode.CONTROL, Keycode.UP_ARROW),
    "show_desktop":     (Keycode.F11,),
    "app_switcher":     (Keycode.COMMAND, Keycode.TAB),
    "previous_app":     (Keycode.COMMAND, Keycode.SHIFT, Keycode.TAB),
    "close_window":     (Keycode.COMMAND, Keycode.W),
    "full_screen":      (Keycode.CONTROL, Keycode.COMMAND, Keycode.F),
    "minimize":         (Keycode.COMMAND, Keycode.M),
    "hide_window":      (Keycode.COMMAND, Keycode.H),
    "emoji_picker":     (Keycode.CONTROL, Keycode.COMMAND, Keycode.SPACE),
    # editing
    "undo":             (Keycode.COMMAND, Keycode.Z),
    "redo":             (Keycode.COMMAND, Keycode.SHIFT, Keycode.Z),
    "copy":             (Keycode.COMMAND, Keycode.C),
    "cut":              (Keycode.COMMAND, Keycode.X),
    "paste":            (Keycode.COMMAND, Keycode.V),
    "select_all":       (Keycode.COMMAND, Keycode.A),
    "save":             (Keycode.COMMAND, Keycode.S),
    "find":             (Keycode.COMMAND, Keycode.F),
    "zoom_in":          (Keycode.COMMAND, Keycode.EQUALS),
    "zoom_out":         (Keycode.COMMAND, Keycode.MINUS),
    # browser / tabs
    "new_tab":          (Keycode.COMMAND, Keycode.T),
    "close_tab":        (Keycode.COMMAND, Keycode.W),
    "prev_tab":         (Keycode.COMMAND, Keycode.SHIFT, Keycode.LEFT_BRACKET),
    "next_tab":         (Keycode.COMMAND, Keycode.SHIFT, Keycode.RIGHT_BRACKET),
    "reload":           (Keycode.COMMAND, Keycode.R),
    # coding / VSCode
    "command_palette":  (Keycode.SHIFT, Keycode.COMMAND, Keycode.P),
    "toggle_terminal":  (Keycode.COMMAND, Keycode.J),
    "format_document":  (Keycode.OPTION, Keycode.SHIFT, Keycode.F),
    "new_terminal":     (Keycode.CONTROL, Keycode.GRAVE_ACCENT),
    "split_editor":     (Keycode.COMMAND, Keycode.BACKSLASH),
    "vscode_go_file":   (Keycode.COMMAND, Keycode.P),
    "vscode_go_line":   (Keycode.CONTROL, Keycode.G),
    "vscode_rename":    (Keycode.F2,),
    "vscode_comment":   (Keycode.COMMAND, Keycode.FORWARD_SLASH),
    "vscode_explorer":  (Keycode.COMMAND, Keycode.SHIFT, Keycode.E),
    "vscode_git":       (Keycode.CONTROL, Keycode.SHIFT, Keycode.G),
    "vscode_problems":  (Keycode.COMMAND, Keycode.SHIFT, Keycode.M),
    "vscode_run":       (Keycode.F5,),
    "vscode_fold":      (Keycode.COMMAND, Keycode.SHIFT, Keycode.LEFT_BRACKET),
    "vscode_unfold":    (Keycode.COMMAND, Keycode.SHIFT, Keycode.RIGHT_BRACKET),
    "vscode_sidebar":   (Keycode.COMMAND, Keycode.B),
    # other
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


def _save_settings():
    try:
        import persistence
        persistence.save_button_actions()
    except (OSError, ValueError) as e:
        print("settings save error:", e)


def send_shortcut(*keys):
    keyboard.press(*keys)
    ble_hid.press(*keys)
    time.sleep(0.1)
    keyboard.release_all()
    ble_hid.release_all()


def send_media(consumer_code):
    consumer_control.send(consumer_code)
    ble_hid.send_consumer(consumer_code)


def _wait_raw_tap():
    """Block until touch press + release. Returns median (raw_cmd_y, raw_cmd_x)."""
    while touch.read_raw_position() is None:
        time.sleep(0.02)
    samples_y = []
    samples_x = []
    while True:
        r = touch.read_raw_position()
        if r is None:
            break
        samples_y.append(r[0])
        samples_x.append(r[1])
        time.sleep(0.02)
    samples_y.sort()
    samples_x.sort()
    mid = len(samples_y) // 2
    time.sleep(0.3)
    return samples_y[mid], samples_x[mid]


def run_touch_calibration():
    MARGIN = 20
    W, H = 240, 320

    # 4 corners: (label, screen_x, screen_y)
    steps = [
        ("Oben Links",    MARGIN,      MARGIN),
        ("Oben Rechts",   W - MARGIN,  MARGIN),
        ("Unten Links",   MARGIN,      H - MARGIN),
        ("Unten Rechts",  W - MARGIN,  H - MARGIN),
    ]
    results = []
    for i, (name, sx, sy) in enumerate(steps):
        display.show_message("{}/4  Tippe:".format(i + 1), name)
        ry, rx = _wait_raw_tap()
        results.append((sx, sy, ry, rx))

    # Average the two left-edge and two right-edge CMD_Y readings → X axis
    left_ry  = (results[0][2] + results[2][2]) // 2   # oben-links + unten-links
    right_ry = (results[1][2] + results[3][2]) // 2   # oben-rechts + unten-rechts
    # Average the two top-edge and two bottom-edge CMD_X readings → Y axis
    top_rx   = (results[0][3] + results[1][3]) // 2   # oben-links + oben-rechts
    bot_rx   = (results[2][3] + results[3][3]) // 2   # unten-links + unten-rechts

    # Extrapolate to screen edges (compensate for MARGIN offset)
    ry_range = right_ry - left_ry
    rx_range = bot_rx   - top_rx
    margin_ratio_x = MARGIN / (W - 2 * MARGIN)
    margin_ratio_y = MARGIN / (H - 2 * MARGIN)
    x_min = int(left_ry - ry_range * margin_ratio_x)
    x_max = int(right_ry + ry_range * margin_ratio_x)
    y_min = int(top_rx  - rx_range * margin_ratio_y)
    y_max = int(bot_rx  + rx_range * margin_ratio_y)

    state.touch_cal = (x_min, x_max, y_min, y_max)
    touch.apply_calibration(x_min, x_max, y_min, y_max)
    _save_settings()
    display.show_message("Kalibriert", "OK")
    time.sleep(1.5)
    display.draw_menu()


def execute_action(action):
    if action not in ("nav_back", "nav_up", "nav_down", "nav_select"):
        display.show_message("Action", menus.format_action_label(action))
        time.sleep(0.2)
    if action.startswith("text:"):
        text = action[5:]
        keyboard_layout.write(text)
        ble_hid.send_text(text)
    elif action in SHORTCUT_ACTIONS:
        send_shortcut(*SHORTCUT_ACTIONS[action])
    elif action == "open_vscode":
        send_shortcut(Keycode.COMMAND, Keycode.SPACE)
        time.sleep(0.5)
        keyboard_layout.write("code\n")
        ble_hid.send_text("code\n")
    elif action in MEDIA_ACTIONS:  # noqa (keep elif chain)
        send_media(MEDIA_ACTIONS[action])
    elif action in ENCODER_MODE_ACTIONS:
        state.encoder_mode = ENCODER_MODE_ACTIONS[action]
        _save_settings()
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
                label = "STA" if wifi_server.mode == "sta" else wifi_server.SSID
                display.show_message(label, wifi_server.ip())
                time.sleep(2.0)
            else:
                display.show_message("WiFi Fehler", "")
                time.sleep(1.0)
    elif action == "toggle_encoder_dir":
        state.encoder_reversed = not state.encoder_reversed
        _save_settings()
        display.show_message("Enc. Richtung", "Invertiert" if state.encoder_reversed else "Normal")
        time.sleep(0.8)
    elif action == "encoder_speed_slow":
        state.encoder_threshold = 4
        _save_settings()
        display.show_message("Enc. Speed", "Langsam")
        time.sleep(0.8)
    elif action == "encoder_speed_normal":
        state.encoder_threshold = 2
        _save_settings()
        display.show_message("Enc. Speed", "Normal")
        time.sleep(0.8)
    elif action == "encoder_speed_fast":
        state.encoder_threshold = 1
        _save_settings()
        display.show_message("Enc. Speed", "Schnell")
        time.sleep(0.8)
    elif action == "hold_time_05":
        state.button_assign_hold_time = 0.5
        _save_settings()
        display.show_message("Hold-Zeit", "0.5 Sek")
        time.sleep(0.8)
    elif action == "hold_time_10":
        state.button_assign_hold_time = 1.0
        _save_settings()
        display.show_message("Hold-Zeit", "1.0 Sek")
        time.sleep(0.8)
    elif action == "hold_time_20":
        state.button_assign_hold_time = 2.0
        _save_settings()
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
    elif action == "idle_mode_dim":
        state.idle_mode = "dim"
        _save_settings()
        display.show_message("Idle Modus", "Nur Dimmen")
        time.sleep(0.8)
    elif action == "idle_mode_screensaver":
        state.idle_mode = "screensaver"
        _save_settings()
        display.show_message("Idle Modus", "Screensaver")
        time.sleep(0.8)
    elif action.startswith("dim_brightness_"):
        try:
            level = int(action.split("_")[2])
            state.dim_brightness = max(10, min(50, level))
            _save_settings()
            display.show_message("Dimm-Hell.", str(state.dim_brightness) + "%")
            time.sleep(0.8)
        except (ValueError, IndexError):
            pass
    elif action == "ss_timeout_15":
        state.screensaver_timeout = 15
        _save_settings()
        display.show_message("Bildschirm", "15 Sek")
        time.sleep(0.8)
    elif action == "ss_timeout_30":
        state.screensaver_timeout = 30
        _save_settings()
        display.show_message("Bildschirm", "30 Sek")
        time.sleep(0.8)
    elif action == "ss_timeout_60":
        state.screensaver_timeout = 60
        _save_settings()
        display.show_message("Bildschirm", "1 Minute")
        time.sleep(0.8)
    elif action == "ss_timeout_300":
        state.screensaver_timeout = 300
        _save_settings()
        display.show_message("Bildschirm", "5 Minuten")
        time.sleep(0.8)
    elif action == "ss_timeout_600":
        state.screensaver_timeout = 600
        _save_settings()
        display.show_message("Bildschirm", "10 Minuten")
        time.sleep(0.8)
    elif action == "ss_timeout_900":
        state.screensaver_timeout = 900
        _save_settings()
        display.show_message("Bildschirm", "15 Minuten")
        time.sleep(0.8)
    elif action == "ss_timeout_1800":
        state.screensaver_timeout = 1800
        _save_settings()
        display.show_message("Bildschirm", "30 Minuten")
        time.sleep(0.8)
    elif action == "ss_timeout_off":
        state.screensaver_timeout = 9999
        _save_settings()
        display.show_message("Bildschirm", "Aus")
        time.sleep(0.8)
    elif action.startswith("brightness_"):
        try:
            level = int(action.split("_")[1])
            state.brightness = max(10, min(100, level))
            display.set_brightness(state.brightness)
            _save_settings()
            display.show_message("Helligkeit", str(state.brightness) + "%")
            time.sleep(0.6)
        except (ValueError, IndexError):
            pass
    elif action == "sd_status":
        if not sdcard.mounted:
            err = sdcard.last_error[:12] if sdcard.last_error else "Kein Modul?"
            display.show_message("SD fehlt", err)
            time.sleep(2.0)
        else:
            try:
                st = os.statvfs("/sd")
                total_mb = (st[2] * st[0]) // (1024 * 1024)
                free_mb  = (st[4] * st[0]) // (1024 * 1024)
                if total_mb >= 1024:
                    size_str = str(total_mb // 1024) + "." + str((total_mb % 1024) // 100) + "GB"
                else:
                    size_str = str(total_mb) + "MB"
                display.show_message("SD: " + size_str, str(free_mb) + "MB frei")
                time.sleep(1.5)
                try:
                    p_count = len([n for n in os.listdir("/sd/profiles") if n.lower().endswith(".bmp")])
                except OSError:
                    p_count = 0
                try:
                    ss_count = len([n for n in os.listdir("/sd/screensaver") if n.lower().endswith(".bmp")])
                except OSError:
                    ss_count = 0
                display.show_message("Bilder", "P:" + str(p_count) + " SS:" + str(ss_count))
                time.sleep(1.5)
            except OSError:
                display.show_message("SD Fehler", "")
                time.sleep(1.0)
    elif action == "sd_reload":
        display.show_message("SD", "Einh\xe4ngen...")
        display.reset_sd_caches()
        if sdcard.mounted:
            try:
                storage.umount("/sd")
            except Exception:
                pass
            sdcard.mounted = False
            time.sleep(1.0)
        if sdcard.mount():
            screensaver._scan_ss_images()
            n = len(screensaver._ss_images)
            display.show_message("SD OK", str(n) + " SS-Bilder")
            time.sleep(1.0)
        else:
            err = sdcard.last_error[:12] if sdcard.last_error else "Kein Modul?"
            display.show_message("SD fehlt", err)
            time.sleep(2.0)
    elif action.startswith("theme_"):
        display.set_theme(action[6:])
        _save_settings()
        display.show_message("Theme", menus.format_action_label(action))
        time.sleep(0.6)
    elif action == "toggle_inversion":
        display.set_inversion(not state.display_inverted)
        _save_settings()
        display.show_message("Invertierung", "Ein" if state.display_inverted else "Aus")
        time.sleep(0.6)
    elif action.startswith("rotation_"):
        try:
            rot = int(action.split("_")[1])
            if rot in (0, 90, 180, 270):
                state.display_rotation = rot
                state.needs_touch_calibration = True
                _save_settings()
                display.show_message("Ausrichtung", str(rot) + "\xb0 - Neustart")
                time.sleep(1.0)
                import supervisor as _sv
                _sv.reload()
        except (ValueError, IndexError):
            pass
        return
    elif action == "touch_calibrate":
        run_touch_calibration()
        return
    elif action == "display_test":
        state.display_test_mode = True
        display.start_display_test()
        return
    elif action == "menu_timeout_off":
        state.menu_timeout = 0
        _save_settings()
        display.show_message("Men\xfc-Timeout", "Aus")
        time.sleep(0.6)
    elif action.startswith("menu_timeout_"):
        try:
            state.menu_timeout = int(action.split("_")[2])
            _save_settings()
            display.show_message("Men\xfc-Timeout", action.split("_")[2] + " Sek")
            time.sleep(0.6)
        except (ValueError, IndexError):
            pass
    elif action in ("nav_back", "nav_up", "nav_down", "nav_select"):
        state.remote_nav = action[4:]  # strip "nav_" → "back"/"up"/"down"/"select"
        return
    time.sleep(0.3)
    display.draw_menu()


def handle_encoder_mode_step(step):
    if state.encoder_mode == "volume":
        send_media(ConsumerControlCode.VOLUME_INCREMENT if step > 0 else ConsumerControlCode.VOLUME_DECREMENT)
        state.local_volume = max(0, min(100, state.local_volume + step * 6))
        display.show_level_overlay("VOL", state.local_volume, 100)
    elif state.encoder_mode == "brightness":
        state.brightness = max(10, min(100, state.brightness + step * 10))
        display.set_brightness(state.brightness)
        display.show_level_overlay("HELL.", state.brightness, 100)
    elif state.encoder_mode == "mac_brightness":
        send_media(ConsumerControlCode.BRIGHTNESS_INCREMENT if step > 0 else ConsumerControlCode.BRIGHTNESS_DECREMENT)
        state.local_mac_brightness = max(0, min(100, state.local_mac_brightness + step * 6))
        display.show_level_overlay("MAC H.", state.local_mac_brightness, 100)
