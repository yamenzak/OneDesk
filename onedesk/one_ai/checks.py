"""OneAI's part of the integration suite (one_demo/check.py runs it):
AICenter as an administrator and as somebody who isn't, and web search only
while its service is on."""

import json

import frappe
from frappe.utils import add_days, getdate, today

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import VILLA, _each_way, check
from onedesk.one_demo.people import OWNER


@check
def a_folder_reads_for_whoever_turned_it_on():
	with as_user("samir@one.test"):
		folder = frappe.get_doc({"doctype": "File", "file_name": f"Site Photos {frappe.generate_hash(length=6)}", "is_folder": 1, "folder": "Home"}).insert()
	for way, got in _each_way("samir@one.test", "File", folder.name, {"one_intake": 1, "one_intake_for": "omar@one.test"}).items():
		assert not isinstance(got, Exception), (way, got)
		assert got.one_intake_for == "samir@one.test", (way, got)


@check
def oneai_is_not_offered_as_a_recipient():
	"""The Email dialog suggests contacts. OneAI's account has none, so it is
	never offered as somebody to write to."""
	from frappe.email import get_contact_list

	from onedesk.one_hr import hiring

	assert not frappe.db.exists("Contact", {"user": hiring.AUTHOR}), "OneAI has a contact"
	assert hiring.AUTHOR not in [one.value for one in get_contact_list("oneai")], "OneAI is offered as a recipient"


def _sample(stem: str) -> str:
	"""The reading a kept Intake sample made in the demo."""
	from onedesk.one_demo import samples

	return samples.readings_of(next(path for path in samples.samples() if path.stem == stem))[0]


@check
def oneintake_layla_works_through_what_oneai_read():
	"""Layla's Intake inbox as she works it: what waits and what is done, a
	document opened and explained, the expense claim the auditor doubted kept,
	the new employee OneAI proposed turned down and a contact taken back, a task undone, a
	mark cleared, the drafts submitted, a duplicate supplier cleared and
	another merged, her mailbox switched off and on, and the year's documents
	as a zip. OneAI finds a document by its words."""
	from unittest import mock

	from onedesk.one_ai.reading import (
		act,
		agent,
		bundle,
		drafts,
		explain,
		identity,
		inbox,
		mark,
		panel,
		switches,
	)
	from onedesk.one_demo import intake

	doubted = _sample("taxi-receipt-doubted")
	with as_user(OWNER):
		before = inbox.counts()
		waiting = {one["name"] for one in inbox.listing("waiting")["items"]}
		assert doubted in waiting and before["waiting"] >= 2, (before, waiting)
		assert len(inbox.listing("done")["items"]) >= 15
		opened = inbox.item(doubted)
		wrong = next(one for one in opened["actions"] if one.get("audit") == "Wrong")
		assert inbox.keep(wrong["name"]) == {"audit": "Kept"}
		assert doubted not in {one["name"] for one in inbox.listing("waiting")["items"]}
		assert inbox.seen_all("done") >= 15 and inbox.counts()["unread"] < before["unread"]
		said = {"explanation": "Tariq paid for a taxi and asks for the fare back.", "todo": [{"what": "Approve the fare", "by": None}], "reply": "", "reply_language": "en"}
		with mock.patch("onedesk.one_ai.run.once", return_value=frappe.as_json(said)) as asked:
			assert explain.explain(doubted)["explanation"] == said["explanation"]
			explain.explain(doubted)
			assert asked.call_count == 1, "explained once, then read back"

		contract = _sample("signed-contract")
		proposed = frappe.get_all("Reading Action", filters={"reading": contract, "level": "Proposed"}, pluck="name")[0]
		act.settle(proposed, 0)
		assert frappe.db.get_value("Reading Action", proposed, "level") != "Proposed"
		contact = frappe.db.get_value("Reading Action", {"reading": contract, "target_doctype": "Contact", "level": "Done"}, "name")
		assert act.undo_one(contact)["undone"] == 1
		drawings = _sample("drawings-request")
		task = frappe.db.get_value("Reading Action", {"reading": drawings, "target_doctype": "Task", "level": "Done"}, "target_name")
		assert act.undo(drawings)["undone"] >= 1 and not frappe.db.exists("Task", task)

		marked = [
			one
			for one in frappe.get_all("AI Touch", filters={"for_doctype": "Task", "fieldname": mark.WHOLE}, pluck="record")
			if frappe.has_permission("Task", "write", one)
		]
		assert marked, "no task OneAI made that Layla may change"
		mark.looks_right("Task", marked[0])
		assert not mark.is_marked("Task", marked[0])

		listed = drafts.listed()
		ready = listed["ready"]
		assert not listed["red"], listed["red"]
		bill = next(one for one in ready if one["doctype"] == "Purchase Invoice")
		assert frappe.db.get_value("Purchase Invoice", bill["name"], "taxes_and_charges"), "a bill carries the VAT its document charges"
		receipt = next(one for one in ready if one["doctype"] == "Purchase Receipt")
		done = drafts.submit_all([[receipt["doctype"], receipt["name"]]])
		assert frappe.db.get_value("Purchase Receipt", receipt["name"], "docstatus") == 1, done

		known = frappe.get_all("Supplier", filters={"email_id": ["is", "set"]}, fields=["name", "email_id"], limit=1)[0]
		twice = frappe.get_doc({"doctype": "Supplier", "supplier_name": f"{known.name} Trading", "supplier_group": frappe.db.get_value("Supplier", known.name, "supplier_group"), "email_id": known.email_id}).insert()
		assert frappe.db.get_value("Supplier", twice.name, "one_duplicate_of") == known.name
		identity.not_duplicate("Supplier", twice.name)
		assert not frappe.db.get_value("Supplier", twice.name, "one_duplicate_of")
		assert identity.merge("Supplier", twice.name, known.name) == known.name and not frappe.db.exists("Supplier", twice.name)

		mailbox = intake.mailbox()
		assert switches.mailbox_state(mailbox)["on"]
		assert not switches.set_mailbox(mailbox, 0)["on"] and switches.set_mailbox(mailbox, 1)["on"]
		mail = frappe.db.get_value("Reading", doubted, "source_name")
		assert panel.for_message(mail)["name"] == doubted
		bundle.year(getdate(today()).year)
		assert frappe.response["filecontent"][:2] == b"PK", "a zip"
		assert agent.find_documents("taxi")["documents"]

	with as_user(intake.ACCOUNTS):
		folder = intake.folder()
		assert switches.folder_state(folder)["on"]
		assert not switches.set_folder(folder, 0)["on"] and switches.set_folder(folder, 1)["on"]
		statement = frappe.get_all("File", filters={"folder": folder}, pluck="name")[0]
		assert panel.for_file(statement)["kind"] == "Bank Statement"
	with as_user("samir@one.test"):
		schedule = frappe.db.get_value("File", {"attached_to_name": VILLA, "file_name": "Window schedule.csv"})
		with mock.patch("onedesk.one_ai.reading.pipeline.later") as later:
			switches.read_now(schedule)
		assert later.call_args.args[0] == "read_file"


