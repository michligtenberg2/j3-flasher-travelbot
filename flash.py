import json
import logging
import os
import platform
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path
from PyQt6 import QtWidgets, QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QTextEdit,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QLabel,
    QTabWidget,
)
from PyQt6.QtCore import Qt, QTimer

import sys

import requests

CONFIG_FILE = 'device_config.json'
CACHE_DIR = Path('cache')
LOG_FILE = 'flasher.log'
TWRP_URL = 'https://eu.dl.twrp.me/j3lte/twrp-3.7.0_9-0-j3lte.img'
TWRP_IMG = Path('twrp-j3lte.img')
DOWNLOADS_DIR = Path('downloads')
MAGISK_URL = 'https://github.com/topjohnwu/Magisk/releases/download/v23.0/Magisk-v23.0.zip'
MAGISK_ZIP = DOWNLOADS_DIR / 'Magisk-v23.0.zip'
TRAVELBOT_APK = DOWNLOADS_DIR / 'travelbot.apk'

INSTRUCTION_TEXT = (
    "1. Enable USB debugging and OEM unlock in Developer Options.\n"
    "2. Boot the phone into Download Mode (Power+Home+Vol Down, then Vol Up).\n"
"3. Connect the phone and click 'Detecteer Toestel'.\n"
"4. Gebruik 'Install Tools' om ADB en Heimdall te installeren indien nodig.\n"
"5. Kies 'Auto Flash TWRP' voor automatische flashing van de recovery.\n"
"6. Handmatig flashen kan via 'Flash TWRP' of 'Flash LineageOS'.\n"
"7. Alle voortgang verschijnt hieronder en in flasher.log.\n"
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
    return QMessageBox.question(None, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes


def log(message, text_widget=None):
    """Log a message to the log file and optionally to the GUI log box."""
    logging.info(message)
    print(message)
    if text_widget:
        text_widget.append(message)


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
    cmd = [HEIMDALL_NAME, 'flash', '--RECOVERY', str(img), '--no-reboot']
    output_lines = []
    with open(LOG_FILE, 'a') as log_fh:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
        )
        for line in process.stdout:
            line = line.strip()
            output_lines.append(line)
            log(line, text_widget)
            log_fh.write(line + '\n')
        process.wait()

    output_text = '\n'.join(output_lines)
    if process.returncode != 0:
        error_text = output_text
        if (
            'protocol initialisation failed' in error_text.lower()
            or 'failed to receive session end confirmation' in error_text.lower()
        ):
            error_text += (
                '\n\nGebruik een originele USB-datakabel.\n'
                'Vermijd USB-hubs, zet het toestel opnieuw in Download Mode\n'
                'en stop eventueel ModemManager: `sudo systemctl stop ModemManager`'
            )
        show_error('Flash Failed', error_text)
        return False

    if 'RECOVERY upload successful' not in output_text:
        show_error('Flash Failed', output_text)
        return False

    show_info(
        'TWRP Geflasht',
        (
            '✅ TWRP succesvol geflasht!\n\n'
            '⚠️ BELANGRIJK: Houd nu Power + Home + Volume Up ingedrukt totdat '
            'het Samsung-logo verschijnt om direct in TWRP te booten. Doe dit '
            'voordat het toestel normaal opstart, anders wordt TWRP overschreven.'
        ),
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


def flash_twrp_gui(text_widget=None):
    """Flash TWRP for the J3 using Heimdall and guide the user."""
    if not check_heimdall(text_widget):
        return
    if not detect_device(text_widget):
        return
    if not TWRP_IMG.exists():
        show_error('Bestand ontbreekt', f'{TWRP_IMG} niet gevonden in de werkmap')
        log('TWRP image missing', text_widget)
        return
    flash_recovery(TWRP_IMG, text_widget)


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
    dialog = QFileDialog()
    dialog.setNameFilter('APK files (*.apk)')
    if dialog.exec() and dialog.selectedFiles():
        install_apk(dialog.selectedFiles()[0], text_widget)


def install_travelbot_apk(text_widget):
    if not TRAVELBOT_APK.exists():
        show_error('Bestand ontbreekt', f'{TRAVELBOT_APK} niet gevonden')
        log('APK missing', text_widget)
        return
    install_apk(str(TRAVELBOT_APK), text_widget)


def download_magisk(text_widget):
    DOWNLOADS_DIR.mkdir(exist_ok=True)
    if MAGISK_ZIP.exists():
        log(f'{MAGISK_ZIP} al gedownload.', text_widget)
        return MAGISK_ZIP
    log(f'Downloading Magisk from {MAGISK_URL}', text_widget)
    resp = requests.get(MAGISK_URL, stream=True)
    if resp.status_code != 200:
        show_error('Download Mislukt', f'Kon {MAGISK_URL} niet downloaden')
        return None
    with open(MAGISK_ZIP, 'wb') as fh:
        for chunk in resp.iter_content(chunk_size=8192):
            fh.write(chunk)
    log('Magisk download voltooid.', text_widget)
    return MAGISK_ZIP


def push_magisk(text_widget):
    ensure_adb(text_widget)
    if not device_connected():
        show_error('Geen toestel', '❌ Geen toestel gedetecteerd via ADB.')
        log('No device found for Magisk push.', text_widget)
        return
    if not MAGISK_ZIP.exists():
        show_error('Bestand ontbreekt', f'{MAGISK_ZIP} niet gevonden, download eerst.')
        log('Magisk zip missing', text_widget)
        return
    log('Pushing Magisk.zip naar /sdcard/', text_widget)
    adb_command(['push', str(MAGISK_ZIP), '/sdcard/'])
    show_info(
        'Flash Magisk',
        (
            'Magisk.zip staat nu op /sdcard/.\n'
            'Boot naar TWRP en kies Install → Magisk.zip om te flashen.\n'
            'Gebruik eventueel `adb sideload` als TWRP dat ondersteunt.'
        ),
    )


def check_root_status(text_widget):
    ensure_adb(text_widget)
    if not device_connected():
        show_error('Geen toestel', '❌ Geen toestel gedetecteerd via ADB.')
        log('No device for root check.', text_widget)
        return
    result = adb_command(['shell', 'su', '-v'])
    output = result.stdout.strip()
    if result.returncode == 0 and output:
        log(f'Root gevonden: {output}', text_widget)
        show_info('Rootstatus', f'✅ Root aanwezig: {output}')
        return
    result = adb_command(['shell', 'which', 'su'])
    output = result.stdout.strip()
    if result.returncode == 0 and output:
        log('su binary gevonden op ' + output, text_widget)
        show_info('Rootstatus', '✅ su binary aanwezig, maar versie onbekend.')
        return
    log('Geen roottoegang gevonden.', text_widget)
    show_info('Rootstatus', '❌ Geen root-toegang gevonden.')


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
            progress.setRange(0, 1)
            progress.setVisible(False)

    progress.setRange(0, 0)
    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def start_flash_recovery(text_widget, progress):

    def run():
        try:
            flash_twrp_gui(text_widget)
        finally:
            progress.setRange(0, 1)
            progress.setVisible(False)

    progress.setRange(0, 0)
    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def start_auto_flash(text_widget, progress):

    def run():
        try:
            auto_flash_j3(text_widget)
        finally:
            progress.setRange(0, 1)
            progress.setVisible(False)

    progress.setRange(0, 0)
    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def start_install_tools(text_widget, progress):

    def run():
        try:
            install_tools(text_widget)
        finally:
            progress.setRange(0, 1)
            progress.setVisible(False)

    progress.setRange(0, 0)
    progress.setVisible(True)
    threading.Thread(target=run, daemon=True).start()


def check_device(text_widget):
    ensure_adb(text_widget)
    if device_connected():
        log('Device detected!', text_widget)
    else:
        log('No device found.', text_widget)




class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('📱 Travelbot Flasher')
        self.setMinimumSize(600, 400)
        self.setStyleSheet('background-color: #E6E6FA;')

        main_layout = QVBoxLayout(self)

        title = QLabel('📱 Travelbot Flasher')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QtGui.QFont('Helvetica', 16, QtGui.QFont.Weight.Bold))
        main_layout.addWidget(title)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs, 1)

        # ---- Tab 1: Flasher ----
        self.tab_flasher = QWidget()
        flasher_layout = QVBoxLayout(self.tab_flasher)

        instructions = QLabel(INSTRUCTION_TEXT)
        instructions.setWordWrap(True)
        flasher_layout.addWidget(instructions)

        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        flasher_layout.addWidget(self.log_box, 1)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        flasher_layout.addWidget(self.progress)

        self.btn_detect_device = QPushButton('Detecteer Toestel')
        self.btn_detect_device.clicked.connect(lambda: check_device(self.log_box))
        self.btn_flash_twrp = QPushButton('Flash TWRP')
        self.btn_flash_twrp.clicked.connect(lambda: start_flash_recovery(self.log_box, self.progress))
        self.btn_flash_lineage = QPushButton('Flash LineageOS')
        self.btn_flash_lineage.clicked.connect(lambda: start_flash(self.log_box, None, self.progress))
        self.btn_install_apk = QPushButton('Install APK')
        self.btn_install_apk.clicked.connect(lambda: install_travelbot_apk(self.log_box))
        self.btn_reboot_recovery = QPushButton('Reboot to Recovery')
        self.btn_reboot_recovery.clicked.connect(lambda: reboot_device('recovery', self.log_box))
        self.btn_reboot_system = QPushButton('Reboot System')
        self.btn_reboot_system.clicked.connect(lambda: reboot_device('system', self.log_box))

        other_buttons = [
            ('Detect Download Mode', lambda: detect_device(self.log_box)),
            ('Check Heimdall', lambda: check_heimdall(self.log_box)),
            ('Install Tools', lambda: start_install_tools(self.log_box, self.progress)),
            ('Auto Flash TWRP', lambda: start_auto_flash(self.log_box, self.progress)),
            ('Download ROM', lambda: download_rom(self.log_box)),
            ('Open Log', open_log_file),
            ('Clear Log', lambda: clear_log(self.log_box)),
            ('Help', show_help),
        ]

        for text, func in other_buttons:
            btn = QPushButton(text)
            btn.clicked.connect(func)
            flasher_layout.addWidget(btn)

        # device dependent buttons
        for btn in [
            self.btn_detect_device,
            self.btn_flash_twrp,
            self.btn_flash_lineage,
            self.btn_install_apk,
            self.btn_reboot_recovery,
            self.btn_reboot_system,
        ]:
            flasher_layout.addWidget(btn)

        self.tabs.addTab(self.tab_flasher, '📲 Flasher')

        # ---- Tab 2: Root ----
        self.tab_root = QWidget()
        root_layout = QVBoxLayout(self.tab_root)

        root_info = QLabel('Root-toegang is optioneel maar vereist voor diepere systeemtoegang.')
        root_info.setWordWrap(True)
        root_layout.addWidget(root_info)

        self.btn_download_magisk = QPushButton('Download Magisk.zip')
        self.btn_download_magisk.clicked.connect(lambda: download_magisk(self.log_box))
        self.btn_push_magisk = QPushButton('Flash Magisk via TWRP')
        self.btn_push_magisk.clicked.connect(lambda: push_magisk(self.log_box))
        self.btn_check_root = QPushButton('Controleer Rootstatus')
        self.btn_check_root.clicked.connect(lambda: check_root_status(self.log_box))

        for btn in [self.btn_download_magisk, self.btn_push_magisk, self.btn_check_root]:
            root_layout.addWidget(btn)

        root_layout.addStretch()

        self.tabs.addTab(self.tab_root, '🔓 Geef Root-toegang')

        self.device_buttons = [
            self.btn_flash_twrp,
            self.btn_flash_lineage,
            self.btn_install_apk,
            self.btn_reboot_recovery,
            self.btn_reboot_system,
            self.btn_push_magisk,
            self.btn_check_root,
        ]

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_device_state)
        self.timer.start(3000)
        self.update_device_state()

    def update_device_state(self):
        connected = device_connected()
        for btn in self.device_buttons:
            btn.setEnabled(connected)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
