"""News on the desk: the sources a person follows, and the headlines the
top bar runs in place of announcements when they choose News. Who follows
what is their own user default; following nothing chosen is following all."""

import json

import frappe
from frappe import _

from onedesk.one import news

FOLLOWING = "one_news_following"
ON_THE_BAR = 12


def _chosen() -> list[str]:
	try:
		return list(json.loads(frappe.defaults.get_user_default(FOLLOWING) or "[]"))
	except ValueError:
		return []


def followed() -> list[str]:
	"""The enabled sources this person reads on the bar: those chosen, or all."""
	enabled = frappe.get_list(news.SOURCE, filters={"enabled": 1}, pluck="name", limit_page_length=500)
	chosen = [one for one in _chosen() if one in enabled]
	return chosen or enabled


def headlines() -> list[dict]:
	"""The newest headlines from the sources this person follows, as the bar
	runs them: each opens its story, or its item when it was written here."""
	if not frappe.has_permission(news.ITEM, "read"):
		return []
	sources = followed()
	if not sources:
		return []
	out = []
	for one in news.items(sources, most=ON_THE_BAR):
		out.append(
			{
				"name": one["name"],
				"title": one["title"],
				"publisher": one["publisher"],
				"logo": one["logo"],
				"link": one["link"],
				"route": [] if one["link"] else ["Form", news.ITEM, one["name"]],
			}
		)
	return out


@frappe.whitelist()
@frappe.read_only()
def following() -> dict:
	"""Every source this person may read, and whether they follow it."""
	chosen = set(_chosen())
	sources = frappe.get_list(
		news.SOURCE,
		filters={"enabled": 1},
		fields=["name", "kind", "category", "logo"],
		order_by="category asc, name asc",
		limit_page_length=500,
	)
	return {
		"all": not chosen,
		"sources": [
			{**one, "kind": _(one.kind), "followed": not chosen or one.name in chosen} for one in sources
		],
	}


@frappe.whitelist(methods=["POST"])
def follow(sources: str | list) -> None:
	"""Follow these sources on the bar; all of them, or none chosen, is all."""
	chosen = frappe.parse_json(sources) if isinstance(sources, str) else sources
	enabled = set(frappe.get_list(news.SOURCE, filters={"enabled": 1}, pluck="name", limit_page_length=500))
	chosen = sorted({one for one in chosen or [] if one in enabled})
	if not chosen or set(chosen) == enabled:
		frappe.defaults.clear_user_default(FOLLOWING)
	else:
		frappe.defaults.set_user_default(FOLLOWING, json.dumps(chosen))
