"""Sessions on a server we connected: a site started fresh, from the demo
company or from a copy of a workspace's database, with its own address, and
deleted by itself when its time is up. An operator starts one on the
Sessions screen, a workspace's administrator a training copy of its own
through proxy.copies_start (`start_for`). AGENTS.md, Sessions and copies.
"""

import secrets

import frappe
from frappe.utils import add_to_date, get_datetime, now_datetime

from onedesk.one import setup_answers
from onedesk.one.registry import fields
from onedesk.one_admin import answers, backups, boxes, cloudflare, faults, features, fleet, hosts, pilot, servers, site, steps
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
READY = "ready_demo"
READY_KIND = "session-ready-demo"

ADVANCE_TIMEOUT = 3600
COPIES = "training_copies"
AGREED_WITHIN_HOURS = 3
LAPSED_AFTER_HOURS = 48

KINDS = {"fresh": FRESH, "demo": DEMO, "data": COPY}
"""What a workspace asks for, and the session it is."""
MOST_AT_ONCE = 3
"""The training copies a workspace may have at once."""
UNCOPIED = ("people", "steps")
"""What a fresh copy leaves out of the workspace's answers: nobody is
invited to it, and an app's steps can reach outside (a mail domain), which
a copy never does."""
SET_UP = "session-setup"


WALKS = {
	FRESH: ("create", "created", "configure", LAST_STEP),
	DEMO: ("create", "created", "configure", "demo", "agent_done", LAST_STEP),
	COPY: ("create", "created", "copy", "restore", "restored", "configure", "quiet", "agent_done", LAST_STEP),
}


READY_WALK = (READY, "agent_done", "configure", LAST_STEP)

OWN_WALK = ("create", "created", "configure", "set_up", "agent_done", LAST_STEP)


def walk_of(source: str, ready: bool = False, own: bool = False) -> tuple:
	"""A session's steps: a demo restored from its release's ready demo has
	no site to create and no demo to build, and a fresh copy a workspace
	asked for is set up from its own answers. Pure."""
	if source == DEMO and ready:
		return READY_WALK
	if source == FRESH and own:
		return OWN_WALK
	return WALKS[source]


def after(source: str, step: str, ready: bool = False, own: bool = False) -> str | None:
	"""The step that follows this one. Pure."""
	walk = walk_of(source, ready, own)
	at = walk.index(step) + 1
	return walk[at] if at < len(walk) else None


def ready_release(release: str | None, about: dict | None) -> str | None:
	"""The release whose ready demo a session from the demo restores, or None
	when the demo must be built: the bench names no release, or its release
	carries no demo. Pure."""
	return release if release and (about or {}).get("demo") else None


def _ready(row, bench: str) -> tuple[str | None, str]:
	"""The release a demo session restores from, if any, and what its
	timeline says about it."""
	release = next((one.get("release") for one in servers.benches(row) if one.get("bench") == bench), None)
	about = None
	if release:
		try:
			about = boxes.release_of(servers._keys(), release)
		except Exception:
			frappe.log_error(title=f"Reading release {release} for a demo session")
	if ready_release(release, about):
		return release, frappe._("Made from the ready demo of release {0}, so it starts in about a minute.").format(release[:8])
	if about is not None:
		return None, frappe._("Release {0} has no ready demo, so the demo is built on this copy. That takes a while.").format(release[:8])
	return None, frappe._("The server could not say which release it runs, so the demo is built on this copy. That takes a while.")


def expires_on(start, lasts: str):
	"""When a session started now ends. Pure."""
	return add_to_date(start, hours=LASTS[lasts])


def config_for(source: str, link: str, ends=None, company: str | None = None) -> dict:
	"""What a site is told: a copy's mail and jobs stay off, only a demo may
	build the demo company, every session says when it ends, which the
	frame's band shows (one/dev.py, kind), and a demo copy asked for a field
	names the company it opens on (one/copies.py, open_on). Pure."""
	config = {"hostname": link, "mute_emails": 1, "pause_scheduler": 1 if source == COPY else 0}
	if ends:
		config["one_copy_ends"] = str(ends)
	if source == DEMO:
		config["one_dev"] = 1
		if company:
			config["one_copy_company"] = company
	return config


