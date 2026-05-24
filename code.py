import console_log
console_log.setup()

import json
import sys
import time
import board
import digitalio
import supervisor

import state
import menus
import display
import actions
import persistence
import touch
import sdcard
import wifi_server
import screensaver
import boot_anim
import ble_hid


# =========================
# HARDWARE SETUP
# =========================

def setup_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    return button


btn_f1 = setup_button(board.GP8)
btn_f2 = setup_button(board.GP9)
btn_f3 = setup_button(board.GP10)
btn_f4 = setup_button(board.GP11)
btn_f5 = setup_button(board.GP16)
btn_f6 = setup_button(board.GP19)

encoder_clk = setup_button(board.GP12)
encoder_dt  = setup_button(board.GP13)
encoder_sw  = setup_button(board.GP14)

state.last_encoder_state = (encoder_clk.value << 1) | encoder_dt.value
state.last_encoder_button_state = encoder_sw.value


def _menu_items():
    return menus.get_menu_items(state.current_menu)


def _normalize_selected_index():
    items = _menu_items()
    if not items:
        state.selected_index = 0
        return items
    if state.selected_index < 0:
        state.selected_index = 0
    elif state.selected_index >= len(items):
        state.selected_index = len(items) - 1
    return items


def _record_exception(context, err):
    msg = "{}: {}".format(context, str(err))[:120]
    state.last_exception = msg
    if hasattr(console_log, "add_exception"):
        console_log.add_exception(context, err)
    else:
        console_log.log("ERR " + msg)


# =========================
# INPUT HANDLERS
# =========================

def is_pressed(button):
    return not button.value


def handle_encoder():
    now = time.monotonic()
    if now - state.last_encoder_time < 0.0005:
        return
    current_state = (encoder_clk.value << 1) | encoder_dt.value
    if current_state == state.last_encoder_state:
        return
    transition = (state.last_encoder_state << 2) | current_state
    if transition in (0b0001, 0b0111, 0b1110, 0b1000):
        state.encoder_steps -= 1
    elif transition in (0b0010, 0b1011, 0b1101, 0b0100):
        state.encoder_steps += 1
    state.last_encoder_state = current_state
    state.last_encoder_time = now
    while state.encoder_steps >= state.encoder_threshold:
        state.last_activity = now
        state.last_encoder_activity = now
        step = -1 if state.encoder_reversed else 1
        if state.encoder_mode == "navigate":
            if state.current_menu != "dashboard":
                state.selected_index = (state.selected_index + step) % len(menus.get_menu_items(state.current_menu))
                display.draw_menu()
        else:
            actions.handle_encoder_mode_step(step)
        state.encoder_steps -= state.encoder_threshold
    while state.encoder_steps <= -state.encoder_threshold:
        state.last_activity = now
        state.last_encoder_activity = now
        step = 1 if state.encoder_reversed else -1
        if state.encoder_mode == "navigate":
            if state.current_menu != "dashboard":
                state.selected_index = (state.selected_index + step) % len(menus.get_menu_items(state.current_menu))
                display.draw_menu()
        else:
            actions.handle_encoder_mode_step(step)
        state.encoder_steps += state.encoder_threshold


def handle_encoder_button():
    now = time.monotonic()
    current_state = encoder_sw.value
    if not current_state and state.last_encoder_button_state:
        state.encoder_button_pressed_at = now
        state.last_encoder_activity = now
    elif current_state and not state.last_encoder_button_state:
        if state.ignore_next_encoder_release:
            state.ignore_next_encoder_release = False
            state.last_encoder_button_state = current_state
            return
        press_duration = now - state.encoder_button_pressed_at
        state.last_encoder_activity = now
        if press_duration >= state.encoder_back_hold_time:
            if state.encoder_mode == "navigate":
                display.go_back()
            else:
                state.encoder_mode = "navigate"
                display.draw_menu()
        else:
            if state.encoder_mode != "navigate":
                state.encoder_mode = "navigate"
                display.draw_menu()
            elif state.current_menu == "dashboard":
                state.menu_stack.append("dashboard")
                state.current_menu = "main"
                state.selected_index = 0
                display.draw_menu()
            else:
                run_action()
        time.sleep(0.15)
    state.last_encoder_button_state = current_state


