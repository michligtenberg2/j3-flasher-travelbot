#!/bin/bash
# Minimal example script for flashing LineageOS on the Samsung Galaxy J3 (2016)
# This script demonstrates the basic steps for manual flashing using adb and fastboot
#
# Prerequisites:
# - Device must have Developer Options enabled with USB Debugging
# - OEM unlocking must be enabled
# - Device should be connected via USB
# - twrp.img and lineage.zip files should be present in the current directory

set -e  # Exit on any error
set -u  # Exit on undefined variables

# Function to check if required files exist
check_files() {
    if [ ! -f "twrp.img" ]; then
        echo "Error: twrp.img not found in current directory"
        exit 1
    fi
    
    if [ ! -f "lineage.zip" ]; then
        echo "Error: lineage.zip not found in current directory"
        exit 1
    fi
}

# Function to check if required tools are available
check_tools() {
    if ! command -v adb &> /dev/null; then
        echo "Error: adb not found. Please install Android platform tools"
        exit 1
    fi
    
    if ! command -v fastboot &> /dev/null; then
        echo "Error: fastboot not found. Please install Android platform tools"
        exit 1
    fi
}

# Main flashing process
main() {
    echo "Starting LineageOS flash process for Samsung Galaxy J3..."
    
    # Check prerequisites
    check_tools
    check_files
    
    # Step 1: Reboot device to bootloader/fastboot mode
    echo "Rebooting device to bootloader mode..."
    adb reboot bootloader
    
    # Wait for device to enter fastboot mode
    echo "Waiting for device to enter fastboot mode..."
    sleep 10
    
    # Step 2: Flash TWRP recovery
    echo "Flashing TWRP recovery..."
    fastboot flash recovery twrp.img
    
    # Step 3: Reboot to recovery mode
    echo "Rebooting to recovery mode..."
    fastboot reboot
    
    # Wait for device to boot into recovery
    echo "Waiting for device to boot into recovery mode..."
    sleep 15
    
    # Step 4: Sideload LineageOS ROM
    echo "Sideloading LineageOS ROM..."
    adb sideload lineage.zip
    
    echo "Flash process completed successfully!"
    echo "The device should now reboot automatically."
}

# Run main function
main "$@"
