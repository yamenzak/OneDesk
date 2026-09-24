"""The tax year's documents, in one download (docs/INTAKE.md §16.6).

A tax adviser asks for the same things every spring: the invoices and
receipts, the payslips, the bank statements, the tax office's letters and
the contracts, for one year. They have all been read already, so this is a
zip of them by kind, with a list of every document, its date, whom it is
from and its amount, that opens in any spreadsheet.

A reader gets what was read for them; an administrator of the workspace gets
the workspace's. Only a file the reader may open goes in, as everywhere
else. A DATEV-shaped export for a business is not built.
"""

import csv
import io
import re
import zipfile
from typing import Annotated

import frappe
from frappe import _

from onedesk.one_intake import search

#: What a tax adviser asks for.
KINDS = (
	"Invoice", "Credit Note", "Receipt", "Payslip", "Bank Statement", "Payment Advice", "Tax Assessment",
	"Letter From an Authority", "Contract", "Certificate",
)  # fmt: skip

#: The most documents one download holds.
MOST = 3000


@frappe.whitelist()
def year(year: Annotated[int, "The tax year, as four digits."]) -> None:
	"""The year's documents as a zip, by kind, with an index."""
	from onedesk.one.roles import administers

	year = int(year)
	rows = documents(year, None if administers() else frappe.session.user)
	frappe.response.filename = f"{_('Documents')} {year}.zip"
	frappe.response.filecontent = packed(year, rows)
	frappe.response.type = "download"


def documents(year: int, person: str | None) -> list[dict]:
	"""The year's readings of the kinds an adviser asks for, each with the
	file the reader may open. A batch scan is its letters, not itself."""
	conditions = [
		"state = 'Understood'",
		"kind in %(kinds)s",
		"ifnull(copy_of, '') = ''",
		"year(ifnull(issued_on, creation)) = %(year)s",
		"name not in (select part_of from `tabReading` where ifnull(part_of, '') != '')",
	]
	values = {"kinds": KINDS, "year": year}
	if person:
		conditions.append("on_behalf_of = %(person)s")
		values["person"] = person
	rows = frappe.db.sql(
		f"""select name, title, kind, number, issued_on, gross, currency, part_of, message_id, source_doctype, source_name, `key`
		from `tabReading` where {" and ".join(conditions)} order by issued_on, creation limit {MOST}""",
		values,
		as_dict=True,
	)
	out = []
	for row in rows:
		files = search.files_of({**search.root_of(row), "name": row.name})
		if not files:
			continue
		party = frappe.db.get_value("Reading Party", {"parent": row.name, "role": ["in", ("Sender", "Paid To", "Holder")]}, "party_name")
		out.append({**row, "file": files[0], "party": party})
	return out


def packed(year: int, rows: list[dict]) -> bytes:
	"""The zip: a folder per kind, and index.csv."""
	buffer = io.BytesIO()
	taken: set[str] = set()
	index = io.StringIO()
	writer = csv.writer(index)
	writer.writerow([_("Date"), _("Kind"), _("From"), _("Number"), _("Amount"), _("Currency"), _("Title"), _("File")])
	with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as out:
		for row in rows:
			said = row["kind"]
			kind = _(said)
			path = unique(f"{year}/{safe(kind)}/{safe(row['file'].file_name)}", taken)
			content = frappe.get_doc("File", row["file"].name).get_content()
			out.writestr(path, content if isinstance(content, bytes) else content.encode())
			writer.writerow([row.get("issued_on") or "", kind, row.get("party") or "", row.get("number") or "", row.get("gross") or "", row.get("currency") or "", row.get("title") or "", path])
		out.writestr(f"{year}/index.csv", "\ufeff" + index.getvalue())
	return buffer.getvalue()


def safe(name: str) -> str:
	"""A name every operating system accepts as a file or folder. Pure."""
	cleaned = " ".join(re.sub(r'[\\/:*?"<>|\x00-\x1f]+', " ", str(name or "")).split()).strip(" .")
	return cleaned[:120] or "document"


def unique(path: str, taken: set) -> str:
	"""The path, or the path with (2), (3)… when it is already in the zip. Pure."""
	stem, dot, ext = path.rpartition(".") if "." in path.rsplit("/", 1)[-1] else (path, "", "")
	found, count = path, 1
	while found in taken:
		count += 1
		found = f"{stem} ({count}).{ext}" if dot else f"{path} ({count})"
	taken.add(found)
	return found
