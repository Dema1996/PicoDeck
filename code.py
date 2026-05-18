import time
import board
import digitalio

import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

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

# =========================
# ROTARY ENCODER SETUP
# =========================

encoder_clk = setup_button(board.GP12)
encoder_dt = setup_button(board.GP13)
encoder_sw = setup_button(board.GP14)

last_encoder_state = (encoder_clk.value << 1) | encoder_dt.value
last_encoder_time = 0
encoder_steps = 0


# =========================
# MENU SETUP
# =========================

menu_items = [
    "Spotlight",
    "Mission Control",
    "Mute",
    "Screenshot",
    "Lock Mac"
]

selected_index = 0
last_selected_index = -1


# =========================
# DISPLAY FUNCTIONS
# =========================

def draw_menu():
    global last_selected_index

    if selected_index == last_selected_index:
        return

    last_selected_index = selected_index

    lcd.clear()

    first_line = "> " + menu_items[selected_index]

    if selected_index + 1 < len(menu_items):
        second_line = "  " + menu_items[selected_index + 1]
    else:
        second_line = ""

    lcd.message = first_line[:16] + "\n" + second_line[:16]


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


def run_action(index):
    action = menu_items[index]

    show_message("Aktion:", action)
    time.sleep(0.4)

    if action == "Spotlight":
        send_shortcut(Keycode.COMMAND, Keycode.SPACE)

    elif action == "Mission Control":
        send_shortcut(Keycode.CONTROL, Keycode.UP_ARROW)

    elif action == "Mute":
        send_shortcut(Keycode.COMMAND, Keycode.SHIFT, Keycode.M)

    elif action == "Screenshot":
        send_shortcut(Keycode.COMMAND, Keycode.SHIFT, Keycode.FIVE)

    elif action == "Lock Mac":
        send_shortcut(Keycode.CONTROL, Keycode.COMMAND, Keycode.Q)

    time.sleep(0.3)
    draw_menu()


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
        encoder_steps += 1
    elif transition in (0b0010, 0b1011, 0b1101, 0b0100):
        encoder_steps -= 1

    last_encoder_state = current_state
    last_encoder_time = now

    # viele Encoder liefern 4 Teilschritte pro Rastung
    if encoder_steps >= 2:
        selected_index += 1
        if selected_index >= len(menu_items):
            selected_index = 0

        encoder_steps = 0
        draw_menu()

    elif encoder_steps <= -2:
        selected_index -= 1
        if selected_index < 0:
            selected_index = len(menu_items) - 1

        encoder_steps = 0
        draw_menu()

def handle_encoder_button():

    if is_pressed(encoder_sw):

        run_action(selected_index)

        wait_until_released(encoder_sw)

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

    if is_pressed(btn_up):
        selected_index -= 1
        if selected_index < 0:
            selected_index = len(menu_items) - 1

        draw_menu()
        wait_until_released(btn_up)
        time.sleep(0.15)

    if is_pressed(btn_down):
        selected_index += 1
        if selected_index >= len(menu_items):
            selected_index = 0

        draw_menu()
        wait_until_released(btn_down)
        time.sleep(0.15)

    if is_pressed(btn_select):
        run_action(selected_index)
        wait_until_released(btn_select)
        time.sleep(0.15)

    if is_pressed(btn_back):
        show_message("Zurueck", "Hauptmenue")
        time.sleep(0.5)
        draw_menu()
        wait_until_released(btn_back)
        time.sleep(0.15)

    time.sleep(0.01)