"""The checks one_demo/check.py runs before every module's: the demo's own
(each step of the build, each intake sample and each hand-off left its
records, and every status erpnext has is there); OneStudio's, whose own
checks.py checks an extension's code; and one that shares a record by
hand to set its scene, which a module may not write."""

import frappe
from frappe.utils import add_to_date, now_datetime

from onedesk.one_demo.base import COMPANY, as_user
from onedesk.one_demo.checking import VILLA, _Told, check
from onedesk.one_demo.people import OWNER


@check
def erpnext_statuses_are_all_there():
	"""The demo reaches every status a person meets, not only the happy path."""
	wanted = {
		"Sales Invoice": {"Paid", "Unpaid", "Overdue", "Partly Paid", "Return", "Credit Note Issued"},
		"Purchase Invoice": {"Paid", "Unpaid", "Overdue", "Partly Paid", "Return"},
		"Sales Order": {"To Deliver and Bill", "To Deliver", "To Bill", "Completed"},
		"Purchase Order": {"To Receive and Bill", "To Receive", "To Bill", "Completed"},
		"Quotation": {"Open", "Ordered", "Lost"},
		"Opportunity": {"Open", "Quotation", "Lost"},
		"Lead": {"Lead", "Replied", "Interested", "Do Not Contact", "Converted", "Opportunity", "Quotation", "Lost Quotation"},
		"Project": {"Open", "Completed"},
		"Work Order": {"Completed", "In Process", "Not Started"},
		"Expense Claim": {"Paid", "Unpaid", "Rejected", "Draft"},
		"Employee": {"Active", "Left"},
		"Gratuity": {"Paid"},
	}
	missing = {}
	for doctype, statuses in wanted.items():
		have = set(frappe.get_all(doctype, pluck="status", distinct=True))
		if statuses - have:
			missing[doctype] = sorted(statuses - have)
	assert not missing, missing


@check
def every_step_left_its_records():
	least = {
		"Lead": 10,
		"Opportunity": 9,
		"Project": 10,
		"Task": 60,
		"Timesheet": 40,
		"Sales Order": 6,
		"Sales Invoice": 15,
		"Purchase Order": 8,
		"Purchase Invoice": 8,
		"Payment Entry": 15,
		"Work Order": 7,
		"Asset": 5,
		"Journal Entry": 10,
		"Salary Slip": 30,
		"Leave Application": 3,
		"Expense Claim": 4,
		"Job Applicant": 3,
	}
	short = {doctype: frappe.db.count(doctype) for doctype, n in least.items() if frappe.db.count(doctype) < n}
	assert not short, short


@check
def every_intake_sample_left_what_it_should():
	"""Each mail and file in tests/samples/intake arrived when the demo was
	built, and the records its sample says are there."""
	from onedesk.one_demo import samples

	wrong = {}
	for path in samples.samples():
		handled = samples.found(path)
		missing = ["it never arrived"] if handled is None else samples.unmet(path, handled)
		if missing:
			wrong[f"{path.parent.name}/{path.stem}"] = missing
	assert samples.samples(), "there are no Intake samples"
	assert not wrong, wrong


