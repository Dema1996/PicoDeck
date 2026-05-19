import time
import board
import digitalio

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
encoder_assign_hold_time = 1.2
favorite_action = "play_pause"
pending_button_assignment = None
button_actions = {
    "back": "mission_control",
    "up": "play_pause",
    "down": "previous_track",
    "select": "volume_down",
    "favorite": "play_pause"
}


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
        }
    ],

    "media": [
        {
            "label": "Play/Pause",
            "action": "play_pause"
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
            "label": "Zurueck",
            "action": "back"
        }
    ]
}

current_menu = "main"
menu_stack = []

selected_index = 0
last_selected_index = -1


# =========================
# DISPLAY FUNCTIONS
# =========================

def draw_menu():
    lcd.clear()

    items = menus[current_menu]
    item = items[selected_index]["label"]

    header = current_menu.upper()
    counter = str(selected_index + 1) + "/" + str(len(items))

    line1 = header[:10] + " " + counter
    line2 = "> " + item

    lcd.message = line1[:16] + "\n" + line2[:16]


def show_message(line1, line2=""):
    lcd.clear()
    lcd.message = line1[:16] + "\n" + line2[:16]


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

    time.sleep(0.3)
    draw_menu()


def start_button_assignment():
    global pending_button_assignment

    item = menus[current_menu][selected_index]

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

    pending_button_assignment = action
    show_message("Button waehlen", item["label"])
    time.sleep(0.2)


def assign_action_to_button(button_name):
    global favorite_action
    global pending_button_assignment

    action = pending_button_assignment
    button_actions[button_name] = action

    if button_name == "favorite":
        favorite_action = action

    pending_button_assignment = None
    show_message("Gemappt auf", button_name.upper())
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

    item = menus[current_menu][selected_index]

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
        if selected_index >= len(menus[current_menu]):
            selected_index = 0

        encoder_steps = 0
        draw_menu()

    elif encoder_steps <= -2:
        selected_index -= 1
        if selected_index < 0:
            selected_index = len(menus[current_menu]) - 1

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

        if press_duration >= encoder_assign_hold_time:
            start_button_assignment()
        elif press_duration >= encoder_back_hold_time:
            go_back()
        else:
            run_action()

        time.sleep(0.15)

    last_encoder_button_state = current_state


def handle_macro_button(button, button_name):
    if not is_pressed(button):
        return

    if pending_button_assignment is not None:
        assign_action_to_button(button_name)
    else:
        trigger_button_action(button_name)

    wait_until_released(button)
    time.sleep(0.15)

# =========================
# STARTUP
# =========================

show_message("Macro Pad", "Startet...")
time.sleep(1)

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
