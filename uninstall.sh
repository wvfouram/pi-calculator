#!/bin/bash
# Removes Calculator.
SRC="$(cd "$(dirname "$0")" && pwd)"
if [ "$(id -u)" = "0" ]; then
  echo "Run this as your normal user (not with sudo)."
  exit 1
fi

sudo rm -rf /opt/pi-calculator /usr/local/bin/pi-calculator /usr/share/applications/pi-calculator.desktop \
  /usr/share/icons/hicolor/scalable/apps/pi-calculator.svg
sudo update-desktop-database -q /usr/share/applications 2>/dev/null || true
echo "Calculator removed. Your settings are still in ~/.config/pi-calculator (delete that folder to remove them)."
