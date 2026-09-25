"""What OneProject tells people, as notification types (one/notify.py)."""

from frappe import _lt

TYPES = [
	# updates: the project asks its people how it is going.
	{
		"name": _lt("Project Update Asked"),
		"app": "OneProject",
		"about": _lt(
			"A project asks its people how it is going, as often as the project says. The email is one "
			"they can reply to, so it is always sent, and a project's own question is asked instead of this text."
		),
		"subject": _lt("How is {project} going?"),
		"message": _lt("Post your update on the project's page, or reply to the email."),
		"email": False,
	},
]
