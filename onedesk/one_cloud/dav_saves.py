"""Saves from the drive that never land over somebody else's work. Without
its app's lock, a save from a version the file no longer holds (its
If-Match, else what the person last downloaded) goes beside it as "Name
(Huda's copy).ext". Safe saves (a temporary file moved over the file, or
the file moved aside or deleted and another moved into its name) stay
saves of the same File. AGENTS.md, Under the hood, dav_saves.py."""

import hashlib
import time

import frappe
from frappe import _
from frappe.utils import get_fullname

BASE_SECONDS = 12 * 60 * 60
COPY_SECONDS = 10 * 60
GONE_SECONDS = 2 * 60


def tag(item: dict) -> str:
	"""A file's version as the drive names it, its ETag: the same while the
	content is. Pure."""
	url = hashlib.sha1((item.get("url") or "").encode()).hexdigest()[:12]
	return f"{item.get('id')}-{url}-{item.get('size') or 0}"


def matches(header: str | None, etag: str) -> bool:
	"""Whether an If-Match header names `etag` (or any, with *). Pure."""
	for one in (header or "").split(","):
		one = one.strip()
		if one.startswith("W/"):
			one = one[2:]
		if one == "*" or one.strip('"') == etag:
			return True
	return False


def stale(base: str | None, current: str, locked: bool) -> bool:
	"""Whether a save started from a version the file no longer holds: not
	while the saver holds its lock, and not when nothing says where it
	started. Pure."""
	return bool(not locked and base and base != current)


def copy_name(file_name: str, first: str, words: str) -> str:
	""""Budget (Huda's copy).xlsx" for "Budget.xlsx", in `words` ("{0}
	({1}'s copy)", translated). Pure."""
	stem, dot, suffix = file_name.rpartition(".")
	if not dot or not stem:
		stem, suffix = file_name, ""
	named = words.format(stem, first)
	return f"{named}.{suffix}" if suffix else named


def claims(gone: dict | None, user: str, now: float) -> bool:
	"""Whether a save takes a File back into a name it left moments ago:
	moved aside or deleted by the same person in the last two minutes.
	Pure."""
	return bool(gone and gone.get("file") and gone.get("by") == user and now - float(gone.get("on") or 0) < GONE_SECONDS)


TEMPORARY_ENDS = (".tmp", ".temp", ".bak", "~", ".swp", ".wbk")
TEMPORARY_STARTS = ("~", ".~", "Word Work File", "Excel Work File", "PowerPoint Work File")


def temporary(path: str) -> bool:
	"""Whether a name is where an app puts a file aside while it saves: Word's
	~WRL0001.tmp, Mac Office's Word Work File, a .sb- safe-save name, or
	anything in macOS's "(A Document Being Saved By …)" folder. Pure."""
	parts = [part for part in (path or "").split("/") if part]
	name = parts[-1] if parts else ""
	return (
		name.startswith(TEMPORARY_STARTS)
		or name.lower().endswith(TEMPORARY_ENDS)
		or ".sb-" in name
		or any(part.startswith("(A Document Being Saved By") for part in parts[:-1])
	)


def _base_key(file: str) -> str:
	return f"onecloud_dav_base:{frappe.session.user}:{file}"


def _copy_key(file: str) -> str:
	return f"onecloud_dav_copy:{frappe.session.user}:{file}"


def _gone_key(path: str) -> str:
	return f"onecloud_dav_gone:{frappe.session.user}:{path}"


def _ghost_key(path: str) -> str:
	return f"onecloud_dav_ghost:{frappe.session.user}:{path}"


def read(item: dict) -> None:
	"""The reader fetched this version from the drive."""
	frappe.cache.set_value(_base_key(item["id"]), tag(item), expires_in_sec=BASE_SECONDS)


def base(file: str) -> str | None:
	return frappe.cache.get_value(_base_key(file))


def copy_of(file: str) -> str | None:
	"""The copy this person's saves on `file` go into, if it is still there."""
	made = frappe.cache.get_value(_copy_key(file))
	return made if made and frappe.db.get_value("File", made, "one_deleted") == 0 else None