@check
def oneai_is_told_what_every_place_shows():
	"""Every entry on every space's rail and every desk page tells OneAI more
	than its title: a report its filters, a dashboard its charts, a home what it
	opens, a page what is on it (one_ai/here.py)."""
	from onedesk.one_ai import here

	frappe.set_user("Administrator")
	missed = here.untold()
	assert not missed, "OneAI is told only the title of: " + "; ".join(
		f"{one['space']} › {one['label']} {one['sent']}" for one in missed
	)


@check
def oneai_a_conversation_its_cards_and_its_settings():
	"""Omar's conversation with OneAI from start to forgotten, the cards it
	suggests waiting, refused, applied and taken into a form, and Layla's
	OneAI settings, where nothing about a model is set. A model is not
	called: what the account and the model would say is said here."""
	from unittest import mock

	from onedesk.one import ai_workspace
	from onedesk.one_ai import center, chat, files, proposals, run
	from onedesk.one_crm import agent as crm

	deal = frappe.db.get_value("Opportunity", {"title": "Webb Hotel lobby curtain wall"})
	with as_user("omar@one.test"):
		started = chat.start()
		assert chat.rename(started["name"], "Webb hotel follow-up")["title"] == "Webb hotel follow-up"
		with mock.patch("frappe.enqueue") as queued:
			said = chat.say("What is next on the Webb hotel deal?", started["name"], {"doctype": "Opportunity", "name": deal})
		assert said["run"] and queued.call_args.kwargs["chat"] == started["name"]
		assert chat.opened(started["name"])["said"] and started["name"] in {one.name for one in chat.chats()}
		assert chat.progress(said["run"])["chat"] == started["name"]
		assert files.attached(started["name"]) == []
		assert chat.suggestions({"doctype": "Opportunity", "name": deal})

		card = crm.plan_next_step("Opportunity", deal, "Call to agree the price", str(add_days(today(), 2)))["proposal"]
		other = crm.add_lead("Joanna Pike", "joanna@pike.example", "Pike Hotels")["proposal"]
		assert {card, other} <= {one["name"] for one in run.waiting()}
		assert {one["name"] for one in chat.cards([card, other])} == {card, other}
		run.refuse(other)
		assert frappe.db.get_value("AI Proposal", other, "state") == "Refused"
		assert run.took(card)["changes"]["one_next_step"] == "Call to agree the price"
		call = crm.write_up_call("Opportunity", deal, "They want the price by Thursday.")["proposal"]
		run.apply(call)
		assert frappe.db.get_value("AI Proposal", call, "state") == "Applied"
		field = frappe.get_doc("AI Proposal", proposals.propose("Edit", "Lead", {"company_name": "Pike Hotels"}))
		run.took(field.name)
		lead = frappe.get_doc({"doctype": "Lead", "first_name": "Joanna", "last_name": "Pike", "company_name": "Pike Hotels", "email_id": "jp@pikehotels.example"}).insert()
		assert run.landed(field.name, lead.name) == {"company_name": "Pike Hotels"}
		assert len(run.tools()) > 50
		used = run.use("crm_facts", {"record_type": "Opportunity", "name": deal})
		assert used["ran"] and used["answer"]["history"], used
		chat.forget(started["name"])
		assert not frappe.db.exists("AI Chat", started["name"])
	with as_user(OWNER):
		with mock.patch("onedesk.one.account.ask", return_value=[{"tier": "balanced", "credits": 0.4}]):
			held = center.state()
		assert set(held) == {"on", "tier", "tiers", "credits"} and held["tier"] in {"fast", "balanced", "full"}, "a workspace sets no model and no words"
		with (
			mock.patch("onedesk.one.account.configured", return_value=True),
			mock.patch("onedesk.one.account.ask", return_value={"actions": [{"action": chat.CHAT, "calls": 3, "credits": 1.5}]}),
		):
			said = ai_workspace.workspace_oneai()
		assert said["last_30_days"][0]["calls"] == 3 and said["summaries"], said


