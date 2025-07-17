import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
)
from PyQt6.QtCore import QTimer

import requests

CONFIG_FILE = 'device_config.json'
CACHE_DIR = Path('cache')
LOG_FILE = 'flasher.log'

INSTRUCTION_TEXT = (
    "1. Enable USB debugging and OEM unlock in Developer Options.\n"
    "2. Boot the phone into Download Mode (Power+Home+Vol Down, then Vol Up).\n"
    "3. Connect the phone and click 'Check Device'.\n"
    "4. Use 'Install Tools' to download ADB and install Heimdall if needed.\n"
    "5. To flash only TWRP, click 'Flash Recovery Only'.\n"
    "6. For the full flash, optionally pick an APK and press 'Flash All'.\n"
    "7. Progress appears below and in flasher.log.\n"
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
    QMessageBox.information(None, title, message)


def show_error(title, message):
    QMessageBox.critical(None, title, message)


def ask_yes_no(title, message):
    result = QMessageBox.question(
        None,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return result == QMessageBox.StandardButton.Yes


def log(message, text_widget=None):
    """Log a message to the log file and optionally to a QTextEdit widget."""
    logging.info(message)
    print(message)
    if text_widget:
        text_widget.append(message)
        text_widget.ensureCursorVisible()


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
        show_info(
            'Windows Detected',
            'Please use Odin to flash the recovery image manually.'
        )
        return
    if not ensure_heimdall(text):
        return
    log('Flashing TWRP recovery...', text)
    subprocess.run([HEIMDALL_NAME, 'flash', '--RECOVERY', img, '--no-reboot'])
    show_info(
        'Action Required',
        'Recovery flashed. Boot the phone into recovery now (Vol+ Home Power).'
    )


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


def install_apk(apk, text):
    log(f'Installing APK {apk}', text)
    subprocess.run([ADB_NAME, 'install', apk])


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
    text_widget.clear()
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
            QTimer.singleShot(0, lambda: progress.setVisible(False))

    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def start_flash_recovery(text_widget, progress):

    def run():
        try:
            flash_recovery_only(text_widget)
        finally:
            QTimer.singleShot(0, lambda: progress.setVisible(False))

    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def start_install_tools(text_widget, progress):

    def run():
        try:
            install_tools(text_widget)
        finally:
            QTimer.singleShot(0, lambda: progress.setVisible(False))

    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def check_device(text_widget):
    ensure_adb(text_widget)
    if device_connected():
        log('Device detected!', text_widget)
    else:
        log('No device found.', text_widget)


def select_apk(var_container):
    path, _ = QFileDialog.getOpenFileName(None, 'Select APK', '', 'APK files (*.apk)')
    if path:
        var_container[0] = path


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Travelbot Flasher')

        layout = QVBoxLayout(self)

        label = QLabel(INSTRUCTION_TEXT)
        label.setWordWrap(True)
        layout.addWidget(label)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.apk_path = [None]

        btn_check_device = QPushButton('Check Device')
        btn_check_device.clicked.connect(lambda: check_device(self.log_box))
        layout.addWidget(btn_check_device)

        btn_check_tools = QPushButton('Check Tools')
        btn_check_tools.clicked.connect(lambda: check_tools(self.log_box))
        layout.addWidget(btn_check_tools)

        btn_install_tools = QPushButton('Install Tools')
        btn_install_tools.clicked.connect(lambda: start_install_tools(self.log_box, self.progress))
        layout.addWidget(btn_install_tools)

        btn_flash_recovery = QPushButton('Flash Recovery Only')
        btn_flash_recovery.clicked.connect(lambda: start_flash_recovery(self.log_box, self.progress))
        layout.addWidget(btn_flash_recovery)

        btn_select_apk = QPushButton('Select APK')
        btn_select_apk.clicked.connect(lambda: select_apk(self.apk_path))
        layout.addWidget(btn_select_apk)

        btn_flash_all = QPushButton('Flash All')
        btn_flash_all.clicked.connect(lambda: start_flash(self.log_box, self.apk_path[0], self.progress))
        layout.addWidget(btn_flash_all)

        btn_reboot_recovery = QPushButton('Reboot to Recovery')
        btn_reboot_recovery.clicked.connect(lambda: reboot_device('recovery', self.log_box))
        layout.addWidget(btn_reboot_recovery)

        btn_reboot_system = QPushButton('Reboot System')
        btn_reboot_system.clicked.connect(lambda: reboot_device('system', self.log_box))
        layout.addWidget(btn_reboot_system)

        btn_open_log = QPushButton('Open Log')
        btn_open_log.clicked.connect(open_log_file)
        layout.addWidget(btn_open_log)

        btn_clear_log = QPushButton('Clear Log')
        btn_clear_log.clicked.connect(lambda: clear_log(self.log_box))
        layout.addWidget(btn_clear_log)

        btn_help = QPushButton('Help')
        btn_help.clicked.connect(show_help)
        layout.addWidget(btn_help)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
