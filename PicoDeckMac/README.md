# PicoDeckMac

Native macOS-App als serielle Alternative zur Web-UI des PicoDeck.

## Stand

Das aktuelle MVP kann:

- seriellen Pico-Port auswaehlen und verbinden
- Live-Status des Menues pollen
- Navigation und Makro-Buttons ausloesen
- Profile wechseln, anlegen und loeschen
- Button-Mappings setzen
- Laufzeiteinstellungen seriell speichern
- WLAN-Zugangsdaten seriell speichern
- rohe JSON-/Log-Zeilen anzeigen

## Start

1. `PicoDeckMac/Package.swift` in Xcode oeffnen
2. Executable `PicoDeckMac` auswaehlen
3. App starten
4. den passenden `/dev/cu.usbmodem...`-Port waehlen
5. `Verbinden` klicken

## Hinweis

Der Pico muss die serielle JSON-Steuerung aus der angepassten Firmware in `code.py` bereits geladen haben.
