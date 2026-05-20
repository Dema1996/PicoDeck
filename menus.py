import state

menus = {
    "main": [
        {"label": "Medien",        "submenu": "media"},
        {"label": "System",        "submenu": "system"},
        {"label": "Coding",        "submenu": "coding"},
        {"label": "Encoder",       "submenu": "encoder"},
        {"label": "Einstellungen", "submenu": "settings"},
    ],
    "settings": [
        {"label": "Tasten",      "submenu": "buttons"},
        {"label": "Profil",      "submenu": "profiles"},
        {"label": "WiFi",        "submenu": "wifi"},
        {"label": "Enc. Richt.", "action": "toggle_encoder_dir"},
        {"label": "Enc. Speed",  "submenu": "encoder_speed"},
        {"label": "Hold-Zeit",   "submenu": "hold_time"},
        {"label": "Bildschirm",  "submenu": "display_settings"},
        {"label": "Bluetooth",   "submenu": "bluetooth"},
        {"label": "Alles Reset", "action": "reset_button_defaults"},
        {"label": "Zur\xfcck",   "action": "back"},
    ],
    "wifi": [
        {"label": "WiFi Status", "action": "wifi_status"},
        {"label": "AP Modus",    "action": "wifi_start_ap"},
        {"label": "WiFi an/aus", "action": "toggle_wifi"},
        {"label": "Zur\xfcck",   "action": "back"},
    ],
    "encoder_speed": [
        {"label": "Langsam",   "action": "encoder_speed_slow"},
        {"label": "Normal",    "action": "encoder_speed_normal"},
        {"label": "Schnell",   "action": "encoder_speed_fast"},
        {"label": "Zur\xfcck", "action": "back"},
    ],
    "hold_time": [
        {"label": "0.5 Sek",   "action": "hold_time_05"},
        {"label": "1.0 Sek",   "action": "hold_time_10"},
        {"label": "2.0 Sek",   "action": "hold_time_20"},
        {"label": "Zur\xfcck", "action": "back"},
    ],
    "bluetooth": [
        {"label": "BT Status",  "action": "bt_status"},
        {"label": "BT an/aus",  "action": "bt_toggle"},
        {"label": "Zur\xfcck",  "action": "back"},
    ],
    "display_settings": [
        {"label": "Helligkeit",     "submenu": "brightness"},
        {"label": "Screensaver",    "submenu": "screensaver"},
        {"label": "Invertieren",    "action":  "toggle_inversion"},
        {"label": "Men\xfc-Timeout","submenu": "menu_timeout"},
        {"label": "Zur\xfcck",      "action":  "back"},
    ],
    "menu_timeout": [
        {"label": "Aus",     "action": "menu_timeout_off"},
        {"label": "15 Sek",  "action": "menu_timeout_15"},
        {"label": "30 Sek",  "action": "menu_timeout_30"},
        {"label": "60 Sek",  "action": "menu_timeout_60"},
        {"label": "2 Min",   "action": "menu_timeout_120"},
        {"label": "Zur\xfcck","action": "back"},
    ],
    "brightness": [
        {"label": "10%",  "action": "brightness_10"},
        {"label": "20%",  "action": "brightness_20"},
        {"label": "30%",  "action": "brightness_30"},
        {"label": "40%",  "action": "brightness_40"},
        {"label": "50%",  "action": "brightness_50"},
        {"label": "60%",  "action": "brightness_60"},
        {"label": "70%",  "action": "brightness_70"},
        {"label": "80%",  "action": "brightness_80"},
        {"label": "90%",  "action": "brightness_90"},
        {"label": "100%", "action": "brightness_100"},
        {"label": "Zur\xfcck", "action": "back"},
    ],
    "screensaver": [
        {"label": "15 Sek",    "action": "ss_timeout_15"},
        {"label": "30 Sek",    "action": "ss_timeout_30"},
        {"label": "1 Minute",  "action": "ss_timeout_60"},
        {"label": "5 Minuten", "action": "ss_timeout_300"},
        {"label": "Aus",       "action": "ss_timeout_off"},
        {"label": "Zur\xfcck", "action": "back"},
    ],
    "media": [
        {"label": "Play/Pause",     "action": "play_pause"},
        {"label": "Stop",           "action": "stop"},
        {"label": "Stummschalten",  "action": "mute"},
        {"label": "Voriger Titel",  "action": "previous_track"},
        {"label": "N\xe4chster Ttl","action": "next_track"},
        {"label": "Lauter",         "action": "volume_up"},
        {"label": "Leiser",         "action": "volume_down"},
        {"label": "Zur\xfcck",      "action": "back"},
    ],
    "coding": [
        {"label": "VSCode",       "action": "open_vscode"},
        {"label": "Command Pal",  "action": "command_palette"},
        {"label": "Terminal",     "action": "toggle_terminal"},
        {"label": "Format Doc",   "action": "format_document"},
        {"label": "Screenshot",   "action": "screenshot"},
        {"label": "New Terminal", "action": "new_terminal"},
        {"label": "Split Editor", "action": "split_editor"},
        {"label": "Zur\xfcck",    "action": "back"},
    ],
    "system": [
        {"label": "Spotlight",    "action": "spotlight"},
        {"label": "App-Wechsel",  "action": "app_switcher"},
        {"label": "Letzte App",   "action": "previous_app"},
        {"label": "Mission Ctrl", "action": "mission_control"},
        {"label": "Mac Sperren",  "action": "lock_mac"},
        {"label": "Desktop",      "action": "show_desktop"},
        {"label": "Fenster zu",   "action": "close_window"},
        {"label": "Mac Heller",   "action": "mac_brightness_up"},
        {"label": "Mac Dunkler",   "action": "mac_brightness_down"},
        {"label": "OpenWhisper",   "action": "open_whisper"},
        {"label": "Zur\xfcck",     "action": "back"},
    ],
    "encoder": [
        {"label": "Navigieren",    "action": "encoder_navigate"},
        {"label": "Lautst\xe4rke", "action": "encoder_volume"},
        {"label": "Helligkeit",    "action": "encoder_brightness"},
        {"label": "Mac Hellgk.",   "action": "encoder_mac_brightness"},
        {"label": "Zur\xfcck",     "action": "back"},
    ],
}


