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

## On the internet

With a domain in your Cloudflare account, after `setup.sh`:

    bash ~/one-bench/apps/onedesk/deploy/local/public.sh 4dl.dev

makes `one.4dl.dev` (a workspace) and `admin.4dl.dev` (OneAdmin) as two more
sites, served through a Cloudflare Tunnel: HTTPS, realtime included, and no
port opened on the server. The tunnel is a line of the Procfile, so they are
online exactly while `bench start` runs. Their Administrator password is
`PUBLIC_ADMIN_PASSWORD` in `~/.one-local`.

## Set up in one go

`dev-config.sh` takes `public.sh`'s two empty sites to a working pair: the
setup wizard on each, OneAdmin Settings filled with the dev values, and the
workspace linked to the dev OneAdmin as its own workspace, so OneAI, weather
and news work there unbilled.

    cp ~/one-bench/apps/onedesk/deploy/local/dev.example.json ~/.one-dev.json
    chmod 600 ~/.one-dev.json     # then fill it in
    bash ~/one-bench/apps/onedesk/deploy/local/dev-config.sh 4dl.dev

The values are dev's own: separate R2 buckets, an AI gateway named `one-dev`,
Stripe test keys. It refuses a Stripe live key, touches only sites `public.sh`
marked `one_dev`, and writes the Frappe Cloud and Cloudflare fields blank, so a
dev OneAdmin can never build a real site or rewrite production's tokens and
routes. Run it again after changing the file.

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
