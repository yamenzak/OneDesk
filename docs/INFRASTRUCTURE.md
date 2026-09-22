# The platform — one app, one admin site, and a proxy for everything billed

One codebase ships to every site. A site is the admin site when its
`site_config.json` says so, and a tenant workspace otherwise. There is no second
app, no second repo, and no second deploy.

Everything a customer is billed for goes through the admin site, and the admin
site is in the **control path and never the data path** — it checks, it signs, it
records, and the bytes go somewhere else.

## What each party owns

**Frappe Cloud owns the servers.** Servers, benches, clusters, sites, their
backups and their upgrades are press's, and we are a press customer rather than
its operator. We never reach a server or the agent daemon; press's whitelisted
HTTP API is the whole boundary.

**We own the commercial facts.** Who the customer is, what they bought, what they
have spent, which region we sold them and what their workspace is called. That is
the `Tenant` record and everything hanging off it.

**Nothing is mirrored.** There is no `Press Server`, no `Press Bench Group`, no
`Press Site` table. A table of somebody else's state is a table that is wrong
between syncs, and the way you find out is a customer who cannot be placed on a
bench that exists. What benches and clusters exist is read live from press and
cached for a minute, so a picker cannot go stale. What we store on `Tenant` is
not a copy of press's state — it is the record of **what we asked press for**,
which is ours and which has to survive press being unreachable.

The exception, if it is ever wanted: a read-only virtual doctype over press's
site list, so an operator can ask "which tenants does press think are suspended
while our ledger says active". Start without it — the same question is better
answered by a nightly reconcile that writes a `Tenant Event`, and a Link field
pointing at a virtual doctype does not validate, so the schema around it gets
infected.

## The admin flag

`site_config.json` carries `"one_admin": 1`. Nothing else turns it on. It is not a
role, not a setting and not a fixture, because all three are editable from a desk
and this one must not be: a tenant administrator can reach everything in their
own database and nothing in their own `site_config`.

What the flag changes:

* the One Admin workspace, its rail and its doctypes are visible;
* the proxy endpoints answer instead of refusing;
* the provisioning scheduler runs.

On a tenant site the same doctypes exist as empty tables and are hidden the way
`one/declutter.py` already hides things. That is the cost of one app and it is
a small one — fifteen empty tables, no rail entries, no search hits.

## The proxy, and the one rule about it

Every call goes **tenant to admin**. Admin never calls a tenant site. That single
direction removes a whole class of credentials: there is no admin key that opens
every workspace, because admin never needs to open one.

A tenant proves who it is with a token written into its own `site_config` at
provision time; admin stores only a hash of it. **Bench common config carries the
admin URL and nothing else.** The old design put R2 credentials, the Cloudflare
token and the AI keys in common config, which every tenant site can read — one
compromised tenant was the whole fleet's storage. Nothing shared and secret ever
goes there again.

What the proxy answers:

    hello              what plan, what limits, what is left
    storage.put_url    quota checked, presigned R2 PUT returned
    storage.get_url    presigned R2 GET
    storage.delete     and the usage adjustment
    storage.report     nightly, what this workspace is holding
    backup.put_url     presigned PUT under backups/<tenant>/<stamp>/
    ai.run             hold, call the gateway, settle, return
    credits.balance
    domain.add         press add-domain, returns the CNAME to show
    domain.status
    checkout           a Stripe session for a plan, pack or add-on

Files never pass through admin. A browser uploading a 200 MB attachment asks
admin for a signed URL and then talks to R2 directly; admin has handled a few
hundred bytes. Doing it the other way puts every tenant's uploads through one
Frappe site with four workers, and that is the first thing that would fall over.

AI is the deliberate exception. Payloads are kilobytes and admin owns the ledger
anyway, so one call does hold, call and settle rather than three round trips —
and the gateway token never exists on a tenant site at all. The tenant's
background worker republishes the stream to its own socketio room.

**Anything that charges carries an idempotency key.** A network timeout leaves us
unable to tell whether a call landed, and the failure we refuse is billing a
customer twice because a response was lost.

What breaks when admin is down: new uploads, new AI calls, checkout. What does
not: every other thing anybody does all day.

## Domains

Frappe Cloud gives a site a name on its own domain. We are not Frappe, so every
workspace is reached at `<slug>.t.4dl.app`, and the customer may later put their
own hostname in front of it.

