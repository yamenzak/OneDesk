"""A row of a doctype's customization that the workspace made: a custom field
or a property setter, which frappe does not otherwise tell from ours. Reset
removes what these name. See one/customize.py."""

from frappe.model.document import Document


class WorkspaceCustomization(Document):
	pass
