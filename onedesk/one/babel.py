"""What a standard number card, dashboard chart or print format says, for
translation.

frappe's extractors read doctypes, workspaces, reports and the rest, but not a
card's label, a chart's name or the labels of a format laid out in the print
format builder. The dashboard shows the first two through `__()`, and the
builder's macros print each label through `_()`. An app may add its own
extractors in `babel_extractors.csv` beside it; these are listed there.
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


def print_format(fileobj, *args, **kwargs):
	data = json.load(fileobj)
	if not (isinstance(data, dict) and data.get("doctype") == "Print Format" and data.get("format_data")):
		return
	try:
		layout = json.loads(data["format_data"])
	except ValueError:
		return
	for label in sorted(set(_labels(layout))):
		yield None, "_", label, [f"Label in the {data.get('name')} print format"]


def _labels(data):
	"""Every label a builder layout prints: its blocks' and their columns'."""
	if isinstance(data, dict):
		if data.get("fieldtype") and data.get("label") and data.get("fieldtype") != "Field Template":
			yield data["label"]
		for value in data.values():
			yield from _labels(value)
	elif isinstance(data, list):
		for value in data:
			yield from _labels(value)
