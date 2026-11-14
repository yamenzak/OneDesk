"""What OneProject's coordinator makes of what OneAI read (docs/ARC-AI.md,
The agents): one task per matter, nudged, moved or closed by what comes
later, a task for what our own mail promised, and a site's day report on
its project. Pure: each answers actions, which the agents' door takes."""

from onedesk.one_ai.reading.act import Action
from onedesk.one_ai.reading.plans import PERSONAL, REAL, real
from onedesk.one_project.intake import task_in


PRIORITY = ("Low", "Medium", "High", "Urgent")


def tasks(reading: dict, ctx: dict) -> list[Action]:
	"""One task per matter. A new matter's asks become its steps; a later
	document nudges, moves or closes the task the matter already has."""
	if ctx.get("history") or reading.get("verdict") not in REAL:
		return []
	change = reading.get("change") or "New"
	held = ctx.get("task")
	if held:
		return _follow(reading, ctx, held, change)
	asks = [one for one in reading.get("asks") or [] if not one.get("promise") and not (one.get("what") == "Pay" and ctx.get("nobody_pays"))]
	if ctx.get("direction") == "Sent" or not asks or change in ("Nothing New", "Closing"):
		return []
	sensitive = reading.get("sensitivity") in PERSONAL
	steps = [{"step": _step(one, ctx), "done_when": ctx.get("done_when", {}).get(one.get("what"))} for one in asks]
	by = sorted(str(one["by_date"]) for one in asks if one.get("by_date"))
	about = ctx.get("about")
	subject = ctx["said"]["arrived_for"].format(ctx.get("about_title") or "") if sensitive else (reading.get("title") or ctx["said"]["arrived"])
	values = {
		"subject": subject[:140],
		"exp_end_date": by[0] if by else None,
		"description": None if sensitive else reading.get("summary"),
		"one_about_doctype": about[0] if about else None,
		"one_about": about[1] if about else None,
		"one_steps": [{k: v for k, v in one.items() if v} for one in steps],
		"assign_to": ctx.get("person"),
		"project": task_in(ctx.get("project"), by[0] if by else None),
	}
	return [Action("Create", "Task", values={k: v for k, v in values.items() if v}, key="task", flow="onedesk.one_ai.reading.planning.make_task", sure=True)]


def _step(ask: dict, ctx: dict) -> str:
	what = ctx["said"]["asks"].get(ask.get("what"), ask.get("what") or "")
	detail = (ask.get("detail") or "").strip()
	return f"{what}: {detail}"[:140] if detail else what


def _follow(reading: dict, ctx: dict, held: dict, change: str) -> list[Action]:
	"""What a later document does to the matter's task. A task a person
	closed is not reopened; they are told instead (planning does that)."""
	if held.get("status") in ("Completed", "Cancelled"):
		return []
	out: list[Action] = []
	if change == "Nudge":
		now = held.get("priority") or "Medium"
		higher = PRIORITY[min(PRIORITY.index(now) + 1, len(PRIORITY) - 1)] if now in PRIORITY else "High"
		values = {"priority": higher}
		new_by = sorted(str(one["by_date"]) for one in reading.get("asks") or [] if one.get("by_date"))
		if new_by and (not held.get("exp_end_date") or new_by[0] < str(held["exp_end_date"])[:10]):
			values["exp_end_date"] = new_by[0]
		out.append(Action("Update", "Task", held["name"], values, key=f"task|nudge|{reading.get('name')}", sure=True))
		out.append(Action("Comment", "Task", held["name"], {"comment_type": "Info", "content": ctx["said"]["nudged"].format(reading.get("title") or "")}, key=f"task|nudged|{reading.get('name')}", sure=True))
	elif change == "Update":
		new_by = sorted(str(one["by_date"]) for one in reading.get("asks") or [] if one.get("by_date"))
		if new_by and str(held.get("exp_end_date") or "")[:10] != new_by[0]:
			out.append(Action("Update", "Task", held["name"], {"exp_end_date": new_by[0]}, key=f"task|moved|{reading.get('name')}", sure=True))
	elif change == "Closing":
		out.append(Action("Update", "Task", held["name"], {"status": "Completed"}, key="task|closed", sure=True))
	return out


def promises(reading: dict, ctx: dict) -> list[Action]:
	"""What our own mail promised, as a task for whoever wrote it."""
	if ctx.get("direction") != "Sent" or ctx.get("history") or not ctx.get("sender_user"):
		return []
	out = []
	for index, one in enumerate(one for one in reading.get("asks") or [] if one.get("promise")):
		values = {
			"subject": (one.get("detail") or "")[:140],
			"exp_end_date": str(one["by_date"]) if one.get("by_date") else None,
			"one_about_doctype": ctx["about"][0] if ctx.get("about") else None,
			"one_about": ctx["about"][1] if ctx.get("about") else None,
			"assign_to": ctx["sender_user"],
		}
		out.append(Action("Create", "Task", values={k: v for k, v in values.items() if v}, key=f"promise|{index}", flow="onedesk.one_ai.reading.planning.make_task", sure=True))
	return out


def site_log(reading: dict, ctx: dict) -> list[Action]:
	"""A day's report from a site, on the project it names: a colleague's is
	their part of the day's Project Update, as if they had written it there;
	anybody else's a comment on the project."""
	if not real(reading, ctx) or reading.get("kind") != "Site Log" or not ctx.get("project") or ctx.get("direction") == "Sent":
		return []
	note = (reading.get("text") or reading.get("summary") or "").strip()
	if ctx.get("subject") and note.startswith(ctx["subject"]):
		note = note[len(ctx["subject"]) :].strip()
	if not note:
		return []
	if ctx.get("sender_colleague"):
		values = {"project": ctx["project"], "user": ctx["sender_colleague"], "note": note}
		return [Action("Create", "Project Update", values=values, key="project|log", flow="onedesk.one_project.updates.logged", sure=True)]
	return [Action("Comment", "Project", ctx["project"], {"comment_type": "Comment", "content": note}, key="project|log", sure=True)]
