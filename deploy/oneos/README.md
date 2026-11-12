# OneOS

A desktop in the browser for one file at a time: a Cloudflare Container per
session, running LibreOffice on a small Linux desktop, shown in the browser
over a websocket through the Worker `one-os`. The file is copied in when the
session starts and copied back each time it is saved; nothing stays in the
container after the session ends.

## How it is reached

Two ways in, each guarded by the secret Set Up Cloudflare made
(`oneos_secret` in the vault; `ONE_SECRET` on the Worker).

- **OneAdmin**, with the secret as `x-one-secret`:
  - `POST /sessions/{id}` with `{file_url, save_url, name, app, size,
    lasts_seconds}` starts the session's container and answers
    `{state: "starting"}` (202). Both addresses must be https; `app` is
    `libreoffice`, `size` is `standard-1`, `lasts_seconds` 60 to 86400.
  - `GET /sessions/{id}` answers `{state, idle_seconds, saved_at}`, `state`
    being `starting`, `running` or `stopped`. A session whose file could not
    be downloaded is stopped and says why in `reason`.
  - `POST /sessions/{id}/stop` asks LibreOffice to save, sends the file back
    if it changed, destroys the container and answers
    `{state: "stopped", saved_at}`.
  - `saved_at` is UTC, `2026-11-12T10:00:00Z`, or null before the first save.
- **A browser**, at `/s/{id}/?t=TOKEN`. `TOKEN` is
  `{expires}.{hex HMAC-SHA256(secret, "{id}.{expires}")}`, `expires` in Unix
  seconds. The Worker checks it, leaves it as the `one-os` cookie
  (`Path=/s/{id}`, HttpOnly, Secure, until `expires`) and sends the browser
  on to the same address without it; every later request and the websocket
  are let through on the cookie. A token for one session opens no other.
  Neither the cookie nor the secret is passed to the container, and the
  browser path never starts a container: a session OneAdmin did not start,
  or one that ended, answers 410.

Anything else is 404, and a call without the secret 403.

A session id is 8 to 64 letters, digits, `_` or `-`: the Durable Object
`Session` named by it holds the one container. A session stops by itself
ten minutes after the last request reaches it with no browser open, and
always ten minutes after its `lasts_seconds`, whatever OneAdmin does.

## Inside the container

`image/` is the container: linuxserver's Selkies base on Alpine
(`lscr.io/linuxserver/baseimage-selkies:alpine324`) with LibreOffice
Writer, Calc, Impress and Draw, English, German and Arabic, and the fonts
that stand in for Office's. Selkies streams the desktop to the browser over
a websocket from nginx on port 3000, which has no login of its own: only
the Worker can reach a container. `HARDEN_DESKTOP` turns off the terminal,
sudo, file transfers in the sidebar and opening other programs, and
LibreOffice's macros are off.

`one-session` starts with the desktop (`/defaults/autostart`, as the
desktop's user `abc`, home `/config`). It downloads `file_url` into
`/config/Documents/<name>`, opens it in LibreOffice, maximised, and opens it
again if it is closed. Each save (LibreOffice writes a new file and renames
it over the old, so `inotifywait` hears `moved_to` as well as `close_write`)
is POSTed to `save_url` as a form with the file in its `file` field, unless
it is what was last sent. Port 3100 answers `GET /state` with
`{ready, failed, idle_seconds, saved_at, saves}`, the idle seconds being
`xprintidle`'s since the last key or mouse movement on the desktop, and
`POST /state` presses Ctrl+S in LibreOffice first (it keeps the file's own
format without asking) and waits for the save to be sent.

The base image moved from KasmVNC to Selkies in July 2025, and linuxserver's
KasmVNC base has had no build since, so OneOS is on Selkies: the same idea,
the desktop drawn in the browser over a websocket, and the base linuxserver
keeps up. It runs on X11 rather than Wayland (`PIXELFLUX_WAYLAND=false`) so
that `xprintidle` and `xdotool` work.

## The image

`.github/workflows/oneos-image.yml` builds `image/` whenever it changes on
`main` (or when run by hand) and pushes it to Cloudflare's own registry
with `wrangler containers push`, tagged with the folder's tree id
(`git rev-parse HEAD:deploy/oneos/image`). Cloudflare's registry is the one
it pulls from fastest, and GitHub's is not among those it can pull from. It
pushes with two repository secrets, which production's Set Up Cloudflare
writes through OneAdmin's GitHub App (`Setup.github`), so nobody pastes them:

- `CLOUDFLARE_ACCOUNT_ID`: the account Set Up Cloudflare uses.
- `CLOUDFLARE_CONTAINERS_TOKEN`: the `[one-prod] OneOS Images` token, allowed
  **Account Settings Read** and **Workers Containers Write** on that account
  only, rolled on every run.

Until its image is in the registry, the deploy fails. On a first setup, press
Set Up Again once GitHub is connected, run the OneOS image workflow from
GitHub's Actions tab, then Set Up Again.

## Deploying

Set Up Cloudflare (`one_admin/setup.py`, `Setup.oneos`) runs `npm install`
and `wrangler deploy` here with a `wrangler.jsonc` it writes (the name
carries the environment: `one-os-dev` on dev), naming the image
`registry.cloudflare.com/<account>/one-os:<tree id>`, which it works out from
the files themselves. It puts the secret, and keeps the address in One Admin
Settings (OneOS) and the secret in the vault. It is done again only when the
Worker's files or the image change. At most ten sessions run at once
(`ONEOS_MOST`).

## What it costs

A session is a `standard-1` instance: half a vCPU, 4 GiB, 8 GB of disk.
Cloudflare bills memory and disk for every second it runs and CPU while it
works: about $0.038 an hour idle and $0.074 busy, and the picture sent to
the browser as data out, a few hundred MB to a GB or two an hour. OneAdmin
bills each running minute at the workspace's rate and stops a session that
has been idle for fifteen minutes, so nothing runs for nobody.

## Licences

LibreOffice is MPL-2.0, Selkies MPL-2.0, linuxserver's base image GPL-3.0,
and Alpine's packages their own free licences. The image is built from their
public sources and ours (AGPL-3.0, `one-session`, `autostart` and the
LibreOffice settings), and is kept in Cloudflare's registry for this account
only.
