"""What OneTask tells people, as notification types (one/notify.py).

Sent by `tell.py`. A task given to somebody is frappe's own assignment line,
said in ours as it is written (`given`); a task done is told to whoever gave
it; and each morning a person hears what is due that day and what is late.
"""

from frappe import _lt

TYPES = [
	{
		"name": _lt("Task Given"),
		"app": "OneTask",
		"about": _lt("When somebody gives you a task."),
		"to": _lt("Each person given it, but whoever gave it"),
		"subject": _lt("{who} gave you {task}"),
		"message": _lt("<b>{task}</b>{due}{project}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Task Done"),
		"app": "OneTask",
		"about": _lt("When somebody else completes a task you gave them or made."),
		"to": _lt("Whoever gave the task and whoever made it, but whoever completed it"),
		"subject": _lt("{who} completed {task}"),
		"message": _lt("<b>{task}</b>{project} is done."),
		"push_default": True,
	},
	{
		"name": _lt("Today's Tasks"),
		"app": "OneTask",
		"about": _lt(
			"Every morning, what is due that day and what is late. Not sent on a day with nothing due."
		),
		"to": _lt("Each person, for the tasks given to them"),
		"subject": _lt("{count} to do today"),
		"message": _lt("{tasks}"),
		"email_default": True,
	},
]
