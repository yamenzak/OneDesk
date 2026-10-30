"""What OneSlide tells people, and when (its kinds are in
notifications/one_storage, beside OneCloud's own, until OneSlide is a module
of its own)."""

import frappe

from onedesk.one import notify


def video(asker: str, name: str, what: str, failed: bool = False) -> None:
	"""A video OneAI made for a presentation is on its last slide, or could
	not be made."""
	notify.notify(
		"Video Not Made for a Presentation" if failed else "Video Made for a Presentation",
		asker,
		record=("Presentation", name),
		link=f"/desk/presentation/{name}",
		what=what,
		presentation=frappe.db.get_value("Presentation", name, "title") or name,
	)
