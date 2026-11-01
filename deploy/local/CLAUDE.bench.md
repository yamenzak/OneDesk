<!-- Written by apps/onedesk/deploy/local/setup.sh from CLAUDE.bench.md, every run. Edit it there. -->
# This machine: One's dev bench

You are on the dev server, not production. Production is on Frappe Cloud and
is changed only by pushing `main` and deploying there. Nothing on this machine
reaches it, and nothing you do here should try to.

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
- A doctype or fixture JSON change needs `bench --site SITE migrate`.
- You may be running under the `one-claude` service (Remote Control), started
  in `apps/onedesk` and sharing it with the bench: what you change is served
  at once. Never stop or restart `one-claude` yourself; that ends the session
  you are in.

## The sites

`ls sites` lists them. The pair on the domain (`one.DOMAIN`, a workspace, and
`admin.DOMAIN`, OneAdmin) are served over HTTPS through the tunnel, realtime
included: `/socket.io` goes to a local nginx on 9001, which adds the Origin
header socketio insists on and passes it to 9000, and the sites set
`socketio_port` 443 for it. They are marked `one_dev` in their site config. The workspace is linked to
the dev OneAdmin as its house workspace, so its OneAI is unbilled.

Passwords are in `~/.one-local` (`PUBLIC_ADMIN_PASSWORD` for the domain pair).
Dev's OneAdmin values are in `~/.one-dev.json`; `deploy/local/dev-config.sh
DOMAIN` writes them again. Never print either file.

## What never to do here

- Never clear Environment in the dev OneAdmin, and never give it production's
  domains (`t.4dl.app`, `m.4dl.app`, `noreply@4dl.app`). Environment `dev` is
  what keeps Set Up Cloudflare on its own Workers, store, tokens and catch-all;
  dev-config.sh writes it every run.
- Never put a Stripe live key here; dev takes test keys.
- Never commit in `apps/frappe`, `apps/erpnext` or `apps/hrms`. Their changed
  files are build output.
- Never drop or reinstall the domain sites without being asked: they hold the
  setup the person using them did by hand.
- A signup on the dev OneAdmin builds a real site on Frappe Cloud, on the dev
  bench group, and costs money while it lives: archive what you made for a
  test when the test is done.

## The gates

From `apps/onedesk`: `../../env/bin/python -m pytest -q`. `python3
scripts/docs.py` first when docs or the registry changed, and
`../../env/bin/python scripts/overrides.py` after touching an override. Push
only with the gates green.
