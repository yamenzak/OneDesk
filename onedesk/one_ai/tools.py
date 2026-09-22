"""What a model may ask for, and what it may only suggest.

Everything a person can do here a tool can do — read a list, read a record,
count, look at a type, create, edit, delete — and the difference between the
first four and the last three is the whole of this module's design:

**A read runs. A create, an edit or a delete becomes a card.** Nothing in here
writes. A write tool checks the asker's permission for the verb, writes an
`AI Proposal` and hands back its id, and the doing happens when a person presses
Apply. A tool that saved would be a tool that saves on a model's say-so, and the
failure mode is not a wrong field — it is a wrong *record*, at the end of a
chain of lookups nobody read.

**Every tool runs as the session user.** Not as Administrator with a filter
bolted on afterwards, and not with `ignore_permissions` anywhere: the same
`frappe.get_list` the browser would have called, under the same permissions, so
a model asked about somebody else's salary gets what that person would get,
which is nothing. This is the one rule in the module with no exception and no
override, and a tool that needs more than its caller has is a tool that does not
ship.

Reading the whole of Frappe this way is the point. The alternative is a
hand-written tool per doctype, which is out of date the week somebody adds a
field.
"""

from typing import Annotated

import frappe

from onedesk.one_ai import proposals, schema

#: Fieldtypes never handed to a model, whatever the caller may see. A password
#: is a credential rather than a fact about a record, and a model that can read
#: one can put it in an answer.
NEVER_READ = ("Password",)

#: How many rows a list tool may answer with. A model given five hundred records
#: is a model given five hundred records' worth of somebody's month.
MOST = 100


# --------------------------------------------------------------- what it reads


def list_records(
	doctype: Annotated[str, "The type of record to look in, spelled as it is on screen."],
	filters: Annotated[dict, "Field name to value. All of them have to match."] | None = None,
	fields: Annotated[list, "Which fields to answer with. Defaults to what a list shows."]
	| None = None,
	limit: Annotated[int, "At most this many rows."] = 20,
	order_by: Annotated[str, "A field and a direction, such as 'creation desc'."] | None = None,
) -> list:
	"""Find records of one type. Answers only with what the person asking may see.

	`frappe.get_list` and nothing else: the role, the user permissions and every
	`permission_query_conditions` hook apply exactly as they do in the browser.
	"""
	return frappe.get_list(
		doctype,
		filters=filters or {},
		fields=fields or _shown(doctype),
		order_by=order_by,
		limit_page_length=min(int(limit or 20), MOST),
	)


def read_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
) -> dict:
	"""Read one record in full, if the person asking may see it."""
	held = frappe.get_doc(doctype, name)
	held.check_permission("read")
	return _without_secrets(doctype, held.as_dict())


def count_records(
	doctype: Annotated[str, "The type of record to count."],
	filters: Annotated[dict, "Field name to value. All of them have to match."] | None = None,
) -> int:
	"""Count records of one type, counting only what the person asking may see."""
	return len(
		frappe.get_list(
			doctype, filters=filters or {}, fields=["name"], limit_page_length=0
		)
	)


def describe_type(
	doctype: Annotated[str, "The type of record to describe."],
) -> dict:
	"""List the fields one type of record has, so they can be asked for by name."""
	if not frappe.has_permission(doctype, ptype="read"):
		frappe.throw(
			frappe._("You may not read {0}.").format(doctype), frappe.PermissionError
		)
	meta = frappe.get_meta(doctype)
	return {
		"doctype": doctype,
		"fields": [
			{
				"fieldname": f.fieldname,
				"label": f.label,
				"fieldtype": f.fieldtype,
				"options": f.options if f.fieldtype in ("Link", "Select") else None,
			}
			for f in meta.fields
			if f.fieldtype not in NEVER_READ
			and f.fieldtype not in ("Section Break", "Column Break", "Tab Break", "HTML")
		],
	}


# ------------------------------------------------------ what it may only suggest


def create_record(
	doctype: Annotated[str, "The type of record to create."],
	values: Annotated[dict, "Field name to value."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Suggest creating a record. Nothing is created until a person approves it."""
	return _card(proposals.propose("Create", doctype, changes=values, why=why))


def edit_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	changes: Annotated[dict, "Field name to new value. Only the fields that change."],
	why: Annotated[str, "One sentence on what this is for."] | None = None,
) -> dict:
	"""Suggest changing a record. Nothing changes until a person approves it."""
	return _card(proposals.propose("Edit", doctype, changes=changes, record=name, why=why))


def delete_record(
	doctype: Annotated[str, "The type of record."],
	name: Annotated[str, "Its id."],
	why: Annotated[str, "One sentence on why."] | None = None,
) -> dict:
	"""Suggest deleting a record. Nothing is deleted until a person approves it."""
	return _card(proposals.propose("Delete", doctype, record=name, why=why))


#: What runs when a model asks for it.
READS = (list_records, read_record, count_records, describe_type)

#: What becomes a card instead. Named separately rather than flagged, because a
#: tool moving from one tuple to the other is a line in a diff somebody reviews.
SUGGESTS = (create_record, edit_record, delete_record)

BY_NAME = {fn.__name__: fn for fn in READS + SUGGESTS}


def declared() -> list[dict]:
	"""Every tool, as a provider's function declaration."""
	return [schema.of(fn) for fn in READS + SUGGESTS]


def run(name: str, args: dict | None = None) -> dict:
	"""Call one tool as the person asking, and say whether it happened.

	`ran` is the thing a model has to be told: a read happened and here is the
	answer; a write did not happen and here is the card somebody has to approve.
	"""
	fn = BY_NAME.get(name)
	if not fn:
		frappe.throw(frappe._("{0} is not a tool.").format(name))
	answer = fn(**(args or {}))
	return {"tool": name, "ran": fn in READS, "answer": answer}


def _card(proposal: str) -> dict:
	return {
		"proposal": proposal,
		"state": "Proposed",
		"said": frappe._("Suggested. It happens when somebody approves it."),
	}


def _shown(doctype: str) -> list[str]:
	"""What a list of this type shows, which is what somebody would have seen."""
	meta = frappe.get_meta(doctype)
	fields = ["name"] + [f.fieldname for f in meta.fields if f.in_list_view and f.fieldtype not in NEVER_READ]
	if meta.title_field and meta.title_field not in fields:
		fields.append(meta.title_field)
	return fields


def _without_secrets(doctype: str, said: dict) -> dict:
	secret = {f.fieldname for f in frappe.get_meta(doctype).fields if f.fieldtype in NEVER_READ}
	return {key: value for key, value in said.items() if key not in secret}
