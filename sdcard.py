import board
import busio
import digitalio
import storage
import time
import console_log
from adafruit_sdcard import SDCard as _SDCard

MOUNT_POINT = "/sd"
mounted = False
last_error = ""
_sd_obj = None

# Enable pull-up on MISO before SPI takes the pin; RP2350 pad register persists after pin-function change
_miso_pu = digitalio.DigitalInOut(board.GP28)
_miso_pu.direction = digitalio.Direction.INPUT
_miso_pu.pull = digitalio.Pull.UP
_miso_pu.deinit()

# Dedicated SPI1 bus — isolated from the display's SPI0 (GP2/3/4)
_spi = busio.SPI(clock=board.GP26, MOSI=board.GP27, MISO=board.GP28)

# CS pin as DigitalInOut (adafruit_sdcard expects DigitalInOut, not raw Pin)
_cs = digitalio.DigitalInOut(board.GP22)
_cs.direction = digitalio.Direction.OUTPUT
_cs.value = True  # deselected


def mount():
    """Mount the SD card at /sd. Returns True on success."""
    global mounted, last_error, _sd_obj
    for attempt in range(2):
        last_error = ""
        if _sd_obj is not None:
            try:
                storage.umount(MOUNT_POINT)
            except Exception:
                pass
            _sd_obj = None
        if attempt:
            time.sleep(1.0)
        try:
            sd = _SDCard(_spi, _cs)
            vfs = storage.VfsFat(sd)
            storage.mount(vfs, MOUNT_POINT)
            _sd_obj = sd
            mounted = True
            return True
        except Exception as e:
            last_error = str(e)
            console_log.log("SD attempt " + str(attempt + 1) + " failed: " + last_error)
    mounted = False
    return False