@check
def oneai_setup_cards_wait_for_approval_and_stay_within_bounds():
	"""What OneAI suggests to Layla changes nothing until she approves it. A
	report of something that is not a record, or a level that would not
	change, is sent back to be put right, and a level changed since its card
	was written is not changed again. A report by mail goes as whoever
	approved it. Omar may suggest no dashboard, show nothing to everybody,
	and approve no card of an administrator's."""
	from onedesk.one_ai import run as runs
	from onedesk.one_studio import ai_setup

	with as_user(OWNER):
		card = ai_setup.suggest_group("Night Crew", ["rania@one.test", "tariq@one.test"])
		assert card.get("proposal") and not frappe.db.exists("User Group", "Night Crew"), "made before it was approved"
		assert ai_setup.suggest_saved_report("Sales Invoice Item", "Lines", ["item_code"]).get("mend")
		assert ai_setup.suggest_saved_report("Sales Invoice", "Hidden", ["no_such_field"]).get("mend")
		assert "nothing would change" in ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Opportunity", "rights": ["read"]}]).get("error", "")
		first = ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Quotation", "rights": ["export"]}])
		second = ai_setup.suggest_level("OneCRM", "User", give=[{"doctype": "Quotation", "rights": ["export"]}])
		assert first.get("proposal") and second.get("proposal"), (first, second)
		runs.apply(first["proposal"])
		try:
			runs.apply(second["proposal"])
			raise AssertionError("a level was changed by a card written before it last changed")
		except frappe.ValidationError as stale:
			assert "no longer applies" in str(stale)
		mail = ai_setup.suggest_report_mail("Accounts Receivable", ["huda@one.test"], "Weekly", "Monday")
		runs.apply(mail["proposal"])
		assert frappe.db.get_value("Auto Email Report", {"report": "Accounts Receivable"}, "user") == OWNER
		changes = frappe.parse_json(frappe.db.get_value("AI Proposal", card["proposal"], "changes"))
	with as_user("omar@one.test"):
		assert ai_setup.suggest_dashboard("Mine", [{"title": "Deals", "doctype": "Opportunity", "measure": "count"}]).get("error")
		assert ai_setup.suggest_saved_report("Opportunity", "Everyone's deals", ["name"], everybody=True).get("mend")
		for what in ({**changes, "what": "mail", "doc": {"doctype": "Auto Email Report"}}, {"what": "level"}):
			try:
				ai_setup.apply(what)
				raise AssertionError("Omar approved an administrator's card")
			except frappe.PermissionError:
				pass


@check
def intake_fills_only_the_record_it_is_making():
	"""A supplier Intake makes from a document is given its name and what else
	it needs from that document. A supplier made by hand, or another kind made
	on the way, is never asked about."""
	from unittest import mock

	from onedesk.one_ai import kind
	from onedesk.one_ai.reading import fill

	reading = frappe.get_all("Reading", pluck="name", limit=1)[0]
	group = frappe.get_all("Supplier Group", filters={"is_group": 0}, pluck="name", limit=1)[0]
	asked = []

	def answer(doc, needs, reading):
		asked.append((doc.doctype, sorted(one["fieldname"] for one in needs)))
		return {"supplier_name": "Coastal Sealants", "supplier_group": group, kind.TYPED: "Coastal Sealants", "website": "never asked"}

	with as_user(OWNER), mock.patch.object(fill, "_ask", side_effect=answer):
		with fill.filling(reading, "Supplier"):
			made = frappe.get_doc({"doctype": "Supplier"}).insert()
			frappe.get_doc({"doctype": "Customer", "customer_name": "Made on the way"}).insert()
		frappe.get_doc({"doctype": "Supplier", "supplier_name": "Typed by hand", "supplier_group": group}).insert()
	assert made.supplier_name == "Coastal Sealants" and not made.website, made.as_dict()
	assert asked and {doctype for doctype, _fields in asked} == {"Supplier"}, asked
	assert any("supplier_name" in fields or kind.TYPED in fields for _doctype, fields in asked), asked


