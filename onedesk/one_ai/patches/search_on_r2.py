"""Search by meaning moved from MariaDB to the workspace's index on R2
(one_ai/vectors.py): each source's pieces are carried over as they are, so
nothing is embedded again, and what could not be carried is indexed afresh
by the catch-up."""

import array
import base64

import frappe

from onedesk.one_ai import index


def _vector(blob: str | None) -> list[float]:
	found = array.array("f")
	found.frombytes(base64.b64decode(blob or ""))
	return list(found)


def execute():
	if not frappe.db.has_column("AI Chunk", "vector"):
		return
	sources = frappe.db.sql("select distinct source_doctype, source_name from `tabAI Chunk`")
	if not sources:
		return
	if not index.on():
		frappe.db.delete("AI Chunk")
		return
	from onedesk.one_ai import vectors

	for doctype, name in sources:
		rows = frappe.db.sql(
			"""select part, title, text, model, vector from `tabAI Chunk`
			where source_doctype = %s and source_name = %s order by part""",
			(doctype, name),
			as_dict=True,
		)
		try:
			vectors.put(
				doctype,
				name,
				[
					{
						"source_doctype": doctype,
						"source_name": name,
						"part": one.part,
						"title": one.title or "",
						"text": one.text or "",
						"model": one.model or "",
						"vector": _vector(one.vector),
					}
					for one in rows
					if one.vector
				],
			)
		except Exception:
			frappe.log_error(title="Search could not carry a source to R2", reference_doctype=doctype, reference_name=name)
			frappe.db.delete("AI Chunk", {"source_doctype": doctype, "source_name": name})
	frappe.db.sql("update `tabAI Chunk` set text = null, vector = null")
