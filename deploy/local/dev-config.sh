#!/usr/bin/env bash
# One command from public.sh's two empty sites to a dev pair that works: the
# setup wizard done on each, OneAdmin Settings filled with the dev values, and
# the workspace linked to the dev OneAdmin so its OneAI, weather and news go
# through it.
#
#   cp ~/one-bench/apps/onedesk/deploy/local/dev.example.json ~/.one-dev.json
#   chmod 600 ~/.one-dev.json      then fill it in
#   bash dev-config.sh 4dl.dev
#
# Safe to run again; the wizard is skipped where it is done, and the settings
# are written again from the file, so the file is where a dev key changes.
#
# It never reaches production, and refuses to help it: only sites public.sh
# marked one_dev are touched, Stripe live keys are refused, and the Frappe
# Cloud and Cloudflare fields that would let a dev OneAdmin build a real site
# or rewrite production's tokens and routes are written blank.

set -euo pipefail

DOMAIN="${1:-}"
BENCH="${BENCH:-$HOME/one-bench}"
FILE="${DEV_CONFIG:-$HOME/.one-dev.json}"

say() { printf '\n\033[1;34m== %s\033[0m\n' "$*"; }
fail() { printf '\n\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

[ -n "$DOMAIN" ] || fail "Usage: bash dev-config.sh 4dl.dev"
[ -f "$FILE" ] || fail "No $FILE. Copy deploy/local/dev.example.json there, chmod 600 it, and fill it in."
jq empty "$FILE" 2>/dev/null || fail "$FILE is not valid JSON."
WORKSPACE="one.$DOMAIN"
ADMIN="admin.$DOMAIN"

export PATH="$HOME/.local/bin:$PATH"
# shellcheck disable=SC1091
. "$HOME/.nvm/nvm.sh"
cd "$BENCH"
# shellcheck disable=SC1090
. "$HOME/.one-local"
[ -n "${PUBLIC_ADMIN_PASSWORD:-}" ] || fail "No PUBLIC_ADMIN_PASSWORD in ~/.one-local; run public.sh first."

for site in "$WORKSPACE" "$ADMIN"; do
	[ -f "sites/$site/site_config.json" ] || fail "No site $site; run public.sh $DOMAIN first."
	[ "$(jq -r '.one_dev // 0' "sites/$site/site_config.json")" = 1 ] || fail "$site is not marked one_dev; run public.sh $DOMAIN again, which marks it."
done
[ "$(jq -r '.one_admin // 0' "sites/$ADMIN/site_config.json")" = 1 ] || fail "$ADMIN is not an admin site."

if jq -r '.one_admin_settings | to_entries[] | .value' "$FILE" | grep -qE '^(sk|pk|rk)_live_'; then
	fail "$FILE holds a Stripe live key. Dev takes test keys only (pk_test_, sk_test_)."
fi

# --- The setup wizard, once per site ---------------------------------------------------
wizard() {
	local site="$1" company="$2" abbr="$3"
	if [ "$(bench --site "$site" execute frappe.is_setup_complete 2>/dev/null | tail -1)" = "true" ]; then
		echo "$site: wizard already done"
		return
	fi
	say "Setup wizard on $site"
	local year
	year="$(date +%Y)"
	local args
	args="$(jq -c --arg company "$company" --arg abbr "$abbr" --arg password "$PUBLIC_ADMIN_PASSWORD" --arg year "$year" '{args: (.owner + {
		company_name: $company, company_abbr: $abbr, password: $password,
		fy_start_date: ($year + "-01-01"), fy_end_date: ($year + "-12-31"),
		setup_demo: 0, onedesk_theme: "Light",
		onedesk_day_starts: "08:00:00", onedesk_day_ends: "17:00:00", onedesk_weekly_off: "Sunday"
	})}' "$FILE")"
	bench --site "$site" execute frappe.desk.page.setup_wizard.setup_wizard.setup_complete --kwargs "$args"
}
wizard "$WORKSPACE" "$(jq -r '.workspace_company[0]' "$FILE")" "$(jq -r '.workspace_company[1]' "$FILE")"
wizard "$ADMIN" "$(jq -r '.admin_company[0]' "$FILE")" "$(jq -r '.admin_company[1]' "$FILE")"

# --- OneAdmin Settings ---------------------------------------------------------------------
say "OneAdmin Settings on $ADMIN"
values="$(jq -c '.one_admin_settings + {
	press_team: "", press_token: "", press_bench: "", press_plan: "",
	cloudflare_master_token: "", cloudflare_token: "", cloudflare_kv: "", cloudflare_zone: "",
	tenant_domain: "", mail_domain: ""
} | with_entries(select(.value != null))' "$FILE")"
bench --site "$ADMIN" execute frappe.client.set_value \
	--kwargs "$(jq -cn --argjson v "$values" '{doctype: "One Admin Settings", name: "One Admin Settings", fieldname: $v}')" >/dev/null
echo "written: $(jq -r 'keys | join(", ")' <<<"$values")"

# --- The workspace speaks to the dev OneAdmin as its house workspace -----------------------
# The admin site linked itself to its own workspace (house.link, after every
# migrate); the dev workspace takes the same tenant and token, so it is served
# as ours: never billed, never refused for credits.
say "Linking $WORKSPACE to $ADMIN"
bench --site "$ADMIN" migrate >/dev/null
tenant="$(jq -r '.one_tenant // empty' "sites/$ADMIN/site_config.json")"
token="$(jq -r '.one_token // empty' "sites/$ADMIN/site_config.json")"
[ -n "$tenant" ] && [ -n "$token" ] || fail "$ADMIN has not linked itself to its own workspace yet."
bench --site "$WORKSPACE" set-config one_tenant "$tenant"
bench --site "$WORKSPACE" set-config one_token "$token"
bench --site "$WORKSPACE" set-config one_admin_url "https://$ADMIN"
for site in "$WORKSPACE" "$ADMIN"; do bench --site "$site" clear-cache; done

say "Ready"
cat <<DONE
  https://$WORKSPACE    a workspace, linked to the dev OneAdmin
  https://$ADMIN  OneAdmin, with the dev settings

Sign in as $(jq -r '.owner.email' "$FILE") with PUBLIC_ADMIN_PASSWORD from ~/.one-local.
Press Test Gateway in OneAdmin Settings to check the AI gateway.
DONE
