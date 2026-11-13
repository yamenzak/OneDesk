"""News (one/AGENTS.md, news/): sources a workspace adds, fetched on their
own schedule into News Items (fetching.py), and read here by the desk's
top bar and OneDisplay's ticker and news widgets. A source is a feed
(library.py has ready ones), Google News, OneAI, or written by hand; each
keeps only its newest items."""

import frappe
from frappe.utils import cint

from onedesk.trust_center import services

SOURCE, ITEM, CATEGORY = "News Source", "News Item", "News Category"

def category(name: str | None) -> str | None:
	"""A News Category by its name, made the first time it is needed."""
	name = (name or "").strip()
	if not name:
		return None
	if not frappe.db.exists(CATEGORY, name):
		frappe.get_doc({"doctype": CATEGORY, "category_name": name}).insert(ignore_permissions=True)
	return name


def logos(domains: set[str]) -> dict[str, str]:
	"""The logo found for each publisher's site; those never looked for are
	looked for in the background, while the logos service is on."""
	from onedesk.one_mail import faces

	domains = {one for one in domains if one}
	if not domains:
		return {}
	rows = frappe.get_all("Face", filters={"name": ["in", list(domains)]}, fields=["name", "image", "found"])
	known = {row.name for row in rows}
	missing = sorted(domains - known)
	if missing and services.on("logos"):
		frappe.enqueue(
			"onedesk.one_mail.faces.fetch_many",
			queue="short",
			job_id=f"one_news_logos:{','.join(missing)[:120]}",
			deduplicate=True,
			enqueue_after_commit=True,
			keys=missing[:30],
		)
	return {row.name: row.image for row in rows if row.found and row.image}


def items(sources: list[str] | None = None, most: int = 20, order: str = "Newest") -> list[dict]:
	"""The newest items of enabled sources, as a ticker or a news widget
	draws them: each with its source, category and colour, and a logo, the
	publisher's where the item names one, else its source's. `order` is
	Newest, or By Category to keep a category's items together."""
	S, I, C = frappe.qb.DocType(SOURCE), frappe.qb.DocType(ITEM), frappe.qb.DocType(CATEGORY)
	query = (
		frappe.qb.from_(I)
		.join(S)
		.on(I.source == S.name)
		.left_join(C)
		.on(I.category == C.name)
		.where(S.enabled == 1)
		# a hidden headline is read nowhere: the bar, screens, a source's form
		.where(I.hidden_item == 0)
		.select(
			I.name,
			I.title,
			I.summary,
			I.link,
			I.image,
			I.published,
			I.publisher,
			I.publisher_site,
			I.source,
			I.category,
			S.logo.as_("source_logo"),
			C.colour,
		)
		.orderby(I.published, order=frappe.qb.desc)
		.limit(max(1, min(cint(most) or 20, 100)))
	)
	if sources:
		query = query.where(I.source.isin(list(sources)))
	rows = query.run(as_dict=True)
	found = logos({row.publisher_site for row in rows if row.publisher_site})
	out = []
	for row in rows:
		out.append(
			{
				"name": row.name,
				"title": row.title,
				"summary": row.summary or "",
				"link": row.link or "",
				"image": row.image or "",
				"published": str(row.published) if row.published else "",
				"ago": frappe.utils.pretty_date(row.published) if row.published else "",
				"source": row.source,
				"publisher": row.publisher or row.source,
				"category": row.category or "",
				"colour": row.colour or "",
				"logo": found.get(row.publisher_site) or row.source_logo or "",
			}
		)
	if order == "By Category":
		firsts = {}
		for i, one in enumerate(out):
			firsts.setdefault(one["category"], i)
		out.sort(key=lambda one: firsts[one["category"]])
	return out


def written(source: str) -> bool:
	return frappe.db.get_value(SOURCE, source, "kind") == "Written"