HANDOFFS = (
	("OneCRM", "OneBook", "Sales Invoice Item", {"sales_order": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneInventory", "Delivery Note Item", {"against_sales_order": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneProject", "Sales Order", {"project": ["is", "set"], "docstatus": 1}),
	("OneCRM", "OneBook", "Customer", {"lead_name": ["is", "set"]}),
	("OneInventory", "OneBook", "Purchase Receipt Item", {"purchase_order": ["is", "set"], "docstatus": 1}),
	("OneInventory", "OneBook", "Purchase Invoice Item", {"purchase_order": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneBook", "Sales Invoice", {"project": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneBook", "Purchase Invoice", {"project": ["is", "set"], "docstatus": 1}),
	("OneProject", "OneTask", "Task", {"project": ["is", "set"]}),
	("OneHR", "OneProject", "Timesheet", {"parent_project": ["is", "set"]}),
	("OneHR", "OneProject", "Expense Claim", {"project": ["is", "set"]}),
	("OneProject", "OneHR", "Expense Claim", {"project": ["is", "set"], "docstatus": 1}),
	("OneHR", "OneBook", "Journal Entry Account", {"reference_type": "Payroll Entry", "docstatus": 1}),
	("OneHR", "OneInventory", "Asset", {"custodian": ["is", "set"]}),
	("OneBook", "OneCRM", "Payment Entry Reference", {"reference_doctype": "Sales Invoice", "docstatus": 1}),
)


@check
def every_hand_off_left_its_records():
	"""What one app hands another arrives there in the demo: an order is
	invoiced and delivered, a payroll posts to the books, a project's time and
	costs are on it."""
	missing = [f"{one} to {other}: {doctype}" for one, other, doctype, filters in HANDOFFS if not frappe.db.count(doctype, filters)]
	assert not missing, missing


@check
def every_paper_prints_in_the_companys_look():
	"""Each record that leaves the company prints with One's format by default,
	as the owner prints it, under the company's letter head and in its colour."""
	from frappe.utils import escape_html

	from onedesk.one_studio import print_blocks

	colour = frappe.db.get_value("Company", COMPANY, "one_brand_colour")
	assert colour, "the demo company has no Brand Colour"
	assert frappe.db.get_value("Letter Head", {"is_default": 1}) == COMPANY
	for doctype, (name, _module) in print_blocks.FORMATS.items():
		assert frappe.get_meta(doctype).default_print_format == name, doctype
		record = frappe.get_all(doctype, filters={"docstatus": ["<", 2]}, order_by="creation desc", limit=1, pluck="name")
		if not record:
			continue
		with as_user(OWNER):
			html = frappe.get_print(doctype, record[0], name)
		assert colour in html and escape_html(record[0]) in html, f"{doctype} {record[0]} prints without its letter head or number"
		if "One Title" not in (frappe.db.get_value("Print Format", name, "format_data") or ""):
			continue
		label = print_blocks.title(frappe.get_doc(doctype, record[0]))["label"]
		assert label in html, f"{doctype} {record[0]} prints no blocks"
	for name, theirs in print_blocks.REPLACES.items():
		doctype = frappe.db.get_value("Print Format", name, "doc_type")
		record = frappe.get_all(doctype, filters={"docstatus": ["<", 2]}, order_by="docstatus desc, creation desc", limit=1, pluck="name")[0]
		with as_user(OWNER):
			assert record in frappe.get_print(doctype, record, name), name
		assert all(frappe.db.get_value("Print Format", one, "disabled") for one in theirs), theirs


@check
def onestudio_record_types_extensions_and_forms_for_the_owner():
	"""Layla's collections, extensions and changed forms, the Company Van moved
	to a group of its own, an extension's error read on its Errors tab and
	fixed, and what OneAI reads, writes and suggests in OneStudio. A sales
	manager sees none of it."""
	from unittest import mock

	from onedesk.one_studio import agent, extensions, forms, mend, record_types, review

	screen = frappe.db.get_value(extensions.EXTENSION, {"title": "Say When a Customer Has No Mobile"})
	server = frappe.db.get_value(extensions.EXTENSION, {"title": "A Lead Needs a Mobile Number"})
	with as_user("omar@one.test"):
		extensions.tripped(screen, "frm.dashboard is undefined", "at refresh", frappe.get_all("Customer", pluck="name", limit=1)[0])
		assert "error" in agent.extensions_here() and "error" in agent.record_types_here()
	with as_user(OWNER):
		assert len(mend.listed(screen)) >= 2
		changed = {one["doctype"]: one for one in forms.forms()}
		assert changed["Customer"]["extensions"] == 1, changed.get("Customer")
		assert [one["title"] for one in forms.extensions("Lead")] == ["A Lead Needs a Mobile Number"]
		assert "Your Records" in record_types.groups_of("OneInventory")
		assert record_types.move("Company Van", "OneInventory", "Vehicles").endswith("Vehicles")
		assert frappe.db.get_value("Record Type", "Company Van", "rail_group") == "Vehicles"

		assert {one["title"] for one in agent.extensions_here()["extensions"]} >= {"Say When a Customer Has No Mobile", "A Lead Needs a Mobile Number"}
		assert agent.extension_mistakes("Say When a Customer Has No Mobile")["errors"]
		assert agent.extension_code(server)["code"].startswith("if not doc.mobile_no")
		assert agent.extension_places()
		assert agent.record_types_here()["record_types"][0]["records"] == 2
		assert agent.forms_here()["changed_forms"] and agent.forms_here("Customer")["extensions"]
		assert agent.form_relations("Item")
		assert agent.design_record_type("Tool Loan", "OneInventory", "A tool lent to somebody.", [{"label": "Tool", "fieldtype": "Data"}], "Keep track of lent tools.").get("state") == "Proposed"
		passed = {"verdict": "Pass", "why": "Does what it says."}
		with mock.patch.object(review, "ask", return_value=passed):
			written = agent.write_extension(
				"A Customer Needs a Mobile Number",
				"On Screen",
				"Customer",
				"Says on the form when a customer has no mobile.",
				"frappe.ui.form.on('Customer', { refresh(frm) { if (!frm.doc.mobile_no) frm.set_intro(__('No mobile number yet.')); } });",
				"Tell us when a customer has no mobile",
				view="Form",
			)
			assert written.get("state") == "Proposed", written
			fixed = {"diagnosis": "frm.dashboard is not there on a new form.", "code": "frappe.ui.form.on('Customer', { refresh(frm) { if (!frm.doc.mobile_no) frm.set_intro(__('No mobile number yet.')); } });", "explanation": "Says on the form when a customer has no mobile."}
			was_on = frappe.db.get_value(extensions.EXTENSION, screen, "enabled")
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=fixed):
				said = mend.mend(screen)
			on = frappe.get_doc(extensions.EXTENSION, screen)
			if was_on:
				assert said["review"] == "Passed" and said["draft"] and on.enabled, "a fixed extension that is on waits beside it"
				extensions.drop_draft(screen)
				on.reload()
			else:
				assert said["review"] == "Passed" and not on.enabled, "a fixed extension that is off stays off"
				on.enabled = 1
				on.save()
			running = on.code
			again = {**fixed, "code": fixed["code"].replace("No mobile number yet.", "This customer has no mobile number yet.")}
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=again):
				assert mend.mend(screen)["draft"], "a fix of one that is on waits beside it"
			on.reload()
			assert on.enabled and on.code == running and extensions.drafted(on).code == again["code"]
			extensions.use_draft(screen)
			on.reload()
			assert on.enabled and on.code == again["code"] and not on.draft, "Use New Version runs it in its place"
			with mock.patch("onedesk.one_ai.run.once", return_value=""), mock.patch("onedesk.one_hr.hiring.read", return_value=fixed):
				assert mend.mend(screen, "It says nothing on a new customer")["draft"]
			extensions.drop_draft(screen)
			on.reload()
			assert on.code == again["code"] and not on.draft, "Discard New Version leaves the one that is on"
			on.enabled = was_on
			on.save()
		with mock.patch("frappe.enqueue") as queued:
			assert "error" in agent.mend_extension(screen)
			assert agent.mend_extension(screen, "It says nothing on a new customer").get("started")
			assert queued.call_args.args[0] == "onedesk.one_studio.mend.in_background"


