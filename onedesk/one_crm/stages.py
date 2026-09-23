"""A sales stage that means something.

ERPNext's `Sales Stage` is a name and nothing else, so an opportunity's stage
and its status are two answers to one question that nothing keeps in step.
Here a stage has a position, a probability and an outcome, and the outcome is
what ties the two together: a stage whose outcome is Won is a converted
opportunity, one whose outcome is Lost is a lost one, and the stage follows
when ERPNext's own verbs — Declare Lost, a quotation lost, a sales order —
change the status instead.

Stage changes are recorded by frappe's Milestone Tracker, a fixture, so the
day an opportunity reached its stage is a row rather than a guess.
"""

import frappe
from frappe import _

#: What an outcome makes an opportunity's status.
STATUS = {"Won": "Converted", "Lost": "Lost"}

#: ERPNext's daily job that sets status Open on any lead or opportunity with an
#: Event today, converted and lost ones included.
REOPENER = "erpnext.crm.utils.open_leads_opportunities_based_on_todays_event"

#: The stages a small business recognises: name, position, probability, outcome.
SIX = (
	("New", 1, 10, "Open"),
	("Qualified", 2, 25, "Open"),
	("Proposal", 3, 50, "Open"),
	("Negotiation", 4, 75, "Open"),
	("Won", 5, 100, "Won"),
	("Lost", 6, 0, "Lost"),
)

#: The eight stages ERPNext's setup wizard writes, retired where none is in use.
TEXTBOOK = (
	"Prospecting",
	"Qualification",
	"Needs Analysis",
	"Value Proposition",
	"Identifying Decision Makers",
	"Perception Analysis",
	"Proposal/Price Quote",
	"Negotiation/Review",
)


def settle() -> None:
	frappe.db.set_value("Scheduled Job Type", {"method": REOPENER}, "stopped", 1)
	seed()
	used = set(frappe.get_all("Opportunity", distinct=True, pluck="sales_stage"))
	used |= set(frappe.get_all("Prospect Opportunity", distinct=True, pluck="stage"))
	for name in TEXTBOOK:
		if name not in used and frappe.db.exists("Sales Stage", name):
			frappe.delete_doc("Sales Stage", name, ignore_permissions=True, force=True)


def seed() -> None:
	"""The six stages, once. Not a fixture: fixtures sync before custom fields
	do, so on a new site the position, probability and outcome had no column
	to land in. Once any stage has a position, the list is the workspace's."""
	if frappe.db.exists("Sales Stage", {"one_position": [">", 0]}):
		return
	for name, position, chance, outcome in SIX:
		values = {"one_position": position, "one_probability": chance, "one_outcome": outcome}
		if frappe.db.exists("Sales Stage", name):
			frappe.db.set_value("Sales Stage", name, values)
		else:
			frappe.get_doc({"doctype": "Sales Stage", "stage_name": name, **values}).insert(ignore_permissions=True)


def stages() -> list[dict]:
	return frappe.get_all(
		"Sales Stage",
		fields=["name", "one_position", "one_probability", "one_outcome"],
		order_by="one_position asc, name asc",
	)


def first(outcome: str) -> str | None:
	return next((one.name for one in stages() if (one.one_outcome or "Open") == outcome), None)


def before_validate(doc, method=None) -> None:
	"""Keep an opportunity's stage, status and probability in step."""
	before = doc.get_doc_before_save()
	was_stage = before.sales_stage if before else None
	was_status = before.status if before else None

	if doc.status != was_status and doc.status in ("Lost", "Converted"):
		# One of ERPNext's verbs decided; the stage goes where the status went.
		wanted = "Lost" if doc.status == "Lost" else "Won"
		if _outcome(doc.sales_stage) != wanted:
			doc.sales_stage = first(wanted) or doc.sales_stage
	elif doc.status != was_status and doc.status == "Open" and _outcome(doc.sales_stage) != "Open":
		# Reopened: back to the stage it was in before it was won or lost.
		doc.sales_stage = last_open(doc.name) or first("Open")
	elif doc.sales_stage != was_stage:
		moved_to = _outcome(doc.sales_stage)
		if moved_to == "Lost" and doc.status != "Lost":
			frappe.throw(_("Use Declare Lost to say why it was lost."), title=_("Why Was It Lost?"))
		if moved_to in STATUS:
			doc.status = STATUS[moved_to]
		elif was_stage and _outcome(was_stage) != "Open":
			doc.status = "Open"
			doc.set_status()

	if not doc.sales_stage:
		doc.sales_stage = first("Open")
	doc.probability = probability(
		_row(doc.sales_stage),
		doc.probability,
		was=before.probability if before else None,
		moved=doc.sales_stage != was_stage,
	)


