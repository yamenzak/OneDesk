"""What One's own records say above their fields. See one/head.py.

A News Source says why its last fetch failed, and a hidden News Item says it
is hidden, each in one sentence; the form scripts keep their buttons.
"""

from frappe import _


def news_failed(doc):
	"""Why the last fetch failed, until one works."""
	if doc.get("last_error"):
		return {"text": doc.last_error, "colour": "orange"}
	return None


def news_hidden(doc):
	if doc.get("hidden_item"):
		return {"text": _("Hidden. This headline is not shown on the top bar or on screens."), "colour": "gray"}
	return None


MEASURES = {
	"news.failed": news_failed,
	"news.hidden": news_hidden,
}

HEADS = [
	{"doctype": "News Source", "sentences": [{"measure": "news.failed"}]},
	{"doctype": "News Item", "sentences": [{"measure": "news.hidden"}]},
]
