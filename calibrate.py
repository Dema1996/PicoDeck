"""
Touch calibration tool.
Deploy as code.py, open serial console, then tap each crosshair when prompted.
At the end the new calibration constants are printed — paste them into touch.py.
"""
import displayio
import board
import busio
import fourwire
import digitalio
import terminalio
import time
from adafruit_ili9341 import ILI9341
from adafruit_display_text import label

displayio.release_displays()

spi = busio.SPI(clock=board.GP2, MOSI=board.GP3, MISO=board.GP4)
bus = fourwire.FourWire(spi, command=board.GP6, chip_select=board.GP5, reset=board.GP7)
tft = ILI9341(bus, width=240, height=320)
tft.auto_refresh = False

bl = digitalio.DigitalInOut(board.GP15)
bl.direction = digitalio.Direction.OUTPUT
bl.value = True

touch_cs = digitalio.DigitalInOut(board.GP17)
touch_cs.direction = digitalio.Direction.OUTPUT
touch_cs.value = True

_CMD_X  = 0xD0
_CMD_Y  = 0x90
_CMD_Z1 = 0xB0
_Z_THRESH = 200

W = 240
H = 320
MARGIN = 20


def read_raw(cmd):
    buf = bytearray(3)
    touch_cs.value = False
    while not spi.try_lock():
        pass
    spi.configure(baudrate=1_000_000, phase=0, polarity=0)
    spi.write_readinto(bytes([cmd, 0, 0]), buf)
    spi.unlock()
    touch_cs.value = True
    return ((buf[1] << 8) | buf[2]) >> 3


def wait_for_tap():
    """Wait for press + release, return median of CMD_Y and CMD_X samples."""
    # wait for press
    while read_raw(_CMD_Z1) < _Z_THRESH:
        time.sleep(0.02)
    samples_y = []
    samples_x = []
    while read_raw(_CMD_Z1) >= _Z_THRESH:
        samples_y.append(read_raw(_CMD_Y))
        samples_x.append(read_raw(_CMD_X))
        time.sleep(0.02)
    # median
    samples_y.sort()
    samples_x.sort()
    mid = len(samples_y) // 2
    time.sleep(0.3)  # debounce
    return samples_y[mid], samples_x[mid]


def draw_cross(grp, bm, cx, cy, color):
    pal = displayio.Palette(2)
    pal[0] = 0x000000
    pal[1] = color
    arm = 12
    for dx in range(-arm, arm + 1):
        if 0 <= cx + dx < W:
            bm[cx + dx, cy] = 1
    for dy in range(-arm, arm + 1):
        if 0 <= cy + dy < H:
            bm[cx, cy + dy] = 1


bm = displayio.Bitmap(W, H, 2)
pal = displayio.Palette(2)
pal[0] = 0x000000
pal[1] = 0xFFFFFF

grp = displayio.Group()
grp.append(displayio.TileGrid(bm, pixel_shader=pal))

msg = label.Label(terminalio.FONT, text="", color=0xFFFF00, scale=2)
msg.anchor_point = (0.5, 0.5)
msg.anchored_position = (W // 2, H // 2)
grp.append(msg)

sub = label.Label(terminalio.FONT, text="", color=0xAAAAAA, scale=1)
sub.anchor_point = (0.5, 0.5)
sub.anchored_position = (W // 2, H // 2 + 28)
grp.append(sub)

tft.root_group = grp
tft.refresh()

# corners: (screen_x, screen_y, label)
corners = [
    (MARGIN,     MARGIN,      "oben links"),
    (W - MARGIN, MARGIN,      "oben rechts"),
    (MARGIN,     H - MARGIN,  "unten links"),
    (W - MARGIN, H - MARGIN,  "unten rechts"),
]

raw_results = []

for i, (cx, cy, name) in enumerate(corners):
    # clear bitmap
    for px in range(W * H):
        bm[px % W, px // W] = 0
    draw_cross(grp, bm, cx, cy, 0xFFFFFF)
    msg.text = f"Tippe: {name}"
    sub.text = f"({i+1}/4)"
    tft.refresh()
    print(f"Tap {name} ({cx},{cy})...")

    ry, rx = wait_for_tap()
    raw_results.append((cx, cy, ry, rx))
    print(f"  raw CMD_Y={ry}  CMD_X={rx}")

    msg.text = "OK"
    sub.text = ""
    tft.refresh()
    time.sleep(0.4)

# --- compute calibration ---
# CMD_Y -> screen X,  CMD_X -> screen Y
# Collect left-edge (cx==MARGIN) and right-edge (cx==W-MARGIN) samples
left_ry  = [r[2] for r in raw_results if r[0] == MARGIN]
right_ry = [r[2] for r in raw_results if r[0] == W - MARGIN]
top_rx   = [r[3] for r in raw_results if r[1] == MARGIN]
bot_rx   = [r[3] for r in raw_results if r[1] == H - MARGIN]

x_min_raw = sum(left_ry)  // len(left_ry)
x_max_raw = sum(right_ry) // len(right_ry)
y_min_raw = sum(top_rx)   // len(top_rx)
y_max_raw = sum(bot_rx)   // len(bot_rx)

# adjust for margin offset so 0 and W/H map to screen edges
x_range = x_max_raw - x_min_raw
y_range = y_max_raw - y_min_raw

x_min_adj = x_min_raw - int(x_range * MARGIN / (W - 2 * MARGIN))
x_max_adj = x_max_raw + int(x_range * MARGIN / (W - 2 * MARGIN))
y_min_adj = y_min_raw - int(y_range * MARGIN / (H - 2 * MARGIN))
y_max_adj = y_max_raw + int(y_range * MARGIN / (H - 2 * MARGIN))

print("\n=== Neue Kalibrierungswerte fuer touch.py ===")
print(f"_X_MIN = {x_min_adj}")
print(f"_X_MAX = {x_max_adj}")
print(f"_Y_MIN = {y_min_adj}")
print(f"_Y_MAX = {y_max_adj}")

msg.text = "Fertig!"
sub.text = "Werte im Serial"
tft.refresh()
