import time
import json
import microcontroller

import state
import menus
import display
import actions


def _default_profile_mapping(profile_name):
    return dict(state.default_button_profiles.get(
        profile_name, state.default_button_profiles["default"]))


def _copy_button_profiles():
    return {name: dict(mapping) for name, mapping in state.button_profiles.items()}


def snapshot_state():
    return {
        "profile_order": list(state.profile_order),
        "profile_labels": dict(state.profile_labels),
        "button_profiles": _copy_button_profiles(),
        "button_actions": dict(state.button_actions),
        "current_profile": state.current_profile,
        "wifi_ssid": state.wifi_ssid,
        "wifi_password": state.wifi_password,
        "theme": state.theme,
        "screensaver_timeout": state.screensaver_timeout,
        "idle_mode": state.idle_mode,
        "dim_brightness": state.dim_brightness,
        "brightness": state.brightness,
        "encoder_mode": state.encoder_mode,
        "encoder_reversed": state.encoder_reversed,
        "encoder_threshold": state.encoder_threshold,
        "button_assign_hold_time": state.button_assign_hold_time,
        "display_inverted": state.display_inverted,
        "menu_timeout": state.menu_timeout,
    }


def restore_state(snapshot):
    state.profile_order = list(snapshot["profile_order"])
    state.profile_labels = dict(snapshot["profile_labels"])
    state.button_profiles = {
        name: dict(mapping) for name, mapping in snapshot["button_profiles"].items()
    }
    state.button_actions = dict(snapshot["button_actions"])
    state.current_profile = snapshot["current_profile"]
    state.wifi_ssid = snapshot["wifi_ssid"]
    state.wifi_password = snapshot["wifi_password"]
    state.theme = snapshot["theme"]
    state.screensaver_timeout = snapshot["screensaver_timeout"]
    state.idle_mode = snapshot["idle_mode"]
    state.dim_brightness = snapshot["dim_brightness"]
    state.brightness = snapshot["brightness"]
    state.encoder_mode = snapshot["encoder_mode"]
    state.encoder_reversed = snapshot["encoder_reversed"]
    state.encoder_threshold = snapshot["encoder_threshold"]
    state.button_assign_hold_time = snapshot["button_assign_hold_time"]
    state.display_inverted = snapshot["display_inverted"]
    state.menu_timeout = snapshot["menu_timeout"]


def _persist_or_rollback(snapshot):
    try:
        save_button_actions()
    except Exception:
        restore_state(snapshot)
        raise


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
            # Restore custom profiles before loading their assignments
            custom_labels = saved_config.get("profile_labels", {})
            for name in saved_config.get("profile_order", []):
                if (name not in state.profile_order
                        and len(state.profile_order) < state.MAX_PROFILES):
                    state.profile_order.append(name)
                    state.profile_labels[name] = custom_labels.get(name, name)
                    state.button_profiles[name] = dict(state.default_button_profiles["default"])

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

        settings = saved_config.get("settings", {})
        state.wifi_ssid = saved_config.get("wifi_ssid", "")
        state.wifi_password = saved_config.get("wifi_password", "")
        saved_theme = settings.get("theme", saved_config.get("theme", "dark"))
        if saved_theme in ("dark", "dracula", "matrix", "amber"):
            state.theme = saved_theme
        try:
            state.screensaver_timeout = int(settings.get("screensaver_timeout", state.screensaver_timeout))
            state.dim_brightness = max(10, min(50, int(settings.get("dim_brightness", state.dim_brightness))))
            state.brightness = max(10, min(100, int(settings.get("brightness", state.brightness))))
            state.encoder_threshold = int(settings.get("encoder_threshold", state.encoder_threshold))
            state.button_assign_hold_time = float(settings.get(
                "button_assign_hold_time", state.button_assign_hold_time))
            state.menu_timeout = int(settings.get("menu_timeout", state.menu_timeout))
        except (ValueError, TypeError):
            pass
        saved_idle_mode = settings.get("idle_mode", state.idle_mode)
        if saved_idle_mode in ("screensaver", "dim"):
            state.idle_mode = saved_idle_mode
        saved_encoder_mode = settings.get("encoder_mode", state.encoder_mode)
        if saved_encoder_mode in ("navigate", "volume", "brightness", "mac_brightness"):
            state.encoder_mode = saved_encoder_mode
        state.encoder_reversed = bool(settings.get("encoder_reversed", state.encoder_reversed))
        state.display_inverted = bool(settings.get("display_inverted", state.display_inverted))
    except (OSError, ValueError):
        pass

    state.button_actions = dict(state.button_profiles[state.current_profile])


