"""Backups, in the locked bucket, through the keeper: each workspace pushes
its own every night, and its database every four hours under `recent/`,
signed with the secret given it here (`ready`, and
one/backup.py on its side); OneAdmin backs itself up and copies every
workspace's files; archiving keeps the newest backup again; and a kept
backup is sent back to Frappe Cloud for a restore (README, Backups)."""

import os
import secrets

import frappe
import requests
from frappe.utils import now_datetime, today

from onedesk.one_admin import cloudflare, faults, keys, pilot, seal, vault

BACKED_UP = ("Live", "Overdue", "Suspended")
OURS = "oneadmin"
CONFIG_COPIES = "config/oneadmin"
RECENT = "recent"
FILE_PARTS = ("public", "private")
ROUNDS = 100
PATIENCE = 900
PIECE = 64 * 1024 * 1024


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
	"""A workspace on a server given its backup secret, once."""
	if tenant.backup_ready or not (tenant.site and tenant.server):
		return bool(tenant.backup_ready)
	pilot.on(tenant, "PATCH", f"/sites/{tenant.site}/configuration", json=given(tenant.slug))
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


def config_copy() -> dict:
	"""OneAdmin's own site config, every key and every server's login, sealed
	to the rescue passphrase (seal.py) and kept under `config/`. This server
	holds only the public half, so it can write the copy and never read it."""
	public = (frappe.db.get_single_value("One Admin Settings", "config_copy_key") or "").strip()
	if not public:
		raise faults.Refused("there is no Config Copy Key; run scripts/rescue.py key")
	with open(frappe.get_site_path("site_config.json"), "rb") as held:
		body = seal.sealed(held.read(), public)
	url, headers = _keeper()
	answered = requests.put(f"{url}/backup/{CONFIG_COPIES}/{today()}.one", data=body, headers=headers, timeout=PATIENCE)
	if not answered.ok:
		raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
	return {"kept": answered.json().get("kept")}


def nightly() -> None:
	"""Scheduled daily: OneAdmin's own backup and sealed config, and a job
	for each workspace still running."""
	from onedesk.one_admin import site

	if not site.is_admin():
		return
	frappe.enqueue("onedesk.one_admin.backups.ours", queue="long", timeout=PATIENCE)
	frappe.enqueue("onedesk.one_admin.backups.config_copy", queue="long", timeout=PATIENCE)
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


def when(where: str, day: str, uploaded: str | None) -> str:
	"""What kept backups are put in order by. A four-hourly one says its time
	in its name (`2026-11-09T0415`) and a nightly one by when it arrived;
	`monthly/` and `archived/` were copied later, so only their day means
	anything. Pure."""
	if where == RECENT:
		return f"{day[:13]}:{day[13:]}"
	return (uploaded or day) if where == "daily" else day


def listed(slug: str) -> list[dict]:
	"""Every backup kept of a workspace, newest first: its day (and for a
	four-hourly one its time), where it is kept, and its parts."""
	url, headers = _keeper()
	days: dict[tuple, dict] = {}
	for where in ("archived", "monthly", "daily", RECENT):
		cursor = None
		while True:
			answered = requests.get(f"{url}/backups", params={"prefix": f"{where}/{slug}/", "cursor": cursor or ""}, headers=headers, timeout=60)
			if not answered.ok:
				raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
			said = answered.json()
			for one in said.get("objects") or []:
				_where, _slug, day, part, _name = one["key"].split("/", 4)
				held = days.setdefault((day, where), {"day": day, "where": where, "parts": {}, "at": when(where, day, one.get("uploaded"))})
				held["parts"][part] = {"key": one["key"], "size": one["size"]}
			cursor = said.get("cursor")
			if not cursor:
				break
	return sorted(days.values(), key=lambda one: (one["at"], one["where"] == "archived"), reverse=True)


def kept_on(slug: str, day: str) -> bool:
	"""Whether a workspace's daily backup for this day is kept."""
	url, headers = _keeper()
	answered = requests.get(f"{url}/backups", params={"prefix": f"daily/{slug}/{day}/"}, headers=headers, timeout=60)
	if not answered.ok:
		raise faults.raised("keeper", answered.status_code, answered.text[: faults.KEPT])
	return bool(answered.json().get("objects"))


def chosen(slug: str, day: str, where: str, new_site: bool = False) -> dict:
	"""One kept backup of a workspace: its parts, as `listed` gives them. A
	four-hourly one has no files, so one going onto a new site takes them
	from the newest night up to it; a site rolled back keeps its own."""
	kept = listed(slug)
	found = next((one for one in kept if one["day"] == day and one["where"] == where), None)
	if not found or "database" not in found["parts"]:
		raise faults.Refused(f"no backup of {slug} kept for {where} {day}")
	if new_site and where == RECENT:
		night = next((one for one in kept if one["where"] != RECENT and one["day"] <= day and set(one["parts"]) & set(FILE_PARTS)), None)
		found["parts"].update({part: held for part, held in (night["parts"] if night else {}).items() if part in FILE_PARTS})
	return found


def to_server(tenant, parts: dict) -> tuple[str, list[str]]:
	"""A kept backup sent to a server's Pilot for a restore, streamed from the
	keeper in pieces a request can carry: the upload's id and the parts."""
	wanted = {name: kept for name, kept in parts.items() if name in ("database", "public", "private")}
	files = {name: {"filename": os.path.basename(kept["key"]), "size": kept["size"]} for name, kept in wanted.items()}
	started = pilot.on(tenant, "POST", f"/sites/{tenant.site}/uploads", json={"files": files}) or {}
	upload = started.get("upload_id")
	if not upload:
		raise faults.Again(f"{tenant.server} gave no upload")
	url, headers = _keeper()
	for name, kept in wanted.items():
		with requests.get(f"{url}/backup/{kept['key']}", headers=headers, stream=True, timeout=PATIENCE) as held:
			if not held.ok:
				raise faults.raised("keeper", held.status_code, held.text[: faults.KEPT])
			offset = 0
			for piece in held.iter_content(PIECE):
				pilot.on(tenant, "PUT", f"/sites/{tenant.site}/uploads/{upload}/files/{name}?offset={offset}", data=piece)
				offset += len(piece)
	return upload, list(wanted)
