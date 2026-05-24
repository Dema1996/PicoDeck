# PicoDeck Wiring

TFT und Touch teilen sich **SPI0** auf GP2–GP4. Die SD-Karte hat einen eigenen **SPI1**-Bus auf GP26–GP28.  
Buttons verwenden `INPUT_PULLUP` — gedrückt = LOW.

## Pinbelegung

| Pin | GPIO | Funktion | Komponente |
|---|---|---|---|
| Pin 4 | GP2 | SPI0 SCK | TFT / Touch (shared) |
| Pin 5 | GP3 | SPI0 MOSI | TFT / Touch (shared) |
| Pin 6 | GP4 | SPI0 MISO | TFT / Touch (shared) |
| Pin 7 | GP5 | TFT CS | ILI9341 |
| Pin 8 | GP6 | TFT D/C | ILI9341 |
| Pin 9 | GP7 | TFT RESET | ILI9341 |
| Pin 10 | GP8 | F1 | Macro Button |
| Pin 11 | GP9 | F2 | Macro Button |
| Pin 13 | GP10 | F3 | Macro Button |
| Pin 14 | GP11 | F4 | Macro Button |
| Pin 15 | GP12 | Encoder CLK | Rotary Encoder |
| Pin 16 | GP13 | Encoder DT | Rotary Encoder |
| Pin 17 | GP14 | Encoder SW | Rotary Encoder (Push) |
| Pin 18 | GP15 | TFT Backlight (PWM) | ILI9341 |
| Pin 19 | GP16 | F5 | Macro Button |
| Pin 20 | GP17 | Touch CS | XPT2046 |
| Pin 22 | GP18 | Touch IRQ | XPT2046 |
| Pin 23 | GP19 | F6 | Macro Button |
| Pin 26 | GP22 | SD CS | microSD-Modul |
| Pin 28 | GP26 | SPI1 SCK | microSD-Modul |
| Pin 29 | GP27 | SPI1 MOSI | microSD-Modul |
| Pin 31 | GP28 | SPI1 MISO | microSD-Modul |

**Freie GPIOs:** GP0, GP1, GP20, GP21

## Komponenten

### ILI9341 TFT (2,4" 240×320)
| Display-Pin | Pico GPIO |
|---|---|
| SCK | GP2 |
| MOSI | GP3 |
| MISO | GP4 |
| CS | GP5 |
| D/C | GP6 |
| RESET | GP7 |
| LED | GP15 (PWM) |
| VCC | 3.3V |
| GND | GND |

### XPT2046 Touch (auf gleichem Board wie TFT)
| Touch-Pin | Pico GPIO |
|---|---|
| SCK | GP2 (shared mit TFT) |
| MOSI | GP3 (shared mit TFT) |
| MISO | GP4 (shared mit TFT) |
| CS | GP17 |
| IRQ | GP18 |

> **Achsen-Quirk:** CMD_X (0xD0) ist physisch die vertikale Achse, CMD_Y (0x90) die horizontale — entgegen der Kanal-Bezeichnung. `touch.py` kompensiert das. Beide Achsen sind zusätzlich invertiert (MIN > MAX).

### Macro Buttons (F1–F6)
Ein Pin gegen GND, der andere auf den jeweiligen GPIO. Kein externer Pull-Widerstand nötig — `INPUT_PULLUP` aktiv.

| Button | GPIO | GND |
|---|---|---|
| F1 | GP8 | GND |
| F2 | GP9 | GND |
| F3 | GP10 | GND |
| F4 | GP11 | GND |
| F5 | GP16 | GND |
| F6 | GP19 | GND |

### Rotary Encoder (KY-040 o.ä.)
| Encoder-Pin | Pico GPIO |
|---|---|
| CLK | GP12 |
| DT | GP13 |
| SW | GP14 |
| + | 3.3V |
| GND | GND |

### microSD-Modul (SPI1, isoliert von TFT)
| SD-Pin | Pico GPIO |
|---|---|
| SCK | GP26 |
| MOSI | GP27 |
| MISO | GP28 |
| CS | GP22 |
| VCC | 3.3V |
| GND | GND |

> GP28 (MISO) bekommt vor der SPI-Initialisierung kurz einen Software-Pull-Up gesetzt, da der RP2350-Pad-Register den Zustand nach dem Pin-Funktionswechsel beibehält. Siehe `sdcard.py`.
