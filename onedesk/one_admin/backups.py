"""Every workspace's newest backup and its files, and OneAdmin's own, copied
each night into the locked backup bucket through the keeper, kept again when
a workspace is archived, and listed for a restore. A workspace not on
Frappe Cloud (no bench: dev's own sites) is left out (README, Backups)."""

import os

import frappe
import requests
from frappe.utils import getdate, now_datetime, today

from onedesk.one_admin import faults, keys, press, vault

PARTS = ("database", "public", "private", "config")
BACKED_UP = ("Live", "Overdue", "Suspended")
OURS = "oneadmin"
ROUNDS = 100
PATIENCE = 900


def _keeper() -> tuple[str, dict]:
	url = (frappe.db.get_single_value("One Admin Settings", "keeper_url") or "").rstrip("/")
	secret = vault.get("keeper_secret")
	if not (url and secret):
		raise faults.Refused("the keeper is not set up")
	return url, {"x-one-secret": secret}


def _post(path: str, body: dict) -> dict:
	url, headers = _keeper()
	try:
		answered = requests.post(f"{url}{path}", json=body, headers=headers, timeout=PATIENCE)
	except requests.RequestException as reason:
		raise faults.Again(f"the keeper did not answer: {reason}") from reason
	if not answered.ok:
		raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
	return answered.json()


def key(where: str, slug: str, day: str, part: str, name: str) -> str:
	"""Where one part of one backup is kept: `daily/sahara/2026-11-08/database/x.sql.gz`.
	Pure."""
	return f"{where}/{slug}/{day}/{part}/{os.path.basename(name or part)}"


def newest(site: str) -> dict | None:
	"""Frappe Cloud's newest backup of a site, offsite first."""
	held = [one for one in press.call("press.api.site.backups", name=site) or [] if isinstance(one, dict)]
	return next((one for one in held if one.get("offsite")), held[0] if held else None)


def _copy_backup(tenant, held: dict, where: tuple[str, ...]) -> list[str]:
	day = str(getdate(held.get("creation")))
	kept = []
	for part in PARTS:
		if not held.get(f"remote_{part}_file"):
			continue
		link = press.call("press.api.site.get_backup_link", name=tenant.site, backup=held["name"], file=part)
		if not link:
			continue
		for prefix in where:
			said = _post("/fetch", {"url": link, "key": key(prefix, tenant.slug, day, part, held.get(f"{part}_file"))})
			kept.append(said.get("kept"))
	return kept


def _copy_files(tenant) -> int:
	"""The workspace's files, from its bucket into `files/`, skipping what is
	kept already: how many were new."""
	bucket = "files_eu" if tenant.jurisdiction == "EU" else "files"
	cursor, copied = None, 0
	for _round in range(ROUNDS):
		said = _post("/copy", {"bucket": bucket, "prefix": keys.prefix(tenant.name), "into": "files/", "cursor": cursor})
		copied += said.get("copied") or 0
		cursor = said.get("cursor")
		if not cursor:
			break
	return copied


def tenant(name: str) -> dict:
	"""One workspace backed up: its newest backup, kept daily (and monthly
	on the first), and its files."""
	held = frappe.get_doc("Tenant", name)
	if not (held.site and held.bench) or held.is_house:
		return {"skipped": True}
	found = newest(held.site)
	where = ("daily", "monthly") if today().endswith("-01") else ("daily",)
	kept = _copy_backup(held, found, where) if found else []
	files = _copy_files(held)
	held.db_set("last_backup", now_datetime(), update_modified=False)
	return {"kept": kept, "files": files}


def ours() -> dict:
	"""OneAdmin's own database, backed up here and kept like a workspace's."""
	from frappe.utils.backups import new_backup

	made = new_backup(ignore_files=True, force=True)
	path = made.backup_path_db
	url, headers = _keeper()
	day = today()
	kept = []
	for where in ("daily", "monthly") if day.endswith("-01") else ("daily",):
		with open(path, "rb") as body:
			answered = requests.put(f"{url}/backup/{key(where, OURS, day, 'database', path)}", data=body, headers=headers, timeout=PATIENCE)
		if not answered.ok:
			raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
		kept.append(answered.json().get("kept"))
	return {"kept": kept}


