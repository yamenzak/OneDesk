"""The Agents Worker calling this workspace back (docs/ARC-AI.md, Decided):
one tool of one agent per call, each carrying a token of its own
(token.py). The tool runs here as the agent's user, so its permissions are
the only ones that count, and every write goes through door.py."""

import importlib
import time

import frappe
from frappe.rate_limiter import rate_limit

from onedesk.one.registry import agents
from onedesk.one_ai.agents import connect, token, workspace

HEADER = "X-One-Agent-Token"
CALLS_A_MINUTE = 120


def seen(jti: str, until: int) -> bool:
	"""Whether a token was used before; remembered until it lapses, set and
	asked in one step so two calls with it at once cannot both pass."""
	key = frappe.cache.make_key(f"one_agent_token:{jti}")
	return not frappe.cache.set(key, 1, ex=max(1, until - int(time.time()) + token.EARLY), nx=True)


def tool_of(app: str, name: str):
	"""The tool an agent may call: one its agent.py lists in TOOLS, or one
	every agent has (levels.EVERY_AGENT, in work.py)."""
	from onedesk.one_ai.agents import levels, work

	if name in levels.EVERY_AGENT:
		return getattr(work, name)
	module = importlib.import_module(f"onedesk.{app}.agent")
	if name not in getattr(module, "TOOLS", ()):
		raise token.Refused("no such tool")
	return getattr(module, name)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=CALLS_A_MINUTE, seconds=60)
def tool(tool: str | None = None, args: dict | None = None):
	said = connect.config()
	body = frappe.request.get_data(as_text=True)
	try:
		claims = token.verify(said.get("secret"), frappe.get_request_header(HEADER) or "", "workspace", body, int(time.time()), seen)
		agent = agents.get(claims.get("agent"))
		if claims.get("ws") != said.get("workspace") or not agent or agents.is_centred(agent.app) or claims.get("tool") != tool:
			raise token.Refused("not this workspace's agent")
		run = tool_of(agent.app, tool)
		asked_by = claims.get("for")
		if asked_by and not frappe.db.get_value("User", asked_by, "enabled"):
			raise token.Refused("asked by nobody here")
	except token.Refused:
		frappe.throw(frappe._("Not allowed."), frappe.PermissionError)
	workspace.refuse(agent.app)
	frappe.set_user(agent.email)
	return run(**(frappe.parse_json(args) or {}), asked_by=asked_by)