def format_action_label(action):
    labels = {
        "mission_control":  "MissionCtrl",
        "play_pause":       "PlayPause",
        "stop":             "Stop",
        "mute":             "Stummschalten",
        "previous_track":   "Voriger Ttl",
        "next_track":       "N\xe4chst. Ttl",
        "volume_up":        "Lauter",
        "volume_down":      "Leiser",
        "spotlight":        "Spotlight",
        "app_switcher":     "App-Wechsel",
        "previous_app":     "Letzte App",
        "lock_mac":         "Mac Sperren",
        "show_desktop":     "Desktop",
        "open_vscode":      "VSCode",
        "command_palette":  "CmdPalette",
        "toggle_terminal":  "Terminal",
        "format_document":  "Format Doc",
        "screenshot":       "Screenshot",
        "new_terminal":     "New Terminal",
        "split_editor":     "Split Editor",
        "close_window":     "Fenster zu",
        "encoder_navigate":       "Enc Nav",
        "encoder_volume":         "Enc Vol",
        "encoder_brightness":     "Enc Bright",
        "encoder_mac_brightness": "Enc MacBrt",
        "mac_brightness_up":      "Mac Heller",
        "mac_brightness_down":    "Mac Dunkler",
        "open_whisper":           "OpenWhisper",
        "wifi_status":            "WiFi Status",
        "wifi_start_ap":          "AP Modus",
        "toggle_wifi":            "WiFi",
        "toggle_encoder_dir":     "Enc Richt.",
        "encoder_speed_slow":     "Enc Langsam",
        "encoder_speed_normal":   "Enc Normal",
        "encoder_speed_fast":     "Enc Schnell",
        "hold_time_05":           "Hold 0.5s",
        "hold_time_10":           "Hold 1.0s",
        "hold_time_20":           "Hold 2.0s",
        "bt_status":              "BT Status",
        "bt_toggle":              "BT an/aus",
        "ss_timeout_15":          "Schoner 15s",
        "ss_timeout_30":          "Schoner 30s",
        "ss_timeout_60":          "Schoner 1m",
        "ss_timeout_300":         "Schoner 5m",
        "ss_timeout_off":         "Schoner Aus",
        "toggle_inversion":       "Invertieren",
    }
    if action.startswith("profile:"):
        profile_name = action.split(":", 1)[1]
        return "Prof " + state.profile_labels.get(profile_name, profile_name[:6])
    if action.startswith("brightness_"):
        return "Hell. " + action.split("_")[1] + "%"
    if action.startswith("menu_timeout_"):
        suffix = action.split("_")[2]
        return "Men\xfc " + ("Aus" if suffix == "off" else suffix + "s")
    return labels.get(action, action[:10])


