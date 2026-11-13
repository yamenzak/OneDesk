set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Run this as root." >&2; exit 1; }

NAME=one-copies
HOME_OF="/home/$NAME"
removed=""

gone() {
	echo "Removed $2."
	removed="$removed${removed:+,}\"$1\""
}

if id "$NAME" >/dev/null 2>&1; then
	if [ "$(getent passwd "$NAME" | cut -d: -f5)" != "One copies" ] || [ "$(getent passwd "$NAME" | cut -d: -f6)" != "$HOME_OF" ]; then
		echo "$NAME on this machine wasn't made by Connect Server, so nothing was removed." >&2
		exit 1
	fi
	uid=$(id -u "$NAME")
	as_copies() {
		sudo -u "$NAME" env XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" "$@"
	}

	unit="$HOME_OF/.config/systemd/user/one-box.service"
	if [ -f "$unit" ]; then
		as_copies systemctl --user disable --now one-box.service >/dev/null 2>&1 || true
		rm -f "$unit"
		as_copies systemctl --user daemon-reload >/dev/null 2>&1 || true
		gone unit "the one-box service"
	fi

	if as_copies podman container exists one-box 2>/dev/null; then
		as_copies podman rm -f -t 60 one-box >/dev/null
		gone container "the one-box container"
	fi

	if as_copies podman image exists one-box 2>/dev/null; then
		as_copies podman rmi -f one-box docker.io/library/ubuntu:24.04 >/dev/null 2>&1 || as_copies podman rmi -f one-box >/dev/null
		gone image "the one-box image and the Ubuntu image it was built from"
	fi
fi

if [ -e "/var/lib/systemd/linger/$NAME" ]; then
	loginctl disable-linger "$NAME"
	gone linger "$NAME's linger"
fi

if id "$NAME" >/dev/null 2>&1; then
	loginctl terminate-user "$NAME" >/dev/null 2>&1 || true
	for _ in $(seq 1 30); do
		pgrep -u "$NAME" >/dev/null || break
		sleep 1
	done
	pkill -KILL -u "$NAME" 2>/dev/null || true
fi

if grep -q "^$NAME:" /etc/subuid /etc/subgid 2>/dev/null; then
	sed -i "/^$NAME:/d" /etc/subuid /etc/subgid
	gone subuids "$NAME's subuids and subgids"
fi

if id "$NAME" >/dev/null 2>&1; then
	userdel -r "$NAME" >/dev/null 2>&1 || userdel "$NAME"
	gone user "the user $NAME"
fi
if [ -d "$HOME_OF" ]; then
	rm -rf -- "$HOME_OF"
	gone home "$HOME_OF"
fi

[ -n "$removed" ] || echo "Nothing Connect Server made was left on this machine."

said="{\"server\":\"$ONE_SERVER\",\"removed\":[$removed]}"
signature=$(printf '%s' "$said" | openssl dgst -sha256 -hmac "$ONE_AGENT" -r | cut -d' ' -f1)
if curl -fsS -m 30 -X POST -H 'Content-Type: application/json' -H 'User-Agent: OneAgent/1.0' -H "X-One-Agent: $signature" --data-binary "$said" "$ONE_ADMIN/api/method/onedesk.one_admin.releasing.released" >/dev/null; then
	echo "Released. OneAdmin has cleared $ONE_SERVER's addresses and keys."
else
	echo "OneAdmin wasn't told. Press Finish Release on $ONE_SERVER in OneAdmin." >&2
fi
echo "Podman and the packages Connect Server installed stay on this machine."
