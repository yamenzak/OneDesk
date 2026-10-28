"""What OnePortal tells people, one entry per kind of notification, read by
onedesk/notifications/__init__.py beside the other modules' files (docs/
READY.md, mechanism 8). Both go to somebody outside the workspace, so both
are mail alone: the invitation to sign in (invite.py, through OneAccount's
invite) and a link to one record (share.py). Pure."""

TYPES = [
	{
		"name": "Portal Invitation",
		"app": "OnePortal",
		"about": "When someone invites a customer's or supplier's contact to the portal.",
		"to": "The contact invited",
		"channels": {
			"bell": "It goes to somebody outside the workspace, who has no bell.",
			"email": True,
			"push": "It goes to somebody outside the workspace, whose devices One never sees.",
		},
		"button": "Choose your password",
		"outside": True,
		"sender": "workspace",
		"subject": "{inviter} invited you to the {workspace} portal",
		"message": "There you can see {what}.<br><br>The link works for {days} days. You sign in with {address}.",
	},
	{
		"name": "Portal Link",
		"app": "OnePortal",
		"about": "When someone sends a customer or supplier a link to a record.",
		"to": "Whoever the link is for",
		"channels": {
			"bell": "It goes to somebody outside the workspace, who has no bell.",
			"email": True,
			"push": "It goes to somebody outside the workspace, whose devices One never sees.",
		},
		"button": "{button}",
		"outside": True,
		"sender": "workspace",
		"subject": "{by} sent you {what}",
		"message": "From {workspace}.<br><br>The link works until {until}. You don't need an account to open it.",
	},
]
