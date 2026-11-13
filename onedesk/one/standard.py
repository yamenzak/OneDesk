"""The standard every module and screen of One is held to (docs/STANDARD.md),
as one numbered list. Pure, so the guards, OneLint and ready.py all read it.

A point says its group, whether a module is held to it before it is marked
ready (`live`), and, where no rule can settle it, what a person looks at
(`look`). The rules that hold each point are tests/guards/registry.py's
GUARDS, each naming its point by number.
"""

from typing import NamedTuple


class Point(NamedTuple):
	number: int
	key: str
	title: str
	group: str
	live: bool = False
	look: str = ""


GROUPS = ("Works", "Stays desk", "Speaks", "Knows", "Rules")

POINTS = {
	point.number: point
	for point in (
		Point(
			1,
			"demo",
			"Demo and tests",
			"Works",
			live=True,
			look="the demo company uses every part of it and nothing in the demo makes it look wrong",
		),
		Point(2, "rules", "Rules on the server", "Works"),
		Point(3, "handoffs", "Hand-offs", "Works"),
		Point(4, "erpnext", "What ERPNext already does", "Works"),
		Point(5, "settings", "Settings and setup", "Works", live=True),
		Point(6, "tiers", "Tier declared", "Stays desk"),
		Point(
			7,
			"interface",
			"Our look",
			"Stays desk",
			live=True,
			look="each screen, as each role, on a desktop and a phone: tokens only, frappe's controls, live where data changes, and the reader's formats",
		),
		Point(8, "kept", "Nothing lost, and extensible", "Stays desk"),
		Point(9, "frappe", "Built from frappe", "Stays desk"),
		Point(10, "overrides", "Overrides recorded", "Stays desk"),
		Point(
			11,
			"notifications",
			"Notifications",
			"Speaks",
			live=True,
			look="it tells people what they need, on the channels that make sense, only to the roles that should hear it",
		),
		Point(12, "printed", "Printed", "Speaks"),
		Point(
			13,
			"copy",
			"Plain words",
			"Speaks",
			live=True,
			look="every heading, description and message it shows reads as the copy rules say, in English, Arabic and German",
		),
		Point(14, "documented", "Documented, with Help and a tour", "Knows", live=True),
		Point(15, "versioned", "Versioned, with What's New", "Knows", live=True),
		Point(16, "oneai", "OneAI knows and does", "Knows", live=True),
		Point(17, "intake", "Intake", "Knows"),
		Point(18, "roles", "Permissions and roles", "Rules", live=True),
		Point(
			19,
			"legal",
			"Legal",
			"Rules",
			live=True,
			look="what it does with data, read against what its clauses, subprocessors and optional services say",
		),
		Point(20, "home", "One home, clean code", "Rules", live=True),
	)
}

