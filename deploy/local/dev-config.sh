#!/usr/bin/env bash
# One command from public.sh's two empty sites to a dev pair that works: the
# setup wizard done on each, OneAdmin Settings filled with the dev values, the
# workspace linked to the dev OneAdmin so its OneAI, weather and news go
# through it, and, given a Cloudflare master token, Set Up Cloudflare run for
# the dev environment.
#
#   cp ~/one-bench/apps/onedesk/deploy/local/dev.example.json ~/.one-dev.json
#   chmod 600 ~/.one-dev.json      then fill it in
#   bash dev-config.sh 4dl.dev
#
# Safe to run again; the wizard is skipped where it is done, the settings are
# written again from the file (an empty value is left as the site has it), and
# Set Up Cloudflare finds what it made before.
#
# The dev OneAdmin is the dev environment: Environment is always written as
# dev, so everything Set Up Cloudflare makes is named apart from production's
# (one-mail-dev, one-sites-dev, "[one-dev] OneAI"), its catch-all is never taken
# from production, and it needs domains of its own, which may not be
# production's. Only sites public.sh marked one_dev are touched, and a Stripe
# live key is refused. The two things left by hand are the Stripe test keys
# and the OpenWeather key, in the file, and the webhook in Stripe's test mode.

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
for key in tenant_domain mail_domain sender_email; do
	value="$(jq -r ".one_admin_settings.$key // empty" "$FILE")"
	[ -n "$value" ] || fail "$FILE has no $key. Dev brings its own (dev.example.json has the usual ones)."
	case "$value" in
	t.4dl.app | m.4dl.app | noreply@4dl.app) fail "$key is production's ($value). Dev takes its own." ;;
	esac
done

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
# The site first knows every field the file names.
bench --site "$ADMIN" migrate >/dev/null
values="$(jq -c '.one_admin_settings | with_entries(select(.value != null and .value != "")) + {environment: "dev"}' "$FILE")"
bench --site "$ADMIN" execute frappe.client.set_value \
	--kwargs "$(jq -cn --argjson v "$values" '{doctype: "One Admin Settings", name: "One Admin Settings", fieldname: $v}')" >/dev/null
echo "written: $(jq -r 'keys | map(select(test("token|secret|key") | not)) | join(", ")' <<<"$values"), and the keys"

# --- Set Up Cloudflare, as the dev environment -------------------------------------------
if [ -n "$(jq -r '.one_admin_settings.cloudflare_master_token // empty' "$FILE")" ]; then
	say "Set Up Cloudflare for dev (a few minutes)"
	bench --site "$ADMIN" execute onedesk.one_admin.setup.run | tail -1 |
		jq -r '.[] | "  \(.state | ascii_upcase)\t\(.step)\t\(.detail)"' 2>/dev/null ||
		echo "  Set Up Cloudflare said nothing readable; open OneAdmin Settings and look under Last Setup."
else
	echo "No cloudflare_master_token in $FILE: Set Up Cloudflare left for later."
fi

# --- The workspace speaks to the dev OneAdmin as its house workspace -----------------------
# The admin site linked itself to its own workspace (house.link, after every
# migrate); the dev workspace takes the same tenant and token, so it is served
# as ours: never billed, never refused for credits.
say "Linking $WORKSPACE to $ADMIN"
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
  https://$ADMIN  OneAdmin, the dev environment

Sign in as $(jq -r '.owner.email' "$FILE") with PUBLIC_ADMIN_PASSWORD from ~/.one-local.
Press Test Gateway in OneAdmin Settings to check the AI gateway.

Left by hand, in Stripe's test mode: a webhook to
  https://$ADMIN/api/method/onedesk.one_admin.stripe.webhook
with these five events, its signing secret in stripe_webhook_secret:
  checkout.session.completed
  invoice.paid
  invoice.payment_failed
  customer.subscription.deleted
  charge.refunded
DONE
