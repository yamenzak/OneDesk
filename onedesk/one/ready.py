"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under
`public/js/<folder>/` and `public/css/<folder>/`, and its screens under
`frontend/src/<screens>/`. OUTSIDE lists what still
sits elsewhere until it moves in; it only shrinks.
"""

import hashlib
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

# One is declared ready for production once every module is. Until then the
# agreements change freely (docs/READY.md, Before production).
PRODUCTION = False

MODULES = {
	"OneMail": {
		"folder": "one_mail",
		"screens": "mail",
		"names": ("one_mail", "onemail"),
		"ready": True,
		# The points a guard can't settle, each as a person last looked at it
		# (HAND).
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
		},
		# Its help pages in reading order, each with its icon (docs/).
		"help": (
			("overview", "info"),
			("your-addresses", "at-sign"),
			("reading-and-writing", "mail"),
			("connecting-a-mailbox", "plug"),
			("rules-and-out-of-office", "workflow"),
			("mail-on-records", "link"),
			("attachments-and-pictures", "paperclip"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneLegal": {
		"folder": "one_legal",
		"screens": "legal",
		"names": ("one_legal", "onelegal"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
		},
		# A module whose screen is a centre other modules open has no window,
		# so no foot or settings of its own; it says why (docs/READY.md, A
		# module with no window).
		"windowless": "TrustCenter is a dialog every module's foot opens, so OneLegal has no window, foot or settings of its own.",
		"help": (
			("overview", "info"),
			("agreeing", "file-check"),
			("optional-services", "toggle-right"),
			("changes", "history"),
			("who-can-do-what", "shield"),
		),
	},
	"OneAccount": {
		"folder": "one_account",
		"screens": "account",
		"names": ("one_account", "oneaccount"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "359b1fca3473", "by": "Claude, for Yamen"},
		},
		"windowless": "AccountCenter is a dialog the avatar's menu and links open, so OneAccount has no window, foot or settings of its own.",
		"help": (
			("overview", "info"),
			("your-account", "user"),
			("people-and-devices", "users"),
			("plan-and-credits", "credit-card"),
			("who-can-do-what", "shield"),
		),
	},
	"OneCalendar": {
		"folder": "one_calendar",
		"screens": "calendar",
		"names": ("one_calendar", "onecalendar"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "bfa493356848", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "bfa493356848", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "bfa493356848", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "bfa493356848", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "bfa493356848", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("calendars", "layers"),
			("events", "calendar-plus"),
			("deadlines", "alarm-clock"),
			("record-calendars", "folder-open"),
			("calendar-link", "link"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneTask": {
		"folder": "one_task",
		"screens": "task",
		"names": ("one_task", "onetask"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "837180a1818d", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "837180a1818d", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "837180a1818d", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "837180a1818d", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "837180a1818d", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("my-tasks", "list-checks"),
			("all-tasks", "circle-check"),
			("a-task", "file-text"),
			("timing", "timer"),
			("repeats-kinds-delays", "repeat"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneProject": {
		"folder": "one_project",
		"screens": "project",
		"names": ("one_project", "oneproject"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "88d62702eadc", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "88d62702eadc", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "88d62702eadc", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "88d62702eadc", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "88d62702eadc", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("projects", "folder-kanban"),
			("starting-a-project", "plus"),
			("a-projects-page", "layout-dashboard"),
			("tasks-and-schedule", "list-checks"),
			("time", "timer"),
			("billing", "receipt"),
			("costs-and-budget", "wallet"),
			("subcontracts", "hard-hat"),
			("sub-projects", "git-branch"),
			("the-team", "users"),
			("the-customer", "globe"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneInventory": {
		"folder": "one_inventory",
		"screens": "inventory",
		"names": ("one_inventory", "oneinventory"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("getting-ready", "list-checks"),
			("items", "package"),
			("an-items-page", "layout-dashboard"),
			("stock", "warehouse"),
			("buying", "shopping-cart"),
			("receiving-and-delivering", "truck"),
			("manufacturing", "factory"),
			("batches-and-quality", "layers"),
			("equipment", "wrench"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneBook": {
		"folder": "one_book",
		"screens": "books",
		"names": ("one_book", "onebook"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("home", "layout-dashboard"),
			("getting-ready", "list-checks"),
			("invoices", "receipt"),
			("payments", "banknote"),
			("the-bank", "landmark"),
			("journal-entries", "book-open"),
			("tax", "percent"),
			("closing", "lock"),
			("currencies", "coins"),
			("printing", "printer"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneCRM": {
		"folder": "one_crm",
		"screens": "crm",
		"names": ("one_crm", "onecrm"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("leads", "user-plus"),
			("next-step", "calendar-check"),
			("a-record-page", "layout-dashboard"),
			("home", "house"),
			("stages-and-pipeline", "kanban"),
			("quoting", "file-text"),
			("customers", "building-2"),
			("appointments-and-campaigns", "megaphone"),
			("support", "life-buoy"),
			("reports", "chart-bar"),
			("setup", "list-checks"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneDisplay": {
		"folder": "one_display",
		"screens": "display",
		"names": ("one_display", "onedisplay"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "840bb5083686", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("screens-and-pairing", "tv"),
			("channels", "radio"),
			("slides", "images"),
			("widgets-and-sources", "layout-dashboard"),
			("music-and-voice", "music"),
			("queues", "list-ordered"),
			("alerts", "siren"),
			("notifications", "bell"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneHR": {
		"folder": "one_hr",
		"screens": "hr",
		"names": ("one_hr", "onehr"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "2d2abb28732e", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("employees", "id-card"),
			("clocking-in", "clock"),
			("attendance", "calendar-check"),
			("leave", "plane"),
			("pay", "banknote"),
			("tax-and-benefits", "percent"),
			("expenses", "receipt"),
			("hiring", "user-plus"),
			("growth", "trending-up"),
			("joining-and-leaving", "door-open"),
			("setup", "list-checks"),
			("notifications", "bell"),
			("printing", "printer"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneSlide": {
		"folder": "one_slide",
		"screens": "slide",
		"names": ("one_slide", "oneslide"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "617254c5e56c", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "617254c5e56c", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "617254c5e56c", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "617254c5e56c", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "617254c5e56c", "by": "Claude, for Yamen"},
		},
		"windowless": "A presentation opens from OneCloud in an editor that fills the window, so OneSlide's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("working-on-slides", "presentation"),
			("design-and-layers", "layers"),
			("history-and-pdf", "history"),
			("presenting-by-link", "link"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OneWriter": {
		"folder": "one_doc",
		"screens": "writer",
		"names": ("one_doc", "onedoc"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "0abc825c1f8d", "by": "Claude, for Yamen"},
		},
		"windowless": "A document opens from OneCloud in an editor that fills the window, so OneWriter's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("writing", "pencil"),
			("writing-together", "users"),
			("history-and-templates", "history"),
			("printing-and-word", "printer"),
			("on-a-record", "link"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OneWorkbook": {
		"folder": "one_sheet",
		"screens": "sheet",
		"names": ("one_sheet", "onesheet"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "d4446016e786", "by": "Claude, for Yamen"},
		},
		"windowless": "A workbook opens from OneCloud in an editor that fills the window, so OneWorkbook's foot and settings are OneCloud's.",
		"help": (
			("overview", "info"),
			("working-in-a-workbook", "sheet"),
			("excel-and-csv", "file-spreadsheet"),
			("history-and-templates", "history"),
			("printing", "printer"),
			("a-records-table", "table"),
			("branded-sheets", "palette"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
		),
	},
	"OnePortal": {
		"folder": "one_portal",
		"screens": "portal",
		# Its own frappe-ui app, built apart from the islands (frontend/portal).
		"app": "portal",
		"names": ("one_portal", "oneportal"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-28", "commit": "6c558d9cdec3", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-28", "commit": "6c558d9cdec3", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-28", "commit": "6c558d9cdec3", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-28", "commit": "6c558d9cdec3", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-28", "commit": "6c558d9cdec3", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "globe"),
			("inviting", "user-plus"),
			("links", "link"),
			("what-they-see", "eye"),
			("who-can-do-what", "shield"),
		),
	},
	"One": {
		"folder": "one",
		"screens": "one",
		"names": ("one_control", "access_center", "notification_center", "role_matrix"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-29", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-29", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-29", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-29", "commit": "840bb5083686", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-29", "commit": "840bb5083686", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("home", "house"),
			("address-book", "book-user"),
			("announcements", "megaphone"),
			("records", "file-text"),
			("recycle-bin", "trash-2"),
			("notifications", "bell"),
			("access-and-the-audit-log", "shield-check"),
			("your-data", "folder-lock"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
	"OneAI": {
		"folder": "one_ai",
		"screens": "intake",
		"names": ("one_ai", "oneai"),
		"ready": True,
		"checked": {
			"copy": {"on": "2026-10-30", "commit": "55ab6de111c0", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-30", "commit": "55ab6de111c0", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-30", "commit": "55ab6de111c0", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-30", "commit": "55ab6de111c0", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-30", "commit": "55ab6de111c0", "by": "Claude, for Yamen"},
		},
		"help": (
			("overview", "info"),
			("asking-oneai", "sparkles"),
			("cards", "check-check"),
			("writing", "pencil"),
			("summaries", "notebook-text"),
			("reading", "inbox"),
			("finding", "search"),
			("remembers", "brain"),
			("web-search", "globe"),
			("tiers-and-credits", "coins"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
}

# The fourteen points a module is held to before it is marked ready
# (docs/READY.md, The fourteen points), in that order: what each is called,
# and the guards that hold every module to it on every run.
READY = "tests/guards/test_ready.py::"
POINTS = {
	"home": {
		"title": "One home",
		"guards": (
			READY + "test_nothing_of_a_module_is_left_outside",
			READY + "test_nothing_outside_a_module_is_named_for_it",
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
		),
	},
	"versioned": {
		"title": "Versioned",
		"guards": (
			READY + "test_every_change_to_a_module_is_a_version",
			READY + "test_versions_follow_one_another",
			READY + "test_a_version_is_written_for_the_people_using_it",
		),
	},
	"whats_new": {
		"title": "What's New in the app",
		"guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",),
	},
	"documented": {
		"title": "Documented",
		"guards": (
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
			READY + "test_every_help_page_is_listed_and_every_link_lands",
			READY + "test_a_help_page_names_no_code",
			READY + "test_a_help_page_is_headed_pictured_and_linked_soundly",
		),
	},
	"copy": {
		"title": "Copy",
		"guards": (
			"tests/guards/test_copy.py::test_a_heading_is_five_words_or_fewer",
			"tests/guards/test_copy.py::test_a_description_is_one_sentence",
			"tests/guards/test_copy.py::test_no_banned_word_is_shown",
		),
	},
	"roles": {
		"title": "Roles",
		"guards": (
			READY + "test_a_module_ships_its_roles",
			READY + "test_a_module_grants_through_abilities_alone",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"oneai": {
		"title": "OneAI",
		"guards": (READY + "test_a_module_reaches_every_change_through_oneai_or_says_why_not",),
	},
	"demo": {
		"title": "Demo and tests",
		"guards": (
			"tests/guards/test_coverage.py::test_no_module_has_more_left_to_cover_than_it_had",
			"tests/guards/test_demo.py::test_every_step_is_built_and_written_down",
		),
	},
	"notifications": {
		"title": "Notifications",
		"guards": (
			READY + "test_a_module_says_how_and_from_whom_it_tells_people",
			"tests/guards/test_notifications.py::test_every_type_sent_is_declared",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"interface": {"title": "OneInterface pass", "guards": ()},
	"setup": {"title": "Setup steps", "guards": (READY + "test_a_module_says_what_setting_it_up_takes",)},
	"tour": {"title": "Tour", "guards": (READY + "test_a_module_ships_a_tour_of_its_screen",)},
	"settings": {"title": "Settings", "guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",)},
	"legal": {
		"title": "Legal",
		"guards": (
			READY + "test_a_change_to_what_a_module_agrees_on_is_said",
			"tests/guards/test_legal.py::test_every_modules_legal_file_is_assembled",
		),
	},
}

# The points a guard holds only in part, and what a person looks at: before
# a module is marked ready, and again after a version that adds to it.
HAND = {
	"copy": "every heading, description and message it shows reads as the copy rules say, in English, Arabic and German",
	"demo": "the demo company uses every part of it and nothing in the demo makes it look wrong",
	"notifications": "it tells people what they need, on the channels that make sense, only to the roles that should hear it",
	"interface": "each screen, as each role, on a desktop and a phone: tokens only, frappe's controls, live where data changes, and the reader's formats",
	"legal": "what it does with data, read against what its clauses, subprocessors and optional services say",
}

# Files named for a module, or in its places, that are not its own, and why.
# A path ending in / is a whole folder. A module's files leave them out, so
# its version moves only with what is its own.
_ENGINE = "an engine every module uses, kept in One's folder"
_RAN = "OnePortal's, a patch that has run, kept at the path frappe recorded it under"
SHARED = {
	"brand/onemail.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/oneinventory.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecrm.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onehr.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_crm/business-card.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/business-card.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-ar.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry-de.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/enquiry.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_crm/order-from-lead.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/cv.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/sick-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/signed-contract.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt-doubted.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_hr/taxi-receipt.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onebook.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_inventory/coating-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/coating-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/delivery-note.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_inventory/supplier-quote.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement-2026-10-06.xml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/bank-statement.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/new-supplier-invoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/payment-advice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/supplier-einvoice.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_book/transport-contract.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneportal.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onecalendar.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onedisplay.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/oneslide.svg": "every product's mark is drawn in brand/, into one sprite",
	"docs/ONESLIDE.md": "the plan that made OneSlide and moved OneDisplay's slides into it, across both modules",
	"brand/onedoc.svg": "every product's mark is drawn in brand/, into one sprite",
	"brand/onesheet.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_calendar/site-meeting.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_calendar/site-meeting.json": "reading's samples sit with every module's, under tests/samples",
	"brand/onetask.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_task/drawings-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_task/drawings-request.json": "reading's samples sit with every module's, under tests/samples",
	"brand/oneproject.svg": "every product's mark is drawn in brand/, into one sprite",
	"tests/samples/intake/one_project/extra-work-request.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/extra-work-request.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/scaffolding-bill.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/site-log.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_project/subcontractor-timesheet.json": "reading's samples sit with every module's, under tests/samples",
	"onedesk/templates/emails/one_mail.html": "the frame every mail One sends is laid in, OneMail's or not",
	"brand/oneai.svg": "every product's mark is drawn in brand/, into one sprite",
	"onedesk/public/images/oneai.svg": "the mark as an image, for the places that can't use the sprite",
	"onedesk/one_mail/docs/asking-oneai.md": "OneMail's own Help page on what OneAI does in mail",
	"onedesk/one_mail/docs/asking-oneai/reading.png": "the picture on OneMail's page on OneAI",
	"tests/samples/intake/one_ai/ignore-instructions.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/ignore-instructions.json": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.eml": "reading's samples sit with every module's, under tests/samples",
	"tests/samples/intake/one_ai/locked-invoice.json": "reading's samples sit with every module's, under tests/samples",
	# The engines every module uses (docs/ONE.md, What One keeps).
	"onedesk/one/rights.py": _ENGINE + ": what a role may do in each module (docs/ROLES.md)",
	"onedesk/one/roles.py": _ENGINE + ": who administers the workspace",
	"onedesk/one/notify.py": _ENGINE + ": every notification goes through it",
	"onedesk/one/push.py": _ENGINE + ": every notification's push",
	"onedesk/one/doctype/push_device/": _ENGINE + ": the devices a push goes to",
	"onedesk/one/tell.py": _ENGINE + ": what every module tells people about the workspace goes through it",
	"onedesk/one/account.py": _ENGINE + ": every module asks the account through it",
	"onedesk/one/apps.py": _ENGINE + ": which apps the workspace has turned off, which every module asks",
	"onedesk/one/people.py": _ENGINE + ": the apps every person is given, which every module asks",
	"onedesk/one/head.py": _ENGINE + ": the record head every module's records wear",
	"onedesk/one/stages.py": _ENGINE + ": the record head's stages",
	"onedesk/one/figures.py": _ENGINE + ": the record head's figures",
	"onedesk/one/linked.py": _ENGINE + ": another record's fields edited on this one",
	"onedesk/one/tabs.py": _ENGINE + ": a record's tabs after its fields",
	"onedesk/one/homes.py": _ENGINE + ": where every module's record leads back to",
	"onedesk/one/doctype/record_head/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_band/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_chart/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_indicator/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_linked/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_sentence/": _ENGINE + ": the record head",
	"onedesk/one/doctype/record_head_verb/": _ENGINE + ": the record head",
	"onedesk/one/layer.py": _ENGINE + ": what a workspace may change about any module's forms",
	"onedesk/one/babel.py": _ENGINE + ": every module's standard records in the reader's language",
	"onedesk/one/doctype/workspace_customization/": _ENGINE + ": the workspace layer",
	"onedesk/one/boards.py": _ENGINE + ": the board every module's boards open in",
	"onedesk/one/sections.py": _ENGINE + ": what every centre's section is drawn from and saved to",
	"onedesk/one/print_format_field_template/": _ENGINE + ": the blocks every module's print formats are made of",
	"onedesk/one/ready.py": _ENGINE + ": the READY mechanisms (docs/READY.md)",
	"onedesk/one/versions.py": _ENGINE + ": the READY mechanisms, What's New",
	"onedesk/one/tours.py": _ENGINE + ": the READY mechanisms, tours",
	"onedesk/one/setup_steps.py": _ENGINE + ": the READY mechanisms, setup steps",
	"onedesk/one/setup_wizard.py": _ENGINE + ": the first run, which sets every module up",
	# What is in One's folder on its way to the module it belongs to.
	"onedesk/one/patches/portal_account_forms.py": _RAN,
	"onedesk/one/patches/portal_address_button.py": _RAN,
	"onedesk/one/patches/portal_own_by_record.py": _RAN,
	"onedesk/one/patches/portal_settle.py": _RAN,
	"onedesk/one/privacy.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/privacy_copy.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/privacy_public.py": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/custom/personal_data_deletion_request.json": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/custom/personal_data_download_request.json": "TrustCenter's Your Data, OneLegal's, to move into one_legal",
	"onedesk/one/webhooks.py": "OneStudio's Webhooks, to move into one_studio",
	"onedesk/one/patches/holiday_names.py": "OneHR's holidays, a patch that has run",
}


def shared(path: str) -> bool:
	"""Whether a path, from the repository's root, is in SHARED."""
	return path in SHARED or any(key.endswith("/") and path.startswith(key) for key in SHARED)


