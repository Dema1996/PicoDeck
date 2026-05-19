import time
import json
import board
import digitalio
import microcontroller

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from adafruit_hid.consumer_control import ConsumerControl
from adafruit_hid.consumer_control_code import ConsumerControlCode

import adafruit_character_lcd.character_lcd as characterlcd


# =========================
# LCD SETUP
# =========================

lcd_columns = 16
lcd_rows = 2

lcd_rs = digitalio.DigitalInOut(board.GP2)
lcd_en = digitalio.DigitalInOut(board.GP3)
lcd_d4 = digitalio.DigitalInOut(board.GP4)
lcd_d5 = digitalio.DigitalInOut(board.GP5)
lcd_d6 = digitalio.DigitalInOut(board.GP6)
lcd_d7 = digitalio.DigitalInOut(board.GP7)

lcd = characterlcd.Character_LCD_Mono(
    lcd_rs,
    lcd_en,
    lcd_d4,
    lcd_d5,
    lcd_d6,
    lcd_d7,
    lcd_columns,
    lcd_rows
)


# =========================
# HID SETUP
# =========================

keyboard = Keyboard(usb_hid.devices)
consumer_control = ConsumerControl(usb_hid.devices)


# =========================
# BUTTON SETUP
# =========================

def setup_button(pin):
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    return button


btn_back = setup_button(board.GP8)
btn_up = setup_button(board.GP9)
btn_down = setup_button(board.GP10)
btn_select = setup_button(board.GP11)
btn_favorite = setup_button(board.GP16)

# =========================
# ROTARY ENCODER SETUP
# =========================

encoder_clk = setup_button(board.GP12)
encoder_dt = setup_button(board.GP13)
encoder_sw = setup_button(board.GP14)

last_encoder_state = (encoder_clk.value << 1) | encoder_dt.value
last_encoder_time = 0
encoder_steps = 0
last_encoder_button_state = encoder_sw.value
encoder_button_pressed_at = 0
encoder_back_hold_time = 0.6
button_assign_hold_time = 1.0
nvm_size = 512
favorite_action = "play_pause"
default_button_actions = {
    "back": "mission_control",
    "up": "play_pause",
    "down": "previous_track",
    "select": "volume_down",
    "favorite": "play_pause"
}
button_actions = dict(default_button_actions)
button_pins = {
    "back": "GP8",
    "up": "GP9",
    "down": "GP10",
    "select": "GP11",
    "favorite": "GP16"
}
button_order = ["back", "up", "down", "select", "favorite"]


# =========================
# MENU SETUP
# =========================

menus = {

    "main": [
        {
            "label": "Media",
            "submenu": "media"
        },
        {
            "label": "System",
            "submenu": "system"
        },
        {
            "label": "Coding",
            "submenu": "coding"
        },
        {
            "label": "Buttons",
            "submenu": "buttons"
        }
    ],

    "media": [
        {
            "label": "Play/Pause",
            "action": "play_pause"
        },
        {
            "label": "Stop",
            "action": "stop"
        },
        {
            "label": "Mute",
            "action": "mute"
        },
        {
            "label": "Previous Trk",
            "action": "previous_track"
        },
        {
            "label": "Next Track",
            "action": "next_track"
        },
        {
            "label": "Volume Up",
            "action": "volume_up"
        },
        {
            "label": "Volume Down",
            "action": "volume_down"
        },
        {
            "label": "Zurueck",
            "action": "back"
        }
    ],

    "system": [
        {
            "label": "Spotlight",
            "action": "spotlight"
        },
        {
            "label": "App Switcher",
            "action": "app_switcher"
        },
        {
            "label": "Previous App",
            "action": "previous_app"
        },
        {
            "label": "Mission Control",
            "action": "mission_control"
        },
        {
            "label": "Lock Mac",
            "action": "lock_mac"
        },
        {
            "label": "Show Desktop",
            "action": "show_desktop"
        },
        {
            "label": "Zurueck",
            "action": "back"
        }
    ],

    "coding": [
        {
            "label": "VSCode",
            "action": "open_vscode"
        },
        {
            "label": "Screenshot",
            "action": "screenshot"
        },
        {
            "label": "Zurueck",
            "action": "back"
        }
    ]
}