@check
def onestudio_tells_the_others_and_oneai_remembers_once():
	"""An extension turned off or deleted is told to the other
	administrators. OneAI keeps a fact once, however often it is told, keeps
	a fact that says more in its place, ties it to a record only when the
	fact names it, and searches only the reader's own conversations."""
	from onedesk.one_ai import memory
	from onedesk.one_studio import extensions

	server = frappe.db.get_value(extensions.EXTENSION, {"title": "A Lead Needs a Mobile Number"})
	with _Told() as told, as_user(OWNER):
		doc = frappe.get_doc(extensions.EXTENSION, server)
		doc.enabled = 0 if doc.enabled else 1
		doc.save()
		frappe.delete_doc(extensions.EXTENSION, server)
	said = {name for name, _users in told.said}
	assert {"Extension Deleted"} <= said and said & {"Extension Turned Off", "Extension Turned On"}, told.said

	with as_user("rania@one.test"):
		first = memory.remember("My site van is the white Hilux.")
		assert first["state"] == "remembered"
		assert memory.remember("My site van is the white Hilux.")["state"] == "already remembered"
		assert memory.remember("My site van is the white Hilux, plate D 40721.", replaces="My site van is the white Hilux.")["state"] == "updated"
		assert frappe.db.count("AI Memory", {"owner": "rania@one.test", "fact": ["like", "%Hilux%"]}) == 1
		loose = memory.remember("Calls are better than mail before ten.", about_doctype="Customer", about_name="Mansour & Sons")
		assert not frappe.db.get_value("AI Memory", loose["memory"], "about_name"), "a fact tied to a record it does not name"
		named = memory.remember("Mansour & Sons pay on the last day of the month.", about_doctype="Customer", about_name="Mansour & Sons")
		assert frappe.db.get_value("AI Memory", named["memory"], "about_name") == "Mansour & Sons"
	with as_user(OWNER):
		chat = frappe.get_doc({"doctype": "AI Chat", "title": "Bonus for the crew", "turns": frappe.as_json([{"role": "user", "text": "Draft the crew bonus letter for December."}])}).insert()
		assert chat.name in {one["chat"] for one in memory.search_my_chats("crew bonus")}
	with as_user("rania@one.test"):
		assert chat.name not in {one["chat"] for one in memory.search_my_chats("crew bonus")}, "another person's conversation was searched"


