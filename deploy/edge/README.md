# The edge router

One Worker, one wildcard DNS record, one certificate. Everything a workspace
needs to be reached at `<slug>.t.4dl.app`, and nothing per tenant.

## Why it exists

Frappe Cloud serves a site under its own name — `<slug>.frappe.cloud` — and holds
the certificate for that name. It will not serve ours. A wildcard certificate on
their side needs a `Root Domain` record, which carries AWS credentials and is an
operator-only doctype; we are a customer of theirs, so that door is shut.

Press also refuses any domain that is proxied. `press/utils/dns.py` sends a HEAD
request and reads the `server:` response header; anything that is not
`Frappe Cloud` — Cloudflare's orange cloud answers `cloudflare` — is rejected
with `DomainProxied`. So a proxied `*.t.4dl.app` could never be added to press
even if we wanted it there.

The answer to both is the same: **never tell press about our name.** The Worker
answers for `<slug>.t.4dl.app`, rewrites `Host` to the press site name, and
forwards. Press sees a request for a site it already serves, with a certificate
it already holds. The browser sees Cloudflare's certificate, from the Advanced
Certificate Manager wildcard on the zone. There is nothing to verify because
nothing is asked.

A customer's own domain is the opposite and goes the ordinary way: press adds
it, checks the DNS, and issues a Let's Encrypt certificate over HTTP-01. That is
`one_admin/domains.py`, and it needs no Cloudflare call at all.

## One-time setup

1. **Advanced Certificate Manager** on the `4dl.app` zone, covering
   `*.t.4dl.app`. One level below the apex on purpose: a certificate for it
   cannot also cover the marketing site or the admin console.
2. **A proxied DNS record** for `*.t.4dl.app`. An `A` record at `192.0.2.1` is
   fine — it is never dialled, because the Worker answers before the origin is
   consulted. It must be proxied (orange), or the Worker never runs.
3. **A Workers KV namespace.** Put its id in `wrangler.toml` and the same id in
   One Admin Settings as the Workers KV Namespace.
4. **An API token** with exactly one permission: *Workers KV Storage: Edit*, on
   that namespace. It goes in One Admin Settings. It can do nothing else to the
   account — it cannot touch DNS, certificates, or any other Worker.
5. `wrangler deploy`.

## Per tenant

Nothing, at Cloudflare. Provisioning writes one KV key — the slug against the
press site name — from `one_admin/steps.py:route_it`, and that is the whole of
it. No DNS record, no route, no certificate.

## Why KV rather than asking the admin site

The admin site is the control path and must never become the data path. A Worker
that called it on every request would make an admin outage an outage for every
workspace. KV is Cloudflare's own edge store: once the key is written, serving a
workspace needs nothing of ours at all.