def run_action():
    items = _normalize_selected_index()
    if not items:
        return
    item = items[state.selected_index]

    if "submenu" in item:
        state.menu_stack.append(state.current_menu)
        state.current_menu = item["submenu"]
        state.selected_index = 0
        display.draw_menu()
        return

    if "action" not in item:
        return

    action = item["action"]

    if action == "open_button_detail":
        state.current_button_target = item["button_name"]
        state.menu_stack.append(state.current_menu)
        state.current_menu = "button_detail"
        state.selected_index = 0
        display.draw_menu()
        return

    if action == "switch_profile":
        try:
            persistence.switch_profile(item["profile_name"])
        except (OSError, ValueError):
            display.show_message("Profil fehlg", "Bitte reboot")
            time.sleep(0.8)
            display.draw_menu()
            return
        display.show_message("Profil aktiv", state.profile_labels[item["profile_name"]])
        time.sleep(0.8)
        display.draw_menu()
        return

    if action == "show_button_mapping":
        persistence.show_button_mapping(item["button_name"])
        return

    if action == "assign_button_action":
        try:
            persistence.save_action_to_button(item["button_name"], item["assign_action"])
        except (OSError, ValueError):
            display.show_message("Speichern fehlg", "Bitte reboot")
            time.sleep(0.8)
            display.draw_menu()
            return
        display.show_message("Gemappt auf", state.button_pins[item["button_name"]])
        time.sleep(0.8)
        display.draw_menu()
        return

    if action == "open_profile_detail":
        state.current_profile_target = item["profile_name"]
        state.menu_stack.append(state.current_menu)
        state.current_menu = "profile_detail"
        state.selected_index = 0
        display.draw_menu()
        return

    if action == "delete_profile":
        name = item["profile_name"]
        label = state.profile_labels.get(name, name)
        try:
            persistence.delete_profile(name)
        except (OSError, ValueError):
            display.show_message("Fehler", "Nicht gel\xf6scht")
            time.sleep(0.8)
            display.draw_menu()
            return
        display.show_message("Gel\xf6scht", label)
        time.sleep(0.8)
        state.menu_stack.clear()
        state.current_menu = "profiles"
        state.selected_index = 0
        display.draw_menu()
        return

    if action == "create_profile":
        name = persistence.create_profile()
        if name:
            display.show_message("Erstellt", state.profile_labels[name])
        else:
            display.show_message("Max. Profile", "Limit erreicht")
        time.sleep(0.8)
        display.draw_menu()
        return

    if action == "reset_single_button":
        persistence.reset_single_button(item["button_name"])
        return

    if action == "reset_button_defaults":
        try:
            persistence.reset_button_actions()
        except (OSError, ValueError):
            display.show_message("Reset fehlg", "Bitte reboot")
            time.sleep(0.8)
            display.draw_menu()
            return
        display.show_message("Buttons reset", "Defaults aktiv")
        time.sleep(0.8)
        display.draw_menu()
        return

    if action == "back":
        display.go_back()
        return

    actions.execute_action(action)


