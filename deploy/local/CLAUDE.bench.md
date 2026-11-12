<!-- Written by apps/onedesk/deploy/local/setup.sh from CLAUDE.bench.md, every run. Edit it there. -->
# This machine: One's dev bench

You are on the dev server, not production. Production runs on AWS Lightsail
boxes that OneAdmin runs. It changes only through a release: push `main`, GitHub
builds it, and each workspace moves in its own window. This machine reaches it
in two ways only: its workspace is a test workspace of production's OneAdmin
(`admin.4dl.app`), and the server itself is joined to it with Connect Server
for training copies. `scripts/server.py` builds the first OneAdmin.

The repository is `apps/onedesk`; its own `CLAUDE.md` is the product and the
rules. This file is only about how this machine runs it.

## What runs, and how

- The bench is `~/one-bench`: frappe, erpnext and hrms pinned to the commits in
  `apps/onedesk/upstream.json`, and onedesk on `main`.
- `bench start` runs as the systemd service `one-bench` (always-on.sh), not in
  a terminal. It brings up the web server on 8000, socketio on 9000, a worker,
  the scheduler, both redis servers, the asset watchers, and the Cloudflare
  tunnel. Never start another `bench start` beside it: the ports are taken and
  honcho stops everything.
- `sudo systemctl restart one-bench` after a change to `hooks.py`, a new
  whitelisted method, or anything the worker or scheduler loads at start.
  `journalctl -u one-bench -f` is what it prints.
- Python reloads by itself. `bench watch` rebuilds the desk's JS and CSS and
  the `islands` line rebuilds `frontend/`, both on save; the page needs a
  refresh. The portal (`frontend/portal`) has no watcher: `cd
  apps/onedesk/frontend && yarn build` after changing it.
- A plain stylesheet in `public/css` (phone.css and the like) is served
  under `?v=`, the modified time of `sites/assets/assets.json`, which the
  tunnel's cache keeps for 12 hours: after changing one, `touch
  sites/assets/assets.json` and restart `one-bench`, or the browser keeps
  the old file.
- A doctype or fixture JSON change needs `bench --site SITE migrate`.
- `bench build` runs `deploy/local/build.sh`: it stops `one-bench`, builds,
  and starts it again, because a full build beside the running bench runs
  this machine out of memory. The sites are offline for that minute. Build
  one app where one changed (`bench build --app onedesk`), and never run a
  build in the background beside another.
- You may be running under the `one-claude` service (Remote Control), started
  in `apps/onedesk` and sharing it with the bench: what you change is served
  at once. Never stop or restart `one-claude` yourself; that ends the session
  you are in.

## The site

`ls sites` lists them. The one on the domain, `one.DOMAIN`, is a workspace
with the demo company, served over HTTPS through the tunnel (`one-dev`),
realtime included: `/socket.io` goes to a local nginx on 9001, which adds the
Origin header socketio insists on and passes it to 9000, and the site sets
`socketio_port` 443 for it. It is marked `one_dev` in its site config.

There is no OneAdmin on this machine. The workspace is linked to production's
OneAdmin, `admin.4dl.app`, as a test workspace (Workspaces › New Test
Workspace, then `deploy/local/link.sh`): its OneAI, mail (`m.4dl.app`),
weather and news go through production, nothing is billed, OneAdmin never
updates or moves it, and it sends its own backups to production's keeper.
Its credits are given by hand on its Tenant. `deploy/local/dev-config.sh
DOMAIN` builds the demo and links it.

Passwords are in `~/.one-local` (`PUBLIC_ADMIN_PASSWORD` for the site,
`ONE_OPERATOR_KEY` for `rescue.py pack`). Never print it, or the site's
`one_token`, `one_mail_secret` or `one_backup_secret`.

## What never to do here

- The workspace speaks to production. What its people do with OneAI spends
  real credits and real money at the model providers, and mail it sends goes
  out from `m.4dl.app`. Test with that in mind.
- Never put a Stripe key here, test or live: the workspace bills nothing.
- Never make an admin site here (`one_admin` in a site config) or point the
  workspace at one: dev's own OneAdmin was retired on 12 November 2026.
- Never commit in `apps/frappe`, `apps/erpnext` or `apps/hrms`. Their changed
  files are build output.
- Never drop or reinstall the domain site without being asked: it holds the
  setup the person using it did by hand. Linking it again (`RELINK=1
  dev-config.sh`) makes new keys and the old ones stop working.
- Never run a job on admin.4dl.app against a customer's workspace to test
  something. Test on this workspace, or on a training copy.

## The gates

From `apps/onedesk`: `../../env/bin/python scripts/quick.py --all` (every test, in parallel), and `scripts/quick.py` alone while working. `python3
scripts/docs.py` first when docs or the registry changed, and
`../../env/bin/python scripts/overrides.py` after touching an override. Push
only with the gates green.