@check
def oneai_summarises_a_supplier_once_a_day():
	"""A purchase invoice submitted for Gulf Office Supplies marks it due; a
	draft saved does not. The hourly run writes its summary from what it is
	owed and bought, shows it in the supplier's head, and leaves it for a day
	however much happens. Switched off, nothing marks it due."""
	from unittest import mock

	from onedesk.one import head
	from onedesk.one_ai import brief

	supplier = frappe.db.sql(
		"select supplier from `tabPurchase Invoice` where docstatus = 1 group by supplier order by count(*) desc limit 1"
	)[0][0]
	invoice = frappe.get_doc("Purchase Invoice", frappe.db.get_value("Purchase Invoice", {"supplier": supplier, "docstatus": 1}))
	asked = []

	def said(action, text, files=None, reference=None):
		asked.append(text)
		return "AED 788 is unpaid and not yet due. Nothing is late."

	clear = {brief.BRIEF: None, brief.ON: None, brief.DUE: 0}
	try:
		frappe.db.set_value("Supplier", supplier, clear, update_modified=False)
		for kind in brief.BRIEFS:
			frappe.db.sql(f"update `tab{kind}` set `{brief.DUE}` = 0")
		with mock.patch("onedesk.one_ai.run.once", side_effect=said), mock.patch("onedesk.one.account.configured", return_value=True):
			brief.touched(invoice, "on_update")
			assert not frappe.db.get_value("Supplier", supplier, brief.DUE), "a draft saved is not news"
			brief.touched(invoice, "on_submit")
			assert frappe.db.get_value("Supplier", supplier, brief.DUE)
			assert brief.due() == 1
			assert frappe.db.get_value("Supplier", supplier, brief.BRIEF) == "AED 788 is unpaid and not yet due. Nothing is late."
			told = json.loads(asked[0].split("\n\n", 1)[1])
			assert told["invoiced_this_year"] > 0 and "unpaid" in told, told
			noticed = head.notices_of(frappe.get_doc("Supplier", supplier))
			assert any(one["notice"] == "oneai.summary" and asked and one["lines"][0].startswith("AED 788") for one in noticed), noticed
			brief.touched(invoice, "on_cancel")
			assert brief.due() == 0 and frappe.db.get_value("Supplier", supplier, brief.DUE), "once a day, however much happens"
			with as_user(OWNER):
				brief.switch("Supplier", 0)
			frappe.db.set_value("Supplier", supplier, brief.DUE, 0, update_modified=False)
			brief.touched(invoice, "on_submit")
			assert not frappe.db.get_value("Supplier", supplier, brief.DUE), "switched off"
	finally:
		frappe.db.set_value("Supplier", supplier, clear, update_modified=False)
		frappe.db.set_default(brief.OFF, "[]")


@check
def oneai_lays_out_a_print_format_as_meant():
	"""Layla's print format is laid out from sections a model wrote loosely:
	Python's words for true and none, a table named just before its columns,
	widths in per cent and a sentence after. It prints in the font, page
	number and look asked for, a later restyle keeps its layout, and
	print_layout reads all of it back. Omar may not design one."""
	from onedesk.one import ai_print_design

	with as_user(OWNER):
		said = ai_print_design.print_layout("Sales Invoice")
		assert said.get("starting_layout") and said.get("fields"), said
		loose = frappe.as_json(said["starting_layout"], indent=None).replace("true", "True").replace("null", "None") + " That is the layout."
		assert "True" in loose or "None" in loose, "the starting layout has no true or none to write loosely"
		_applied(ai_print_design.design_print_format("Sales Invoice", "Loose Invoice", sections=loose, css=".print-format-doc { color: #333; }", font="Lora", page_number="Bottom Center"))
		held = frappe.db.get_value("Print Format", "Loose Invoice", ["font", "page_number", "css", "format_data"], as_dict=True)
		assert (held.font, held.page_number, held.css) == ("Lora", "Bottom Center", ".print-format-doc { color: #333; }"), held
		read = ai_print_design.print_layout("Sales Invoice", "Loose Invoice")
		assert (read["house_style"], read["css"], read["font"], read["page_number"]) == (False, ".print-format-doc { color: #333; }", "Lora", "Bottom Center"), read
		_applied(ai_print_design.design_print_format("Sales Invoice", "Loose Invoice", css=".section-label { color: #0a5; }", house_style=True))
		read = ai_print_design.print_layout("Sales Invoice", "Loose Invoice")
		assert read["house_style"] and read["css"] == ".section-label { color: #0a5; }", read
		assert frappe.db.get_value("Print Format", "Loose Invoice", "format_data") == held.format_data, "a restyle moved the layout"
		assert ai_print_design._paired(["items", {"columns": ["item_code"]}]) == [{"columns": ["item_code"], "table": "items"}]
		assert ai_print_design._column({"field": "qty", "width": "15%", "label": "Qty"}) == "qty:15:Qty"
	with as_user("omar@one.test"):
		assert ai_print_design.print_layout("Sales Invoice").get("error")


