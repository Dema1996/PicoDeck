button_order = ["back", "up", "down", "select", "favorite"]
button_hold_state = {name: {"pressed_at": None, "handled": False} for name in button_order}
button_pins = {"back": "GP8", "up": "GP9", "down": "GP10", "select": "GP11", "favorite": "GP16"}

profile_order = ["default", "coding", "media"]
profile_labels = {"default": "Default", "coding": "Coding", "media": "Media"}

default_button_profiles = {
    "default": {
        "back": "mission_control",
        "up": "play_pause",
        "down": "previous_track",
        "select": "volume_down",
        "favorite": "play_pause",
    },
    "coding": {
        "back": "command_palette",
        "up": "toggle_terminal",
        "down": "new_terminal",
        "select": "format_document",
        "favorite": "open_vscode",
    },
    "media": {
        "back": "mute",
        "up": "previous_track",
        "down": "next_track",
        "select": "play_pause",
        "favorite": "volume_up",
    },
}
button_profiles = {k: dict(v) for k, v in default_button_profiles.items()}
button_actions = dict(default_button_profiles["default"])
current_profile = "default"

encoder_mode = "navigate"
current_menu = "main"
menu_stack = []
current_button_target = "favorite"
selected_index = 0

button_assign_hold_time = 1.0
encoder_back_hold_time = 0.6
nvm_size = 512

last_encoder_time = 0.0
encoder_steps = 0
encoder_button_pressed_at = 0.0
# set by code.py after hardware init
last_encoder_state = 0
last_encoder_button_state = True
