"""What TrustCenter tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files. Each entry
has the keys of a notification file (notifications/layout.py KEYS), with
`subject` and `message` for its heading and body, and says its `channels`,
each on or why not, and its `sender` (docs/READY.md, mechanism 8). Pure."""

from onedesk.one import registry

TYPES = [
	{
		"name": "Agreements Changed",
		"app": registry.name("trust_center"),
		"roles": ("Workspace Administrator",),
		"about": "When {one} publishes a new version of an agreement the workspace accepted.",
		"to": "Every administrator",
		"channels": {
			"bell": True,
			"email": "It is always mailed, because the time to object runs from it.",
			"push": True,
		},
		"always_mailed": True,
		"button": "Read It",
		"sender": "system",
		"subject": "One's agreements are changing",
		"message": "New versions of: {documents}. They take effect on {effective}, and until then the versions you agreed to hold. {trust_center} shows what changes. To object to a new subprocessor, reply before then.",
	},
	{
		"name": "Policies Changed",
		"app": registry.name("trust_center"),
		"about": "When {one} publishes a new version of a policy each person agreed to.",
		"to": "Everyone in the workspace",
		"channels": {"bell": True, "email": True, "push": True},
		"button": "Read It",
		"sender": "system",
		"subject": "One's policies are changing",
		"message": "New versions of: {documents}. They take effect on {effective}. {trust_center} shows what changes.",
	},
]
