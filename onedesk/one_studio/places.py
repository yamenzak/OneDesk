"""The pages of One an extension may run on, beyond frappe's forms and lists:
what happens on each (its events), what each event gives, and what an
extension may do there.
"""

from onedesk.one.registry.model import _lt


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
		"record": None,
		"events": {
			"drawn": {
				"about": _lt("A record's head is drawn on its form: each time the record is opened or saved."),
				"gives": "record: the record's fields the person may read, as on the form (record.name, record.status…)",
				"may": ("verb", "figure", "note"),
			},
		},
	},
	"oneinventory_item": {
		"label": "OneInventory",
		"record": "Item",
		"events": {
			"stock": {
				"about": _lt("An item's Stock view is opened, and each time its stock changes."),
				"gives": "item.name, item.item_name, stock.places (how many warehouses), stock.low_in (warehouses by name), stock.moves (how many shown)",
				"may": ("note", "action"),
			},
			"buying": {
				"about": _lt("An item's Buying view is opened."),
				"gives": "item.name, item.item_name, buying.suppliers (names), buying.orders (how many open), buying.late (how many late), buying.quotes (how many open)",
				"may": ("note", "action"),
			},
			"selling": {
				"about": _lt("An item's Selling view is opened."),
				"gives": "item.name, item.item_name, selling.orders (how many open), selling.late (how many late), selling.short (how many short of stock), selling.quotes (how many open), selling.customers (names)",
				"may": ("note", "action"),
			},
			"making": {
				"about": _lt("An item's Making view is opened."),
				"gives": "item.name, item.item_name, making.bom (the default bill of materials), making.orders (how many open), making.can_make (how many the free stock would make), making.runs_out_first (the material that limits it)",
				"may": ("note", "action"),
			},
		},
	},
	"oneinventory_stock": {
		"label": "OneInventory",
		"record": "Bin",
		"events": {
			"on_hand": {
				"about": _lt("Stock on Hand is opened, and each time stock moves or another warehouse is chosen."),
				"gives": "stock.warehouse (or null for every one), stock.worth, stock.items (how many), stock.low (item codes), stock.short (item codes)",
				"may": ("note", "action"),
			},
		},
	},
	"onefactory_floor": {
		"label": "OneFactory",
		"record": "Job Card",
		"events": {
			"shown": {
				"about": _lt("Shop Floor is opened, and each time a step starts, pauses or closes."),
				"gives": "floor.open (work orders open), floor.running (steps someone is on), floor.waiting (steps not started), floor.done_today (steps closed today), floor.work_order (the one open, or null), floor.workstation (the one shown, or null)",
				"may": ("note", "action"),
			},
		},
	},
	"onequality_home": {
		"label": "OneQuality",
		"record": "Non Conformance",
		"events": {
			"shown": {
				"about": _lt("OneQuality's Home is opened, and each time a non conformance, an action, a review or a meeting changes."),
				"gives": "home.problems (non conformances open), home.late (action steps past their day), home.failing (goals whose last review failed), home.meetings (meetings still open)",
				"may": ("note", "action"),
			},
		},
	},
	"onefactory_home": {
		"label": "OneFactory",
		"record": "Work Order",
		"events": {
			"shown": {
				"about": _lt("OneFactory's Home is opened, and each time a work order, a step or a subcontracting order changes."),
				"gives": "home.late (work orders past the day they were wanted), home.start (work orders due to have started), home.back (work late back from suppliers), home.drafts (drafts left)",
				"may": ("note", "action"),
			},
		},
	},
	"oneinventory_home": {
		"label": "OneInventory",
		"record": "Item",
		"events": {
			"shown": {
				"about": _lt("OneInventory's Home is opened, and each time an order, a move, a lot or a service changes."),
				"gives": "home.worth (stock worth, or null), home.low (items running low), home.late (orders late), home.going_off (lots going off), home.services (services due this week), home.work (work orders late), home.drafts (drafts left)",
				"may": ("note", "action"),
			},
		},
	},
	"onecrm_home": {
		"label": "OneCRM",
		"record": "Opportunity",
		"events": {
			"shown": {
				"about": _lt("OneCRM's Home is opened, and each time a lead, an opportunity or a quotation changes."),
				"gives": "home.due (next steps due today or late), home.closing (opportunities past their closing date), home.unclaimed (leads nobody has taken), home.expiring (quotations running out this week), home.unplanned (open with no next step), home.drafts (drafts left)",
				"may": ("note", "action"),
			},
		},
	},
	"onehr_home": {
		"label": "OneHR",
		"record": "Employee",
		"events": {
			"shown": {
				"about": _lt("OneHR's Home is opened, and each time a request, a flagged check-in or an interview changes."),
				"gives": "home.mine (the reader's own requests waiting), home.approve (requests waiting on the reader), home.flagged (check-ins flagged), home.expiring (documents expiring within a month), home.ending (contracts or probations ending within a month), home.interviews (interviews today)",
				"may": ("note", "action"),
			},
		},
	},
	"onebook_home": {
		"label": "OneBook",
		"record": "Sales Invoice",
		"events": {
			"shown": {
				"about": _lt("OneBook's Home is opened, and each time an invoice, a payment or a bank line changes."),
				"gives": "home.overdue (sales invoices overdue), home.bills (purchase invoices due this week or late), home.bank (bank lines to reconcile), home.drafts (drafts left)",
				"may": ("note", "action"),
			},
		},
	},
	"oneinventory_order": {
		"label": "OneInventory",
		"record": "Material Request",
		"events": {
			"shown": {
				"about": _lt("To Order is opened, and each time a request, a purchase order or stock changes."),
				"gives": "order.lines (how many), order.requested, order.low, order.cost (at the last prices), order.unpriced (lines with no price yet)",
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
		"label": "Documents",
		"record": "Reading",
		"events": {
			"reading": {
				"about": _lt("A document is opened in Documents."),
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
		"record": "Workspace",
		"events": {
			"home": {
				"about": _lt("A space's home page is opened: One, OneCRM, OneHR, OneBook and every other."),
				"gives": "space.name (the Workspace, such as OneHR), space.title",
				"may": ("note", "action"),
			},
		},
	},
	"oneproject": {
		"label": "OneProject",
		"record": "Project",
		"events": {
			"overview": {
				"about": _lt("A project's Overview is opened, and each time its figures change."),
				"gives": (
					"project.name, project.title, project.kind, project.currency, overview.figures (each card's "
					"figure by its key, such as contract, billed, cost, margin, due), overview.needs (what needs "
					"someone, as it reads), overview.needs_count"
				),
				"may": ("note", "action"),
			},
			"time": {
				"about": _lt("A project's Time view is opened, and each time its hours change."),
				"gives": (
					"project.name, project.title, project.customer, time.entries, time.hours, time.planned, "
					"time.month, time.drafts (hours not submitted), time.allowance (a retainer's hours a month)"
				),
				"may": ("note", "action"),
			},
			"money": {
				"about": _lt("A project's Money view is opened, and each time its figures change."),
				"gives": (
					"project.name, project.title, project.kind, project.currency, money.contract, money.invoiced, "
					"money.spent, money.budget, money.forecast_cost, money.forecast_margin, money.cost_types "
					"(each with cost_type, budget, committed, spent and left)"
				),
				"may": ("note", "action"),
			},
			"invoices": {
				"about": _lt("A project's Invoices view is opened, and each time its invoices change."),
				"gives": (
					"project.name, project.title, project.kind, project.customer, project.currency, invoices.count, "
					"invoices.invoiced, invoices.paid, invoices.outstanding, invoices.overdue, invoices.late (how many "
					"are late), invoices.retention, invoices.drafts, invoices.advance"
				),
				"may": ("note", "action"),
			},
			"suppliers": {
				"about": _lt("A project's Suppliers view is opened, and each time what it buys changes."),
				"gives": (
					"project.name, project.title, project.kind, project.currency, suppliers.count, "
					"suppliers.subcontracts, suppliers.ordered, suppliers.to_pay, suppliers.overdue, suppliers.retention"
				),
				"may": ("note", "action"),
			},
			"team": {
				"about": _lt("A project's Team view is opened, and each time its team changes."),
				"gives": "project.name, team.people (how many), team.contacts (how many outside the company)",
				"may": ("note", "action"),
			},
		},
	},
	"oneproject_list": {
		"label": "OneProject",
		"record": None,
		"events": {
			"projects": {
				"about": _lt("The Projects list is opened, and each time it is drawn again."),
				"gives": (
					"projects.count, projects.rows: each project's name, title, status, health (open ones only), "
					"kind, customer, ends and percent_complete, as the list shows them to the reader"
				),
				"may": ("note", "action"),
			},
		},
	},
	"oneproject_workload": {
		"label": "OneProject",
		"record": None,
		"events": {
			"week": {
				"about": _lt("Workload is opened, and each time it is drawn again."),
				"gives": (
					"week.week (the day picked), week.project, week.said (the week it covers), week.people: "
					"each user, name, capacity, planned, free, load (%), tasks, late, not_estimated"
				),
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