def nightly() -> None:
	"""Scheduled daily: OneAdmin's own backup, and a job for each workspace
	still running."""
	from onedesk.one_admin import site

	if not site.is_admin():
		return
	frappe.enqueue("onedesk.one_admin.backups.ours", queue="long", timeout=PATIENCE)
	for name in frappe.get_all("Tenant", filters={"status": ["in", BACKED_UP], "is_house": 0, "site": ["is", "set"], "bench": ["is", "set"]}, pluck="name"):
		frappe.enqueue("onedesk.one_admin.backups.tenant", queue="long", timeout=PATIENCE * 2, name=name, job_id=f"one_backup_{name}", deduplicate=True)


def archived(tenant) -> list[str]:
	"""A workspace being archived: its newest backup kept under `archived/`,
	which no lifecycle rule expires, and its files once more."""
	found = newest(tenant.site) if tenant.site else None
	kept = _copy_backup(tenant, found, ("archived",)) if found else []
	_copy_files(tenant)
	return kept


def listed(slug: str) -> list[dict]:
	"""Every backup kept of a workspace, newest first: its day, where it is
	kept, and its parts."""
	url, headers = _keeper()
	days: dict[tuple, dict] = {}
	for where in ("archived", "monthly", "daily"):
		cursor = None
		while True:
			answered = requests.get(f"{url}/backups", params={"prefix": f"{where}/{slug}/", "cursor": cursor or ""}, headers=headers, timeout=60)
			if not answered.ok:
				raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
			said = answered.json()
			for one in said.get("objects") or []:
				_where, _slug, day, part, _name = one["key"].split("/", 4)
				held = days.setdefault((day, where), {"day": day, "where": where, "parts": {}})
				held["parts"][part] = {"key": one["key"], "size": one["size"]}
			cursor = said.get("cursor")
			if not cursor:
				break
	return sorted(days.values(), key=lambda one: (one["day"], one["where"] == "archived"), reverse=True)


def chosen(slug: str, day: str, where: str) -> dict:
	"""One kept backup of a workspace: its parts, as `listed` gives them."""
	found = next((one for one in listed(slug) if one["day"] == day and one["where"] == where), None)
	if not found or "database" not in found["parts"]:
		raise faults.Refused(f"no backup of {slug} kept for {where} {day}")
	return found


def form(fields: dict, name: str, size: int, chunks) -> tuple[int, str, object]:
	"""A multipart form of `fields` and one file, streamed: its length, its
	content type and its body, the file's bytes read as they come. S3's
	signed POST takes a length and no chunked upload. Pure but for `chunks`."""
	boundary = f"one-{os.urandom(12).hex()}"
	head = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items())
	head += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
	tail = f"\r\n--{boundary}--\r\n"
	opening, closing = head.encode(), tail.encode()

	def body():
		yield opening
		yield from chunks
		yield closing

	return len(opening) + size + len(closing), f"multipart/form-data; boundary={boundary}", body()


def to_press(part: dict) -> str:
	"""One kept part of a backup uploaded to Frappe Cloud for a restore:
	streamed from the keeper into Frappe Cloud's signed upload, and the name
	Frappe Cloud gives the file."""
	url, headers = _keeper()
	name = os.path.basename(part["key"])
	signed = press.call("press.api.site.get_upload_link", file=name) or {}
	if not signed.get("url"):
		raise faults.Again("Frappe Cloud gave no upload link")
	with requests.get(f"{url}/backup/{part['key']}", headers=headers, stream=True, timeout=PATIENCE) as kept:
		if not kept.ok:
			raise faults.raised("keeper", kept.status_code, kept.text[: faults.KEPT])
		length, kind, body = form(signed.get("fields") or {}, name, part["size"], kept.iter_content(1024 * 1024))
		sent = requests.post(signed["url"], data=body, headers={"Content-Type": kind, "Content-Length": str(length)}, timeout=PATIENCE * 4)
	if sent.status_code not in (200, 201, 204):
		raise faults.raised("upload", sent.status_code, sent.text[: faults.KEPT])
	return press.call(
		"press.api.site.uploaded_backup_info",
		file=name,
		path=(signed.get("fields") or {}).get("key"),
		type="application/x-gzip" if name.endswith(".gz") else "application/x-tar",
		size=part["size"],
	)
