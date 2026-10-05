"""What OneProject tells people, as notification types (one/notify.py).

Sent by `updates.py` (the update asked, and the morning's answers) and
`tell.py` (a person added to a project or made its manager, and a project
marked at risk or off track, and a project completed), `budget.py` (a cost type over its budget) and
`progress.py` (a bill drafted for a share of the work), `retention.py`
(retention falling due), and `tell.py` again
for a retainer (its month ready to invoice, its hours for the month used).
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
	{
		"name": _lt("Project Completed"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt(
			"When a project is completed, by somebody or by its last task, with what's still owed on it."
		),
		"to": _lt("The project's manager, unless they completed it"),
		"subject": _lt("{project} is completed"),
		"message": _lt("<b>{project}</b>{customer}{owed}"),
		"push_default": True,
	},
	# milestones: a milestone billed on completion is done.
	{
		"name": _lt("Milestone Done"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When a milestone that's billed on completion is done."),
		"to": _lt("The manager of the project with the order, unless they marked it done"),
		"subject": _lt("{milestone} is done"),
		"message": _lt("<b>{project}</b> · Bill {share}"),
		"push_default": True,
	},
	# budget: orders and spending on a cost type pass its budget.
	{
		"name": _lt("Over Budget"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When what's ordered and spent on a project's cost type passes its budget."),
		"to": _lt("The project's manager and whoever set the budget"),
		"subject": _lt("{cost_type} is over budget on {project}"),
		"message": _lt("<b>{project}</b> · {cost_type} · {total} of {budget}"),
		"email_default": True,
		"push_default": True,
	},
	# progress: a bill or invoice for a share of the work, waiting to be checked.
	{
		"name": _lt("Progress Bill Drafted"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When somebody saves a bill or invoice for a share of the work done."),
		"to": _lt("The project's manager, unless they saved it"),
		"subject": _lt("{who} drafted a bill for {order} at {share}% done"),
		"message": _lt("<b>{project}</b> · {party} · {amount}"),
		"push_default": True,
	},
	# retention: a share held back on either side, falling due.
	{
		"name": _lt("Retention Due"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("On the day retention held by a customer, or from a supplier, falls due."),
		"to": _lt("The project's manager"),
		"subject": _lt("Retention on {project} is due today"),
		"message": "{held}",
		"email_default": True,
		"push_default": True,
	},
	# tell: a retainer's month, to invoice and over its hours.
	{
		"name": _lt("Retainer Month to Invoice"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("On the first of the month, for each retainer whose last month isn't invoiced."),
		"to": _lt("The project's manager, or whoever made it"),
		"subject": _lt("Invoice {project} for last month"),
		"message": _lt("<b>{project}</b> · {hours} h of {allowance} h{customer}"),
		"email_default": True,
	},
	{
		"name": _lt("Retainer Hours Used"),
		"app": "OneProject",
		"roles": ("Projects User",),
		"about": _lt("When the time logged on a retainer passes its hours for the month."),
		"to": _lt("The project's manager, or whoever made it"),
		"subject": _lt("{project} has used its {allowance} h for this month"),
		"message": _lt("<b>{project}</b> · {hours} h of {allowance} h{customer}"),
		"push_default": True,
	},
]