def get_assignment_target(item):
    action = item.get("action")
    if action == "switch_profile":
        return "profile:" + item["profile_name"]
    return action


def get_menu_header(menu_name):
    profile_short = state.profile_labels[state.current_profile][:3].upper()
    enc_dir = "R" if state.encoder_reversed else "N"
    encoder_short = {"navigate": "NAV", "volume": "VOL", "brightness": str(state.brightness) + "%", "mac_brightness": "MBRT"}[state.encoder_mode]
    headers = {
        "dashboard":     profile_short + " " + encoder_short,
        "main":          "MENU",
        "media":         "MEDIA " + encoder_short,
        "system":        "SYSTEM " + encoder_short,
        "coding":        "CODING " + encoder_short,
        "encoder":       "ENC " + profile_short,
        "settings":      "EINSTELLUNGEN",
        "wifi":          "WIFI",
        "encoder_speed": "ENC SPEED",
        "hold_time":     "HOLD TIME",
        "display_settings": "BILDSCHIRM",
        "brightness":    "HELLIGKEIT",
        "screensaver":   "SCREENSAVER",
        "menu_timeout":  "MEN\xdc-TIMEOUT",
        "bluetooth":     "BLUETOOTH",
        "buttons":       "BTN " + state.profile_labels[state.current_profile][:6].upper(),
        "button_detail": state.button_pins[state.current_button_target],
        "profiles":      "PROF " + encoder_short,
    }
    return headers.get(menu_name, menu_name.upper())


def get_buttons_menu():
    items = []
    for button_name in state.button_order:
        items.append({
            "label": state.button_pins[button_name] + " " + format_action_label(state.button_actions[button_name]),
            "action": "open_button_detail",
            "button_name": button_name,
        })
    items.append({"label": "Reset Default", "action": "reset_button_defaults"})
    items.append({"label": "Zur\xfcck", "action": "back"})
    return items


def get_profiles_menu():
    items = []
    for profile_name in state.profile_order:
        label = state.profile_labels[profile_name]
        if profile_name == state.current_profile:
            label = "* " + label
        items.append({"label": label, "action": "switch_profile", "profile_name": profile_name})
    items.append({"label": "Zur\xfcck", "action": "back"})
    return items


def get_button_detail_menu():
    items = [{
        "label": "Akt: " + format_action_label(state.button_actions[state.current_button_target]),
        "action": "show_button_mapping",
        "button_name": state.current_button_target,
    }]
    for action in sorted(get_valid_actions()):
        items.append({
            "label": format_action_label(action),
            "action": "assign_button_action",
            "button_name": state.current_button_target,
            "assign_action": action,
        })
    items.append({"label": "Reset Taste", "action": "reset_single_button", "button_name": state.current_button_target})
    items.append({"label": "Zur\xfcck", "action": "back"})
    return items


def get_brightness_menu():
    items = []
    for level in range(10, 110, 10):
        label = ("* " if level == state.brightness else "  ") + str(level) + "%"
        items.append({"label": label, "action": "brightness_{}".format(level)})
    items.append({"label": "Zur\xfcck", "action": "back"})
    return items


def get_dashboard_items():
    return [
        {"label": state.button_pins[btn] + "  " + format_action_label(state.button_actions[btn])}
        for btn in state.button_order
    ]


def get_menu_items(menu_name):
    if menu_name == "dashboard":
        return get_dashboard_items()
    if menu_name == "brightness":
        return get_brightness_menu()
    if menu_name == "buttons":
        return get_buttons_menu()
    if menu_name == "button_detail":
        return get_button_detail_menu()
    if menu_name == "profiles":
        return get_profiles_menu()
    return menus[menu_name]


def get_valid_actions():
    actions = set()
    for items in menus.values():
        for item in items:
            action = item.get("action")
            if action and action != "back":
                actions.add(action)
    for profile_name in state.profile_order:
        actions.add("profile:" + profile_name)
    return actions
