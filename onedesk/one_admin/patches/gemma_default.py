"""The owner's call, for testing at a fraction of the price: Gemma 4 runs
OneAI's text by default, where it is on sale. It replaces Gemini 2.5 Flash as
the default for text generation (patches.gemini_default); an action that needs
pictures or sound still falls to a model that reads them
(actions.default_model). Found in the catalogue rather than named: only
gateway.FIRST names a model in code."""

import frappe


def execute():
	gemma = frappe.get_all(
		"AI Model",
		filters={
			"model": ["like", "%gemma-4-26b-a4b%"],
			"capability": "Text Generation",
			"offered": 1,
			"status": "Priced",
		},
		order_by="provider asc",
		pluck="name",
		limit=1,
	)
	if not gemma:
		return
	for name in frappe.get_all("AI Model", filters={"default_for": "Text Generation"}, pluck="name"):
		frappe.db.set_value("AI Model", name, "default_for", None, update_modified=False)
	frappe.db.set_value("AI Model", gemma[0], "default_for", "Text Generation", update_modified=False)
