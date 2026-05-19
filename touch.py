import board
import digitalio
from display import spi

# Calibration: CMD_X (0xD0) is the physical vertical axis on this display,
# CMD_Y (0x90) is the physical horizontal axis — so they are swapped below.
# _X_MIN/_X_MAX calibrate screen-x from CMD_Y raw values.
# _Y_MIN/_Y_MAX calibrate screen-y from CMD_X raw values.
_X_MIN = 3564
_X_MAX = 515
_Y_MIN = 3760
_Y_MAX = 538
_W = 240
_H = 320

_TOUCH_Z_THRESHOLD = 200  # Z1 value above this = screen is pressed

_cs = digitalio.DigitalInOut(board.GP17)
_cs.direction = digitalio.Direction.OUTPUT
_cs.value = True

# XPT2046 command bytes (12-bit differential)
_CMD_X  = 0xD0
_CMD_Y  = 0x90
_CMD_Z1 = 0xB0


def _read_raw(command):
    buf = bytearray(3)
    _cs.value = False
    while not spi.try_lock():
        pass
    try:
        spi.configure(baudrate=1_000_000, phase=0, polarity=0)
        spi.write_readinto(bytes([command, 0, 0]), buf)
    finally:
        spi.unlock()
    _cs.value = True
    return ((buf[1] << 8) | buf[2]) >> 3


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def read_position():
    """Returns (x, y) in screen coordinates if touched, else None."""
    if _read_raw(_CMD_Z1) < _TOUCH_Z_THRESHOLD:
        return None
    raw_horiz = _read_raw(_CMD_Y)  # CMD_Y = physical horizontal = screen X
    raw_vert  = _read_raw(_CMD_X)  # CMD_X = physical vertical  = screen Y
    x = int((raw_horiz - _X_MIN) * _W / (_X_MAX - _X_MIN))
    y = int((raw_vert  - _Y_MIN) * _H / (_Y_MAX - _Y_MIN))
    return _clamp(x, 0, _W - 1), _clamp(y, 0, _H - 1)
