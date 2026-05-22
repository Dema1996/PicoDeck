# Repository Guidelines

## Project Structure & Module Organization
This repository is a small CircuitPython firmware project for a Raspberry Pi Pico 2 W macro deck.

- `code.py`: main application entry point; contains LCD setup, input handling, menu state, and HID actions.
- `lib/`: bundled CircuitPython dependencies copied to the device, including `adafruit_character_lcd` and `adafruit_hid`.
- `sd/`: placeholder for SD card content or future runtime assets.
- `settings.toml`: optional CircuitPython configuration values.
- `README.md`: hardware wiring, setup notes, and feature scope.

Keep new firmware logic in `code.py` unless the file becomes difficult to maintain; at that point, split reusable helpers into `lib/`-style modules.

## Build, Test, and Development Commands
There is no local build step. Development is a copy-to-device workflow.

- `cp code.py /Volumes/CIRCUITPY/`: deploy the main script to the board.
- `cp actions.py /Volumes/CIRCUITPY/`, `cp display.py /Volumes/CIRCUITPY/`, `cp persistence.py /Volumes/CIRCUITPY/`, etc.: deploy any changed firmware modules after editing them.
- `cp -R lib /Volumes/CIRCUITPY/`: deploy bundled dependencies.
- `screen /dev/tty.usbmodem* 115200`: open the CircuitPython serial console for logs and tracebacks.
- `git status` and `git diff`: review firmware changes before deploy.

Adjust the `CIRCUITPY` mount path for your machine.

When code files are changed in this repo, do not stop at editing the local workspace. Copy every changed firmware file to the mounted `CIRCUITPY` device as part of completing the task, unless the user explicitly asks not to deploy.

## Coding Style & Naming Conventions
Use Python with 4-space indentation and keep the existing style in `code.py`.

- Prefer `snake_case` for variables and functions such as `handle_encoder_button`.
- Keep menu definitions as dictionaries/lists with explicit keys like `label`, `submenu`, and `action`.
- Use short comments only where hardware behavior or debounce logic is not obvious.
- Stay ASCII unless hardware text or user-facing labels require otherwise.

## Testing Guidelines
There is currently no automated test suite. Validate changes on hardware.

- Boot the board and confirm the LCD renders correctly.
- Exercise every affected button and encoder path.
- Verify USB HID shortcuts on the target host OS.
- When adding menu items, test navigation wraparound and back-stack behavior.

Document any manual test steps in the PR when behavior changes.

## Commit & Pull Request Guidelines
Recent commits use short, descriptive subjects, for example: `Better menu and back button`.

- Write commit messages in imperative style and keep them specific to one change.
- PRs should include a concise summary, hardware impact, manual test notes, and photos or video if LCD/menu behavior changed.
- Link related issues or planned features when relevant.
