"""Ask OneAI in a document: a request about the selection, or about the
document, becomes words to put in or an answer. Nothing is written here; the
editor puts them in as one edit that undo takes back. Through the account's
gateway and credits, like Ask in a workbook. README, Asking OneAI.
"""

import frappe
from frappe import _

from onedesk.one_doc import api
from onedesk.one_doc.ai import clean, text_of

ACTION = "doc_assist"

MOST_PROMPT = 2000

#: What the model is shown of the document and of the selection.
MOST_DOCUMENT, MOST_SELECTION = 12_000, 6_000


@frappe.whitelist(methods=["POST"])
def ai_assist(name: str, prompt: str, selection: str | None = None) -> dict:
	"""The editor's Ask: {"html"} to put in place of the selection, or at the
	cursor when nothing is selected, or {"answer"} to tell the person."""
	from onedesk.one_ai import run
	from onedesk.one_hr.hiring import read

	api._may(name, "write")
	prompt = (prompt or "").strip()
	if not prompt:
		frappe.throw(_("Enter a request first."))
	if len(prompt) > MOST_PROMPT:
		frappe.throw(_("The request is too long."))
	whole = text_of(frappe.db.get_value(api.DOCUMENT, name, "html"))[:MOST_DOCUMENT]
	chosen = text_of(selection)[:MOST_SELECTION] if selection else ""
	asked = f"The document:\n{whole}\n\n" + (f"The selection:\n{chosen}\n\n" if chosen else "No selection.\n\n") + f"The request: {prompt}"
	said = read(run.once(ACTION, asked, reference=name)) or {}
	if isinstance(said.get("html"), str) and text_of(said["html"]):
		return {"html": clean(said["html"])}
	if isinstance(said.get("answer"), str) and said["answer"].strip():
		return {"answer": said["answer"].strip()[:4000]}
	return {"answer": _("OneAI had nothing to add.")}
