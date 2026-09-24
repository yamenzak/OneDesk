"""R2, signed by admin and carried by Cloudflare.

Admin is in the control path and never the data path. It checks the quota, works
out the key and signs a URL; the browser then talks to R2 directly and not one
byte passes through this process. Doing it the other way would put every
tenant's uploads through one Frappe site with four workers, and that is the
first thing that would fall over.

**Two buckets, Global and EU, and a prefix per tenant.** Jurisdiction is chosen
once at signup and is permanent — R2 pins a bucket to it at creation, so moving
afterwards means copying every object. Never a bucket per tenant: a lifecycle
rule written against one bucket gets written against the next one too, and a key
scoped to a bucket still reaches every tenant in it.

**Usage is measured, not reported.** The nightly pass lists each prefix and adds
it up. A workspace that reported its own number would be a workspace that could
under-report it, and the whole reason storage is billed from here is that a
tenant cannot be the authority on what it owes.
"""

import boto3
from botocore.client import Config

import frappe
from frappe.utils import cint

from onedesk.one_admin import keys

#: How long a signed URL is good for. Long enough for a slow upload on a bad
#: connection, short enough that one found in a log is not a key to the object.
GOOD_FOR = 15 * 60

#: Where R2 answers. Account-scoped, with the EU bucket reached through a
#: jurisdiction-specific host.
HOSTS = {
	"Global": "https://{account}.r2.cloudflarestorage.com",
	"EU": "https://{account}.eu.r2.cloudflarestorage.com",
}

#: R2 ignores regions but boto3 insists on one.
REGION = "auto"


def put_url(tenant, key: str, size: int) -> dict:
	"""A URL the browser may PUT this object to, if there is room for it."""
	held = cint(tenant.storage_bytes)
	pending = cint(tenant.storage_pending)
	if not keys.room_for(held, pending, cint(tenant.storage_limit), cint(size)):
		frappe.throw(
			frappe._("This workspace has no room for another {0}.").format(
				frappe.format_value(size, {"fieldtype": "Int"})
			),
			frappe.ValidationError,
		)

	full = keys.under(tenant.name, key)
	signed = _client(tenant.jurisdiction).generate_presigned_url(
		"put_object",
		Params={"Bucket": _bucket(tenant.jurisdiction), "Key": full},
		ExpiresIn=GOOD_FOR,
	)
	frappe.db.set_value(
		"Tenant", tenant.name, "storage_pending", pending + cint(size), update_modified=False
	)
	return {"url": signed, "key": full, "expires_in": GOOD_FOR}


def get_url(tenant, key: str, filename: str | None = None, inline: bool = True) -> dict:
	"""A URL the browser may GET this object from. With a filename, R2 answers
	with it in Content-Disposition, so a download is saved under the name the
	person knows rather than the key; inline or as an attachment."""
	full = keys.under(tenant.name, key)
	params = {"Bucket": _bucket(tenant.jurisdiction), "Key": full}
	if filename:
		import mimetypes

		params["ResponseContentDisposition"] = disposition(filename, inline)
		params["ResponseContentType"] = mimetypes.guess_type(filename)[0] or "application/octet-stream"
	signed = _client(tenant.jurisdiction).generate_presigned_url(
		"get_object",
		Params=params,
		ExpiresIn=GOOD_FOR,
	)
	return {"url": signed, "key": full, "expires_in": GOOD_FOR}


def disposition(filename: str, inline: bool = True) -> str:
	"""A Content-Disposition naming the file, for every browser: an ASCII
	fallback and the real name in RFC 5987 form. Pure."""
	from urllib.parse import quote

	plain = "".join(ch if 32 <= ord(ch) < 127 and ch not in '"\\' else "_" for ch in filename) or "file"
	kind = "inline" if inline else "attachment"
	return f"{kind}; filename=\"{plain}\"; filename*=UTF-8''{quote(filename, safe='')}"


def remove(tenant, key: str) -> dict:
	"""Delete one object.

	Done here rather than signed, because a signed DELETE is a capability to
	destroy that outlives the request, and unlike a read there is nothing to gain
	from letting the browser do it directly.
	"""
	full = keys.under(tenant.name, key)
	_client(tenant.jurisdiction).delete_object(Bucket=_bucket(tenant.jurisdiction), Key=full)
	return {"key": full, "deleted": True}


#: Objects per delete call. S3 caps this at a thousand and R2 follows it.
AT_A_TIME = 1000


