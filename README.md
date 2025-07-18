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
- Quick links to the bundled HTML documentation
- Optionally installs Magisk for root and a custom APK
- Logs actions to `flasher.log` with automatic rotation
- Root-tab acties loggen afzonderlijk naar `root.log`

### Root access?

See the [root info](docs/root.html) page for details on when root is useful and why it is optional for Travelbot.
For step-by-step instructions on enabling root, check the [root installation guide](docs/root-install.html).

## Prerequisites

### System Requirements
- **Operating System**: Windows 10/11, Linux (Ubuntu/Debian recommended), or macOS
- **Python**: Version 3.8 or higher
- **USB Port**: Available USB port for device connection
- **Internet Connection**: Required for downloading tools and ROM files

### Device Requirements
- **Samsung Galaxy J3 (2016)** model SM-J320FN
- **Developer Options** enabled
- **USB Debugging** enabled
- **OEM Unlock** enabled
- **Original USB cable** (avoid USB hubs or extension cables)

## Installation

### 1. Clone or Download
```bash
git clone https://github.com/michligtenberg2/j3-flasher-travelbot.git
cd j3-flasher-travelbot
```

### 2. Create Virtual Environment (Recommended)
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install System Tools (Linux only)
On Linux, you may need to install Heimdall:
```bash
sudo apt update
sudo apt install heimdall-flash
```

## Usage

### Quick Start
1. **Prepare your device**:
   - Enable Developer Options (tap Build Number 7 times in Settings > About Phone)
   - Enable USB Debugging in Developer Options
   - Enable OEM Unlock in Developer Options
   - Power off the device

2. **Start the application**:
   ```bash
   python flash.py
   ```

3. **Follow the GUI**:
   - Click "Install Tools" if prompted
   - Put device in Download Mode (Power + Home + Volume Down, then Volume Up)
   - Connect device via USB
   - Click "Detecteer toestel" to verify connection
   - Choose flashing option:
     - "Flash TWRP" for recovery only
     - "Flash LineageOS" for full ROM

### Detailed Steps

#### Preparing the Phone
1. **Enable Developer Options**:
   - Go to Settings > About Phone
   - Tap "Build Number" 7 times until you see "Developer mode enabled"

2. **Enable USB Debugging and OEM Unlock**:
   - Go to Settings > Developer Options
   - Enable "USB Debugging"
   - Enable "OEM Unlock" (may require internet connection)

3. **Enter Download Mode**:
   - Power off the phone completely
   - Hold **Power + Home + Volume Down** simultaneously
   - When warning screen appears, press **Volume Up** to continue
   - Connect phone to computer via USB

#### Using the Application
1. **Install Tools** (first time only):
   - Click "Install Tools" to download ADB and platform tools
   - On Linux, install Heimdall when prompted

2. **Verify Connection**:
   - Click "Detecteer toestel" to check if device is detected
   - Should show success message if properly connected

3. **Flash Recovery**:
   - Click "Flash TWRP" to install custom recovery
   - Wait for completion message
   - **Important**: After TWRP flash, immediately hold Power + Home + Volume Up to boot into TWRP

4. **Flash ROM** (optional):
   - Click "Flash LineageOS" to install custom ROM
   - Process will reboot device multiple times
   - Wait for completion

## Directory Structure
- `scripts/` – optional helper scripts or recovery tools
- `images/` – logo or branding assets
- `docs/` – HTML documentation and guides
- `cache/` – downloaded files (created automatically)
- `flash.py` – main application
- `requirements.txt` – Python dependencies
- `device_config.json` – device-specific URLs and configuration

## Troubleshooting

### Common Issues

#### Device Not Detected
**Symptoms**: "Geen toestel gedetecteerd" error
**Solutions**:
- Ensure device is in Download Mode (not Recovery or normal boot)
- Use original USB cable, avoid hubs or extensions
- Try different USB ports
- On Linux: Stop ModemManager with `sudo systemctl stop ModemManager`
- Check USB permissions: add user to dialout group with `sudo usermod -a -G dialout $USER`

#### Heimdall Issues
**Symptoms**: "Heimdall Missing" error
**Solutions**:
- On Linux: Install with `sudo apt install heimdall-flash`
- On Windows: Use Odin instead, or install Heimdall manually
- Ensure device drivers are installed properly

#### Network/Download Issues
**Symptoms**: Download failures or network errors
**Solutions**:
- Check internet connection
- Verify firewall isn't blocking downloads
- Try running with administrator/sudo privileges
- Clear cache directory and retry

#### Flash Failures
**Symptoms**: Flash process fails or device becomes unresponsive
**Solutions**:
- Ensure device has sufficient battery (>50%)
- Use original USB cable
- Don't disconnect device during flashing
- If device appears "bricked", try entering Download Mode again
- For recovery: Try flashing TWRP only first

#### Permission Issues (Linux)
**Symptoms**: Access denied errors
**Solutions**:
- Add user to dialout group: `sudo usermod -a -G dialout $USER`
- Log out and back in for group changes to take effect
- Run with sudo if necessary: `sudo python flash.py`

### Advanced Troubleshooting

#### Reset to Stock
If you need to return to stock firmware:
1. Download official Samsung firmware for SM-J320FN
2. Use Odin (Windows) or Heimdall (Linux) to flash stock firmware
3. Follow Samsung's official recovery procedures

#### Log Analysis
- Check `flasher.log` for detailed error messages
- Use "Bekijk log" button in GUI to view current log
- Look for specific error codes or messages for web searches

#### Getting Help
- Check existing issues on GitHub repository
- Include relevant log entries when reporting issues
- Specify your operating system and Python version
- Describe exact steps that led to the problem

## Safety Warnings

⚠️ **Important Safety Information**:
- **Backup your data** before flashing - all data will be erased
- Ensure device has **>50% battery** before starting
- **Do not disconnect** device during flashing process
- Use **original USB cable** for best results
- Flashing custom firmware **voids warranty**
- Author is **not responsible** for damaged devices

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- LineageOS team for the custom ROM
- TWRP team for the custom recovery
- Samsung for the original firmware
- Python and PyQt6 communities

