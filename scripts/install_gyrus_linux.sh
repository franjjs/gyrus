#!/bin/bash
set -e

# Get project root (parent of this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure venv exists and python is available
if [ ! -x "$PROJECT_ROOT/.venv/bin/python" ]; then
  echo "ERROR: Python venv not found at $PROJECT_ROOT/.venv. Please create it first."
  exit 1
fi

USER_NAME=$(whoami)
WORKDIR="$PROJECT_ROOT"
VENV_PATH="$PROJECT_ROOT/.venv/bin/python"
DISPLAY_VAR=${DISPLAY:-":0"}
XAUTHORITY_FILE="/home/$USER_NAME/.Xauthority"

USER_SERVICE_DIR="$HOME/.config/systemd/user"
mkdir -p "$USER_SERVICE_DIR"
USER_SERVICE_FILE="$USER_SERVICE_DIR/gyrus.service"

cat <<EOF > "$USER_SERVICE_FILE"
[Unit]
Description=Gyrus Clipboard Daemon (User Service)
After=graphical-session.target

[Service]
Type=simple
WorkingDirectory=$WORKDIR
ExecStart=$VENV_PATH -m gyrus.main
Restart=on-failure
Environment=PYTHONUNBUFFERED=1
Environment=DISPLAY=$DISPLAY_VAR
Environment=XAUTHORITY=$XAUTHORITY_FILE

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now gyrus

cat <<EOM

✅ Gyrus user systemd service created and started.

Useful commands:
  Check status:     systemctl --user status gyrus
  View logs:        journalctl --user -u gyrus -f
  Stop service:     systemctl --user stop gyrus
  Start service:    systemctl --user start gyrus
  Restart service:  systemctl --user restart gyrus
  Disable service:  systemctl --user disable gyrus
  Enable at login:  systemctl --user enable gyrus
  Check enabled:    systemctl --user is-enabled gyrus

If you see X11 errors, ensure you run this script from a graphical session and that DISPLAY and XAUTHORITY are correct.
EOM