def _applied(said: dict) -> str:
	"""A OneAI card, approved as its person would approve it."""
	from onedesk.one_ai import run as runs

	assert said.get("proposal"), said
	runs.apply(said["proposal"])
	assert frappe.db.get_value("AI Proposal", said["proposal"], "state") == "Applied", said
	return said["proposal"]


@check
def oneai_reads_and_sets_up_the_workspace_with_layla():
	"""What OneAI reads about the workspace for Layla, and about herself for
	Rania, without an error; and each setup card it suggests, approved and
	there afterwards: a holiday, a second quotation series, a print format
	drawn and made the default, a notification's text, the workspace's
	signature, a mail template and an automation on invoices. A field on
	leads and an approval on purchase orders are suggested and read, not
	approved, since each adds a column to its table.
	"""
	from onedesk.one import (
		ai_approvals,
		ai_automations,
		ai_customize,
		ai_notifications,
		ai_numbering,
		ai_print_design,
		ai_printing,
		ai_workspace,
		privacy_copy,
	)
	from onedesk.one_ai import memory, tools
	from onedesk.one_mail import agent as mail_agent
	from onedesk.one_mail import holders
	from onedesk.one_studio import printing

	with as_user("rania@one.test"):
		for said in (ai_workspace.my_day(), mail_agent.my_mailboxes(), memory.recall(), ai_notifications.my_notifications(), ai_workspace.my_sign_in()):
			assert "error" not in said, said
		privacy_copy.ask()
	asked = frappe.db.get_value(privacy_copy.DOWNLOAD, {"user": "rania@one.test"})
	kind = frappe.db.get_value("Notification Type", {"one_rule": ["is", "not set"]}) or frappe.db.get_value("Notification Type", {})
	with as_user(OWNER):
		read = {
			"people": ai_workspace.workspace_people(),
			"access": ai_workspace.workspace_access(),
			"reports": ai_workspace.workspace_reports(),
			"bin": tools.list_records(
				"Deleted Document",
				filters={"creation": [">=", add_days(today(), -30)]},
				fields=["deleted_doctype", "deleted_name", "owner", "creation", "restored", "new_name"],
				order_by="creation desc",
			),
			"announcements": ai_workspace.announcements(),
			"webhooks": ai_workspace.webhooks(7),
			"audit": ai_workspace.audit_log("changes", days=7),
			"privacy": ai_workspace.privacy_request(asked),
			"intake": ai_workspace.workspace_intake(),
			"holidays": ai_workspace.workspace_holidays(),
			"oneai": ai_workspace.workspace_oneai(),
			"plan": ai_workspace.workspace_plan(),
			"sign-in": ai_workspace.workspace_sign_in(),
			"numbering": ai_numbering.workspace_numbering("Quotation"),
			"printing": ai_printing.workspace_printing("Sales Invoice"),
			"layout": ai_print_design.print_layout("Sales Invoice"),
			"mail templates": mail_agent.workspace_mail_templates("Sales Invoice"),
			"approvals": ai_approvals.workspace_approvals("Purchase Order"),
			"automations": ai_automations.workspace_automations("Sales Invoice"),
			"a notification": ai_notifications.notification_type(kind),
		}
		wrong = {name: said for name, said in read.items() if isinstance(said, dict) and said.get("error")}
		assert not wrong, wrong
		assert "cname_target" in read["plan"] and isinstance(read["plan"]["domains"], list), read["plan"]

		field = ai_customize.customize("Lead", add=[{"label": "Site Visit Date", "kind": "Date"}])
		assert "Site Visit Date" in frappe.db.get_value("AI Proposal", field["proposal"], "changes")
		holiday = f"{getdate(today()).year}-12-31"
		_applied(ai_workspace.change_holidays(add=[{"date": holiday, "name": "Year end closure"}]))
		assert frappe.db.exists("Holiday", {"holiday_date": holiday, "description": ["like", "%Year end closure%"]})
		series = [one["series"] for one in __import__("onedesk.one_studio.numbering", fromlist=["series"]).series("Quotation")]
		_applied(ai_numbering.change_numbering("Quotation", series=[*series, "QTN-SG-.####"]))
		assert "QTN-SG-.####" in frappe.get_meta("Quotation").get_field("naming_series").options
		drawn = ai_print_design.design_print_format("Sales Invoice", "Sahara Clean", make_default=True)
		assert "<" in printing.proposal_preview(drawn["proposal"])
		_applied(drawn)
		assert frappe.db.exists("Print Format", "Sahara Clean")
		assert ai_printing.change_printing(doctype="Sales Invoice", default_format="Sahara Clean").get("error"), "a change to what already prints"
		other = frappe.db.get_value("Print Format", {"doc_type": "Sales Invoice", "name": ["!=", "Sahara Clean"], "disabled": 0})
		_applied(ai_printing.change_printing(doctype="Sales Invoice", default_format=other))
		assert printing.default("Sales Invoice") == other
		_applied(ai_notifications.rewrite_notification(kind, "Something for you to look at"))
		ours = frappe.db.get_value("Email Account", holders.workspace(), "email_id")
		_applied(mail_agent.sign_mailbox(ours, "Sahara Glass\nDubai Investments Park"))
		assert "Dubai Investments Park" in (frappe.db.get_value("Email Account", holders.workspace(), "signature") or "")
		_applied(mail_agent.write_mail_template("Invoice {{ name }} is due", "Dear {{ customer_name }},\n\nA reminder that invoice {{ name }} is due.", new_name="Payment reminder", for_doctype="Sales Invoice"))
		assert frappe.db.exists("Email Template", "Payment reminder")
		approval = (
			ai_approvals.suggest_approval(
				"Purchase Order",
				[
					{"state": "Draft", "editable_by": "Purchase User"},
					{"state": "Approved", "submitted": True, "editable_by": "Purchase Manager"},
					{"state": "Rejected", "editable_by": "Purchase Manager"},
				],
				[
					{"from": "Draft", "action": "Approve", "to": "Approved", "by": "Purchase Manager"},
					{"from": "Draft", "action": "Reject", "to": "Rejected", "by": "Purchase Manager"},
				],
				name="Purchase approval",
				turn_on=True,
			)
		)
		assert "Purchase Manager" in frappe.db.get_value("AI Proposal", approval["proposal"], "changes")
		_applied(ai_automations.suggest_automation("Sales Invoice", "submitted", [{"do": "tell", "who": ["huda@one.test"], "subject": "Invoice {{ doc.name }} is out", "message": "For {{ doc.customer }}."}], title="Tell Huda of invoices", turn_on=True))
		assert frappe.db.exists("Automation Flow", {"title": "Tell Huda of invoices"}) or frappe.db.count("Automation Flow")


