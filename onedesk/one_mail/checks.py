"""OneMail's part of the integration suite (one_demo/check.py runs it): the
demo company's mail read back as the people in it, from Layla sorting her
own to a shared mailbox given and let go, rules, out of office and what
OneAI may read."""

import frappe
from frappe.utils import add_days, today

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import VILLA, _asked, _employee, _unasked, check
from onedesk.one_demo.people import OWNER


@check
def onemail_layla_reads_sorts_and_files_her_mail():
	"""Layla's own address, with the mail the samples brought: a folder read,
	a conversation opened, read and starred, moved into a folder of her own
	and back, deleted and put back, filed on the villa and taken off, sorted
	by a rule OneAI suggests, and answered on a card. Her out of office and
	her workspace's signature. Omar cannot see into her mailbox."""
	from onedesk.one_demo import intake
	from onedesk.one_mail import actions, ai, api, holders, linking, rules
	from onedesk.one_mail import demo as mail

	account = intake.mailbox()
	# The demo's mail as the demo brought it, unread, whoever has read it since.
	sent = frappe.qb.DocType("Communication")
	brought = (sent.one_folder == "INBOX") & sent.subject.isin([subject for _sender, subject, _days, _body in mail.MAILS])
	frappe.qb.update(sent).set(sent.seen, 0).where(brought).run()
	for box in set(frappe.qb.from_(sent).select(sent.email_account).where(brought).run(pluck=True)):
		actions.recount(box, "INBOX")
	with as_user(OWNER):
		boxes = {one["name"]: one for one in api.mailboxes()}
		assert account in boxes and account in {one["name"] for one in holders.mailboxes()}
		first = holders.mailboxes()[0]
		assert first["workspace"] and first["unread"] == len(mail.MAILS), first
		unread = frappe.db.count("Communication", {"email_account": account, "one_folder": "INBOX", "seen": 0})
		assert boxes[account]["unread"] == unread, (boxes[account]["unread"], unread)
		inbox = next(one["name"] for one in boxes[account]["folders"] if one["kind"] == "Inbox")
		listed = api.conversations(account, inbox)["items"]
		assert len(listed) >= 10, len(listed)
		found = api.conversations(account, search='subject:"shop drawings" from:acme')["items"]
		assert [one["subject"] for one in found] == ["Shop drawings for the New York lobby"], found
		thread = found[0]["thread"]
		said = api.conversation(account, thread)["messages"]
		assert said[0].sender == "jordan@acme.example"
		names = api.names(account, [thread])
		actions.mark(names, 0)
		assert api.conversations(account, search="is:unread lobby")["items"]
		actions.mark(names, 1)
		actions.star(names, 1)
		assert frappe.db.get_value("Communication", names[0], "one_flagged") == 1

		folder = actions.create_folder(account, "Acme")
		actions.rename_folder(folder, "Acme Lobby")
		path = frappe.db.get_value("Mail Folder", folder, "path")
		moved = actions.move(names, folder)
		assert frappe.db.get_value("Communication", names[0], "one_folder") == path
		assert api.conversations(account, folder)["items"][0]["thread"] == thread
		actions.put_back(moved["was"])
		assert frappe.db.get_value("Communication", names[0], "one_folder") == "INBOX"
		deleted = actions.delete(names)
		assert frappe.db.get_value("Communication", names[0], "one_folder") == "Trash"
		actions.put_back(deleted["was"])
		actions.delete_folder(folder)
		assert not frappe.db.exists("Mail Folder", folder)

		linking.file(names, "Project", VILLA)
		assert thread in {one["thread"] for one in linking.record("Project", VILLA)}
		assert ("Project", VILLA) in {(one.link_doctype, one.link_name) for one in linking.links_of(names)}
		linking.getdoc("Project", VILLA)
		linking.get_docinfo(doctype="Project", name=VILLA)
		assert names[0] in {one["name"] for one in linking.get_communications("Project", VILLA)}
		linking.unfile(names, "Project", VILLA)
		assert thread not in {one["thread"] for one in linking.record("Project", VILLA)}

		opened = ai.open_conversation(account, thread)
		assert opened["subject"] == "Shop drawings for the New York lobby" and opened["messages"]
		assert thread in {one["thread"] for one in ai.waiting_for_answer(account, inbox)["waiting"]}
		reply = ai.draft_reply(account, thread, "Dear Jordan,\n\nThe drawings follow on Monday.\n\nLayla")
		assert frappe.db.get_value("AI Proposal", reply["proposal"], "state") == "Proposed"
		rule = ai.suggest_mail_rule("Taxis", mailbox=account, text_contains="taxi", sort_inbox_now=True)["proposal"]
		from onedesk.one_ai import run as runs

		runs.apply(rule)
		taxis = frappe.db.get_value("Mail Folder", {"account": account, "label": "Taxis"}, "path")
		assert frappe.db.exists("Mail Rule", {"account": account, "steps": ["like", "%taxi%"]})
		assert frappe.db.count("Communication", {"email_account": account, "one_folder": taxis}) >= 2

		rules.set_away(account, 1, str(add_days(today(), 7)), "Back next week.")
		assert rules.away_of(account).one_away == 1
		rules.set_away(account, 0)

		ours = holders.workspace()
		assert ours in {one["name"] for one in holders.shared()["mailboxes"]}
		holders.set_signature(ours, "<p>Layla Nasser<br>Sahara Glass</p>")
		assert holders.signature_of(ours).startswith("<p>Layla Nasser")
		assert holders.signature_for(frappe.db.get_value("Email Account", ours, "email_id")).startswith("<p>Layla")
		holders.set_personal_sends(0)
		assert frappe.db.get_value("Email Account", account, "enable_outgoing") == 1, "the default moved a given address"
		holders.set_personal_sends(1)
		holders.set_sends(account, 0)
		assert not next(one for one in holders.addresses_of_people() if one["name"] == account)["sends"]
		try:
			holders.set_signature(account, "Layla")
			raise AssertionError("an address that only receives signs nothing")
		except frappe.ValidationError:
			pass
		holders.set_sends(account, 1)
		assert frappe.db.get_value("Email Account", account, "enable_outgoing") == 1
		holders.set_access(ours, [{"user": OWNER, "sends": 1}, {"user": "omar@one.test", "sends": 0}])
		assert holders.may_send(ours, OWNER) and not holders.may_send(ours, "omar@one.test")
	with as_user("omar@one.test"):
		assert ours in {one["name"] for one in api.mailboxes()}
		assert not next(one for one in api.mailboxes() if one["name"] == ours)["sends"], "Omar reads the workspace's mailbox but may not send"
		try:
			api.conversations(account, inbox)
			raise AssertionError("Omar read Layla's mailbox")
		except frappe.PermissionError:
			pass


