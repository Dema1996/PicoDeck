import board
import sdcardio
import storage
from display import spi

MOUNT_POINT = "/sd"
mounted = False


def mount():
    """Mount the SD card at /sd. Returns True on success."""
    global mounted
    try:
        sd = sdcardio.SDCard(spi, board.GP22)
        vfs = storage.VfsFat(sd)
        storage.mount(vfs, MOUNT_POINT)
        mounted = True
    except Exception:
        mounted = False
    return mounted