@check
def oneai_suggests_a_customer_and_its_quotation_together():
	"""A chain: one create_records call makes a card for a new customer and one
	for a quotation pointing at it; Approve All makes both, the quotation for
	the customer just made, and each carries OneAI's marks."""
	from onedesk.one_ai import proposals, run, tools, touch

	item = frappe.db.sql(
		"""select name from tabItem where is_sales_item = 1 and disabled = 0 and has_variants = 0
		and name not in (select parent from `tabItem Customer Detail`) limit 1"""
	)[0][0]
	with as_user("omar@one.test"):
		said = tools.create_records(
			[
				{"ref": "new", "doctype": "Customer", "values": {"customer_name": "Harbor Lights LLC", "customer_type": "Company"}},
				{"doctype": "Quotation", "values": {"quotation_to": "Customer", "party_name": "@new", "items": [{"item_code": item, "qty": 3}]}},
			]
		)
		first, second = (one["proposal"] for one in said["cards"])
		assert json.loads(frappe.db.get_value("AI Proposal", second, "needs")) == [first]
		assert not frappe.db.exists("Customer", "Harbor Lights LLC"), "nothing is made before it is approved"
		try:
			tools.create_record("Quotation", {"quotation_to": "Customer", "party_name": "@PROP-99-999999", "items": [{"item_code": item, "qty": 1}]})
			raise AssertionError("a pointer at no card was taken")
		except frappe.ValidationError as e:
			assert "no card PROP-99-999999" in str(e), e
	with as_user("samir@one.test"):
		try:
			tools.create_record("Quotation", {"quotation_to": "Customer", "party_name": f"@{first}", "items": [{"item_code": item, "qty": 1}]})
			raise AssertionError("pointed at somebody else's card")
		except frappe.ValidationError:
			pass
	with as_user("omar@one.test"):
		done = run.apply_all([first, second])
		assert [one["state"] for one in done] == ["Applied", "Applied"], done
		quotation = frappe.db.get_value("AI Proposal", second, "applied_doc")
		assert frappe.db.get_value("Quotation", quotation, "party_name") == "Harbor Lights LLC"
		held = frappe.get_doc("Customer", "Harbor Lights LLC")
		touch.onload(held)
		assert held.get_onload().get("ai_made"), "the record says OneAI made it"
		assert "customer_type" in (held.get_onload().get("ai_touched") or {}), "a field that is not prose is marked too"
		assert proposals.apply_all([first, second]) == [], "approving twice does nothing"