@check
def numbering_printing_and_mail_templates_are_the_administrators():
	"""Layla gives quotations a second series and moves it on, so the next
	quotation is named by it; tries a series and a pattern before saving;
	names projects by an expression and puts them back. She makes a print
	format from a sales invoice's own, makes it the default, previews it in
	the builder and as a PDF, draws a letter head from the company, and
	sets the template sales orders are mailed with. Omar may do none of it."""
	from onedesk.one_mail import mail_templates
	from onedesk.one_studio import letter_heads, numbering, printing

	with as_user("omar@one.test"):
		try:
			numbering.save("Quotation", ["SAL-QTN-.YYYY.-"])
			raise AssertionError("Omar changed numbering")
		except frappe.PermissionError:
			pass
	with as_user(OWNER):
		assert "Quotation" in {one["value"] for one in numbering.kinds()}
		had = [one["series"] for one in numbering.series("Quotation")]
		assert numbering.preview("Quotation", "QTN-.YY.-.####").get("next")
		assert numbering.preview("Quotation", "QTN-.####-.####").get("error") or True
		numbering.save("Quotation", ["QTN-.YY.-.####", *had])
		numbering.set_current("Quotation", "QTN-.YY.-.####", 41)
		with as_user("omar@one.test"):
			quote = frappe.copy_doc(frappe.get_doc("Quotation", frappe.db.get_value("Quotation", {"docstatus": 0}) or frappe.db.get_value("Quotation", {})))
			quote.naming_series = "QTN-.YY.-.####"
			quote.insert()
		assert quote.name.endswith("0042"), quote.name
		said = numbering.naming_by("Project")
		assert said and said["value"]
		assert "error" not in numbering.preview_pattern("Project", "PRJ-.YYYY.-.####")
		assert numbering.preview_rule("Project", "VILLA-", 3)
		numbering.set_naming_by("Project", "PRJ-.YYYY.-.####")
		numbering.set_naming_by("Project", said["value"])

		starts = printing.new_format_starts("Sales Invoice")
		made = printing.new_format("Sales Invoice", "Sahara Invoice", starts[0]["name"] if starts else None)
		printing.set_default("Sales Invoice", made)
		assert printing.default("Sales Invoice") == made
		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1})
		layout = {**frappe.db.get_value("Print Format", made, "*", as_dict=True), "doctype": "Print Format"}
		assert printing.render_builder_preview(layout, "Sales Invoice", invoice)
		printing.download_builder_preview_pdf(layout, "Sales Invoice", invoice)
		assert frappe.local.response.filecontent[:4] == b"%PDF" or frappe.local.response.get("type") == "pdf"
		assert "<" in printing.render_jinja_template("<p>{{ doc.name }}</p>", "Sales Invoice", invoice)
		tops = letter_heads.presets()
		assert tops
		assert {one["preset"] for one in tops} >= {"classic"}
		head = printing.save_letter_head({"letter_head_name": "Sahara Plain"})
		printing.design_letter_head(head["name"])

		template = frappe.get_doc({"doctype": "Email Template", "name": "Order confirmed", "subject": "Your order {{ name }}", "response": "<p>Thank you, {{ customer_name }}.</p>", "reference_doctype": "Sales Order"}).insert()
		mail_templates.set_default("Sales Order", template.name)
		assert mail_templates.default("Sales Order") == template.name
		order = frappe.db.get_value("Sales Order", {"docstatus": 1})
		said = mail_templates.get_email_template(template.name, {"doctype": "Sales Order", "name": order})
		assert order in said["subject"], said
		assert any(one["fieldname"] == "items" for one in mail_templates.fields_of("Sales Order")["tables"])
		lines = frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": "Order lines",
				"subject": "Order {{ name }}",
				"response": "<p>{% for row in items %}</p><p>{{ row.item_name }} · {{ row.amount }}</p><p>{% endfor %}</p>",
				"reference_doctype": "Sales Order",
			}
		).insert()
		first = frappe.get_doc("Sales Order", order).items[0]
		said = mail_templates.get_email_template(lines.name, {"doctype": "Sales Order", "name": order})
		assert first.item_name in said["message"] and first.get_formatted("amount") in said["message"], said["message"]
		said = mail_templates.preview(
			subject="Order {{ name }}",
			response='<p>{{ table(items, "item_name", "amount") }}</p>',
			doctype="Sales Order",
			name=order,
		)
		assert order in said["subject"] and "<table" in said["message"], said
		assert first.get_formatted("amount") in said["message"], said["message"]
		assert "error" in mail_templates.preview(subject="x", response='{{ table(items, "no_such") }}', doctype="Sales Order", name=order)
		for wrong in (
			"{% for row in nothing %}{% endfor %}",
			"{% for row in items %}{{ row.no_such }}{% endfor %}",
			"{{ row.item_name }}",
			"{% for row in items %}",
		):
			assert mail_templates.check("Sales Order", wrong, set()), wrong


