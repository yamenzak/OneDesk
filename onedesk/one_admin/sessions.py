"""Sessions on a server we connected: a site started fresh, from the demo
company or from a copy of a workspace's database, with its own address, and
deleted by itself when its time is up. README, Sessions and copies.
"""

import secrets

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one_admin import backups, cloudflare, faults, features, fleet, hosts, pilot, servers, site, steps
from onedesk.one_admin.site import OPERATOR

DOCTYPE = "Workspace Session"
FRESH = "Fresh"
DEMO = "Demo Data"
COPY = "Workspace Copy"
LASTS = {"8 Hours": 8, "1 Day": 24, "7 Days": 168, "30 Days": 720}
LIVE = ("Starting", "Running", "Stopped", "Deleting", "Failed")
ON_THE_SERVER = ("Starting", "Running", "Stopped", "Deleting")
LAST_STEP = "route"
WAIT = "wait"

ADVANCE_TIMEOUT = 3600
COPIES = "training_copies"
AGREED_WITHIN_HOURS = 3
LAPSED_AFTER_HOURS = 48


WALKS = {
	FRESH: ("create", "created", "configure", LAST_STEP),
	DEMO: ("create", "created", "configure", "demo", "agent_done", LAST_STEP),
	COPY: ("create", "created", "copy", "restore", "restored", "configure", "quiet", "agent_done", LAST_STEP),
}


def after(source: str, step: str) -> str | None:
	"""The step that follows this one. Pure."""
	walk = WALKS[source]
	at = walk.index(step) + 1
	return walk[at] if at < len(walk) else None


def expires_on(start, lasts: str):
	"""When a session started now ends. Pure."""
	return add_to_date(start, hours=LASTS[lasts])


def config_for(source: str, link: str) -> dict:
	"""What a site is told: a copy's mail and jobs stay off, and only a demo
	may build the demo company. Pure."""
	config = {"hostname": link, "mute_emails": 1, "pause_scheduler": 1 if source == COPY else 0}
	if source == DEMO:
		config["one_dev"] = 1
	return config


def agreed(agreed_on, now, within_hours: int = AGREED_WITHIN_HOURS) -> bool:
	"""Whether a workspace said it has Training Copies on recently enough.
	Pure."""
	return bool(agreed_on) and get_datetime(agreed_on) >= add_to_date(now, hours=-within_hours)


def why_not_copied(held, agreed_on, now, within_hours: int = AGREED_WITHIN_HOURS) -> str | None:
	"""Why a workspace may not be copied: its plan has no Training Copies
	(`plan`), or it has not said lately that they are on and agreed to
	(`agreed`). None when it may. Pure."""
	if COPIES not in held:
		return "plan"
	if not agreed(agreed_on, now, within_hours):
		return "agreed"
	return None


def _server():
	"""The connected server with the fewest sessions on it that has room."""
	rows = [one for one in fleet.rows() if one.connected and one.status == "Up"]
	counts = {one.server: frappe.db.count(DOCTYPE, {"server": one.server, "status": ["in", ON_THE_SERVER]}) for one in rows}
	room = [one for one in rows if not one.capacity or counts[one.server] < one.capacity]
	if not rows:
		frappe.throw(frappe._("No server is connected yet. Connect one under Servers."))
	if not room:
		frappe.throw(frappe._("Every connected server is full. Delete a session first."))
	return min(room, key=lambda one: counts[one.server])


def _allowed_workspaces() -> list[dict]:
	"""Workspaces with Training Copies on, that a copy may be started from."""
	since = add_to_date(now_datetime(), hours=-AGREED_WITHIN_HOURS)
	return frappe.get_all(
		"Tenant",
		filters={"copies_agreed_on": [">=", since], "site": ["is", "set"], "name": ["in", features.tenants_with(COPIES) or [""]]},
		fields=["name", "workspace_name"],
		order_by="workspace_name asc",
	)


def _may() -> None:
	site.require_admin()
	frappe.only_for(OPERATOR)


