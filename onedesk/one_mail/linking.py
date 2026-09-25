"""Mail and records: which messages belong to which customer, supplier,
employee, lead or document.

A message's links are Frappe's own `timeline_links` (Communication Link
rows), so a message shows on several records at once and Frappe's timeline
reads them. Each row says how it was made, in `one_linked_by`, since a link
nobody can explain is one nobody will trust:
- **contact**: Frappe's own, from a Contact with the address and whatever
  that contact is linked to. Rows Frappe makes carry no mark and read as this.
- **address**: an Employee or Lead with the address, which contacts do not
  reach.
- **thread**: a reply takes the links of the conversation it joins.
- **text**: a document named in the subject or the new part of the message,
  by a prefix of a naming series this site issues, and only if that document
  exists. The quoted history of a reply is not read: its names were found
  when those messages arrived.
- **manual**: somebody filed it, or sent it from the record.

**A link never grants read.** Linking a message to a customer does not show
it to everybody who can read the customer: it opens only for the people who
hold its mailbox (access.py), and a record's Mail tab and timeline list only
the messages the reader may open (`visible`).
"""

import re

import frappe
from frappe import _, _lt

from onedesk.one_mail import actions, live

#: Documents a message may be found to name in its text, by their naming series.
NAMED = (
	"Sales Invoice", "Purchase Invoice", "Sales Order", "Purchase Order", "Quotation", "Supplier Quotation",
	"Delivery Note", "Purchase Receipt", "Payment Entry", "Material Request", "Request for Quotation",
	"Opportunity", "Issue", "Project", "Task", "Job Applicant", "Expense Claim",
)  # fmt: skip

#: The Mail tab, on the records mail is about: the conversations filed on
#: one, and a way to write from it (record_mail.js). See one/tabs.py.
TABS = [
	{
		"name": "mail",
		"label": _lt("Mail"),
		"order": 70,
		"doctypes": (
			"Customer",
			"Supplier",
			"Lead",
			"Contact",
			"Employee",
			"Opportunity",
			"Project",
			"Issue",
			"Job Applicant",
			"Quotation",
			"Sales Order",
			"Sales Invoice",
			"Purchase Order",
			"Purchase Invoice",
			"Supplier Quotation",
		),
	}
]

#: The records an address is looked up on, beyond Frappe's contacts: (doctype, fields).
BY_ADDRESS = (
	("Employee", ("company_email", "personal_email", "prefered_email")),
	("Lead", ("email_id",)),
)

#: Where the quoted history of a reply begins, in text or HTML.
QUOTED = re.compile(
	r"(<blockquote|<div class=\"gmail_quote|-----\s*Original Message|^On .{0,200} wrote:$|^>)",
	re.IGNORECASE | re.MULTILINE,
)

#: Most documents one message is linked to by its text.
MOST_NAMED = 10


# ------------------------------------------------------------------ pure


def fresh_part(content: str | None) -> str:
	"""A message without the history it quotes. Pure."""
	content = content or ""
	found = QUOTED.search(content)
	return content[: found.start()] if found else content


def prefixes(options: str | None) -> list[str]:
	"""The fixed start of each naming series in a Select's options, such as
	`ACC-SINV-` from `ACC-SINV-.YYYY.-`. Pure."""
	out = []
	for line in (options or "").splitlines():
		head = line.strip().split(".", 1)[0]
		if len(head) >= 3 and re.fullmatch(r"[A-Za-z0-9-/]+", head):
			out.append(head)
	return out


def candidates(text: str, starts: list[str]) -> list[str]:
	"""Words in `text` that begin with one of `starts` and go on to a number.
	Pure."""
	if not starts:
		return []
	pattern = re.compile(
		r"(?<![A-Za-z0-9-])(?:"
		+ "|".join(re.escape(one) for one in sorted(starts, key=len, reverse=True))
		+ r")[A-Za-z0-9./-]*\d"
	)
	return list(dict.fromkeys(pattern.findall(text or "")))


# ------------------------------------------------------------------ making links


def held_links(name: str) -> set[tuple[str, str]]:
	return {
		(row.link_doctype, row.link_name)
		for row in frappe.get_all(
			"Communication Link", filters={"parent": name}, fields=["link_doctype", "link_name"]
		)
	}