current_menu = "main"
menu_stack = []
current_button_target = "favorite"

selected_index = 0
last_selected_index = -1


# =========================
# DISPLAY FUNCTIONS
# =========================

def draw_menu():
    lcd.clear()

    items = get_menu_items(current_menu)
    item = items[selected_index]["label"]

    header = current_menu.upper()
    counter = str(selected_index + 1) + "/" + str(len(items))

    line1 = header[:10] + " " + counter
    line2 = "> " + item

    lcd.message = line1[:16] + "\n" + line2[:16]


def show_message(line1, line2=""):
    lcd.clear()
    lcd.message = line1[:16] + "\n" + line2[:16]


def format_action_label(action):
    labels = {
        "mission_control": "MissionCtrl",
        "play_pause": "PlayPause",
        "stop": "Stop",
        "mute": "Mute",
        "previous_track": "Prev Track",
        "next_track": "Next Track",
        "volume_up": "Volume Up",
        "volume_down": "Volume Dn",
        "spotlight": "Spotlight",
        "app_switcher": "AppSwitch",
        "previous_app": "Prev App",
        "lock_mac": "Lock Mac",
        "show_desktop": "Desktop",
        "open_vscode": "VSCode",
        "screenshot": "Screenshot"
    }
    return labels.get(action, action[:10])


def get_buttons_menu():
    items = []

    for button_name in button_order:
        items.append({
            "label": button_pins[button_name],
            "action": "open_button_detail",
            "button_name": button_name
        })

    items.append({
        "label": "Reset Default",
        "action": "reset_button_defaults"
    })
    items.append({
        "label": "Zurueck",
        "action": "back"
    })

    return items


def get_menu_items(menu_name):
    if menu_name == "buttons":
        return get_buttons_menu()
    if menu_name == "button_detail":
        return get_button_detail_menu()

    return menus[menu_name]


def get_button_detail_menu():
    items = [{
        "label": "Akt: " + format_action_label(button_actions[current_button_target]),
        "action": "show_button_mapping",
        "button_name": current_button_target
    }]

    for action in sorted(get_valid_actions()):
        items.append({
            "label": format_action_label(action),
            "action": "assign_button_action",
            "button_name": current_button_target,
            "assign_action": action
        })

    items.append({
        "label": "Reset Taste",
        "action": "reset_single_button",
        "button_name": current_button_target
    })
    items.append({
        "label": "Zurueck",
        "action": "back"
    })

    return items


def get_valid_actions():
    actions = set()

    for items in menus.values():
        for item in items:
            action = item.get("action")
            if action and action != "back":
                actions.add(action)

    return actions


def load_button_actions():
    global favorite_action
    global button_actions

    valid_actions = get_valid_actions()
    button_actions = dict(default_button_actions)

    try:
        raw_config = bytes(microcontroller.nvm[:nvm_size])
        raw_config = raw_config.split(b"\x00", 1)[0]

        if not raw_config:
            favorite_action = button_actions["favorite"]
            return

        saved_actions = json.loads(raw_config.decode("utf-8"))

        for button_name in default_button_actions:
            action = saved_actions.get(button_name)
            if action in valid_actions:
                button_actions[button_name] = action

    except (OSError, ValueError):
        pass

    favorite_action = button_actions["favorite"]


def save_button_actions():
    serialized = json.dumps(button_actions).encode("utf-8")

    if len(serialized) >= nvm_size:
        raise ValueError("button mapping too large for NVM")

    padded = serialized + b"\x00" * (nvm_size - len(serialized))
    microcontroller.nvm[:nvm_size] = padded


def reset_button_actions():
    global favorite_action
    global button_actions

    button_actions = dict(default_button_actions)
    favorite_action = button_actions["favorite"]
    save_button_actions()


def save_action_to_button(button_name, action):
    global favorite_action

    button_actions[button_name] = action

    if button_name == "favorite":
        favorite_action = action

    save_button_actions()


# =========================
# ACTIONS
# =========================