OUTSIDE = {
	"OneCRM": [],
	"OneHR": [],
	"OneMail": [],
	"One": [],
	"OneAI": [],
	"OneLegal": [],
	"OneAccount": [],
	"OnePortal": [],
	"OneInventory": [],
	"OneBook": [],
	"OneDisplay": [],
	"OneSlide": [],
	"OneWriter": [],
	"OneWorkbook": [],
}


def files(module: str) -> list[Path]:
	"""Every file of a module: its folder, its static files, its screens, and
	what still sits outside."""
	found = []
	for root in places(module):
		if root.exists():
			found += [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
	found = [path for path in found if not shared(str(path.relative_to(ROOT)))]
	found += [ROOT / one for one in OUTSIDE.get(module, [])]
	return sorted(found)


def places(module: str) -> list[Path]:
	"""Where a module's files may be: its folder, its static folders and its
	screens."""
	spec = MODULES[module]
	return [
		APP / spec["folder"],
		APP / "public" / "js" / spec["folder"],
		APP / "public" / "css" / spec["folder"],
		ROOT / "frontend" / "src" / spec["screens"],
	] + ([ROOT / "frontend" / spec["app"]] if spec.get("app") else [])


# What a version is taken over: what the module ships and its help pages,
# not what only we read or run (AGENTS.md, SCRATCHPAD.md, its versions, its
# tests, its checks and its part of the demo).
UNSHIPPED = ("AGENTS.md", "SCRATCHPAD.md", "checks.py", "demo.py")
KINDS = ("major", "minor", "fix")
HEAD = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def shipped(module: str) -> list[Path]:
	"""The files a module's version is taken over."""
	return [
		path
		for path in files(module)
		if path.name not in UNSHIPPED
		and "tests" not in path.parts
		and "changelog" not in path.parts
		and path.suffix not in (".pyc",)
	]


def fingerprint(module: str) -> str:
	"""Twelve hex characters over every shipped file's path and bytes, so it
	moves with any change to the module and nothing else."""
	digest = hashlib.sha256()
	for path in shipped(module):
		digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
	return digest.hexdigest()[:12]


def changelog(module: str) -> Path:
	return APP / MODULES[module]["folder"] / "docs" / "changelog"


def number(version: str) -> tuple[int, int, int]:
	major, minor, fix = (int(one) for one in version.split("."))
	return major, minor, fix


def versions(module: str) -> list[dict]:
	"""Every version of a module, newest first: its front matter (version,
	date, kind, title, fingerprint) and its words, read from
	docs/changelog/<version>.md."""
	found = []
	for path in changelog(module).glob("*.md"):
		text = path.read_text(encoding="utf-8")
		head = HEAD.match(text)
		if not head:
			raise ValueError(f"{path} has no front matter")
		said = dict(line.split(": ", 1) for line in head.group(1).splitlines())
		said["docs"] = [one.strip() for one in said.get("docs", "").split(",") if one.strip()]
		found.append({**said, "version": path.stem, "body": text[head.end() :].strip(), "path": path})
	return sorted(found, key=lambda one: number(one["version"]), reverse=True)


def legal(module: str) -> str:
	"""What a module agrees on, as a version of it records it
	(one_legal/assemble.py `stamp`)."""
	from onedesk.one_legal import assemble

	return assemble.stamp(module)


def current(module: str) -> str | None:
	"""A module's version: its newest changelog entry's."""
	found = versions(module)
	return found[0]["version"] if found else None


def help_pages(module: str) -> list[dict]:
	"""A module's help pages in reading order: id, icon, title (its first
	heading), the rest of its words, and where it is, which its pictures sit
	beside."""
	folder = APP / MODULES[module]["folder"] / "docs"
	found = []
	for page, icon in MODULES[module].get("help", ()):
		text = (folder / f"{page}.md").read_text(encoding="utf-8")
		title, _, body = text.partition("\n")
		found.append(
			{"id": page, "icon": icon, "title": title.lstrip("# ").strip(), "body": body.strip(), "path": folder / f"{page}.md"}
		)
	return found


def registry(module: str) -> list[dict]:
	"""Where a module stands on each point: the guards that hold it, and, for
	a point a person must look at, when they last did."""
	checked = MODULES[module].get("checked", {})
	return [
		{
			"point": key,
			"title": point["title"],
			"guards": point["guards"],
			"look": HAND.get(key),
			"checked": checked.get(key),
		}
		for key, point in POINTS.items()
	]