def _status_payload():
    items = _normalize_selected_index()
    total = len(items)
    start = 0
    if state.current_menu != "dashboard" and total > 7:
        start = max(0, min(state.selected_index - 3, total - 7))
    visible = []
    for idx in range(start, min(total, start + 7)):
        visible.append({
            "index": idx,
            "label": items[idx]["label"],
            "selected": idx == state.selected_index,
        })
    last_exception_log = console_log.get_last_exception() if hasattr(console_log, "get_last_exception") else []
    return {
        "current_menu": state.current_menu,
        "menu_stack": list(state.menu_stack),
        "selected_index": state.selected_index,
        "profile": state.current_profile,
        "profile_label": state.profile_labels[state.current_profile],
        "profiles": list(state.profile_order),
        "profile_labels": dict(state.profile_labels),
        "button_actions": dict(state.button_actions),
        "button_order": list(state.button_order),
        "brightness": state.brightness,
        "dim_brightness": state.dim_brightness,
        "idle_mode": state.idle_mode,
        "screensaver_timeout": state.screensaver_timeout,
        "menu_timeout": state.menu_timeout,
        "theme": state.theme,
        "encoder_mode": state.encoder_mode,
        "encoder_reversed": state.encoder_reversed,
        "encoder_threshold": state.encoder_threshold,
        "button_assign_hold_time": state.button_assign_hold_time,
        "display_inverted": state.display_inverted,
        "display_rotation": state.display_rotation,
        "track_title": state.track_title,
        "local_volume": state.local_volume,
        "local_mac_brightness": state.local_mac_brightness,
        "wifi_active": wifi_server.active,
        "wifi_mode": wifi_server.mode,
        "wifi_ip": wifi_server.ip(),
        "wifi_ssid": state.wifi_ssid,
        "time_sync_source": state.time_sync_source,
        "ble_available": ble_hid.available(),
        "ble_active": ble_hid.active,
        "ble_connected": ble_hid.connected,
        "ble_status": ble_hid.status_str(),
        "last_exception": state.last_exception,
        "last_exception_log": last_exception_log,
        "screensaver_active": screensaver.active,
        "screensaver_dimmed": screensaver.dimmed,
        "menu_items": visible,
        "actions": sorted(menus.get_valid_actions()),
    }


def _serial_send(msg_type, **payload):
    payload["type"] = msg_type
    print(json.dumps(payload))


def _set_rtc_from_unix(unix_time):
    import rtc
    t = time.localtime(int(unix_time))
    rtc.RTC().datetime = t
    state.ntp_synced = True
    state.time_sync_source = "host"


def _set_rtc_from_fields(data):
    import rtc
    year = int(data.get("year"))
    month = int(data.get("month"))
    day = int(data.get("day"))
    hour = int(data.get("hour"))
    minute = int(data.get("minute"))
    second = int(data.get("second", 0))
    weekday = int(data.get("weekday", 0))
    rtc.RTC().datetime = time.struct_time((year, month, day, hour, minute, second, weekday, -1, -1))
    state.ntp_synced = True
    state.time_sync_source = "host"


def _apply_runtime_settings():
    if screensaver.active or screensaver.dimmed:
        screensaver.dismiss()
    display.set_theme(state.theme)
    display.set_brightness(state.brightness)
    display.set_inversion(state.display_inverted)
    display.draw_menu()


def _set_runtime_value(key, value):
    if key == "brightness":
        state.brightness = max(10, min(100, int(value)))
    elif key == "dim_brightness":
        state.dim_brightness = max(10, min(50, int(value)))
    elif key == "screensaver_timeout":
        state.screensaver_timeout = int(value)
    elif key == "menu_timeout":
        state.menu_timeout = max(0, int(value))
    elif key == "theme":
        if value not in ("dark", "dracula", "matrix", "amber"):
            raise ValueError("invalid theme")
        state.theme = value
    elif key == "idle_mode":
        if value not in ("dim", "screensaver"):
            raise ValueError("invalid idle_mode")
        state.idle_mode = value
    elif key == "encoder_mode":
        if value not in ("navigate", "volume", "brightness", "mac_brightness"):
            raise ValueError("invalid encoder_mode")
        state.encoder_mode = value
    elif key == "encoder_reversed":
        state.encoder_reversed = bool(value)
    elif key == "encoder_threshold":
        if int(value) not in (1, 2, 4):
            raise ValueError("invalid encoder_threshold")
        state.encoder_threshold = int(value)
    elif key == "button_assign_hold_time":
        if float(value) not in (0.5, 1.0, 2.0):
            raise ValueError("invalid button_assign_hold_time")
        state.button_assign_hold_time = float(value)
    elif key == "display_inverted":
        state.display_inverted = bool(value)
    elif key == "display_rotation":
        if int(value) not in (0, 90, 180, 270):
            raise ValueError("invalid display_rotation")
        rotation = int(value)
        if rotation != state.display_rotation:
            state.display_rotation = rotation
            state.needs_touch_calibration = True
    else:
        raise ValueError("unknown setting")


