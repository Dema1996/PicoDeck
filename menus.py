import state

menus = {
    "main": [
        {"label": "Media",    "submenu": "media"},
        {"label": "System",   "submenu": "system"},
        {"label": "Coding",   "submenu": "coding"},
        {"label": "Encoder",  "submenu": "encoder"},
        {"label": "Buttons",  "submenu": "buttons"},
        {"label": "Profiles", "submenu": "profiles"},
    ],
    "media": [
        {"label": "Play/Pause",   "action": "play_pause"},
        {"label": "Stop",         "action": "stop"},
        {"label": "Mute",         "action": "mute"},
        {"label": "Previous Trk", "action": "previous_track"},
        {"label": "Next Track",   "action": "next_track"},
        {"label": "Volume Up",    "action": "volume_up"},
        {"label": "Volume Down",  "action": "volume_down"},
        {"label": "Zurueck",      "action": "back"},
    ],
    "coding": [
        {"label": "VSCode",       "action": "open_vscode"},
        {"label": "Command Pal",  "action": "command_palette"},
        {"label": "Terminal",     "action": "toggle_terminal"},
        {"label": "Format Doc",   "action": "format_document"},
        {"label": "Screenshot",   "action": "screenshot"},
        {"label": "New Terminal", "action": "new_terminal"},
        {"label": "Split Editor", "action": "split_editor"},
        {"label": "Zurueck",      "action": "back"},
    ],
    "system": [
        {"label": "Spotlight",    "action": "spotlight"},
        {"label": "App Switcher", "action": "app_switcher"},
        {"label": "Previous App", "action": "previous_app"},
        {"label": "Mission Ctrl", "action": "mission_control"},
        {"label": "Lock Mac",     "action": "lock_mac"},
        {"label": "Show Desktop", "action": "show_desktop"},
        {"label": "Close Window", "action": "close_window"},
        {"label": "Zurueck",      "action": "back"},
    ],
    "encoder": [
        {"label": "Navigate",   "action": "encoder_navigate"},
        {"label": "Volume",     "action": "encoder_volume"},
        {"label": "Brightness", "action": "encoder_brightness"},
        {"label": "Zurueck",    "action": "back"},
    ],
}


def format_action_label(action):
    labels = {
        "mission_control":  "MissionCtrl",
        "play_pause":       "PlayPause",
        "stop":             "Stop",
        "mute":             "Mute",
        "previous_track":   "Prev Track",
        "next_track":       "Next Track",
        "volume_up":        "Volume Up",
        "volume_down":      "Volume Dn",
        "spotlight":        "Spotlight",
        "app_switcher":     "AppSwitch",
        "previous_app":     "Prev App",
        "lock_mac":         "Lock Mac",
        "show_desktop":     "Desktop",
        "open_vscode":      "VSCode",
        "command_palette":  "CmdPalette",
        "toggle_terminal":  "Terminal",
        "format_document":  "Format Doc",
        "screenshot":       "Screenshot",
        "new_terminal":     "New Terminal",
        "split_editor":     "Split Editor",
        "close_window":     "Close Window",
        "encoder_navigate": "Enc Nav",
        "encoder_volume":   "Enc Vol",
        "encoder_brightness": "Enc Bright",
    }
    if action.startswith("profile:"):
        profile_name = action.split(":", 1)[1]
        return "Prof " + state.profile_labels.get(profile_name, profile_name[:6])
    return labels.get(action, action[:10])


def get_assignment_target(item):
    action = item.get("action")
    if action == "switch_profile":
        return "profile:" + item["profile_name"]
    return action


def get_menu_header(menu_name):
    profile_short = state.profile_labels[state.current_profile][:3].upper()
    encoder_short = {"navigate": "NAV", "volume": "VOL", "brightness": "BRT"}[state.encoder_mode]
    headers = {
        "main":          "M " + profile_short + " " + encoder_short,
        "media":         "MEDIA " + encoder_short,
        "system":        "SYSTEM " + encoder_short,
        "coding":        "CODING " + encoder_short,
        "encoder":       "ENC " + profile_short,
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
    items.append({"label": "Zurueck", "action": "back"})
    return items


def get_profiles_menu():
    items = []
    for profile_name in state.profile_order:
        label = state.profile_labels[profile_name]
        if profile_name == state.current_profile:
            label = "* " + label
        items.append({"label": label, "action": "switch_profile", "profile_name": profile_name})
    items.append({"label": "Zurueck", "action": "back"})
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
    items.append({"label": "Zurueck", "action": "back"})
    return items


def get_menu_items(menu_name):
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