def _report(address: str, action: str, status: str) -> bytes:
	"""A mail server's delivery report about one address."""
	from email.message import Message
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText

	report = MIMEMultipart("report", report_type="delivery-status")
	report["From"] = "Mail Delivery System <mailer-daemon@mx.example.com>"
	report["Subject"] = "Delivery Status Notification"
	report.attach(MIMEText("Your message could not be delivered."))
	about = Message()
	about.set_type("message/delivery-status")
	server, person = Message(), Message()
	server["Reporting-MTA"] = "dns; mx.example.com"
	person["Final-Recipient"] = f"rfc822; {address}"
	person["Action"] = action
	person["Status"] = status
	person["Diagnostic-Code"] = f"smtp; {status} mailbox"
	about.set_payload([server, person])
	report.attach(about)
	return report.as_bytes()


@check
def onemail_a_mailbox_is_its_holders_and_threads_by_what_was_answered():
	"""Layla's own mailbox is hers: Rania neither lists it nor opens a message
	in it. Two mails with one subject are two conversations, and a reply
	joins the one it answers. An address given is kept. A delivery report
	that an address is gone for good stops mail to it, and one that only
	says it is late does not."""
	from email.message import EmailMessage
	from email.utils import make_msgid

	from onedesk.one_demo import intake
	from onedesk.one_mail import addresses, api
	from onedesk.one_mail.inbound import Arrival

	account = intake.mailbox()
	message = frappe.db.get_value("Communication", {"email_account": account})
	with as_user("rania@one.test"):
		assert not frappe.has_permission("Communication", "read", doc=message), "a message opened for somebody who does not hold its mailbox"
		try:
			api.conversations(account)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania listed Layla's mailbox")

	box = frappe.get_doc("Email Account", frappe.db.get_value("Email Account", {"email_id": addresses.workspace_address()}))
	said = []
	for body, answers in (("First enquiry", None), ("Second enquiry", None), ("Reply to the first", 0)):
		one = EmailMessage()
		one["From"] = "Grace Lim <grace@palminteriors.example>"
		one["To"] = box.email_id
		one["Subject"] = "Office partitions"
		one["Message-ID"] = make_msgid(domain="palminteriors.example")
		if answers is not None:
			one["In-Reply-To"] = said[answers]["Message-ID"]
		one.set_content(body)
		said.append(one)
		Arrival(one.as_bytes(), box).process()
	thread = {one["Message-ID"]: frappe.db.get_value("Communication", {"message_id": one["Message-ID"].strip("<>")}, "one_thread") for one in said}
	first, second, reply = (thread[one["Message-ID"]] for one in said)
	assert first and first != second and reply == first, thread

	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
		try:
			addresses.give("rania@one.test", "rania2")
		except frappe.ValidationError as e:
			assert "can't be changed" in str(e), e
		else:
			raise AssertionError("an address people already write to was changed")

	Arrival(_report("grace@palminteriors.example", "failed", "5.1.1"), box).process()
	Arrival(_report("hessa@bayview.example", "delayed", "4.4.1"), box).process()
	assert frappe.db.exists("Email Unsubscribe", {"email": "grace@palminteriors.example", "global_unsubscribe": 1}), "a lost address is mailed again"
	assert not frappe.db.exists("Email Unsubscribe", {"email": "hessa@bayview.example"}), "a late delivery stopped mail to Hessa"