def save_wifi_config(ssid, password):
    snapshot = snapshot_state()
    state.wifi_ssid = ssid
    if password:
        state.wifi_password = password
    _persist_or_rollback(snapshot)


def save_button_actions():
    builtin = set(state.default_button_profiles.keys())
    custom_labels = {k: v for k, v in state.profile_labels.items() if k not in builtin}
    custom_order  = [p for p in state.profile_order if p not in builtin]
    serialized = json.dumps({
        "current_profile": state.current_profile,
        "profiles": state.button_profiles,
        "profile_labels": custom_labels,
        "profile_order":  custom_order,
        "wifi_ssid": state.wifi_ssid,
        "wifi_password": state.wifi_password,
        "settings": {
            "theme": state.theme,
            "screensaver_timeout": state.screensaver_timeout,
            "idle_mode": state.idle_mode,
            "dim_brightness": state.dim_brightness,
            "brightness": state.brightness,
            "encoder_mode": state.encoder_mode,
            "encoder_reversed": state.encoder_reversed,
            "encoder_threshold": state.encoder_threshold,
            "button_assign_hold_time": state.button_assign_hold_time,
            "display_inverted": state.display_inverted,
            "menu_timeout": state.menu_timeout,
        },
    }).encode("utf-8")
    if len(serialized) >= state.nvm_size:
        raise ValueError("button mapping too large for NVM")
    padded = serialized + b"\x00" * (state.nvm_size - len(serialized))
    microcontroller.nvm[:state.nvm_size] = padded


def reset_button_actions():
    snapshot = snapshot_state()
    state.button_actions = _default_profile_mapping(state.current_profile)
    state.button_profiles[state.current_profile] = dict(state.button_actions)
    _persist_or_rollback(snapshot)


def save_action_to_button(button_name, action):
    snapshot = snapshot_state()
    state.button_actions[button_name] = action
    state.button_profiles[state.current_profile][button_name] = action
    _persist_or_rollback(snapshot)


def switch_profile(profile_name):
    snapshot = snapshot_state()
    state.current_profile = profile_name
    state.button_actions = dict(state.button_profiles[state.current_profile])
    _persist_or_rollback(snapshot)


def delete_profile(profile_name):
    builtin = set(state.default_button_profiles.keys())
    if profile_name in builtin or profile_name not in state.profile_order:
        return
    snapshot = snapshot_state()
    state.profile_order.remove(profile_name)
    del state.profile_labels[profile_name]
    del state.button_profiles[profile_name]
    if state.current_profile == profile_name:
        state.current_profile = state.profile_order[0]
        state.button_actions = dict(state.button_profiles[state.current_profile])
    _persist_or_rollback(snapshot)


def create_profile(label=None):
    for i in range(1, state.MAX_PROFILES + 1):
        name = "custom{}".format(i)
        if name not in state.profile_order:
            snapshot = snapshot_state()
            if label is None:
                label = "Custom {}".format(i)
            label = label[:12]
            state.profile_order.append(name)
            state.profile_labels[name] = label
            state.button_profiles[name] = dict(state.button_profiles[state.current_profile])
            state.current_profile = name
            state.button_actions = dict(state.button_profiles[name])
            _persist_or_rollback(snapshot)
            return name
    return None


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
        defaults = _default_profile_mapping(state.current_profile)
        save_action_to_button(button_name, defaults[button_name])
    except (OSError, ValueError):
        display.show_message("Reset fehlg", state.button_pins[button_name])
        time.sleep(0.8)
        display.draw_menu()
        return
    display.show_message("Reset", state.button_pins[button_name])
    time.sleep(0.8)
    display.draw_menu()