`t.` rather than the apex is deliberate: a certificate for `*.4dl.app` would
cover the marketing site and the admin portal, and tenant hostnames should not
share a namespace with our own hosts.

There are two ways to make `<slug>.t.4dl.app` work and the difference is whether
a signup waits for a certificate.

**The one we want — Cloudflare in front, press never learns the hostname.**
Advanced Certificate Manager issues one wildcard certificate for `*.t.4dl.app`,
Cloudflare terminates TLS with it, and a Worker rewrites the `Host` header to the
press site name before passing the request to the origin. Press sees a request
for a site it already serves. Provisioning does no domain work at all: no
add-domain call, no certificate, no waiting, ever. The site's own config carries
`host_name` so Frappe builds its links and cookies against the public hostname
rather than the one the origin saw.

**Read against press's own code, this is not a preference — it is the only door
open to us.** Press issues a wildcard certificate only for a `Root Domain`, and
that path runs `certbot --dns-route53` with AWS credentials held on an
operator-only doctype (`tls_certificate.py`). We are a customer; there is no
call by which `t.4dl.app` becomes one. Press also refuses any domain that is
proxied: `utils/dns.py` sends a HEAD and rejects anything whose `server:` header
is not `Frappe Cloud`, and Cloudflare's orange cloud answers `cloudflare`. So a
proxied `*.t.4dl.app` could not be added to press even if we wanted it there.
Never telling press about the name answers both at once.

One detail decides the shape rather than the principle: the Host rewrite is
load-bearing. If it breaks, every workspace meets press's nginx as an unknown
host. So it is one Worker with one job — `deploy/edge/` — and it is proved
end to end before anything is built on top of it.

**Per tenant, Cloudflare is asked for nothing.** A proxied wildcard record and
one Worker route cover every slug, and provisioning writes a single Workers KV
key, the slug against the press site name. That is the whole of the per-tenant
work, and the API token it needs carries one permission: Workers KV Storage:
Edit, on one namespace. It cannot touch DNS, certificates or any other Worker.
KV rather than the Worker asking the admin site, because admin is the control
path and a Worker that called it on every request would make an admin outage
everybody's outage.

What this buys beyond speed: every tenant hostname is behind Cloudflare, so WAF,
rate limiting, caching and per-hostname analytics come with it.

**The fallback, if the rewrite cannot be made to work.** Provisioning calls
press's add-domain for `<slug>.t.4dl.app` and marks it default, exactly as a
customer domain is added later. Simple, entirely supported, and every signup
waits out certificate issuance. It is the same code path as a custom domain, so
choosing it costs a configuration switch rather than a rewrite.

**A customer's own domain is the other case and is per-domain by nature.** They
enter `erp.acme.com` in their One area, their site asks the proxy, admin calls
press's add-domain and hands back the CNAME target to display, and the tenant
site polls admin until press reports it active. The tenant never holds a press
token. Certificate issuance takes a minute or two here and that is fine — a
customer pointing their own DNS expects to wait for something.

## Where a workspace lives

One question at signup, not two. **"Where should this workspace live"** sets both
the press cluster the site is created on and the R2 bucket its files go in.
Asking twice lets somebody choose EU storage with US compute and then ask us why.

With one cluster there is no picker — the page does not render a choice of one.

Jurisdiction is permanent and the signup page says so. R2 pins a bucket to its
jurisdiction at creation, and changing it afterwards means copying every object.
Two buckets exist, one Global and one EU, and a tenant is a prefix inside one of
them. There is never a bucket per tenant: a lifecycle rule written against one
bucket gets written against the next one too, and a key scoped to a bucket still
reaches every tenant in it, so bucket-per-hundred-tenants bounded nothing worth
bounding.

## Provisioning

A resumable job, driven by a two-minute cron rather than inline, so a request
never blocks on press and a worker restart mid-provision loses nothing.

**Every step is idempotent**, because a timeout leaves us genuinely unable to tell
whether the call landed, and the failure mode we refuse is creating two sites and
billing for both. A step returns done, or "not yet, come back", or raises a
permanent failure that stops the job and tells an operator why.

The steps:

1. take the money — the request is not provisioned until Stripe says so;
2. claim a warm site from the standby pool, or create one;
3. push site config: the admin URL, the tenant token, `host_name`, the region;
4. write the Workers KV key so the edge can route the slug;
5. write the R2 prefix and record it on the tenant;
6. create the first user and send them a link;
7. mark the tenant live.

