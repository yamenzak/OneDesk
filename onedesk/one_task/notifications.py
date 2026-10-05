"""What OneTask tells people, as notification types (one/notify.py).

Sent by `tell.py`. A task given to somebody is frappe's own assignment line,
said in ours as it is written (`given`); a task done is told to whoever gave
it; a task whose last dependency is done, sent for review or given a new due
date is told to its people (`changed`); and each morning a person hears what
is due that day and what is late.
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
		"name": _lt("Task Ready"),
		"app": "OneTask",
		"about": _lt("When the last task a task waits on is done."),
		"to": _lt("Each person given the task, or whoever made it, but whoever completed the last one"),
		"subject": _lt("{task} is ready"),
		"message": _lt("<b>{task}</b>{due}{project}<br>{done} is done."),
		"push_default": True,
	},
	{
		"name": _lt("Pending Review"),
		"app": "OneTask",
		"about": _lt("When somebody marks a task Pending Review."),
		"to": _lt("Whoever gave the task and whoever made it, but whoever marked it"),
		"subject": _lt("{who} asked you to review {task}"),
		"message": _lt("<b>{task}</b>{due}{project}"),
		"email_default": True,
		"push_default": True,
	},
	{
		"name": _lt("Due Date Changed"),
		"app": "OneTask",
		"about": _lt("When somebody changes the due date of a task given to you."),
		"to": _lt("Each person given the task, but whoever changed it"),
		"subject": _lt("{who} moved {task} to {due}"),
		"message": _lt("<b>{task}</b>{was}{project}"),
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
