"""Every opening, everyone who applied to it, and how far each one got.

HRMS's `Recruitment Analytics` builds its rows from Staffing Plans:

	staffing_plan_details = get_staffing_plan(filters)
	staffing_plan_list = list(set([details["name"] for details in staffing_plan_details]))
	sp_jo_map, jo_list = get_job_opening(staffing_plan_list, filters)

An opening with no `staffing_plan` on it is not in `jo_list`, so its applicants
are never fetched and its offers never counted. Staffing plans are optional —
nothing in hiring asks for one, and most workspaces never make one — so the
report answers "nothing is happening" on a site that is hiring four people. It
is the same fault as `Shift Attendance`: a measurement built out of the records
that happen to exist rather than out of the thing being measured.

So this starts from the Job Opening, which is the record hiring actually turns
on, and left-joins everything else. An opening nobody has applied to is a row
that says so, because "nobody applied" is the answer somebody opened this to
find. The staffing plan is a column, not the spine.

The counting is deliberately one row per applicant rather than a tree: a tree
whose parent rows are blank in nine columns reads worse than a flat list, and
it cannot be sorted or exported by the column somebody cares about.
"""

import frappe
from frappe import _
from frappe.query_builder import Order

#: The applicant statuses that mean somebody made a decision, not that the
#: application is still sitting there. Used for the summary only.
DECIDED = ("Accepted", "Rejected")


def execute(filters: dict | None = None) -> tuple:
	filters = frappe._dict(filters or {})
	openings = _openings(filters)
	applicants = _applicants([row.name for row in openings], filters)
	rows = _rows(openings, applicants)
	return _columns(), rows, None, None, _totals(openings, applicants)


def _openings(filters) -> list[frappe._dict]:
	"""Every opening in the period. No staffing plan is required of any of them."""
	opening = frappe.qb.DocType("Job Opening")
	query = (
		frappe.qb.from_(opening)
		.select(
			opening.name,
			opening.job_title,
			opening.designation,
			opening.department,
			opening.status,
			opening.vacancies,
			opening.posted_on,
			opening.closes_on,
			opening.staffing_plan,
		)
		.orderby(opening.posted_on, order=Order.desc)
	)
	if filters.from_date:
		query = query.where(opening.posted_on >= filters.from_date)
	if filters.to_date:
		query = query.where(opening.posted_on <= f"{filters.to_date} 23:59:59")
	for field in ("name", "designation", "department", "status"):
		value = filters.get("job_opening" if field == "name" else field)
		if value:
			query = query.where(opening[field] == value)
	return query.run(as_dict=True)


def _applicants(openings: list[str], filters) -> list[frappe._dict]:
	"""Everyone who applied to those openings, with the interview and the offer.

	The latest interview and the latest offer, because an applicant can be seen
	twice and be offered twice, and the one that matters is the last one.
	"""
	if not openings:
		return []

	applicant = frappe.qb.DocType("Job Applicant")
	query = (
		frappe.qb.from_(applicant)
		.select(
			applicant.name,
			applicant.applicant_name,
			applicant.job_title.as_("job_opening"),
			applicant.status,
			applicant.applicant_rating,
			applicant.source,
			applicant.creation,
		)
		.where(applicant.job_title.isin(openings))
		.orderby(applicant.creation)
	)
	if filters.applicant_status:
		query = query.where(applicant.status == filters.applicant_status)
	rows = query.run(as_dict=True)
	if not rows:
		return []

	names = [row.name for row in rows]
	interviews = _latest("Interview", "job_applicant", names, "scheduled_on")
	offers = _latest("Job Offer", "job_applicant", names, "offer_date")
	seen = frappe._dict()
	for row in frappe.get_all(
		"Interview", filters={"job_applicant": ["in", names]}, fields=["job_applicant", "name"]
	):
		seen[row.job_applicant] = seen.get(row.job_applicant, 0) + 1

	for row in rows:
		row.interviews = seen.get(row.name, 0)
		interview = interviews.get(row.name)
		row.interview_on = interview.scheduled_on if interview else None
		row.interview_status = interview.status if interview else ""
		offer = offers.get(row.name)
		row.offer = offer.name if offer else None
		row.offer_date = offer.offer_date if offer else None
		row.offer_status = offer.status if offer else ""
	return rows


def _latest(doctype: str, link: str, names: list[str], on: str) -> dict:
	"""The last row of `doctype` per applicant, by `on` and then by creation.

	Cancelled and amended documents are left out: an amended interview leaves
	the cancelled original behind, and the cancelled one is not the answer.
	"""
	found = {}
	for row in frappe.get_all(
		doctype,
		filters={link: ["in", names], "docstatus": ["<", 2]},
		fields=["name", link, "status", on, "creation"],
		order_by=f"{on} asc, creation asc",
	):
		found[row.get(link)] = row
	return found


