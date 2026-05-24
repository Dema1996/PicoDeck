# Konzept: Button-Matrix

Theoretische Grundlage für eine spätere Erweiterung des PicoDeck auf mehr Macro-Buttons ohne proportional mehr GPIO-Pins zu verbrauchen.

## Problem mit direktem GPIO-Mapping

Aktuell belegt jeder Button einen eigenen GPIO-Pin (1:1). Bei 6 Buttons sind das 6 Pins. Mehr Buttons bedeuten mehr Pins — irgendwann ist das Limit erreicht.

**Aktuell belegte Button-Pins:**

| Button | GPIO |
|---|---|
| F1 | GP8 |
| F2 | GP9 |
| F3 | GP10 |
| F4 | GP11 |
| F5 | GP16 |
| F6 | GP19 |

Noch freie GPIOs: GP0, GP1, GP20, GP21, GP26, GP27, GP28

## Wie eine Button-Matrix funktioniert

Buttons werden in einem Raster aus **Rows (Zeilen)** und **Columns (Spalten)** angeordnet. Der Controller setzt eine Row nach der anderen auf LOW (Scanning) und liest gleichzeitig alle Columns aus. Ein gedrückter Button schließt den Stromkreis an genau einem Row/Col-Kreuzungspunkt.

```
        Col0  Col1  Col2  Col3
Row0 →  [F1]  [F2]  [F3]  [F4]
Row1 →  [F5]  [F6]  [F7]  [F8]
Row2 →  [F9]  [F10] [F11] [F12]
```

**Formel:** N Rows + M Cols = **N×M Buttons** mit nur **N+M Pins**

### Vergleich möglicher Konfigurationen

| Konfiguration | Buttons | Pins | Ersparnis |
|---|---|---|---|
| Direkt (aktuell) | 6 | 6 | Baseline |
| 2×4 Matrix | **8** | 6 | Gleiche Pins, 2 mehr Buttons |
| 3×3 Matrix | **9** | 6 | Gleiche Pins, 3 mehr Buttons |
| 3×4 Matrix | **12** | 7 | 1 Pin mehr, doppelt so viele Buttons |
| 4×4 Matrix | **16** | 8 | 2 Pins mehr, fast 3× so viele Buttons |

## Ghosting und Dioden

Ohne Gegenmaßnahmen entsteht bei gleichzeitig gedrückten Buttons **Ghosting**: der Controller erkennt Buttons als gedrückt, die es nicht sind. Ursache ist ein Rückstrom über benachbarte Leitungen.

**Lösung:** Eine **Diode (1N4148)** in Reihe mit jedem Button. Die Diode sperrt den Rückstrom und verhindert Ghosting vollständig.

```
Row ──┤>├── Button ── Col
         1N4148
```

Das ist der einzige hardware-seitige Mehraufwand gegenüber der direkten Verdrahtung.

## CircuitPython-Unterstützung

CircuitPython hat `keypad.KeyMatrix` eingebaut — kein externer Treiber nötig:

```python
import keypad

km = keypad.KeyMatrix(
    row_pins=(board.GP8, board.GP9, board.GP10),
    column_pins=(board.GP20, board.GP21, board.GP26, board.GP27),
)

while True:
    event = km.events.get()
    if event:
        if event.pressed:
            print(f"Button {event.key_number} gedrückt")
        elif event.released:
            print(f"Button {event.key_number} losgelassen")
```

`KeyMatrix` übernimmt das Scanning und liefert Key-Events (pressed/released). Das passt gut zur bestehenden Hold-Logik in `handle_macro_button()`.

## Anpassungen bei Umsetzung

### Hardware
- Dioden (1N4148) auf jeden Button
- Neuverkabelung als Rows/Cols statt Einzelpins

### Software (`code.py`, `state.py`)
- `setup_button()` und direktes `digitalio`-Lesen entfällt
- `handle_macro_button()` wird auf Event-basiertes Scanning umgestellt
- Hold-Erkennung bleibt konzeptuell gleich: Timestamp beim `event.pressed` setzen, beim `event.released` auswerten
- `state.button_order` und `state.button_hold_state` bleiben verwendbar, nur die Anzahl der Einträge wächst

## Empfehlung

Für die aktuelle Platine mit 6 Buttons lohnt der Umbau nicht. Eine Matrix wird interessant sobald **mehr als ~8 Buttons** gewünscht sind und keine freien GPIO-Pins mehr zur Verfügung stehen — etwa bei einer v2-Platine mit erweitertem Layout.