def send_shortcut(*keys):
    keyboard.press(*keys)
    time.sleep(0.1)
    keyboard.release_all()


def send_media(consumer_code):
    consumer_control.send(consumer_code)


def go_back():
    global current_menu
    global selected_index
    global last_selected_index

    if len(menu_stack) > 0:
        current_menu = menu_stack.pop()
        selected_index = 0
        last_selected_index = -1
        draw_menu()


def execute_action(action):
    show_message("Action", action)
    time.sleep(0.2)

    if action == "spotlight":
        send_shortcut(
            Keycode.COMMAND, 
            Keycode.SPACE
        )

    elif action == "lock_mac":
        send_shortcut(
            Keycode.CONTROL,
            Keycode.COMMAND,
            Keycode.Q
        )

    elif action == "screenshot":
        send_shortcut(
            Keycode.COMMAND,
            Keycode.SHIFT,
            Keycode.FIVE
        )
    
    elif action == "mission_control":
        send_shortcut(
            Keycode.CONTROL, 
            Keycode.UP_ARROW
        )

    elif action == "show_desktop":
        send_shortcut(Keycode.F11)

    elif action == "play_pause":
        send_media(ConsumerControlCode.PLAY_PAUSE)

    elif action == "stop":
        send_media(ConsumerControlCode.STOP)

    elif action == "mute":
        send_media(ConsumerControlCode.MUTE)

    elif action == "next_track":
        send_media(ConsumerControlCode.SCAN_NEXT_TRACK)

    elif action == "previous_track":
        send_media(ConsumerControlCode.SCAN_PREVIOUS_TRACK)

    elif action == "volume_up":
        send_media(ConsumerControlCode.VOLUME_INCREMENT)

    elif action == "volume_down":
        send_media(ConsumerControlCode.VOLUME_DECREMENT)

    elif action == "open_vscode":
        send_shortcut(
            Keycode.COMMAND, 
            Keycode.SPACE
        )

    elif action == "app_switcher":
        send_shortcut(
            Keycode.COMMAND,
            Keycode.TAB
        )

    elif action == "previous_app":
        send_shortcut(
            Keycode.COMMAND,
            Keycode.SHIFT,
            Keycode.TAB
        )

    time.sleep(0.3)
    draw_menu()


def assign_current_action_to_button(button_name):
    item = get_menu_items(current_menu)[selected_index]

    if "action" not in item:
        show_message("Kein Mapping", "Nur Makros")
        time.sleep(0.8)
        draw_menu()
        return

    action = item["action"]

    if action == "back":
        show_message("Kein Mapping", "Nicht Zurueck")
        time.sleep(0.8)
        draw_menu()
        return

    try:
        save_action_to_button(button_name, action)
    except (OSError, ValueError):
        show_message("Speichern fehlg", "Mapping aktiv")
        time.sleep(0.8)
        draw_menu()
        return

    show_message("Gemappt auf", button_name.upper())
    time.sleep(0.8)
    draw_menu()


def show_button_mapping(button_name):
    show_message(
        button_pins[button_name],
        format_action_label(button_actions[button_name])
    )
    time.sleep(1.0)
    draw_menu()


def reset_single_button(button_name):
    try:
        save_action_to_button(button_name, default_button_actions[button_name])
    except (OSError, ValueError):
        show_message("Reset fehlg", button_pins[button_name])
        time.sleep(0.8)
        draw_menu()
        return

    show_message("Reset", button_pins[button_name])
    time.sleep(0.8)
    draw_menu()


def trigger_button_action(button_name):
    action = button_actions[button_name]

    if action == "back":
        go_back()
        return

    execute_action(action)


