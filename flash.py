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
from tkinter import filedialog, messagebox, scrolledtext, Tk, Button, END

import requests

CONFIG_FILE = 'device_config.json'
CACHE_DIR = Path('cache')
LOG_FILE = 'flasher.log'

IS_WINDOWS = platform.system().lower() == 'windows'
ADB_NAME = 'adb.exe' if IS_WINDOWS else 'adb'
HEIMDALL_NAME = 'heimdall.exe' if IS_WINDOWS else 'heimdall'

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def log(message, text_widget=None):
    logging.info(message)
    print(message)
    if text_widget:
        text_widget.insert(END, message + '\n')
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
    log('Heimdall not found. Please install Heimdall (or Odin on Windows).', text)
    return False


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


def flash_recovery(img, text):
    if IS_WINDOWS:
        messagebox.showinfo(
            'Windows Detected',
            'Please use Odin to flash the recovery image manually.'
        )
        return
    if not ensure_heimdall(text):
        return
    log('Flashing TWRP recovery...', text)
    subprocess.run([HEIMDALL_NAME, 'flash', '--RECOVERY', img, '--no-reboot'])
    messagebox.showinfo('Action Required',
                        'Recovery flashed. Boot the phone into recovery now (Vol+ Home Power).')


def sideload_zip(zip_path, text):
    log('Sideloading LineageOS...', text)
    adb_command(['reboot', 'recovery'])
    adb_command(['wait-for-device'])
    subprocess.run([ADB_NAME, 'sideload', zip_path])


def install_apk(apk, text):
    log(f'Installing APK {apk}', text)
    subprocess.run([ADB_NAME, 'install', apk])


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
        messagebox.showinfo('Download Mode',
                            'Put the phone in Download Mode (Power+Home+Vol Down) and connect it.')
        flash_recovery(str(recovery_img), text_widget)
        sideload_zip(str(rom_zip), text_widget)
        if apk_path:
            install_apk(apk_path, text_widget)
        log('Flashing complete.', text_widget)
    except Exception as exc:  # noqa: BLE001
        messagebox.showerror('Error', str(exc))
        log(f'Error: {exc}', text_widget)


def start_flash(text_widget, apk_var):
    apk_path = apk_var.get() if apk_var.get() else None
    threading.Thread(target=flash_process, args=(text_widget, apk_path), daemon=True).start()


def check_device(text_widget):
    ensure_adb(text_widget)
    if device_connected():
        log('Device detected!', text_widget)
    else:
        log('No device found.', text_widget)


def select_apk(var):
    path = filedialog.askopenfilename(filetypes=[('APK files', '*.apk')])
    if path:
        var.set(path)


def main():
    root = Tk()
    root.title('Travelbot Flasher')

    log_box = scrolledtext.ScrolledText(root, width=80, height=20)
    log_box.pack(padx=10, pady=10)

    apk_var = tk.StringVar()

    Button(root, text='Check Device', command=lambda: check_device(log_box)).pack(fill='x')
    Button(root, text='Select APK', command=lambda: select_apk(apk_var)).pack(fill='x')
    Button(root, text='Flash', command=lambda: start_flash(log_box, apk_var)).pack(fill='x')

    root.mainloop()


if __name__ == '__main__':
    main()
