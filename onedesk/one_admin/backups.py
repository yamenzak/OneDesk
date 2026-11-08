"""Backups, in the locked bucket, through the keeper: each workspace pushes
its own every night, signed with the secret given it here (`ready`, and
one/backup.py on its side); OneAdmin backs itself up and copies every
workspace's files; archiving keeps the newest backup again; and a kept
backup is sent back to Frappe Cloud for a restore (README, Backups)."""

import os
import secrets

import frappe
import requests
from frappe.utils import now_datetime, today

from onedesk.one_admin import cloudflare, faults, keys, press, vault

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


def given(slug: str) -> dict:
	"""A workspace's backup secret, new: written where the keeper reads it
	(`backup:<slug>` in the routing store), and the config the workspace
	needs to sign its uploads with it."""
	secret = secrets.token_urlsafe(32)
	cloudflare._call("PUT", f"values/backup:{slug}", data=frappe.as_json({"secret": secret}))
	url = (frappe.db.get_single_value("One Admin Settings", "keeper_url") or "").rstrip("/")
	return {"one_backup_secret": secret, "one_keeper_url": url}


def ready(tenant) -> bool:
	"""A workspace on Frappe Cloud given its backup secret, once."""
	if tenant.backup_ready or not (tenant.site and tenant.bench):
		return bool(tenant.backup_ready)
	config = given(tenant.slug)
	press.call(
		"press.api.site.update_config",
		name=tenant.site,
		config=frappe.as_json([{"key": key_, "value": value, "type": "Password" if key_.endswith("secret") else "String"} for key_, value in config.items()]),
	)
	tenant.db_set("backup_ready", 1)
	return True


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
	"""One workspace: given its backup secret if it has none yet (it pushes
	its own backup), and its files copied."""
	held = frappe.get_doc("Tenant", name)
	if held.is_house:
		return {"skipped": True}
	ready(held)
	files = _copy_files(held)
	held.db_set("last_backup", now_datetime(), update_modified=False)
	return {"files": files}


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
	for name in frappe.get_all("Tenant", filters={"status": ["in", BACKED_UP], "is_house": 0, "site": ["is", "set"]}, pluck="name"):
		frappe.enqueue("onedesk.one_admin.backups.tenant", queue="long", timeout=PATIENCE * 2, name=name, job_id=f"one_backup_{name}", deduplicate=True)


def archived(tenant) -> list[str]:
	"""A workspace being archived: its newest backup kept again under
	`archived/`, which no lifecycle rule expires, and its files once more.
	A workspace with no backup kept is refused: nothing is archived that
	could not be rebuilt."""
	kept = [one for one in listed(tenant.slug) if one["where"] == "daily" and "database" in one["parts"]]
	if not kept:
		raise faults.Again(f"no backup of {tenant.slug} is kept yet")
	said = _post("/again", {"slug": tenant.slug, "day": kept[0]["day"], "into": "archived"})
	_copy_files(tenant)
	return said.get("kept") or []


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


class Streamed:
	"""A body requests sends with its length rather than chunked: read as
	asked, from the opening, the file's chunks and the closing."""

	def __init__(self, pieces, length: int):
		self.pieces, self.length, self.held = iter(pieces), length, b""

	def __len__(self) -> int:
		return self.length

	def read(self, size: int = -1) -> bytes:
		while size < 0 or len(self.held) < size:
			piece = next(self.pieces, None)
			if piece is None:
				break
			self.held += piece
		if size < 0:
			out, self.held = self.held, b""
		else:
			out, self.held = self.held[:size], self.held[size:]
		return out


def form(fields: dict, name: str, size: int, chunks) -> tuple[int, str, Streamed]:
	"""A multipart form of `fields` and one file, streamed: its length, its
	content type and its body, the file's bytes read as they come. S3's
	signed POST takes a length and no chunked upload. Pure but for `chunks`."""
	boundary = f"one-{os.urandom(12).hex()}"
	head = "".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items())
	head += f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'
	opening, closing = head.encode(), f"\r\n--{boundary}--\r\n".encode()
	length = len(opening) + size + len(closing)

	def pieces():
		yield opening
		yield from chunks
		yield closing

	return length, f"multipart/form-data; boundary={boundary}", Streamed(pieces(), length)


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
