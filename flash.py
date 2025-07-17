import argparse
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import questionary
import requests

CONFIG_FILE = 'device_config.json'
CACHE_DIR = Path('cache')

IS_WINDOWS = platform.system().lower() == 'windows'
ADB_NAME = 'adb.exe' if IS_WINDOWS else 'adb'
FASTBOOT_NAME = 'fastboot.exe' if IS_WINDOWS else 'fastboot'

LOG_FILE = 'flasher.log'
logging.basicConfig(filename=LOG_FILE,
                    level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def log_and_print(message):
    print(message)
    logging.info(message)

def check_tool(name):
    path = shutil.which(name)
    return path if path else None

def download_platform_tools():
    system = 'windows' if IS_WINDOWS else 'linux'
    url = f'https://dl.google.com/android/repository/platform-tools-latest-{system}.zip'
    log_and_print(f'Downloading platform tools from {url}')
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError('Failed to download platform tools')
    zpath = Path('platform-tools.zip')
    with open(zpath, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)
    log_and_print('Extracting platform tools...')
    with zipfile.ZipFile(zpath, 'r') as zip_ref:
        zip_ref.extractall('.')
    zpath.unlink()
    if not IS_WINDOWS:
        os.chmod('platform-tools/adb', 0o755)
        os.chmod('platform-tools/fastboot', 0o755)


def ensure_tools():
    adb = check_tool(ADB_NAME)
    fastboot = check_tool(FASTBOOT_NAME)
    if not adb or not fastboot:
        local_adb = Path('platform-tools') / ADB_NAME
        local_fb = Path('platform-tools') / FASTBOOT_NAME
        if local_adb.exists() and local_fb.exists():
            log_and_print('Using local platform-tools binaries')
            return
        log_and_print('ADB/Fastboot not found, downloading platform tools...')
        download_platform_tools()
    else:
        log_and_print('ADB and Fastboot found')


def adb_command(args):
    adb_path = check_tool(ADB_NAME) or str(Path('platform-tools') / ADB_NAME)
    return subprocess.run([str(adb_path)] + args, capture_output=True, text=True)


def fastboot_command(args):
    fb_path = check_tool(FASTBOOT_NAME) or str(Path('platform-tools') / FASTBOOT_NAME)
    return subprocess.run([str(fb_path)] + args, capture_output=True, text=True)


def device_connected():
    result = adb_command(['devices'])
    lines = result.stdout.strip().splitlines()
    devices = [l for l in lines[1:] if l.strip()]
    return len(devices) > 0


def detect_device():
    model = adb_command(['shell', 'getprop', 'ro.product.model']).stdout.strip()
    if not model:
        model = adb_command(['shell', 'getprop', 'ro.product.device']).stdout.strip()
    log_and_print(f'Detected device model: {model}')
    return model


def load_device_profile(model):
    if not Path(CONFIG_FILE).exists():
        log_and_print(f'Config file {CONFIG_FILE} not found')
        return None
    with open(CONFIG_FILE, 'r') as fh:
        data = json.load(fh)
    profile = data.get(model)
    if not profile:
        log_and_print(f'No configuration for {model} in {CONFIG_FILE}')
    return profile


def download_file(url, dest):
    CACHE_DIR.mkdir(exist_ok=True)
    if dest.exists():
        log_and_print(f'{dest} already exists, skipping download')
        return
    log_and_print(f'Downloading {url}')
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise RuntimeError(f'Failed to download {url}')
    with open(dest, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)


def flash_recovery(recovery_img):
    log_and_print('Flashing recovery...')
    adb_command(['reboot', 'bootloader'])
    fastboot_command(['flash', 'recovery', recovery_img])
    fastboot_command(['reboot'])


def sideload_zip(zip_path):
    log_and_print('Sideloading ROM...')
    adb_command(['reboot', 'recovery'])
    adb_command(['wait-for-device'])
    adb_command(['sideload', zip_path])


def install_apk(apk_path):
    log_and_print(f'Installing APK {apk_path}')
    adb_command(['install', apk_path])


def bootloader_unlocked():
    log_and_print('Checking bootloader status...')
    adb_command(['reboot', 'bootloader'])
    result = fastboot_command(['oem', 'device-info'])
    fastboot_command(['reboot'])
    output = (result.stdout + result.stderr).lower()
    if 'unlocked: yes' in output or 'device unlocked: true' in output:
        log_and_print('Bootloader is unlocked.')
        return True
    log_and_print('Bootloader is locked. Please unlock it before flashing.')
    return False


def clean_cache():
    if CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)
        log_and_print('Cache directory removed.')


def main():
    parser = argparse.ArgumentParser(description='Travelbot Flasher')
    parser.add_argument('--flash', action='store_true', help='Flash LineageOS')
    parser.add_argument('--apk', help='Optional APK to install')
    parser.add_argument('--root', action='store_true', help='Install Magisk for root')
    parser.add_argument('--clean', action='store_true', help='Clean cache after flashing')
    args = parser.parse_args()

    ensure_tools()

    if not device_connected():
        log_and_print('Phone not found. Is USB debugging enabled?')
        sys.exit(1)

    if not any([args.flash, args.root, args.apk]):
        choices = questionary.checkbox(
            'Select actions to perform',
            choices=[
                questionary.Choice('Flash LineageOS', 'flash'),
                questionary.Choice('Install Magisk (root)', 'root'),
                questionary.Choice('Install APK', 'apk'),
                questionary.Choice('Clean cache after flashing', 'clean'),
            ],
        ).ask()
        args.flash = 'flash' in choices
        args.root = 'root' in choices
        args.clean = 'clean' in choices
        if 'apk' in choices:
            args.apk = questionary.path('Path to APK').ask()

    model = detect_device()
    profile = load_device_profile(model)
    if not profile:
        sys.exit(1)

    if not bootloader_unlocked():
        sys.exit('Please unlock the bootloader and run the script again.')

    if args.flash:
        recovery_img = CACHE_DIR / Path(profile['recovery_url']).name
        rom_zip = CACHE_DIR / Path(profile['rom_url']).name
        download_file(profile['recovery_url'], recovery_img)
        download_file(profile['rom_url'], rom_zip)
        flash_recovery(str(recovery_img))
        sideload_zip(str(rom_zip))
        if args.root and profile.get('magisk_url'):
            magisk_zip = CACHE_DIR / Path(profile['magisk_url']).name
            download_file(profile['magisk_url'], magisk_zip)
            sideload_zip(str(magisk_zip))
    if args.apk:
        install_apk(args.apk)

    log_and_print('Operations complete!')
    if args.clean:
        clean_cache()

if __name__ == '__main__':
    main()
