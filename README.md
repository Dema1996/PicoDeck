# PicoDeck

DIY-Macro-Pad auf Basis eines Raspberry Pi Pico 2 W mit 2,4" TFT-Touchdisplay, 5 Hardware-Buttons und einem Rotary Encoder. Steuert macOS per USB-HID und bietet ein eingebettetes Web-UI über WiFi.

## Hardware

| Komponente | Details |
|---|---|
| Controller | Raspberry Pi Pico 2 W (RP2350, CYW43439) |
| Display | AZDelivery 2,4" ILI9341 SPI, 240×320 px, Portrait |
| Touch | XPT2046 (auf gleichem Board wie Display) |
| Buttons | 5× taktiler Taster (INPUT\_PULLUP, gedrückt = LOW) |
| Encoder | Rotary Encoder mit Push-Button (KY-040 o.ä.) |
| SD-Karte | microSD via SPI (optional) |

### Pinbelegung

| Funktion | Pin |
|---|---|
| TFT SCK / MOSI / MISO | GP2 / GP3 / GP4 |
| TFT CS / D/C / RESET | GP5 / GP6 / GP7 |
| btn\_back / btn\_up / btn\_down / btn\_select | GP8 – GP11 |
| Encoder CLK / DT / SW | GP12 / GP13 / GP14 |
| TFT Backlight (PWM) | GP15 |
| btn\_favorite | GP16 |
| Touch CS / IRQ | GP17 / GP18 |
| SD CS | GP22 |

> **Touch-Achsen-Quirk:** Der XPT2046 auf diesem Board hat vertauscht gemeldete Achsen — CMD\_X (0xD0) ist physisch die Y-Achse. `touch.py` kompensiert das.

## Features

### Firmware
- Matrix-Boot-Animation mit „PicoDeck"-Titeloverlay
- Vollständig deutsches Menüsystem (7 sichtbare Einträge, Scrolling für lange Labels)
- USB-HID: Tastatur-Shortcuts und Media-Tasten (macOS)
- 3 unabhängige Profile (`Default`, `Coding`, `Media`) mit eigenen Button-Belegungen
- Persistenz in `microcontroller.nvm` (1 KB, JSON-Schema)

### Eingabe
- 5 Hardware-Buttons: kurzer Druck → Aktion, langer Druck (≥ 1 s) → aktuellen Menüpunkt auf Button mappen
- Rotary Encoder: Modi Navigate / Lautstärke / Helligkeit / Mac-Helligkeit
- Langer Encoder-Druck: zurück / Modus verlassen
- Touchscreen-Navigation

### Display
- Menü mit farbigem Header (aktives Profil + Encoder-Modus)
- Bildschirmschoner nach konfigurierbarem Timeout (15 s / 30 s / 1 min / 5 min / aus): Uhrzeit, Datum, scrollender Track-Titel, Profil, WiFi-Info, Signalstärken-Balken (Bitmap)
- PWM-Helligkeitsregelung

### WiFi
- STA-Modus (Heimnetz) oder AP-Modus (`PicoDeck` / `picodeck1`)
- NTP-Zeitsync: Gateway zuerst (FRITZ!Box), dann Pool-Server, HTTP-Fallback
- RSSI via `start_scanning_networks()` (da `ap_info.rssi` auf dem CYW43439 nicht implementiert)

### Web-UI (`http://<IP>/`)
- Button-Mapping pro Profil
- Einstellungen: Bildschirmschoner-Timeout, Helligkeit, Encoder-Modus/-Richtung/-Speed, Hold-Zeit
- Live Display-Vorschau (polling `/status` alle 1 s, gerendert als HTML-Mockup)
- WiFi-Anmeldedaten setzen inkl. Neustart-Flow
- Speichern-Bestätigung mit ✓-Seite und Auto-Redirect

### Track-Title-Endpoint
```bash
curl -X POST http://<IP>/track -d "title=Mein+Song"
```
Der Titel scrollt automatisch im Screensaver.

## Projektstruktur

