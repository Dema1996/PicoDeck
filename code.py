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

encoder_clk = setup_button(board.GP12)
encoder_dt  = setup_button(board.GP13)
encoder_sw  = setup_button(board.GP14)

state.last_encoder_state = (encoder_clk.value << 1) | encoder_dt.value
state.last_encoder_button_state = encoder_sw.value


# =========================
# INPUT HANDLERS
# =========================

def is_pressed(button):
    return not button.value


def handle_encoder():
    now = time.monotonic()
    if now - state.last_encoder_time < 0.001:
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
    if state.encoder_steps >= state.encoder_threshold:
        state.last_activity = now
        state.last_encoder_activity = now
        step = -1 if state.encoder_reversed else 1
        if state.encoder_mode == "navigate":
            if state.current_menu != "dashboard":
                state.selected_index = (state.selected_index + step) % len(menus.get_menu_items(state.current_menu))
                display.draw_menu()
        else:
            actions.handle_encoder_mode_step(step)
        state.encoder_steps = 0
    elif state.encoder_steps <= -state.encoder_threshold:
        state.last_activity = now
        state.last_encoder_activity = now
        step = 1 if state.encoder_reversed else -1
        if state.encoder_mode == "navigate":
            if state.current_menu != "dashboard":
                state.selected_index = (state.selected_index + step) % len(menus.get_menu_items(state.current_menu))
                display.draw_menu()
        else:
            actions.handle_encoder_mode_step(step)
        state.encoder_steps = 0


def handle_encoder_button():
    now = time.monotonic()
    current_state = encoder_sw.value
    if not current_state and state.last_encoder_button_state:
        state.encoder_button_pressed_at = now
        state.last_encoder_activity = now
    elif current_state and not state.last_encoder_button_state:
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
    item = menus.get_menu_items(state.current_menu)[state.selected_index]

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


def handle_touch():
    pos = touch.read_position()
    if pos is None:
        return
    _x, y = pos
    # wait for release
    while touch.read_position() is not None:
        time.sleep(0.01)
    time.sleep(0.05)
    state.last_activity = time.monotonic()

    if state.current_menu == "dashboard":
        state.menu_stack.append("dashboard")
        state.current_menu = "main"
        state.selected_index = 0
        display.draw_menu()
        return

    if y < display._HDR:
        display.go_back()
        return
    idx = display.item_at_y(y)
    if idx is not None:
        state.selected_index = idx
        display.draw_menu()
        time.sleep(0.08)
        run_action()


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

boot_anim.play(2.5)
persistence.load_button_actions()
sdcard.mount()
display.show_message("Bluetooth", "Startet...")
ble_hid.setup()
ble_hid.start_advertising()
display.show_message("WiFi", "Startet...")
if wifi_server.start():
    state.wifi_active = True
    label = "STA" if wifi_server.mode == "sta" else wifi_server.SSID
    display.show_message(label, wifi_server.ip())
    time.sleep(1.5)
else:
    display.show_message("WiFi Fehler", "")
    time.sleep(1.0)
display.draw_menu()
state.last_activity = time.monotonic()


# =========================
# MAIN LOOP
# =========================

while True:
    any_fn  = (is_pressed(btn_f1) or is_pressed(btn_f2) or is_pressed(btn_f3)
               or is_pressed(btn_f4) or is_pressed(btn_f5))
    any_enc = not encoder_sw.value

    if any_fn or any_enc:
        state.last_activity = time.monotonic()

    # Fx buttons always execute their mapped action, even during screensaver
    handle_macro_button(btn_f1, "f1")
    handle_macro_button(btn_f2, "f2")
    handle_macro_button(btn_f3, "f3")
    handle_macro_button(btn_f4, "f4")
    handle_macro_button(btn_f5, "f5")

    if screensaver.active:
        if any_fn or any_enc or touch.read_position() is not None:
            screensaver.dismiss()
            while not encoder_sw.value:
                time.sleep(0.01)
        else:
            screensaver.update()
    else:
        handle_encoder()
        handle_encoder_button()
        handle_touch()
        display.update_menu_scroll()
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
    time.sleep(0.01)
