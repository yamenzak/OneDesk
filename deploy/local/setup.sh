#!/usr/bin/env bash
# One on your own machine: a bench in WSL2 Ubuntu (24.04 or later) with frappe, erpnext,
# hrms and onedesk at the commits upstream.json records, and two sites:
#
#   one.localhost    a workspace, for building and trying One
#   admin.localhost  an admin site (one_admin), for building OneAdmin
#
# Run it inside Ubuntu, as your own user (not root):
#
#   bash setup.sh
#
# It is safe to run again: every step checks before it acts. It asks for your
# sudo password once and, if you have not signed in to GitHub yet, opens the
# GitHub sign-in so it can clone onedesk.
#
# Passwords it makes are kept in ~/.one-local (readable by you only).

set -euo pipefail

BENCH="${BENCH:-$HOME/one-bench}"
REPO="${REPO:-https://github.com/yamenzak/onedesk}"
BRANCH="${BRANCH:-main}"
PY_VERSION=3.14
NODE_VERSION=24
SITES=(one.localhost admin.localhost)

say() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -ne 0 ] || fail "Run this as your own user, not root."
grep -qi microsoft /proc/version || echo "Not WSL; carrying on as plain Linux."

# --- WSL itself: systemd on, and /etc/hosts kept, so the two sites resolve ----
restart=0
if grep -qi microsoft /proc/version; then
	if ! grep -q "^systemd=true" /etc/wsl.conf 2>/dev/null; then
		printf '\n[boot]\nsystemd=true\n' | sudo tee -a /etc/wsl.conf >/dev/null
		restart=1
	fi
	if ! grep -q "^generateHosts=false" /etc/wsl.conf 2>/dev/null; then
		printf '\n[network]\ngenerateHosts=false\n' | sudo tee -a /etc/wsl.conf >/dev/null
		restart=1
	fi
fi
for site in "${SITES[@]}"; do
	grep -q " $site" /etc/hosts || echo "127.0.0.1 $site" | sudo tee -a /etc/hosts >/dev/null
done
if [ "$restart" = 1 ] || [ "$(ps -p 1 -o comm=)" != "systemd" ]; then
	fail "WSL settings changed. In PowerShell run:  wsl --shutdown
Then open Ubuntu again and run this script again."
fi

# --- System packages ----------------------------------------------------------
say "System packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
	git curl ca-certificates build-essential pkg-config jq unzip cron \
	mariadb-server mariadb-client libmariadb-dev redis-server \
	libffi-dev libssl-dev fontconfig xfonts-75dpi xfonts-base \
	gh >/dev/null
# bench starts its own redis on 11000 and 13000; the system one only takes memory.
sudo systemctl disable --now redis-server >/dev/null 2>&1 || true

if ! wkhtmltopdf --version 2>/dev/null | grep -q "with patched qt"; then
	say "wkhtmltopdf (patched qt, for headers and footers on prints)"
	deb=/tmp/wkhtmltox.deb
	curl -fsSL -o "$deb" https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.jammy_amd64.deb
	# Built for 22.04; where a newer Ubuntu can't take it, the distribution's
	# own wkhtmltopdf prints everything but headers and footers.
	sudo apt-get install -y -qq "$deb" >/dev/null 2>&1 || sudo apt-get install -y -qq wkhtmltopdf >/dev/null
	rm -f "$deb"
fi

# --- Passwords ------------------------------------------------------------------
SECRETS="$HOME/.one-local"
if [ ! -f "$SECRETS" ]; then
	umask 077
	{
		echo "DB_ROOT_PASSWORD=$(openssl rand -hex 16)"
		echo "ADMIN_PASSWORD=admin"
	} >"$SECRETS"
	umask 022
fi
# shellcheck disable=SC1090
. "$SECRETS"

# --- MariaDB --------------------------------------------------------------------
say "MariaDB"
sudo tee /etc/mysql/mariadb.conf.d/99-frappe.cnf >/dev/null <<'CNF'
[mysqld]
character-set-client-handshake = FALSE
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
innodb_buffer_pool_size = 1G

[mysql]
default-character-set = utf8mb4
CNF
sudo systemctl enable --now mariadb >/dev/null
sudo systemctl restart mariadb
if ! mariadb -uroot -p"$DB_ROOT_PASSWORD" -e "select 1" >/dev/null 2>&1; then
	sudo mariadb -e "ALTER USER root@localhost IDENTIFIED VIA unix_socket OR mysql_native_password USING PASSWORD('$DB_ROOT_PASSWORD'); FLUSH PRIVILEGES;"
fi

