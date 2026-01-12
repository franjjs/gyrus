#!/bin/bash
set -e

SERVICE_NAME="gyrus"
USER_SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

# Stop the user service if running
systemctl --user stop "$SERVICE_NAME" || true

# Disable the user service
systemctl --user disable "$SERVICE_NAME" || true

# Remove the service file
if [ -f "$USER_SERVICE_FILE" ]; then
  rm "$USER_SERVICE_FILE"
  echo "Removed $USER_SERVICE_FILE"
else
  echo "$USER_SERVICE_FILE not found."
fi

# Reload user systemd
systemctl --user daemon-reload

echo -e "\n✅ Gyrus user systemd service stopped, disabled, and removed."
