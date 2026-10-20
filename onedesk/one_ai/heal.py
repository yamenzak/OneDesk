"""What an error tells the model to do next.

The server's own error goes first, as it sent it, then the one thing that
mends it; a refusal says not to try again. Nothing here names the software underneath: the model
repeats what it reads. README, heal.py.
"""

import inspect
import re

import frappe
from frappe.utils import strip_html

MOST = 3000

UNDERNEATH = re.compile(r"\b(frappe|erpnext|hrms)\b(\.\w+)*", re.I)


def said(raised: Exception, tool: str | None = None, args: dict | None = None, fn=None) -> str:
	"""The server's own error as it sent it, with its kind, and on a line of
	its own what mends it."""
	raw = _plain(raised) or type(raised).__name__
	fix = _fix(raised, raw, tool, args or {}, fn)
	return _clip(f"{type(raised).__name__}: {raw}") + (f"\nWhat to do: {fix}" if fix else "")


def _fix(raised: Exception, raw: str, tool: str | None, args: dict, fn) -> str:
	if isinstance(raised, TypeError) and fn is not None and _about_arguments(raw):
		return _arguments(tool, fn, args)
	if isinstance(raised, frappe.PermissionError):
		return (
			"The person asking may not do this, so do not try again: tell them, and that somebody who looks "
			"after the workspace could."
		)
	if isinstance(raised, frappe.DuplicateEntryError):
		return "It exists already: use that one (read it with read_record), or change it with edit_record."
	if isinstance(raised, frappe.LinkValidationError) or raw.startswith("Could not find"):
		return (
			"Find the right one with find_records (the type and the words the person used) and use the id it "
			"answers with. If it does not exist yet, suggest it first and point at its card with @ and the "
			"card's id, or suggest both together with create_records."
		)
	if isinstance(raised, frappe.DoesNotExistError):
		return "Look for it with search_everywhere or find_records and use the id it answers with; never guess an id."
	if isinstance(raised, frappe.TimestampMismatchError):
		return "It changed since it was read: read it again, then suggest the change again."
	if isinstance(raised, frappe.MandatoryError):
		return _mandatory(raw, args)
	if isinstance(raised, frappe.ValidationError):
		return "Correct what it names and call again."
	return "This was not about what you asked: try once more, differently if you can, then tell the person it did not work."


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


def _mandatory(raw: str, args: dict) -> str:
	"""What a record still needs, by label, and how to fill it."""
	ask = "Fill them from what the person already said, or find a value with about_field; ask them only for what they have not said."
	if "Still needed" in raw or "suggest it again" in raw:
		return ask
	doctype = args.get("doctype")
	named = re.findall(r"\b[a-z][a-z0-9_]+\b", raw.split("]:", 1)[-1]) if "]:" in raw else []
	if doctype and named and frappe.db.exists("DocType", doctype):
		meta = frappe.get_meta(doctype)
		labels = [f"{(meta.get_field(one) and meta.get_field(one).label) or one} ({one})" for one in named]
		return f"{doctype} still needs {', '.join(labels)}. {ask}"
	return ask


def _about_arguments(text: str) -> bool:
	return bool(re.search(r"unexpected keyword argument|missing \d+ required|positional argument", text))


def _plain(raised: Exception) -> str:
	"""The message as the server sent it, without markup, and without naming
	the software underneath."""
	return " ".join(UNDERNEATH.sub("One", strip_html(str(raised) or "")).split())


def _near(tool: str, known: list[str]) -> list[str]:
	from difflib import get_close_matches

	words = set(tool.lower().split("_"))
	close = get_close_matches(tool, known, n=3, cutoff=0.6)
	sharing = [one for one in known if words & set(one.split("_")) - {"record", "records"}]
	return list(dict.fromkeys(close + sharing))[:4]


def _clip(text: str) -> str:
	return text if len(text) <= MOST else text[: MOST - 1] + "…"