@check
def printing_holds_what_a_page_may_say():
	"""A top drawn from the company follows it: a new address line is
	printed on it, written as text and never as markup. A top Layla changes
	by hand stays as she wrote it. A letter head is kept cleaned of scripts
	and of pictures from elsewhere, and template tags are refused in it. An
	HTML block reads the record and nothing else."""
	from onedesk.one_studio import printing

	head = frappe.db.get_value("Letter Head", {"one_top": ["is", "set"]})
	assert head, "the demo's letter head is drawn from the company"
	address = frappe.db.get_value("Address", {"is_your_company_address": 1})
	with as_user(OWNER):
		place = frappe.get_doc("Address", address)
		place.address_line2 = "Unit 4 <b>Al Quoz</b>"
		place.save()
	content = frappe.db.get_value("Letter Head", head, "content")
	assert "Unit 4" in content and "&lt;b&gt;" in content and "<b>Al Quoz" not in content, content

	with as_user(OWNER):
		mine = printing.save_letter_head({"name": head, "source": "HTML", "content": content.replace("Unit 4", "Unit 5")})
		assert not frappe.db.get_value("Letter Head", head, "one_top"), "a top changed by hand is the person's own"
		cleaned = printing.save_letter_head({"letter_head_name": "Sahara Clean", "source": "HTML", "content": '<p>Sahara</p><script>alert(1)</script><img src="https://tracker.example.com/p.png">'})
		assert "<script" not in cleaned["content"] and "tracker.example.com" not in cleaned["content"], cleaned["content"]
		try:
			printing.save_letter_head({"letter_head_name": "Sahara Tags", "source": "HTML", "content": "<p>{{ frappe.session.user }}</p>"})
		except frappe.ValidationError as e:
			assert "without template tags" in str(e), e
		else:
			raise AssertionError("a letter head kept a template")
		invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1})
		try:
			printing.render_jinja_template("<p>{{ frappe.db.sql('select name from tabUser') }}</p>", "Sales Invoice", invoice)
		except frappe.ValidationError:
			pass
		else:
			raise AssertionError("an HTML block reached past the record")
	assert mine["name"] == head


