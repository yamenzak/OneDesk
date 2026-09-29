"""The owner's call: Gemini runs OneAI by default. The default for text
generation becomes Gemini 2.5 Flash where it is on sale, and a default from
another provider goes, so the actions that need pictures or sound fall to a
Gemini model too (actions.default_model)."""

import frappe

GEMINI = "google-ai-studio:gemini-2.5-flash"


def execute():
	on_sale = frappe.db.get_value("AI Model", GEMINI, ["offered", "status"], as_dict=True)
	if not on_sale or not on_sale.offered or on_sale.status != "Priced":
		return
	for name in frappe.get_all(
		"AI Model",
		filters={"default_for": ["is", "set"], "provider": ["!=", "google-ai-studio"]},
		pluck="name",
	):
		frappe.db.set_value("AI Model", name, "default_for", None, update_modified=False)
	if not frappe.db.exists("AI Model", {"default_for": "Text Generation"}):
		frappe.db.set_value("AI Model", GEMINI, "default_for", "Text Generation", update_modified=False)
