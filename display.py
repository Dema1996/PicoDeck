import board
import busio
import displayio
import fourwire
import terminalio
from adafruit_display_text import label
from adafruit_ili9341 import ILI9341
import pwmio
import supervisor
import usb_cdc

import time as _time
import state
import menus

displayio.release_displays()

spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)
_bus = fourwire.FourWire(spi, command=board.GP6, chip_select=board.GP5, reset=board.GP7)
tft = ILI9341(_bus, width=240, height=320)
tft.auto_refresh = False

_backlight = pwmio.PWMOut(board.GP15, frequency=1000, duty_cycle=65535)

_F   = terminalio.FONT
_W   = 240  # display width
_H   = 320  # display height
_HDR = 40   # header height px
_IH  = 40   # item row height px
_VIS = 7    # visible items  (40*7 + 40 header = 320)
_MENU_VISIBLE    = 17    # label chars visible at scale=2 (232px / 12px)
_MENU_SCROLL_STEP = 0.4  # seconds per scroll step

_C_BG      = 0x0d1117
_C_HDR_BG  = 0x161b22
_C_SEL_BG  = 0x1f4e8a
_C_HDR_FG  = 0x79c0ff
_C_HDR_SUB = 0x6e7681
_C_SEL_FG  = 0xffffff
_C_ITEM_FG = 0x8b949e

_menu_scroll_offset = 0
_menu_scroll_time   = 0.0
_menu_last_label    = ""

# ── menu group ──────────────────────────────────────────────────────────────

_root = displayio.Group()

_bg_bm = displayio.Bitmap(_W, _H, 1)
_bg_pal = displayio.Palette(1)
_bg_pal[0] = _C_BG
_root.append(displayio.TileGrid(_bg_bm, pixel_shader=_bg_pal))

_hdr_bm = displayio.Bitmap(_W, _HDR, 1)
_hdr_pal = displayio.Palette(1)
_hdr_pal[0] = _C_HDR_BG
_root.append(displayio.TileGrid(_hdr_bm, pixel_shader=_hdr_pal, x=0, y=0))

