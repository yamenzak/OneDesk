#!/usr/bin/env bash
# Run the dev bench as a system service: bench start at boot, again within
# seconds if it stops, with no terminal open. Run it as the bench's user,
# after setup.sh:
#
#   bash always-on.sh          turn it on
#   bash always-on.sh off      back to bench start by hand
#
# Then: sudo systemctl restart one-bench   after a change to hooks.py
#       journalctl -u one-bench -f         to watch what bench start prints

set -euo pipefail

BENCH="${BENCH:-$HOME/one-bench}"
UNIT=/etc/systemd/system/one-bench.service

if [ "${1:-}" = off ]; then
	sudo systemctl disable --now one-bench >/dev/null 2>&1 || true
	sudo rm -f "$UNIT"
	sudo systemctl daemon-reload
	echo "Off. Run bench start yourself again."
	exit 0
fi

[ -d "$BENCH/apps/onedesk" ] || { echo "No bench at $BENCH yet; run setup.sh first." >&2; exit 1; }
# shellcheck disable=SC1091
. "$HOME/.nvm/nvm.sh"
NODE_BIN="$(dirname "$(command -v node)")"

sudo tee "$UNIT" >/dev/null <<UNIT
[Unit]
Description=One dev bench (bench start)
After=network-online.target mariadb.service
Wants=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$BENCH
Environment=PATH=$HOME/.local/bin:$NODE_BIN:/usr/local/bin:/usr/bin:/bin
ExecStart=$HOME/.local/bin/bench start
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now one-bench >/dev/null
sleep 3
systemctl is-active --quiet one-bench && echo "On. The bench now runs by itself, and starts again after a reboot."
