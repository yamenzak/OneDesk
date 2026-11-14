"""The agents as members of OneChat (docs/ARC-AI.md, OneChat): Una, who
everybody talks to first, and each app's agent from the registry
(registry/agents.py), reached by whoever may open its app. An agent is
asked in a conversation of its own (an Agent channel) or by being mentioned
in a channel, and answers with its own tools as the person who asked
(answers.py, one_ai/agents/talk.py): AGENTS.md, How an agent answers."""

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one.registry import agents

UNA = "una"
"""Una's id: she has no app and no user of her own (docs/ARC-AI.md, The agents)."""

FACE = "bottts"
"""The DiceBear style every agent's face is drawn in, seeded by its id so it
never changes (one/avatars.py draws it on this server)."""


def una() -> str:
	return _("Una")


def name_of(agent: str) -> str:
	"""What an agent is called where people read it: Una, or "OneBook's
	accountant"."""
	if agent == UNA:
		return una()
	one = agents.get(agent)
	if not one:
		return agent
	from onedesk.one_ai.agents import users

	return users.full_name(one)


def handle_of(agent: str) -> str:
	"""What a person types after @ to ask it: Una, or the app's name."""
	return una() if agent == UNA else registry.name(agent)


def user_of(agent: str) -> str | None:
	"""The user an agent writes as; Una writes as nobody."""
	one = agents.get(agent)
	return one.email if one else None


def of_user(user: str | None) -> str | None:
	"""The agent a user is, if it is one."""
	one = agents.by_email(user) if user else None
	return one.app if one else None


def reaches(agent: str, user: str | None = None) -> bool:
	"""Whether a person may talk to an agent: Una to everybody, an app's agent
	to whoever holds one of its app's roles (docs/ARC-AI.md, Trust and
	permissions)."""
	if agent == UNA:
		return True
	one = agents.get(agent)
	if not one:
		return False
	if agents.is_centred(agent):
		from onedesk.one_ai.agents import levels

		return bool(levels.home(agent).reaches(user))
	app = registry.get(agent)
	held = set(frappe.get_roles(user or frappe.session.user))
	return bool(held & {*app.roles.user, *app.roles.manager})


def listed(user: str | None = None) -> list[dict]:
	"""Una and every agent this person may talk to, in the rail's order."""
	ids = [UNA, *(one.app for one in (*agents.listed(), *agents.centred()))]
	return [shown(one) for one in ids if reaches(one, user)]


def shown(agent: str) -> dict:
	return {
		"agent": agent,
		"name": name_of(agent),
		"handle": handle_of(agent),
		"app": "" if agent == UNA else agent,
		"face": face(agent),
	}


def face(agent: str) -> str | None:
	"""Its face as an SVG, drawn once and kept; None where this server
	cannot draw."""

	def drawn():
		from onedesk.one import avatars

		try:
			return (avatars.draw([(FACE, agent)]) or [None])[0]
		except Exception:
			return None

	return frappe.cache.get_value(f"one_chat_face:{agent}", drawn)


def for_page(page: dict | str | None) -> str:
	"""Who the panel talks to on a page: the agent of the centre open over
	it or of the app the page belongs to, when the reader may reach it,
	else Una."""
	if isinstance(page, str):
		page = frappe.parse_json(page) if page.strip() else None
	page = page if isinstance(page, dict) else {}
	centre = _centre(page)
	if centre and reaches(centre):
		return centre
	module = _module(page)
	app = registry.of_module(module) if module else None
	if app and agents.get(app.id) and reaches(app.id):
		return app.id
	return UNA


def _centre(page: dict) -> str | None:
	"""The agent of the centre the reader has open (oneai.js `where`, a
	centre's key as its page), if that centre has one."""
	key = page.get("page")
	held = {registry.get(one.app).centre.key: one.app for one in agents.centred() if registry.get(one.app).centre}
	return held.get(key) if key else None


def _module(page: dict) -> str | None:
	doctype = page.get("doctype")
	if doctype and frappe.db.exists("DocType", doctype):
		return frappe.get_meta(doctype).module
	if page.get("page") and frappe.db.exists("Page", page["page"]):
		return frappe.db.get_value("Page", page["page"], "module")
	if page.get("report") and frappe.db.exists("Report", page["report"]):
		return frappe.db.get_value("Report", page["report"], "module")
	return None


def mentioned(text: str, handles: dict[str, str]) -> list[str]:
	"""The keys whose handle follows an @ in the text, in the order they are
	said; the longest handle is tried first, so "@Huda Saleh" is not read as
	"@Huda". Pure."""
	said = (text or "").casefold()
	found, taken = [], []
	for key, handle in sorted(handles.items(), key=lambda one: -len(one[1] or "")):
		mark = f"@{(handle or '').casefold()}"
		if not handle:
			continue
		at = said.find(mark)
		while at >= 0:
			end = at + len(mark)
			inside = any(start <= at < stop for start, stop in taken)
			alone = (at == 0 or not said[at - 1].isalnum()) and (end == len(said) or not (said[end].isalnum() or said[end] == "_"))
			if not inside and alone:
				found.append((at, key))
				taken.append((at, end))
				break
			at = said.find(mark, at + 1)
	return [key for _at, key in sorted(found)]
