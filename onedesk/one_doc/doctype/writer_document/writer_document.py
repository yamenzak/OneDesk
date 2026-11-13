"""A document's content: the editor's Yjs state, the same document as HTML,
its page setup and its comments. The File in OneCloud is what people see,
move, share and delete; this is only what it holds. AGENTS.md, api.py.
"""

from frappe.model.document import Document

from onedesk.one_cloud import editors


class WriterDocument(Document):
	def before_insert(self):
		editors.making(self)
