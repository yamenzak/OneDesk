from frappe import _
from frappe.model.document import Document


class DisplayBoard(Document):
	def validate(self):
		"""Items and states named once each; an item in a state the board no
		longer has is left without one."""
		import frappe

		for rows, field, what in ((self.items, "item_name", _("item")), (self.states, "state", _("state"))):
			seen = set()
			for row in rows:
				name = (row.get(field) or "").strip()
				row.set(field, name)
				if name in seen:
					frappe.throw(_("{0} is named twice. Each {1} needs its own name.").format(name, what))
				seen.add(name)
		states = {row.state for row in self.states}
		for row in self.items:
			if row.state and row.state not in states:
				row.state = None