def _rows(openings: list, applicants: list) -> list[frappe._dict]:
	"""One row per applicant, and one row per opening that has none."""
	by_opening = {}
	for row in applicants:
		by_opening.setdefault(row.job_opening, []).append(row)

	rows = []
	for opening in openings:
		mine = by_opening.get(opening.name) or []
		if not mine:
			rows.append(_row(opening, None))
			continue
		for applicant in mine:
			rows.append(_row(opening, applicant))
	return rows


def _row(opening, applicant) -> frappe._dict:
	row = frappe._dict(
		job_opening=opening.name,
		job_title=opening.job_title,
		designation=opening.designation,
		department=opening.department,
		opening_status=_(opening.status),
		vacancies=opening.vacancies,
		staffing_plan=opening.staffing_plan,
	)
	if not applicant:
		row.applicant_name = _("nobody yet")
		return row

	row.update(
		job_applicant=applicant.name,
		applicant_name=applicant.applicant_name,
		applied_on=applicant.creation,
		applicant_status=_(applicant.status),
		rating=applicant.applicant_rating,
		source=applicant.source,
		interviews=applicant.interviews or None,
		interview_on=applicant.interview_on,
		interview_status=_(applicant.interview_status) if applicant.interview_status else "",
		offer=applicant.offer,
		offer_date=applicant.offer_date,
		offer_status=_(applicant.offer_status) if applicant.offer_status else "",
	)
	return row


def _columns() -> list[dict]:
	return [
		{"label": _("Opening"), "fieldname": "job_title", "fieldtype": "Data", "width": 180},
		{
			"label": _("Designation"),
			"fieldname": "designation",
			"fieldtype": "Link",
			"options": "Designation",
			"width": 140,
		},
		{
			"label": _("Department"),
			"fieldname": "department",
			"fieldtype": "Link",
			"options": "Department",
			"width": 150,
		},
		{"label": _("Status"), "fieldname": "opening_status", "fieldtype": "Data", "width": 90},
		{"label": _("Vacancies"), "fieldname": "vacancies", "fieldtype": "Int", "width": 100},
		{"label": _("Applicant"), "fieldname": "applicant_name", "fieldtype": "Data", "width": 180},
		{"label": _("Applied"), "fieldname": "applied_on", "fieldtype": "Date", "width": 110},
		{"label": _("Stage"), "fieldname": "applicant_status", "fieldtype": "Data", "width": 110},
		{"label": _("Rating"), "fieldname": "rating", "fieldtype": "Rating", "width": 100},
		{"label": _("Interviews"), "fieldname": "interviews", "fieldtype": "Int", "width": 90},
		{"label": _("Last Interview"), "fieldname": "interview_on", "fieldtype": "Date", "width": 120},
		{"label": _("Interview"), "fieldname": "interview_status", "fieldtype": "Data", "width": 110},
		{"label": _("Offered On"), "fieldname": "offer_date", "fieldtype": "Date", "width": 110},
		{"label": _("Offer"), "fieldname": "offer_status", "fieldtype": "Data", "width": 130},
		{
			"label": _("Source"),
			"fieldname": "source",
			"fieldtype": "Link",
			"options": "Job Applicant Source",
			"width": 130,
		},
		{
			"label": _("Staffing Plan"),
			"fieldname": "staffing_plan",
			"fieldtype": "Link",
			"options": "Staffing Plan",
			"width": 130,
		},
	]


def _totals(openings: list, applicants: list) -> list[dict] | None:
	"""Openings, and how far the people in them got.

	`Nobody Applied` is the one the old report could never have said, because an
	opening it could not see had no count to be zero.
	"""
	if not openings:
		return None

	applied_to = {row.job_opening for row in applicants}
	interviewed = sum(1 for row in applicants if row.interviews)
	offered = sum(1 for row in applicants if row.offer)
	accepted = sum(1 for row in applicants if row.offer_status == "Accepted")
	waiting = sum(1 for row in applicants if row.status not in DECIDED)

	tiles = [
		{"label": _("Openings"), "value": len(openings), "indicator": "Blue", "datatype": "Int"},
		{
			"label": _("Vacancies"),
			"value": sum(row.vacancies or 0 for row in openings),
			"indicator": "Blue",
			"datatype": "Int",
		},
		{"label": _("Applicants"), "value": len(applicants), "indicator": "Blue", "datatype": "Int"},
		{"label": _("Waiting"), "value": waiting, "indicator": "Orange", "datatype": "Int"},
		{"label": _("Interviewed"), "value": interviewed, "indicator": "Blue", "datatype": "Int"},
		{"label": _("Offered"), "value": offered, "indicator": "Green", "datatype": "Int"},
		{"label": _("Accepted"), "value": accepted, "indicator": "Green", "datatype": "Int"},
	]
	empty = len(openings) - len(applied_to)
	if empty:
		tiles.append(
			{"label": _("Nobody Applied"), "value": empty, "indicator": "Red", "datatype": "Int"}
		)
	return tiles