def add(name: str, doctype: str, docname: str, by: str) -> bool:
	"""Link a message to a record, once. The first record that is not a
	contact also becomes the message's reference, which the framework's own
	reply matching reads."""
	if (doctype, docname) in held_links(name) or not frappe.db.exists(doctype, docname):
		return False
	title_field = frappe.get_meta(doctype).get_title_field()
	row = frappe.get_doc(
		{
			"doctype": "Communication Link",
			"parent": name,
			"parenttype": "Communication",
			"parentfield": "timeline_links",
			"idx": len(held_links(name)) + 1,
			"link_doctype": doctype,
			"link_name": docname,
			"link_title": frappe.db.get_value(doctype, docname, title_field)
			if title_field != "name"
			else None,
			"one_linked_by": by,
		}
	)
	row.db_insert()
	if doctype != "Contact" and not frappe.db.get_value("Communication", name, "reference_name"):
		frappe.db.set_value(
			"Communication",
			name,
			{"reference_doctype": doctype, "reference_name": docname},
			update_modified=False,
		)
	return True


def arrived(doc) -> None:
	"""A message read from a mailbox (inbound.Arrival) is linked by its
	thread, its addresses and the documents it names."""
	if doc.communication_medium != "Email" or not doc.one_folder:
		return
	for doctype, docname in from_thread(doc):
		add(doc.name, doctype, docname, "thread")
	for doctype, docname in by_address(doc):
		add(doc.name, doctype, docname, "address")
	for doctype, docname in from_text(doc):
		add(doc.name, doctype, docname, "text")


def from_thread(doc) -> list[tuple[str, str]]:
	if not doc.one_thread:
		return []
	C, L = frappe.qb.DocType("Communication"), frappe.qb.DocType("Communication Link")
	rows = (
		frappe.qb.from_(L)
		.join(C)
		.on(L.parent == C.name)
		.where(C.one_thread == doc.one_thread)
		.where(C.name != doc.name)
		.where(L.link_doctype != "Contact")
		.select(L.link_doctype, L.link_name)
		.distinct()
		.run()
	)
	return [tuple(row) for row in rows]


def _addresses(doc) -> list[str]:
	from email.utils import getaddresses

	mine = {row.lower() for row in frappe.get_all("Email Account", pluck="email_id") if row}
	found = [
		one.lower()
		for _name, one in getaddresses([doc.sender or "", doc.recipients or "", doc.cc or ""])
		if one
	]
	return [one for one in dict.fromkeys(found) if one not in mine]


def by_address(doc) -> list[tuple[str, str]]:
	out = []
	addresses = _addresses(doc)
	if not addresses:
		return out
	for doctype, fields in BY_ADDRESS:
		if not frappe.db.exists("DocType", doctype):
			continue
		meta = frappe.get_meta(doctype)
		for field in fields:
			if meta.has_field(field):
				out += [
					(doctype, one)
					for one in frappe.get_all(doctype, filters={field: ["in", addresses]}, pluck="name")
				]
	return list(dict.fromkeys(out))


def starts() -> dict[str, str]:
	"""Each naming-series prefix this site issues, and whose it is."""
	cached = frappe.cache.get_value("one_mail_series")
	if cached:
		return cached
	out = {}
	for doctype in NAMED:
		if not frappe.db.exists("DocType", doctype):
			continue
		field = frappe.get_meta(doctype).get_field("naming_series")
		for prefix in prefixes(field.options if field else None):
			out.setdefault(prefix, doctype)
	frappe.cache.set_value("one_mail_series", out, expires_in_sec=3600)
	return out


def from_text(doc) -> list[tuple[str, str]]:
	known = starts()
	text = f"{doc.subject or ''}\n{fresh_part(doc.content)}"
	out = []
	for word in candidates(text, list(known)):
		prefix = max((one for one in known if word.startswith(one)), key=len)
		# A prefix match is a guess; the document existing is not.
		if frappe.db.exists(known[prefix], word):
			out.append((known[prefix], word))
		if len(out) >= MOST_NAMED:
			break
	return out


# ------------------------------------------------------------------ reading


def visible(names: list[str], user: str | None = None) -> set[str]:
	"""Which of these messages the reader may open: those in no mailbox, and
	those in a mailbox they hold."""
	user = user or frappe.session.user
	if not names:
		return set()
	rows = frappe.get_all(
		"Communication",
		filters={"name": ["in", names]},
		fields=["name", "email_account", "communication_medium"],
	)
	if user == "Administrator":
		return {row.name for row in rows}
	held = set(frappe.get_all("User Email", filters={"parent": user}, pluck="email_account"))
	return {
		row.name
		for row in rows
		if row.communication_medium != "Email" or not row.email_account or row.email_account in held
	}


