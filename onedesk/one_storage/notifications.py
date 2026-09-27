"""What OneCloud tells people, as notification types (one/notify.py).

Four of them go to addresses outside the workspace (`outside`): a file
request, its reminder, a shared link and its code. Nobody there has settings
to choose channels in, so they are only ever mailed, through `notify.mail()`.
"""

from frappe import _lt

TYPES = [
	# share: a file or folder shared with somebody in the workspace.
	{
		"name": _lt("Shared With You"),
		"app": "OneCloud",
		"about": _lt("When somebody shares a file or folder with you."),
		"to": _lt("Whoever it is shared with"),
		"subject": _lt("{who} shared {file} with you"),
	},
	# library: somebody added to a library.
	{
		"name": _lt("Added to a Library"),
		"app": "OneCloud",
		"about": _lt("When somebody adds you to a library."),
		"to": _lt("Whoever is added"),
		"subject": _lt("{who} added you to the library {library}"),
	},
	# file_requests: what came back for a file request.
	{
		"name": _lt("File Request Answered"),
		"app": "OneCloud",
		"about": _lt("When somebody sends a file you asked for."),
		"to": _lt("Whoever asked"),
		"subject": _lt("{sender} sent {item} for {request}"),
	},
	{
		"name": _lt("File Request Complete"),
		"app": "OneCloud",
		"about": _lt("When somebody has sent everything you asked for."),
		"to": _lt("Whoever asked"),
		"subject": _lt("{sender} sent everything for {request}"),
		"email_default": True,
	},
	# links: files that arrived through an upload link.
	{
		"name": _lt("Arrived Through a Link"),
		"app": "OneCloud",
		"about": _lt("When somebody outside the workspace uploads files through a link you made."),
		"to": _lt("Whoever made the link"),
		"subject": _lt("{count} files arrived in {folder} through your link"),
	},
	{
		"name": _lt("Arrived Through a Link, One File"),
		"app": "OneCloud",
		"about": _lt("When somebody outside the workspace uploads one file through a link you made."),
		"to": _lt("Whoever made the link"),
		"follows": "Arrived Through a Link",
		"subject": _lt("{file} arrived in {folder} through your link"),
	},
	# file_requests: the mail to the people asked.
	{
		"name": _lt("File Request"),
		"app": "OneCloud",
		"about": _lt("When a file request is sent, with the link to send the files."),
		"to": _lt("Each address it asks"),
		"subject": _lt("{who} asks you for files: {request}"),
		"message": _lt(
			'<b>{who}</b> asks you for files: <b>{request}</b>{note}{due}<br><br><a href="{link}">Send them</a>'
		),
		"outside": True,
	},
	{
		"name": _lt("File Request Reminder"),
		"app": "OneCloud",
		"about": _lt("Before a file request is due, or when its owner sends a reminder."),
		"to": _lt("Whoever has not sent everything"),
		"subject": _lt("Reminder: {who} asks you for files: {request}"),
		"message": _lt(
			'<b>{who}</b> is still waiting for files for <b>{request}</b>.<br><br><a href="{link}">Send them</a>'
		),
		"outside": True,
	},
	# links: the mail to each invited address.
	{
		"name": _lt("Link Shared"),
		"app": "OneCloud",
		"about": _lt("When a link is shared with an address."),
		"to": _lt("Each address invited"),
		"subject": _lt("{who} shared {file} with you"),
		"message": _lt(
			'{who} shared {file} with you.<br><br><a href="{link}">Open it</a><br><br>'
			"You will be asked for a code, which is sent to this address."
		),
		"outside": True,
	},
	{
		"name": _lt("Link Code"),
		"app": "OneCloud",
		"about": _lt(
			"When an invited address opens a shared link. It cannot be turned off, or nobody could open one."
		),
		"to": _lt("The invited address"),
		"subject": _lt("Your code for {file}"),
		"message": _lt("Your code is <b>{code}</b>. It works for ten minutes."),
		"outside": True,
		"required": True,
	},
]
