"""A presentation's guides: lines dragged out of the editor's rulers to line
things up against, across or down every slide (AGENTS.md, Rulers and
guides). They are kept on the presentation, drawn only in the editor, and
snapped to like the slide's centre is."""

import json
import uuid
from typing import Annotated

import frappe

#: The most guides one presentation keeps.
MOST = 60


def cleaned(guides, frame: tuple[int, int]) -> list[dict]:
	"""Guides as kept: an id, an axis and a place within the slide, at most
	`MOST`, anything else dropped. Pure."""
	if isinstance(guides, str):
		try:
			guides = json.loads(guides or "[]")
		except ValueError:
			return []
	kept = []
	for one in guides if isinstance(guides, list) else []:
		if not isinstance(one, dict) or one.get("axis") not in ("x", "y"):
			continue
		try:
			at = round(float(one.get("at")), 1)
		except (TypeError, ValueError):
			continue
		if at != at or not 0 <= at <= frame[0 if one["axis"] == "x" else 1]:
			continue
		ident = str(one.get("id") or "")[:20] or uuid.uuid4().hex[:8]
		kept.append({"id": ident, "axis": one["axis"], "at": at})
	return kept[:MOST]


def scaled(guides, before: tuple[int, int], after: tuple[int, int]) -> list[dict]:
	"""Guides moved with the slide when its size changes, each the same share of
	the way across. Pure."""
	sx, sy = after[0] / before[0], after[1] / before[1]
	moved = [{**one, "at": one["at"] * (sx if one["axis"] == "x" else sy)} for one in cleaned(guides, before)]
	return cleaned(moved, after)


@frappe.whitelist(methods=["POST"])
def keep(
	name: Annotated[str, "The presentation."],
	guides: Annotated[str | list, "The guides, each an axis (x or y) and a place in pixels."],
) -> list[dict]:
	"""The presentation's guides, as they are now."""
	from onedesk.one_deck import api

	api._may(name, "write")
	kept = cleaned(guides, api.frame(name))
	frappe.db.set_value(api.PRESENTATION, name, "guides", json.dumps(kept), update_modified=False)
	return kept
