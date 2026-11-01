"""Help's pictures and clips, from the repository into the public `one-docs`
bucket every environment shares (one/media.py). An admin site sends what is
missing whenever it migrates; by hand:
bench --site <admin site> execute onedesk.one_admin.media.push
"""

import frappe

from onedesk.one import media
from onedesk.one_admin import site, storage
from onedesk.one_admin.setup import DOCS_BUCKET as BUCKET

# A file's address changes with what it holds, so what is at one never does.
KEPT = "public, max-age=31536000, immutable"


def held(client) -> set[str]:
	"""What the bucket has under the docs prefix."""
	found = set()
	for page in client.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=f"{media.PREFIX}/"):
		found.update(one["Key"] for one in page.get("Contents", []))
	return found


def push() -> dict:
	"""Send every picture and clip R2 does not have yet."""
	client = storage._client("Global")
	there = held(client)
	sent = []
	for path in media.every():
		key = media.key(path)
		if key in there:
			continue
		client.put_object(Bucket=BUCKET, Key=key, Body=path.read_bytes(), ContentType=media.kind(path), CacheControl=KEPT)
		there.add(key)
		sent.append(key)
	return {"sent": len(sent), "held": len(there)}


def after_migrate() -> None:
	"""On an admin site whose R2 is set up, send what is new. A migrate
	never fails for it: what was not sent is sent the next time, and the
	pages show it from the workspace meanwhile."""
	if not site.is_admin():
		return
	settings = frappe.get_cached_doc("One Admin Settings")
	if not (settings.get("r2_key_id") and (frappe.conf.get("cloudflare_account") or settings.get("cloudflare_account"))):
		return
	try:
		said = push()
		if said["sent"]:
			print(f"Help pictures: {said['sent']} sent to R2")
	except Exception:
		frappe.log_error(title="Help pictures were not sent to R2")
