#!/bin/bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
pin() { python3 -c "import json,sys; print(json.load(open('$repo/upstream.json'))[sys.argv[1]]['sha'])" "$1"; }

slug="${GITHUB_REPOSITORY:-yamenzak/onedesk}"
sha="$(git -C "$repo" rev-parse HEAD)"
branch="${RELEASE_BRANCH:-main}"
name="r${sha:0:8}"
bench="$HOME/pilot/benches/$name"
site="template.one"
out="${OUT:-/tmp/release}"
mkdir -p "$out"

pilot -y new "$name" --frappe-branch develop --admin-password "Ci$(openssl rand -hex 12)-Z9"
pilot -y -b "$name" init --commit "$(pin frappe)"

(umask 077; python3 -c "
import json, os
print(json.dumps({'provider': 'github', 'token': os.environ['GH_TOKEN'], 'username': 'x-access-token', 'token_expires_at': None, 'is_token_valid': True}))
" > "$bench/.bench.git.info")

pilot -y -b "$name" get-app https://github.com/frappe/erpnext --branch develop --commit "$(pin erpnext)"
pilot -y -b "$name" get-app https://github.com/frappe/hrms --branch develop --commit "$(pin hrms)"
pilot -y -b "$name" get-app "https://github.com/$slug" --branch "$branch" --commit "$sha"
rm -f "$bench/.bench.git.info"
if grep -rlF "$GH_TOKEN" "$bench"/apps/*/.git/config; then
	echo "a clone kept the token" >&2
	exit 1
fi

cd "$bench"
list="$(mktemp)"
for app in frappe erpnext hrms onedesk; do
	git -C "apps/$app" ls-files -oi --exclude-standard --directory \
		| grep -E "/public/|/www/" | grep -vE "node_modules|__pycache__" | sed "s#^#apps/$app/#" >> "$list"
done
for one in assets.json assets-rtl.json css js locale; do
	echo "sites/assets/$one" >> "$list"
done
tar czf "$out/$sha.tar.gz" -T "$list"
sha256sum "$out/$sha.tar.gz" | cut -d' ' -f1 > "$out/$sha.tar.gz.sha256"

pyhome="$(sed -n 's/^home *= *//p' env/pyvenv.cfg)"
python_dirs=""
for one in "$(dirname "$pyhome")" "$(readlink -f "$(dirname "$pyhome")")"; do
	case "$one" in
		"$HOME"/*) python_dirs="$python_dirs ${one#"$HOME"/}" ;;
	esac
done
cd "$HOME"
whole="$(mktemp)"
{
	printf '%s\n' "pilot/benches/$name" "pilot/benches/$name/sites" "pilot/benches/$name/sites/apps.txt"
	find "pilot/benches/$name/apps" -name node_modules -prune -o -print
	find "pilot/benches/$name/apps/frappe/node_modules" -print
	find "pilot/benches/$name/env" "pilot/benches/$name/sites/assets" -print
	for one in $python_dirs; do
		find "$one" -print
	done
} | sort -u > "$whole"
tar czf "$out/$sha.bench.tar.gz" --no-recursion -T "$whole"
sha256sum "$out/$sha.bench.tar.gz" | cut -d' ' -f1 > "$out/$sha.bench.tar.gz.sha256"
echo "$python_dirs" | xargs -n1 | sort -u > "$out/$sha.bench.python"

pilot -b "$name" start > "$out/start.log" 2>&1 &
started=$!
pilot -b "$name" wait-for-database
pilot -y -b "$name" new-site "$site" --apps frappe erpnext hrms onedesk --admin-password "T$(openssl rand -hex 12)-Z9"
pilot -b "$name" frappe --site "$site" migrate
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
sha256sum "$out/$sha.site.tar.gz" | cut -d' ' -f1 > "$out/$sha.site.tar.gz.sha256"

"$bench/env/bin/python" "$repo/deploy/release/upload.py" publish "$out" "$sha" "$(pin frappe)" "$(pin erpnext)" "$(pin hrms)"