# --- Python, bench, Node ----------------------------------------------------------
say "Python $PY_VERSION and bench"
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null
uv python install "$PY_VERSION" >/dev/null
PY="$(uv python find "$PY_VERSION")"
command -v bench >/dev/null || uv tool install frappe-bench >/dev/null

say "Node $NODE_VERSION and yarn"
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] || curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash >/dev/null
# shellcheck disable=SC1091
. "$NVM_DIR/nvm.sh"
nvm install "$NODE_VERSION" >/dev/null
nvm alias default "$NODE_VERSION" >/dev/null
command -v yarn >/dev/null || npm install -g yarn >/dev/null

# --- GitHub, for the private repository -------------------------------------------
say "GitHub"
gh auth status >/dev/null 2>&1 || gh auth login --hostname github.com --git-protocol https --web
gh auth setup-git

# --- The bench ----------------------------------------------------------------------
if [ ! -d "$BENCH/apps/frappe" ]; then
	say "bench init (several minutes)"
	bench init "$BENCH" --frappe-branch develop --python "$PY" --verbose
fi
cd "$BENCH"
for app in erpnext hrms; do
	[ -d "apps/$app" ] || { say "get-app $app"; bench get-app --branch develop "https://github.com/frappe/$app"; }
done
[ -d apps/onedesk ] || { say "get-app onedesk"; bench get-app --branch "$BRANCH" "$REPO"; }
[ -d apps/onedesk ] || fail "onedesk did not arrive in $BENCH/apps."

# --- Pin frappe, erpnext and hrms to what onedesk was last checked against ------------
say "Pinning to upstream.json"
moved=0
for app in frappe erpnext hrms; do
	sha="$(jq -r ".$app.sha" apps/onedesk/upstream.json)"
	dir="apps/$app"
	remote="$(git -C "$dir" remote | head -1)"
	if [ "$(git -C "$dir" rev-parse HEAD)" != "$sha" ]; then
		git -C "$dir" fetch -q --depth 1 "$remote" "$sha"
		git -C "$dir" checkout -q "$sha"
		moved=1
	fi
	echo "$app $(git -C "$dir" rev-parse --short HEAD)"
done
if [ "$moved" = 1 ]; then
	say "Requirements and build for the pinned commits"
	bench setup requirements
	bench build
fi
uv pip install -q --python env/bin/python pytest openpyxl

# --- Sites ----------------------------------------------------------------------------
bench config dns_multitenant on >/dev/null
# Installing an app writes to the cache and the queue, which bench start would
# run; until then, start them here, or an app's own setup fails halfway.
redis-cli -p 13000 ping >/dev/null 2>&1 || redis-server config/redis_cache.conf --daemonize yes >/dev/null
redis-cli -p 11000 ping >/dev/null 2>&1 || redis-server config/redis_queue.conf --daemonize yes >/dev/null
make_site() {
	local site="$1" admin="$2"
	[ -d "sites/$site" ] && return
	say "Site $site"
	bench new-site "$site" --db-root-username root --db-root-password "$DB_ROOT_PASSWORD" --admin-password "$ADMIN_PASSWORD"
	bench --site "$site" set-config -p developer_mode 1
	bench --site "$site" set-config host_name "http://$site:8000"
	[ "$admin" = 1 ] && bench --site "$site" set-config -p one_admin 1
	bench --site "$site" install-app erpnext hrms onedesk
	bench --site "$site" migrate
}
make_site one.localhost 0
make_site admin.localhost 1
# No `bench use`: with a current site, bench serve answers every address as
# that one site, and admin.localhost would open the workspace.

# bench start runs the Procfile. bench watch rebuilds the desk's own JS and CSS
# on save; onedesk's islands (frontend/) have their own watcher, added here.
grep -q "^islands:" Procfile || echo "islands: cd apps/onedesk/frontend && yarn dev" >>Procfile

# bench start runs its own redis on these ports, and stops everything if
# either is already taken.
redis-cli -p 13000 shutdown nosave >/dev/null 2>&1 || true
redis-cli -p 11000 shutdown nosave >/dev/null 2>&1 || true

say "Ready"
cat <<DONE
Start everything (web, worker, socketio, redis, and the watchers that rebuild
on save):

  cd $BENCH && bench start

Then open, in your browser (on a server, first connect with
ssh -L 8000:localhost:8000 -L 9000:localhost:9000 you@server):

  http://one.localhost:8000      a workspace
  http://admin.localhost:8000    OneAdmin

Sign in as Administrator with the password in ~/.one-local and go through the
setup wizard once on each. The code is in $BENCH/apps/onedesk; open it in VS
Code from Ubuntu with:  code $BENCH/apps/onedesk
DONE
