"""What every agent's money planner shares (one_book, one_crm and
one_inventory planner.py): whether a document is one to book, and the action
a money record is made with. Pure."""

from onedesk.one_ai.reading.act import Action as _Action

REAL = ("Action", "Information", "", None)


def Action(*args, **kwargs) -> _Action:
	"""Every money action is applied as whoever approves its card, never as
	OneAI: ERPNext checks the signed-in user's access to each account a
	draft touches. An agent writes it as itself."""
	return _Action(*args, **{**kwargs, "as_person": True})


def _real(reading: dict, ctx: dict) -> bool:
	return bool(ctx.get("books")) and reading.get("verdict") in REAL and not ctx.get("history") and ctx.get("direction") != "Sent"