@check
def ai_center_sets_the_tier_and_a_modules_part():
	"""AICenter (one_ai/center.py): the tier set and put back, one of
	OneHR's switches turned and put back, OneMail's mailboxes listed, one of
	reading's settings changed and put back, and reading and OneAI turned off
	and on; somebody who doesn't administer the workspace
	is refused all of it and sees only what OneAI keeps about them."""
	from unittest import mock

	from onedesk.one import apps
	from onedesk.one_ai import center

	with as_user("nadia@one.test"):
		assert "facts" in center.yours()
		for refused in (center.state, center.parts, lambda: center.set_tier("full")):
			try:
				refused()
			except frappe.PermissionError:
				continue
			raise AssertionError("somebody who doesn't administer the workspace reached AICenter's workspace parts")
	with as_user("wsadmin@one.test"), mock.patch("onedesk.one.account.ask", return_value=[]):
		was = center.tier()
		try:
			assert center.set_tier("full" if was != "full" else "fast") == center.state()["tier"] != was
		finally:
			center.set_tier(was)
		parts = {one["module"]: one for one in center.parts()}
		assert {"OneHR", "OneMail"} <= set(parts) and parts["OneMail"]["mailboxes"], parts
		job = next(one for one in parts["OneHR"]["jobs"] if one["kind"] == "switch")
		try:
			assert center.set_job(job["key"], 0 if job["value"] else 1)["value"] != job["value"]
		finally:
			center.set_job(job["key"], job["value"])
		try:
			center.set_on(0)
			assert not apps.ai_on() and center.modules()
		finally:
			center.set_on(1)
		assert apps.ai_on()
		read = center.reading()
		assert read["on"] and {one["key"] for one in read["settings"]} >= {"floor", "quiet_minutes", "audit"}, read
		quiet = next(one["value"] for one in read["settings"] if one["key"] == "quiet_minutes")
		try:
			center.set_reading("quiet_minutes", 9)
			assert frappe.db.get_single_value("Reading Settings", "quiet_minutes") == 9
		finally:
			center.set_reading("quiet_minutes", quiet or 0)
		try:
			center.set_reading_on(0)
			assert apps.ai_on() and not apps.intake_on()
		finally:
			center.set_reading_on(1)
		assert apps.intake_on()
		assert center.summaries() and isinstance(center.knowledge(), list)
		used = center.usage()
		assert used["reached"] or not used["jobs"], used


@check
def oneai_searches_the_web_only_while_its_service_is_on():
	"""Web search (one_ai/ai_web.py): off, OneAI isn't given the tool or its
	group, and asking it reaches nobody; on, the question alone goes to the
	account, and the pages come back."""
	from unittest import mock

	from onedesk.one_ai import ai_web, groups, tools
	from onedesk.trust_center import services

	with as_user(OWNER):
		was = services.on(ai_web.SERVICE)
		try:
			services.switch(ai_web.SERVICE, 0)
			frappe.local.one_services = {}
			assert "web_search" not in tools.names() and "web" not in groups.chosen("look up Gulf Extrusions online")
			with mock.patch("onedesk.one.account.ask") as asked:
				assert ai_web.web_search("Gulf Extrusions Dubai")["pages"] == []
				asked.assert_not_called()
			services.switch(ai_web.SERVICE, 1)
			frappe.local.one_services = {}
			assert "web_search" in tools.names() and "web" in groups.chosen("look up Gulf Extrusions online")
			page = {"url": "https://gulf.example", "title": "Gulf Extrusions", "about": "Aluminium profiles"}
			with mock.patch("onedesk.one.account.ask", return_value={"pages": [page]}) as asked:
				assert ai_web.web_search("Gulf Extrusions Dubai") == {"pages": [page]}
				assert asked.call_args.kwargs == {"query": "Gulf Extrusions Dubai", "most": ai_web.MOST}, asked.call_args
		finally:
			services.switch(ai_web.SERVICE, int(was))
			frappe.local.one_services = {}


