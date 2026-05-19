import time
import board
import digitalio
from display import spi

# Calibration: raw XPT2046 values at screen edges.
# Run a calibration sketch or adjust these until taps line up with the UI.
# Swap X_MIN/X_MAX or Y_MIN/Y_MAX if the axis is inverted.
_X_MIN = 200
_X_MAX = 3800
_Y_MIN = 300
_Y_MAX = 3700

_cs = digitalio.DigitalInOut(board.GP17)
_cs.direction = digitalio.Direction.OUTPUT
_cs.value = True

_irq = digitalio.DigitalInOut(board.GP18)
_irq.direction = digitalio.Direction.INPUT
_irq.pull = digitalio.Pull.UP

# XPT2046 command bytes (12-bit differential, power-down between conversions)
_CMD_X = 0xD0   # S=1, A2-A0=101 (X), MODE=0, SER=0, PD=00
_CMD_Y = 0x90   # S=1, A2-A0=001 (Y), MODE=0, SER=0, PD=00


def is_touched():
    return not _irq.value


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
    return ((buf[1] << 8) | buf[2]) >> 3  # 12-bit result


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def read_position():
    """Returns (x, y) in screen coordinates (0-319, 0-239), or None if not touched."""
    if not is_touched():
        return None
    raw_x = _read_raw(_CMD_X)
    raw_y = _read_raw(_CMD_Y)
    x = int((raw_x - _X_MIN) * 320 / (_X_MAX - _X_MIN))
    y = int((raw_y - _Y_MIN) * 240 / (_Y_MAX - _Y_MIN))
    return _clamp(x, 0, 319), _clamp(y, 0, 239)
