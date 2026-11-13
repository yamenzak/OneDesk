"""A spreadsheet's content: every sheet, its formats, comments and charts, as
one compressed blob. The File in OneCloud is what people see, move, share and
delete; this is only what it holds. AGENTS.md, api.py.
"""

from frappe.model.document import Document

from onedesk.one_cloud import editors


class Workbook(Document):
	def before_insert(self):
		editors.making(self)
