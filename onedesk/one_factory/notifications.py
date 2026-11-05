"""What OneFactory tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Pure."""

ALL = {"bell": True, "email": True, "push": True}

TYPES = [
	{
		"name": "Back From Supplier Late",
		"app": "OneFactory",
		"roles": ("Purchase User", "Purchase Manager", "Manufacturing User"),
		"about": "The day after subcontracted goods were due back and have not all come back.",
		"to": "Whoever made the subcontracting order",
		"channels": ALL,
		"email_default": True,
		"sender": "workspace",
		"subject": "{supplier} is late returning {order}",
		"message": "It was due back on {due}. Chase {supplier}.",
	},
	{
		"name": "Work Order Done",
		"app": "OneFactory",
		"roles": ("Manufacturing User", "Projects Manager", "Sales User"),
		"about": "When everything a work order was for has been made.",
		"to": "Whoever asked for it, and the project's manager",
		"channels": ALL,
		"email_default": False,
		"sender": "workspace",
		"subject": "{item} is made",
		"message": "All {qty} on {order} are made and in {warehouse}.",
	},
]
