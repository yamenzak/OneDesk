import frappe
from frappe import _
from frappe.model.document import Document

from onedesk.one import news
from onedesk.one.news import fetching

# What, changed, means the source is fetched again at the next tick.
FETCHED_BY = (
	"kind",
	"feed_url",
	"google_topic",
	"google_query",
	"ai_brief",
	"country",
	"language",
	"fetch_every",
	"fetch_at",
	"enabled",
)


class NewsSource(Document):
	def _validate_links(self):
		# a category is a name to type, made the first time it is used, and
		# frappe checks links before any hook of ours runs
		self.category = news.category(self.category)
		super()._validate_links()

	def validate(self):
		if self.kind == "Feed" and self.feed_url and not self.feed_url.startswith("https://"):
			frappe.throw(_("A feed is read over https. Use its https address."))
		if self.fetch_every == fetching.SET_TIMES:
			fetching.check_times(self.fetch_at)
		elif self.kind in fetching.LEAST and fetching.EVERY.get(self.fetch_every, 0) < fetching.LEAST[self.kind]:
			least = next(label for label, minutes in fetching.EVERY.items() if minutes >= fetching.LEAST[self.kind])
			self.fetch_every = least
			frappe.msgprint(
				_("{0} is fetched at most every {1} minutes, so this source is fetched {2}.").format(
					_(self.kind), fetching.LEAST[self.kind], _(least).lower()
				),
				alert=True,
			)
		if self.keep is None or self.keep < 0:
			self.keep = 0

	def on_update(self):
		if (
			self.kind != "Written"
			and self.enabled
			and (self.is_new() or any(self.has_value_changed(one) for one in FETCHED_BY))
		):
			fetching.soon(self.name)
			fetching.later(self.name)
		if self.has_value_changed("keep"):
			fetching.prune(self.name, self.keep)

	def on_trash(self):
		frappe.db.delete(news.ITEM, {"source": self.name})
