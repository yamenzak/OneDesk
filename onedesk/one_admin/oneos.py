"""OneOS: a desktop in the browser, one container per session on Cloudflare
(deploy/oneos), opened from a workspace's file and billed to it by the
minute out of a 30-minute hold renewed every 15. Each minute's tick charges,
warns, renews or stops (AGENTS.md, Under the hood, OneOS)."""

import hashlib
import hmac
import math
import time
from dataclasses import dataclass
from datetime import datetime

import frappe
import requests
from frappe import _
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one_admin import ledger, price_list, site, vault
from onedesk.one_admin.faults import Refused

DOCTYPE = "OneOS Session"
APP = "libreoffice"
SIZE = "standard-1"

CPU = 0.00002
MEMORY = 0.0000025
DISK = 0.00000007
STREAM_GB_AN_HOUR = 1.5
EGRESS_GB = 0.025

SIZES = {
	"standard-1": (0.5, 4, 8),
	"standard-2": (1, 6, 12),
	"standard-3": (2, 8, 16),
	"standard-4": (4, 12, 20),
}

HOLD_MINUTES = 30
RENEW_MINUTES = 15
WARN_IDLE = 10 * 60
STOP_IDLE = 15 * 60
LONGEST = 8 * 60 * 60
MISSES = 2
WAIT = 30

STARTING, RUNNING, STOPPED = "Starting", "Running", "Stopped"
LIVE = (STARTING, RUNNING)

CLOSED = "Closed"
IDLE = "Idle"
TIME_LIMIT = "Time Limit"
NO_CREDITS = "No Credits"
NOT_ANSWERING = "Not Answering"
NOT_STARTED = "Not Started"
ENDED = "Ended"
OPERATOR = "Stopped by Operator"


def cost_a_minute(size: str = SIZE) -> float:
	"""What a minute of a session costs us, in dollars. Pure."""
	cpu, memory, disk = SIZES[size]
	return 60 * (cpu * CPU + memory * MEMORY + disk * DISK) + STREAM_GB_AN_HOUR * EGRESS_GB / 60


def credits_a_minute(size: str, markup: float, per_dollar: float) -> float:
	"""What a minute of a session is charged, in OneCredits, unrounded. Pure."""
	return round(cost_a_minute(size) * (markup or 1) * (per_dollar or 0), 6)


def hold_for(size: str, markup: float, per_dollar: float) -> float:
	"""The credits a session holds ahead of itself. Pure."""
	return round(credits_a_minute(size, markup, per_dollar) * HOLD_MINUTES, 6)


def rates(markup: float | None = None, per_dollar: float | None = None) -> list[dict]:
	"""Each size's minute, what it costs us and what it is charged, for the
	price list. Pure."""
	markup = price_list.MARKUP["oneos"] if markup is None else markup
	per_dollar = price_list.credits_per_dollar() if per_dollar is None else per_dollar
	return [
		{
			"size": size,
			"usd_a_minute": round(cost_a_minute(size), 6),
			"credits_a_minute": credits_a_minute(size, markup, per_dollar),
			"credits_an_hour": round(credits_a_minute(size, markup, per_dollar) * 60, 2),
		}
		for size in SIZES
	]


def on_trial(status: str, trial_days: int, since, today) -> bool:
	"""Whether a workspace is still in its plan's free days. Pure."""
	from frappe.utils import add_days, getdate

	return status == "Live" and bool(trial_days) and bool(since) and add_days(getdate(since), trial_days) >= getdate(today)


def _trying(tenant) -> bool:
	from frappe.utils import today

	days = frappe.db.get_value("Offering", tenant.offering, "trial_days") if tenant.get("offering") else 0
	return on_trial(tenant.status, days, tenant.get("live_on") or tenant.get("creation"), today())


def offered(tenant) -> dict:
	"""Whether a workspace is offered OneOS, and what an hour of it costs at
	the size it opens: never while OneOS is not set up here, nor during a
	trial."""
	url = frappe.get_cached_doc("One Admin Settings").get("oneos_url")
	hour = next((one["credits_an_hour"] for one in rates() if one["size"] == SIZE), 0)
	return {"on": bool(url) and not _trying(tenant), "credits_an_hour": hour}


