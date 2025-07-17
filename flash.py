import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path
import tkinter as tk
from tkinter import (
    Tk,
    ttk,
    scrolledtext,
    filedialog,
    messagebox,
    END,
)

import sys

import requests

CONFIG_FILE = 'device_config.json'
CACHE_DIR = Path('cache')
LOG_FILE = 'flasher.log'
TWRP_URL = 'https://eu.dl.twrp.me/j3lte/twrp-3.7.0_9-0-j3lte.img'
TWRP_IMG = Path('twrp-j3lte.img')

INSTRUCTION_TEXT = (
    "1. Enable USB debugging and OEM unlock in Developer Options.\n"
    "2. Boot the phone into Download Mode (Power+Home+Vol Down, then Vol Up).\n"
    "3. Connect the phone and click 'Check Device'.\n"
    "4. Use 'Install Tools' to download ADB and install Heimdall if needed.\n"
    "5. Use 'Auto Flash TWRP' for a quick recovery flash.\n"
    "6. To flash only TWRP manually, click 'Flash Recovery Only'.\n"
    "7. For the full flash, optionally pick an APK and press 'Flash All'.\n"
    "8. Progress appears below and in flasher.log.\n"
)

IS_WINDOWS = platform.system().lower() == 'windows'
ADB_NAME = 'adb.exe' if IS_WINDOWS else 'adb'
HEIMDALL_NAME = 'heimdall.exe' if IS_WINDOWS else 'heimdall'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def show_info(title, message):
    messagebox.showinfo(title, message)


def show_error(title, message):
    messagebox.showerror(title, message)


def ask_yes_no(title, message):
    return messagebox.askyesno(title, message)


def log(message, text_widget=None):
    """Log a message to the log file and optionally to the GUI log box."""
    logging.info(message)
    print(message)
    if text_widget:
        text_widget.insert(END, message + "\n")
        text_widget.see(END)


def check_tool(name):
    return shutil.which(name)


def download_platform_tools(text):
    system = 'windows' if IS_WINDOWS else 'linux'
    url = f'https://dl.google.com/android/repository/platform-tools-latest-{system}.zip'
    log(f'Downloading platform tools from {url}', text)
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError('Failed to download platform tools')
    zpath = Path('platform-tools.zip')
    with open(zpath, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)
    log('Extracting platform tools...', text)
    with zipfile.ZipFile(zpath, 'r') as zip_ref:
        zip_ref.extractall('.')
    zpath.unlink()
    if not IS_WINDOWS:
        os.chmod('platform-tools/adb', 0o755)
    log('Platform tools ready.', text)


def ensure_adb(text):
    adb = check_tool(ADB_NAME)
    if adb:
        log('ADB found on system.', text)
        return
    local_adb = Path('platform-tools') / ADB_NAME
    if local_adb.exists():
        log('Using local platform-tools binaries.', text)
        return
    log('ADB not found, downloading platform tools...', text)
    download_platform_tools(text)


def ensure_heimdall(text):
    if check_tool(HEIMDALL_NAME):
        log('Heimdall found.', text)
        return True
    log('Heimdall not found.', text)
    if not IS_WINDOWS:
        if ask_yes_no('Install Heimdall',
                      'Heimdall is missing. Install via apt? (sudo required)'):
            try:
                subprocess.run(['sudo', 'apt', 'install', '-y', 'heimdall-flash'], check=False)
            except Exception as exc:  # noqa: BLE001
                log(f'Failed to run apt: {exc}', text)
    if check_tool(HEIMDALL_NAME):
        log('Heimdall installed.', text)
        return True
    log('Please install Heimdall manually (or use Odin on Windows).', text)
    return False