@check
def onemail_a_mailbox_is_set_up_in_its_own_tabs():
	"""Layla manages the workspace mailbox from OneMail's settings: who holds
	it, an acknowledgement to new conversations, how far OneAI reads it and a
	monthly limit; then her own signature from a preset with her name on it,
	and the workspace's rules for outside mailboxes. Turning
	OneAI off for her own mailbox stops even the OneAI panel reading it."""
	from onedesk.one_mail import ai, gate, holders, mail_templates, rules, signatures
	from onedesk.one_storage import api

	with as_user(OWNER):
		ours = holders.workspace()
		assert holders.mailbox(ours)["may_manage"]
		holders.grant(ours, "omar@one.test", 0)
		assert any(one["user"] == "omar@one.test" for one in holders._people(ours))
		holders.revoke(ours, "omar@one.test")
		said = gate.set_settings(ours, level=gate.FILE, limit=500)
		assert said["level"] == gate.FILE and said["limit"] == 500
		gate.set_settings(ours, level=gate.ACT, limit=0)
		own = next(one["name"] for one in holders.mailboxes() if not one["shared"])
		gate.set_settings(own, on=0)
		assert not gate.settings_of(own)["on"]
		assert "error" in ai.open_conversation(own, "anything"), "the panel can't read a mailbox OneAI is off for"
		gate.set_settings(own, on=1)
		was = frappe.db.get_value("Email Account", own, ["signature", "one_signature_preset", "one_signature_show"])
		drawn = signatures.presets_of(own, ["title", "email"])
		assert drawn["presets"] and all(one["html"] for one in drawn["presets"])
		signatures.set_preset(own, "accent", ["email"])
		assert "Layla" in holders.signature_of(own), "her signature doesn't carry her name"
		frappe.db.set_value(
			"Email Account", own, dict(zip(("signature", "one_signature_preset", "one_signature_show"), was, strict=True)), update_modified=False
		)
		made = rules.save_rule(own, {"title": "Invoices", "steps": [{"type": "if", "id": "i1", "test": {"items": [{"field": "subject", "op": "contains", "value": "invoice"}]}, "then": [{"type": "star"}], "else": []}]})
		assert any(one["name"] == made for one in rules.rules_of_mailbox(own)["rules"])
		rules.enable_rule(made, 0)
		assert not frappe.db.get_value("Mail Rule", made, "enabled")
		rules.delete_rule(made)
		holders.set_external(0)
		holders.set_allowed_domains(["gmail.com"])
		holders.set_allowed_domains([])
		holders.set_external(1)
		assert isinstance(mail_templates.templates(), list)
		if frappe.db.exists("Email Template", "Leave Approval Notification"):
			mail_templates.settle()
			was = frappe.db.get_single_value("HR Settings", "leave_approval_notification_template")
			frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", "Leave Approval Notification")
			try:
				row = next(one for one in mail_templates.templates() if one["name"] == "Leave Approval Notification")
				assert row["reference_doctype"] == "Leave Application", row
				assert row["used_by"] and row["code"], "HR's template says who sends it and that it holds code"
				try:
					frappe.delete_doc("Email Template", "Leave Approval Notification")
					raise AssertionError("a template HR Settings sends was deleted")
				except frappe.ValidationError:
					pass
			finally:
				frappe.db.set_single_value("HR Settings", "leave_approval_notification_template", was)
		assert {one["label"] for one in api.capacity()}


@check
def onemail_people_ask_and_mail_managers_decide():
	"""Rania asks for a rule on the address the workspace issued her and
	can't turn it on herself; Layla approves it and it runs. Tariq, made a
	Mail Manager, manages the workspace's mailbox and Rania's address
	without holding either, and gives Rania's address a sender name.
	Rania sets her own address's out-of-office, and it answers by itself
	while she is on approved leave."""
	from onedesk.one import roles
	from onedesk.one_mail import addresses, holders, rules, signatures

	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
	theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
	with as_user("rania@one.test"):
		assert holders.issued_to_them(theirs), "an issued address is the workspace's"
		assert holders.may(theirs, "away") and not holders.may(theirs, "signature"), "her own out-of-office, nothing more"
		asked = rules.save_rule(theirs, {"title": "Invoices", "steps": [{"type": "if", "id": "i1", "test": {"items": [{"field": "subject", "op": "contains", "value": "invoice"}]}, "then": [{"type": "star"}], "else": []}]})
		assert frappe.db.get_value("Mail Rule", asked, ["enabled", "requested_by"]) == (0, "rania@one.test")
		try:
			rules.enable_rule(asked, 1)
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania turned on a rule nobody approved")
		try:
			signatures.set_preset(theirs, "simple", ["email"])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("Rania changed the workspace's address")
		rules.set_away(theirs, 1, None, "Away")
		rules.set_away(theirs, 0)
		assert rules.on_leave(theirs) is None or rules.away_of(theirs)["leave_until"]
	with as_user(OWNER):
		rules.decide_rule(asked, 1)
		assert frappe.db.get_value("Mail Rule", asked, ["enabled", "requested_by"]) == (1, None)
		rules.delete_rule(asked)
	frappe.get_doc("User", "tariq@one.test").add_roles(roles.MAIL_MANAGER)
	try:
		with as_user("tariq@one.test"):
			assert holders.may_manage(holders.workspace()) and holders.may_manage(theirs)
			assert any(one["name"] == theirs for one in holders.addresses_of_people())
			signatures.set_preset(theirs, "simple", ["email"], sender_name="Rania at Sahara Glass")
			assert signatures.sender_name_for(None, addresses.person_address("rania")) == "Rania at Sahara Glass"
			signatures.set_preset(theirs, "simple", ["email"], sender_name="")
			assert signatures.sender_name_for(theirs, None) is None
	finally:
		frappe.get_doc("User", "tariq@one.test").remove_roles(roles.MAIL_MANAGER)
		frappe.db.set_value(
			"Email Account", theirs, {"signature": None, "add_signature": 0, "one_signature_preset": None, "one_signature_show": None}
		)


