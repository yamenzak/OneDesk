"""One step of a signup's setup wizard reached, finished, skipped or left,
with when (one_admin/wizard.py); OneAdmin's Home counts them."""

from frappe.model.document import Document


class AccountRequestStep(Document):
	pass
