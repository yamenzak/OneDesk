#!/bin/bash
set -euo pipefail

repo="$(cd "$(dirname "$0")/../.." && pwd)"
pin() { python3 -c "import json,sys; print(json.load(open('$repo/upstream.json'))[sys.argv[1]]['sha'])" "$1"; }

bench=~/pilot/benches/build
slug="${GITHUB_REPOSITORY:-yamenzak/onedesk}"
sha="$(git -C "$repo" rev-parse HEAD)"
branch="${RELEASE_BRANCH:-main}"

pilot -y new build --frappe-branch develop --admin-password "Ci$(openssl rand -hex 12)-Z9"
pilot -y -b build init --commit "$(pin frappe)"

(umask 077; python3 -c "
import json, os
print(json.dumps({'provider': 'github', 'token': os.environ['GH_TOKEN'], 'username': 'x-access-token', 'token_expires_at': None, 'is_token_valid': True}))
" > "$bench/.bench.git.info")

pilot -y -b build get-app https://github.com/frappe/erpnext --branch develop --commit "$(pin erpnext)"
pilot -y -b build get-app https://github.com/frappe/hrms --branch develop --commit "$(pin hrms)"
pilot -y -b build get-app "https://github.com/$slug" --branch "$branch" --commit "$sha"

cd "$bench"
list="$(mktemp)"
for app in frappe erpnext hrms onedesk; do
	git -C "apps/$app" ls-files -oi --exclude-standard --directory \
		| grep -E "/public/|/www/" | grep -vE "node_modules|__pycache__" | sed "s#^#apps/$app/#" >> "$list"
done
for one in assets.json assets-rtl.json css js locale; do
	echo "sites/assets/$one" >> "$list"
done

out="$RUNNER_TEMP/$sha.tar.gz"
tar czf "$out" -T "$list"
sha256sum "$out" | cut -d' ' -f1 > "$out.sha256"
env/bin/python "$repo/deploy/release/upload.py" "$out" "$sha" "$(pin frappe)" "$(pin erpnext)" "$(pin hrms)"