def _handle_remote_command(nav):
    state.last_activity = time.monotonic()
    if nav == "up":
        if state.current_menu != "dashboard":
            items = _normalize_selected_index()
            if not items:
                return
            state.selected_index = (state.selected_index - 1) % len(items)
            display.draw_menu()
    elif nav == "down":
        if state.current_menu != "dashboard":
            items = _normalize_selected_index()
            if not items:
                return
            state.selected_index = (state.selected_index + 1) % len(items)
            display.draw_menu()
    elif nav == "back":
        display.go_back()
    elif nav == "select":
        run_action()
    elif nav in state.button_order:
        persistence.trigger_button_action(nav)
    else:
        actions.execute_action(nav)


def _handle_serial_command(line):
    line = line.strip()
    if not line:
        return
    try:
        data = json.loads(line)
    except ValueError:
        _serial_send("error", ok=False, error="invalid_json")
        return

    cmd = data.get("cmd")
    if cmd == "ping":
        _serial_send("pong", ok=True)
        return
    if cmd == "reboot":
        _serial_send("ack", ok=True, cmd=cmd)
        supervisor.reload()
        return
    if cmd == "status":
        _serial_send("status", ok=True, status=_status_payload())
        return
    if cmd == "list_actions":
        _serial_send("actions", ok=True, actions=sorted(menus.get_valid_actions()))
        return
    if cmd == "action":
        value = data.get("value")
        if not value:
            _serial_send("error", ok=False, error="missing_action")
            return
        _handle_remote_command(value)
        _serial_send("ack", ok=True, cmd=cmd, value=value, status=_status_payload())
        return
    if cmd == "switch_profile":
        profile_name = data.get("profile")
        if profile_name not in state.profile_order:
            _serial_send("error", ok=False, error="unknown_profile")
            return
        try:
            persistence.switch_profile(profile_name)
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        display.draw_menu()
        _serial_send("ack", ok=True, cmd=cmd, profile=profile_name, status=_status_payload())
        return
    if cmd == "set_button":
        button_name = data.get("button")
        action_name = data.get("action")
        if button_name not in state.button_order:
            _serial_send("error", ok=False, error="unknown_button")
            return
        if action_name not in menus.get_valid_actions():
            _serial_send("error", ok=False, error="unknown_action")
            return
        try:
            persistence.save_action_to_button(button_name, action_name)
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        display.draw_menu()
        _serial_send("ack", ok=True, cmd=cmd, button=button_name, action=action_name, status=_status_payload())
        return
    if cmd == "set_buttons":
        mapping = data.get("mapping")
        if not isinstance(mapping, dict) or not mapping:
            _serial_send("error", ok=False, error="missing_mapping")
            return
        cleaned = {}
        valid_actions = menus.get_valid_actions()
        for button_name, action_name in mapping.items():
            if button_name not in state.button_order:
                _serial_send("error", ok=False, error="unknown_button")
                return
            if action_name not in valid_actions:
                _serial_send("error", ok=False, error="unknown_action")
                return
            cleaned[button_name] = action_name
        try:
            persistence.save_actions_to_buttons(cleaned)
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        display.draw_menu()
        _serial_send("ack", ok=True, cmd=cmd, status=_status_payload())
        return
    if cmd == "create_profile":
        try:
            profile_name = persistence.create_profile(data.get("label"))
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        if not profile_name:
            _serial_send("error", ok=False, error="profile_limit")
            return
        display.draw_menu()
        _serial_send("ack", ok=True, cmd=cmd, profile=profile_name, status=_status_payload())
        return
    if cmd == "delete_profile":
        profile_name = data.get("profile")
        if profile_name not in state.profile_order:
            _serial_send("error", ok=False, error="unknown_profile")
            return
        try:
            persistence.delete_profile(profile_name)
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        display.draw_menu()
        _serial_send("ack", ok=True, cmd=cmd, profile=profile_name, status=_status_payload())
        return
    if cmd == "save_wifi":
        ssid = data.get("ssid", "")
        password = data.get("password", "")
        if not ssid:
            _serial_send("error", ok=False, error="missing_ssid")
            return
        try:
            persistence.save_wifi_config(ssid, password)
        except (OSError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        _serial_send("ack", ok=True, cmd=cmd, status=_status_payload())
        return
    if cmd == "host_state":
        try:
            if "title" in data:
                state.track_title = str(data.get("title") or "")[:120]
            if "volume" in data:
                state.local_volume = max(0, min(100, int(data.get("volume"))))
            if "mac_brightness" in data:
                state.local_mac_brightness = max(0, min(100, int(data.get("mac_brightness"))))
            has_local_time = ("year" in data and "month" in data and "day" in data
                              and "hour" in data and "minute" in data)
            if has_local_time:
                _set_rtc_from_fields(data)
            elif "unix_time" in data:
                _set_rtc_from_unix(data.get("unix_time"))
        except (TypeError, ValueError) as e:
            _serial_send("error", ok=False, error=str(e))
            return
        if screensaver.active:
            screensaver.draw()
        elif state.current_menu == "dashboard":
            display.draw_menu()
        elif state.current_menu != "dashboard" and state.ntp_synced:
            display.draw_menu()
        if screensaver.active:
            screensaver.update()
        _serial_send("ack", ok=True, cmd=cmd, status=_status_payload())
        return
    if cmd == "set":
        changes = data.get("values")
        if not isinstance(changes, dict) or not changes:
            _serial_send("error", ok=False, error="missing_values")
            return
        snapshot = persistence.snapshot_state()
        try:
            for key, value in changes.items():
                _set_runtime_value(key, value)
            persistence.save_button_actions()
        except (OSError, ValueError, TypeError) as e:
            persistence.restore_state(snapshot)
            _apply_runtime_settings()
            _serial_send("error", ok=False, error=str(e))
            return
        _apply_runtime_settings()
        _serial_send("ack", ok=True, cmd=cmd, status=_status_payload())
        return
    _serial_send("error", ok=False, error="unknown_command")


def poll_serial():
    while supervisor.runtime.serial_bytes_available:
        try:
            line = sys.stdin.readline()
        except Exception as e:
            _serial_send("error", ok=False, error=str(e))
            return
        if not line:
            return
        _handle_serial_command(line)


def handle_touch():
    pos = touch.read_position()
    if pos is None:
        return
    _x, y_start = pos
    y_end = y_start
    max_dy = 0
    while True:
        p = touch.read_position()
        if p is None:
            break
        y_end = p[1]
        if abs(y_end - y_start) > abs(max_dy):
            max_dy = y_end - y_start
        time.sleep(0.01)
    time.sleep(0.05)
    state.last_activity = time.monotonic()

    if state.current_menu == "dashboard":
        state.menu_stack.append("dashboard")
        state.current_menu = "main"
        state.selected_index = 0
        display.draw_menu()
        return

    dy = max_dy if abs(max_dy) > abs(y_end - y_start) else y_end - y_start
    if abs(dy) >= display._IH // 2:
        items = _normalize_selected_index()
        total = len(items)
        if not total:
            return
        if dy < 0:
            state.selected_index = min(state.selected_index + 1, total - 1)
        else:
            state.selected_index = max(state.selected_index - 1, 0)
        display.draw_menu()
        return

    if y_start < display._HDR:
        display.go_back()
        return
    idx = display.item_at_y(y_start)
    if idx is not None:
        state.selected_index = idx
        display.draw_menu()
        time.sleep(0.08)
        run_action()


def handle_display_test():
    sample = touch.read_position_with_raw()
    pos = None
    raw = None
    if sample is not None:
        pos, raw = sample
        state.last_activity = time.monotonic()
        if pos[1] < display._HDR:
            state.display_test_mode = False
            display.draw_menu()
            time.sleep(0.15)
            return
    display.update_display_test(pos, raw)


def handle_macro_button(button, button_name):
    s = state.button_hold_state[button_name]
    pressed = is_pressed(button)
    if pressed and s["pressed_at"] is None:
        s["pressed_at"] = time.monotonic()
        s["handled"] = False
    elif pressed and not s["handled"]:
        if time.monotonic() - s["pressed_at"] >= state.button_assign_hold_time:
            persistence.assign_current_action_to_button(button_name)
            s["handled"] = True
    elif not pressed and s["pressed_at"] is not None:
        if not s["handled"]:
            persistence.trigger_button_action(button_name)
            time.sleep(0.15)
        s["pressed_at"] = None
        s["handled"] = False


# =========================
# STARTUP
# =========================

_anim = boot_anim.BootAnim()

_anim.set_status("SD Karte laden...")
sdcard.mount()
_anim.tick(4)
_anim.set_status("SD: OK" if sdcard.mounted else "SD: Fehler")
_anim.tick(6)

persistence.load_button_actions()
_anim.tick(3)

if state.touch_cal:
    touch.apply_calibration(*state.touch_cal)
if state.needs_touch_calibration:
    state.needs_touch_calibration = False
    persistence.save_button_actions()
    _anim.set_status("Touch kalibrieren")
    _anim.tick(4)
    actions.run_touch_calibration()

if state.theme != "dark":
    display.set_theme(state.theme)
display.set_brightness(state.brightness)
if state.display_inverted:
    display.set_inversion(True)
_anim.tick(2)

_anim.set_status("Bluetooth...")
ble_hid.setup()
ble_hid.start_advertising()
_anim.set_status("BLE: " + ble_hid.status_str()[:12])
_anim.tick(4)

_anim.set_status("WiFi...")
if wifi_server.start():
    state.wifi_active = True
    _anim.set_status(wifi_server.ip())
    _anim.tick(10)
else:
    state.wifi_active = False
    _anim.set_status("WiFi: Fehler")
    _anim.tick(8)

display.draw_menu()
state.last_activity = time.monotonic()


# =========================
# MAIN LOOP
# =========================

while True:
    try:
        any_fn  = (is_pressed(btn_f1) or is_pressed(btn_f2) or is_pressed(btn_f3)
                   or is_pressed(btn_f4) or is_pressed(btn_f5) or is_pressed(btn_f6))
        any_enc = not encoder_sw.value

        if any_fn or any_enc:
            state.last_activity = time.monotonic()

        # Fx buttons always execute their mapped action, even during screensaver
        handle_macro_button(btn_f1, "f1")
        handle_macro_button(btn_f2, "f2")
        handle_macro_button(btn_f3, "f3")
        handle_macro_button(btn_f4, "f4")
        handle_macro_button(btn_f5, "f5")
        handle_macro_button(btn_f6, "f6")
        poll_serial()

        if state.display_test_mode:
            if any_enc:
                state.ignore_next_encoder_release = True
                state.display_test_mode = False
                display.draw_menu()
                time.sleep(0.15)
                continue
            handle_display_test()
            ble_hid.poll()
            wifi_server.poll()
            time.sleep(0.01)
            continue

        if screensaver.active or screensaver.dimmed:
            if any_fn or any_enc or touch.read_position() is not None:
                if any_enc:
                    state.ignore_next_encoder_release = True
                screensaver.dismiss()
            else:
                if screensaver.active:
                    screensaver.update()
        else:
            handle_encoder()
            handle_encoder_button()
            handle_touch()
            if state.remote_nav is not None:
                nav = state.remote_nav
                state.remote_nav = None
                _handle_remote_command(nav)
            display.update_menu_scroll()
            display.update_overlay()
            if (state.encoder_mode != "navigate"
                    and time.monotonic() - state.last_encoder_activity > 15.0):
                state.encoder_mode = "navigate"
                state.last_encoder_activity = time.monotonic()
                display.draw_menu()
            if (state.menu_timeout > 0
                    and state.current_menu != "dashboard"
                    and time.monotonic() - state.last_activity > state.menu_timeout):
                state.menu_stack.clear()
                state.current_menu = "dashboard"
                state.selected_index = 0
                display.draw_menu()
            if time.monotonic() - state.last_activity > state.screensaver_timeout:
                screensaver.draw()

        ble_hid.poll()
        wifi_server.poll()
        if wifi_server.needs_reboot:
            display.show_message("WiFi", "Neustart...")
            time.sleep(1.5)
            supervisor.reload()
        if wifi_server.needs_redraw:
            display.draw_menu()
            wifi_server.needs_redraw = False
    except Exception as e:
        _record_exception("loop", e)
        try:
            display.show_message("Fehler", str(e)[:18])
        except Exception:
            pass
        time.sleep(0.5)
    time.sleep(0.01)
