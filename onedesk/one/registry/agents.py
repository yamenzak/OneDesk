"""Every app's agent (docs/ARC-AI.md, The agents), read from the manifests:
the user it works as and the only roles that user holds, its app's User
roles. Never a manager's role, never one that runs the workspace. Pure."""

from dataclasses import dataclass
from functools import cache

from onedesk.one import registry

DOMAIN = "agents.one.invalid"

NEVER = ("Administrator", "System Manager", "Workspace Administrator", "AccountCenter Manager")
"""Roles no agent holds: each changes roles, settings or the workspace itself."""


class Invalid(ValueError):
	"""A manifest whose agent would hold a role no agent may."""


@dataclass(frozen=True)
class Agent:
	app: str
	email: str
	title: str
	roles: tuple[str, ...]


def email(app: str) -> str:
	return f"{app.replace('_', '-')}@{DOMAIN}"


def of(app) -> Agent | None:
	"""The agent an app declares, or None when it has no agent or no User roles."""
	if not app.agent or not app.roles.user:
		return None
	given = tuple(app.roles.user)
	refused = [role for role in given if role in NEVER or role in app.roles.manager]
	if refused:
		raise Invalid(f"{app.id}/manifest.py: an agent never holds {refused}")
	return Agent(app.id, email(app.id), app.agent, given)


@cache
def listed() -> tuple[Agent, ...]:
	"""Every app's agent, in the rail's order."""
	return tuple(one for one in (of(app) for app in registry.apps()) if one)


def by_email(address: str) -> Agent | None:
	return next((one for one in listed() if one.email == address), None)


def get(app: str) -> Agent | None:
	return next((one for one in listed() if one.app == app), None)