def _rows() -> list[dict]:
	fields = ["name", "title", "status", "source", "tenant", "link", "expires_on", "error", "step", "creation"]
	rows = frappe.get_all(DOCTYPE, filters={"status": ["!=", "Deleted"]}, fields=fields, order_by="creation desc")
	now = now_datetime()
	for row in rows:
		row["expires_in_hours"] = max(0, int((get_datetime(row.expires_on) - now).total_seconds() // 3600))
	return rows


@frappe.whitelist()
def board() -> dict:
	"""Everything the Sessions screen shows."""
	_may()
	return {
		"sessions": _rows(),
		"workspaces": _allowed_workspaces(),
		"can_start": any(one.connected and one.status == "Up" for one in fleet.rows()),
		"lasts": list(LASTS),
	}


@frappe.whitelist(methods=["POST"])
def start(title: str, source: str, lasts: str, tenant: str | None = None) -> str:
	"""A new session, started in the background. A copy needs a workspace
	whose plan includes Training Copies and that has them on."""
	_may()
	if source not in WALKS or lasts not in LASTS:
		frappe.throw(frappe._("Choose where the session starts from and how long it lasts."))
	if source == COPY:
		if not tenant or not frappe.db.exists("Tenant", tenant):
			frappe.throw(frappe._("Choose a workspace to copy."))
		why = why_not_copied(features.of_tenant(tenant), frappe.db.get_value("Tenant", tenant, "copies_agreed_on"), now_datetime())
		if why == "plan":
			frappe.throw(frappe._("{0}'s plan doesn't include Training Copies.").format(tenant))
		if why:
			frappe.throw(frappe._("{0} has not turned on Training Copies.").format(tenant))
	row = _server()
	slug = f"s-{secrets.token_hex(4)}"
	domain = frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"
	name = hosts.under(slug, domain)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"title": (title or "").strip() or slug,
			"status": "Starting",
			"source": source,
			"tenant": tenant if source == COPY else None,
			"lasts": lasts,
			"expires_on": expires_on(now_datetime(), lasts),
			"server": row.server,
			"bench": servers.current(row),
			"slug": slug,
			"site": name,
			"link": f"https://{name}",
			"step": WALKS[source][0],
		}
	).insert(ignore_permissions=True)
	_queue(doc.name)
	return doc.name


@frappe.whitelist(methods=["POST"])
def stop(name: str) -> dict:
	"""The site stops answering and its jobs pause; nothing in it is lost."""
	_may()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status != "Running":
		frappe.throw(frappe._("Only a running session can be stopped."))
	_asked(_quiet, doc, 1)
	doc.db_set("status", "Stopped", notify=True)
	return {"status": "Stopped"}


@frappe.whitelist(methods=["POST"])
def resume(name: str) -> dict:
	_may()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status != "Stopped":
		frappe.throw(frappe._("Only a stopped session can be started."))
	_asked(_quiet, doc, 0)
	doc.db_set("status", "Running", notify=True)
	return {"status": "Running"}


def _asked(fn, *args):
	"""The server's trouble, told as trouble rather than a crash."""
	try:
		return fn(*args)
	except faults.Refused as refused:
		frappe.throw(str(refused))


def _quiet(doc, on: int) -> None:
	jobs_off = on or doc.source == COPY
	body = {"maintenance_mode": on, "pause_scheduler": 1 if jobs_off else 0}
	pilot.on(doc, "PATCH", f"/sites/{doc.site}/configuration", json=body)


@frappe.whitelist(methods=["POST"])
def delete(name: str) -> dict:
	_may()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status in ("Deleting", "Deleted"):
		return {"status": doc.status}
	_begin_deleting(doc)
	return {"status": "Deleting"}


def _begin_deleting(doc) -> None:
	doc.db_set({"status": "Deleting", "task": None, "error": None}, notify=True)
	_queue(doc.name)


@frappe.whitelist(methods=["POST"])
def sign_in(name: str) -> dict:
	"""A one-time sign-in to a Fresh or Demo session. A copy has none here: it
	is the workspace's own data, for the people it belongs to."""
	_may()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.source == COPY:
		return {"url": doc.link}
	said = _asked(pilot.on, doc, "POST", f"/sites/{doc.site}/login") or {}
	return {"url": said.get("url") or doc.link}


def create(doc) -> None:
	answered = pilot.on(doc, "POST", "/sites", key=f"{doc.name}:site", json={"name": doc.site, "apps": ["frappe", *steps.APPS]})
	doc.db_set("task", (answered or {}).get("task_id"))


def created(doc) -> str | None:
	if not doc.task:
		return None
	return None if pilot.task(doc.server, doc.task, bench=doc.bench) == "done" else WAIT


def configure(doc) -> None:
	pilot.on(doc, "PATCH", f"/sites/{doc.site}/configuration", json=config_for(doc.source, doc.link))


def demo(doc) -> None:
	servers.instruct(doc.server, "session-demo", session=doc.name, bench=doc.bench, site=doc.site)


def copy(doc) -> None:
	"""The workspace's newest nightly backup, its database alone, sent to the
	server and held for `restore`."""
	slug = frappe.db.get_value("Tenant", doc.tenant, "slug")
	kept = next((one for one in backups.listed(slug) if one["where"] == "daily" and "database" in one["parts"]), None)
	if not kept:
		raise faults.Refused(f"no backup of {slug} is kept yet")
	upload, _parts = backups.to_server(doc, {"database": kept["parts"]["database"]})
	doc.db_set("upload", upload)


def restore(doc) -> None:
	answered = pilot.on(doc, "POST", f"/sites/{doc.site}/actions/restore", key=f"{doc.name}:restore", json={"parts": ["database"], "upload_id": doc.upload})
	doc.db_set("task", (answered or {}).get("task_id"))


def restored(doc) -> str | None:
	return created(doc)


