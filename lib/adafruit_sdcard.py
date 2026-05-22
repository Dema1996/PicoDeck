"""
Minimal SD card SPI driver with extended ACMD41 timeout (5 s).
Compatible with storage.VfsFat as a block device.
"""
import time

_CMD_TIMEOUT = 200

_R1_IDLE_STATE = 0x01
_TOKEN_CMD25 = 0xFC
_TOKEN_STOP_TRAN = 0xFD
_TOKEN_DATA = 0xFE


class SDCard:
    def __init__(self, spi, cs, baudrate=1320000):
        self._spi = spi
        self._cs = cs
        self._baudrate = baudrate
        self._buf = bytearray(1)
        self._cmd_buf = bytearray(6)
        self._cdv = 512
        self._init_card()

    def _cmd(self, cmd, arg=0, crc=0, release=True, skip1=False):
        """Send command (CS managed by caller) and return R1."""
        self._cs.value = False
        self._cmd_buf[0] = 0x40 | cmd
        self._cmd_buf[1] = (arg >> 24) & 0xFF
        self._cmd_buf[2] = (arg >> 16) & 0xFF
        self._cmd_buf[3] = (arg >> 8) & 0xFF
        self._cmd_buf[4] = arg & 0xFF
        self._cmd_buf[5] = crc | 0x01
        self._spi.write(self._cmd_buf)
        if skip1:
            self._spi.readinto(self._buf, write_value=0xFF)
        for _ in range(_CMD_TIMEOUT):
            self._spi.readinto(self._buf, write_value=0xFF)
            if not (self._buf[0] & 0x80):  # valid R1 has bit 7 = 0
                r1 = self._buf[0]
                if release:
                    self._cs.value = True
                    self._spi.write(bytes([0xFF]))
                return r1
        if release:
            self._cs.value = True
            self._spi.write(bytes([0xFF]))
        return 0xFF

    def _init_card(self):
        self._cs.value = True
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=100000, phase=0, polarity=0)

        # 640 clock pulses with CS high (Toshiba C4 needs many clocks before CMD0)
        self._spi.write(bytes([0xFF] * 80))

        # CMD0 — software reset, enter SPI mode
        r = self._cmd(0, 0, 0x95)
        if r != _R1_IDLE_STATE:
            self._spi.unlock()
            raise OSError("no card (CMD0 r=%02x)" % r)

        # CMD59 — disable CRC checking
        self._cmd(59, 0, 0x91)

        # CMD8 — check voltage / identify v2
        r = self._cmd(8, 0x000001AA, 0x87, release=False)
        if r != _R1_IDLE_STATE:
            self._cs.value = True
            self._spi.write(bytes([0xFF]))
            self._spi.unlock()
            raise OSError("v1/MMC not supported (CMD8 r=%02x)" % r)
        buf4 = bytearray(4)
        self._spi.readinto(buf4, write_value=0xFF)
        self._cs.value = True
        self._spi.write(bytes([0xFF]))

        # ACMD41 — poll until ready (up to ~2 s); card must return 0x00 within 1 s per spec
        ready = False
        for _ in range(200):
            r55 = self._cmd(55, 0, 0x01)
            r41 = self._cmd(41, 0x40000000, 0x01)
            if r41 == 0x00:
                ready = True
                break
            time.sleep(0.010)
        if not ready:
            self._spi.unlock()
            raise OSError("SD init timeout (ACMD41 r=%02x)" % r41)

        # CMD58 — read OCR, check CCS for SDHC
        r = self._cmd(58, 0, 0x01, release=False)
        self._spi.readinto(buf4, write_value=0xFF)
        self._cs.value = True
        self._spi.write(bytes([0xFF]))
        if buf4[0] & 0x40:
            self._cdv = 1    # SDHC: block-addressed
        else:
            self._cdv = 512  # SDSC: byte-addressed
            self._cmd(16, 512, 0x01)

        self._spi.configure(baudrate=self._baudrate, phase=0, polarity=0)
        self._spi.unlock()

    @property
    def count(self):
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=self._baudrate, phase=0, polarity=0)
        r = self._cmd(9, 0, 0x01, release=False)
        if r != 0x00:
            self._cs.value = True
            self._spi.write(bytes([0xFF]))
            self._spi.unlock()
            return 0
        # Wait for data token
        for _ in range(_CMD_TIMEOUT):
            self._spi.readinto(self._buf, write_value=0xFF)
            if self._buf[0] == _TOKEN_DATA:
                break
        csd = bytearray(16)
        self._spi.readinto(csd, write_value=0xFF)
        self._spi.readinto(self._buf, write_value=0xFF)
        self._spi.readinto(self._buf, write_value=0xFF)
        self._cs.value = True
        self._spi.write(bytes([0xFF]))
        self._spi.unlock()
        if (csd[0] >> 6) == 0b01:
            c_size = ((csd[7] & 0x3F) << 16) | (csd[8] << 8) | csd[9]
            return (c_size + 1) * 1024
        c_size = ((csd[6] & 0x03) << 10) | (csd[7] << 2) | (csd[8] >> 6)
        c_mult = ((csd[9] & 0x03) << 1) | (csd[10] >> 7)
        bl_len = csd[5] & 0x0F
        return (c_size + 1) * (2 ** (c_mult + 2)) * (2 ** bl_len) // 512

    def readblocks(self, n, buf):
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=self._baudrate, phase=0, polarity=0)
        try:
            nblocks = len(buf) // 512
            if nblocks == 1:
                r = self._cmd(17, n * self._cdv, 0x01, release=False)
                if r:
                    raise OSError("CMD17 r=%02x" % r)
                self._wait_token()
                self._spi.readinto(buf, write_value=0xFF)
                self._spi.readinto(self._buf, write_value=0xFF)
                self._spi.readinto(self._buf, write_value=0xFF)
                self._cs.value = True
                self._spi.write(bytes([0xFF]))
            else:
                r = self._cmd(18, n * self._cdv, 0x01, release=False)
                if r:
                    raise OSError("CMD18 r=%02x" % r)
                offset = 0
                for _ in range(nblocks):
                    self._wait_token()
                    self._spi.readinto(memoryview(buf)[offset:offset + 512], write_value=0xFF)
                    self._spi.readinto(self._buf, write_value=0xFF)
                    self._spi.readinto(self._buf, write_value=0xFF)
                    offset += 512
                self._cmd(12, skip1=True)
        finally:
            self._spi.unlock()

    def _wait_token(self):
        for _ in range(_CMD_TIMEOUT):
            self._spi.readinto(self._buf, write_value=0xFF)
            if self._buf[0] == _TOKEN_DATA:
                return
        self._cs.value = True
        raise OSError("data token timeout")

    def writeblocks(self, n, buf):
        while not self._spi.try_lock():
            pass
        self._spi.configure(baudrate=self._baudrate, phase=0, polarity=0)
        try:
            nblocks = len(buf) // 512
            if nblocks == 1:
                r = self._cmd(24, n * self._cdv, 0x01)
                if r:
                    raise OSError("CMD24 r=%02x" % r)
                self._write_block(_TOKEN_DATA, buf, 0)
            else:
                r = self._cmd(25, n * self._cdv, 0x01)
                if r:
                    raise OSError("CMD25 r=%02x" % r)
                for i in range(nblocks):
                    self._write_block(_TOKEN_CMD25, buf, i * 512)
                self._cs.value = False
                self._spi.write(bytes([_TOKEN_STOP_TRAN, 0xFF]))
                self._wait_busy()
                self._cs.value = True
                self._spi.write(bytes([0xFF]))
        finally:
            self._spi.unlock()

    def _write_block(self, token, buf, offset):
        self._cs.value = False
        self._spi.write(bytes([token]))
        self._spi.write(memoryview(buf)[offset:offset + 512])
        self._spi.write(bytes([0xFF, 0xFF]))  # CRC
        self._spi.readinto(self._buf, write_value=0xFF)
        if (self._buf[0] & 0x1F) != 0x05:
            self._cs.value = True
            self._spi.write(bytes([0xFF]))
            raise OSError("write rejected 0x%x" % self._buf[0])
        self._wait_busy()
        self._cs.value = True
        self._spi.write(bytes([0xFF]))

    def _wait_busy(self):
        for _ in range(10000):
            self._spi.readinto(self._buf, write_value=0xFF)
            if self._buf[0] != 0x00:
                return
        raise OSError("write busy timeout")
