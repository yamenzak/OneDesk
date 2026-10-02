"""Trying an extension before it is kept, so OneAI hears what is wrong while
it can still mend it.

- **Screen code is parsed** by node (`node --check`), which reads it and
  runs nothing: a missing bracket comes back with its line, rather than as a
  form that silently has no extension. Where the bench has no node, nothing
  is said.
- **Server code is run once on a real record** of its kind, the newest the
  person may read, inside a savepoint that is rolled back: whatever it
  changed or made is undone. A scheduled one is run once as it will run,
  with no record, and undone the same way. What happened comes back to OneAI as it would
  on that record: it stopped the save with this message, it changed these
  fields, or it ran into this error, which refuses it.

Both come after guard.py and checks.py, so what is tried has already been
read for what it may do and for the names it uses.
"""

import os
import re
import shutil
import subprocess
import tempfile

import frappe

from onedesk.one_studio.guard import Refused

#: How long node may take to read one extension.
PARSED_WITHIN = 10

#: How node says where it failed: "/tmp/x.js:12".
_AT = re.compile(r"\.js:(\d+)")


def _node() -> str | None:
	found = shutil.which("node")
	if found:
		return found
	for one in sorted(os.listdir("/opt"), reverse=True) if os.path.isdir("/opt") else []:
		candidate = f"/opt/{one}/bin/node"
		if one.startswith("node") and os.path.exists(candidate):
			return candidate
	return None


def parsed(code: str) -> None:
	"""Refuse screen code that is not JavaScript, with the line node stops at.
	Wrapped as a function body, as the extension runs (guard.wrapped_on_screen,
	places.js), on the same lines."""
	node = _node()
	if not node:
		return
	with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as held:
		held.write("(function (frappe, one) {" + (code or "") + "\n});\n")
		path = held.name
	try:
		done = subprocess.run(
			[node, "--check", path], capture_output=True, text=True, timeout=PARSED_WITHIN, check=False
		)
	except (OSError, subprocess.TimeoutExpired):
		return
	finally:
		os.unlink(path)
	if done.returncode == 0:
		return
	said = done.stderr or ""
	line = _AT.search(said)
	error = next((one.strip() for one in said.splitlines() if "Error" in one), "it does not parse")
	where = f" on line {line.group(1)}" if line else ""
	raise Refused(f"It is not JavaScript: {error}{where}.")


def ran(code: str, doctype: str | None, event: str | None) -> str:
	"""Run server code once, undone after, and say what it did. Refuse it if
	it runs into an error. Says nothing where the bench runs no server code,
	or no record of its kind can be read."""
	from frappe.utils.safe_exec import is_safe_exec_enabled, safe_exec

	if not is_safe_exec_enabled():
		return ""
	from onedesk.one_studio.guard import SCHEDULED

	record = None
	if doctype and event and event not in SCHEDULED:
		names = frappe.get_list(doctype, pluck="name", order_by="modified desc", limit=1)
		if not names:
			return f"Not tried: there is no {doctype} to try it on yet."
		record = frappe.get_doc(doctype, names[0])
		before = record.as_dict(no_default_fields=True)
	frappe.db.savepoint("one_studio_trial")
	stopped = None
	try:
		safe_exec(
			code,
			_locals={"doc": record} if record else None,
			restrict_commit_rollback=True,
			script_filename="OneStudio trial",
		)
	except frappe.ValidationError as meant:
		stopped = frappe.utils.strip_html(str(meant)) or "(no message)"
	except Exception as error:
		frappe.db.rollback(save_point="one_studio_trial")
		frappe.clear_last_message()
		where = f" on {doctype} {record.name}" if record else ""
		raise Refused(f"It was tried{where} and ran into an error: {type(error).__name__}: {error}") from None
	frappe.db.rollback(save_point="one_studio_trial")
	frappe.clear_messages()
	if not record:
		return "Tried once, undone after: it ran without an error."
	if stopped:
		return f"Tried on {doctype} {record.name}, undone after: it stopped the save, saying: {stopped}"
	after = record.as_dict(no_default_fields=True)
	changed = sorted(key for key in after if key in before and after[key] != before[key])
	if changed:
		return f"Tried on {doctype} {record.name}, undone after: it changed {', '.join(changed)}."
	return f"Tried on {doctype} {record.name}, undone after: it ran without an error and changed nothing on it."