def probability(stage: dict | None, typed, was=None, moved: bool = False):
	"""What an opportunity's probability should be. Pure.

	Won and lost are 100 and 0 whatever was typed. Otherwise a stage sets it
	when the opportunity arrives there, unless the same save typed another.
	"""
	if not stage:
		return typed
	outcome = stage.get("one_outcome") or "Open"
	if outcome == "Won":
		return 100
	if outcome == "Lost":
		return 0
	typed_now = typed not in (None, "") and (was is None or typed != was)
	if moved and not typed_now:
		return stage.get("one_probability") or 0
	return typed


def follow(doc, method=None) -> None:
	"""A quotation or a sales order changed an opportunity's status behind its
	back, with `db_set`, so no hook of the opportunity's ran. Catch up."""
	quotations = [doc]
	if doc.doctype == "Sales Order":
		names = {row.prevdoc_docname for row in doc.items if row.get("prevdoc_docname")}
		quotations = [frappe.get_doc("Quotation", name) for name in names]
	opportunities = set()
	for quotation in quotations:
		opportunities.add(quotation.get("opportunity"))
		opportunities |= {
			row.prevdoc_docname for row in quotation.items if row.get("prevdoc_doctype") == "Opportunity"
		}
	for name in filter(None, opportunities):
		_catch_up(name)
		if doc.doctype == "Quotation" and doc.status == "Lost":
			carry_reasons(doc, name)


def carry_reasons(quotation, opportunity: str) -> None:
	"""A deal lost because its quotation was lost is lost for the quotation's
	reasons, so "why we lose" is read from one place. The two reason lists are
	one list (fixtures), and a reason only the quotation's list has is added."""
	if frappe.db.exists("Opportunity Lost Reason Detail", {"parent": opportunity, "parenttype": "Opportunity"}):
		return
	for idx, row in enumerate(quotation.get("lost_reasons") or [], 1):
		if not frappe.db.exists("Opportunity Lost Reason", row.lost_reason):
			frappe.get_doc({"doctype": "Opportunity Lost Reason", "lost_reason": row.lost_reason}).insert(
				ignore_permissions=True
			)
		frappe.get_doc(
			{
				"doctype": "Opportunity Lost Reason Detail",
				"parent": opportunity,
				"parenttype": "Opportunity",
				"parentfield": "lost_reasons",
				"lost_reason": row.lost_reason,
				"idx": idx,
			}
		).db_insert()
	if quotation.order_lost_reason and not frappe.db.get_value("Opportunity", opportunity, "order_lost_reason"):
		frappe.db.set_value("Opportunity", opportunity, "order_lost_reason", quotation.order_lost_reason)


def _catch_up(name: str) -> None:
	status, stage = frappe.db.get_value("Opportunity", name, ["status", "sales_stage"])
	now = _outcome(stage)
	if status in ("Lost", "Converted"):
		wanted = first("Lost" if status == "Lost" else "Won")
	elif now != "Open":
		wanted = last_open(name) or first("Open")
	else:
		return
	if not wanted or wanted == stage:
		return
	row = _row(wanted)
	frappe.db.set_value(
		"Opportunity",
		name,
		{"sales_stage": wanted, "probability": probability(row, None, moved=True)},
	)
	frappe.get_doc(
		doctype="Milestone",
		reference_type="Opportunity",
		reference_name=name,
		track_field="sales_stage",
		value=wanted,
		milestone_tracker="Opportunity-sales_stage",
	).insert(ignore_permissions=True)


def last_open(name: str) -> str | None:
	"""The last stage an opportunity was in whose outcome is Open."""
	for value in frappe.get_all(
		"Milestone",
		filters={"reference_type": "Opportunity", "reference_name": name, "track_field": "sales_stage"},
		order_by="creation desc",
		pluck="value",
	):
		if _outcome(value) == "Open":
			return value
	return None


def _row(name: str | None) -> dict | None:
	return next((one for one in stages() if one.name == name), None) if name else None


def _outcome(name: str | None) -> str | None:
	row = _row(name)
	return (row.one_outcome or "Open") if row else None