def check_heimdall(text_widget=None):
    """Verify that Heimdall is installed by calling `heimdall version`."""
    try:
        result = subprocess.run(
            [HEIMDALL_NAME, 'version'], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        show_error(
            'Heimdall Missing',
            'Heimdall is not installed. Please install it with `sudo apt install heimdall-flash`',
        )
        log('Heimdall command not found.', text_widget)
        return False
    if result.returncode != 0:
        show_error(
            'Heimdall Missing',
            'Heimdall is not installed. Please install it with `sudo apt install heimdall-flash`',
        )
        log(result.stderr.strip(), text_widget)
        return False
    log(result.stdout.strip(), text_widget)
    return True


def detect_device(text_widget=None):
    """Check if a device is in Download Mode via `heimdall detect`."""
    try:
        result = subprocess.run(
            [HEIMDALL_NAME, 'detect'], capture_output=True, text=True, check=False
        )
    except FileNotFoundError:
        show_error(
            'Heimdall Missing',
            'Heimdall is not installed. Please install it with `sudo apt install heimdall-flash`',
        )
        log('Heimdall command not found.', text_widget)
        return False
    log(result.stdout.strip(), text_widget)
    if result.returncode != 0:
        show_error(
            'Geen toestel',
            '❌ Geen toestel gedetecteerd. Zorg dat je in Download Mode zit en met USB verbonden bent.',
        )
        log(result.stderr.strip(), text_widget)
        return False
    return True


def download_twrp(text_widget=None):
    """Download the TWRP image if it's missing."""
    if TWRP_IMG.exists():
        log(f'{TWRP_IMG} already present.', text_widget)
        return TWRP_IMG
    log(f'Downloading TWRP from {TWRP_URL}', text_widget)
    response = requests.get(TWRP_URL, stream=True)
    if response.status_code != 200:
        raise RuntimeError('Failed to download TWRP image')
    with open(TWRP_IMG, 'wb') as fh:
        for chunk in response.iter_content(chunk_size=8192):
            fh.write(chunk)
    log('TWRP download complete.', text_widget)
    return TWRP_IMG


def flash_recovery(img, text_widget=None):
    """Flash the recovery image using Heimdall and log the output."""
    log('⚡ Flashing TWRP...', text_widget)
    with open(LOG_FILE, 'a') as log_fh:
        result = subprocess.run(
            [HEIMDALL_NAME, 'flash', '--RECOVERY', str(img), '--no-reboot'],
            capture_output=True,
            text=True,
        )
        log_fh.write(result.stdout)
        log_fh.write(result.stderr)
    if result.returncode != 0:
        show_error('Flash Failed', result.stderr.strip())
        return False
    show_info(
        'Action Required',
        'Recovery flashed. Houd Power + Home + Volume Up ingedrukt om in TWRP te booten.',
    )
    return True


def auto_flash_j3(text_widget=None):
    """Run the full automatic flashing procedure for the SM-J320FN."""
    if not check_heimdall(text_widget):
        return
    if not detect_device(text_widget):
        return
    img = download_twrp(text_widget)
    flash_recovery(img, text_widget)


def adb_command(args):
    adb_path = check_tool(ADB_NAME) or str(Path('platform-tools') / ADB_NAME)
    return subprocess.run([adb_path] + args, capture_output=True, text=True)


def device_connected():
    result = adb_command(['devices'])
    lines = result.stdout.strip().splitlines()
    devices = [l for l in lines[1:] if l.strip()]
    return len(devices) > 0


def load_profile():
    if not Path(CONFIG_FILE).exists():
        return None
    with open(CONFIG_FILE, 'r') as fh:
        data = json.load(fh)
    return data.get('SM-J320FN')


def download_file(url, dest, text):
    CACHE_DIR.mkdir(exist_ok=True)
    if dest.exists():
        log(f'{dest} already exists, skipping download', text)
        return
    log(f'Downloading {url}', text)
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f'Failed to download {url}')
    with open(dest, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)




def sideload_zip(zip_path, text):
    log('Sideloading LineageOS...', text)
    adb_command(['reboot', 'recovery'])
    adb_command(['wait-for-device'])
    subprocess.run([ADB_NAME, 'sideload', zip_path])


def install_tools(text_widget):
    try:
        ensure_adb(text_widget)
        ensure_heimdall(text_widget)
        log('Tool installation complete.', text_widget)
    except Exception as exc:  # noqa: BLE001
        show_error('Error', str(exc))
        log(f'Error: {exc}', text_widget)


def check_tools(text_widget):
    ensure_adb(text_widget)
    ensure_heimdall(text_widget)


def download_rom(text_widget):
    """Download only the LineageOS ROM."""
    try:
        profile = load_profile()
        if not profile:
            log('Device profile not found.', text_widget)
            return
        rom_zip = CACHE_DIR / Path(profile['rom_url']).name
        download_file(profile['rom_url'], rom_zip, text_widget)
        log('ROM download complete.', text_widget)
    except Exception as exc:  # noqa: BLE001
        show_error('Error', str(exc))
        log(f'Error: {exc}', text_widget)


def install_apk(apk, text):
    log(f'Installing APK {apk}', text)
    subprocess.run([ADB_NAME, 'install', apk])


def install_apk_prompt(text_widget):
    path = filedialog.askopenfilename(filetypes=[('APK files', '*.apk')])
    if path:
        install_apk(path, text_widget)


def reboot_device(mode, text):
    log(f'Rebooting to {mode}...', text)
    adb_command(['reboot', mode])


def open_log_file():
    if IS_WINDOWS:
        os.startfile(LOG_FILE)
    elif shutil.which('xdg-open'):
        subprocess.run(['xdg-open', LOG_FILE], check=False)
    else:
        show_info('Log File', f'Log located at {LOG_FILE}')


def clear_log(text_widget):
    text_widget.delete('1.0', END)
    Path(LOG_FILE).write_text('')
    log('Log cleared.', text_widget)


