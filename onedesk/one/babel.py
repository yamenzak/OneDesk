"""What a standard number card or dashboard chart says, for translation.

frappe's extractors read doctypes, workspaces, reports and the rest, but not a
card's label or a chart's name, and the dashboard shows both through `__()`.
An app may add its own extractors in `babel_extractors.csv` beside it; these
two are listed there.
"""

import json


def number_card(fileobj, *args, **kwargs):
	data = json.load(fileobj)
	if isinstance(data, dict) and data.get("doctype") == "Number Card" and data.get("label"):
		yield None, "_", data["label"], ["Label of a number card"]


def dashboard_chart(fileobj, *args, **kwargs):
	data = json.load(fileobj)
	if isinstance(data, dict) and data.get("doctype") == "Dashboard Chart" and data.get("chart_name"):
		yield None, "_", data["chart_name"], ["Name of a dashboard chart"]
