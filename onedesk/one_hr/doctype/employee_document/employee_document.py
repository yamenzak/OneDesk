"""One identity document an employee holds: a passport, a visa, a licence.

Replaces erpnext's four flat passport fields, which can hold one document and
cannot say when it runs out. The type is HRMS's own `Identification Document
Type` rather than a list of ours — it already exists, `Travel Request` already
links to it, and which documents a country cares about is a thing a workplace
adds a row to.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class EmployeeDocument(Document):
	def validate(self):
		if self.issued_on and self.expires_on and getdate(self.expires_on) < getdate(self.issued_on):
			frappe.throw(
				_("Row {0}: {1} expires before it was issued.").format(self.idx, self.document_type)
			)
