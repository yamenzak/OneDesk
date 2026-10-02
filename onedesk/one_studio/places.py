"""The pages of One an extension may run on, beyond frappe's forms and lists.

A frappe Client Script reaches a kind of record's form and its list, and
nothing else: OneMail, OneCalendar, OneTask, OneCloud, OneIntake, the pipeline
board, every space's home and the head of a record are One's own, drawn by
One's code. So each of those says here, once, what happens on it
that an extension may hear (its events), what each event tells the
extension (`gives`), and the few things the extension may do there (`may`).

This is the whole contract. The browser runs only these events with only
these powers (public/js/places.js); guard.py refuses code that listens for
an event the page does not have; and OneAI reads it to know what each page
allows (one_studio/ai.py `extension_places`), so what it writes and what
runs are the same list.
"""


def _lt(text: str) -> str:
	"""Marks a string for translation where it is written; it is translated
	where it is shown (extensions._place_said). Pure."""
	return text


#: What an extension may do on a page, said the way OneAI reads it.
POWERS = {
	"note": "page.note(text, tone): a line of text shown on the page; tone is gray, blue, green, orange or red.",
	"action": "page.action(label, handler): a button; handler() runs when it is pressed.",
	"verb": "page.verb(label, handler): a button in the record's head, beside its own verbs.",
	"figure": "page.figure(label, value): a figure in the record's head, beside its own.",
	"set": "page.set(field, value): fills subject, cc or bcc in the message being written.",
}

PLACES = {
	"onemail": {
		"label": "OneMail",
		# The kind of record what happens here is about, for the list, the
		# review and the guard's permission check.
		"record": "Communication",
		"events": {
			"conversation": {
				"about": _lt("A conversation is opened in OneMail's reading pane."),
				"gives": (
					"mail.subject; mail.mailbox (the address being read); mail.folder (Inbox, Sent…); "
					"mail.messages, oldest first, each with sender, sender_full_name, recipients, cc, subject, "
					"date, sent_or_received (Sent or Received), has_attachment, reference_doctype, reference_name"
				),
				"may": ("note", "action"),
			},
			"compose": {
				"about": _lt("A message is being written anywhere in One: new, a reply or a forward."),
				"gives": "mail.recipients, mail.cc, mail.subject, mail.reply (true for a reply), mail.reference_doctype, mail.reference_name",
				"may": ("note", "set"),
			},
		},
	},
	"record_head": {
		"label": _lt("Record Head"),
		# The kind of record is the extension's own: it runs on that kind's head.
		"record": None,
		"events": {
			"drawn": {
				"about": _lt("A record's head is drawn on its form: each time the record is opened or saved."),
				"gives": "record: the record's fields the person may read, as on the form (record.name, record.status…)",
				"may": ("verb", "figure", "note"),
			},
		},
	},
	"onetask": {
		"label": "OneTask",
		"record": "Task",
		"events": {
			"listed": {
				"about": _lt("OneTask shows one of its views of the reader's tasks."),
				"gives": (
					"tasks.view (mine or inbox); tasks.groups, each with key (overdue, today, week, later, someday), "
					"label and tasks, each with name, subject, priority, due, project, project_title, is_milestone"
				),
				"may": ("note", "action"),
			},
		},
	},
	"onecloud": {
		"label": "OneCloud",
		"record": "File",
		"events": {
			"file": {
				"about": _lt("A file is chosen in OneCloud and its preview is shown."),
				"gives": (
					"file.name, file.type, file.size (bytes), file.modified, file.folder (where it is), file.owner, "
					"file.record ([doctype, name] it is filed on, or null)"
				),
				"may": ("note", "action"),
			},
		},
	},
	"intake": {
		"label": "OneIntake",
		"record": "Reading",
		"events": {
			"reading": {
				"about": _lt("A document is opened in OneIntake's inbox."),
				"gives": (
					"reading.name, reading.title, reading.kind, reading.person, reading.summary, reading.route, "
					"reading.actions, each with said, level (Done, Proposed or Refused) and record ([doctype, name] or null)"
				),
				"may": ("note", "action"),
			},
		},
	},
	"onecrm": {
		"label": "OneCRM",
		"record": "Opportunity",
		"events": {
			"board": {
				"about": _lt("The pipeline board is drawn, and each time what a stage is worth changes."),
				"gives": "board.currency; board.stages, by stage name, each with value and weighted",
				"may": ("note",),
			},
		},
	},
	"space": {
		"label": _lt("Space Home"),
		# A space's home is a frappe Workspace; nothing of it is a record.
		"record": "Workspace",
		"events": {
			"home": {
				"about": _lt("A space's home page is opened: One, OneCRM, OneHR, OneBook and every other."),
				"gives": "space.name (the Workspace, such as OneHR), space.title",
				"may": ("note", "action"),
			},
		},
	},
	"onecalendar": {
		"label": "OneCalendar",
		"record": "Event",
		"events": {
			"event": {
				"about": _lt("An event's card is opened in OneCalendar."),
				"gives": (
					"event.name, event.subject, event.starts_on, event.ends_on, event.all_day, event.location, "
					"event.description, event.people (each with name, email, answer), "
					"event.about (the record it is about, [doctype, name], or null)"
				),
				"may": ("note", "action"),
			},
		},
	},
}


def place_of(key: str | None) -> tuple[str, str] | None:
	"""`onemail.conversation` as (place, event), when both are known. Pure."""
	place, _dot, event = (key or "").partition(".")
	if place in PLACES and event in PLACES[place]["events"]:
		return place, event
	return None


def keys() -> list[str]:
	"""Every place.event an extension may be written for. Pure."""
	return [f"{place}.{event}" for place, one in PLACES.items() for event in one["events"]]


def doctype_for(key: str, chosen: str | None) -> str | None:
	"""The kind of record an extension on this place is about: the page's own,
	or for the head the one asked for. Pure."""
	found = place_of(key)
	if not found:
		return None
	return PLACES[found[0]]["record"] or chosen


def described() -> list[dict]:
	"""Every place, as OneAI reads it. Pure."""
	return [
		{
			"place": f"{place}.{event}",
			"page": one["label"],
			"when": said["about"],
			"gives": said["gives"],
			"may": [POWERS[power] for power in said["may"]],
			"record": one["record"] or "the kind of record you name",
		}
		for place, one in PLACES.items()
		for event, said in one["events"].items()
	]


def for_boot() -> dict:
	"""What the browser needs to run them: each place's events and powers."""
	return {
		place: {event: list(said["may"]) for event, said in one["events"].items()}
		for place, one in PLACES.items()
	}