@check
def onemail_roles_and_one_mailbox_grants():
	"""Layla makes a OneMail role that may change signatures on every
	mailbox and nothing else, and one, cell by cell in the role builder,
	that may change only a person's own address; and lets Samir change the workspace mailbox's signature alone,
	without a role, from its Users tab. Taking Samir off the mailbox takes
	that away too."""
	from onedesk.one import access
	from onedesk.one_mail import addresses, holders

	ours = holders.workspace()
	made = []
	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
		theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
		brand = access.new_level("OneMail", "Brand Team", "User")
		made.append(brand)
		access.save_level(brand, brand, [], {"signature": "all"})
		own = access.new_level("OneMail", "Own Address", "User")
		made.append(own)
		own = made[-1] = access.rename_role(own, "Their Own Mailbox")
		access.change_ability(own, "signature", "own")
		said = access.change_ability(own, "away", "own")
		assert access.ability_matrix("OneMail")["values"] == said["values"]
		assert [role["name"] for role in said["roles"]] == ["User", brand, own, "Manager"]
		assert said["values"][own]["signature"] == "own" and said["values"][own]["holders"] == 0
		assert {one["key"]: one["value"] for one in access.level(brand)["abilities"]}["signature"] == "all"
		assert said["least"][own]["rules"] == "none", "User asks for approval"
	try:
		frappe.get_doc("User", "tariq@one.test").add_roles(brand)
		frappe.get_doc("User", "rania@one.test").add_roles(own)
		with as_user("tariq@one.test"):
			assert holders.may(ours, "signature") and holders.may(theirs, "signature")
			assert not holders.may(ours, "rules") and not holders.may(ours, "away")
		with as_user("rania@one.test"):
			assert holders.may(theirs, "signature") and holders.may(theirs, "away"), "her own address"
			assert not holders.may(ours, "signature") and not holders.may(theirs, "rules")
		with as_user(OWNER):
			holders.grant(ours, "samir@one.test", 1)
			assert holders.give(ours, "samir@one.test", ["signature"]) == ["signature"]
		with as_user("samir@one.test"):
			assert holders.may(ours, "signature") and not holders.may(ours, "away"), "one mailbox, one thing"
		with as_user(OWNER):
			holders.revoke(ours, "samir@one.test")
		with as_user("samir@one.test"):
			assert not holders.may(ours, "signature"), "off the mailbox, off what it gave"
	finally:
		frappe.get_doc("User", "tariq@one.test").remove_roles(brand)
		frappe.get_doc("User", "rania@one.test").remove_roles(own)
		with as_user(OWNER):
			for role in made:
				access.delete_level(role)


@check
def onemail_rules_are_steps_that_branch_and_ask_oneai():
	"""Layla builds rules on the workspace mailbox as steps: an If on who
	wrote, with a group of Any inside, stars and files mail from a customer
	and tells her; an Acknowledge rule answers a new conversation from
	outside once a day, not twice; an Ask OneAI rule waits for OneAI's
	reading and takes the branch of the label it picked, or Otherwise, and is
	refused on a mailbox whose new mail is not read. A rule needs an action,
	and a folder in its own mailbox."""
	from unittest import mock

	from onedesk.one_mail import flow, holders, rules
	from onedesk.one_mail.patches import rules_are_steps

	ours = holders.workspace()
	message = frappe.db.get_value(
		"Communication", {"email_account": ours, "sent_or_received": "Received", "sender": ["like", "%marinahotels%"]}, "name"
	)
	made, sent = [], []
	was = frappe.db.get_value("Communication", message, ["one_flagged", "one_folder"])
	archive = frappe.db.get_value("Mail Folder", {"account": ours, "kind": "Archive"})
	try:
		with as_user(OWNER):
			try:
				rules.save_rule(ours, {"title": "Nothing", "steps": [{"type": "if", "id": "i", "test": {}, "then": [], "else": []}]})
				raise AssertionError("a rule that does nothing was saved")
			except frappe.ValidationError:
				pass
			customers = rules.save_rule(
				ours,
				{
					"title": "Customers",
					"steps": [
						{
							"type": "if",
							"id": "i1",
							"test": {
								"items": [
									{"field": "sender_is", "op": "is", "value": "Customer"},
									{"any": True, "items": [{"field": "subject", "op": "contains", "value": "balcony, glass"}, {"field": "attachment", "value": True}]},
								]
							},
							"then": [{"type": "star"}, {"type": "link"}, {"type": "notify", "user": OWNER}],
							"else": [],
						}
					],
				},
			)
			made.append(customers)
			ack = rules.save_rule(ours, {"title": "Acknowledge", "steps": rules_are_steps.acknowledge(""), "priority": 20})
			made.append(ack)
			asking = {"title": "Asks", "steps": [{"type": "ask", "id": "a", "ask": "yes", "question": "a complaint", "then": [{"type": "star"}], "else": []}]}
			frappe.db.set_value("Email Account", ours, "one_intake", 0)
			try:
				rules.save_rule(ours, asking)
				raise AssertionError("an Ask OneAI rule was saved on a mailbox whose new mail is not read")
			except frappe.ValidationError:
				pass
			frappe.db.set_value("Email Account", ours, "one_intake", 1)
			sort = rules.save_rule(
				ours,
				{
					"title": "Sort",
					"priority": 30,
					"steps": [
						{
							"type": "ask",
							"id": "a1",
							"ask": "pick",
							"labels": [{"label": "Maintenance", "then": [{"type": "move", "folder": archive}]}, {"label": "Quote", "then": []}],
							"else": [{"type": "read"}],
						}
					],
				},
			)
			made.append(sort)
			listed = {one["name"]: one for one in rules.rules_of_mailbox(ours)["rules"]}
			assert "Customer" in listed[customers]["when"] and "Star" in listed[customers]["then"]
		replied = mock.patch("onedesk.one_mail.rules._send", side_effect=lambda account, comm, html: sent.append(comm.name))
		made_ = frappe.get_doc("Communication", message)
		with replied:
			done = rules.run_rules(made_, headers={})
			assert customers in done and ack in done and sort not in done, done
			assert frappe.db.get_value("Communication", message, "one_flagged") == 1
			assert sent == [message], "acknowledged once"
			rules.run_rules(made_, headers={})
			assert sent == [message], "not twice in a day"
		topics = rules.topics_of_mailbox(ours)
		assert (f"{sort}#a1#0", "Maintenance") in topics
		assert rules.run_rules(made_, {f"{sort}#a1#0"}) == [sort]
		assert frappe.db.get_value("Communication", message, "one_folder") == frappe.db.get_value("Mail Folder", archive, "path")
		steps = rules.flow_of(frappe.get_doc("Mail Rule", sort))
		assert flow.walk(steps, rules.facts_of(message), flow.answers_of(sort, steps, set()))[0] == [{"type": "read"}], "Otherwise"
	finally:
		with as_user(OWNER):
			for one in made:
				rules.delete_rule(one)
		frappe.db.set_value("Communication", message, {"one_flagged": was[0], "one_folder": was[1]}, update_modified=False)
		frappe.db.delete("Notification Log", {"for_user": OWNER, "subject": ["like", "%marinahotels%"]})


