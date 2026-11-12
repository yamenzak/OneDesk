#!/bin/bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
pin() { python3 -c "import json,sys; print(json.load(open('$repo/upstream.json'))[sys.argv[1]]['sha'])" "$1"; }
in_pilot() { PYTHONPATH="$HOME/pilot" "$HOME/pilot/.admin-venv/bin/python" "$@"; }
on_pilot() { in_pilot "$repo/deploy/release/base.py" "$@"; }

slug="${GITHUB_REPOSITORY:-yamenzak/onedesk}"
sha="$(git -C "$repo" rev-parse HEAD)"
branch="${RELEASE_BRANCH:-main}"
name="r${sha:0:8}"
bench="$HOME/pilot/benches/$name"
site="template.one"
out="${OUT:-/tmp/release}"
base="${ONE_BASE:-}"
template="${ONE_TEMPLATE:-}"
gz="$(command -v pigz || echo gzip)"
mkdir -p "$out"

python_dirs() {
	local pyhome one
	pyhome="$(sed -n 's/^home *= *//p' "$bench/env/pyvenv.cfg")"
	for one in "$(dirname "$pyhome")" "$(readlink -f "$(dirname "$pyhome")")"; do
		case "$one" in
			"$HOME"/*) echo "${one#"$HOME"/}" ;;
		esac
	done | sort -u
}

unshared() {
	if grep -rlF "$GH_TOKEN" "$bench"/apps/*/.git/config; then
		echo "a clone kept the token" >&2
		exit 1
	fi
}

fresh() {
	pilot -y -b "$name" init --commit "$(pin frappe)"
	pilot -y -b "$name" get-app https://github.com/frappe/erpnext --branch develop --commit "$(pin erpnext)"
	pilot -y -b "$name" get-app https://github.com/frappe/hrms --branch develop --commit "$(pin hrms)"
	[ -n "$base" ] || return 0
	unshared
	local list
	list="$(mktemp)"
	(
		cd "$HOME"
		{
			find "pilot/benches/$name" \( -path "pilot/benches/$name/logs" -o -path "pilot/benches/$name/pids" \) -prune -o -print
			for one in $(python_dirs); do
				find "$one" -print
			done
		} | sort -u > "$list"
		tar cf "$base/base.tar" --no-recursion -T "$list"
	)
	sha256sum "$base/base.tar" | cut -d' ' -f1 > "$base/base.tar.sha256"
	on_pilot apps "$bench" > "$base/apps.json"
	echo "$name" > "$base/name"
	echo "base kept: $(stat -c %s "$base/base.tar") bytes, $(wc -l < "$list") entries"
}

reused() {
	[ -n "$base" ] && [ -s "$base/base.tar" ] && [ -s "$base/name" ] && [ -s "$base/apps.json" ] \
		&& [ "$(sha256sum "$base/base.tar" | cut -d' ' -f1)" = "$(cat "$base/base.tar.sha256")" ]
}

reuse() {
	local old moved left
	old="$(cat "$base/name")"
	tar xf "$base/base.tar" -C "$HOME" --skip-old-files --transform "s#pilot/benches/$old#pilot/benches/$name#"
	if [ "$old" != "$name" ]; then
		moved="$(mktemp)"
		grep -rlFZ "benches/$old" "$bench" > "$moved" || true
		xargs -0 -r perl -pi -e "s#benches/$old#benches/$name#g" < "$moved"
		echo "base of $old moved here: $(tr -cd '\0' < "$moved" | wc -c) files rewritten"
		left="$(grep -rlF "benches/$old" "$bench" || true)$(find "$bench" -lname "*benches/$old*")"
		if [ -n "$left" ]; then
			echo "the base still names $old in:" >&2
			echo "$left" | head -5 >&2
			exit 1
		fi
	fi
	on_pilot settle "$bench" "$base/apps.json"
	"$bench/env/bin/python" -c "import frappe, erpnext, hrms"
}

pilot -y new "$name" --frappe-branch develop --admin-password "Ci$(openssl rand -hex 12)-Z9"
if reused; then
	reuse
	echo "base: reused $(cat "$base/name") at ${SECONDS}s"
else
	fresh
	echo "base: built at ${SECONDS}s"
fi

