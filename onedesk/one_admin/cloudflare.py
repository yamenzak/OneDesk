"""The one thing Cloudflare is asked to do, and the reason it is so little.

A workspace is reached at `<slug>.t.4dl.app`. That name resolves to one proxied
wildcard record and one Worker route, both made once by **Set up Cloudflare**
(setup.py); no tenant ever gets a DNS record of its own. What the Worker needs is the answer to one
question — which press site is this slug? — and this module writes that answer
into a Workers KV namespace as the site is provisioned.

**Why KV rather than the Worker asking us.** The admin site is the control path
and must never become the data path. A Worker that calls us on every request
means an admin outage is an outage for every workspace, which is exactly the
coupling the rest of this design avoids. KV is Cloudflare's own edge store: once
the key is written, serving a workspace needs nothing of ours at all.

**Nothing here issues a certificate.** `*.t.4dl.app` is covered by the Advanced
Certificate Manager wildcard on the zone, which is a one-time purchase rather
than a per-tenant call. A customer's own domain is press's to certify, over
Let's Encrypt — see `domains.py`.

The token this uses needs one permission, Workers KV Storage: Edit, on one
namespace. It can do nothing else to the account.
"""

import json

import frappe
import requests

from onedesk.one_admin import faults

#: Cloudflare's v4 API. The KV endpoints are the only ones we call.
API = "https://api.cloudflare.com/client/v4"

#: Seconds. KV writes are small and fast; anything slower than this is an outage
#: rather than a slow call, and the step will be retried by the runner.
TIMEOUT = 15


def route(slug: str, site: str) -> None:
	"""Tell the edge that this slug is served by this press site.

	A plain PUT of the same value, so running it twice is running it once. That
	matters because this is a provisioning step and every step is retried.
	"""
	if not slug or not site:
		raise faults.Refused("a route needs both a workspace and a site")
	_call("PUT", f"values/{slug}", data=site)


def mail_route(slug: str, record: dict) -> None:
	"""What the mail Worker reads for this workspace, under `mail:<slug>`: the
	site to tell, the secret to sign with, the bucket and prefix to store in,
	and the names it may receive for. The whole record, every time, so a
	retry is free and nothing is merged."""
	if not slug or not record.get("site") or not record.get("secret"):
		raise faults.Refused("a mail route needs a workspace, a site and a secret")
	_call("PUT", f"values/mail:{slug}", data=json.dumps(record))


def mail_entry(tenant, secret: str, names: list[str]) -> dict:
	"""The mail Worker's record for a workspace (deploy/mail/worker.js)."""
	from onedesk.one_admin import keys

	return {
		"site": tenant.site,
		"secret": secret,
		"bucket": "EU" if tenant.jurisdiction == "EU" else "Global",
		"prefix": keys.prefix(tenant.slug),
		"names": sorted(set(names)),
	}


def mail_domain() -> str:
	return frappe.get_cached_value("One Admin Settings", None, "mail_domain") or "m.4dl.app"


def mail_record(slug: str) -> dict | None:
	answered = _call("GET", f"values/mail:{slug}", raw=True)
	return json.loads(answered) if answered else None


def forget(slug: str) -> None:
	"""Stop serving this slug at the edge.

	Used when a workspace is archived. A DELETE of a key that is not there
	answers 200, so this is safe to run on a workspace that never had one.
	"""
	_call("DELETE", f"values/{slug}")


def routed(slug: str) -> str | None:
	"""What the edge currently believes, for the operator screen that asks.

	Not consulted by anything that provisions: a step that reads before writing
	is a step with two ways to fail instead of one.
	"""
	answered = _call("GET", f"values/{slug}", raw=True)
	return answered or None


def _call(method: str, path: str, data: str | None = None, raw: bool = False):
	account, token, namespace = _settings()
	url = f"{API}/accounts/{account}/storage/kv/namespaces/{namespace}/{path}"
	try:
		answered = requests.request(
			method,
			url,
			headers={"Authorization": f"Bearer {token}"},
			# Multipart, as the write-with-metadata endpoint takes it. A plain
			# form is stored as it is sent: `value=…&metadata=…`, in the value.
			files={"value": (None, data), "metadata": (None, "{}")} if data is not None else None,
			timeout=TIMEOUT,
		)
	except requests.RequestException as reason:
		raise faults.Again(f"cloudflare did not answer: {reason}") from reason

	if answered.status_code == 404 and method == "GET":
		return None
	if answered.status_code >= 400:
		raise faults.raised("cloudflare", answered.status_code, _detail(answered))
	return answered.text if raw else None


def _detail(answered) -> str:
	"""What Cloudflare said, in the shape it says it.

	Its errors arrive as a list of `{code, message}` under `errors`, and the
	message is the part worth keeping on a Provisioning Job.
	"""
	try:
		body = answered.json()
	except ValueError:
		return (answered.text or "")[:faults.KEPT]
	said = body.get("errors") or []
	if isinstance(said, list) and said:
		return "; ".join(str(one.get("message") or one) for one in said)[: faults.KEPT]
	return (answered.text or "")[: faults.KEPT]


def _settings():
	"""Refuses rather than skipping.

	A missing token is not "route nothing"; it is a workspace that will be built
	and then unreachable. Better to fail the step and have somebody notice.
	"""
	held = frappe.get_cached_doc("One Admin Settings")
	account = frappe.conf.get("cloudflare_account") or held.cloudflare_account
	token = frappe.conf.get("cloudflare_token") or held.get_password(
		"cloudflare_token", raise_exception=False
	)
	namespace = frappe.conf.get("cloudflare_kv") or held.cloudflare_kv
	if not (account and token and namespace):
		raise faults.Refused(
			"Cloudflare is not configured. Set the account, the token and the KV namespace"
			" in One Admin Settings."
		)
	return account, token, namespace