def show_help():
    show_info('Help', INSTRUCTION_TEXT)


def flash_recovery_only(text_widget):
    try:
        ensure_adb(text_widget)
        if not device_connected():
            log('No device detected via ADB.', text_widget)
            return
        profile = load_profile()
        if not profile:
            log('Device profile not found.', text_widget)
            return
        recovery_img = CACHE_DIR / Path(profile['recovery_url']).name
        download_file(profile['recovery_url'], recovery_img, text_widget)
        show_info(
            'Download Mode',
            'Put the phone in Download Mode (Power+Home+Vol Down) and connect it.'
        )
        flash_recovery(str(recovery_img), text_widget)
        log('Recovery flash complete.', text_widget)
    except Exception as exc:  # noqa: BLE001
        show_error('Error', str(exc))
        log(f'Error: {exc}', text_widget)


def flash_process(text_widget, apk_path=None):
    try:
        ensure_adb(text_widget)
        if not device_connected():
            log('No device detected via ADB.', text_widget)
            return
        profile = load_profile()
        if not profile:
            log('Device profile not found.', text_widget)
            return
        recovery_img = CACHE_DIR / Path(profile['recovery_url']).name
        rom_zip = CACHE_DIR / Path(profile['rom_url']).name
        download_file(profile['recovery_url'], recovery_img, text_widget)
        download_file(profile['rom_url'], rom_zip, text_widget)
        show_info(
            'Download Mode',
            'Put the phone in Download Mode (Power+Home+Vol Down) and connect it.'
        )
        flash_recovery(str(recovery_img), text_widget)
        sideload_zip(str(rom_zip), text_widget)
        if apk_path:
            install_apk(apk_path, text_widget)
        log('Flashing complete.', text_widget)
    except Exception as exc:  # noqa: BLE001
        show_error('Error', str(exc))
        log(f'Error: {exc}', text_widget)


def start_flash(text_widget, apk_path, progress):

    def run():
        try:
            flash_process(text_widget, apk_path)
        finally:
            progress.stop()

    progress.start()
    threading.Thread(target=run, daemon=True).start()


def start_flash_recovery(text_widget, progress):

    def run():
        try:
            flash_recovery_only(text_widget)
        finally:
            progress.stop()

    progress.start()
    threading.Thread(target=run, daemon=True).start()


def start_auto_flash(text_widget, progress):

    def run():
        try:
            auto_flash_j3(text_widget)
        finally:
            progress.stop()

    progress.start()
    threading.Thread(target=run, daemon=True).start()


def start_install_tools(text_widget, progress):

    def run():
        try:
            install_tools(text_widget)
        finally:
            progress.stop()

    progress.start()
    threading.Thread(target=run, daemon=True).start()


def check_device(text_widget):
    ensure_adb(text_widget)
    if device_connected():
        log('Device detected!', text_widget)
    else:
        log('No device found.', text_widget)




def main():
    root = Tk()
    root.title('📱 Travelbot Flasher')
    root.minsize(600, 400)
    root.configure(bg='#E6E6FA')
    root.option_add('*Font', 'Helvetica 12')

    style = ttk.Style(root)
    if 'clam' in style.theme_names():
        style.theme_use('clam')
    style.configure('TFrame', background='#E6E6FA')
    style.configure('TLabel', background='#E6E6FA', foreground='#000033')
    style.configure('TButton', font=('Helvetica', 12), padding=6)

    frame = ttk.Frame(root, padding=10)
    frame.pack(fill='both', expand=True)

    ttk.Label(frame, text='📱 Travelbot Flasher', font=('Helvetica', 16, 'bold')).pack(pady=(0, 10))
    ttk.Label(frame, text=INSTRUCTION_TEXT, justify='left', wraplength=560).pack(pady=(0, 10))

    log_box = scrolledtext.ScrolledText(frame, height=10)
    log_box.pack(fill='both', expand=True, pady=10)

    progress = ttk.Progressbar(frame, mode='indeterminate')
    progress.pack(fill='x', pady=5)

    ttk.Button(frame, text='Detecteer Toestel', command=lambda: check_device(log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Download ROM', command=lambda: download_rom(log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Flash TWRP', command=lambda: start_flash_recovery(log_box, progress)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Flash LineageOS', command=lambda: start_flash(log_box, None, progress)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Install APK', command=lambda: install_apk_prompt(log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Reboot to Recovery', command=lambda: reboot_device('recovery', log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Reboot System', command=lambda: reboot_device('system', log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Open Log', command=open_log_file).pack(fill='x', pady=2)
    ttk.Button(frame, text='Clear Log', command=lambda: clear_log(log_box)).pack(fill='x', pady=2)
    ttk.Button(frame, text='Help', command=show_help).pack(fill='x', pady=2)

    root.mainloop()


if __name__ == '__main__':
    main()
