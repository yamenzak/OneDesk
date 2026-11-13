"""R2, signed by admin and carried by Cloudflare.

Admin checks the quota, works out the key and signs a URL; the browser talks to
R2 directly. Two buckets, Global and EU, a prefix per tenant, and usage is
measured nightly, not reported.
"""

import boto3
import frappe
from botocore.client import Config
from frappe.utils import cint

from onedesk.one import registry
from onedesk.one_admin import keys, vault

GOOD_FOR = 15 * 60

HOSTS = {
	"Global": "https://{account}.r2.cloudflarestorage.com",
	"EU": "https://{account}.eu.r2.cloudflarestorage.com",
}

REGION = "auto"


class NoRoom(frappe.ValidationError):
	"""The workspace's storage is full. Its name travels back as `exc_type`,
	so the workspace can tell "full" from any other refusal (store.NoRoom)."""


def put_url(tenant, key: str, size: int) -> dict:
	"""A URL the browser may PUT this object to, if there is room for it."""
	held = cint(tenant.storage_bytes)
	pending = cint(tenant.storage_pending)
	if not keys.room_for(held, pending, cint(tenant.storage_limit), cint(size)):
		frappe.throw(
			frappe._("This workspace has no room for another {0}.").format(
				frappe.format_value(size, {"fieldtype": "Int"})
			),
			NoRoom,
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


#: Where a workspace's search index lives, under its own prefix, and how long
#: the key it is lent for it lasts.
SEARCH = "search/"
SEARCH_KEY_LASTS = 60 * 60


def search_access(tenant) -> dict:
	"""A key to the workspace's search index on R2, good for an hour and for
	its own `search/` prefix alone: LanceDB lists and writes objects there
	itself, which a signed URL a file at a time cannot do. Cloudflare's
	temporary credentials, made by the keeper Worker (deploy/keeper), since
	the token they need could also lift the backup bucket's lock."""
	import requests

	from onedesk.one_admin import faults

	stored = frappe.get_cached_doc("One Admin Settings")
	account = frappe.conf.get("cloudflare_account") or stored.cloudflare_account
	keeper, secret = stored.keeper_url, vault.get("keeper_secret")
	if not (account and keeper and secret):
		frappe.throw(frappe._("R2 is not configured. Set it in {0} Settings.").format(registry.name("one_admin")))
	bucket = _bucket(tenant.jurisdiction)
	prefix = keys.prefix(tenant.name) + SEARCH
	try:
		answered = requests.post(
			f"{keeper.rstrip('/')}/search-credentials",
			headers={"x-one-secret": secret},
			json={"bucket": bucket, "prefix": prefix, "ttl": SEARCH_KEY_LASTS},
			timeout=20,
		)
	except requests.RequestException as reason:
		raise faults.Again(f"the keeper did not answer: {reason}") from reason
	if answered.status_code != 200:
		raise faults.raised("r2 credentials", answered.status_code, answered.text[: faults.KEPT])
	said = answered.json().get("result") or {}
	endpoint = frappe.conf.get("r2_endpoint") or HOSTS[tenant.jurisdiction if tenant.jurisdiction in HOSTS else "Global"].format(
		account=account
	)
	return {
		"uri": f"s3://{bucket}/{prefix}lance",
		"options": {
			"aws_access_key_id": said.get("accessKeyId"),
			"aws_secret_access_key": said.get("secretAccessKey"),
			"aws_session_token": said.get("sessionToken"),
			"aws_endpoint": endpoint,
			"aws_region": REGION,
		},
		"expires_in": SEARCH_KEY_LASTS,
	}


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


AT_A_TIME = 1000


def empty(tenant) -> int:
	"""Delete everything under this workspace's prefix, and say how much.

	The last rung of the ladder, safe to run twice. The prefix comes from
	`keys.prefix`, which refuses a slug with a slash in it.
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
	from onedesk.one_admin import log

	log.over_storage(slug, held, limit)


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
	secret = vault.get("r2_secret")
	if not (account and key_id and secret):
		frappe.throw(frappe._("R2 is not configured. Set it in {0} Settings.").format(registry.name("one_admin")))
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


MAIL_AT_A_TIME = 100


def mail_waiting(tenant, after: str | None = None) -> list[dict]:
	"""Keys of raw messages under `mail/in/`, oldest first, after the last one
	the site read. The Worker names them by arrival time, so the order of
	the keys is the order they came in."""
	prefix = keys.prefix(tenant.name)
	listed = _client(tenant.jurisdiction).list_objects_v2(
		Bucket=_bucket(tenant.jurisdiction),
		Prefix=f"{prefix}mail/in/",
		StartAfter=keys.under(tenant.name, after) if after else f"{prefix}mail/in/",
		MaxKeys=MAIL_AT_A_TIME,
	)
	return [
		{"key": item["Key"][len(prefix) :], "size": item["Size"]}
		for item in listed.get("Contents") or []
	]

