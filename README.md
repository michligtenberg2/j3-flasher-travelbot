# Travelbot Flasher

This project provides a Python-based application to flash a Samsung Galaxy J3 (SM-J320FN) with a minimal LineageOS ROM. The GUI is built with **PyQt6** and lets you manage the flashing process through simple buttons.

## Features
- Detects if the phone is connected via ADB
- Ensures `adb` and `fastboot` binaries are available (downloads Android platform tools locally if missing)
- Downloads the required TWRP recovery and LineageOS build
- Flashes TWRP and LineageOS automatically
- Optionally flash only TWRP via dedicated button
- Button to install ADB and check for Heimdall
- Extra buttons for rebooting, viewing logs, and clearing the log
- Built-in help window with step-by-step instructions
- Uses a simple ttk theme for a cleaner interface
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
   python flash.py
   ```

The GUI shows progress in a log window and also writes all actions to `flasher.log`.
The interface includes buttons to check devices and tools, flash only the recovery or the full ROM, reboot the phone, view or clear the log file, and open a help window with detailed instructions. When Heimdall is missing on Linux, the application can run `sudo apt install heimdall-flash` for you after confirmation.

## Preparing the Phone

1. Enable **USB debugging** and **OEM unlock** in the Developer Options menu.
2. Power off the phone, then hold **Power + Home + Volume Down** to enter **Download Mode**. Press **Volume Up** to continue.
3. Connect the device via USB before starting the flash process.

## Rooting with Magisk

To obtain root access on the Galaxy J3 (SM-J320FN) you need TWRP installed first.
From the flasher tool open the **🔓 Geef Root-toegang** tab and use the
**Download Magisk.zip** button to fetch `Magisk-v23.0.zip` if you don't already
have it. Push the zip to the phone with **Flash Magisk via TWRP** and then boot
to TWRP manually. In TWRP choose <code>Install → Magisk-v23.0.zip</code> and
flash the file. Reboot Android and verify the root status using the
"Controleer Rootstatus" button or by running `adb shell su -v`.

