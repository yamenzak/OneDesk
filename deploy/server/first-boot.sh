set -euo pipefail
umask 022
trap 'shutdown -h now' ERR
exec > /var/log/one-first-boot.log 2>&1

fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab

export DEBIAN_FRONTEND=noninteractive
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" > /etc/apt/sources.list.d/cloudflared.list
apt-get update -qq
apt-get install -y -qq cloudflared
cloudflared service install "$ONE_TUNNEL_TOKEN"

apt-get install -y -qq unattended-upgrades
cat > /etc/apt/apt.conf.d/52one <<'APT'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "02:30";
APT

curl -fsSL --retry 5 --retry-delay 20 --retry-all-errors https://raw.githubusercontent.com/frappe/pilot/develop/install.sh -o /tmp/pilot.sh
PILOT_VERSION=v0.0.99-pre-alpha sh /tmp/pilot.sh
chmod 644 /tmp/pilot.sh
for attempt in $(seq 1 20); do
	sudo -iu frappe env PILOT_VERSION=v0.0.99-pre-alpha bash /tmp/pilot.sh && break
	[ "$attempt" = 20 ] && exit 1
	sleep 60
done

install -m 700 -o frappe -g frappe /dev/null /home/frappe/boot.env
export -p | grep -E ' ONE_' | grep -v ONE_TUNNEL_TOKEN > /home/frappe/boot.env

cat > /home/frappe/boot.sh <<'BOOT'
set -euo pipefail
. ~/boot.env
export PATH="$HOME/pilot/bin:$HOME/.local/bin:$PATH"
bench=~/pilot/benches/main

pilot -y new main --frappe-branch develop --admin-password "$ONE_PILOT_PASSWORD"
printf '\n[build]\nmemory_limit_mb = 2800\n' >> "$bench/bench.toml"
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

pilot -y -b main processes disable frappe-flow_server
pilot -y -b main setup production --admin-domain "$ONE_ADMIN_HOST"
pilot -y -b main restart
BOOT

chown frappe:frappe /home/frappe/boot.sh
sudo -iu frappe bash /home/frappe/boot.sh

cat > /etc/cron.d/one-after-boot <<'CRON'
@reboot root sleep 60 && sudo -iu frappe bash -lc 'for bench in $(ls ~/pilot/benches | grep -v common_config); do pilot -y -b "$bench" restart; done'
CRON
chmod 644 /etc/cron.d/one-after-boot

install -m 755 -o frappe -g frappe /root/one-agent.py /home/frappe/one-agent.py
sudo -iu frappe env S="$ONE_SERVER" A="$ONE_AGENT_SECRET" U="$ONE_ADMIN_URL" E="$ONE_R2_ENDPOINT" B="$ONE_R2_BUCKET" K="$ONE_R2_KEY" R="$ONE_R2_SECRET" G="$ONE_GITHUB_TOKEN" P="$ONE_PILOT_PASSWORD" python3 -c "import json, os; json.dump({'server': os.environ['S'], 'secret': os.environ['A'], 'admin_url': os.environ['U'], 'r2_endpoint': os.environ['E'], 'r2_bucket': os.environ['B'], 'r2_key': os.environ['K'], 'r2_secret': os.environ['R'], 'github_token': os.environ['G'], 'pilot_password': os.environ['P']}, open('/home/frappe/.one-agent.json', 'w')); os.chmod('/home/frappe/.one-agent.json', 0o600)" 2>&1
cat > /etc/cron.d/one-agent <<'CRON'
* * * * * frappe cd /home/frappe && PYTHONPATH=/home/frappe/pilot /home/frappe/pilot/.admin-venv/bin/python /home/frappe/one-agent.py >> /home/frappe/agent.log 2>&1
CRON
chmod 644 /etc/cron.d/one-agent

rm -f /home/frappe/boot.env /home/frappe/boot.sh /tmp/pilot.sh
rm -f /var/lib/cloud/instance/user-data.txt* /var/lib/cloud/instance/scripts/part-* /var/lib/cloud/instance/obj.pkl
echo FIRST-BOOT-DONE
