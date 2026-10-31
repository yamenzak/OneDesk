"""News for the demo: the office's own news, written here, and three feeds
from the library, each in a category with its colour. The feeds fill when
the scheduler first fetches them; the written items are there at once."""

import frappe

from onedesk.one_demo.base import as_user

OWNER = "wsadmin@one.test"

CATEGORIES = (("Company", "#059669"), ("Business", "#2563EB"), ("World", "#DC2626"))

FEEDS = (
	(
		"The National · Business",
		"https://www.thenationalnews.com/arc/outboundfeeds/rss/category/business/?outputType=xml",
		"Business",
	),
	("Khaleej Times", "https://www.khaleejtimes.com/stories.rss", "World"),
	("BBC عربي", "https://feeds.bbci.co.uk/arabic/rss.xml", "World"),
)

WRITTEN = (
	(
		"New curtain wall line opens in Jebel Ali",
		"The second line doubles our unitised panel output from January.",
	),
	("Safety: 400 days without a lost-time injury", "Thank you to every crew on site this year."),
	(
		"Bayview tower facade topped out",
		"The last unitised panel went up on Thursday, two weeks ahead of plan.",
	),
)

SAHARA = "Sahara News"


def run(password=None):
	with as_user(OWNER):
		for name, colour in CATEGORIES:
			if not frappe.db.exists("News Category", name):
				frappe.get_doc({"doctype": "News Category", "category_name": name, "colour": colour}).insert()
		for name, url, category in FEEDS:
			if not frappe.db.exists("News Source", {"feed_url": url}):
				frappe.get_doc(
					{
						"doctype": "News Source",
						"source_name": name,
						"kind": "Feed",
						"feed_url": url,
						"category": category,
						"keep": 30,
					}
				).insert()
		if not frappe.db.exists("News Source", SAHARA):
			frappe.get_doc(
				{
					"doctype": "News Source",
					"source_name": SAHARA,
					"kind": "Written",
					"category": "Company",
					"keep": 0,
				}
			).insert()
		for title, summary in WRITTEN:
			if not frappe.db.exists("News Item", {"source": SAHARA, "title": title}):
				frappe.get_doc(
					{"doctype": "News Item", "source": SAHARA, "title": title, "summary": summary}
				).insert()
