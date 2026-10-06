"""What a standard number card, dashboard chart, print format or project
template says, for translation.

Extractors listed in `babel_extractors.csv`, for what frappe's own leave out.
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


def project_template(fileobj, *args, **kwargs):
	"""A preset in one_project/library: its title, what it is for and every
	task, copied into a workspace in its own language."""
	data = json.load(fileobj)
	yield None, "_", data["title"], ["Name of a project template"]
	yield None, "_", data["about"], ["What a project template is for"]
	for subject in sorted(set(_subjects(data["tasks"]))):
		yield None, "_", subject, [f"Task in the {data['title']} project template"]


def _subjects(tasks):
	for task in tasks:
		yield task["subject"]
		yield from _subjects(task.get("tasks") or [])