**Warm sites.** Creating a site takes minutes and somebody who has just entered
card details should not watch that. Sites are built ahead of demand under
throwaway names and claimed at signup; the customer never sees the underlying
name because they reach their workspace at `<slug>.t.4dl.app`. With the Host
rewrite, a claim is as fast as a config push.

**Nothing unwinds.** A failure marks the request failed with a reason, an operator
resumes it, and the customer is told something true. Unwinding a half-provisioned
site is how you end up having taken money and deleted the thing it bought.

## The setup wizard

Provisioning pre-fills what it already knows — the company name from the account
request, the country from the region — so the first screen a customer sees asks
for what only they can answer. `one/setup_wizard.py` is already the place that
decides what a new workspace gets; this adds the facts it should not have to ask
for.

## What lives where

Fifteen doctypes on the operator side, against thirty-eight in the old control
plane. The four that described SPA spaces die with the SPA, the four that
mirrored press become live calls, and plan, pack, add-on and catalogue price
collapse into one `Offering` with quota rows.

**One Admin** — `One Admin Settings` (single), `Tenant` (+ `Tenant Member`),
`Tenant Event`, `Account Request`, `Provisioning Job`, `Standby Site`,
`Offering` (+ `Offering Quota`), `Promo Code`, `Subscription`,
`Stripe Webhook Event`, `Credit Ledger Entry`, `Credit Reservation`,
`AI Model` (+ `AI Model Rate`), `AI Usage Record`, `Support Login`.

**One AI**, on every site — `AI Action` (a fixture an operator may edit),
`AI Action Setting`, `AI Run`, `AI Proposal`.

**One**, on every site — `Workspace Account`, a single holding what this
workspace last heard from admin about its plan, its storage and its credits, so a
screen can be drawn without a round trip and an admin outage does not blank it.

Storage is a measurement rather than a ledger: a nightly report writes the number
onto `Tenant` and an overage writes a `Tenant Event`. A second ledger to
reconcile against the first is a second thing to be wrong.

## The stages

**INFRA 1 — the hostname.** One Worker, the Host rewrite, the wildcard
certificate, `host_name` in site config, and a real tenant site reachable at
`<slug>.t.4dl.app`. Nothing else is built until this is proved, because the
fallback changes what provisioning does.

**INFRA 2 — the admin flag.** `one_admin` in site config, the One Admin module,
the rail, and the hiding on tenant sites. A guard that fails if an operator
doctype is reachable on a site without the flag.

**INFRA 3 — press, called not mirrored.** The client over press's API with its
errors classified into retry and never-retry, the cluster and bench reads with
their one-minute cache, and no tables.

**INFRA 4 — the tenant and the job.** `Tenant`, `Provisioning Job`, the step
runner, the cron, and provisioning one site end to end by hand from the desk.

**INFRA 5 — the proxy.** Token auth and `hello`. One endpoint proved before
there are ten.

The idempotency key moves to the first call that actually charges, which is not
storage: storage is billed for what is *held*, measured nightly, so signing the
same URL twice costs nothing and a key there would guard nothing. It lands with
the Stripe top-up in INFRA 7 and the credit spend in OneAI — and as a unique
field on the row the call writes rather than a table of keys, so a retry meets
the index rather than a check.

**INFRA 6 — storage.** The two buckets, the presigned put and get, the quota
check, the nightly measurement, and the overage event.

Usage is **measured, not reported**: the nightly pass lists each tenant's prefix
and adds it up. A workspace reporting its own number would be a workspace able to
under-report it, and the reason storage is billed from admin at all is that a
tenant cannot be the authority on what it owes. Between measurements the quota
also counts what has been *signed for*, because a signed URL is a promise
somebody may keep.

**INFRA 7 — the portal.** Signup, Stripe checkout, the webhook, the warm pool,
and a customer going from a card to a working workspace without anyone helping.

**INFRA 8 — domains.** *Done.* `hosts.py` decides what a workspace may claim
and is pure, like `keys.py` and for the same reason. `cloudflare.py` writes the
one KV key. `domains.py` relays add, check, drop and make-primary to press and
keeps a `Tenant Domain` row so the workspace's screen draws without a round
trip; `nightly` catches up on what press did while nobody was looking. The
Worker and its one-time Cloudflare setup are in `deploy/edge/`.