def kept_copy(file: str, made: str) -> None:
	frappe.cache.set_value(_copy_key(file), made, expires_in_sec=COPY_SECONDS)


def first_name(user: str | None = None) -> str:
	user = user or frappe.session.user
	return (get_fullname(user) or "").split(" ")[0] or user


def left(path: str, file: str, name: str, aside: str | None = None) -> None:
	"""A File left this name on the drive: moved `aside`, or deleted."""
	frappe.cache.set_value(
		_gone_key(path),
		{"file": file, "name": name, "aside": aside, "by": frappe.session.user, "on": time.time()},
		expires_in_sec=GONE_SECONDS,
	)


def taken_back(path: str) -> dict | None:
	"""The File that left `path` moments ago, for a save into it to keep."""
	gone = frappe.cache.get_value(_gone_key(path))
	if not claims(gone, frappe.session.user, time.time()) or not frappe.db.exists("File", gone["file"]):
		return None
	frappe.cache.delete_value(_gone_key(path))
	return gone


def bring_back(gone: dict) -> dict:
	"""A File that left its name for a safe save, back in it: out of the
	Recycle Bin, or renamed back from where it was put aside, whose name is
	then a ghost to delete. Its drive node."""
	from onedesk.one_cloud import api, dav
	from onedesk.one_cloud import namespace as ns

	file = gone["file"]
	if frappe.db.get_value("File", file, "one_deleted"):
		api.restore([file])
	else:
		api.rename(file, dav._stored(dav._as_file(ns.node(ns.row(file))), gone["name"]))
		if gone.get("aside"):
			ghost(gone["aside"])
	return dav._as_file(ns.node(ns.row(file)))


def save_into(target: dict, environ: dict, parent: dict, content: bytes | None = None, src: str | None = None) -> None:
	"""A save from the drive into the file `target`, of `content` or of the
	File `src` an app wrote first and moved over it. Refused 423 while
	somebody else holds the file alone; from a version it no longer holds,
	kept beside it as the saver's copy; else a new version, one per sitting."""
	from onedesk.one_cloud import api, dav, history, lease, upload
	from onedesk.one_cloud import namespace as ns

	same = target["id"]
	held = lease.blocking(same)
	if held and not (held["mine"] and held["kind"] == lease.DAV):
		raise dav._error(423)
	if dav._own(target):
		data = content if src is None else dav.read_bytes(ns.node(ns.row(src)))
		if src:
			frappe.delete_doc("File", src, ignore_permissions=True)
		from onedesk.one_cloud import saving

		with saving.through(lease.DAV):
			dav.write_own(target, data)
		return
	copied = copy_of(same)
	if copied:
		same, target = copied, ns.node(ns.row(copied))
	elif stale("?" if environ.get("onecloud.stale") else base(same), tag(target), bool(held)):
		if src is None and not content:
			return
		name = copy_name(target["name"], first_name(), _("{0} ({1}'s copy)"))
		made = api.rename(src, name)["id"] if src else upload._place(parent["id"], None, {"file_name": name, "content": content})["id"]
		kept_copy(target["id"], made)
		history.note(made, _("saved a copy, since {0} had changed after it was opened").format(target["name"]))
		read(ns.node(ns.row(made)))
		return
	sitting = lease.sitting(same, "drive")
	if src:
		api._need(ns.row(same), "write")
		history.replace(ns.row(same), src, sitting=sitting)
	else:
		upload._place(parent["id"], None, {"file_name": target["name"], "content": content}, replace=1, version_of=same, sitting=sitting)
	read(ns.node(ns.row(same)))


def ghost(path: str) -> None:
	"""The name a file was moved aside to, after it came back: deleting it
	succeeds and does nothing."""
	frappe.cache.set_value(_ghost_key(path), 1, expires_in_sec=GONE_SECONDS)


def unghost(path: str) -> None:
	frappe.cache.delete_value(_ghost_key(path))


def is_ghost(path: str) -> bool:
	return bool(frappe.cache.get_value(_ghost_key(path)))
