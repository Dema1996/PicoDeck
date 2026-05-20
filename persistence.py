import time
import json
import microcontroller

import state
import menus
import display
import actions


def load_button_actions():
    valid_actions = menus.get_valid_actions()
    state.button_actions = dict(state.default_button_profiles["default"])
    state.button_profiles = {k: dict(v) for k, v in state.default_button_profiles.items()}
    state.current_profile = "default"

    try:
        raw_config = bytes(microcontroller.nvm[:state.nvm_size])
        raw_config = raw_config.split(b"\x00", 1)[0]
        if not raw_config:
            return
        saved_config = json.loads(raw_config.decode("utf-8"))

        if "profiles" in saved_config:
            saved_profiles = saved_config.get("profiles", {})
            for profile_name in state.profile_order:
                saved_actions = saved_profiles.get(profile_name, {})
                for button_name in state.default_button_profiles["default"]:
                    action = saved_actions.get(button_name)
                    if action in valid_actions:
                        state.button_profiles[profile_name][button_name] = action
            saved_profile = saved_config.get("current_profile")
            if saved_profile in state.profile_order:
                state.current_profile = saved_profile
        else:
            for button_name in state.default_button_profiles["default"]:
                action = saved_config.get(button_name)
                if action in valid_actions:
                    state.button_profiles["default"][button_name] = action

        state.wifi_ssid = saved_config.get("wifi_ssid", "")
        state.wifi_password = saved_config.get("wifi_password", "")
    except (OSError, ValueError):
        pass

    state.button_actions = dict(state.button_profiles[state.current_profile])


def save_wifi_config(ssid, password):
    state.wifi_ssid = ssid
    if password:
        state.wifi_password = password
    save_button_actions()


def save_button_actions():
    serialized = json.dumps({
        "current_profile": state.current_profile,
        "profiles": state.button_profiles,
        "wifi_ssid": state.wifi_ssid,
        "wifi_password": state.wifi_password,
    }).encode("utf-8")
    if len(serialized) >= state.nvm_size:
        raise ValueError("button mapping too large for NVM")
    padded = serialized + b"\x00" * (state.nvm_size - len(serialized))
    microcontroller.nvm[:state.nvm_size] = padded


def reset_button_actions():
    state.button_actions = dict(state.default_button_profiles[state.current_profile])
    state.button_profiles[state.current_profile] = dict(state.default_button_profiles[state.current_profile])
    save_button_actions()


def save_action_to_button(button_name, action):
    state.button_actions[button_name] = action
    state.button_profiles[state.current_profile][button_name] = action
    save_button_actions()


def switch_profile(profile_name):
    state.current_profile = profile_name
    state.button_actions = dict(state.button_profiles[state.current_profile])
    save_button_actions()


def trigger_mapped_action(action):
    if action == "back":
        display.go_back()
        return
    if action.startswith("profile:"):
        profile_name = action.split(":", 1)[1]
        if profile_name in state.profile_order:
            switch_profile(profile_name)
            display.show_message("Profil aktiv", state.profile_labels[profile_name])
            time.sleep(0.8)
            display.draw_menu()
        return
    actions.execute_action(action)


def trigger_button_action(button_name):
    trigger_mapped_action(state.button_actions[button_name])


def assign_current_action_to_button(button_name):
    item = menus.get_menu_items(state.current_menu)[state.selected_index]
    if "action" not in item:
        display.show_message("Kein Mapping", "Nur Makros")
        time.sleep(0.8)
        display.draw_menu()
        return
    action = menus.get_assignment_target(item)
    if action == "back":
        display.show_message("Kein Mapping", "Nicht Zurück")
        time.sleep(0.8)
        display.draw_menu()
        return
    try:
        save_action_to_button(button_name, action)
    except (OSError, ValueError):
        display.show_message("Speichern fehlg", "Mapping aktiv")
        time.sleep(0.8)
        display.draw_menu()
        return
    display.show_message("Gemappt auf", button_name.upper())
    time.sleep(0.8)
    display.draw_menu()


def show_button_mapping(button_name):
    display.show_message(
        state.button_pins[button_name],
        menus.format_action_label(state.button_actions[button_name]),
    )
    time.sleep(1.0)
    display.draw_menu()


def reset_single_button(button_name):
    try:
        save_action_to_button(button_name, state.default_button_profiles[state.current_profile][button_name])
    except (OSError, ValueError):
        display.show_message("Reset fehlg", state.button_pins[button_name])
        time.sleep(0.8)
        display.draw_menu()
        return
    display.show_message("Reset", state.button_pins[button_name])
    time.sleep(0.8)
    display.draw_menu()