def opens_on(source: str, field: str | None) -> str | None:
	"""The demo company a copy from the demo opens on: its field's
	(registry/fields.py, demo), or the demo's own default when no field was
	chosen. Pure."""
	return fields.demo(field) if source == DEMO and field else None


def fresh_answers(held: dict | None, email: str | None) -> dict | None:
	"""A fresh copy's setup answers: the workspace's own, without its people
	or its apps' steps (UNCOPIED), owned by the administrator who asked and
	inviting nobody, since nothing in a copy sends mail. None when the
	workspace's answers are not kept or would not set a site up. Pure."""
	if not held or not email:
		return None
	kept = {key: value for key, value in held.items() if key not in UNCOPIED}
	kept["owner"] = {"email": email.strip().lower(), "first_name": email.split("@", 1)[0], "invite": False}
	try:
		return setup_answers.check(kept)
	except setup_answers.Invalid:
		return None


def why_not_started(kind: str, lasts: str, field: str | None, held, agreed_on, now, live: int) -> str | None:
	"""Why a workspace's administrator may not start this copy: an unknown
	kind or length (`asked`), a field that is not one (`field`), a plan
	without Training Copies (`plan`), Training Copies not on (`agreed`), or
	MOST_AT_ONCE copies already (`many`). None when it may. Pure."""
	if kind not in KINDS or lasts not in LASTS:
		return "asked"
	if kind == "demo" and field and field not in fields.IDS:
		return "field"
	why = why_not_copied(held, agreed_on, now)
	if why:
		return why
	return "many" if live >= MOST_AT_ONCE else None


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


def _roomy():
	"""The connected server with the fewest sessions on it that has room,
	or None and why (`none`, `full`)."""
	rows = [one for one in fleet.rows() if one.connected and one.status == "Up"]
	counts = {one.server: frappe.db.count(DOCTYPE, {"server": one.server, "status": ["in", ON_THE_SERVER]}) for one in rows}
	room = [one for one in rows if not one.capacity or counts[one.server] < one.capacity]
	if not rows:
		return None, "none"
	if not room:
		return None, "full"
	return min(room, key=lambda one: counts[one.server]), None


def _server():
	row, why = _roomy()
	if why == "none":
		frappe.throw(frappe._("No server is connected yet. Connect one under Servers."))
	if why:
		frappe.throw(frappe._("Every connected server is full. Delete a session first."))
	return row


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
	return _begin(_server(), title, source, lasts, tenant if source == COPY else None).name


def _begin(row, title: str | None, source: str, lasts: str, tenant: str | None, field: str | None = None, by: str | None = None):
	"""The session's record, on this server, and its first step queued."""
	bench = servers.current(row)
	release, said = _ready(row, bench) if source == DEMO else (None, None)
	slug = f"s-{secrets.token_hex(4)}"
	domain = frappe.get_cached_value("One Admin Settings", None, "tenant_domain") or "t.4dl.app"
	name = hosts.under(slug, domain)
	doc = frappe.get_doc(
		{
			"doctype": DOCTYPE,
			"title": (title or "").strip() or slug,
			"status": "Starting",
			"source": source,
			"tenant": tenant,
			"field": field if source == DEMO else None,
			"started_by": by,
			"lasts": lasts,
			"expires_on": expires_on(now_datetime(), lasts),
			"server": row.server,
			"bench": bench,
			"slug": slug,
			"site": name,
			"link": f"https://{name}",
			"upload": release,
			"step": walk_of(source, bool(release), bool(tenant and by))[0],
		}
	).insert(ignore_permissions=True)
	if said:
		doc.add_comment("Info", said)
	_queue(doc.name)
	return doc


def _live_of(tenant: str) -> int:
	return frappe.db.count(DOCTYPE, {"tenant": tenant, "status": ["in", ON_THE_SERVER]})


