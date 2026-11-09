# One on your own machine

A bench in WSL2 on Windows, with two sites: `one.localhost` (a workspace) and
`admin.localhost` (OneAdmin). Frappe Cloud stays where One runs for real; this
is where it is built, because a change shows up in seconds instead of after a
deploy.

## Windows, once

In PowerShell, as administrator:

    wsl --install -d Ubuntu

Restart when it asks, open **Ubuntu** from the Start menu, and choose a user
name and password. Install **VS Code** on Windows with its **WSL** extension.

## Ubuntu

Copy `setup.sh` into Ubuntu and run it as your own user:

    bash setup.sh

It stops once to have WSL restarted (`wsl --shutdown` in PowerShell, then open
Ubuntu again and run it again), and once for the GitHub sign-in. The rest takes
twenty minutes or so. Run it again at any time; it only does what is missing.

Keep the bench in Ubuntu's own home (`~/one-bench`), never under `/mnt/c`:
files on the Windows side are many times slower to read from Linux.

## Or on a server

The same script runs on any Ubuntu server (24.04 or later, 8 GB of memory or
more), as a user with sudo. Nothing needs opening to the internet: connect with

    ssh -L 8000:localhost:8000 -L 9000:localhost:9000 ubuntu@SERVER

and the addresses below open in your own browser as if the bench were local.
Port 9000 is socketio, which the desk's realtime needs.

On a server, `setup.sh` also adds a swap file (4 to 8 GB), and `bench build`
runs `build.sh`: the bench is stopped for the build and started again after,
since a full build beside a running bench can use up a small machine's memory.

## On the internet

With a domain in your Cloudflare account, give it to `setup.sh`:

    bash setup.sh 4dl.dev

and it makes `one.4dl.dev` (a workspace) and `admin.4dl.dev` (OneAdmin)
instead of the `.localhost` pair, by running `public.sh` at the end, served
through a Cloudflare Tunnel: HTTPS, realtime included, and no port opened on
the server. Once a bench is on a domain, `bash setup.sh` with none keeps to it
and never adds the `.localhost` pair. On a bench that already has the
`.localhost` pair, `public.sh 4dl.dev` adds the domain pair beside them. The tunnel is a line of the Procfile, so they are
online exactly while `bench start` runs. Their Administrator password is
`PUBLIC_ADMIN_PASSWORD` in `~/.one-local`.

## Set up in one go

`dev-config.sh` takes `public.sh`'s two empty sites to a working pair: the
setup wizard on each, OneAdmin Settings filled with the dev values, the
workspace linked to the dev OneAdmin as its own workspace (OneAI, weather and
news unbilled), and, given a Cloudflare master token in the file, Set Up
Cloudflare run as the `dev` environment.

    cp ~/one-bench/apps/onedesk/deploy/local/dev.example.json ~/.one-dev.json
    chmod 600 ~/.one-dev.json     # then fill it in
    bash ~/one-bench/apps/onedesk/deploy/local/dev-config.sh 4dl.dev

The dev OneAdmin is the `dev` environment of the same Cloudflare and Frappe
Cloud accounts: its Workers, store, buckets, gateway and tokens carry `-dev`,
its workspaces are `slug.d.4dl.app` and its mail `m.4dl.dev`, and a signup on
it builds a real site on its own bench group (`one-dev`), to be archived after
the test. It refuses production's domains and a Stripe live key, and touches
only sites `public.sh` marked `one_dev`. Run it again after changing the file.

Left by hand, in each environment: the OpenWeather key and Stripe's keys.
Saving Stripe's secret key makes the webhook through Stripe's API and keeps its
signing secret, so nobody adds it.

## Always on

On a server, `bash ~/one-bench/apps/onedesk/deploy/local/always-on.sh` runs
`bench start` as a system service: at boot, again within seconds if it stops,
and with no terminal open. `sudo systemctl restart one-bench` after a change to
`hooks.py`; `journalctl -u one-bench -f` shows what it prints; `always-on.sh
off` hands it back to you. Once Claude Code is installed and
`claude remote-control` has been run by hand in `apps/onedesk`, the same script
runs Remote Control as `one-claude` too, so a session on this machine can be
opened from claude.ai/code or the Claude app at any time.

## For Claude Code

`setup.sh` copies `CLAUDE.bench.md` to `~/one-bench/CLAUDE.md`, which Claude
Code reads from anywhere in the bench: the service, the sites, the gates, and
what never to do on a dev machine. Edit it here, not there.

## Every day

    cd ~/one-bench && bench start

Python reloads on save, `bench watch` rebuilds the desk's JS and CSS, and the
`islands` line in the Procfile rebuilds onedesk's frontend; refresh the page
to see a change. Open `http://one.localhost:8000` or `http://admin.localhost:8000` in the
Windows browser. Passwords are in `~/.one-local`. Push to `main` as before;
Frappe Cloud deploys from there.

frappe, erpnext and hrms are pinned to the commits in `upstream.json`, which
is what the tests were last checked against. When Frappe Cloud's bench moves
ahead, record the new commits there and run `setup.sh` again.

## A new dev machine

Copy `deploy/local/setup.sh` onto a fresh Ubuntu server, as a user with
passwordless sudo, and run:

    ONE_RESCUE_PASSPHRASE=... bash setup.sh

With no further question it fetches the newest rescue kit from the keeper, puts
every key back (GitHub and the tunnel included), builds the bench and the
domain's sites, restores each from its newest nightly backup, and turns on the
service and the nightly backups. Claude Code's own sign-in is not in the kit.

The kit is in `one-backups-dev`, under `rescue/`; if the keeper is down, fetch
the newest file from Cloudflare's dashboard and set `ONE_RESCUE_KIT` to it. The
passphrase is in Yamen's Google Password Manager under `one-rescue-kit`.

`python scripts/rescue.py pack` makes a new kit, which holds the domain sites'
configs and `~/.cloudflared`, and tells the keeper the secret a new machine
fetches it with. Pack again after a new key or a new tunnel.

**Nightly backups.** `always-on.sh` schedules `scripts/rescue.py nightly` at
02:10 UTC: every `one_dev` site's database and files go to the dev keeper under
`daily/dev-<site>/`, and its site config is sealed first, since it holds keys.
`python scripts/rescue.py key` makes the sealing key from the passphrase, once.
