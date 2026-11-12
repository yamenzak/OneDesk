#!/usr/bin/env bash
# The dev bench on the internet, through a Cloudflare Tunnel: a workspace
# named after a domain you have in Cloudflare, reachable over HTTPS with no
# port opened on the server. It is linked to production's OneAdmin as a test
# workspace afterwards (dev-config.sh); the bench holds no OneAdmin of its own.
#
#   bash public.sh 4dl.dev      ->  https://one.4dl.dev    a workspace
#
# Run it after setup.sh, as the same user. It asks once for the Cloudflare
# sign-in (open the link it prints, pick the domain) and is safe to run again.
# The tunnel runs as a line of the Procfile, so the sites are online exactly
# while bench start is.
#
# The Administrator password of the site is made here and kept in
# ~/.one-local as PUBLIC_ADMIN_PASSWORD; it is on the internet, so it is
# never "admin".

set -euo pipefail

DOMAIN="${1:-}"
BENCH="${BENCH:-$HOME/one-bench}"
TUNNEL="${TUNNEL:-one-dev}"

say() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

[ -n "$DOMAIN" ] || fail "Usage: bash public.sh 4dl.dev"
[ -d "$BENCH/apps/onedesk" ] || fail "No bench at $BENCH yet; run setup.sh first."
WORKSPACE="one.$DOMAIN"

export PATH="$HOME/.local/bin:$PATH"
# shellcheck disable=SC1091
. "$HOME/.nvm/nvm.sh"
cd "$BENCH"

SECRETS="$HOME/.one-local"
# shellcheck disable=SC1090
. "$SECRETS"
if [ -z "${PUBLIC_ADMIN_PASSWORD:-}" ]; then
	echo "PUBLIC_ADMIN_PASSWORD=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 20)" >>"$SECRETS"
	# shellcheck disable=SC1090
	. "$SECRETS"
fi

# --- cloudflared ------------------------------------------------------------------
if ! command -v cloudflared >/dev/null; then
	say "cloudflared"
	deb=/tmp/cloudflared.deb
	curl -fsSL -o "$deb" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$(dpkg --print-architecture).deb"
	sudo apt-get install -y -qq "$deb" >/dev/null
	rm -f "$deb"
fi

if [ ! -f "$HOME/.cloudflared/cert.pem" ]; then
	say "Cloudflare sign-in: open the link below and choose $DOMAIN"
	cloudflared tunnel login
fi

tunnel_id() { cloudflared tunnel list -o json 2>/dev/null | jq -r --arg n "$TUNNEL" '(. // [])[] | select(.name == $n) | .id' | head -1; }
ID="$(tunnel_id)"
if [ -z "$ID" ]; then
	say "Tunnel $TUNNEL"
	cloudflared tunnel create "$TUNNEL" >/dev/null
	ID="$(tunnel_id)"
fi
[ -n "$ID" ] || fail "The tunnel $TUNNEL could not be made."

cloudflared tunnel route dns --overwrite-dns "$TUNNEL" "$WORKSPACE" >/dev/null

# Pages to the web server on 8000; /socket.io to a local nginx on 9001 in
# front of socketio on 9000. The Host header is set to the public name on
# both, which is how the site is found. socketio also refuses a connection
# whose Origin is missing or names another host ("Invalid origin"), and a
# browser sends no Origin on the first, same-origin request of the handshake;
# production's nginx sets it (proxy_set_header Origin), and so does this one.
command -v nginx >/dev/null || { say "nginx"; sudo apt-get install -y -qq nginx >/dev/null; }
sudo tee /etc/nginx/conf.d/one-dev-socketio.conf >/dev/null <<'NGINX'
server {
	listen 127.0.0.1:9001;
	location / {
		proxy_http_version 1.1;
		proxy_set_header Upgrade $http_upgrade;
		proxy_set_header Connection "upgrade";
		proxy_set_header Host $host;
		proxy_set_header Origin https://$host;
		proxy_read_timeout 3600s;
		proxy_pass http://127.0.0.1:9000;
	}
}
NGINX
sudo nginx -t -q && sudo systemctl reload-or-restart nginx

CONFIG="$HOME/.cloudflared/config.yml"
{
	echo "tunnel: $ID"
	echo "credentials-file: $HOME/.cloudflared/$ID.json"
	echo "ingress:"
	for host in "$WORKSPACE"; do
		echo "  - hostname: $host"
		echo "    path: ^/socket\\.io"
		echo "    service: http://127.0.0.1:9001"
		echo "    originRequest:"
		echo "      httpHostHeader: $host"
		echo "  - hostname: $host"
		echo "    service: http://localhost:8000"
		echo "    originRequest:"
		echo "      httpHostHeader: $host"
	done
	echo "  - service: http_status:404"
} >"$CONFIG"
cloudflared tunnel --config "$CONFIG" ingress validate >/dev/null

# --- The site --------------------------------------------------------------------
started=()
for port in 13000 11000; do
	if ! redis-cli -p "$port" ping >/dev/null 2>&1; then
		conf=config/redis_cache.conf
		[ "$port" = 11000 ] && conf=config/redis_queue.conf
		redis-server "$conf" --daemonize yes >/dev/null
		started+=("$port")
	fi
done

make_site() {
	local site="$1"
	[ -d "sites/$site" ] && return
	say "Site $site"
	bench new-site "$site" --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$PUBLIC_ADMIN_PASSWORD"
	bench --site "$site" set-config -p developer_mode 1
	bench --site "$site" set-config host_name "https://$site"
	# The desk, served by the dev server, looks for socketio on this port of
	# its own address; through the tunnel that is 443, which carries
	# /socket.io to 9000.
	bench --site "$site" set-config -p socketio_port 443
	bench --site "$site" install-app erpnext hrms onedesk
	bench --site "$site" migrate
}
make_site "$WORKSPACE"
# The mark dev-config.sh asks for before it writes anything to the site, and
# what lets it hold the demo company.
bench --site "$WORKSPACE" set-config -p one_dev 1 >/dev/null

for port in "${started[@]}"; do
	redis-cli -p "$port" shutdown nosave >/dev/null 2>&1 || true
done

grep -q "^tunnel:" Procfile || echo "tunnel: cloudflared tunnel --no-autoupdate --config $CONFIG run" >>Procfile

say "Ready"
cat <<DONE
Restart bench start (Ctrl+C, then bench start) so it runs the tunnel too, then
open:

  https://$WORKSPACE    a workspace

Then build the demo on it and link it to production's OneAdmin:
  bash apps/onedesk/deploy/local/dev-config.sh $DOMAIN
It is online while bench start runs.
DONE
