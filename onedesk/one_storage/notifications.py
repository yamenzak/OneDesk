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
		"about": _lt("When someone shares a file or folder with you."),
		"to": _lt("The person it's shared with"),
		"subject": _lt("{who} shared {file} with you"),
	},
	# library: somebody added to a library.
	{
		"name": _lt("Added to a Library"),
		"app": "OneCloud",
		"about": _lt("When someone adds you to a library."),
		"to": _lt("The person added"),
		"subject": _lt("{who} added you to the library {library}"),
	},
	# file_requests: what came back for a file request.
	{
		"name": _lt("File Request Answered"),
		"app": "OneCloud",
		"about": _lt("When someone sends a file you requested."),
		"to": _lt("Whoever asked"),
		"subject": _lt("{sender} sent {item} for {request}"),
	},
	{
		"name": _lt("File Request Complete"),
		"app": "OneCloud",
		"about": _lt("When someone sends all the files you requested."),
		"to": _lt("Whoever asked"),
		"subject": _lt("{sender} sent everything for {request}"),
		"email_default": True,
	},
	# links: files that arrived through an upload link.
	{
		"name": _lt("Arrived Through a Link"),
		"app": "OneCloud",
		"about": _lt("When someone uploads files through a link you created."),
		"to": _lt("The person who created the link"),
		"subject": _lt("{count} files uploaded to {folder}"),
	},
	{
		"name": _lt("Arrived Through a Link, One File"),
		"app": "OneCloud",
		"about": _lt("When someone uploads one file through a link you created."),
		"to": _lt("The person who created the link"),
		"follows": "Arrived Through a Link",
		"subject": _lt("{file} uploaded to {folder}"),
	},
	# file_requests: the mail to the people asked.
	{
		"name": _lt("File Request"),
		"app": "OneCloud",
		"about": _lt("When a file request is sent."),
		"to": _lt("Each recipient"),
		"subject": _lt("{who} requested files for {request}"),
		"message": _lt(
			'<b>{who}</b> requested files for <b>{request}</b>.{note}{due}<br><br><a href="{link}">Upload Files</a>'
		),
		"outside": True,
	},
	{
		"name": _lt("File Request Reminder"),
		"app": "OneCloud",
		"about": _lt("Before a file request is due, or when its owner sends a reminder."),
		"to": _lt("Recipients who haven't sent everything"),
		"subject": _lt("Reminder: {who} requested files for {request}"),
		"message": _lt(
			'<b>{who}</b> is still waiting for files for <b>{request}</b>.<br><br><a href="{link}">Upload Files</a>'
		),
		"outside": True,
	},
	# links: the mail to each invited address.
	{
		"name": _lt("Link Shared"),
		"app": "OneCloud",
		"about": _lt("When a link is shared with an email address."),
		"to": _lt("Each invited address"),
		"subject": _lt("{who} shared {file} with you"),
		"message": _lt(
			'{who} shared {file} with you.<br><br><a href="{link}">Open</a><br><br>'
			"You'll get a sign-in code at this address when you open it."
		),
		"outside": True,
	},
	{
		"name": _lt("Link Code"),
		"app": "OneCloud",
		"about": _lt("When an invited address opens a shared link. It can't be turned off."),
		"to": _lt("The invited address"),
		"subject": _lt("Your code for {file}"),
		"message": _lt("Your code is <b>{code}</b>. It expires in 10 minutes."),
		"outside": True,
		"required": True,
	},
]
