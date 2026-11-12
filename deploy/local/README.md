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

and it makes `one.4dl.dev`, a workspace, instead of the `.localhost` pair, by
running `public.sh` at the end, served through a Cloudflare Tunnel: HTTPS,
realtime included, and no port opened on the server. Once a bench is on a
domain, `bash setup.sh` with none keeps to it and never adds the `.localhost`
pair. The tunnel is a line of the Procfile, so the site is online exactly
while `bench start` runs. Its Administrator password is
`PUBLIC_ADMIN_PASSWORD` in `~/.one-local`.

## The demo, linked to production

The dev server has no OneAdmin of its own. Its workspace is a **test
workspace** of production's, `admin.4dl.app` (one_admin/AGENTS.md, Test
workspaces): never billed, never updated or moved by OneAdmin, backing itself
up to production's keeper, its OneAI, mail, weather and news going through
production, and its credits given by hand.

1. On `admin.4dl.app`, **Workspaces**, the menu's **New Test Workspace**:
   address `one.4dl.dev` and a name. It shows the site config once.
2. On the server:

       bash ~/one-bench/apps/onedesk/deploy/local/dev-config.sh 4dl.dev

   builds the demo company on the site if it is new, then runs `link.sh`,
   which asks for the site config: paste it and press Ctrl+D. It is not shown
   while pasted. `link.sh SITE` alone links any site of the bench the same way.

New Test Workspace again with the same address makes new keys for the same
workspace, and the old ones stop working: run `RELINK=1 dev-config.sh` after
it.

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

It fetches the newest rescue kit from production's keeper, puts every key back
(GitHub and the tunnel included), builds the bench and the domain's workspace,
puts it back from the newest backup it sent the keeper, and turns on the
service. The backup is read from the locked bucket with a sign-in to
Cloudflare, the one question it asks: open the link it prints and paste the
address the browser ends on. Claude Code's own sign-in is not in the kit.

The kit is in `one-backups`, under `rescue/`; if the keeper is down, fetch the
newest file from Cloudflare's dashboard and set `ONE_RESCUE_KIT` to it. The
passphrase is in Yamen's Google Password Manager under `one-rescue-kit`.

`python scripts/rescue.py pack` makes a new kit, which holds the site's config
and `~/.cloudflared`, and sends it to `admin.4dl.app` with an operator's API
key, `ONE_OPERATOR_KEY=key:secret` in `~/.one-local` (an operator's user on
admin.4dl.app, API Access, Generate Keys). OneAdmin adds it under `rescue/`
through its keeper and tells the keeper the secret a new machine fetches it
with; this machine never holds the keeper's own secret. Pack again after a
new key, a new tunnel or linking the site again.

**Backups.** The workspace sends its own to production's keeper, every night
and its database every four hours, as every workspace does; nothing on the
server is scheduled for them.
