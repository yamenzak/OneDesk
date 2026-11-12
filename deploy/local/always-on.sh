#!/usr/bin/env bash
# Run the dev bench as a system service: bench start at boot, again within
# seconds if it stops, with no terminal open. Where Claude Code is installed
# and signed in, Remote Control runs the same way (one-claude), so a session
# can be opened on this machine from claude.ai/code or the Claude app at any
# time. Run it as the bench's user, after setup.sh:
#
#   bash always-on.sh          turn it on
#   bash always-on.sh off      back to bench start by hand
#
# The workspace backs itself up to production's keeper (one/backup.py), so
# nothing here is scheduled for it; the one-dev-backup timer an older run
# made is taken away.
#
# Then: sudo systemctl restart one-bench   after a change to hooks.py
#       journalctl -u one-bench -f         to watch what bench start prints

set -euo pipefail

BENCH="${BENCH:-$HOME/one-bench}"
UNIT=/etc/systemd/system/one-bench.service
CLAUDE_UNIT=/etc/systemd/system/one-claude.service
OLD_BACKUP=(/etc/systemd/system/one-dev-backup.service /etc/systemd/system/one-dev-backup.timer)

sudo systemctl disable --now one-dev-backup.timer >/dev/null 2>&1 || true
sudo rm -f "${OLD_BACKUP[@]}"

if [ "${1:-}" = off ]; then
	sudo systemctl disable --now one-bench one-claude >/dev/null 2>&1 || true
	sudo rm -f "$UNIT" "$CLAUDE_UNIT"
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
Environment=NODE_OPTIONS=--max-old-space-size=2048
ExecStart=$HOME/.local/bin/bench start
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=20

[Install]
WantedBy=multi-user.target
UNIT

# Remote Control, in the repository, sharing its directory with the bench so
# a change made from the phone is served at once. It needs to have been run
# by hand once (claude remote-control), which signs in and asks to be turned
# on; without that it is left out.
if [ -x "$HOME/.local/bin/claude" ] && [ -d "$HOME/.claude" ]; then
	sudo tee "$CLAUDE_UNIT" >/dev/null <<UNIT
[Unit]
Description=Claude Code Remote Control in onedesk
After=network-online.target one-bench.service
Wants=network-online.target

[Service]
User=$(id -un)
WorkingDirectory=$BENCH/apps/onedesk
Environment=PATH=$HOME/.local/bin:$NODE_BIN:/usr/local/bin:/usr/bin:/bin
Environment=HOME=$HOME
ExecStart=$HOME/.local/bin/claude remote-control --spawn=same-dir
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
UNIT
fi

sudo systemctl daemon-reload
sudo systemctl enable --now one-bench >/dev/null
[ -f "$CLAUDE_UNIT" ] && sudo systemctl enable --now one-claude >/dev/null
sleep 3
systemctl is-active --quiet one-bench && echo "On. The bench now runs by itself, and starts again after a reboot."
if [ -f "$CLAUDE_UNIT" ]; then
	systemctl is-active --quiet one-claude && echo "Remote Control too: open a session from claude.ai/code or the Claude app."
else
	echo "Remote Control left out: run 'claude remote-control' in apps/onedesk once by hand, then this again."
fi
