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
	"""`home` is the module that declares its tools, levels and labels: its
	app's agent.py, or for a centre's agent a file of its own beside the
	centre (one/setup_center_agent.py)."""

	app: str
	email: str
	title: str
	roles: tuple[str, ...]
	only: tuple[str, ...] = ()
	home: str = ""


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
	return Agent(app.id, email(app.id), app.agent, given + only, only, f"onedesk.{app.id}.agent")


@cache
def centred() -> tuple[Agent, ...]:
	"""The agents of centres, such as SetupCenter's setup guide: none holds
	a role, so whatever it would change is a card for a person, and it is
	not one of the departments' agents (`listed`) that Intake, the Worker
	and AICenter's tabs work with. Each declares itself in
	`onedesk/<folder>/<centre>_agent.py`."""
	found = []
	for folder, part in registry.part_folders():
		if part.agent:
			found.append(Agent(part.id, email(part.id), part.agent, (), (), f"onedesk.{folder}.{part.id}_agent"))
	return tuple(found)


@cache
def listed() -> tuple[Agent, ...]:
	"""Every app's agent, in the rail's order."""
	return tuple(one for one in (of(app) for app in registry.apps()) if one)


def only() -> dict[str, str]:
	"""Every role one agent holds alone, {role: that agent's email}."""
	return {role: one.email for one in listed() for role in one.only}


def by_email(address: str) -> Agent | None:
	return next((one for one in (*listed(), *centred()) if one.email == address), None)


def get(app: str) -> Agent | None:
	return next((one for one in (*listed(), *centred()) if one.app == app), None)


def is_centred(app: str | None) -> bool:
	return any(one.app == app for one in centred())
