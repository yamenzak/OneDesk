"""A spreadsheet's content: every sheet, its formats, comments and charts, as
one compressed blob. The File in OneCloud is what people see, move, share and
delete; this is only what it holds. AGENTS.md, api.py.
"""

from frappe.model.document import Document


class Workbook(Document):
	pass
