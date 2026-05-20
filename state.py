button_order = ["f1", "f2", "f3", "f4", "f5"]
button_hold_state = {name: {"pressed_at": None, "handled": False} for name in button_order}
button_pins = {"f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5"}

profile_order = ["default", "coding", "media"]
profile_labels = {"default": "Default", "coding": "Coding", "media": "Media"}

default_button_profiles = {
    "default": {
        "f1": "mission_control",
        "f2": "play_pause",
        "f3": "previous_track",
        "f4": "volume_down",
        "f5": "play_pause",
    },
    "coding": {
        "f1": "command_palette",
        "f2": "toggle_terminal",
        "f3": "new_terminal",
        "f4": "format_document",
        "f5": "open_vscode",
    },
    "media": {
        "f1": "mute",
        "f2": "previous_track",
        "f3": "next_track",
        "f4": "play_pause",
        "f5": "volume_up",
    },
}
button_profiles = {k: dict(v) for k, v in default_button_profiles.items()}
button_actions = dict(default_button_profiles["default"])
current_profile = "default"

encoder_mode = "navigate"
encoder_reversed = False
wifi_active = False
wifi_ssid = ""
wifi_password = ""
encoder_threshold = 2   # half-steps per detent action (1=fast, 2=normal, 4=slow)
brightness = 100        # display backlight 10-100 %
current_menu = "dashboard"
menu_stack = []
current_button_target = "f5"
selected_index = 0

button_assign_hold_time = 1.0
encoder_back_hold_time = 0.6
nvm_size = 1024

screensaver_timeout = 30
menu_timeout = 30
display_inverted = False
last_activity = 0.0
track_title = ""
tz_offset = 2       # UTC+2 (CEST); change to 1 in winter (CET)
ntp_synced = False

last_encoder_time = 0.0
last_encoder_activity = 0.0
encoder_steps = 0
encoder_button_pressed_at = 0.0
# set by code.py after hardware init
last_encoder_state = 0
last_encoder_button_state = True
