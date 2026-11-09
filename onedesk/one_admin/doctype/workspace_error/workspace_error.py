"""A kind of error one workspace has had, from its own Error Log. Written by
errors.heard; an operator may mark it Fixed, and it opens again if it returns."""

from frappe.model.document import Document


class WorkspaceError(Document):
	pass
