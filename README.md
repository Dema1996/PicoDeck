# PicoDeck

DIY-Macro-Deck auf Basis eines Raspberry Pi Pico 2 W mit 16x2-LCD, Buttons, Rotary Encoder und USB-HID fuer macOS-orientierte Shortcuts.

## Status

Die Firmware laeuft direkt aus `code.py` und bietet aktuell:

- Menues fuer `Media`, `System`, `Coding`, `Encoder`, `Buttons` und `Profiles`
- frei belegbare Hardware-Buttons auf `GP8`, `GP9`, `GP10`, `GP11`, `GP16`
- persistente Button-Mappings in `microcontroller.nvm`
- mehrere Profile mit eigenen Button-Belegungen
- Encoder-Modi fuer Navigation, Lautstaerke und Bildschirmhelligkeit

## Projektstruktur

```text
PicoDeck/
├── code.py
├── lib/
│   ├── adafruit_character_lcd/
│   └── adafruit_hid/
├── sd/
├── settings.toml
├── README.md
└── AGENTS.md
```

## Hardware

- Raspberry Pi Pico 2 W
- LCD 1602A im 4-Bit-Modus
- 5 Taster mit `INPUT_PULLUP`
- Rotary Encoder mit Push-Button, z. B. KY-040

### Pinbelegung

| Funktion | Pico Pin |
|---|---|
| LCD RS / E | GP2 / GP3 |
| LCD D4-D7 | GP4-GP7 |
| Button 1-4 | GP8-GP11 |
| Encoder CLK / DT / SW | GP12 / GP13 / GP14 |
| Zusatz-Button | GP16 |

Button-Logik: gedrueckt = `LOW`, nicht gedrueckt = `HIGH`.

## Bedienung

### Encoder

- drehen im Modus `Navigate`: Menue-Navigation
- kurzer Druck im Modus `Navigate`: Menuepunkt ausfuehren
- langer Druck im Modus `Navigate`: `Zurueck`
- Modus `Volume`: drehen aendert Lautstaerke
- Modus `Brightness`: drehen aendert Bildschirmhelligkeit
- langer Druck in `Volume` oder `Brightness`: zurueck auf `Navigate`

### Hardware-Buttons

- kurzer Druck: aktuell gemappte Aktion ausfuehren
- langer Druck auf einem Menue-Makro: dieses Makro auf genau diesen Button mappen

### Buttons-Menue

- zeigt die aktuelle Belegung jeder Taste direkt in der Liste
- Detailansicht pro Taste zum direkten Remappen
- `Reset Taste` fuer einzelne Taste
- `Reset Default` fuer das ganze aktuelle Profil

### Profiles-Menue

- `Default`
- `Coding`
- `Media`

Jedes Profil hat eigene persistente Button-Belegungen.

## Aktuelle Aktionen

### Media

- `play_pause`
- `stop`
- `mute`
- `previous_track`
- `next_track`
- `volume_up`
- `volume_down`

### System

- `spotlight`
- `app_switcher`
- `previous_app`
- `mission_control`
- `lock_mac`
- `show_desktop`

### Coding

- `open_vscode`
- `command_palette`
- `toggle_terminal`
- `format_document`
- `screenshot`

## Persistenz

Button-Mappings werden nicht im CIRCUITPY-Dateisystem gespeichert, sondern in `microcontroller.nvm`. Dadurch bleiben die Belegungen ueber Reboots erhalten, ohne Schreibprobleme auf dem USB-Massenspeicher zu verursachen.

## Setup

1. CircuitPython fuer `raspberry_pi_pico2_w` installieren:
   https://circuitpython.org/board/raspberry_pi_pico2_w/
2. `code.py` nach `CIRCUITPY/` kopieren.
3. Den Ordner `lib/` nach `CIRCUITPY/lib/` kopieren.
4. Optional Konfiguration in `settings.toml` ablegen.

Der Pico startet nach dem Kopieren automatisch neu.

## Entwicklung

- Serielle Konsole: `screen /dev/tty.usbmodem* 115200`
- Deployment: `cp code.py /Volumes/CIRCUITPY/code.py`
- Bibliotheken bleiben vendorisiert unter `lib/`
- Der aktuelle Stand wird bewusst noch in einer Datei gehalten; mittelfristig lohnt sich eine Aufteilung in Module

## Naechste sinnvolle Schritte

- mehr robuste Coding-Makros
- host-spezifische Shortcut-Profile
- Menue-/Action-Logik in Module aufteilen
- manuelle Hardware-Testmatrix dokumentieren

---

# Lizenz

MIT
