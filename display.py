import board
import busio
import displayio
import fourwire
import terminalio
import vectorio
from adafruit_display_text import label
from adafruit_ili9341 import ILI9341
import pwmio
import supervisor
import usb_cdc

import time as _time
import state
import menus
import console_log
import sdcard

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

_THEMES = {
    "dark":    (0x0d1117, 0x161b22, 0x1f4e8a, 0x79c0ff, 0x6e7681, 0xffffff, 0x8b949e, 0x21262d),
    "dracula": (0x282a36, 0x44475a, 0x6272a4, 0xbd93f9, 0x6272a4, 0xf8f8f2, 0x6272a4, 0x383a4a),
    "matrix":  (0x000000, 0x001400, 0x005000, 0x00ff41, 0x007700, 0x00ff41, 0x00aa00, 0x001a00),
    "amber":   (0x0a0800, 0x1a1200, 0x4d3300, 0xffaa00, 0x886600, 0xffcc44, 0xaa7700, 0x1a1200),
}

_menu_scroll_offset = 0
_menu_scroll_time   = 0.0
_menu_last_label    = ""

# ── menu group ──────────────────────────────────────────────────────────────

_root = displayio.Group()

_bg_bm = displayio.Bitmap(_W, _H, 1)
_bg_pal = displayio.Palette(1)
_bg_pal[0] = _C_BG
_bg_tg = displayio.TileGrid(_bg_bm, pixel_shader=_bg_pal)
_root.append(_bg_tg)

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

_sep_bm = displayio.Bitmap(_W, 2, 1)
_sep_pal = displayio.Palette(1)
_sep_pal[0] = _C_SEL_BG
_root.append(displayio.TileGrid(_sep_bm, pixel_shader=_sep_pal, x=0, y=_HDR - 2))

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

_footer_sep_bm  = displayio.Bitmap(_W, 1, 1)
_footer_sep_pal = displayio.Palette(1)
_footer_sep_pal[0] = _C_SEL_BG
_footer_sep_pal.make_transparent(0)   # hidden by default; shown in dashboard
_root.append(displayio.TileGrid(_footer_sep_bm, pixel_shader=_footer_sep_pal,
                                 x=0, y=_HDR + 5 * _IH))

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

# ── level overlay (volume / brightness) ──────────────────────────────────────

_lvl_grp = displayio.Group()

_lvl_bg_pal = displayio.Palette(1)
_lvl_bg_pal[0] = _C_BG
_lvl_grp.append(vectorio.Rectangle(pixel_shader=_lvl_bg_pal,
                                    width=_W, height=_H, x=0, y=0))

