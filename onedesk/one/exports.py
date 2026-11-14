"""A large export waits for a workspace administrator (one/second.py).
Every way frappe lets somebody take records out in a file is held to the
workspace's Export Limit: run as frappe runs it, the rows of the file are
counted, and over the limit the file is not sent but an approval asked.
Once approved, the same person exports it again within a day, once. More
in one/AGENTS.md, Second approval."""

import csv
import io

import frappe
from frappe import _
from frappe.utils import add_days, cint, fmt_money, now_datetime

from onedesk.one import roles, second, tell

FIELD = "one_export_limit"

DEFAULT = 1000

KEPT_FOR = 1
"""Days an approved export may be made, once."""

NAMES = ("filecontent", "result", "filename", "type", "doctype")


def limit() -> int:
	"""How many records one person may export at once; 0 for any number."""
	held = frappe.db.get_single_value("System Settings", FIELD)
	return DEFAULT if held is None else cint(held)


def _approved(doctype: str, records: int) -> str | None:
	"""The person's approved export of at least this many of a kind, from
	the last day and not used yet."""
	return frappe.db.get_value(
		second.DOCTYPE,
		{
			"kind": "Export",
			"status": second.APPROVED,
			"asked_by": frappe.session.user,
			"export_from": doctype,
			"records": [">=", records],
			"used_on": ["is", "not set"],
			"decided_on": [">=", add_days(now_datetime(), -KEPT_FOR)],
		},
		"name",
	)


def held(doctype: str, records: int, method: str):
	"""None when the person may export `records` of a kind now: within the
	limit, or approved (which is then used). Else the waiting Export
	approval, asked of the administrators the first time."""
	most = limit()
	if not most or records <= most:
		return None
	approved = _approved(doctype, records)
	if approved:
		frappe.db.set_value(second.DOCTYPE, approved, "used_on", now_datetime(), update_modified=False)
		return None
	return asked(doctype, records, method)


def asked(doctype: str, records: int, method: str):
	"""An export of `records` of a kind, waiting for an administrator."""
	row, new = second.ask(
		"Export",
		_("Export of {0} {1}").format(fmt_money(records, precision=0), _(doctype)),
		[_("More than {0} records").format(fmt_money(limit(), precision=0))],
		roles.ADMINISTRATOR,
		{"export_from": doctype, "asked_by": second.asker()},
		records=records,
		method=method,
	)
	if not new and cint(row.records) < records:
		row.records = records
		row.flags.ignore_permissions = True
		row.save()
	if new:
		tell.export_waiting(row, second.deciders(row))
	return row


def rows(content, filename: str = "") -> int:
	"""The records in an exported file: its rows less the heading. Pure."""
	if content is None:
		return 0
	raw = content if isinstance(content, bytes) else str(content).encode()
	if raw[:2] == b"PK" or filename.endswith(".xlsx"):
		from openpyxl import load_workbook

		book = load_workbook(io.BytesIO(raw), read_only=True)
		return max(0, sum(sheet.max_row or 0 for sheet in book.worksheets) - 1)
	return max(0, sum(1 for line in csv.reader(io.StringIO(raw.decode("utf-8-sig", "replace"))) if line) - 1)


def _counted() -> int:
	return rows(frappe.response.get("filecontent") or frappe.response.get("result"), frappe.response.get("filename") or "")


def _kept(doctype: str, method: str) -> None:
	"""After frappe made the file: sent, or held and a page in its place."""
	row = held(doctype, _counted(), method)
	if row:
		for name in NAMES:
			frappe.response.pop(name, None)
		_page(row)


def _back() -> str:
	"""Where the page's Back goes: the screen the export was asked from, on
	this site, else the desk."""
	request = getattr(frappe.local, "request", None)
	came = request.headers.get("Referer") if request else None
	return came if came and came.startswith(frappe.utils.get_url()) else "/desk"


def _page(row) -> None:
	frappe.respond_as_web_page(
		_("Export Waiting for Approval"),
		_("Exporting {0} {1} needs a workspace administrator's approval. They have been asked, and you are told when one decides.").format(
			fmt_money(row.records, precision=0), _(row.export_from)
		),
		indicator_color="orange",
		http_status_code=403,
		primary_action=_back(),
		primary_label=_("Back"),
	)


@frappe.whitelist(methods=["POST"])
def report_view():
	"""frappe's Export of a list, the report view and the report builder."""
	from frappe.desk import reportview
	from frappe.desk.utils import pop_csv_params

	form = frappe._dict(frappe.local.form_dict)
	doctype = form.get("doctype")
	if not cint(form.get("export_in_background")):
		reportview.export_query()
		return _kept(doctype, _("Report View"))
	params = reportview.get_form_params()
	params["limit_page_length"] = None
	params["as_list"] = True
	csv_params = pop_csv_params(params)
	params.pop("with_link_titles", None)
	params.pop("export_in_background", None)
	_later("report_view_job", form_params=params, csv_params=csv_params)