@check
def a_oneai_manager_writes_knowledge():
	"""Knowledge (one_ai/center.py keep_knowledge): Nadia, with no role
	beyond User, is refused; given OneAI Manager she writes a piece, changes
	it and removes it in AICenter, though the record type's own form is an
	administrator's; OneAI may do none of it (agent.py NOT_FOR_AI)."""
	from onedesk.one_ai import agent, center

	with as_user("nadia@one.test"):
		assert not center.may()["knowledge"]
		try:
			center.keep_knowledge("Refused", "Nobody reads this.")
			raise AssertionError("Nadia wrote Knowledge")
		except frappe.PermissionError:
			pass
	user = frappe.get_doc("User", "nadia@one.test")
	user.add_roles("OneAI Manager")
	try:
		with as_user("nadia@one.test"):
			assert center.may()["knowledge"], "OneAI Manager holds Knowledge, given once by the update that brought it"
			assert not frappe.has_permission("AI Knowledge", "create"), "the record type's own form stays an administrator's"
			name = center.keep_knowledge("Site visits", "<p>Site visits are booked two days ahead.</p>", enabled=1)
			assert center.knowledge_of(name)["title"] == "Site visits"
			center.keep_knowledge("Site visits", "<p>Three days ahead.</p>", enabled=0, name=name)
			assert {"name": name, "enabled": 0} in [{"name": one["name"], "enabled": one["enabled"]} for one in center.knowledge()]
			center.drop_knowledge(name)
			assert not frappe.db.exists("AI Knowledge", name)
	finally:
		user.remove_roles("OneAI Manager")
	assert "center.keep_knowledge" in agent.NOT_FOR_AI and "center.drop_knowledge" in agent.NOT_FOR_AI


@check
def the_agents_call_back_with_one_token_for_one_tool_once():
	"""The Agents Worker's way back in (one_ai/agents/api.py): each agent is
	a user turned off with its app's User roles and its own, which nobody
	else holds; a token signed for this workspace opens one tool of its
	agent, as that agent, for its own body. OneMail's receptionist finds the kept sample invoice in its mail
	and hands it on, a comment on the mail that can be undone; OneBook's
	accountant finds the draft Intake made rather than making a second."""
	import time
	from types import SimpleNamespace
	from unittest import mock

	from frappe.permissions import AUTOMATIC_ROLES

	from onedesk.one.registry import agents
	from onedesk.one_ai.agents import api, token
	from onedesk.one_ai.reading import act
	from onedesk.one_mail import gate

	for agent in agents.listed():
		assert not frappe.db.get_value("User", agent.email, "enabled"), agent.email
		assert set(frappe.get_roles(agent.email)) - set(AUTOMATIC_ROLES) == set(agent.roles), agent.email
	held = frappe.get_all("Has Role", filters={"role": ["in", list(agents.only()) or [""]], "parenttype": "User"}, fields=["parent", "role"])
	assert all(agents.only()[one.role] == one.parent for one in held), held
	reading = _sample("new-supplier-invoice")
	message = gate.message_of(reading)
	secret = token.secret_for("check", "demo")

	def called(app: str, tool: str, args: dict, body: str | None = None):
		said = json.dumps({"tool": tool, "args": args})
		signed = token.mint(secret, {"aud": "workspace", "ws": "demo", "agent": app, "tool": tool}, said, int(time.time()))
		request = SimpleNamespace(method="POST", get_data=lambda as_text=False: body or said, headers={api.HEADER: signed})
		config = {"one_agents": {"url": "https://agents.test", "secret": secret}, "one_tenant": "demo"}
		with mock.patch.dict(frappe.local.conf, config), mock.patch.object(frappe, "request", request), mock.patch.object(frappe.local, "request_ip", "127.0.0.1", create=True):
			try:
				return api.tool(tool, args)
			finally:
				frappe.set_user("Administrator")

	came = called("one_mail", "incoming", {"message": message})
	assert reading in came["invoices"], came
	for refused in (("one_mail", "draft_purchase_invoice", {"reading": reading}, None), ("one_book", "incoming", {"message": message}, None), ("one_mail", "incoming", {"message": message}, "{}")):
		try:
			called(*refused)
			raise AssertionError(f"{refused} was let in")
		except frappe.PermissionError:
			pass
	handed = called("one_mail", "hand_on", {"message": message, "reading": reading, "to": "one_book"})
	row = frappe.get_doc("Reading Action", handed["action"])
	assert (row.agent, row.agent_level, row.level, row.kind) == (agents.email("one_mail"), "Do it", "Done", "Comment"), row.as_dict()
	assert frappe.db.get_value("Comment", json.loads(row.after)["comment"], "owner") == agents.email("one_mail")
	with as_user(row.on_behalf_of):
		assert act.undo_one(row.name)["undone"] == 1
	bills = frappe.db.count("Purchase Invoice", {"bill_no": "GS-11873"})
	drafted = called("one_book", "draft_purchase_invoice", {"reading": reading})["drafts"]
	assert {one.target_doctype for one in drafted} <= {"Purchase Invoice"}, drafted
	assert frappe.db.count("Purchase Invoice", {"bill_no": "GS-11873"}) == bills, "a second bill for the same invoice"