def owed(started: datetime, upto: datetime, billed: int, whole: bool = False) -> int:
	"""The minutes run since `started` not billed yet: whole minutes while it
	runs, and the minute begun once it stops. Pure."""
	seconds = max(0.0, (upto - started).total_seconds())
	ran = math.ceil(seconds / 60) if whole else math.floor(seconds / 60)
	return max(0, ran - (billed or 0))


@dataclass(frozen=True)
class Step:
	"""What one tick does to a session: the state it is left in, the minutes
	to charge, whether the hold is renewed, why it stops if it does, the
	failed reads in a row and whether the person is warned."""

	state: str
	minutes: int
	renew: bool
	stop: str | None
	misses: int
	warn: bool
	idle: int


def step(
	state: str,
	started: datetime,
	held_at: datetime,
	billed: int,
	misses: int,
	read: dict | None,
	now: datetime,
	last_seen: datetime | None = None,
) -> Step:
	"""One tick of a session, given what the Worker said (None when it did
	not answer). Pure."""
	if read is None:
		misses = (misses or 0) + 1
		if misses >= MISSES:
			return Step(STOPPED, owed(started, last_seen or started, billed, whole=True), False, NOT_ANSWERING, misses, False, 0)
		return Step(state, 0, False, None, misses, False, 0)
	said = (read.get("state") or "").lower()
	idle = int(read.get("idle_seconds") or 0)
	if said == "stopped":
		return Step(STOPPED, owed(started, now, billed, whole=True), False, ENDED, 0, False, idle)
	ran = (now - started).total_seconds()
	stop = TIME_LIMIT if ran >= LONGEST else IDLE if idle >= STOP_IDLE else None
	if stop:
		return Step(STOPPED, owed(started, now, billed, whole=True), False, stop, 0, False, idle)
	renew = (now - held_at).total_seconds() >= RENEW_MINUTES * 60
	return Step(RUNNING if said == "running" else STARTING, owed(started, now, billed), renew, None, 0, idle >= WARN_IDLE, idle)


def token(secret: str, session: str, expires: int) -> str:
	"""What opens a session's desktop in a browser until `expires`, as the
	Worker checks it (deploy/oneos/guard.js). Pure."""
	signed = hmac.new(secret.encode(), f"{session}.{expires}".encode(), hashlib.sha256).hexdigest()
	return f"{expires}.{signed}"


def _where() -> tuple[str, str]:
	url = (frappe.get_cached_doc("One Admin Settings").get("oneos_url") or "").rstrip("/")
	secret = vault.get("oneos_secret") if url else None
	if not url or not secret:
		raise Refused("OneOS is not set up")
	return url, secret


def _address(url: str, secret: str, session: str, started) -> str:
	left = LONGEST - (now_datetime() - get_datetime(started)).total_seconds()
	expires = int(time.time() + max(60, left))
	return f"{url}/s/{session}/?t={token(secret, session, expires)}"


def _money() -> tuple[float, float]:
	return price_list.MARKUP["oneos"], price_list.credits_per_dollar()


