import displayio
import terminalio
from adafruit_display_text import label
import display

_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-=#@"


class BootAnim:
    """Matrix rain boot animation that stays active during the entire startup."""

    def __init__(self):
        import random
        from display import _W, _H

        _N = _W // 16
        self._N = _N
        self._H = _H

        grp = displayio.Group()

        bg_bm = displayio.Bitmap(_W, _H, 1)
        bg_pal = displayio.Palette(1)
        bg_pal[0] = 0x000000
        grp.append(displayio.TileGrid(bg_bm, pixel_shader=bg_pal))

        col_x = [i * (_W // _N) for i in range(_N)]
        self._speeds = [random.randint(10, 24) for _ in range(_N)]
        self._ys = [random.randint(-_H, 0) for _ in range(_N)]

        self._streams = []
        for i in range(_N):
            lbl = label.Label(terminalio.FONT, text="@", color=0x00ff41, scale=1)
            lbl.anchor_point = (0.0, 0.0)
            lbl.anchored_position = (col_x[i], self._ys[i])
            grp.append(lbl)
            self._streams.append(lbl)

        title_lbl = label.Label(terminalio.FONT, text="PicoDeck", color=0xffd700,
                                scale=3, background_color=0x000000)
        title_lbl.anchor_point = (0.5, 0.5)
        title_lbl.anchored_position = (_W // 2, _H // 2 - 24)
        grp.append(title_lbl)

        self._status_lbl = label.Label(terminalio.FONT, text="Startet...", color=0x00cc33,
                                       scale=2, background_color=0x000000)
        self._status_lbl.anchor_point = (0.5, 0.5)
        self._status_lbl.anchored_position = (_W // 2, _H // 2 + 44)
        grp.append(self._status_lbl)

        self._col_x = col_x
        self._frame = 0

        display.tft.root_group = grp
        self.tick()

    def set_status(self, text):
        """Update the status label and refresh immediately."""
        self._status_lbl.text = text
        display.tft.refresh()

    def tick(self, n=1):
        """Advance n animation frames."""
        import random
        for _ in range(n):
            for i in range(self._N):
                self._ys[i] += self._speeds[i]
                if self._ys[i] > self._H:
                    self._ys[i] = random.randint(-150, -20)
                    self._speeds[i] = random.randint(10, 24)
                self._streams[i].anchored_position = (self._col_x[i], self._ys[i])
                self._streams[i].text = _CHARS[(self._frame + i * 7) % len(_CHARS)]
            self._frame += 1
            display.tft.refresh()