def empty(tenant) -> int:
	"""Delete everything under this workspace's prefix, and say how much.

	The last rung of the ladder and the only step on it that destroys anything
	of ours. It is written to be safe to run twice, because the runner retries:
	emptying a prefix that is already empty deletes nothing and succeeds, so a
	sweep that died half way finishes on the next attempt rather than starting
	an argument about where it got to.

	The prefix comes from `keys.prefix`, which refuses a slug with a slash in
	it. That is the whole of what stands between this and deleting the wrong
	workspace's objects, and it is the reason that function is pure and tested.
	"""
	client = _client(tenant.jurisdiction)
	bucket = _bucket(tenant.jurisdiction)
	prefix = keys.prefix(tenant.name)
	gone = 0
	pages = client.get_paginator("list_objects_v2")
	for page in pages.paginate(Bucket=bucket, Prefix=prefix):
		held = [{"Key": item["Key"]} for item in page.get("Contents") or []]
		for at in range(0, len(held), AT_A_TIME):
			batch = held[at : at + AT_A_TIME]
			client.delete_objects(Bucket=bucket, Delete={"Objects": batch, "Quiet": True})
			gone += len(batch)
	frappe.db.set_value(
		"Tenant",
		tenant.name,
		{"storage_bytes": 0, "storage_pending": 0},
		update_modified=False,
	)
	return gone


def measure(slug: str) -> int:
	"""Add up everything under this workspace's prefix."""
	tenant = frappe.get_doc("Tenant", slug)
	total = 0
	pages = _client(tenant.jurisdiction).get_paginator("list_objects_v2")
	for page in pages.paginate(
		Bucket=_bucket(tenant.jurisdiction), Prefix=keys.prefix(slug)
	):
		total += sum(item["Size"] for item in page.get("Contents") or [])
	frappe.db.set_value(
		"Tenant", slug, {"storage_bytes": total, "storage_pending": 0}, update_modified=False
	)
	return total


def nightly() -> None:
	"""Measure every live workspace and say so when one is over.

	Sequential on purpose. A hundred tenants is a hundred listings once a night,
	and a queue of parallel jobs against one bucket is a way to be rate-limited
	by Cloudflare at three in the morning.
	"""
	from onedesk.one_admin import site

	if not site.is_admin():
		return
	for slug, limit in frappe.get_all(
		"Tenant", filters={"status": "Live"}, fields=["name", "storage_limit"], as_list=True
	):
		try:
			held = measure(slug)
		except Exception:
			frappe.log_error(title=f"Measuring {slug}")
			continue
		if cint(limit) and held > cint(limit):
			_over(slug, held, cint(limit))
		frappe.db.commit()


def _over(slug: str, held: int, limit: int) -> None:
	frappe.get_doc(
		{
			"doctype": "Tenant Event",
			"tenant": slug,
			"kind": "Over Storage",
			"detail": f"holding {held} bytes against a limit of {limit}",
		}
	).insert(ignore_permissions=True)


def _bucket(jurisdiction: str) -> str:
	field = "bucket_eu" if jurisdiction == "EU" else "bucket_global"
	name = frappe.get_cached_value("One Admin Settings", None, field)
	if not name:
		frappe.throw(frappe._("No {0} bucket is configured.").format(jurisdiction))
	return name


def _client(jurisdiction: str):
	stored = frappe.get_cached_doc("One Admin Settings")
	account = frappe.conf.get("cloudflare_account") or stored.cloudflare_account
	key_id = frappe.conf.get("r2_key_id") or stored.r2_key_id
	secret = frappe.conf.get("r2_secret") or stored.get_password("r2_secret", raise_exception=False)
	if not (account and key_id and secret):
		frappe.throw(frappe._("R2 is not configured. Set it in One Admin Settings."))
	# Any S3-compatible endpoint instead of R2's, for a self-hosted bench and
	# for development against a local stand-in. Site config only: an endpoint is
	# where every tenant's bytes go, so no screen may change it.
	endpoint = frappe.conf.get("r2_endpoint") or HOSTS[jurisdiction if jurisdiction in HOSTS else "Global"].format(
		account=account
	)
	return boto3.client(
		"s3",
		endpoint_url=endpoint,
		aws_access_key_id=key_id,
		aws_secret_access_key=secret,
		region_name=REGION,
		config=Config(signature_version="s3v4"),
	)
