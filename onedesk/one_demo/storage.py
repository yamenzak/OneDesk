"""OneCloud as the team uses it: a Projects library Samir runs with the site
team in it, the villa's elevations there with a link for the customer and a
second version, Samir's site visit notes shared with Rania, a request to a
supplier for its papers, and a drive password for the office laptop."""

import frappe

from onedesk.one_demo.base import ahead, as_user

PM = "samir@one.test"
LIBRARY = "Projects"
ELEVATIONS = "Mansour villa elevations.pdf"
SUPPLIER = "sales@alnoor.example"
NOTES = "Mansour site visit notes.txt"
NOTES_SAID = "Ground floor frames in. Sill on W03 needs packing. Khalid wants the balustrade glass clear, not tinted."


def run(password=None):
	from onedesk.one_cloud import dav, file_requests, library, links, share, upload
	from onedesk.one_cloud import namespace as ns

	with as_user(PM):
		root = frappe.db.get_value("File", {"one_library": 1, "file_name": LIBRARY})
		if not root:
			root = library.make(LIBRARY)["id"]
			library.add(root, ["rania@one.test", "tariq@one.test"], "Member")
			library.add(root, ["yousef@one.test"], "Reader")
		if not frappe.db.exists("File", {"folder": root, "file_name": ELEVATIONS}):
			first = upload._place(root, None, {"file_name": ELEVATIONS, "content": _pdf("Elevations, first issue")})
			links.make(first["id"])
			upload._place(root, None, {"file_name": ELEVATIONS, "content": _pdf("Elevations, revision B")}, replace=1)
		notes = frappe.db.get_value("File", {"owner": PM, "file_name": NOTES})
		if not notes:
			notes = upload._place(ns.home(PM), None, {"file_name": NOTES, "content": NOTES_SAID.encode()})["id"]
			share.share([notes], ["rania@one.test"])
		if not frappe.db.exists("Cloud Drive Password", {"user": PM}):
			dav.make_password("Office laptop")
	with as_user("karim@one.test"):
		if not frappe.db.exists("Cloud File Request", {"title": "Al Noor papers for this year"}):
			file_requests.make(
				ns.home("karim@one.test"),
				{
					"title": "Al Noor papers for this year",
					"message": "Please send this year's trade licence and VAT certificate.",
					"due_date": str(ahead(14)),
					"items": [{"label": "Trade licence", "required": 1}, {"label": "VAT certificate", "required": 1}],
					"recipients": SUPPLIER,
				},
			)


def _pdf(line: str) -> bytes:
	"""A one-page PDF that says `line`, written out rather than shipped."""
	text = f"BT /F1 24 Tf 72 720 Td ({line}) Tj ET".encode()
	objects = [
		b"<< /Type /Catalog /Pages 2 0 R >>",
		b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
		b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
		b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text + b"\nendstream",
		b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
	]
	out, offsets = b"%PDF-1.4\n", []
	for number, body in enumerate(objects, 1):
		offsets.append(len(out))
		out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"
	start = len(out)
	out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
	out += b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets)
	out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{start}\n%%EOF\n".encode()
	return out
