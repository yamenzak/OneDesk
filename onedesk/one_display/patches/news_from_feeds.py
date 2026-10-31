"""A Feed source reads a News Source now, where it held its own address
(one/news): each address becomes a News Source that fetches on its own
schedule, and the Display Source shows its headlines."""

import frappe


def execute():
	if "feed_url" not in set(frappe.db.get_table_columns("Display Source")):
		return
	rows = frappe.db.sql(
		"""select name, source_name, feed_url from `tabDisplay Source`
		where kind = 'Feed' and ifnull(feed_url, '') != ''""",
		as_dict=True,
	)
	for row in rows:
		named = frappe.db.get_value("News Source", {"feed_url": row.feed_url}, "name")
		if not named:
			base = named = row.source_name or row.name
			n = 1
			while frappe.db.exists("News Source", named):
				n += 1
				named = f"{base} {n}"
			frappe.get_doc(
				{"doctype": "News Source", "source_name": named, "kind": "Feed", "feed_url": row.feed_url}
			).insert(ignore_permissions=True)
		source = frappe.get_doc("Display Source", row.name)
		source.kind = "News"
		source.set("news_sources", [{"news_source": named}])
		source.flags.ignore_validate = True
		source.save(ignore_permissions=True)
