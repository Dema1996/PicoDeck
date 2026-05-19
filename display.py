import board
import busio
import displayio
import terminalio
from adafruit_display_text import label
from adafruit_ili9341 import ILI9341
import digitalio
import supervisor
import usb_cdc

import state
import menus

displayio.release_displays()

spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)
_bus = displayio.FourWire(spi, command=board.GP6, chip_select=board.GP5, reset=board.GP7)
tft = ILI9341(_bus, width=320, height=240)

_backlight = digitalio.DigitalInOut(board.GP15)
_backlight.direction = digitalio.Direction.OUTPUT
_backlight.value = True

_F   = terminalio.FONT
_HDR = 40   # header height px
_IH  = 40   # item row height px
_VIS = 5    # visible items

_C_BG      = 0x0d1117
_C_HDR_BG  = 0x161b22
_C_SEL_BG  = 0x1f4e8a
_C_HDR_FG  = 0x79c0ff
_C_HDR_SUB = 0x6e7681
_C_SEL_FG  = 0xffffff
_C_ITEM_FG = 0x8b949e

# ── menu group ──────────────────────────────────────────────────────────────

_root = displayio.Group()

_bg_bm = displayio.Bitmap(320, 240, 1)
_bg_pal = displayio.Palette(1)
_bg_pal[0] = _C_BG
_root.append(displayio.TileGrid(_bg_bm, pixel_shader=_bg_pal))

_hdr_bm = displayio.Bitmap(320, _HDR, 1)
_hdr_pal = displayio.Palette(1)
_hdr_pal[0] = _C_HDR_BG
_root.append(displayio.TileGrid(_hdr_bm, pixel_shader=_hdr_pal, x=0, y=0))

_hdr_title = label.Label(_F, text="MENU", color=_C_HDR_FG, scale=2)
_hdr_title.anchor_point = (0.0, 0.5)
_hdr_title.anchored_position = (12, _HDR // 2)
_root.append(_hdr_title)

_hdr_info = label.Label(_F, text="", color=_C_HDR_SUB, scale=1)
_hdr_info.anchor_point = (1.0, 0.5)
_hdr_info.anchored_position = (316, _HDR // 2)
_root.append(_hdr_info)

_row_pals = []
_row_lbls = []
for _i in range(_VIS):
    _y = _HDR + _i * _IH
    _bm = displayio.Bitmap(320, _IH, 1)
    _pal = displayio.Palette(1)
    _pal[0] = _C_BG
    _row_pals.append(_pal)
    _root.append(displayio.TileGrid(_bm, pixel_shader=_pal, x=0, y=_y))
    _lbl = label.Label(_F, text="", color=_C_ITEM_FG, scale=2)
    _lbl.anchor_point = (0.0, 0.5)
    _lbl.anchored_position = (16, _y + _IH // 2)
    _row_lbls.append(_lbl)
    _root.append(_lbl)

# ── message group ─────────────────────────────────────────────────────────────

_msg_grp = displayio.Group()
_msg_bm = displayio.Bitmap(320, 240, 1)
_msg_pal = displayio.Palette(1)
_msg_pal[0] = _C_BG
_msg_grp.append(displayio.TileGrid(_msg_bm, pixel_shader=_msg_pal))

_msg_l1 = label.Label(_F, text="", color=0xffd700, scale=3)
_msg_l1.anchor_point = (0.5, 0.5)
_msg_l1.anchored_position = (160, 95)
_msg_grp.append(_msg_l1)

_msg_l2 = label.Label(_F, text="", color=_C_SEL_FG, scale=2)
_msg_l2.anchor_point = (0.5, 0.5)
_msg_l2.anchored_position = (160, 155)
_msg_grp.append(_msg_l2)

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

def draw_menu():
    items = menus.get_menu_items(state.current_menu)
    total = len(items)
    offset = _scroll_offset(total)

    _hdr_title.text = menus.get_menu_header(state.current_menu)

    enc_short = {"navigate": "NAV", "volume": "VOL", "brightness": "BRT"}[state.encoder_mode]
    _hdr_info.text = (state.profile_labels[state.current_profile][:3].upper()
                      + " " + enc_short
                      + " " + str(state.selected_index + 1) + "/" + str(total))

    for i in range(_VIS):
        idx = offset + i
        if idx < total:
            selected = (idx == state.selected_index)
            _row_pals[i][0] = _C_SEL_BG if selected else _C_BG
            _row_lbls[i].color = _C_SEL_FG if selected else _C_ITEM_FG
            _row_lbls[i].text = ("> " if selected else "  ") + items[idx]["label"]
        else:
            _row_pals[i][0] = _C_BG
            _row_lbls[i].text = ""

    tft.root_group = _root
    _print_lcd(_hdr_title.text, items[state.selected_index]["label"])


def show_message(line1, line2=""):
    _msg_l1.text = line1
    _msg_l2.text = line2
    tft.root_group = _msg_grp
    _print_lcd(line1, line2)


def go_back():
    if state.menu_stack:
        state.current_menu = state.menu_stack.pop()
        state.selected_index = 0
        draw_menu()


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
