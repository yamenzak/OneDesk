#!/usr/bin/env bash
# Link a site on this bench to production's OneAdmin as a test workspace.
# On admin.4dl.app, Workspaces, the menu's New Test Workspace shows the site
# config once; paste it here:
#
#   bash link.sh one.4dl.dev        paste the block, then Ctrl+D
#
# Each key is written with bench set-config, then the site asks OneAdmin who
# it is (one.account.refresh). What is pasted is not shown while pasting and
# never printed; only the names of the keys written are. Safe to run again
# with a new block, which replaces the old one.

set -euo pipefail

SITE="${1:-}"
BENCH="${BENCH:-$HOME/one-bench}"
KEYS='["one_admin_url","one_tenant","one_token","one_mail_secret","one_mail_domain","one_backup_secret","one_keeper_url","max_file_size"]'
NEEDED='["one_admin_url","one_tenant","one_token","one_backup_secret","one_keeper_url"]'

fail() { printf '\n\033[1;31m%s\033[0m\n' "$*" >&2; exit 1; }

[ -n "$SITE" ] || fail "Usage: bash link.sh SITE, then paste the site config New Test Workspace showed."
[ -f "$BENCH/sites/$SITE/site_config.json" ] || fail "No site $SITE in $BENCH."
export PATH="$PATH:$HOME/.local/bin"

if [ -t 0 ]; then
	echo "Paste the site config, then press Ctrl+D:"
	stty -echo
	trap 'stty echo' EXIT
fi
block="$(cat)"
[ -t 0 ] && stty echo

jq -e 'type == "object"' >/dev/null 2>&1 <<<"$block" || fail "That is not the site config New Test Workspace showed."
unknown="$(jq -r --argjson keys "$KEYS" 'keys - $keys | join(", ")' <<<"$block")"
[ -z "$unknown" ] || fail "The block has keys a test workspace isn't given: $unknown."
missing="$(jq -r --argjson needed "$NEEDED" '$needed - (to_entries | map(select(.value != null and .value != "")) | map(.key)) | join(", ")' <<<"$block")"
[ -z "$missing" ] || fail "The block has no $missing."
jq -e '(.one_admin_url | startswith("https://")) and (.one_keeper_url | startswith("https://"))' >/dev/null <<<"$block" || fail "OneAdmin and the keeper are reached over https only."
jq -e '.one_tenant | test("^[a-z0-9][a-z0-9-]{1,39}$")' >/dev/null <<<"$block" || fail "one_tenant is not a workspace id."

cd "$BENCH"
while IFS= read -r key; do
	if [ "$(jq -r --arg k "$key" '.[$k] | type' <<<"$block")" = number ]; then
		bench --site "$SITE" set-config -p "$key" "$(jq -r --arg k "$key" '.[$k]' <<<"$block")" >/dev/null
	else
		bench --site "$SITE" set-config "$key" "$(jq -r --arg k "$key" '.[$k]' <<<"$block")" >/dev/null
	fi
	echo "written: $key"
done < <(jq -r 'keys[]' <<<"$block")

bench --site "$SITE" clear-cache >/dev/null
said="$(bench --site "$SITE" execute onedesk.one.account.refresh 2>/dev/null | tail -1)"
error="$(jq -r '.last_error // empty' 2>/dev/null <<<"$said" || true)"
[ -z "$error" ] || fail "Written, but OneAdmin refused the site: $error"
echo "$SITE is linked to $(jq -r '.one_admin_url' <<<"$block") as $(jq -r '.one_tenant' <<<"$block")."
