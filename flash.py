import argparse
import logging
import os
import platform
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import requests

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
    system = 'linux' if platform.system().lower() != 'windows' else 'windows'
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
    os.chmod('platform-tools/adb', 0o755)
    os.chmod('platform-tools/fastboot', 0o755)


def ensure_tools():
    adb = check_tool('adb') or Path('platform-tools/adb').exists()
    fastboot = check_tool('fastboot') or Path('platform-tools/fastboot').exists()
    if adb and fastboot:
        log_and_print('ADB and Fastboot found')
        return
    log_and_print('ADB/Fastboot not found, downloading platform tools...')
    download_platform_tools()


def adb_command(args):
    adb_path = check_tool('adb') or str(Path('platform-tools/adb'))
    return subprocess.run([adb_path] + args, capture_output=True, text=True)


def fastboot_command(args):
    fb_path = check_tool('fastboot') or str(Path('platform-tools/fastboot'))
    return subprocess.run([fb_path] + args, capture_output=True, text=True)


def device_connected():
    result = adb_command(['devices'])
    lines = result.stdout.strip().splitlines()
    devices = [l for l in lines[1:] if l.strip()]
    return len(devices) > 0


def download_file(url, dest):
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


def main():
    parser = argparse.ArgumentParser(description='Travelbot Flasher')
    parser.add_argument('--flash', action='store_true', help='Flash LineageOS')
    parser.add_argument('--apk', help='Optional APK to install')
    parser.add_argument('--root', action='store_true', help='Install Magisk for root')
    args = parser.parse_args()

    ensure_tools()

    if not device_connected():
        log_and_print('Phone not found. Is USB debugging enabled?')
        sys.exit(1)

    lineage_url = 'https://example.com/lineage.zip'
    twrp_url = 'https://example.com/twrp.img'
    lineage_zip = Path('lineage.zip')
    twrp_img = Path('twrp.img')

    if args.flash:
        if not lineage_zip.exists():
            download_file(lineage_url, lineage_zip)
        if not twrp_img.exists():
            download_file(twrp_url, twrp_img)
        flash_recovery(str(twrp_img))
        sideload_zip(str(lineage_zip))
        if args.root:
            magisk_url = 'https://example.com/magisk.zip'
            magisk_zip = Path('magisk.zip')
            if not magisk_zip.exists():
                download_file(magisk_url, magisk_zip)
            sideload_zip(str(magisk_zip))
        if args.apk:
            install_apk(args.apk)
        log_and_print('Flashing complete!')
    else:
        log_and_print('No action specified. Use --flash to start flashing.')

if __name__ == '__main__':
    main()