@check
def onemail_out_of_office_answers_for_its_person():
	"""Rania sets her own address's out-of-office: from tomorrow it is not on
	today; on today, to the workspace only, it answers Samir once and a
	buyer outside not at all, under her name. On
	leave her reply says the day she is back and that Samir covers, and
	Samir reads her address while she is away without owning it, until the
	leave is cancelled. A shared mailbox has no out-of-office; the half day
	of a half-day leave answers nothing."""
	import types
	from unittest import mock

	from onedesk.one_mail import actions, addresses, holders, rules, signatures

	with as_user(OWNER):
		if not frappe.db.exists("Email Account", {"email_id": addresses.person_address("rania")}):
			addresses.give("rania@one.test", "rania")
	theirs = frappe.db.get_value("Email Account", {"email_id": addresses.person_address("rania")})
	sent = []

	def arrived(sender):
		return types.SimpleNamespace(email_account=theirs, sender=sender, subject="Quote", message_id=f"<{sender}>")

	replied = mock.patch(
		"onedesk.one_mail.rules._reply", side_effect=lambda account, made, text, html=None: sent.append((made.sender, text, html))
	)
	leave = frappe._dict(
		name="LEAVE-CHECK",
		employee=_employee("Rania"),
		one_covering=_employee("Samir"),
		one_covering_reads=1,
		docstatus=1,
		status="Approved",
		from_date=today(),
		to_date=add_days(today(), 2),
	)
	try:
		with as_user("rania@one.test"):
			rules.set_away(theirs, 1, None, "", str(add_days(today(), 1)))
			assert not rules.switched_on(frappe.get_doc("Email Account", theirs)), "it starts tomorrow"
			rules.set_away(theirs, 1, str(add_days(today(), 3)), "", None, "Workspace")
			assert rules.away_state(theirs)["until"]
			drawn = rules.away_preview(theirs, "")
			assert drawn["default"] and 'dir="auto"' in drawn["html"]
		with as_user("samir@one.test"):
			assert [one["email"] for one in rules.who_is_away([addresses.person_address("rania")])] == [
				addresses.person_address("rania")
			], "who writes to her is told"
		with replied, mock.patch("onedesk.one_mail.rules.on_leave", return_value=None):
			assert not rules.away(arrived("buyer@outside.test"), {}), "only the workspace"
			assert rules.away(arrived("samir@one.test"), {})
			assert not rules.away(arrived("samir@one.test"), {}), "once per sender"
		assert sent[-1][1] == "I'm away and will reply when I'm back." and 'dir="auto"' in sent[-1][2]
		with as_user(OWNER):
			try:
				rules.set_away(holders.workspace(), 1)
				raise AssertionError("a shared mailbox took an out-of-office")
			except frappe.ValidationError:
				pass
		with as_user("rania@one.test"):
			rules.set_away(theirs, 0)

		rules.covered(leave)
		assert actions.holds(theirs, "samir@one.test") and not actions.owns(theirs, "samir@one.test")
		assert signatures.person_of(theirs) == "rania@one.test", "covering is not owning"
		with as_user("samir@one.test"):
			assert not holders.may(theirs, "away")
			assert {one["name"]: one["covering_until"] for one in holders.mailboxes()}[theirs]
		back = rules.back_on(leave.employee, leave.to_date)
		said = rules.away_message(
			frappe.get_doc("Email Account", theirs),
			{"back": back, "covering": rules.covering_of(leave.one_covering), "one_away_message": "Off to Beirut."},
			"en",
		)
		assert said.startswith("Off to Beirut.") and "Samir" in said, "her words, then who covers"
		assert back > frappe.utils.getdate(leave.to_date)
		assert rules.half_day_today(frappe._dict(half_day=1, from_date=today(), to_date=today(), half_day_date=None))
		leave.docstatus = 2
		rules.covered(leave)
		assert not actions.holds(theirs, "samir@one.test"), "cancelled, and he no longer reads it"
	finally:
		frappe.db.delete("User Email", {"email_account": theirs, "one_cover_until": ["is", "set"]})
		frappe.db.set_value(
			"Email Account",
			theirs,
			{"one_away": 0, "one_away_from": None, "one_away_until": None, "one_away_to": "Everyone"},
			update_modified=False,
		)
		frappe.db.delete("Notification Log", {"for_user": "samir@one.test", "subject": ["like", "%covering%"]})


