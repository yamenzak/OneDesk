# The keeper

A Worker holding the powers OneAdmin's server must not hold, so that
somebody who takes the server, its database and its config can still not
delete a backup or change the bucket's lock.

## What it does

- **Backups** (`BACKUPS`, the `one-backups` bucket, `one-backups-dev` on
  dev): `PUT /backup/<key>` adds an object, `POST /fetch {url, key}` fetches
  a signed link (a Frappe Cloud backup) and keeps it, `POST /copy {bucket,
  prefix, into, cursor}` copies a tenant's files from its bucket, 200 at a
  time, skipping what is already kept. `GET /backup/<key>` and `GET
  /backups?prefix=` read them back for a restore. Nothing deletes or
  overwrites: a key already kept is left as it is.
- **The rescue kit**: `GET /rescue/latest` gives the newest file under
  `rescue/` to whoever shows `x-one-rescue`, a secret worked out from the
  rescue passphrase. The keeper holds only its SHA-256 (`rescue:hash` in the
  routing store, set by `POST /rescue-key` with the keeper's secret), so a new
  machine needs the passphrase alone to fetch the kit (deploy/local/README.md).
- **A workspace's own backups**, signed with its own secret: `PUT
  /workspace/<slug>/<part>/<name>` keeps the night's under `daily/`, and
  `PUT /workspace/<slug>/recent/<stamp>/<part>/<name>` keeps a four-hourly
  database or config under `recent/`. A stamp more than an hour old or in
  the future is refused, so a stolen secret cannot put a backup at the top
  of the list.
- **Search credentials**: `POST /search-credentials {bucket, prefix, ttl}`
  makes Cloudflare's temporary R2 credentials for a workspace's `search/`
  prefix alone, in a workspace bucket alone. Cloudflare asks an
  account-wide R2 token for these (tested on 8 November 2026: a bucket-item
  token is refused), and that token could also lift a bucket's lock, so it
  lives here as a Worker secret and never on the server.

Every call needs the secret Set Up Cloudflare made (`x-one-secret`), kept in
OneAdmin's config as `keeper_secret`.

## The bucket and its lock

Set Up Cloudflare makes the bucket and locks every object in it for 30
days (an R2 bucket lock), and adds lifecycle rules so `recent/` goes after 7
days, `daily/` after 31 and `monthly/` after 366. A lock outranks a lifecycle
rule, so while the whole bucket is locked for 30 days a four-hourly backup
really stays 30 days. Locks and lifecycle are changed only by a run
of Set Up Cloudflare, with the master key, which is never kept. OneAdmin's
day-to-day token has no R2 or Workers rights at all, so it cannot redeploy
this Worker with a delete path either.

## Deploying

`Setup.keeper` uploads `worker.js` through the API with its bindings: the
backup bucket, both workspace buckets, the account, the storage key's id,
the workspace buckets' names, and two secrets (`ONE_SECRET`, `R2_TOKEN`).
`R2_TOKEN` is One's "Keeper" token, rolled for a new secret on every run
and given only to the Worker.