_hdr_title = label.Label(_F, text="MENU", color=_C_HDR_FG, scale=2)
_hdr_title.anchor_point = (0.0, 0.5)
_hdr_title.anchored_position = (8, _HDR // 2)
_root.append(_hdr_title)

_hdr_info = label.Label(_F, text="", color=_C_HDR_SUB, scale=1)
_hdr_info.anchor_point = (1.0, 0.5)
_hdr_info.anchored_position = (_W - 4, _HDR // 2)
_root.append(_hdr_info)

_row_pals = []
_row_lbls = []
for _i in range(_VIS):
    _y = _HDR + _i * _IH
    _bm = displayio.Bitmap(_W, _IH, 1)
    _pal = displayio.Palette(1)
    _pal[0] = _C_BG
    _row_pals.append(_pal)
    _root.append(displayio.TileGrid(_bm, pixel_shader=_pal, x=0, y=_y))
    _lbl = label.Label(_F, text="", color=_C_ITEM_FG, scale=2)
    _lbl.anchor_point = (0.0, 0.5)
    _lbl.anchored_position = (8, _y + _IH // 2)
    _row_lbls.append(_lbl)
    _root.append(_lbl)

# ── message group ─────────────────────────────────────────────────────────────

_msg_grp = displayio.Group()
_msg_bm = displayio.Bitmap(_W, _H, 1)
_msg_pal = displayio.Palette(1)
_msg_pal[0] = _C_BG
_msg_grp.append(displayio.TileGrid(_msg_bm, pixel_shader=_msg_pal))

_msg_l1 = label.Label(_F, text="", color=0xffd700, scale=3)
_msg_l1.anchor_point = (0.5, 0.5)
_msg_l1.anchored_position = (_W // 2, _H // 2 - 30)
_msg_grp.append(_msg_l1)

_msg_l2 = label.Label(_F, text="", color=_C_SEL_FG, scale=2)
_msg_l2.anchor_point = (0.5, 0.5)
_msg_l2.anchored_position = (_W // 2, _H // 2 + 30)
_msg_grp.append(_msg_l2)

# ── screensaver group ─────────────────────────────────────────────────────────

_ss_grp = displayio.Group()
_ss_bg_bm = displayio.Bitmap(_W, _H, 1)
_ss_bg_pal = displayio.Palette(1)
_ss_bg_pal[0] = _C_BG
_ss_grp.append(displayio.TileGrid(_ss_bg_bm, pixel_shader=_ss_bg_pal))

_ss_time = label.Label(_F, text="--:--", color=_C_HDR_FG, scale=3)
_ss_time.anchor_point = (0.5, 0.5)
_ss_time.anchored_position = (_W // 2, 65)
_ss_grp.append(_ss_time)

_ss_date = label.Label(_F, text="", color=_C_SEL_FG, scale=2)
_ss_date.anchor_point = (0.5, 0.5)
_ss_date.anchored_position = (_W // 2, 130)
_ss_grp.append(_ss_date)

_ss_track = label.Label(_F, text="", color=0xffd700, scale=2)
_ss_track.anchor_point = (0.5, 0.5)
_ss_track.anchored_position = (_W // 2, 185)
_ss_grp.append(_ss_track)

_ss_profile = label.Label(_F, text="", color=_C_ITEM_FG, scale=1)
_ss_profile.anchor_point = (0.5, 0.5)
_ss_profile.anchored_position = (_W // 2, 240)
_ss_grp.append(_ss_profile)

_ss_wifi = label.Label(_F, text="", color=_C_ITEM_FG, scale=1)
_ss_wifi.anchor_point = (0.5, 0.5)
_ss_wifi.anchored_position = (_W // 2, 290)
_ss_grp.append(_ss_wifi)

# Signal bars: 4 bars (3 px wide, 1 px gap), heights 4/7/10/14, total 15×14 px
_BARS_W, _BARS_H = 15, 14
_ss_bars_bm  = displayio.Bitmap(_BARS_W, _BARS_H, 3)
_ss_bars_pal = displayio.Palette(3)
_ss_bars_pal[0] = _C_BG       # background
_ss_bars_pal[1] = 0x58a6ff    # filled bar
_ss_bars_pal[2] = 0x21262d    # empty bar
_ss_grp.append(displayio.TileGrid(
    _ss_bars_bm, pixel_shader=_ss_bars_pal,
    x=(_W - _BARS_W) // 2, y=267))

tft.root_group = _root


# ── helpers ───────────────────────────────────────────────────────────────────

def _pad16(s):
    s = s[:16]
    return s + " " * (16 - len(s))


def _print_lcd(line1, line2):
    if not supervisor.runtime.serial_connected:
        return
    try:
        msg = ("+----------------+\r\n"
               "|" + _pad16(line1) + "|\r\n"
               "|" + _pad16(line2) + "|\r\n"
               "+----------------+\r\n")
        usb_cdc.console.write(msg.encode())
    except OSError:
        pass


def _scroll_offset(total):
    half = _VIS // 2
    return max(0, min(state.selected_index - half, total - _VIS))


# ── public API ────────────────────────────────────────────────────────────────

def draw_dashboard():
    profile_short = state.profile_labels[state.current_profile][:8].upper()
    enc_short = {"navigate": "NAV", "volume": "VOL",
                 "brightness": str(state.brightness) + "%",
                 "mac_brightness": "MBRT"}[state.encoder_mode]
    _hdr_title.text = profile_short
    _hdr_info.text = enc_short
    for i, btn in enumerate(state.button_order):
        action_lbl = menus.format_action_label(state.button_actions[btn])
        _row_pals[i][0] = _C_BG
        _row_lbls[i].color = _C_SEL_FG
        _row_lbls[i].text = "  " + state.button_pins[btn] + "  " + action_lbl[:13]
    for i in range(len(state.button_order), _VIS):
        _row_pals[i][0] = _C_BG
        _row_lbls[i].text = ""
    tft.root_group = _root
    tft.refresh()


def draw_menu():
    if state.current_menu == "dashboard":
        draw_dashboard()
        return
    global _menu_scroll_offset, _menu_last_label
    items = menus.get_menu_items(state.current_menu)
    total = len(items)
    v_offset = _scroll_offset(total)

    sel_label = items[state.selected_index]["label"] if state.selected_index < total else ""
    if sel_label != _menu_last_label:
        _menu_scroll_offset = 0
        _menu_last_label = sel_label

    _hdr_title.text = menus.get_menu_header(state.current_menu)

    enc_short = {"navigate": "NAV", "volume": "VOL", "brightness": str(state.brightness) + "%", "mac_brightness": "MBRT"}[state.encoder_mode]
    _hdr_info.text = (state.profile_labels[state.current_profile][:3].upper()
                      + " " + enc_short
                      + " " + str(state.selected_index + 1) + "/" + str(total))

    for i in range(_VIS):
        idx = v_offset + i
        if idx < total:
            selected = (idx == state.selected_index)
            _row_pals[i][0] = _C_SEL_BG if selected else _C_BG
            _row_lbls[i].color = _C_SEL_FG if selected else _C_ITEM_FG
            raw = items[idx]["label"]
            if selected and len(raw) > _MENU_VISIBLE:
                padded = raw + "    "
                doubled = padded + padded
                h = _menu_scroll_offset % len(padded)
                text = "> " + doubled[h:h + _MENU_VISIBLE]
            else:
                text = ("> " if selected else "  ") + raw[:_MENU_VISIBLE]
            _row_lbls[i].text = text
        else:
            _row_pals[i][0] = _C_BG
            _row_lbls[i].text = ""

    tft.root_group = _root
    tft.refresh()
    _print_lcd(_hdr_title.text, items[state.selected_index]["label"])



def update_menu_scroll():
    global _menu_scroll_offset, _menu_scroll_time
    if state.current_menu == "dashboard":
        return
    items = menus.get_menu_items(state.current_menu)
    if not items or state.selected_index >= len(items):
        return
    if len(items[state.selected_index]["label"]) <= _MENU_VISIBLE:
        return
    now = _time.monotonic()
    if now - _menu_scroll_time >= _MENU_SCROLL_STEP:
        _menu_scroll_offset += 1
        _menu_scroll_time = now
        draw_menu()


def show_message(line1, line2=""):
    _msg_l1.text = line1
    _msg_l2.text = line2
    tft.root_group = _msg_grp
    tft.refresh()
    _print_lcd(line1, line2)


def go_back():
    if state.menu_stack:
        state.current_menu = state.menu_stack.pop()
    else:
        state.current_menu = "dashboard"
    state.selected_index = 0
    draw_menu()


def _draw_bars(rssi):
    if rssi is None:    filled = 0
    elif rssi >= -60:   filled = 4
    elif rssi >= -70:   filled = 3
    elif rssi >= -80:   filled = 2
    else:               filled = 1
    heights = [4, 7, 10, 14]
    for i, h in enumerate(heights):
        c = 1 if i < filled else 2
        x0 = i * 4
        for bx in range(3):
            for y in range(_BARS_H):
                _ss_bars_bm[x0 + bx, y] = c if y >= _BARS_H - h else 0


def show_screensaver(time_str, date_str, track_str, profile_str, wifi_str, rssi=None):
    _ss_time.text = time_str
    _ss_date.text = date_str
    _ss_track.text = track_str
    _ss_profile.text = profile_str
    _ss_wifi.text = wifi_str
    _draw_bars(rssi)
    tft.root_group = _ss_grp
    tft.refresh()


def set_brightness(level):
    level = max(10, min(100, level))
    _backlight.duty_cycle = int(level / 100 * 65535)


def set_inversion(inverted):
    try:
        _bus.send(0x21 if inverted else 0x20, b"")
        state.display_inverted = inverted
    except Exception as e:
        print("inversion error:", e)


def item_at_y(y):
    """Returns the menu item index at screen y, or None if in the header area."""
    if y < _HDR:
        return None
    row = (y - _HDR) // _IH
    if row >= _VIS:
        return None
    items = menus.get_menu_items(state.current_menu)
    idx = _scroll_offset(len(items)) + row
    return idx if idx < len(items) else None
