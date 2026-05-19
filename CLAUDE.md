# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

CircuitPython firmware for a Raspberry Pi Pico 2 W macro pad with a 16x2 LCD, 5 hardware buttons, and a rotary encoder. All firmware lives in `code.py`. The `lib/` directory contains vendored CircuitPython libraries that are copied to the device as-is.

## Development Commands

There is no build step — development is a copy-to-device workflow:

```bash
cp code.py /Volumes/CIRCUITPY/code.py          # deploy firmware
cp -R lib /Volumes/CIRCUITPY/lib               # deploy dependencies (rarely needed)
screen /dev/tty.usbmodem* 115200               # open serial console for tracebacks
```

The Pico auto-restarts when `code.py` changes on the CIRCUITPY volume. There is no automated test suite; changes must be validated on hardware.

## Architecture

### Menu System

Menus are defined as a `menus` dict of lists of item dicts. Each item has a `label` and either a `submenu` key (opens a child menu) or an `action` key (executes something). Navigation state is three globals: `current_menu`, `selected_index`, and `menu_stack` (a push-down stack for back navigation).

Dynamic menus (`buttons`, `button_detail`, `profiles`) are generated at read-time by `get_menu_items()` rather than stored in the static `menus` dict. This keeps live state (current button mappings, active profile) reflected correctly without re-initializing the dict.

### Adding a New Action

For keyboard shortcuts: add an entry to `SHORTCUT_ACTIONS` (tuple of `Keycode.*` values) and add a menu item to the relevant submenu. For media keys: add to `MEDIA_ACTIONS` (a `ConsumerControlCode.*` value). `execute_action()` dispatches via these dicts; no new branches needed for standard shortcuts.

For actions with custom behaviour (e.g. `open_vscode` which types text via `keyboard_layout`), add an `elif` branch in `execute_action()`.

Always add a display label in `format_action_label()`.

`get_valid_actions()` derives the assignable-action set from `menus` automatically, so new menu actions become button-mappable for free.

### NVM Persistence

Button mappings are stored in `microcontroller.nvm` as a null-terminated JSON blob (max 512 bytes). Schema:

```json
{"current_profile": "default", "profiles": {"default": {...}, "coding": {...}, "media": {...}}}
```

`load_button_actions()` runs once at startup; `save_button_actions()` writes on every mapping change. The NVM size is fixed at 512 bytes — keep the serialized profile data well under that limit.

### Encoder State Machine

The encoder uses a 4-step gray-code transition table. Accumulator `encoder_steps` counts half-steps; an action fires every 2 steps to match the physical detent feel. Debounce is 1 ms between transitions (`last_encoder_time`).

### Button Hold Behaviour

`handle_macro_button()` is non-blocking. It uses `button_hold_state` (a dict keyed by button name) to track press start time and whether the hold action already fired. A hold ≥ `button_assign_hold_time` (1 s) maps the currently highlighted menu item to that button; a short press executes the mapped action. The main loop calls all five buttons every iteration, so encoder and other buttons stay responsive during a hold.

### Profile Defaults

Each profile (`default`, `coding`, `media`) has its own factory defaults in `default_button_profiles`. `reset_button_actions()` and `reset_single_button()` restore to the active profile's defaults, not the global `default` profile.

## CircuitPython Gotchas

- **No `str.ljust()`** — CircuitPython omits this method. Use the `_pad16()` helper (string slice + space concatenation).
- **`print()` blocks when USB is connected but no terminal is reading** — use `supervisor.runtime.serial_connected` as a guard and write to `usb_cdc.console` directly.
- **`.mpy` files are version-locked** — the format version must match the running CircuitPython major version. A `.mpy` compiled for CP 9.x will not load under CP 10.x.

## Pin Map

| Role | Pin |
|---|---|
| TFT SCK / MOSI / MISO | GP2 / GP3 / GP4 |
| TFT CS / D/C / RESET | GP5 / GP6 / GP7 |
| btn_back / btn_up / btn_down / btn_select | GP8–GP11 |
| Encoder CLK / DT / SW | GP12 / GP13 / GP14 |
| TFT LED (backlight) | GP15 |
| btn_favorite | GP16 |
| Touch CS / IRQ (optional) | GP17 / GP18 |

Buttons use `INPUT_PULLUP`; pressed = `LOW`.

Display: AZDelivery 2.4" ILI9341 SPI (320×240). SPI0 hardware bus on GP2–GP4.
