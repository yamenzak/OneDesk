set -euo pipefail

[ "$(id -u)" = 0 ] || { echo "Run this as root." >&2; exit 1; }

NAME=one-copies
HOME_OF="/home/$NAME"

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq podman uidmap slirp4netns passt fuse-overlayfs openssl

ask() {
	curl -fsS --noproxy '*' --connect-timeout 1 -m 3 "$@" 2>/dev/null || true
}
found=""
heard() {
	if [ -n "$2" ]; then
		found="$found${found:+,}\"$1\":\"$(printf '%s' "$2" | head -c 49152 | base64 -w0)\""
	fi
}
heard oracle "$(ask -H 'Authorization: Bearer Oracle' http://169.254.169.254/opc/v2/instance/canonicalRegionName)"
token=$(ask -X PUT -H 'X-aws-ec2-metadata-token-ttl-seconds: 60' http://169.254.169.254/latest/api/token)
if [ -n "$token" ]; then
	heard aws "$(ask -H "X-aws-ec2-metadata-token: $token" http://169.254.169.254/latest/dynamic/instance-identity/document)"
fi
heard google "$(ask -H 'Metadata-Flavor: Google' http://metadata.google.internal/computeMetadata/v1/instance/zone)"
heard azure "$(ask -H 'Metadata: true' 'http://169.254.169.254/metadata/instance/compute?api-version=2021-02-01')"
heard digitalocean "$(ask http://169.254.169.254/metadata/v1/region)"
heard hetzner "$(ask http://169.254.169.254/hetzner/v1/metadata/availability-zone)"
heard vultr "$(ask http://169.254.169.254/v1.json)"
token=$(ask -X PUT -H 'Metadata-Token-Expiry-Seconds: 60' http://169.254.169.254/v1/token)
if [ -n "$token" ]; then
	heard akamai "$(ask -H "Metadata-Token: $token" -H 'Accept: application/json' http://169.254.169.254/v1/instance)"
fi
heard scaleway "$(ask 'http://169.254.42.42/conf?format=json')"
said="{\"server\":\"$ONE_SERVER\",\"found\":{$found}}"
signature=$(printf '%s' "$said" | openssl dgst -sha256 -hmac "$ONE_AGENT" -r | cut -d' ' -f1)
curl -fsS -m 30 -X POST -H 'Content-Type: application/json' -H 'User-Agent: OneAgent/1.0' -H "X-One-Agent: $signature" --data-binary "$said" "$ONE_ADMIN/api/method/onedesk.one_admin.servers.located" >/dev/null \
	|| echo "OneAdmin wasn't told which cloud this machine is on, so it shows Other." >&2

id "$NAME" >/dev/null 2>&1 || useradd -m -s /bin/bash -c "One copies" "$NAME"
chmod 750 "$HOME_OF"
grep -q "^$NAME:" /etc/subuid || usermod --add-subuids 200000-265535 --add-subgids 200000-265535 "$NAME"

if id -nG "$NAME" | grep -qw sudo; then
	echo "$NAME is in the sudo group, so it could read this machine's keys. Stopped." >&2
	exit 1
fi
for held in /root /home/*; do
	[ "$held" = "$HOME_OF" ] && continue
	if sudo -u "$NAME" test -r "$held"; then
		echo "$NAME can read $held, so a copy could read what is kept there. Stopped: run chmod 750 $held and connect again." >&2
		exit 1
	fi
done

loginctl enable-linger "$NAME"
uid=$(id -u "$NAME")
for _ in $(seq 1 30); do
	[ -S "/run/user/$uid/bus" ] && break
	sleep 1
done

as_copies() {
	sudo -u "$NAME" env XDG_RUNTIME_DIR="/run/user/$uid" DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$uid/bus" "$@"
}

install -d -m 700 -o "$NAME" -g "$NAME" "$HOME_OF/box" "$HOME_OF/.config" "$HOME_OF/.config/systemd" "$HOME_OF/.config/systemd/user"
cat > "$HOME_OF/box/Containerfile" <<'IMAGE'
FROM docker.io/library/ubuntu:24.04
RUN apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq systemd systemd-sysv dbus cron sudo curl ca-certificates python3 git gnupg lsb-release
RUN systemctl enable cron
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
IMAGE
chown "$NAME:$NAME" "$HOME_OF/box/Containerfile"
as_copies podman build -q -t one-box "$HOME_OF/box"

if ! as_copies podman container exists one-box; then
	as_copies podman create --name one-box --hostname one-box --systemd=always --memory="$ONE_MEMORY" --memory-swap="$ONE_MEMORY_SWAP" --pids-limit=4000 one-box
fi

cat > "$HOME_OF/.config/systemd/user/one-box.service" <<'UNIT'
[Unit]
Description=One's server for training and disposable copies

[Service]
ExecStart=/usr/bin/podman start -a one-box
ExecStop=/usr/bin/podman stop -t 60 one-box
Restart=always
RestartSec=30

[Install]
WantedBy=default.target
UNIT
chown "$NAME:$NAME" "$HOME_OF/.config/systemd/user/one-box.service"
as_copies systemctl --user daemon-reload
as_copies systemctl --user enable --now one-box.service

for _ in $(seq 1 60); do
	as_copies podman exec one-box true 2>/dev/null && break
	sleep 2
done

(umask 077; printf '%s' "$ONE_BOX" | base64 -d > "$HOME_OF/box/first-boot")
chown "$NAME:$NAME" "$HOME_OF/box/first-boot"
as_copies podman cp "$HOME_OF/box/first-boot" one-box:/root/first-boot
rm -f "$HOME_OF/box/first-boot"
as_copies podman exec -d one-box bash -c 'bash /root/first-boot > /root/first-boot.log 2>&1'

echo "Connected. The server is building itself, which takes about 30 minutes; OneAdmin shows it as Up when it is ready."
