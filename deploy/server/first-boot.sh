set -euo pipefail
umask 022
exec > /var/log/one-first-boot.log 2>&1

export DEBIAN_FRONTEND=noninteractive
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" > /etc/apt/sources.list.d/cloudflared.list
apt-get update -qq
apt-get install -y -qq cloudflared
cloudflared service install "$ONE_TUNNEL_TOKEN"

curl -fsSL https://raw.githubusercontent.com/frappe/pilot/develop/install.sh -o /tmp/pilot.sh
sh /tmp/pilot.sh
chmod 644 /tmp/pilot.sh
sudo -iu frappe bash /tmp/pilot.sh

install -m 700 -o frappe -g frappe /dev/null /home/frappe/boot.env
export -p | grep -E ' ONE_' | grep -v ONE_TUNNEL_TOKEN > /home/frappe/boot.env

cat > /home/frappe/boot.sh <<'BOOT'
set -euo pipefail
. ~/boot.env
export PATH="$HOME/pilot/bin:$HOME/.local/bin:$PATH"
bench=~/pilot/benches/main

pilot -y new main --frappe-branch develop --admin-password "$ONE_PILOT_PASSWORD"
pilot -y -b main init --commit "$ONE_FRAPPE"

(umask 077; printf '{"provider":"github","token":"%s","username":"x-access-token","token_expires_at":null,"is_token_valid":true}' "$ONE_GITHUB_TOKEN" > "$bench/.bench.git.info")
pilot -y -b main get-app https://github.com/frappe/erpnext --branch develop --commit "$ONE_ERPNEXT" --skip-assets
pilot -y -b main get-app https://github.com/frappe/hrms --branch develop --commit "$ONE_HRMS" --skip-assets
pilot -y -b main get-app "https://github.com/$ONE_REPOSITORY" --branch "$ONE_BRANCH" --commit "$ONE_RELEASE" --skip-assets

"$bench/env/bin/python" -I - <<'FETCH'
import boto3, hashlib, json, os
store = boto3.client("s3", endpoint_url=os.environ["ONE_R2_ENDPOINT"], region_name="auto", aws_access_key_id=os.environ["ONE_R2_KEY"], aws_secret_access_key=os.environ["ONE_R2_SECRET"])
bucket, key = os.environ["ONE_R2_BUCKET"], f"releases/{os.environ['ONE_RELEASE']}"
about = json.loads(store.get_object(Bucket=bucket, Key=f"{key}.json")["Body"].read())
store.download_file(bucket, f"{key}.tar.gz", "/tmp/release.tar.gz")
digest = hashlib.sha256()
with open("/tmp/release.tar.gz", "rb") as archive:
    for chunk in iter(lambda: archive.read(1 << 20), b""):
        digest.update(chunk)
if digest.hexdigest() != about["sha256"]:
    raise SystemExit("the release archive does not match its checksum")
FETCH

cd "$bench"
tar xzf /tmp/release.tar.gz
rm /tmp/release.tar.gz
for app in frappe erpnext hrms onedesk; do
	ln -sfn "$bench/apps/$app/$app/public" "sites/assets/$app"
done

pilot -y -b main setup production --admin-domain "$ONE_ADMIN_HOST"
pilot -y -b main restart
BOOT

chown frappe:frappe /home/frappe/boot.sh
sudo -iu frappe bash /home/frappe/boot.sh

rm -f /home/frappe/boot.env /home/frappe/boot.sh /tmp/pilot.sh
rm -f /var/lib/cloud/instance/user-data.txt* /var/lib/cloud/instance/scripts/part-*
echo FIRST-BOOT-DONE
