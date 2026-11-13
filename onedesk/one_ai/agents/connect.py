"""Where this workspace's agents run and the secret their calls are signed
with (deploy/agents/README.md): asked of the account once an hour
(one_admin/proxy.py agents_config), or set in the site's config as `one_agents` on a
bench of its own. No address, no agents: Intake goes on as it was."""

import json
import time
from urllib.parse import urlparse

import frappe
import requests

from onedesk.one_ai.agents import token

CACHE = "one_agents_config"
AN_HOUR = 3600
PATIENCE = 10
PATH = "/agents/agent/{workspace}.{app}"


def config() -> dict:
	"""`url`, `secret` and `workspace`, or nothing while agents are not set up."""
	held = frappe.conf.get("one_agents")
	if held:
		return {"workspace": frappe.conf.get("one_tenant"), **held}
	cached = frappe.cache.get_value(CACHE)
	if cached is None:
		cached = _asked()
		frappe.cache.set_value(CACHE, cached, expires_in_sec=AN_HOUR)
	return cached


def on() -> bool:
	said = config()
	return bool(said.get("url") and said.get("secret") and said.get("workspace"))


def _asked() -> dict:
	from onedesk.one import account
	from onedesk.one_admin import faults

	if not account.configured():
		return {}
	try:
		said = account.ask("onedesk.one_admin.proxy.agents_config") or {}
	except (faults.Refused, faults.Again):
		return {}
	return {**said, "workspace": frappe.conf.get("one_tenant")} if said.get("url") else {}


def host() -> str:
	return urlparse(frappe.conf.get("hostname") or frappe.utils.get_url()).netloc


def wake(app: str, event: dict, asked_by: str | None = None) -> bool:
	"""Hand an event to an app's agent on the Worker: signed for the agents'
	way, for this agent and this body, for a minute. False when agents are
	not set up, are turned off or this one is over its credits
	(workspace.py), or the Worker did not take it."""
	from onedesk.one_ai.agents import workspace

	said = config()
	if not on() or workspace.refusal(app):
		return False
	body = json.dumps({**event, "host": host()})
	claims = {"aud": "agents", "ws": said["workspace"], "agent": app, **({"for": asked_by} if asked_by else {})}
	signed = token.mint(said["secret"], claims, body, int(time.time()))
	url = said["url"].rstrip("/") + PATH.format(workspace=said["workspace"], app=app)
	try:
		answer = requests.post(url, data=body, headers={"content-type": "application/json", "x-one-agent-token": signed}, timeout=PATIENCE)
	except requests.RequestException:
		return False
	return answer.status_code == 202