@check
def onemail_a_shared_mailbox_is_connected_given_and_let_go():
	"""Layla connects the company's sales mailbox for the team, chooses who
	holds it, makes it the Default Incoming and Outgoing and back, which never
	moves the sender notifications go out from, gives its password again and
	disconnects it, and gives Huda a second address. The mail server is not
	dialled: where it is is said here. The Worker's notice is believed only
	with the workspace's signature."""
	import time
	from unittest import mock

	from onedesk.one_mail import connect, holders, inbound

	where = {key: value for key, value in connect.guesses("saharaglass.test")[0].items()}
	smtp = "frappe.email.doctype.email_account.email_account.EmailAccount.validate_smtp_conn"
	with as_user(OWNER), mock.patch("onedesk.one_mail.connect.reach", return_value=where), mock.patch(
		"onedesk.one_mail.connect._smtp"
	), mock.patch(smtp), mock.patch("frappe.enqueue"):
		sales = connect.connect("sales@saharaglass.test", "app-password", shared=1)
		assert frappe.db.get_value("Email Account", sales, ["one_connected", "one_shared"]) == (1, 1)
		said = connect.connection_of(sales)
		assert said["incoming"] and said["incoming"].startswith(where["email_server"]), said
		holders.set_access(sales, [{"user": OWNER, "sends": 1}, {"user": "omar@one.test", "sends": 1}])
		assert set(frappe.get_all("User Email", filters={"email_account": sales}, pluck="parent")) == {OWNER, "omar@one.test"}
		system, ours = holders.system_sender(), holders.workspace()
		assert holders.set_defaults(incoming=sales, outgoing=sales) == {"incoming": sales, "outgoing": sales}
		assert holders.mailbox(sales)["sends_default"] and holders.system_sender() == system, "notifications moved"
		from onedesk.one import notify

		assert notify.replies_to() == "sales@saharaglass.test"
		assert holders.set_defaults(incoming=ours, outgoing=ours) == {"incoming": ours, "outgoing": ours}
		assert holders.system_sender() == system
		from onedesk.one_mail import addresses

		holders.set_external(0)
		with as_user("omar@one.test"):
			work = connect.connect("omar@saharaglass.test", "app-password")
			try:
				connect.connect("omar.farouk@gmail.test", "app-password")
				raise AssertionError("a private mailbox was connected while they are off")
			except frappe.ValidationError:
				pass
		holders.set_external(1)
		with as_user("omar@one.test"):
			private = connect.connect("omar.farouk@gmail.test", "app-password")
		listed = [one["name"] for one in holders.addresses_of_people()]
		assert work in listed and private not in listed, listed
		assert holders.may(work, "signature") and not holders.may(private, "signature")
		with as_user("omar@one.test"):
			assert holders.may(private, "signature") and holders.mailbox(private)["private"]
			connect.disconnect(private)
			connect.disconnect(work)
		with mock.patch("onedesk.one_mail.connect.hosted_by", return_value=connect.HOSTED_BY["google.com"]):
			assert connect.servers_for("saharaglass.org")["email_server"] == "imap.gmail.com", "Google Workspace, by MX"
		served = "frappe.email.doctype.email_domain.email_domain.EmailDomain.validate_"
		with mock.patch(served + "incoming_server_conn"), mock.patch(served + "outgoing_server_conn"):
			connect.add_domain("saharaglass.org", "mail.saharaglass.org", 993, "mail.saharaglass.org", 587)
		assert "saharaglass.org" in [one["domain_name"] for one in connect.domains()]
		assert connect.candidates("karim@saharaglass.org")[0]["email_server"] == "mail.saharaglass.org"
		karim = connect.connect_for("karim@one.test", "karim@saharaglass.org", "app-password")
		assert frappe.db.exists("User Email", {"parent": "karim@one.test", "email_account": karim}), "connected for Karim"
		try:
			connect.connect_for("karim@one.test", "karim.mansour@gmail.test", "app-password")
			raise AssertionError("an administrator connected somebody's private mailbox")
		except frappe.ValidationError:
			pass
		connect.disconnect(karim)
		connect.remove_domain("saharaglass.org")
		connect.reconnect(sales, "new-app-password")
		connect.disconnect(sales)
		assert not frappe.db.exists("Email Account", sales)
	with as_user("omar@one.test"):
		try:
			holders.shared()
			raise AssertionError("Omar listed who holds the workspace's mailboxes")
		except frappe.PermissionError:
			pass

	body = b'{"key": "mail/2026/10/07/x~layla.eml"}'
	at = str(int(time.time()))
	with mock.patch.dict(frappe.conf, {"one_mail_secret": "demo-secret"}), mock.patch("frappe.enqueue") as queued:
		frappe.set_user("Guest")
		_asked(data=body, headers={"X-One-Timestamp": at, "X-One-Signature": inbound.signed("demo-secret", at, body)})
		assert inbound.notice() == "ok" and queued.call_args.args[0] == "onedesk.one_mail.inbound.sweep"
		_asked(data=body, headers={"X-One-Timestamp": at, "X-One-Signature": "0" * 64})
		try:
			inbound.notice()
			raise AssertionError("an unsigned notice was believed")
		except frappe.PermissionError:
			pass
	_unasked()