def start(tenant: str, user: str, file: str, file_name: str, file_url: str, save_url: str, again: str | None = None) -> dict:
	"""A file of a workspace opened in OneOS for one person: the session and
	the address that opens it. The same person's live session on the same
	file is given a new address rather than a second session."""
	site.require_admin()
	url, secret = _where()
	if _trying(frappe.get_doc("Tenant", tenant)):
		raise Refused("on a trial")
	if again:
		held = frappe.db.get_value(DOCTYPE, again, ["tenant", "user", "file", "state", "started_at"], as_dict=True)
		if held and held.tenant == tenant and held.user == user and held.file == file and held.state in LIVE:
			return {"session": again, "url": _address(url, secret, again, held.started_at), "state": held.state}
	markup, per_dollar = _money()
	session = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"tenant": tenant,
			"user": user,
			"file": file,
			"file_name": file_name,
			"app": APP,
			"size": SIZE,
			"state": STARTING,
			"started_at": now_datetime(),
			"held_at": now_datetime(),
			"last_seen": now_datetime(),
			"ends_on": add_to_date(now_datetime(), seconds=LONGEST),
			"rate": credits_a_minute(SIZE, markup, per_dollar),
		}
	)
	session.flags.ignore_permissions = True
	session.insert()
	holding = ledger.reserve(tenant, hold_for(SIZE, markup, per_dollar), why="oneos", reference=f"OneOS {session.name}", action="oneos_start")
	session.db_set({"reservation": holding, "held": hold_for(SIZE, markup, per_dollar)}, update_modified=False)
	try:
		answered = requests.post(
			f"{url}/sessions/{session.name}",
			headers={"x-one-secret": secret},
			json={"file_url": file_url, "save_url": save_url, "name": file_name, "app": APP, "size": SIZE, "lasts_seconds": LONGEST},
			timeout=WAIT,
		)
		began = answered.ok
	except requests.RequestException:
		began = False
	if not began:
		ledger.release(holding)
		session.db_set({"state": STOPPED, "stop_reason": NOT_STARTED, "stopped_at": now_datetime(), "held": 0}, update_modified=False)
		raise Refused("OneOS did not start")
	return {"session": session.name, "url": _address(url, secret, session.name, session.started_at), "state": STARTING}


def state(tenant: str, session: str) -> dict:
	"""What a workspace is told of one of its sessions."""
	site.require_admin()
	held = frappe.db.get_value(DOCTYPE, session, ["tenant", "state", "stop_reason", "idle_seconds", "warned", "ends_on", "saved_at"], as_dict=True)
	if not held or held.tenant != tenant:
		return {"state": STOPPED, "stop_reason": None, "known": False}
	return {
		"state": held.state,
		"stop_reason": held.stop_reason if held.state == STOPPED else None,
		"warn": bool(held.warned) and held.state in LIVE,
		"idle_seconds": held.idle_seconds or 0,
		"ends_on": str(held.ends_on or ""),
		"saved_at": str(held.saved_at or ""),
		"known": True,
	}


def stop(tenant: str | None, session: str, why: str = CLOSED) -> dict:
	"""A session stopped: the Worker saves the file and ends the container,
	the minutes are charged, the hold goes and the workspace is told."""
	site.require_admin()
	doc = frappe.get_doc(DOCTYPE, session)
	if tenant and doc.tenant != tenant:
		raise Refused("this session belongs to another workspace")
	if doc.state == STOPPED:
		return state(doc.tenant, session)
	_finish(doc, why, owed(get_datetime(doc.started_at), now_datetime(), doc.minutes_billed, whole=True))
	return state(doc.tenant, session)


def tick() -> None:
	"""Every minute, on the admin site: each live session read, charged,
	renewed, warned or stopped."""
	if not site.is_admin():
		return
	for name in frappe.get_all(DOCTYPE, filters={"state": ["in", LIVE]}, pluck="name"):
		try:
			_tick(name)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"OneOS session {name}")


def _read(url: str, secret: str, session: str) -> dict | None:
	try:
		answered = requests.get(f"{url}/sessions/{session}", headers={"x-one-secret": secret}, timeout=10)
		return answered.json() if answered.ok else None
	except (requests.RequestException, ValueError):
		return None


def _tick(name: str) -> None:
	doc = frappe.get_doc(DOCTYPE, name)
	try:
		url, secret = _where()
	except Refused:
		read = None
	else:
		read = _read(url, secret, name)
	now = now_datetime()
	did = step(doc.state, get_datetime(doc.started_at), get_datetime(doc.held_at or doc.started_at), doc.minutes_billed, doc.misses, read, now, get_datetime(doc.last_seen) if doc.last_seen else None)
	seen = {"misses": did.misses, "idle_seconds": did.idle, "warned": int(did.warn)}
	if read is not None:
		seen["last_seen"] = now
		if read.get("saved_at"):
			seen["saved_at"] = _when(read["saved_at"])
	doc.db_set(seen, update_modified=False)
	if did.stop:
		_finish(doc, did.stop, did.minutes, ask_worker=did.stop not in (ENDED,))
		return
	_charge(doc, did.minutes)
	if did.state != doc.state:
		doc.db_set("state", did.state, update_modified=False)
	if did.renew and not _renew(doc):
		_finish(doc, NO_CREDITS, owed(get_datetime(doc.started_at), now, doc.minutes_billed, whole=True))