(umask 077; python3 -c "
import json, os
print(json.dumps({'provider': 'github', 'token': os.environ['GH_TOKEN'], 'username': 'x-access-token', 'token_expires_at': None, 'is_token_valid': True}))
" > "$bench/.bench.git.info")
pilot -y -b "$name" get-app "https://github.com/$slug" --branch "$branch" --commit "$sha"
rm -f "$bench/.bench.git.info"
unshared
echo "onedesk: built at ${SECONDS}s"
in_pilot "$repo/deploy/release/private.py" "$bench" "$repo"
echo "private apps: on the bench at ${SECONDS}s"

cd "$bench"
built() {
	if [ -L "apps/$1" ]; then
		git -C "$2" ls-files -o --directory
	else
		git -C "$2" ls-files -oi --exclude-standard --directory
	fi
}
list="$(mktemp)"
for app in $(cat sites/apps.txt); do
	at="$(realpath --relative-to=. "apps/$app")"
	built "$app" "$at" | awk -v at="$at/" '/\/(public|www)\// && !/node_modules|__pycache__/ { print at $0 }' >> "$list"
done
for one in assets.json assets-rtl.json css js locale; do
	echo "sites/assets/$one" >> "$list"
done
tar -I "$gz" -cf "$out/$sha.tar.gz" -T "$list"
sha256sum "$out/$sha.tar.gz" | cut -d' ' -f1 > "$out/$sha.tar.gz.sha256"

held_python="$(python_dirs)"
cd "$HOME"
whole="$(mktemp)"
{
	printf '%s\n' "pilot/benches/$name" "pilot/benches/$name/sites" "pilot/benches/$name/sites/apps.txt"
	find "pilot/benches/$name/apps" -name node_modules -prune -o -print
	if [ -d "pilot/benches/$name/private-apps" ]; then
		find "pilot/benches/$name/private-apps" -name node_modules -prune -o -print
	fi
	find "pilot/benches/$name/apps/frappe/node_modules" -print
	find "pilot/benches/$name/env" "pilot/benches/$name/sites/assets" -print
	for one in $held_python; do
		find "$one" -print
	done
} | sort -u > "$whole"
tar -I "$gz" -cf "$out/$sha.bench.tar.gz" --no-recursion -T "$whole"
sha256sum "$out/$sha.bench.tar.gz" | cut -d' ' -f1 > "$out/$sha.bench.tar.gz.sha256"
echo "$held_python" > "$out/$sha.bench.python"
echo "archives: made at ${SECONDS}s"

rule() { python3 "$repo/deploy/release/template.py" "$@"; }

installed() {
	pilot -y -b "$name" new-site "$site" --apps frappe erpnext hrms onedesk --admin-password "T$(openssl rand -hex 12)-Z9"
	pilot -b "$name" frappe --site "$site" migrate
}

migrated() {
	local stale kept
	stale="$(mktemp)"
	kept="$(mktemp -d)"
	rule stale "$repo" "$from" "$sha" > "$stale" || return 1
	tar xzf "$template/site.tar.gz" -C "$kept" || return 1
	in_pilot "$repo/deploy/release/template.py" restore "$bench" "$site" "$kept" "T$(openssl rand -hex 12)-Z9" || return 1
	(cd "$bench/sites" && "$bench/env/bin/python" "$repo/deploy/release/template.py" unstamp "$site" "$stale") || return 1
	pilot -b "$name" frappe --site "$site" migrate || return 1
}

from=""
why="no template was kept"
if [ -n "$template" ] && [ -s "$template/site.tar.gz" ] && tar tzf "$template/site.tar.gz" > /dev/null; then
	from="$(cat "$template/commit" 2> /dev/null || true)"
	why="the kept template does not say which commit made it"
	if [ -n "$from" ]; then
		why="$(rule why "$repo" "$from" "$sha" 2>&1)" || why="the rule failed: $why"
	fi
fi

if [ -n "$from" ] && [ "$from" = "$sha" ]; then
	cp "$template/site.tar.gz" "$out/$sha.site.tar.gz"
	echo "template: reused, made at this commit"
else
	began="$SECONDS"
	pilot -b "$name" start > "$out/start.log" 2>&1 &
	started=$!
	pilot -b "$name" wait-for-database
	how=""
	if [ -n "$from" ] && [ -z "$why" ]; then
		echo "template: migrating the one made at $from"
		if migrated; then
			how="migrated from $from"
		else
			echo "::warning::template: migrating the one made at $from failed, so it is installed afresh"
			pilot -y -b "$name" drop-site "$site" --no-backup --force || rm -rf "$bench/sites/$site"
		fi
	else
		echo "template: installing afresh, since"
		echo "$why" | sed 's/^/  /'
	fi
	if [ -z "$how" ]; then
		installed
		how="installed afresh"
	fi
	pilot -b "$name" frappe --site "$site" execute onedesk.one_admin.spares.as_template
	pilot -b "$name" frappe --site "$site" backup
	kill "$started" || true

	held="$bench/sites/$site"
	made="$(mktemp -d)"
	cp "$(ls -t "$held"/private/backups/*-database.sql.gz | head -1)" "$made/database.sql.gz"
	"$bench/env/bin/python" "$repo/deploy/release/upload.py" config "$held/site_config.json" > "$made/site_config.json"
	mkdir -p "$made/public" "$made/private"
	cp -a "$held/public/files" "$made/public/" 2>/dev/null || mkdir -p "$made/public/files"
	cp -a "$held/private/files" "$made/private/" 2>/dev/null || mkdir -p "$made/private/files"
	tar czf "$out/$sha.site.tar.gz" -C "$made" database.sql.gz site_config.json public private
	if [ -n "$template" ]; then
		rm -f "$template/site.tar.gz" "$template/commit"
		cp "$out/$sha.site.tar.gz" "$template/site.tar.gz"
		echo "$sha" > "$template/commit"
	fi
	echo "template: $how in $((SECONDS - began))s, at ${SECONDS}s"
fi
sha256sum "$out/$sha.site.tar.gz" | cut -d' ' -f1 > "$out/$sha.site.tar.gz.sha256"

for part in "$sha.tar.gz" "$sha.bench.tar.gz" "$sha.site.tar.gz"; do
	[ "$(sha256sum "$out/$part" | cut -d' ' -f1)" = "$(cat "$out/$part.sha256")" ]
	tar tzf "$out/$part" > /dev/null
	echo "$part $(stat -c %s "$out/$part") bytes, $(tar tzf "$out/$part" | wc -l) entries"
done
tar xzf "$out/$sha.site.tar.gz" -O database.sql.gz | gzip -t
echo "built in ${SECONDS}s"
[ "${PUBLISH:-true}" = true ] || exit 0
BUILT_IN="$SECONDS" "$bench/env/bin/python" "$repo/deploy/release/upload.py" publish "$out" "$sha" "$(pin frappe)" "$(pin erpnext)" "$(pin hrms)"
