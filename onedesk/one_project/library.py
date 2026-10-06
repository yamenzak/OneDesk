"""Project templates shipped as files (library/), copied into the workspace as
ERPNext's own Project Template when somebody starts from one."""

import json
from pathlib import Path

import frappe
from frappe import _

FOLDER = Path(__file__).parent / "library"

#: What a task in a preset may say.
TASK_KEYS = {"subject", "day", "days", "milestone", "hours", "after", "tasks"}


@frappe.whitelist()
def presets() -> list[dict]:
	"""Every preset in the reader's language, in the order a person meets them
	(`order` in each file), with how many tasks and days it holds."""
	found = []
	for path in FOLDER.glob("*.json"):
		preset = read(path.stem)
		made = rows(preset)
		title, about = preset["title"], preset["about"]
		found.append(
			{
				"key": path.stem,
				"title": _(title),
				"about": _(about),
				"order": preset.get("order", 99),
				"tasks": sum(1 for one in made if not one["is_group"]),
				"days": max(one["start"] + one["duration"] for one in made),
				"copied": bool(frappe.db.exists("Project Template", _(title))),
			}
		)
	return sorted(found, key=lambda one: (one["order"], one["title"]))


def read(key: str) -> dict:
	path = FOLDER / f"{key}.json"
	if path.parent != FOLDER or not path.exists():
		frappe.throw(_("There is no template called {0} in the library.").format(key))
	return json.loads(path.read_text(encoding="utf-8"))


def rows(preset: dict) -> list[dict]:
	"""A preset as the template tasks it makes, in order, a parent before its
	tasks. Each row says its `parent` and what it waits on (`after`) by
	position. A group begins with its first task and ends with its last. A
	task waits on the one before it in the same group when that one ends
	first, unless it says what it comes after. Pure."""
	made: list[dict] = []

	def walk(tasks: list[dict], parent: int | None) -> None:
		previous = None
		for task in tasks:
			unknown = set(task) - TASK_KEYS
			if unknown:
				raise ValueError(f"{task.get('subject')}: {sorted(unknown)}")
			at = len(made)
			made.append(
				{
					"subject": task["subject"].strip(),
					"start": int(task.get("day") or 0),
					"duration": int(task.get("days") or 0),
					"is_milestone": int(bool(task.get("milestone"))),
					"expected_time": float(task.get("hours") or 0),
					"is_group": int(bool(task.get("tasks"))),
					"parent": parent,
					"after": task.get("after"),
				}
			)
			if task.get("tasks"):
				walk(task["tasks"], at)
				inside = [one for one in made[at + 1 :] if one["parent"] == at]
				made[at]["start"] = min(one["start"] for one in inside)
				made[at]["duration"] = (
					max(one["start"] + one["duration"] for one in inside) - made[at]["start"]
				)
			mine = made[at]
			if mine["after"] is None:
				ended = (
					previous is not None
					and made[previous]["start"] + made[previous]["duration"] <= mine["start"]
				)
				mine["after"] = [previous] if ended else []
			previous = at

	walk(preset["tasks"], None)
	names = {one["subject"]: at for at, one in enumerate(made)}
	for one in made:
		one["after"] = [names[after] if isinstance(after, str) else after for after in one["after"]]
	return made


@frappe.whitelist(methods=["POST"])
def copy(key: str) -> str:
	"""The preset as the workspace's own template, made the first time it is
	used and the same one after. Returns its name."""
	preset = read(key)
	title = preset["title"]
	title = _(title)
	if frappe.db.exists("Project Template", title):
		return title
	frappe.has_permission("Project Template", "create", throw=True)
	made = rows(preset)
	for one in made:
		subject = one["subject"]
		one["subject"] = _(subject)
	return make(title, made)


def make(title: str, made: list[dict], project_type: str | None = None) -> str:
	"""A Project Template from rows as `rows` gives them: a template task for
	each, nested, waiting on what it comes after."""
	tasks = []
	for one in made:
		task = frappe.new_doc("Task")
		task.update(
			{
				key: one[key]
				for key in ("subject", "start", "duration", "is_milestone", "expected_time", "is_group")
			}
		)
		task.is_template = 1
		if one["parent"] is not None:
			task.parent_task = tasks[one["parent"]].name
		for after in one["after"]:
			task.append("depends_on", {"task": tasks[after].name})
		task.insert()
		tasks.append(task)
	template = frappe.new_doc("Project Template")
	template.project_type = project_type
	for task in tasks:
		template.append("tasks", {"task": task.name, "subject": task.subject})
	template.insert(set_name=title)
	return template.name
