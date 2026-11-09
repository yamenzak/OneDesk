"""A server's Pilot, called through its Cloudflare Access lock.

Pilot runs the benches and sites on each box, and its Admin API is the whole
boundary. Each server's address and keys are kept by `remember`; a long job
comes back as a task to ask after (`task`). AGENTS.md, Servers.
"""

import frappe
import requests

from onedesk.one_admin import faults, fleet, vault

TIMEOUT = 60
SESSION_LASTS = 20 * 3600
API = "/api/v1"


def remember(server: str, client_id: str, client_secret: str, password: str, tunnel: str | None = None, agent: str | None = None) -> None:
	"""A server's Access token, Pilot password, tunnel and agent secret, in
	the site's config."""
	vault.keep(_key(server), frappe.as_json({"id": client_id, "secret": client_secret, "password": password, "tunnel": tunnel, "agent": agent}))


def forget(server: str) -> None:
	from frappe.installer import update_site_config

	update_site_config(_key(server), "None")


def held(server: str) -> dict:
	found = frappe.parse_json(vault.get(_key(server)) or "null")
	if not found:
		raise faults.Refused(f"there are no keys for {server}")
	return found


def _key(server: str) -> str:
	return f"one_server_{frappe.scrub(server)}"


def _row(server: str):
	found = fleet.row_of(server)
	if not found or not found.pilot_host:
		raise faults.Refused(f"Settings lists no Pilot address for {server}")
	return found


def _host(row, bench: str | None) -> str:
	"""Each bench answers at its own Pilot address; none named is the newest
	ready one, since the first is dropped after an update."""
	rows = frappe.parse_json(row.benches or "[]") or []
	ready = [one for one in rows if one.get("state") == "ready"]
	found = next((one for one in rows if one.get("bench") == bench), None) if bench else (ready[-1] if ready else None)
	return (found or {}).get("host") or row.pilot_host


def _sign_in(server: str, bench: str | None, base: str, session: requests.Session, wait: int = TIMEOUT) -> str:
	"""A Pilot session, kept so a busy OneAdmin does not trip its limit on
	sign-ins."""
	keys = held(server)
	try:
		answer = session.post(f"{base}/auth/session", json={"password": keys["password"]}, timeout=wait, allow_redirects=False)
	except requests.RequestException as raised:
		raise faults.Again(f"{server} could not be reached: {raised}") from raised
	if answer.status_code != 201:
		raise faults.raised(f"{server} sign-in", answer.status_code, faults.detail(None, answer.text))
	sid = answer.cookies.get("sid")
	frappe.cache().set_value(_held_session(server, bench), sid, expires_in_sec=SESSION_LASTS)
	return sid


def _held_session(server: str, bench: str | None) -> str:
	return f"one_admin_pilot_session:{server}:{bench or ''}"


def _session(server: str, bench: str | None, wait: int = TIMEOUT) -> tuple[requests.Session, str]:
	keys = held(server)
	base = f"https://{_host(_row(server), bench)}{API}"
	session = requests.Session()
	session.headers.update({"CF-Access-Client-Id": keys["id"], "CF-Access-Client-Secret": keys["secret"]})
	sid = frappe.cache().get_value(_held_session(server, bench)) or _sign_in(server, bench, base, session, wait)
	session.headers["Authorization"] = f"Bearer {sid}"
	return session, base


def call(server: str, method: str, path: str, key: str | None = None, bench: str | None = None, wait: int = TIMEOUT, **kwargs):
	"""One Admin API call; `key` makes a repeat of it the same task. None for
	a GET that finds no such site or task. `wait` is how long to wait for an
	answer, for a screen that would rather say so than hang."""
	session, base = _session(server, bench, wait)
	headers = {"Idempotency-Key": key} if key else {}
	try:
		answer = session.request(method, f"{base}{path}", headers=headers, timeout=wait, **kwargs)
		if answer.status_code == 401:
			session.headers["Authorization"] = f"Bearer {_sign_in(server, bench, base, session, wait)}"
			answer = session.request(method, f"{base}{path}", headers=headers, timeout=wait, **kwargs)
	except requests.RequestException as raised:
		raise faults.Again(f"{path} on {server} could not be reached: {raised}") from raised
	if answer.status_code == 404 and method == "GET":
		return None
	if answer.status_code == 409:
		raise faults.Busy(f"{path} on {server} waits for another task")
	if answer.status_code >= 300:
		raise faults.raised(f"{path} on {server}", answer.status_code, faults.detail(None, answer.text))
	return answer.json() if answer.content else {}


def on(tenant, method: str, path: str, key: str | None = None, **kwargs):
	"""`call` on the bench this workspace is on."""
	return call(tenant.server, method, path, key=key, bench=tenant.bench, **kwargs)


def task(server: str, task_id: str, bench: str | None = None) -> str:
	"""`running`, or `done`; a task that failed raises what went wrong."""
	found = call(server, "GET", f"/tasks/{task_id}", bench=bench) or {}
	status = found.get("status")
	if status in ("queued", "running"):
		return "running"
	if status == "success":
		return "done"
	failure = found.get("failure") or {}
	raise faults.Refused(f"{found.get('command') or 'the task'} failed on {server}: {failure.get('message') or status}")