def start_for(tenant, kind: str, lasts: str, field: str | None, by: str) -> dict:
	"""A training copy a workspace's administrator asked for, through
	proxy.copies_start. Refused unless the plan has Training Copies, the
	workspace has them on and is under MOST_AT_ONCE; the refusal is a key
	(`refused`) the workspace says in its reader's language (one/copies.py).
	Fresh is set up from the workspace's own answers, From the demo opens
	on the field's company, From our data restores last night's backup with
	its passwords cleared (`quieted`)."""
	held = frappe.get_doc("Tenant", tenant.name)
	why = why_not_started(kind, lasts, field, features.of_tenant(held.name), held.copies_agreed_on, now_datetime(), _live_of(held.name))
	if not why and kind == "fresh" and not fresh_answers(answers.of(held), by):
		why = "answers"
	if not why and kind == "data" and not _kept_backup(held.slug):
		why = "data"
	row, full = (None, None) if why else _roomy()
	if why or full:
		return {"refused": why or "room", "most": MOST_AT_ONCE}
	doc = _begin(row, f"{held.workspace_name or held.name} · {KINDS[kind]}", KINDS[kind], lasts, held.name, field or None, by)
	return _said_of(doc.name)


def _kept_backup(slug: str) -> dict | None:
	return next((one for one in backups.listed(slug) if one["where"] == "daily" and "database" in one["parts"]), None)


WHAT_IS_SAID = ("name", "source", "status", "link", "expires_on", "field", "started_by", "creation")


def _row_of(row) -> dict:
	"""A copy as its workspace sees it: its kind as asked, never the
	server, the step or the error. Pure."""
	kind = next((key for key, source in KINDS.items() if source == row.get("source")), None)
	said = {key: row.get(key) for key in WHAT_IS_SAID if key != "source"}
	return {**said, "kind": kind, "expires_on": str(row.get("expires_on") or ""), "creation": str(row.get("creation") or "")}


def _said_of(name: str) -> dict:
	return _row_of(frappe.db.get_value(DOCTYPE, name, list(WHAT_IS_SAID), as_dict=True) or {})


def of_workspace(tenant) -> list[dict]:
	"""A workspace's copies that are not deleted yet, newest first."""
	rows = frappe.get_all(DOCTYPE, filters={"tenant": tenant.name, "status": ["!=", "Deleted"]}, fields=list(WHAT_IS_SAID), order_by="creation desc")
	return [_row_of(one) for one in rows]


def _theirs(tenant, name: str):
	"""One of this workspace's copies, or a refusal that says no more."""
	if not name or frappe.db.get_value(DOCTYPE, name, "tenant") != tenant.name:
		frappe.throw(frappe._("This workspace has no such training copy."), frappe.DoesNotExistError)
	return frappe.get_doc(DOCTYPE, name)


def end_for(tenant, name: str) -> dict:
	"""A workspace's administrator ends one of its copies: deleted now."""
	doc = _theirs(tenant, name)
	if doc.status not in ("Deleting", "Deleted"):
		_begin_deleting(doc)
	return _said_of(name)


def sign_in_for(tenant, name: str) -> dict:
	"""A one-time sign-in to one of a workspace's copies, for the
	administrator who asked from it: a copy of its data keeps no password
	(`quieted`), so this is the way in."""
	doc = _theirs(tenant, name)
	if doc.status != "Running":
		frappe.throw(frappe._("The copy isn't ready yet. It can be opened once it says Ready."))
	said = _asked(pilot.on, doc, "POST", f"/sites/{doc.site}/login") or {}
	return {"url": said.get("url") or doc.link}


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
	"""A one-time sign-in to a Fresh or Demo session an operator started. A
	workspace's copy has none here: it is the workspace's, opened by its own
	administrator (`sign_in_for`)."""
	_may()
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.source == COPY or doc.tenant:
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
	pilot.on(doc, "PATCH", f"/sites/{doc.site}/configuration", json=config_for(doc.source, doc.link, doc.expires_on, opens_on(doc.source, doc.field)))


def set_up(doc) -> None:
	"""A fresh copy a workspace asked for, set up by the box's agent through
	the setup job (one/setup_job.py) from the workspace's own answers."""
	said = fresh_answers(answers.of(frappe.get_doc("Tenant", doc.tenant)), doc.started_by)
	if not said:
		raise faults.Refused("the workspace's setup answers are not kept")
	servers.instruct(doc.server, SET_UP, session=doc.name, bench=doc.bench, site=doc.site, answers=said)


