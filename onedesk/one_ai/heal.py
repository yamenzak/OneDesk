"""What an error tells the model to do next.

Each kind of failure is said with the one thing that mends it, and a refusal
says not to try again. Nothing here names the software underneath: the model
repeats what it reads. README, heal.py.
"""

import inspect
import re

import frappe
from frappe.utils import strip_html

MOST = 700

UNDERNEATH = re.compile(r"\b(frappe|erpnext|hrms)\b(\.\w+)*", re.I)


def said(raised: Exception, tool: str | None = None, args: dict | None = None, fn=None) -> str:
	"""The error, said so that a model can act on it."""
	args = args or {}
	text = _plain(raised)
	if isinstance(raised, TypeError) and fn is not None and _about_arguments(text):
		return _arguments(tool, fn, args)
	if isinstance(raised, frappe.PermissionError):
		return _clip(
			f"{text} The person asking may not do this, so do not try again: tell them, and that "
			"somebody who looks after the workspace could."
		)
	if isinstance(raised, frappe.DuplicateEntryError):
		return _clip(
			f"{text} It exists already: use that one (read it with read_record), or change it with edit_record, "
			"rather than making it again."
		)
	if isinstance(raised, frappe.LinkValidationError) or text.startswith("Could not find"):
		return _clip(
			f"{text} Find the right one with find_records (the type and the words the person used) and use the "
			"id it answers with. If it does not exist yet, suggest it first and point at its card with @ and the "
			"card's id, or suggest both together with create_records."
		)
	if isinstance(raised, frappe.DoesNotExistError):
		return _clip(
			f"{text} Look for it with search_everywhere or find_records and use the id it answers with; "
			"never guess an id."
		)
	if isinstance(raised, frappe.TimestampMismatchError):
		return _clip(f"{text} It changed since it was read: read it again, then suggest the change again.")
	if isinstance(raised, frappe.MandatoryError):
		return _clip(_mandatory(text, args))
	if isinstance(raised, frappe.ValidationError):
		return _clip(f"{text}{'' if text.endswith('.') else '.'} Correct what it names and call again.")
	return _clip(
		f"{text or type(raised).__name__}. Something went wrong that was not about what you asked: "
		"try once more, differently if you can, then tell the person it did not work."
	)


def unknown(tool: str | None, known: list[str]) -> str:
	"""A tool the model asked for that is not one."""
	near = _near(tool or "", known)
	return (
		f"There is no tool called {tool!r}."
		+ (f" Did you mean {', '.join(near)}?" if near else "")
		+ " Call more_tools to see every group of tools there is."
	)


def _arguments(tool: str | None, fn, args: dict) -> str:
	"""What the tool takes, against what it was given."""
	params = inspect.signature(fn).parameters
	takes = [
		f"{name} (needed)" if one.default is inspect.Parameter.empty else name
		for name, one in params.items()
		if one.kind not in (one.VAR_POSITIONAL, one.VAR_KEYWORD)
	]
	wrong = [one for one in args if one not in params]
	left = [
		name
		for name, one in params.items()
		if one.default is inspect.Parameter.empty
		and one.kind not in (one.VAR_POSITIONAL, one.VAR_KEYWORD)
		and name not in args
	]
	said = [f"{tool} takes {', '.join(takes)}."]
	if wrong:
		said.append(f"It has no {', '.join(wrong)}.")
	if left:
		said.append(f"It needs {', '.join(left)}.")
	said.append("Call it again with those.")
	return " ".join(said)


def _mandatory(text: str, args: dict) -> str:
	"""A record missing what it needs, by label, with how to fill each."""
	if "Still needed" in text or "suggest it again" in text:
		return text
	doctype = args.get("doctype")
	named = re.findall(r"\b[a-z][a-z0-9_]+\b", text.split("]:", 1)[-1]) if "]:" in text else []
	if doctype and named and frappe.db.exists("DocType", doctype):
		meta = frappe.get_meta(doctype)
		labels = [f"{(meta.get_field(one) and meta.get_field(one).label) or one} ({one})" for one in named]
		text = f"{doctype} still needs: {', '.join(labels)}"
	return (
		f"{text}. Fill them from what the person already said, or find a value with about_field; "
		"ask them only for what they have not said."
	)


def _about_arguments(text: str) -> bool:
	return bool(re.search(r"unexpected keyword argument|missing \d+ required|positional argument", text))


def _plain(raised: Exception) -> str:
	"""The message, without markup, the code's own names, or the software's."""
	text = strip_html(str(raised) or "").strip()
	text = re.sub(r"^\w+\(\)\s*", "", text)
	text = re.sub(r"\bDocType\b", "type of record", text)
	text = UNDERNEATH.sub("One", text)
	return " ".join(text.split())


def _near(tool: str, known: list[str]) -> list[str]:
	from difflib import get_close_matches

	words = set(tool.lower().split("_"))
	close = get_close_matches(tool, known, n=3, cutoff=0.6)
	sharing = [one for one in known if words & set(one.split("_")) - {"record", "records"}]
	return list(dict.fromkeys(close + sharing))[:4]


def _clip(text: str) -> str:
	return text if len(text) <= MOST else text[: MOST - 1] + "…"
