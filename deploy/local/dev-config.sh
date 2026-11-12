#!/usr/bin/env bash
# One command from public.sh's empty site to the dev workspace: the demo
# company built on one.DOMAIN, then the site linked to production's OneAdmin
# as a test workspace (link.sh), so its OneAI, mail, weather and news go
# through admin.4dl.app and nothing is billed.
#
#   bash dev-config.sh 4dl.dev
#
# Before the link: on admin.4dl.app, Workspaces, the menu's New Test Workspace
# with one.DOMAIN as its address. It shows the site config to paste when this
# asks. Safe to run again: the demo is built once, and a site already linked
# is left as it is unless RELINK=1.

set -euo pipefail

DOMAIN="${1:-}"
BENCH="${BENCH:-$HOME/one-bench}"
HERE="$(cd "$(dirname "$0")" && pwd)"

say() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

[ -n "$DOMAIN" ] || fail "Usage: bash dev-config.sh 4dl.dev"
WORKSPACE="one.$DOMAIN"
CONFIG="$BENCH/sites/$WORKSPACE/site_config.json"

export PATH="$HOME/.local/bin:$PATH"
# shellcheck disable=SC1091
. "$HOME/.nvm/nvm.sh"
cd "$BENCH"
# shellcheck disable=SC1090
. "$HOME/.one-local"
[ -n "${PUBLIC_ADMIN_PASSWORD:-}" ] || fail "No PUBLIC_ADMIN_PASSWORD in ~/.one-local; run public.sh first."
[ -f "$CONFIG" ] || fail "No site $WORKSPACE; run public.sh $DOMAIN first."
[ "$(jq -r '.one_dev // 0' "$CONFIG")" = 1 ] || fail "$WORKSPACE is not marked one_dev; run public.sh $DOMAIN again, which marks it."
[ "$(jq -r '.one_admin // 0' "$CONFIG")" != 1 ] || fail "$WORKSPACE is an admin site. The dev bench keeps a workspace only."

if [ "$(bench --site "$WORKSPACE" execute frappe.is_setup_complete 2>/dev/null | tail -1)" = "true" ]; then
	echo "$WORKSPACE: already set up"
else
	say "The demo company on $WORKSPACE (a few minutes)"
	bench --site "$WORKSPACE" execute onedesk.one_demo.build.load \
		--kwargs "$(jq -cn --arg password "$PUBLIC_ADMIN_PASSWORD" '{password: $password}')"
fi

if [ -n "$(jq -r '.one_token // empty' "$CONFIG")" ] && [ "${RELINK:-0}" != 1 ]; then
	echo "$WORKSPACE: linked to $(jq -r '.one_admin_url' "$CONFIG") as $(jq -r '.one_tenant' "$CONFIG"); RELINK=1 to link it again"
else
	say "Linking $WORKSPACE to production's OneAdmin"
	echo "On admin.4dl.app: Workspaces, menu, New Test Workspace, address $WORKSPACE."
	bash "$HERE/link.sh" "$WORKSPACE"
fi

say "Ready"
cat <<DONE
  https://$WORKSPACE    the demo company, a test workspace of admin.4dl.app

The demo's people sign in with PUBLIC_ADMIN_PASSWORD from ~/.one-local.
Pack the rescue kit again now that the site config changed:
  env/bin/python apps/onedesk/scripts/rescue.py pack
DONE