@frappe.whitelist()
def record(doctype: str, name: str) -> list[dict]:
	"""A record's correspondence, as conversations, newest first: only the
	messages the reader may open."""
	frappe.get_lazy_doc(doctype, name).check_permission("read")
	L = frappe.qb.DocType("Communication Link")
	linked = set(
		frappe.qb.from_(L)
		.where(L.link_doctype == doctype)
		.where(L.link_name == name)
		.select(L.parent)
		.run(pluck=True)
	) | set(
		frappe.get_all(
			"Communication", filters={"reference_doctype": doctype, "reference_name": name}, pluck="name"
		)
	)
	names = visible(list(linked))
	if not names:
		return []
	rows = frappe.get_all(
		"Communication",
		filters={"name": ["in", list(names)], "communication_medium": "Email"},
		fields=["name", "subject", "sender", "sender_full_name", "recipients", "communication_date", "email_account", "one_thread", "sent_or_received", "seen", "has_attachment", "content"],
		order_by="communication_date desc",
	)  # fmt: skip
	from onedesk.one_mail.api import snippet

	threads = {}
	for row in rows:
		key = (row.email_account, row.one_thread or row.name)
		if key in threads:
			threads[key]["count"] += 1
			continue
		threads[key] = {
			"account": row.email_account,
			"thread": row.one_thread or row.name,
			"subject": row.subject,
			"sender": row.sender,
			"sender_name": row.sender_full_name,
			"sent": int(row.sent_or_received == "Sent"),
			"recipients": row.recipients,
			"date": row.communication_date,
			"snippet": snippet(row.content),
			"attachments": row.has_attachment,
			"count": 1,
		}
	return list(threads.values())


@frappe.whitelist()
def links_of(names) -> list[dict]:
	"""The records the messages of a conversation are on, but their contacts."""
	names = frappe.parse_json(names) if isinstance(names, str) else names
	names = list(visible(names or []))
	if not names:
		return []
	rows = frappe.get_all(
		"Communication Link",
		filters={"parent": ["in", names], "link_doctype": ["!=", "Contact"]},
		fields=["link_doctype", "link_name", "link_title", "one_linked_by"],
		distinct=True,
	)
	seen, out = set(), []
	for row in rows:
		if (row.link_doctype, row.link_name) not in seen and frappe.has_permission(
			row.link_doctype, "read", row.link_name
		):
			seen.add((row.link_doctype, row.link_name))
			out.append(row)
	return out


@frappe.whitelist(methods=["POST"])
def file(names, doctype: str, docname: str) -> int:
	"""File messages on a record, by hand."""
	names = _mine(names)
	frappe.get_lazy_doc(doctype, docname).check_permission("read")
	made = sum(add(name, doctype, docname, "manual") for name in names)
	live.changed(*{frappe.db.get_value("Communication", name, "email_account") for name in names})
	return made


@frappe.whitelist(methods=["POST"])
def unfile(names, doctype: str, docname: str) -> None:
	"""Take messages off a record."""
	names = _mine(names)
	for name in names:
		frappe.db.delete(
			"Communication Link", {"parent": name, "link_doctype": doctype, "link_name": docname}
		)
		reference = frappe.db.get_value("Communication", name, ["reference_doctype", "reference_name"])
		if tuple(reference) == (doctype, docname):
			frappe.db.set_value(
				"Communication",
				name,
				{"reference_doctype": None, "reference_name": None},
				update_modified=False,
			)
	live.changed(*{frappe.db.get_value("Communication", name, "email_account") for name in names})


def _mine(names) -> list[str]:
	names = frappe.parse_json(names) if isinstance(names, str) else names
	accounts = set(
		frappe.get_all("Communication", filters={"name": ["in", names or [""]]}, pluck="email_account")
	)
	for account in accounts:
		if not account:
			frappe.throw(_("A message that belongs to no mailbox cannot be filed here."))
		actions.require(account)
	return names


# ------------------------------------------------------------------ the timeline


def _filter(messages: list) -> list:
	keep = visible([one.get("name") for one in messages])
	return [one for one in messages if one.get("name") in keep]


def _filter_response() -> None:
	docinfo = frappe.response.get("docinfo")
	if docinfo and docinfo.get("communications"):
		docinfo["communications"] = _filter(docinfo["communications"])


@frappe.whitelist()
def getdoc(doctype: str, name: str | int):
	"""Frappe's form load, with the timeline's mail narrowed to what the
	reader may open."""
	from frappe.desk.form import load

	answer = load.getdoc(doctype, name)
	_filter_response()
	return answer


@frappe.whitelist()
def get_docinfo(doc=None, doctype: str | None = None, name: str | int | None = None):
	from frappe.desk.form import load

	load.get_docinfo(doc, doctype, name)
	_filter_response()


@frappe.whitelist()
def get_communications(doctype: str, name: str | int, start: str | int = 0, limit: str | int = 20):
	from frappe.desk.form import load

	return _filter(load.get_communications(doctype, name, start, limit))