def demo(doc) -> None:
	servers.instruct(doc.server, "session-demo", session=doc.name, bench=doc.bench, site=doc.site)


def ready_demo(doc) -> None:
	"""The box's agent makes the site from the release's ready demo, as it
	makes a spare from the template: the copy's own database user, config
	and Administrator password, the demo's records and files."""
	servers.instruct(doc.server, READY_KIND, session=doc.name, bench=doc.bench, site=doc.site, release=doc.upload)


def copy(doc) -> None:
	"""The workspace's newest nightly backup, its database alone, sent to the
	server and held for `restore`."""
	slug = frappe.db.get_value("Tenant", doc.tenant, "slug")
	kept = _kept_backup(slug)
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
	workspace's own world, and mail and webhooks stay off. Its people's
	passwords and API keys are cleared and nobody stays signed in, so
	nothing that opens the workspace opens its copy: the administrator who
	asked opens it once (`sign_in_for`) and sets passwords for whoever
	trains."""
	frappe.db.delete("Webhook")
	frappe.db.delete("__Auth", {"doctype": "User"})
	frappe.db.delete("Sessions")
	for account in frappe.get_all("Email Account", pluck="name"):
		frappe.db.set_value("Email Account", account, {"enable_outgoing": 0, "enable_incoming": 0}, update_modified=False)
	frappe.db.commit()


def _queue(name: str) -> None:
	"""`advance` in the background, and only one at a time for a session:
	sending a backup up takes a while and must not be started twice."""
	frappe.enqueue("onedesk.one_admin.sessions.advance", queue="long", timeout=ADVANCE_TIMEOUT, job_id=f"one_session_{name}", deduplicate=True, enqueue_after_commit=True, name=name)


def _walking(doc) -> tuple:
	"""Which walk a session is on: `upload` names the release of a demo
	restored from its ready demo, as it names a copy's upload, and a fresh
	one a workspace's administrator started is set up from its answers."""
	return doc.source, bool(doc.upload), bool(doc.tenant and doc.started_by)


def advance(name: str) -> None:
	"""One step of a session, and on from there until it waits."""
	doc = frappe.get_doc(DOCTYPE, name)
	if doc.status == "Deleting":
		_deleting(doc)
		return
	if doc.status != "Starting":
		return
	source, ready, own = _walking(doc)
	for _ in range(len(walk_of(source, ready, own))):
		try:
			said = STEPS[doc.step](doc)
		except faults.Again:
			return
		except faults.Refused as refused:
			doc.db_set({"status": "Failed", "error": str(refused)[: faults.KEPT]}, notify=True)
			return
		if said == WAIT:
			return
		following = after(source, doc.step, ready, own)
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


STEPS = {"create": create, "created": created, "configure": configure, "set_up": set_up, "demo": demo, READY: ready_demo, "copy": copy, "restore": restore, "restored": restored, "quiet": quiet, "agent_done": agent_done, "route": route}


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
		source, ready, own = _walking(doc)
		doc.db_set("step", after(source, "agent_done", ready, own))
		_queue(doc.name)


def tick() -> None:
	"""Every two minutes, on the admin site: starting sessions move on, what
	has run its time is deleted, and a copy of a workspace, or one it
	started, goes too once the workspace turned Training Copies off or its
	plan no longer includes them."""
	if not site.is_admin():
		return
	now = now_datetime()
	for row in frappe.get_all(DOCTYPE, filters={"status": ["in", ("Starting", "Deleting")]}, fields=["name"]):
		_safely(_queue, row.name)
	for row in frappe.get_all(DOCTYPE, filters=[["status", "in", ("Starting", "Running", "Stopped", "Failed")], ["expires_on", "is", "set"], ["expires_on", "<=", now]], fields=["name"]):
		_safely(_expired, row.name)
	for row in frappe.get_all(DOCTYPE, filters={"status": ["in", ("Running", "Stopped")], "tenant": ["is", "set"]}, fields=["name", "tenant"]):
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
