"""Asking the account to run a job, from the workspace that wants it.

Only the job, the content and the conversation travel with the call: what the
model is told is `jobs.py`'s, and which model answers is the account's.
"""

import frappe

from onedesk.one import account
from onedesk.one_ai import center


def turn(action: str, text: str, turns: list[dict], tools: list[dict] | None, reference: str | None = None, agent: str | None = None) -> dict:
	"""One round of a conversation with tools: the model's next turn, which
	either answers (`done`) or asks for tools (`wants`). The rounds are the
	asking agent's to run (one_ai/agents/talk.py), and counted against it."""
	from onedesk.one import apps

	apps.refuse_ai()
	out = account.ask(
		"onedesk.one_admin.proxy.ai_run",
		action=action,
		text=text,
		tier=center.tier(),
		reference=reference,
		turns=turns,
		tools=tools,
	)
	_counted(reference, (out or {}).get("credits"), agent)
	return out or {}


def once(action: str, text: str, files: list[dict] | None = None, reference: str | None = None) -> str:
	"""One call, no tools and no loop: what a background job asks.

	The chat's loop is for a model that looks things up as the person asking.
	A job that has already gathered everything the model needs — a CV and the
	opening it was sent to — has nobody to look things up as, so it hands the
	lot over in one turn and takes the words back. `files` carry their bytes,
	base64'd, the shape `files.carried` makes.
	"""
	from onedesk.one import apps

	apps.refuse_ai()
	out = account.ask(
		"onedesk.one_admin.proxy.ai_run",
		action=action,
		text=text,
		tier=center.tier(),
		reference=reference,
		turns=[{"role": "user", "text": text, "calls": [], "files": files or []}],
		tools=None,
	)
	_counted(reference, (out or {}).get("credits"))
	return (out or {}).get("said") or ""


def make(action: str, text: str, reference: str | None = None, voice: str | None = None) -> dict:
	"""A voice, a picture or a song made by a job: `{"data": base64,
	"mime": ...}`, billed like `once`."""
	from onedesk.one import apps

	apps.refuse_ai()
	out = account.ask(
		"onedesk.one_admin.proxy.ai_make",
		action=action,
		text=text,
		tier=center.tier(),
		reference=reference,
		voice=voice,
	)
	_counted(reference, (out or {}).get("credits"))
	return {"data": (out or {}).get("data") or "", "mime": (out or {}).get("mime") or ""}


def begin(action: str, text: str, reference: str | None = None, orientation: str | None = None) -> str:
	"""Begin a video made by a job: the ticket `collect` takes. Nothing is
	billed until it is collected."""
	from onedesk.one import apps

	apps.refuse_ai()
	out = account.ask(
		"onedesk.one_admin.proxy.ai_begin",
		action=action,
		text=text,
		tier=center.tier(),
		reference=reference,
		orientation=orientation,
	)
	return (out or {}).get("ticket") or ""


def collect(ticket: str, reference: str | None = None) -> dict:
	"""A begun video: `{"done": False}` until it is made, then its bytes,
	billed like `once`."""
	out = account.ask("onedesk.one_admin.proxy.ai_collect", ticket=ticket) or {}
	if not out.get("done"):
		return {"done": False}
	_counted(reference, out.get("credits"))
	return {"done": True, "data": out.get("data") or "", "mime": out.get("mime") or ""}


def read(action: str, state: str, asked: dict, reference: str | None = None, on: str | None = None) -> dict:
	"""A reading job's answers (Clef's to questions, Clairic's fields), each
	with how sure the model is: one call, billed like `once`."""
	from onedesk.one import apps

	apps.refuse_ai()
	out = account.ask(
		"onedesk.one_admin.proxy.ai_read",
		action=action,
		state=state,
		asked=asked,
		tier=center.tier(),
		reference=reference,
		on=on,
	)
	_counted(reference, (out or {}).get("credits"))
	return (out or {}).get("result") or {}


def _counted(reference: str | None, credits, app: str | None = None) -> None:
	"""A call made for a reading of mail counts against its mailbox's month
	(one_mail/gate.py), and one made while an agent works, or answers a
	person, against that agent's (agents/workspace.py)."""
	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import workspace
	from onedesk.one_mail import gate

	gate.spent(reference, credits)
	agent = agents.get(app) if app else agents.by_email(frappe.session.user)
	if agent:
		workspace.spend(agent.app, credits)


@frappe.whitelist()
def tools() -> list[dict]:
	"""Every tool, as a provider's function declaration.

	Whitelisted so the tenant can hand the list to the account with a call. The
	account never calls a tool: the tools run here, as the person asking, which
	is the only place their permissions mean anything.
	"""
	from onedesk.one_ai import tools as surface

	return surface.declared()


@frappe.whitelist()
def use(tool: str, args: dict | None = None) -> dict:
	"""Call one tool as whoever is signed in.

	Not `allow_guest`, not as Administrator, and with no `ignore_permissions`
	anywhere beneath it — see `one_ai/tools.py`.
	"""
	from onedesk.one_ai import tools as surface

	if isinstance(args, str):
		args = frappe.parse_json(args)
	return surface.run(tool, args or {})


@frappe.whitelist()
def waiting() -> list[dict]:
	"""What a model has suggested and nobody has answered yet."""
	from onedesk.one_ai import proposals

	return proposals.mine()


@frappe.whitelist(methods=["POST"])
def apply(proposal: str) -> dict:
	"""Do what was suggested, as the person pressing the button."""
	from onedesk.one_ai import proposals

	return proposals.apply(proposal)


@frappe.whitelist(methods=["POST"])
def apply_all(proposals: list | str) -> list[dict]:
	"""Approve the cards one answer suggested, in the order it suggested them."""
	from onedesk.one_ai import proposals as suggested

	named = frappe.parse_json(proposals) if isinstance(proposals, str) else proposals
	return suggested.apply_all([str(one) for one in named or []][:50])


@frappe.whitelist(methods=["POST"])
def refuse(proposal: str) -> dict:
	from onedesk.one_ai import proposals

	return proposals.refuse(proposal)


@frappe.whitelist(methods=["POST"])
def took(proposal: str) -> dict:
	"""A suggested change applied into the open form, for the person to save."""
	from onedesk.one_ai import touch

	return touch.took(proposal)


@frappe.whitelist(methods=["POST"])
def landed(proposal: str, record: str) -> dict:
	"""A change taken into a new document, now that the document has a name."""
	from onedesk.one_ai import touch

	return touch.landed(proposal, record)