def report_view_job(user_email: str, form_params, csv_params) -> None:
	from frappe.desk import reportview
	from frappe.desk.utils import send_report_email

	doctype = form_params.get("doctype")
	name, extension, content = reportview._export_query(form_params, csv_params, populate_response=False)
	if not _held_later(doctype, rows(content, f".{extension}"), _("Report View")):
		send_report_email(user_email, name, extension, content, attached_to_name=name)


@frappe.whitelist(methods=["POST"])
def query_report():
	"""frappe's Export of a report."""
	from frappe.desk import query_report as reports
	from frappe.desk.utils import pop_csv_params

	form = frappe._dict(frappe.local.form_dict)
	doctype = frappe.get_cached_value("Report", form.get("report_name"), "ref_doctype")
	if not cint(form.get("export_in_background")):
		reports.export_query()
		return _kept(doctype, _("Report"))
	csv_params = pop_csv_params(form)
	reports.clean_params(form)
	reports.parse_json(form)
	frappe.permissions.can_export(doctype, raise_exception=True)
	_later("query_report_job", form_params=form, csv_params=csv_params)


def query_report_job(user_email: str, form_params, csv_params) -> None:
	from frappe.desk import query_report as reports
	from frappe.desk.utils import send_report_email

	doctype = frappe.get_cached_value("Report", form_params.report_name, "ref_doctype")
	name, extension, content = reports._export_query(form_params, csv_params, populate_response=False)
	if not _held_later(doctype, rows(content, f".{extension}"), _("Report")):
		send_report_email(user_email, name, extension, content, attached_to_name=form_params.report_name)


def _later(job: str, **kwargs) -> None:
	"""An export frappe makes in the background and mails, as frappe enqueues
	it, counted in the job."""
	user_email = frappe.get_cached_value("User", frappe.session.user, "email")
	frappe.enqueue(f"onedesk.one.exports.{job}", user_email=user_email, queue="long", now=frappe.flags.in_test, **kwargs)
	frappe.msgprint(
		_(
			"Your report is being generated in the background. You will receive an email on {0} with a download link once it is ready."
		).format(user_email)
	)


def _held_later(doctype: str, records: int, method: str) -> bool:
	row = held(doctype, records, method)
	if row:
		tell.export_held(row)
	return bool(row)


@frappe.whitelist(methods=["POST"])
def data_export(
	doctype: str | list | None = None,
	parent_doctype: str | None = None,
	all_doctypes: bool | int | str = True,
	with_data: bool | int | str = False,
	select_columns: str | dict | None = None,
	file_type: str = "CSV",
	template: bool | str = False,
	filters: str | dict | list | None = None,
	export_without_column_meta: bool | str = False,
):
	"""frappe's Data Export."""
	from frappe.core.doctype.data_export import exporter

	exporter.export_data(
		doctype=doctype,
		parent_doctype=parent_doctype,
		all_doctypes=all_doctypes,
		with_data=with_data,
		select_columns=select_columns,
		file_type=file_type,
		template=template,
		filters=filters,
		export_without_column_meta=export_without_column_meta,
	)
	_kept(doctype[0] if isinstance(doctype, list) else doctype, _("Data Export"))


@frappe.whitelist(methods=["POST"])
def data_import_export(
	doctype: str,
	export_fields: str | dict | None = None,
	export_records: str | None = None,
	export_filters: str | dict | list | None = None,
	file_type: str = "CSV",
):
	"""Data Import's Export Data, a template with the records in it."""
	from frappe.core.doctype.data_import import data_import

	data_import.download_template(
		doctype, export_fields=export_fields, export_records=export_records, export_filters=export_filters, file_type=file_type
	)
	if export_records != "blank_template":
		_kept(doctype, _("Data Import"))


@frappe.whitelist(methods=["POST"])
def zip_files(files: str):
	"""The file list's Download, several files in one zip."""
	from frappe.core.api import file

	picked = frappe.parse_json(files) or []
	row = held("File", len(picked), _("Download"))
	if row:
		return _page(row)
	return file.zip_files(files)


@frappe.whitelist(methods=["POST"])
def may_export(doctype: str, records: int, method: str | None = None) -> dict:
	"""Before a screen of ours downloads several records at once (OneCloud's
	Download): whether it may, or the approval it now waits for."""
	frappe.has_permission(doctype, "read", throw=True)
	row = held(doctype, cint(records), method or _("Download"))
	if not row:
		return {"allowed": True}
	return {
		"allowed": False,
		"approval": row.name,
		"message": _("Downloading {0} files needs a workspace administrator's approval. They have been asked, and you are told when one decides.").format(
			fmt_money(row.records, precision=0)
		),
	}
