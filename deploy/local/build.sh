#!/usr/bin/env bash
# bench build, without taking the machine down. A full build of frappe, erpnext,
# hrms and onedesk takes several GB on its own; beside bench start's two
# watchers, the web server, the worker, both redis servers and MariaDB, a small
# server runs out of memory and hangs. So this stops the one-bench service for
# the build and starts it again afterwards, whether the build passed or not.
# The sites are offline for that minute or two.
#
#   bash build.sh                  every app, as bench build
#   bash build.sh --app onedesk    one app, which is usually all that changed
#
# setup.sh makes `bench build` in your shell run this, so nothing needs
# remembering. The Remote Control service (one-claude) is left alone: a
# session started by it may be the one running the build.

set -euo pipefail

BENCH="${BENCH:-$HOME/one-bench}"
LOCK=/tmp/one-build.lock

exec 9>"$LOCK"
flock -n 9 || { echo "Another build is running; wait for it." >&2; exit 1; }

cd "$BENCH"
# shellcheck disable=SC1091
[ -s "$HOME/.nvm/nvm.sh" ] && . "$HOME/.nvm/nvm.sh"
export PATH="$HOME/.local/bin:$PATH"
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=2048}"

stopped=0
if systemctl is-active --quiet one-bench 2>/dev/null; then
	echo "Stopping one-bench for the build; the sites are offline until it is done."
	sudo systemctl stop one-bench
	stopped=1
elif ss -ltn 2>/dev/null | grep -q ':8000 '; then
	if [ "${ONE_BUILD_ANYWAY:-}" != 1 ]; then
		echo "bench start is running in a terminal. Stop it (Ctrl+C) and build again," >&2
		echo "or ONE_BUILD_ANYWAY=1 to build beside it." >&2
		exit 1
	fi
fi

back() {
	if [ "$stopped" = 1 ]; then
		sudo systemctl start one-bench
		echo "one-bench started again."
	fi
}
trap back EXIT

command bench build "$@"
