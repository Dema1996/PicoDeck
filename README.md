# PicoDeck

DIY Macro Deck auf Basis eines Raspberry Pi Pico 2 W.

## Features

- LCD 1602A im 4-Bit-Modus
- USB HID für macOS
- 4 Navigationstasten
- Rotary Encoder
- Menüsystem auf LCD
- Erweiterbar für RGB, OLED, WLAN und Bluetooth

---

# Hardware

## Verwendete Komponenten

- Raspberry Pi Pico 2 W
- LCD 1602A
- 4 Buttons
- Rotary Encoder (KY-040 kompatibel)
- Breadboard
- Jumper Kabel

---

# Pinbelegung

## LCD 1602A (4-Bit-Modus)

| LCD Signal | Pico Pin |
|---|---|
| RS | GP2 |
| E | GP3 |
| D4 | GP4 |
| D5 | GP5 |
| D6 | GP6 |
| D7 | GP7 |

## LCD Stromversorgung

| LCD Pin | Verbindung |
|---|---|
| VSS | GND |
| VDD | 5V oder VBUS |
| VO | Potentiometer Mitte |
| A | 5V über Widerstand |
| K | GND |

---

## Buttons

Alle Buttons verwenden:

```text
INPUT_PULLUP
```

Logik:

```text
gedrückt = LOW (0)
nicht gedrückt = HIGH (1)
```

| Funktion | Pico Pin |
|---|---|
| Back | GP8 |
| Up | GP9 |
| Down | GP10 |
| Select | GP11 |

Verdrahtung:

```text
GPIO ↔ Button ↔ GND
```

---

## Rotary Encoder

| Encoder Pin | Pico Pin |
|---|---|
| CLK | GP12 |
| DT | GP13 |
| SW | GP14 |
| + | 3V3 |
| GND | GND |

### Funktionen

| Aktion | Funktion |
|---|---|
| Drehen | Menü Navigation |
| Drücken | Aktion ausführen |

---

# USB

| Verbindung | Zweck |
|---|---|
| USB → MacBook | Strom + USB-HID |

---

# GPIO Übersicht

| GPIO | Funktion |
|---|---|
| GP2 | LCD RS |
| GP3 | LCD E |
| GP4 | LCD D4 |
| GP5 | LCD D5 |
| GP6 | LCD D6 |
| GP7 | LCD D7 |
| GP8 | Button Back |
| GP9 | Button Up |
| GP10 | Button Down |
| GP11 | Button Select |
| GP12 | Encoder CLK |
| GP13 | Encoder DT |
| GP14 | Encoder SW |

---

# Projektstruktur

```text
PicoDeck/
├── README.md
├── src/
│   └── code.py
├── docs/
│   └── wiring.md
└── hardware/
```

---

# Architektur

```text
Buttons / Encoder
        ↓
Menu System
        ↓
LCD Rendering
        ↓
Action Engine
        ↓
USB HID
        ↓
macOS
```

---

# Geplante Features

- Untermenüs
- Lautstärke-Steuerung
- Spotify Integration
- App-spezifische Profile
- OLED Support
- RGB LEDs
- WLAN API
- Bluetooth HID

---

# Setup

## CircuitPython installieren

Download:

https://circuitpython.org/board/raspberry_pi_pico2_w/

UF2-Datei auf den Pico kopieren.

---

## Benötigte Libraries

Nach `CIRCUITPY/lib/` kopieren:

```text
adafruit_character_lcd
adafruit_hid
```

Library Bundle:

https://circuitpython.org/libraries

---

# Start

Datei:

```text
code.py
```

nach:

```text
CIRCUITPY/
```

kopieren.

Der Pico startet automatisch neu.

---

# Lizenz

MIT