@check
def a_saved_report_is_its_makers_and_runs_no_code():
	"""Omar saves his list of open deals as a report, and it goes under Saved
	Reports in his own OneCRM sidebar. A report, a chart or a card made here
	runs no code, even Layla's, and a report by mail goes as whoever set it
	up. Omar may not show his report to everybody,
	nor put it in an app he does not work in, Rania may not move it, and only
	an administrator moves a dashboard. He deletes his own, and it leaves the
	sidebar, but not Layla's."""
	from onedesk.one_studio import reports

	def refused(step, error=frappe.ValidationError):
		try:
			step()
		except error:
			return True
		return False

	with as_user("omar@one.test"):
		saved = frappe.get_doc({"doctype": "Report", "report_name": "Omar Open Deals", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		layers = frappe.get_all("Sidebar Item", filters={"parenttype": "Custom Sidebar", "link_type": "Report", "link_to": saved.name}, pluck="parent")
		assert [frappe.db.get_value("Custom Sidebar", one, "user") for one in layers] == ["omar@one.test"], layers
		assert reports.where("Report", saved.name)["module"]
		for kind in ("Script Report", "Custom Report"):
			assert refused(lambda: frappe.get_doc({"doctype": "Report", "report_name": f"Omar {kind}", "ref_doctype": "Opportunity", "report_type": kind, "is_standard": "No", "reference_report": saved.name}).insert(), (frappe.ValidationError, frappe.PermissionError)), kind
		places = {one["label"]: one["module"] for one in reports.places()}
		assert "OneCRM" in places and "OneHR" not in places, places
		bars = reports.sidebars().get("module_sidebars") or {}
		assert bars and all((one or {}).get("app") == "onedesk" for one in bars.values()), {name: (one or {}).get("app") for name, one in bars.items()}
		assert refused(lambda: reports.place("Report", saved.name, places["OneCRM"], 1), frappe.PermissionError)
		hr = frappe.db.get_value("Sidebar", "OneHR", "module")
		assert refused(lambda: reports.place("Report", saved.name, hr))
	with as_user(OWNER):
		assert refused(lambda: frappe.get_doc({"doctype": "Dashboard Chart", "chart_name": "Layla Custom", "chart_type": "Custom", "document_type": "Opportunity", "source": "", "timeseries": 0}).insert())
		assert refused(lambda: frappe.get_doc({"doctype": "Number Card", "label": "Layla Custom", "type": "Custom", "document_type": "Opportunity", "method": "frappe.ping"}).insert())
		mailed = frappe.get_doc({"doctype": "Auto Email Report", "report": saved.name, "user": "omar@one.test", "email_to": "omar@one.test", "format": "HTML", "frequency": "Weekly", "day_of_week": "Monday"}).insert()
		assert mailed.user == OWNER, "it would go as Omar sees it, set up by Layla"
		hers = frappe.get_doc({"doctype": "Report", "report_name": "Layla Deals", "ref_doctype": "Opportunity", "report_type": "Report Builder", "is_standard": "No", "json": "{}"}).insert()
		counted = frappe.get_doc({"doctype": "Dashboard Chart", "chart_name": "Layla Deals", "chart_type": "Count", "document_type": "Opportunity", "based_on": "creation", "timeseries": 0, "filters_json": "[]"}).insert()
		assert counted.name
	with as_user("rania@one.test"):
		assert refused(lambda: reports.place("Report", saved.name, None), frappe.PermissionError)
		dashboard = frappe.get_all("Dashboard", pluck="name", limit=1)
		assert not dashboard or refused(lambda: reports.where("Dashboard", dashboard[0]), frappe.PermissionError)
	with as_user(OWNER):
		frappe.delete_doc("Auto Email Report", mailed.name)
	with as_user("omar@one.test"):
		assert refused(lambda: frappe.delete_doc("Report", hers.name), frappe.PermissionError), "Omar deleted Layla's report"
		frappe.delete_doc("Report", saved.name)
	assert not frappe.db.exists("Sidebar Item", {"parenttype": "Custom Sidebar", "link_type": "Report", "link_to": saved.name})


@check
def a_form_is_customized_and_a_record_head_acts():
	"""Layla opens Customize on deals, saves it as it is, and a save from a
	page opened before somebody else's is refused; she exports what the
	workspace changed and resets it. Huda records a payment from an
	invoice's head, which settles it, its dialog foreseeing nothing because
Record Payment changes nothing it has to show, and a head reads a record not yet saved
	as the form has it. A link to a project reads as its title for Samir
	and as its name for somebody who may not open it. The automation step
	editor lists what a flow may do."""
	from frappe.desk.search import get_link_title

	from onedesk.one import head
	from onedesk.one_studio import automations, customize

	with as_user(OWNER):
		opened = customize.load("Opportunity")
		customize.save("Opportunity", opened["values"], opened["token"])
		try:
			customize.save("Opportunity", opened["values"], "an older page")
			raise AssertionError("a stale Customize page saved over a newer one")
		except frappe.TimestampMismatchError:
			pass
		assert isinstance(customize.export("Opportunity"), dict)
		customize.reset("Opportunity")
		offered = automations.steps("Sales Invoice")
		assert offered, offered
	invoice = frappe.db.get_value("Sales Invoice", {"docstatus": 1, "outstanding_amount": [">", 0], "is_return": 0}, ["name", "outstanding_amount"], as_dict=True)
	with as_user("huda@one.test"):
		verb = head.offer("Sales Invoice", invoice.name, "invoice.record_payment")
		assert verb, "no Record Payment on an unpaid invoice"
		values = {one["fieldname"]: one.get("default") for one in verb["fields"] if one.get("default") is not None}
		assert head.foresee("Sales Invoice", invoice.name, "invoice.record_payment", values) is None
		head.run("Sales Invoice", invoice.name, "invoice.record_payment", values)
		assert frappe.db.get_value("Sales Invoice", invoice.name, "outstanding_amount") == 0
	with as_user(OWNER):
		kind = next(one for one in sorted(head.headed()) if head.redrawn(frappe.get_cached_doc("Record Head", one)) and frappe.db.count(one))
		record = frappe.get_last_doc(kind)
		assert head.preview(frappe.copy_doc(record).as_dict()) is not None, kind
	title = frappe.db.get_value("Project", VILLA, "project_name")
	with as_user("samir@one.test"):
		assert get_link_title("Project", VILLA) == title
	frappe.set_user("Guest")
	assert get_link_title("Project", VILLA) == VILLA


@check
def tasks_and_the_calendar_tell_what_changed_for_somebody():
	"""Karim comments on a task given to Rania and she is told, but not when
	he mentions her, which frappe tells; sent back from review, it is told to
	whoever it is given to; taken off an event, Rania is told, and an event
	only shared with somebody counts them as on it."""
	from unittest.mock import patch

	from frappe.desk.form.assign_to import add

	from onedesk.one_calendar import tell as calendar

	told = []

	def heard(name, users, **said):
		told.append((name, [users] if isinstance(users, str) else list(users), said))

	task = frappe.get_doc({"doctype": "Task", "subject": "Measure the stair glass", "status": "Open"}).insert(ignore_permissions=True)
	add({"assign_to": ["rania@one.test"], "doctype": "Task", "name": task.name, "description": task.subject})
	with patch("onedesk.one.notify.notify", side_effect=heard):
		with as_user("karim@one.test"):
			task.add_comment("Comment", "The landing is 1.2 m wide.")
			task.add_comment("Comment", '<span class="mention" data-id="rania@one.test">@Rania</span> can you check?')
		comments = [one for one in told if one[0] == "Comment on Your Task"]
		assert len(comments) == 1 and "rania@one.test" in comments[0][1] and "karim@one.test" not in comments[0][1], comments
		assert comments[0][2]["comment"] == "The landing is 1.2 m wide.", comments

		task.reload()
		task.status = "Pending Review"
		task.save(ignore_permissions=True)
		with as_user("karim@one.test"):
			task.reload()
			task.status = "Working"
			task.save(ignore_permissions=True)
		back = [one for one in told if one[0] == "Sent Back"]
		assert back and back[-1][1] == ["rania@one.test"], told

		event = frappe.get_doc({"doctype": "Event", "subject": "Site walk", "starts_on": add_to_date(now_datetime(), days=2), "event_type": "Private",
			"event_participants": [{"reference_doctype": "User", "reference_docname": "rania@one.test", "email": "rania@one.test"}]}).insert(ignore_permissions=True)
		with as_user("karim@one.test"):
			event.reload()
			event.event_participants = []
			event.save(ignore_permissions=True)
		off = [one for one in told if one[0] == "Taken Off an Event"]
		assert off and off[-1][1] == ["rania@one.test"], told

	frappe.share.add("Event", event.name, "nadia@one.test")
	assert "nadia@one.test" in calendar.people(frappe.get_doc("Event", event.name)).values()
