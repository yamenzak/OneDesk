"""What's New, published to the shared `one-docs` bucket as one index, so a
workspace reads what an update brings before it lands (one/versions.py
`coming`). An admin site sends its notes whenever it migrates, merged into
what is there: an older environment never takes a newer one's notes away."""

import json

import frappe
from frappe.utils import md_to_html

from onedesk.one import media, ready
from onedesk.one_admin import site, storage
from onedesk.one_admin.setup import DOCS_BUCKET as BUCKET

KEY = "notes/index.json"
FRESH = "public, max-age=300"


def ours() -> dict:
	"""Every module's versions as this code has them, rendered."""
	out = {}
	for module in ready.MODULES:
		out[module] = [
			{
				"version": one["version"],
				"date": str(one["date"]),
				"kind": one["kind"],
				"title": one["title"],
				"html": md_to_html(media.pictured(module, one["body"], one["path"])),
			}
			for one in ready.versions(module)
		]
	return out


def merged(held: dict, mine: dict) -> dict:
	"""Two indexes as one: every version either has, ours where both do,
	newest first. Pure."""
	out = {}
	for module in set(held) | set(mine):
		by = {one["version"]: one for one in held.get(module) or []}
		by.update({one["version"]: one for one in mine.get(module) or []})
		out[module] = sorted(by.values(), key=lambda one: ready.number(one["version"]), reverse=True)
	return out


def push() -> dict:
	client = storage._client("Global")
	try:
		held = json.loads(client.get_object(Bucket=BUCKET, Key=KEY)["Body"].read())
	except Exception:
		held = {}
	index = merged(held, ours())
	client.put_object(Bucket=BUCKET, Key=KEY, Body=json.dumps(index).encode(), ContentType="application/json", CacheControl=FRESH)
	return {"modules": len(index), "versions": sum(len(one) for one in index.values())}


def after_migrate() -> None:
	"""On an admin site whose R2 is set up. A migrate never fails for it."""
	if not site.is_admin():
		return
	try:
		push()
	except Exception:
		frappe.log_error(title="What's New was not sent to R2")