The certificates, plainly: `*.t.4dl.app` is Cloudflare's, from the Advanced
Certificate Manager wildcard. A customer's own domain is press's, over Let's
Encrypt and HTTP-01. Neither is ours to renew.

**INFRA 9 — the ladder.** *Done.* Five rungs — Live, Overdue, Suspended,
Archived, Dropped — walked one at a time and never skipped. `ladder.py` decides
whether a workspace is due to fall and is pure, because this is the module that
decides when somebody's data is deleted. `lifecycle.py` is what starts a fall
and what ends one; `steps.py` gained a walk per rung, driven by the same runner
and the same backoff as provisioning. An invoice failing starts it, an invoice
paid ends it, and nothing else in Stripe is listened to.

Overdue is nothing at all: the workspace works exactly as it did and somebody is
told, which is why `proxy.SERVING` carries it. Suspended is press deactivating
the site. Archived is press destroying it, having taken its own offsite backup
first. Dropped deletes our R2 prefix, and it is the only rung that destroys
anything of ours.

**The cold copy is not built, and should not be.** The plan said a server-side
R2 copy would promote the daily backup for a request rather than four gigabytes
of transfer. That is not available: press's offsite backups live in press's own
S3, and a server-side copy only works within one provider's credentials, so
getting them into our R2 would mean streaming every byte through this site to no
end — restoring is press's `restore` from press's copy either way. So the backup
is *recorded* and not copied: `archived_backup` names it, press's retention
governs it. And the R2 prefix needs no copy at all, because it is already ours
and already where it belongs; archiving a workspace moves no object.

**What an archived workspace cannot do is come back on its own.** Paying after
an archive is refused, because the site was destroyed and putting a new one in
its place from a backup is somebody's decision rather than a webhook's.

Then OneAI's ten stages run on top of this, with the ledger already where it
belongs: on the admin site, behind the proxy, where a customer cannot write
themselves credits. `docs/ONEAI.md` was written assuming the operator was a role
on the tenant's own site and said plainly that this was its weakest point. It is
not true any more, and that document's caveat section goes when INFRA 5 lands.

## The console

The operator's screens over all of the above, and the two public pages in front
of it. Everything here is the desk — no SPA, no second front end — so the work
was mostly deciding what each screen is allowed to do and then saying it in
frappe's register.

**Every operator record is read-only, and carries verbs instead.** A `Tenant`, a
`Provisioning Job`, an `Account Request` and a `Tenant Domain` are all records of
something that happened elsewhere: press did it, Stripe did it, the runner did
it. A Status field somebody can set to Done is a workspace that silently stopped
being built. So the fields are read-only and the useful actions are buttons that
call a whitelisted method — `operator.py` is the whole of that surface, and every
one of them goes through `_may()`, which is the admin flag *and* the operator
role. `Offering` is the one exception, because a price list is a decision rather
than a record.

**The verbs, and what each screen was missing.** A tenant gained the ladder — the
rung it is on, how long it has, and the fall or restore, each refusing to skip a
rung. A job gained where in its walk it stopped, as a sentence, and Resume. An
account request gained **Build Workspace**, which is `signup.accept` again: a
paid request with no workspace used to need the Stripe webhook replayed by hand.
It refuses when a workspace already exists, because `accept` hands back the one
it made and would have reported success having done nothing — the work left there
is the job's. A tenant domain gained **Refresh**, which re-asks press. An offering
gained the count of workspaces already on it, because quotas are copied onto a
tenant at signup and editing one here changes nothing for anybody who bought.

**What the operator cannot reach is enforced twice.** `has_permission` only fires
when frappe has a document in hand, so it guarded the single and left `get_list`
wide open; `permission_query_conditions` is the other half, and both hooks name
all eight One Admin doctypes.

**`/start` and `/welcome` draw their own chrome.** Frappe's Standard Footer says
"Powered by ERPNext", which on our own signup page is somebody else's badge, so
both pages empty the `navbar` and `footer` blocks and draw a mark and nothing
else. `public/css/portal.css` is a second, smaller token set: these are not desk
screens and none of espresso is loaded on them.

## What is deliberately not here

**No credential that opens more than one workspace**, anywhere, ever — which is
what the one-way proxy is for.

**No mirror of press.** If a fact can be asked for, it is asked for.

**No bytes through admin.** Admin signs and records; R2 and Cloudflare carry.

**No second runtime.** The bench's own queue, its own scheduler, its own
socketio, Cloudflare's Workers, and nothing else to deploy.
