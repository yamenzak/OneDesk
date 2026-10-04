"""What OneProject tells people, as notification types (one/notify.py).

Sent by `updates.py` (the update asked, and the morning's answers) and
`tell.py` (a person added to a project or made its manager, and a project
marked at risk or off track).
"""

from frappe import _lt

TYPES = [
	# updates: the project asks its people how it is going.
	{
		"name": _lt("Project Update Asked"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt(
			"As often as a project says, to ask how it is going. A project's own question replaces this text."
		),
		"to": _lt("The project's people"),
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
		"about": _lt("Every morning, what a project's people said about it the day before."),
		"to": _lt("The project's people"),
		"subject": _lt("What was said about {project} on {date}"),
		"message": "{answers}",
	},
	# tell: who is on a project, and how it is going.
	{
		"name": _lt("Added to Project"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When somebody adds you to a project's members."),
		"to": _lt("Each person added, but whoever added them"),
		"subject": _lt("{who} added you to {project}"),
		"message": _lt("<b>{project}</b>{customer}{due}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Made Project Manager"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When somebody makes you a project's manager."),
		"to": _lt("The new manager, unless they made themselves it"),
		"subject": _lt("{who} made you the manager of {project}"),
		"message": _lt("<b>{project}</b>{customer}{due}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Project Health"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When somebody marks a project At Risk or Off Track."),
		"to": _lt("The project's manager and members, but whoever marked it"),
		"subject": _lt("{who} marked {project} {health}"),
		"message": _lt("<b>{project}</b> is {health}{due}"),
		"push_default": True,
	},
]