```
PicoDeck/
├── code.py          # Haupt-Loop, Hardware-Init, Input-Handler
├── state.py         # Globaler Zustand (Profile, Encoder, Timeouts …)
├── menus.py         # Menü-Definitionen, Label-Formatierung
├── display.py       # displayio-Gruppen, draw_menu(), Screensaver-Renderer
├── actions.py       # USB-HID-Dispatch, Encoder-Modus-Aktionen
├── persistence.py   # NVM lesen/schreiben, Button-Mappings, Profile
├── screensaver.py   # Screensaver-Logik, RSSI-Scan, Scroll
├── boot_anim.py     # Matrix-Boot-Animation
├── ble_hid.py       # BLE-HID-Stub (inaktiv, s. u.)
├── touch.py         # XPT2046-Treiber, Kalibrierung, Achsentausch
├── sdcard.py        # SD-Mount
├── wifi_server.py   # HTTP-Server, NTP, Web-UI, /track, /status, /js
├── lib/
│   ├── adafruit_ble/
│   ├── adafruit_display_text/
│   ├── adafruit_hid/
│   └── adafruit_ili9341.mpy
└── README.md
```

## Entwicklung

```bash
cp <datei>.py /Volumes/CIRCUITPY/<datei>.py   # Datei deployen
screen /dev/tty.usbmodem* 115200              # Serielle Konsole
```

Der Pico startet automatisch neu wenn `code.py` geändert wird.

## Persistenz (NVM-Schema)

```json
{
  "current_profile": "default",
  "profiles": {
    "default":  { "back": "…", "up": "…", "down": "…", "select": "…", "favorite": "…" },
    "coding":   { … },
    "media":    { … }
  },
  "wifi_ssid": "…",
  "wifi_password": "…"
}
```

Maximalgröße: 1024 Byte. Einstellungen wie Timeout und Encoder-Modus sind flüchtig (Reset bei Neustart).

## Bekannte Einschränkungen

- **BLE nicht verfügbar**: CircuitPython hat noch keinen nativen CYW43439-BLE-Support (offenes Issue seit 2023, kein ETA). `ble_hid.py` ist als Platzhalter vorhanden und scheitert graceful mit `active = False`.
- `terminalio.FONT` unterstützt Latin-1 (inkl. Umlaute), aber kein Arabisch/CJK.
- NVM-Persistenz ist auf 1 KB begrenzt — zu viele Profile oder lange SSIDs können die Grenze sprengen.

## Roadmap

### Kurzfristig
- [ ] NVM-Persistenz für Laufzeiteinstellungen (Timeout, Encoder-Modus, Helligkeit)
- [ ] Weitere Aktionen und Profile
- [ ] Web-UI: Profil-Label bearbeiten

### Mittelfristig — Kabellos + Akku
Ziel: vollständig kabelloses Betrieb. Benötigt:

**Hardware:**
- LiPo-Akku 1000–2000 mAh (JST-Stecker)
- TP4056-Modul mit Schutzschaltung (Laden per USB → VSYS des Pico)
- Adafruit AirLift Breakout (ESP32-NINA, SPI) als HCI-BLE-Adapter
- Spannungsteiler (2× Widerstand) an GP26 für Akkustand-ADC
- Ein-/Aus-Schalter

**Software:**
- `boot.py`: AirLift als `_bleio`-HCI-Adapter registrieren
- `ble_hid.py`: SPI-HCI-Init statt nativer Adapter
- USB-Erkennung (`supervisor.runtime.usb_connected`): USB vorhanden → USB HID, sonst → BLE HID
- Akkustand lesen (GP26-ADC) + Anzeige im Screensaver und Web-UI
- Energiesparmodus bei niedrigem Akkustand

> **Warum kein MicroPython?** MicroPython hat zwar CYW43439-BLE, aber kein fertiges USB-HID. Sobald CircuitPython native BLE-Unterstützung für den CYW43439 einführt, wird `ble_hid.py` automatisch funktionieren.

### Langfristig
- [ ] MIDI-Unterstützung (USB MIDI + BLE MIDI)
- [ ] OTA-Firmware-Update über Web-UI
- [ ] Host-Erkennung (macOS / Windows / Linux → automatisch passendes Profil)

---

MIT License
