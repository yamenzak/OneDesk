"""What OneStudio tells people, as notification types (one/notify.py).

Sent by `extensions.failing`, each morning, when an extension tripped the day
before. An extension's own messages (a save it stops, a warning on a form)
are the extension's, shown on the screen where it runs."""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Extensions Failing"),
		"app": "OneStudio",
		"roles": ("Workspace Administrator",),
		"about": _lt(
			"Every morning, the extensions that ran into a mistake the day before. Not sent when none did."
		),
		"to": _lt("Every administrator"),
		"subject": _lt("Extensions ran into mistakes yesterday"),
		"message": _lt(
			"These extensions ran into a mistake, and the records still saved: {extensions}. Ask OneAI in "
			"OneStudio to look at one and mend it, or turn it off."
		),
		"email_default": True,
	},
]