def _when(value) -> datetime | None:
	"""The Worker's UTC time ("2026-11-12T10:00:00Z") in the site's time."""
	from frappe.utils import convert_utc_to_system_timezone

	try:
		return convert_utc_to_system_timezone(get_datetime(str(value).replace("Z", "").replace("T", " ")[:19])).replace(tzinfo=None)
	except (TypeError, ValueError):
		return None


def _charge(doc, minutes: int) -> None:
	"""Minutes run, charged out of the session's hold at its rate."""
	if minutes <= 0 or not doc.reservation:
		return
	credits = round(minutes * (doc.rate or 0), 6)
	ledger.charge(doc.reservation, credits, cost_a_minute(doc.size or SIZE) * minutes, model=f"oneos/{doc.size or SIZE}")
	doc.db_set(
		{"minutes_billed": (doc.minutes_billed or 0) + minutes, "credits": round((doc.credits or 0) + credits, 6)},
		update_modified=False,
	)


def _renew(doc) -> bool:
	"""A fresh 30 minutes held in place of the old hold, or False when the
	workspace can't cover it."""
	markup, per_dollar = _money()
	amount = hold_for(doc.size or SIZE, markup, per_dollar)
	try:
		holding = ledger.renew(doc.reservation, amount, why="oneos", reference=f"OneOS {doc.name}", action="oneos_start")
	except ledger.NotEnough:
		return False
	doc.db_set({"reservation": holding, "held": amount, "held_at": now_datetime()}, update_modified=False)
	return True


def _finish(doc, why: str, minutes: int, ask_worker: bool = True) -> None:
	"""The container ended, what ran charged, the hold let go and the
	workspace told."""
	if ask_worker:
		try:
			url, secret = _where()
			answered = requests.post(f"{url}/sessions/{doc.name}/stop", headers={"x-one-secret": secret}, timeout=60)
			said = answered.json() if answered.ok else {}
			if said.get("saved_at"):
				doc.db_set("saved_at", _when(said["saved_at"]), update_modified=False)
		except (Refused, requests.RequestException, ValueError):
			pass
	if doc.reservation:
		if minutes > 0:
			_charge(doc, minutes)
		ledger.close(doc.reservation)
	doc.db_set({"state": STOPPED, "stop_reason": why, "stopped_at": now_datetime(), "held": 0, "warned": 0}, update_modified=False)
	frappe.enqueue("onedesk.one_admin.oneos.tell", tenant=doc.tenant, session=doc.name, enqueue_after_commit=True)


def tell(tenant: str, session: str) -> None:
	"""The workspace is asked to look at its session: like account.wake, it
	takes nothing on trust and asks for itself."""
	address = frappe.db.get_value("Tenant", tenant, "site")
	if not address:
		return
	try:
		requests.post(f"https://{address}/api/method/onedesk.one_storage.oneos.stopped", json={"session": session}, timeout=15)
	except requests.RequestException:
		pass


@frappe.whitelist(methods=["POST"])
def stop_session(name: str) -> dict:
	"""An operator stops a session from its record."""
	site.require_admin()
	frappe.only_for(site.OPERATOR)
	return stop(None, name, OPERATOR)


def said(raised: Exception) -> str:
	"""What a workspace is told when a session is refused."""
	if isinstance(raised, ledger.NotEnough):
		return _("The workspace doesn't have enough OneCredits to open this in OneOS.")
	if "not set up" in str(raised):
		return _("OneOS isn't available yet.")
	if "on a trial" in str(raised):
		return _("OneOS opens once the trial is over.")
	return _("OneOS could not be started. Try again in a few minutes.")

