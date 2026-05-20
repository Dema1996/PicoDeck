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

_X_MIN = 3760
_X_MAX = 538
_Y_MIN = 3564
_Y_MAX = 515
_Z_THRESH = 200


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


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def read_pos():
    z1 = read_raw(0xB0)
    if z1 < _Z_THRESH:
        return None
    rx = read_raw(0xD0)
    ry = read_raw(0x90)
    x = int((rx - _X_MIN) * 240 / (_X_MAX - _X_MIN))
    y = int((ry - _Y_MIN) * 320 / (_Y_MAX - _Y_MIN))
    return clamp(x, 0, 239), clamp(y, 0, 319), rx, ry, z1


grp = displayio.Group()
bm = displayio.Bitmap(240, 320, 1)
pal = displayio.Palette(1)
pal[0] = 0x000000
grp.append(displayio.TileGrid(bm, pixel_shader=pal))

info = label.Label(terminalio.FONT, text="Tippe irgendwo...", color=0xFFFF00, scale=2)
info.anchor_point = (0.5, 0.3)
info.anchored_position = (120, 100)
grp.append(info)

raw_lbl = label.Label(terminalio.FONT, text="", color=0x8888ff, scale=1)
raw_lbl.anchor_point = (0.5, 0.5)
raw_lbl.anchored_position = (120, 180)
grp.append(raw_lbl)

screen_lbl = label.Label(terminalio.FONT, text="", color=0x00ff88, scale=1)
screen_lbl.anchor_point = (0.5, 0.5)
screen_lbl.anchored_position = (120, 200)
grp.append(screen_lbl)

tft.root_group = grp
tft.refresh()

while True:
    pos = read_pos()
    if pos:
        sx, sy, rx, ry, z = pos
        info.text = f"Z1={z}"
        raw_lbl.text = f"raw X={rx} Y={ry}"
        screen_lbl.text = f"screen x={sx} y={sy}"
        tft.refresh()
        time.sleep(0.1)
