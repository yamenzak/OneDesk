import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one import news
from onedesk.one.news import fetching


class NewsItem(Document):
	def validate(self):
		self.written = int(news.written(self.source))
		if self.is_new() and not self.flags.from_source and not self.written:
			frappe.throw(_("You can only add items to a Written source. Other sources fetch their items automatically."))
		if self.written and not self.guid:
			self.guid = frappe.generate_hash(length=16)

	def after_insert(self):
		if self.written and not self.flags.from_source:
			source = frappe.db.get_value(news.SOURCE, self.source, "keep")
			fetching.prune(self.source, source or 0)
			frappe.publish_realtime("one_news", {"source": self.source}, after_commit=True)