@check
def onemail_oneai_tells_a_sender_only_their_own_records():
	"""A rule's OneAI reply reading their records is given what the portal
	shows the sender, only when the receiving server verified them: Khalid
	of Mansour & Sons gets his own quotations, orders, invoices with what is
	still to pay, and deliveries, and nobody else's: all that is still open
	and the latest of the rest; the same address with a
	forged From line, or a stranger, gets nothing, and a reply not set to
	read records is told to say nothing about them. Verified, OneAI may open
	one of his records in full, and is refused anyone else's."""
	from unittest import mock

	from onedesk.one_mail import rules, theirs

	passed = "mx.example; dkim=pass header.d=mansour.example; dmarc=pass header.from=mansour.example"
	forged = "mx.example; dkim=fail header.d=mansour.example; dmarc=fail header.from=mansour.example"
	assert theirs.verified({"Authentication-Results": passed}, "khalid@mansour.example")
	assert not theirs.verified({"Authentication-Results": forged}, "khalid@mansour.example")

	rows = theirs.records("khalid@mansour.example", "When does my order arrive?")
	assert rows and {row["party"] for row in rows} == {"Mansour & Sons"}, rows
	assert {row["doctype"] for row in rows} >= {"Sales Order", "Sales Invoice"}
	owed = [row["name"] for row in rows if row["doctype"] == "Sales Invoice" and row["status"] != "Paid"]
	open_ = frappe.get_all("Sales Invoice", filters={"customer": "Mansour & Sons", "docstatus": 1, "outstanding_amount": (">", 0)}, pluck="name")
	assert set(open_) <= set(owed), "every invoice still to pay, however old"
	assert any(row.get("owed") for row in rows), "what is still to pay on a part-paid one"
	assert len(theirs.records("khalid@mansour.example", "About ACC-PINV-2026-00019")) == len(rows), "a name not theirs adds nothing"

	asked, looked = [], []

	def ask(action, text, reference=None, only=None, nudges=True):
		from onedesk.one_ai import tools as surface

		asked.append(text)
		looked.append(surface.run("their_record", {"doctype": "Sales Invoice", "name": "ACC-SINV-2026-00001"})["answer"]["totals"])
		try:
			surface.run("their_record", {"doctype": "Purchase Invoice", "name": "ACC-PINV-2026-00019"})
			looked.append("leaked")
		except frappe.ValidationError:
			pass
		return {"said": "ok"}

	with mock.patch("onedesk.one_ai.run.once", side_effect=lambda kind, text, reference=None: asked.append(text) or "ok"), mock.patch(
		"onedesk.one_ai.run.ask", side_effect=ask
	):
		mail = frappe._dict(name=None, sender="khalid@mansour.example", subject="Invoice", content="How much do we owe?")
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=0))
		rules._drafted({"instruction": "Answer from their records.", "records": 0}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer.", "records": 1}, frappe._dict(mail, sender="nobody@stranger.example", one_verified=1))
	assert "ACC-SINV-2026-00001" in asked[0] and "Mansour & Sons" in asked[0]
	assert len(looked) == 1 and any(one.get("label") == "To pay" for one in looked[0]), "one record in full, only theirs"
	assert not frappe.flags.one_ai_tools and not frappe.flags.one_mail_sender, "the tools go with the run"
	assert all("SINV" not in one and "could not be confirmed" in one for one in asked[1:2])
	assert "SINV" not in asked[2] and "Say nothing about any order" in asked[2]
	assert "SINV" not in asked[3] and "Nothing is known" in asked[3]


@check
def onemail_oneai_replies_say_who_wrote_them():
	"""A rule that has OneAI answer sends the reply with a line saying OneAI
	wrote it, as the AI Addendum's onemail-answers says; a reply a person
	wrote for the rule carries no such line."""
	from unittest import mock

	from onedesk.one_mail import holders, rules

	account = frappe.get_doc("Email Account", holders.workspace())
	name = frappe.db.get_value("Communication", {"email_account": account.name, "sent_or_received": "Received"}, "name")
	sent = []
	rule = frappe._dict(name="check-oneai-answers")
	with mock.patch("onedesk.one_mail.gate.of", return_value=frappe._dict(one_ai_off=0)), mock.patch(
		"onedesk.one_mail.gate.over", return_value=False
	), mock.patch.object(rules, "_drafted", return_value="Thank you, we will visit on Tuesday."), mock.patch.object(
		rules, "_send", side_effect=lambda account, comm, html: sent.append(html)
	):
		frappe.cache.delete_keys("one_rule_reply:check-oneai-answers")
		assert rules.answer(rule, {"type": "reply", "with": "OneAI", "instruction": "Offer a visit."}, name) == "sent"
	assert sent and "automatically by OneAI, an AI agent" in sent[0], sent
	frappe.cache.delete_keys("one_rule_reply:check-oneai-answers")


@check
def onemail_a_mailbox_says_what_oneai_may_do_with_its_mail():
	"""Layla switches off Create Tasks for the workspace mailbox: OneIntake
	then makes no task from its mail, while a link it still makes; once a
	rule has made a task from a message, OneIntake makes no second one;
	an unknown job, or a reading from no mailbox, is never held back. Setting
	New Mail to Not Read names the rules that ask OneAI, which then show as
	not running."""
	from onedesk.one_intake import act
	from onedesk.one_mail import gate, holders, rules

	ours = holders.workspace()
	reading = frappe.get_doc("Reading", frappe.db.get_value("Reading", {"source_doctype": "Communication"}, "name", order_by="creation desc"))
	account = gate.account_of("Reading", reading.name)
	assert account, "a reading of mail knows its mailbox"
	reading.on_behalf_of, reading.history = OWNER, 0
	with as_user(OWNER):
		said = gate.set_settings(account, skips=["tasks", "made up"])
	assert said["skips"] == ["tasks"], said["skips"]
	frappe.local.flags.one_intake_mailbox = {}
	task = act.Action("Create", "Task", values={"subject": "Call back"}, key="task", sure=True)
	assert act.apply(task, reading) is None, "a job switched off makes nothing"
	assert gate.does(account, "link") and gate.does(None, "tasks") and gate.does(account, None)
	with as_user(OWNER):
		gate.set_settings(account, skips=[])
	frappe.local.flags.one_intake_mailbox = {}
	assert act.apply(task, reading), "switched back on, it is done or proposed"

	from onedesk.one_mail import linking

	message = gate.message_of(reading.name)
	assert message, "a reading of mail knows its message"
	ruled = frappe.get_doc({"doctype": "Task", "subject": "Made by a rule"}).insert(ignore_permissions=True)
	linking.add(message, "Task", ruled.name, "rule")
	again = act.Action("Create", "Task", values={"subject": "Call back again"}, key="task|again", sure=True)
	assert act.apply(again, reading) is None, "a rule made a task from this message: OneAI makes none"
	event = act.Action("Create", "Event", values={"subject": "Visit", "starts_on": frappe.utils.now()}, key="event", sure=True)
	assert act.apply(event, reading), "the rule's task holds back no other kind"

	frappe.db.set_value("Email Account", ours, "one_intake", 1)
	with as_user(OWNER):
		rules.save_rule(ours, {"title": "Complaints", "steps": [{"type": "ask", "id": "a", "ask": "yes", "question": "a complaint", "then": [{"type": "star"}], "else": []}]})
		assert "Complaints" in gate.settings_of(ours)["asks"]
		gate.set_settings(ours, reads=0)
		listed = rules.rules_of_mailbox(ours)
	assert not listed["reads"] and any(one["needs_ai"] and one["title"] == "Complaints" for one in listed["rules"])


@check
def onemail_oneai_reaches_what_the_page_changes():
	"""OneAI's cards for what OneMail's page changes (ai.REACH), each approved
	as Layla, so done by the page's own call: a folder made, a conversation
	moved into it, starred, filed on the villa and back, the folder renamed
	and deleted; her out of office on and off; a rule turned off and
	deleted; Omar given the workspace's mailbox to read and taken off; her
	own mailboxes allowed and not; the composer's template for interviews;
	the company's domain on a card. Omar gets no card for what his role
	doesn't reach."""
	from unittest import mock

	from onedesk.one_ai import run as runs
	from onedesk.one_demo import intake
	from onedesk.one_mail import actions, addresses, ai, api, holders, mail_templates

	account = intake.mailbox()
	email = frappe.db.get_value("Email Account", account, "email_id")
	made = []

	def approve(said: dict) -> None:
		assert said.get("proposal"), said
		made.append(said["proposal"])
		runs.apply(said["proposal"])

	with as_user(OWNER):
		thread = api.conversations(account, search='subject:"shop drawings"')["items"][0]["thread"]
		names = api.names(account, [thread])
		external, template = addresses.external(), mail_templates.default("Interview")
		try:
			approve(ai.change_folder("make", label="Reach Check", mailbox=email))
			folder = frappe.db.get_value("Mail Folder", {"account": account, "label": "Reach Check"}, "name")
			assert folder
			approve(ai.sort_conversations("move", [thread], mailbox=email, folder="Reach Check"))
			assert frappe.db.get_value("Communication", names[0], "one_folder") == frappe.db.get_value("Mail Folder", folder, "path")
			approve(ai.sort_conversations("star", [thread], mailbox=email))
			assert frappe.db.get_value("Communication", names[0], "one_flagged") == 1
			approve(ai.sort_conversations("move", [thread], mailbox=email, folder="Inbox"))
			assert frappe.db.get_value("Communication", names[0], "one_folder") == "INBOX"
			approve(ai.file_conversation(thread, "Project", VILLA, mailbox=email))
			assert frappe.db.exists("Communication Link", {"parent": names[0], "link_doctype": "Project", "link_name": VILLA})
			approve(ai.file_conversation(thread, "Project", VILLA, take_off=True, mailbox=email))
			assert not frappe.db.exists("Communication Link", {"parent": names[0], "link_doctype": "Project", "link_name": VILLA})
			approve(ai.change_folder("rename", label="Reach Checked", folder="Reach Check", mailbox=email))
			assert frappe.db.get_value("Mail Folder", folder, "label") == "Reach Checked"
			approve(ai.change_folder("delete", folder="Reach Checked", mailbox=email))
			assert not frappe.db.exists("Mail Folder", folder)

			approve(ai.suggest_away(True, mailbox=email, until=str(add_days(today(), 5)), message="Back on Monday."))
			assert frappe.db.get_value("Email Account", account, "one_away") == 1
			approve(ai.suggest_away(False, mailbox=email))
			assert frappe.db.get_value("Email Account", account, "one_away") == 0

			approve(ai.suggest_mail_rule("Reach Check", mailbox=email, subject_contains="reach check"))
			rule = next(one["rule"] for one in ai.mail_rules(email)["rules"] if one["title"] == "Sort mail into Reach Check")
			approve(ai.change_mail_rule(rule, "off"))
			assert frappe.db.get_value("Mail Rule", rule, "enabled") == 0
			approve(ai.change_mail_rule(rule, "delete"))
			assert not frappe.db.exists("Mail Rule", rule)
			actions.delete_folder(frappe.db.get_value("Mail Folder", {"account": account, "label": "Reach Check"}))

			ours = holders.workspace()
			held = {row["user"]: row["sends"] for row in holders._people(ours)}
			listed = ai.workspace_mail()
			assert any(one["workspace"] for one in listed["mailboxes"]), listed
			approve(ai.share_mailbox(ours, "huda@one.test", sends=False))
			assert frappe.db.exists("User Email", {"parent": "huda@one.test", "email_account": ours})
			approve(ai.share_mailbox(ours, "huda@one.test", reads=False))
			assert not frappe.db.exists("User Email", {"parent": "huda@one.test", "email_account": ours})
			assert {row["user"]: row["sends"] for row in holders._people(ours)} == held

			approve(ai.suggest_mail_policy(own_mailboxes=not external))
			assert addresses.external() == (not external)

			approve(ai.default_mail_template("Interview", "Interview Reminder"))
			assert mail_templates.default("Interview") == "Interview Reminder"
			with mock.patch("onedesk.one_mail.connect.hosted_by", return_value=None):
				card = ai.company_domain("reachcheck.example")
			made.append(card["proposal"])
			assert "imap.reachcheck.example" in frappe.db.get_value("AI Proposal", card["proposal"], "changes")
		finally:
			holders.set_external(int(external))
			if template:
				mail_templates.set_default("Interview", template)
			else:
				frappe.db.delete("Property Setter", {"doc_type": "Interview", "property": "default_email_template"})
				frappe.clear_cache(doctype="Interview")
	with as_user("omar@one.test"):
		assert ai.share_mailbox(holders.workspace(), "huda@one.test").get("error")
		assert ai.suggest_mail_policy(own_mailboxes=True).get("error")
		assert ai.company_domain("reachcheck.example").get("error")
	for one in made:
		frappe.delete_doc("AI Proposal", one, ignore_permissions=True, force=True)