_lvl_icon = label.Label(_F, text="VOL", color=_C_HDR_FG, scale=3)
_lvl_icon.anchor_point = (0.5, 0.5)
_lvl_icon.anchored_position = (_W // 2, 100)
_lvl_grp.append(_lvl_icon)

_lvl_pct = label.Label(_F, text="50%", color=_C_SEL_FG, scale=2)
_lvl_pct.anchor_point = (0.5, 0.5)
_lvl_pct.anchored_position = (_W // 2, 175)
_lvl_grp.append(_lvl_pct)

_BAR_X = 20
_BAR_Y = 215
_BAR_W = _W - 40
_BAR_H = 24

_bar_track_pal = displayio.Palette(1)
_bar_track_pal[0] = 0x21262d
_lvl_grp.append(vectorio.Rectangle(pixel_shader=_bar_track_pal,
                                    width=_BAR_W, height=_BAR_H,
                                    x=_BAR_X, y=_BAR_Y))

_bar_fill_pal = displayio.Palette(1)
_bar_fill_pal[0] = _C_HDR_FG
_bar_fill = vectorio.Rectangle(pixel_shader=_bar_fill_pal,
                                width=1, height=_BAR_H,
                                x=_BAR_X, y=_BAR_Y)
_lvl_grp.append(_bar_fill)

_overlay_active     = False
_overlay_dismiss_at = 0.0

tft.root_group = _root

# ── SD card image support ─────────────────────────────────────────────────────

_sd_file      = None   # currently open image file handle
_sd_tg        = None   # TileGrid for the open image
_sd_loaded_for = None  # key to avoid redundant reloads
_dash_file      = None
_dash_tg        = None
_dash_loaded_for = None

_sd_placeholder_bm  = displayio.Bitmap(1, 1, 1)
_sd_placeholder_pal = displayio.Palette(1)
_sd_placeholder_pal[0] = 0
_sd_img_grp = displayio.Group()
_sd_img_grp.append(displayio.TileGrid(_sd_placeholder_bm, pixel_shader=_sd_placeholder_pal))

_root_slot0    = _bg_tg   # tracks what is currently at _root[0]
_sd_img_slot0  = None     # tracks what is currently at _sd_img_grp[0]


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


def _load_sd_image(path, key):
    global _sd_file, _sd_tg, _sd_loaded_for
    if _sd_loaded_for == key:
        return _sd_tg
    _release_sd_image()
    try:
        f = open(path, "rb")
        odb = displayio.OnDiskBitmap(f)
        tg = displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
        _sd_file = f
        _sd_tg = tg
        _sd_loaded_for = key
        return tg
    except (OSError, ValueError):
        _sd_loaded_for = key  # cache failure — don't retry until sd_reload
        return None


def _load_dashboard_image(path, key):
    global _dash_file, _dash_tg, _dash_loaded_for
    if _dash_loaded_for == key:
        return _dash_tg
    _release_dashboard_image()
    try:
        f = open(path, "rb")
        odb = displayio.OnDiskBitmap(f)
        tg = displayio.TileGrid(odb, pixel_shader=odb.pixel_shader)
        _dash_file = f
        _dash_tg = tg
        _dash_loaded_for = key
        return tg
    except (OSError, ValueError):
        _dash_loaded_for = key
        return None


def _release_sd_image():
    global _sd_file, _sd_tg, _sd_loaded_for, _sd_img_slot0
    if _sd_file is not None:
        try:
            _sd_file.close()
        except Exception:
            pass
    _sd_file = None
    _sd_tg = None
    _sd_loaded_for = None
    _sd_img_slot0 = None


def _release_dashboard_image():
    global _dash_file, _dash_tg, _dash_loaded_for
    if _dash_file is not None:
        try:
            _dash_file.close()
        except Exception:
            pass
    _dash_file = None
    _dash_tg = None
    _dash_loaded_for = None


def _handle_sd_render_error(context, err):
    sdcard.last_error = str(err)
    console_log.log("SD render error ({}): {}".format(context, err))
    _release_sd_image()
    _release_dashboard_image()


def reset_sd_caches():
    _release_sd_image()
    _release_dashboard_image()


def _ensure_rows_opaque():
    for p in _row_pals:
        p.make_opaque(0)


def _set_root_bg(tg):
    global _root_slot0
    if _root_slot0 is not tg:
        _root[0] = tg
        _root_slot0 = tg


# ── public API ────────────────────────────────────────────────────────────────

def show_sd_image(path):
    """Display a full-screen BMP from SD card. Returns True on success."""
    global _sd_img_slot0
    tg = _load_sd_image(path, "ss:" + path)
    if tg is None:
        return False
    if _sd_img_slot0 is not tg:
        _sd_img_grp[0] = tg
        _sd_img_slot0 = tg
    tft.root_group = _sd_img_grp
    try:
        tft.refresh()
        return True
    except OSError as e:
        _handle_sd_render_error(path, e)
        return False


def set_theme(name):
    global _C_BG, _C_HDR_BG, _C_SEL_BG, _C_HDR_FG, _C_HDR_SUB, _C_SEL_FG, _C_ITEM_FG
    t = _THEMES.get(name, _THEMES["dark"])
    _C_BG, _C_HDR_BG, _C_SEL_BG, _C_HDR_FG, _C_HDR_SUB, _C_SEL_FG, _C_ITEM_FG, bar_trk = t
    # background + header
    _bg_pal[0]  = _C_BG
    _hdr_pal[0] = _C_HDR_BG
    _sep_pal[0] = _C_SEL_BG
    _footer_sep_pal[0] = _C_SEL_BG
    _hdr_title.color = _C_HDR_FG
    _hdr_info.color  = _C_HDR_SUB
    # message overlay
    _msg_pal[0]   = _C_BG
    _msg_l2.color = _C_SEL_FG
    # level overlay
    _lvl_bg_pal[0]    = _C_BG
    _lvl_icon.color   = _C_HDR_FG
    _lvl_pct.color    = _C_SEL_FG
    _bar_track_pal[0] = bar_trk
    _bar_fill_pal[0]  = _C_HDR_FG
    # screensaver
    _ss_bg_pal[0]     = _C_BG
    _ss_time.color    = _C_HDR_FG
    _ss_date.color    = _C_SEL_FG
    _ss_profile.color = _C_ITEM_FG
    _ss_wifi.color    = _C_ITEM_FG
    _ss_bars_pal[1]   = _C_HDR_FG
    _ss_bars_pal[2]   = bar_trk
    state.theme = name


def show_level_overlay(lbl, level, max_level):
    global _overlay_active, _overlay_dismiss_at
    _overlay_active = True
    _overlay_dismiss_at = _time.monotonic() + 1.5
    _lvl_icon.text = lbl
    pct = int(level * 100 / max_level)
    _lvl_pct.text = str(pct) + "%"
    _bar_fill.width = max(1, int(_BAR_W * level / max_level))
    tft.root_group = _lvl_grp
    tft.refresh()


def update_overlay():
    global _overlay_active
    if _overlay_active and _time.monotonic() >= _overlay_dismiss_at:
        _overlay_active = False
        draw_menu()


def draw_dashboard(skip_sd_image=False):
    _ensure_rows_opaque()
    profile_short = state.profile_labels[state.current_profile][:8].upper()
    enc_short = {"navigate": "NAV", "volume": "VOL",
                 "brightness": str(state.brightness) + "%",
                 "mac_brightness": "MBRT"}[state.encoder_mode]
    _hdr_title.text = profile_short
    _hdr_info.text = enc_short
    for i, btn in enumerate(state.button_order):
        action_lbl = menus.format_action_label(state.button_actions[btn])
        pin = state.button_pins[btn]
        _row_pals[i][0] = _C_HDR_BG if i % 2 else _C_BG
        _row_lbls[i].color = _C_SEL_FG
        _row_lbls[i].text = "[" + pin + "] " + action_lbl[:12]
    enc_map = {"navigate": "NAV", "volume": "VOL",
               "brightness": "HELL.", "mac_brightness": "MAC H."}
    _row_pals[5].make_transparent(0)
    _row_lbls[5].color = _C_HDR_SUB
    _row_lbls[5].text = "  ENC: " + enc_map[state.encoder_mode] + (" R" if state.encoder_reversed else "")
    _row_pals[6].make_transparent(0)
    _row_lbls[6].color = _C_HDR_SUB
    if state.ntp_synced:
        t = _time.localtime()
        time_str = "{:02d}:{:02d}".format(t.tm_hour, t.tm_min)
    else:
        time_str = "--:--"
    _row_lbls[6].text = "  " + time_str + "  " + state.profile_labels[state.current_profile]
    _footer_sep_pal.make_opaque(0)
    # Dashboard uses the theme background directly; SD-backed BMPs are too slow
    # because OnDiskBitmap re-reads from the card on every display refresh.
    for p in _row_pals[:5]:
        p.make_opaque(0)
    _set_root_bg(_bg_tg)
    tft.root_group = _root
    try:
        tft.refresh()
    except OSError as e:
        _handle_sd_render_error("dashboard", e)
        tft.root_group = _root
        tft.refresh()


def draw_menu(skip_dashboard_image=False):
    global _overlay_active, _menu_scroll_offset, _menu_last_label
    _overlay_active = False
    if state.current_menu == "dashboard":
        draw_dashboard(skip_sd_image=skip_dashboard_image)
        return
    _set_root_bg(_bg_tg)
    _ensure_rows_opaque()
    _footer_sep_pal.make_transparent(0)
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
                text = "\xbb " + doubled[h:h + _MENU_VISIBLE]
            else:
                text = ("\xbb " if selected else "  ") + raw[:_MENU_VISIBLE]
            _row_lbls[i].text = text
        else:
            _row_pals[i][0] = _C_BG
            _row_lbls[i].text = ""

    tft.root_group = _root
    tft.refresh()
    _print_lcd(_hdr_title.text, items[state.selected_index]["label"])



def update_menu_scroll():
    global _menu_scroll_offset, _menu_scroll_time
    if _overlay_active or state.current_menu == "dashboard":
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
