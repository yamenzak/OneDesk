"""AccountCenter's tours (one/tours.py, docs/READY.md mechanism 10): one, of
AccountCenter, found by the mark at `at`. AccountCenter has no foot, so it
starts the tour itself the first time it opens."""

from frappe import _lt

ACCOUNT = [
	{
		"target": "centre-tree",
		"side": "right",
		"title": _lt("Yours, Then the Workspace's"),
		"text": _lt("Your profile and how you sign in, and for administrators, the workspace's people, devices, plan and domains."),
	},
	{
		"target": "account-section",
		"side": "left",
		"title": _lt("Saved When You Say"),
		"text": _lt("Change what you need and press Save, and a newer change by somebody else stops yours with a message."),
	},
]

TOURS = [{"key": "account", "at": "centre-tree", "steps": ACCOUNT}]
