"""One lease per File: who has it open to change, and how (a workbook or
document leases the File it sits behind). `live`: anybody in OneWorkbook or
OneWriter, kept while their editor says so each minute. `alone`: one holder,
a OneOS session or a lock on the drive, kept on the File itself. Alone is
refused while anybody may write live; while it is held, the editors read.
README, Under the hood, One lease per file."""

import time

import frappe
from frappe import _
from frappe.utils import add_to_date, get_datetime, get_fullname, now_datetime

LIVE_SECONDS = 2 * 60
ONEOS, DAV = "oneos", "dav"
KINDS = (ONEOS, DAV)
FIELDS = ("one_lease_kind", "one_lease_lock", "one_lease_session", "one_lease_user", "one_lease_until")
APPS = {"workbook": "OneWorkbook", "document": "OneWriter"}
WHERE = {ONEOS: "OneOS"}


def lapsed(until, now) -> bool:
	"""Whether an alone lease has run out. Pure."""
	return not until or get_datetime(until) <= now


def holding(alone: dict | None, now) -> bool:
	"""Whether somebody holds the file alone. Pure."""
	return bool(alone and alone.get("one_lease_user") and not lapsed(alone.get("one_lease_until"), now))


def present(seen: dict, now: float) -> dict:
	"""Who is live, by user, from each editor's last word ({"user|sid":
	{"seen", "write", "app"}}): a person is live while any of their editors
	spoke in the last two minutes, and writes if any of them may. Pure."""
	out = {}
	for key, one in (seen or {}).items():
		if not one or now - float(one.get("seen") or 0) >= LIVE_SECONDS:
			continue
		user = (key.decode() if isinstance(key, bytes) else key).split("|", 1)[0]
		was = out.get(user)
		out[user] = {
			"write": bool(one.get("write")) or bool(was and was["write"]),
			"app": (was or {}).get("app") or one.get("app"),
		}
	return out


def refused(alone: dict | None, live: dict, user: str, kind: str, now) -> dict | None:
	"""Why `user` may not have the file alone for `kind`: somebody else
	already does, they themselves do another way, or somebody may write in it
	live. None when they may. Pure."""
	if holding(alone, now) and (alone["one_lease_user"] != user or alone.get("one_lease_kind") != kind):
		return {"user": alone["one_lease_user"], "kind": alone.get("one_lease_kind")}
	writing = sorted(live.items(), key=lambda one: one[0] == user)
	for who, one in writing:
		if one.get("write"):
			return {"user": who, "app": one.get("app")}
	return None


def reading(alone: dict | None, user: str, now) -> dict | None:
	"""What a native editor is told while the file is held alone: who holds
	it and how. None when it is not. Pure."""
	if not holding(alone, now):
		return None
	return {"user": alone["one_lease_user"], "kind": alone.get("one_lease_kind"), "mine": alone["one_lease_user"] == user}


def holders(alone: dict | None, live: dict, now) -> list[str]:
	"""Everybody who has the file open to change or to read: who holds it
	alone, then who is in it live. Pure."""
	found = [alone["one_lease_user"]] if holding(alone, now) else []
	return found + [user for user in sorted(live) if user not in found]


def _live_key(file: str) -> str:
	return f"onecloud_live:{file}"


def alone_of(file: str, for_update: bool = False) -> dict | None:
	return frappe.db.get_value("File", file, list(FIELDS), as_dict=True, for_update=for_update)


def live_of(file: str) -> dict:
	"""Who is live in the file now, by user."""
	try:
		seen = frappe.cache.hgetall(_live_key(file)) or {}
	except Exception:
		seen = {}
	return present(seen, time.time())


def arrive(file: str, sid: str, write: bool, app: str) -> None:
	"""The reader's editor is in the file, and says so again every minute."""
	if not file or not sid or frappe.session.user == "Guest":
		return
	key = _live_key(file)
	frappe.cache.hset(key, f"{frappe.session.user}|{sid}", {"seen": time.time(), "write": bool(write), "app": app})
	frappe.cache.expire_key(key, LIVE_SECONDS * 2)


def leave(file: str, sid: str) -> None:
	"""The reader's editor left the file."""
	if file and sid:
		frappe.cache.hdel(_live_key(file), f"{frappe.session.user}|{sid}")


