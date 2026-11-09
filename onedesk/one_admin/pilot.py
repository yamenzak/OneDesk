"""A server's Pilot, called through its Cloudflare Access lock.

Pilot runs the benches and sites on each box, and its Admin API is the whole
boundary. Each server's address and keys are kept by `remember`; a long job
comes back as a task to ask after (`task`). README, Servers.
"""

import frappe
import requests

from onedesk.one_admin import faults, vault

TIMEOUT = 60
API = "/api/v1"


def remember(server: str, client_id: str, client_secret: str, password: str, tunnel: str | None = None, agent: str | None = None) -> None:
	"""A server's Access token, Pilot password, tunnel and agent secret, in
	the site's config."""
	vault.keep(_key(server), frappe.as_json({"id": client_id, "secret": client_secret, "password": password, "tunnel": tunnel, "agent": agent}))


def held(server: str) -> dict:
	found = frappe.parse_json(vault.get(_key(server)) or "null")
	if not found:
		raise faults.Refused(f"there are no keys for {server}")
	return found


def _key(server: str) -> str:
	return f"one_server_{frappe.scrub(server)}"


def _row(server: str):
	found = next((one for one in frappe.get_cached_doc("One Admin Settings").get("servers") or [] if one.server == server), None)
	if not found or not found.pilot_host:
		raise faults.Refused(f"Settings lists no Pilot address for {server}")
	return found


def _host(row, bench: str | None) -> str:
	"""Each bench answers at its own Pilot address; none named is the first."""
	found = next((one for one in frappe.parse_json(row.benches or "[]") or [] if one.get("bench") == bench), None)
	return (found or {}).get("host") or row.pilot_host


def _session(server: str, bench: str | None) -> tuple[requests.Session, str]:
	keys = held(server)
	base = f"https://{_host(_row(server), bench)}{API}"
	session = requests.Session()
	session.headers.update({"CF-Access-Client-Id": keys["id"], "CF-Access-Client-Secret": keys["secret"]})
	try:
		answer = session.post(f"{base}/auth/session", json={"password": keys["password"]}, timeout=TIMEOUT, allow_redirects=False)
	except requests.RequestException as raised:
		raise faults.Again(f"{server} could not be reached: {raised}") from raised
	if answer.status_code != 201:
		raise faults.raised(f"{server} sign-in", answer.status_code, faults.detail(None, answer.text))
	return session, base


def call(server: str, method: str, path: str, key: str | None = None, bench: str | None = None, **kwargs):
	"""One Admin API call; `key` makes a repeat of it the same task. None for
	a 404, which here always means there is no such site or task."""
	session, base = _session(server, bench)
	headers = {"Idempotency-Key": key} if key else {}
	try:
		answer = session.request(method, f"{base}{path}", headers=headers, timeout=TIMEOUT, **kwargs)
	except requests.RequestException as raised:
		raise faults.Again(f"{path} on {server} could not be reached: {raised}") from raised
	if answer.status_code == 404:
		return None
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
