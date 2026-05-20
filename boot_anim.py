import displayio
import terminalio
from adafruit_display_text import label
import time
import display

_W, _H = 240, 320
_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-=#@"
_N = 20  # columns at scale=1 → dense rain


def play(duration=2.5):
    import random

    grp = displayio.Group()

    bg_bm = displayio.Bitmap(_W, _H, 1)
    bg_pal = displayio.Palette(1)
    bg_pal[0] = 0x000000
    grp.append(displayio.TileGrid(bg_bm, pixel_shader=bg_pal))

    col_x = [i * (_W // _N) for i in range(_N)]
    speeds = [random.randint(10, 24) for _ in range(_N)]
    ys = [random.randint(-_H, 0) for _ in range(_N)]

    streams = []
    for i in range(_N):
        lbl = label.Label(terminalio.FONT, text="@", color=0x00ff41, scale=1)
        lbl.anchor_point = (0.0, 0.0)
        lbl.anchored_position = (col_x[i], ys[i])
        grp.append(lbl)
        streams.append(lbl)

    # Solid background_color so rain chars cannot bleed through the text
    title_lbl = label.Label(terminalio.FONT, text="PicoDeck", color=0xffd700,
                            scale=3, background_color=0x000000)
    title_lbl.anchor_point = (0.5, 0.5)
    title_lbl.anchored_position = (_W // 2, _H // 2 - 24)
    grp.append(title_lbl)

    sub_lbl = label.Label(terminalio.FONT, text="Startet...", color=0x00cc33,
                          scale=2, background_color=0x000000)
    sub_lbl.anchor_point = (0.5, 0.5)
    sub_lbl.anchored_position = (_W // 2, _H // 2 + 44)
    grp.append(sub_lbl)

    display.tft.root_group = grp

    start = time.monotonic()
    tick = 0
    while time.monotonic() - start < duration:
        for i in range(_N):
            ys[i] += speeds[i]
            if ys[i] > _H:
                ys[i] = random.randint(-150, -20)
                speeds[i] = random.randint(10, 24)
            streams[i].anchored_position = (col_x[i], ys[i])
            streams[i].text = _CHARS[(tick + i * 7) % len(_CHARS)]
        tick += 1
        display.tft.refresh()
