#!/bin/sh
# Minimal example script for flashing LineageOS on the J3 (2016)
adb reboot bootloader
fastboot flash recovery twrp.img
fastboot reboot
sleep 5
adb sideload lineage.zip