def take(file: str, kind: str, user: str, seconds: int, lock: str | None = None) -> dict:
	"""The file alone for `user`: a new lock (`lock`, when the drive's lock
	token is to be the lease's), their own still running (with its session,
	to open again), or `held` saying who has it instead."""
	now = now_datetime()
	alone = alone_of(file, for_update=True)
	why = refused(alone, live_of(file), user, kind, now)
	if why:
		return {"held": said(why, user)}
	if holding(alone, now) and alone.one_lease_session:
		extend(file, alone.one_lease_lock, seconds)
		return {"lock": alone.one_lease_lock, "session": alone.one_lease_session}
	lock = lock or frappe.generate_hash(length=20)
	frappe.db.set_value(
		"File",
		file,
		{
			"one_lease_kind": kind,
			"one_lease_lock": lock,
			"one_lease_session": None,
			"one_lease_user": user,
			"one_lease_until": add_to_date(now, seconds=seconds),
		},
		update_modified=False,
	)
	return {"lock": lock}


def said(why: dict, user: str) -> dict:
	"""A refusal as the person asking reads it: who, and where."""
	return {
		"by": None if why["user"] == user else get_fullname(why["user"]),
		"mine": why["user"] == user,
		"where": WHERE.get(why.get("kind")) or APPS.get(why.get("app")) or _("the drive"),
		"readonly": False,
	}


def extend(file: str, lock: str | None, seconds: int) -> None:
	if lock and frappe.db.get_value("File", file, "one_lease_lock") == lock:
		frappe.db.set_value("File", file, "one_lease_until", add_to_date(now_datetime(), seconds=seconds), update_modified=False)


def in_it(file: str) -> list[str]:
	"""`holders` of a File by name."""
	return holders(alone_of(file), live_of(file), now_datetime())


def by_lock(lock: str | None) -> str | None:
	"""The File whose alone lease is `lock`."""
	return frappe.db.get_value("File", {"one_lease_lock": lock}, "name") if lock else None


def started(file: str, session: str) -> None:
	frappe.db.set_value("File", file, "one_lease_session", session, update_modified=False)


def release(file: str, lock: str | None = None) -> None:
	"""The alone lease let go, if it is still the one named."""
	if lock and frappe.db.get_value("File", file, "one_lease_lock") != lock:
		return
	frappe.db.set_value("File", file, dict.fromkeys(FIELDS), update_modified=False)


def held_alone(item: dict, user: str | None = None, now=None) -> dict | None:
	"""Who holds a File alone, from its row, as an editor or a listing tells
	the reader: their name, how, and whether it is the reader."""
	found = reading(item, user or frappe.session.user, now or now_datetime())
	if not found:
		return None
	return {"by": get_fullname(found["user"]), "kind": found["kind"], "mine": found["mine"]}


def blocking(file: str) -> dict | None:
	"""`held_alone` for a File by name."""
	alone = alone_of(file)
	return held_alone(alone) if alone else None


def told(held: dict) -> str:
	"""The line a native editor shows while the file is held alone."""
	if held["kind"] == ONEOS:
		return _("You are editing this in OneOS.") if held["mine"] else _("{0} is editing this in OneOS.").format(held["by"])
	return _("You are editing this on the drive.") if held["mine"] else _("{0} is editing this on the drive.").format(held["by"])


def sitting(file: str, path: str) -> str:
	"""Which sitting a save belongs to: the reader's alone lock while they
	hold one, else how it came in (the editor, OneOS, the drive)."""
	alone = alone_of(file)
	if holding(alone, now_datetime()) and alone.one_lease_user == frappe.session.user:
		return alone.one_lease_lock
	return path


def file_of(target: str) -> str | None:
	"""The File a target names: a File, or a workbook or document by name."""
	if frappe.db.exists("File", target):
		return target
	for doctype in ("Workbook", "Writer Document"):
		found = frappe.db.get_value(doctype, target, "file")
		if found:
			return found
	return None


@frappe.whitelist()
@frappe.read_only()
def of(target: str) -> dict:
	"""The lease on a File, workbook or document, for whoever may open it:
	who has it alone and how, and who is in it live."""
	from onedesk.one_storage import namespace as ns

	file = file_of(target)
	item = ns.row(file) if file else None
	if not item or not ns.may(item):
		frappe.throw(_("This item no longer exists."), frappe.DoesNotExistError)
	alone = held_alone(alone_of(file))
	live = live_of(file)
	return {
		"mode": "alone" if alone else "live" if live else None,
		"alone": alone,
		"live": [
			{"user": user, "name": get_fullname(user), "write": one["write"], "app": APPS.get(one.get("app"))}
			for user, one in sorted(live.items())
		],
	}
