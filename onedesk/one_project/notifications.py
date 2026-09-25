"""What OneProject tells people, as notification types (one/notify.py)."""

from frappe import _lt

TYPES = [
	# updates: the project asks its people how it is going.
	{
		"name": _lt("Project Update Asked"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt(
			"A project asks its people how it is going, as often as the project says. A project's own "
			"question is asked instead of this text."
		),
		"subject": _lt("How is {project} going?"),
		"message": _lt("Post your update on the project's page, or reply to the email."),
		# Not mailed through the bell, because its own mail is one people reply
		# to, and that is always sent (updates.py, notify.mail).
		"email": False,
		"always_mailed": True,
	},
	# updates: yesterday's answers, which ERPNext mailed only where mail could go.
	{
		"name": _lt("Project Summary"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("What a project's people said about it yesterday. Sent to them each morning."),
		"subject": _lt("What was said about {project} on {date}"),
		"message": "{answers}",
	},
]
