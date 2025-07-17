# Travelbot Flasher

This project provides a Python-based application to flash a Samsung Galaxy J3 (SM-J320FN) with a minimal LineageOS ROM. The goal is to repurpose the device as a lightweight AI travel companion.

## Features
- Detects if the phone is connected via ADB
- Ensures `adb` and `fastboot` binaries are available (downloads Android platform tools locally if missing)
- Downloads the required TWRP recovery and LineageOS build
- Flashes TWRP and LineageOS automatically
- Optionally installs Magisk for root and a custom APK
- Logs actions to `flasher.log`

## Directory Structure
- `scripts/` – optional helper scripts or recovery tools
- `images/` – logo or branding assets
- `flash.py` – main application
- `requirements.txt` – Python dependencies

## Usage
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the flasher:
   ```bash
   python flash.py --flash --apk path/to/app.apk --root
   ```

The script guides you through each step and reports progress in the terminal. All output is also written to `flasher.log`.
