"""What OneStudio tells people, as notification types (one/notify.py).

Sent by `extensions.failing`, each morning, when an extension tripped the day
before, and by `extensions.sync` and `extensions.remove` when an administrator turns one on or off or
deletes it, to the others: a server extension runs on everybody's saves from
that moment. An extension's own messages (a save it stops, a warning on a
form) are the extension's, shown on the screen where it runs."""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Extensions Failing"),
		"app": "OneStudio",
		"roles": ("Workspace Administrator",),
		"about": _lt(
			"Every morning, the extensions that ran into errors the day before. Not sent when none did."
		),
		"to": _lt("Every administrator"),
		"subject": _lt("Extensions ran into errors yesterday"),
		"message": _lt(
			"These extensions ran into errors, and the work went on: {extensions}. Open one and press "
			"Mend With OneAI, or turn it off."
		),
		"email_default": True,
	},
	{
		"name": _lt("Extension Turned On"),
		"app": "OneStudio",
		"roles": ("Workspace Administrator",),
		"about": _lt(
			"When another administrator turns an extension on: what it does, where and when it runs."
		),
		"to": _lt("The other administrators"),
		"subject": _lt("{who} turned on {title}"),
		"message": _lt("{where}, on {kind}. {explanation}"),
		"email_default": True,
	},
	{
		"name": _lt("Extension Turned Off"),
		"app": "OneStudio",
		"roles": ("Workspace Administrator",),
		"about": _lt("When another administrator turns an extension off."),
		"to": _lt("The other administrators"),
		"subject": _lt("{who} turned off {title}"),
		"message": _lt("It no longer runs on {kind}. {explanation}"),
		"email_default": False,
	},
	{
		"name": _lt("Extension Deleted"),
		"app": "OneStudio",
		"roles": ("Workspace Administrator",),
		"about": _lt("When another administrator deletes an extension."),
		"to": _lt("The other administrators"),
		"subject": _lt("{who} deleted {title}"),
		"message": _lt("It no longer runs on {kind}. {explanation}"),
		"email_default": False,
	},
]
