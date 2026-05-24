button_order = ["f1", "f2", "f3", "f4", "f5", "f6"]
button_hold_state = {name: {"pressed_at": None, "handled": False} for name in button_order}
button_pins = {"f1": "F1", "f2": "F2", "f3": "F3", "f4": "F4", "f5": "F5", "f6": "F6"}

MAX_PROFILES = 6

profile_order = ["default", "coding", "media", "system"]
profile_labels = {"default": "Default", "coding": "Coding", "media": "Media", "system": "System"}

default_button_profiles = {
    "default": {
        "f1": "nav_back",
        "f2": "nav_up",
        "f3": "nav_down",
        "f4": "nav_select",
        "f5": "profile:system",
        "f6": "open_whisper",
    },
    "coding": {
        "f1": "command_palette",
        "f2": "toggle_terminal",
        "f3": "new_terminal",
        "f4": "format_document",
        "f5": "open_vscode",
        "f6": "mute",
    },
    "media": {
        "f1": "mute",
        "f2": "previous_track",
        "f3": "next_track",
        "f4": "play_pause",
        "f5": "volume_up",
        "f6": "mute",
    },
    "system": {
        "f1": "wifi_status",
        "f2": "toggle_wifi",
        "f3": "bt_toggle",
        "f4": "screenshot",
        "f5": "profile:default",
        "f6": "lock_mac",
    },
}
button_profiles = {k: dict(v) for k, v in default_button_profiles.items()}
button_actions = dict(default_button_profiles["default"])
current_profile = "default"
current_profile_target = "default"

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
nvm_size = 2048

theme = "dark"
screensaver_timeout = 9999
idle_mode = "screensaver"
dim_brightness = 20
menu_timeout = 30
display_inverted = False
display_rotation = 0   # 0 / 90 / 180 / 270; applied at boot via early NVM read
needs_touch_calibration = False  # set True when rotation changes; cleared after calibration
touch_cal = None   # None = use hardcoded defaults; set to (x_min, x_max, y_min, y_max) after load
display_test_mode = False
local_volume = 50         # estimated 0-100 (no OS feedback)
local_mac_brightness = 50
last_activity = 0.0
track_title = ""
tz_offset = 2       # UTC+2 (CEST); change to 1 in winter (CET)
ntp_synced = False
time_sync_source = "unsynced"   # "unsynced", "host", "ntp_udp", "ntp_http"
last_exception = ""

last_encoder_time = 0.0
last_encoder_activity = 0.0
encoder_steps = 0
encoder_button_pressed_at = 0.0
ignore_next_encoder_release = False
# set by code.py after hardware init
last_encoder_state = 0
last_encoder_button_state = True

remote_nav = None  # set by wifi_server: "up","down","back","select","f1"–"f5", or action str
