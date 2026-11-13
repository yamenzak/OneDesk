"""AccountCenter's setup steps (one/setup_steps.py, docs/READY.md mechanism 9):
inviting the people who work there, which a workspace is little without.
AccountCenter starts with it while it is left to do."""

from frappe import _lt


def _invited() -> bool:
	from onedesk.one.people import seats_used

	return seats_used() > 1


STEPS = [
	{
		"key": "people",
		"title": _lt("Invite Your People"),
		"about": _lt("Everybody who works here, each with the apps their work needs."),
		"needs": None,
		"tab": "people",
		"done": _invited,
	},
]
