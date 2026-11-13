"""The two themes every presentation starts from, Light and Dark, taken from
Suite's fixtures (templates/system.json) and kept as they ship. AGENTS.md.
OneDeck needs nothing set up: a presentation is made in OneCloud.
"""

import json
from functools import cache
from pathlib import Path

import frappe

HERE = Path(__file__).parent / "templates" / "system.json"

STEPS = []


@cache
def system() -> list[dict]:
	return json.loads(HERE.read_text())


def themes() -> None:
	"""after_migrate: each theme in place and as it ships."""
	for one in system():
		fresh = not frappe.db.exists("Presentation", one["name"])
		doc = frappe.new_doc("Presentation") if fresh else frappe.get_doc("Presentation", one["name"])
		doc.update({key: one[key] for key in ("title", "slug", "theme")})
		doc.is_template = 1
		doc.set("slides", one["slides"])
		doc.flags.ignore_permissions = True
		if fresh:
			doc.insert(set_name=one["name"])
		else:
			doc.save()