def run_action():

    global current_menu
    global selected_index
    global last_selected_index
    global current_button_target

    item = get_menu_items(current_menu)[selected_index]

    # Untermenue oeffnen
    if "submenu" in item:

        menu_stack.append(current_menu)

        current_menu = item["submenu"]

        selected_index = 0
        last_selected_index = -1

        draw_menu()

        return

    # Aktion ausfuehren
    if "action" in item:

        action = item["action"]

        if action == "open_button_detail":
            current_button_target = item["button_name"]
            menu_stack.append(current_menu)
            current_menu = "button_detail"
            selected_index = 0
            last_selected_index = -1
            draw_menu()
            return

        if action == "show_button_mapping":
            show_button_mapping(item["button_name"])
            return

        if action == "assign_button_action":
            try:
                save_action_to_button(
                    item["button_name"],
                    item["assign_action"]
                )
            except (OSError, ValueError):
                show_message("Speichern fehlg", "Bitte reboot")
                time.sleep(0.8)
                draw_menu()
                return

            show_message("Gemappt auf", button_pins[item["button_name"]])
            time.sleep(0.8)
            draw_menu()
            return

        if action == "reset_single_button":
            reset_single_button(item["button_name"])
            return

        if action == "reset_button_defaults":
            try:
                reset_button_actions()
            except (OSError, ValueError):
                show_message("Reset fehlg", "Bitte reboot")
                time.sleep(0.8)
                draw_menu()
                return

            show_message("Buttons reset", "Defaults aktiv")
            time.sleep(0.8)
            draw_menu()
            return

        # Zurueck ueber Encoder-Auswahl
        if action == "back":
            go_back()
            return

        execute_action(action)

# =========================
# BUTTON HELPERS
# =========================

def is_pressed(button):
    return not button.value


def wait_until_released(button):
    while is_pressed(button):
        time.sleep(0.01)

# =========================
# ROTARY ENCODER
# =========================

def handle_encoder():
    global last_encoder_state
    global last_encoder_time
    global encoder_steps
    global selected_index

    now = time.monotonic()

    # kleines Debounce-Fenster
    if now - last_encoder_time < 0.001:
        return

    current_state = (encoder_clk.value << 1) | encoder_dt.value

    if current_state == last_encoder_state:
        return

    transition = (last_encoder_state << 2) | current_state

    # gültige Rechts/Links-Schritte
    if transition in (0b0001, 0b0111, 0b1110, 0b1000):
        encoder_steps -= 1
    elif transition in (0b0010, 0b1011, 0b1101, 0b0100):
        encoder_steps += 1

    last_encoder_state = current_state
    last_encoder_time = now

    # viele Encoder liefern 4 Teilschritte pro Rastung
    if encoder_steps >= 2:
        selected_index += 1
        if selected_index >= len(get_menu_items(current_menu)):
            selected_index = 0

        encoder_steps = 0
        draw_menu()

    elif encoder_steps <= -2:
        selected_index -= 1
        if selected_index < 0:
            selected_index = len(get_menu_items(current_menu)) - 1

        encoder_steps = 0
        draw_menu()

def handle_encoder_button():
    global last_encoder_button_state
    global encoder_button_pressed_at

    now = time.monotonic()
    current_state = encoder_sw.value

    if not current_state and last_encoder_button_state:
        encoder_button_pressed_at = now

    elif current_state and not last_encoder_button_state:
        press_duration = now - encoder_button_pressed_at

        if press_duration >= encoder_back_hold_time:
            go_back()
        else:
            run_action()

        time.sleep(0.15)

    last_encoder_button_state = current_state


def handle_macro_button(button, button_name):
    if not is_pressed(button):
        return

    pressed_at = time.monotonic()

    while is_pressed(button):
        if time.monotonic() - pressed_at >= button_assign_hold_time:
            assign_current_action_to_button(button_name)
            wait_until_released(button)
            time.sleep(0.15)
            return

        time.sleep(0.01)

    trigger_button_action(button_name)
    time.sleep(0.15)

# =========================
# STARTUP
# =========================

show_message("Macro Pad", "Startet...")
time.sleep(1)

load_button_actions()
draw_menu()


# =========================
# MAIN LOOP
# =========================

while True:
    handle_encoder()
    handle_encoder_button()

    handle_macro_button(btn_back, "back")
    handle_macro_button(btn_up, "up")
    handle_macro_button(btn_down, "down")
    handle_macro_button(btn_select, "select")
    handle_macro_button(btn_favorite, "favorite")

    time.sleep(0.01)
