"""An automation: a trigger, then steps (one/automation/flow.py), kept by the
app whose trigger starts it (one/automation/kinds.py)."""

import frappe
from frappe import _
from frappe.model.document import Document


class Automation(Document):
	def validate(self):
		from onedesk.one.automation import engine, kinds

		trigger = kinds.trigger(self.trigger)
		self.scope_type = trigger.scope
		steps = self.steps_of()
		said = engine.problems(self.trigger, steps)
		if said:
			frappe.throw(said[0])
		trigger.keeper("validate")(self, steps)
		self.steps = frappe.as_json(steps, indent=None)
		self.title = (self.title or "").strip() or _("Automation")

	def steps_of(self) -> list:
		from onedesk.one.automation import engine

		return engine.steps_of(self)
