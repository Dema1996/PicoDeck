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
}

MEDIA_ACTIONS = {
    "play_pause":     ConsumerControlCode.PLAY_PAUSE,
    "stop":           ConsumerControlCode.STOP,
    "mute":           ConsumerControlCode.MUTE,
    "next_track":     ConsumerControlCode.SCAN_NEXT_TRACK,
    "previous_track": ConsumerControlCode.SCAN_PREVIOUS_TRACK,
    "volume_up":      ConsumerControlCode.VOLUME_INCREMENT,
    "volume_down":    ConsumerControlCode.VOLUME_DECREMENT,
}

ENCODER_MODE_ACTIONS = {
    "encoder_navigate":   "navigate",
    "encoder_volume":     "volume",
    "encoder_brightness": "brightness",
}


def send_shortcut(*keys):
    keyboard.press(*keys)
    time.sleep(0.1)
    keyboard.release_all()


def send_media(consumer_code):
    consumer_control.send(consumer_code)


def execute_action(action):
    display.show_message("Action", menus.format_action_label(action))
    time.sleep(0.2)
    if action in SHORTCUT_ACTIONS:
        send_shortcut(*SHORTCUT_ACTIONS[action])
    elif action == "open_vscode":
        send_shortcut(Keycode.COMMAND, Keycode.SPACE)
        time.sleep(0.5)
        keyboard_layout.write("code\n")
    elif action in MEDIA_ACTIONS:
        send_media(MEDIA_ACTIONS[action])
    elif action in ENCODER_MODE_ACTIONS:
        state.encoder_mode = ENCODER_MODE_ACTIONS[action]
    time.sleep(0.3)
    display.draw_menu()


def handle_encoder_mode_step(step):
    if state.encoder_mode == "volume":
        send_media(ConsumerControlCode.VOLUME_INCREMENT if step > 0 else ConsumerControlCode.VOLUME_DECREMENT)
    elif state.encoder_mode == "brightness":
        send_media(ConsumerControlCode.BRIGHTNESS_INCREMENT if step > 0 else ConsumerControlCode.BRIGHTNESS_DECREMENT)
