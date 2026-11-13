"""Every app's agent (docs/ARC-AI.md, The agents), read from the manifests:
the user it works as and the only roles that user holds: its app's User
roles, and the roles the manifest declares for its agent alone, which no
person holds. Never a manager's role, never one that runs the workspace.
Pure."""

from dataclasses import dataclass
from functools import cache

from onedesk.one import registry

DOMAIN = "agents.one.invalid"

NEVER = ("Administrator", "System Manager", "Workspace Administrator", "AccountCenter Manager")
"""Roles no agent holds: each changes roles, settings or the workspace itself."""


class Invalid(ValueError):
	"""A manifest whose agent would hold a role no agent may, or an agent's
	own role that its people hold too."""


@dataclass(frozen=True)
class Agent:
	app: str
	email: str
	title: str
	roles: tuple[str, ...]
	only: tuple[str, ...] = ()


def email(app: str) -> str:
	return f"{app.replace('_', '-')}@{DOMAIN}"


def of(app) -> Agent | None:
	"""The agent an app declares, or None when it has no agent or no User roles."""
	if not app.agent or not app.roles.user:
		return None
	given, only = tuple(app.roles.user), tuple(app.agent_roles)
	refused = [role for role in given + only if role in NEVER or role in app.roles.manager]
	if refused:
		raise Invalid(f"{app.id}/manifest.py: an agent never holds {refused}")
	people = {role for one in registry.apps() for role in (*one.roles.user, *one.roles.manager)}
	shared = [role for role in only if role in people]
	if shared:
		raise Invalid(f"{app.id}/manifest.py: {shared} are people's roles, not its agent's alone")
	return Agent(app.id, email(app.id), app.agent, given + only, only)


@cache
def listed() -> tuple[Agent, ...]:
	"""Every app's agent, in the rail's order."""
	return tuple(one for one in (of(app) for app in registry.apps()) if one)


def only() -> dict[str, str]:
	"""Every role one agent holds alone, {role: that agent's email}."""
	return {role: one.email for one in listed() for role in one.only}


def by_email(address: str) -> Agent | None:
	return next((one for one in listed() if one.email == address), None)


def get(app: str) -> Agent | None:
	return next((one for one in listed() if one.app == app), None)