def quiet(doc) -> None:
	servers.instruct(doc.server, "session-quiet", session=doc.name, bench=doc.bench, site=doc.site)


def agent_done(doc) -> str:
	"""The box's agent says when it is done, through `heard`."""
	return WAIT


def route(doc) -> None:
	cloudflare.route(doc.slug, f"{doc.site} {_origin(doc.server)}")


def _origin(server: str) -> str:
	found = fleet.row_of(server)
	if not found or not found.origin_host:
		raise faults.Refused(f"Settings lists no Origin Address for {server}")
	return found.origin_host


def quieted() -> None:
	"""Run in a copy, by the box's agent: nothing it does reaches the
	workspace's own world, and mail and webhooks stay off."""
	frappe.db.delete("Webhook")
	for account in frappe.get_all("Email Account", pluck="name"):
		frappe.db.set_value("Email Account", account, {"enable_outgoing": 0, "enable_incoming": 0}, update_modified=False)
	frappe.db.commit()


def _queue(name: str) -> None:
	"""`advance` in the background, and only one at a time for a session:
	sending a backup up takes a while and must not be started twice."""
	frappe.enqueue("onedesk.one_admin.sessions.advance", queue="long", timeout=ADVANCE_TIMEOUT, job_id=f"one_session_{name}", deduplicate=True, enqueue_after_commit=True, name=name)


def advance(name: str) -> None:
	"""One step of a session, and on from there until it waits."""
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status == "Deleting":
		_deleting(doc)
		return
	if doc.status != "Starting":
		return
	for _ in range(len(WALKS[doc.source])):
		try:
			said = STEPS[doc.step](doc)
		except faults.Again:
			return
		except faults.Refused as refused:
			doc.db_set({"status": "Failed", "error": str(refused)[: faults.KEPT]}, notify=True)
			return
		if said == WAIT:
			return
		following = after(doc.source, doc.step)
		if not following:
			doc.db_set({"status": "Running", "task": None, "step": None}, notify=True)
			return
		doc.db_set("step", following)


def _deleting(doc) -> None:
	"""Asked once, and waited on: the address goes, the site with it, then the
	record says so. A session whose site was never made is simply gone."""
	try:
		if not doc.task:
			cloudflare.forget(doc.slug)
			if pilot.on(doc, "GET", f"/sites/{doc.site}") is None:
				doc.db_set({"status": "Deleted", "task": None}, notify=True)
				return
			answered = pilot.on(doc, "DELETE", f"/sites/{doc.site}?no_backup=1", key=f"{doc.name}:drop")
			doc.db_set("task", (answered or {}).get("task_id") or "done")
		if doc.task != "done" and pilot.task(doc.server, doc.task, bench=doc.bench) != "done":
			return
	except faults.Again:
		return
	except faults.Refused as refused:
		doc.db_set({"status": "Failed", "error": str(refused)[: faults.KEPT]}, notify=True)
		return
	doc.db_set({"status": "Deleted", "task": None}, notify=True)


STEPS = {"create": create, "created": created, "configure": configure, "demo": demo, "copy": copy, "restore": restore, "restored": restored, "quiet": quiet, "agent_done": agent_done, "route": route}


def heard(said: dict) -> None:
	"""The box's agent reports on a session it worked on."""
	name = said.get("session")
	if not name or not frappe.db.exists(DOCTYPE, name):
		return
	doc = frappe.get_doc(DOCTYPE, name)
	if not said.get("ok"):
		doc.db_set({"status": "Failed", "error": str(said.get("error"))[: faults.KEPT]}, notify=True)
		return
	if doc.status == "Starting" and doc.step == "agent_done":
		doc.db_set("step", after(doc.source, "agent_done"))
		_queue(doc.name)


def tick() -> None:
	"""Every two minutes, on the admin site: starting sessions move on, what
	has run its time is deleted, and a copy whose workspace turned Training
	Copies off, or whose plan no longer includes them, goes too."""
	if not site.is_admin():
		return
	now = now_datetime()
	for row in frappe.get_all(DOCTYPE, filters={"status": ["in", ("Starting", "Deleting")]}, fields=["name"]):
		_safely(_queue, row.name)
	for row in frappe.get_all(DOCTYPE, filters=[["status", "in", ("Starting", "Running", "Stopped", "Failed")], ["expires_on", "is", "set"], ["expires_on", "<=", now]], fields=["name"]):
		_safely(_expired, row.name)
	for row in frappe.get_all(DOCTYPE, filters={"status": ["in", ("Running", "Stopped")], "source": COPY}, fields=["name", "tenant"]):
		if why_not_copied(features.of_tenant(row.tenant), frappe.db.get_value("Tenant", row.tenant, "copies_agreed_on"), now, LAPSED_AFTER_HOURS):
			_safely(_expired, row.name)


def _expired(name: str) -> None:
	_begin_deleting(frappe.get_doc(DOCTYPE, name))


def _safely(fn, name: str) -> None:
	try:
		fn(name)
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title=f"Session {name}")
