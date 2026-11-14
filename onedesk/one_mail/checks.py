"""OneMail's part of the integration suite (one_demo/check.py runs it): the
demo company's mail read back as the people in it, from Layla sorting her
own to a shared mailbox given and let go, rules, out of office and what
OneAI may read."""

import frappe
from frappe.utils import add_days, today

from onedesk.one_demo.base import as_user
from onedesk.one_demo.checking import VILLA, _asked, _employee, _unasked, check
from onedesk.one_demo.people import OWNER


@check
def onemail_layla_reads_sorts_and_files_her_mail():
	"""Layla's own address, with the mail the samples brought: a folder read,
	a conversation opened, read and starred, moved into a folder of her own
	and back, deleted and put back, filed on the villa and taken off, sorted
	by a rule OneAI suggests, and answered on a card. Her out of office and
	her workspace's signature. Omar cannot see into her mailbox."""
	from onedesk.one_demo import intake
	from onedesk.one_mail import actions, agent, api, holders, linking, rules
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
		unread = frappe.db.count("Communication", {"email_account": account, "one_folder": "INBOX", "seen": 0, "one_held": 0})
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

		opened = agent.open_conversation(account, thread)
		assert opened["subject"] == "Shop drawings for the New York lobby" and opened["messages"]
		assert thread in {one["thread"] for one in agent.waiting_for_answer(account, inbox)["waiting"]}
		reply = agent.draft_reply(account, thread, "Dear Jordan,\n\nThe drawings follow on Monday.\n\nLayla")
		assert frappe.db.get_value("AI Proposal", reply["proposal"], "state") == "Proposed"
		rule = agent.suggest_mail_rule("Taxis", mailbox=account, text_contains="taxi", sort_inbox_now=True)["proposal"]
		from onedesk.one_ai import run as runs

		runs.apply(rule)
		taxis = frappe.db.get_value("Mail Folder", {"account": account, "label": "Taxis"}, "path")
		assert frappe.db.exists("Automation", {"trigger": "one_mail.arrives", "scope": account, "steps": ["like", "%taxi%"]})
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
	from onedesk.one_mail import agent, gate, holders, mail_templates, rules, signatures
	from onedesk.one_cloud import api

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
		assert "error" in agent.open_conversation(own, "anything"), "the panel can't read a mailbox OneAI is off for"
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
		assert not frappe.db.get_value("Automation", made, "enabled")
		rules.delete_rule(made)
		holders.set_external(0)
		holders.set_allowed_domains(["gmail.com"])
		holders.set_allowed_domains([])
		holders.set_external(1)
		assert isinstance(mail_templates.templates(), list)
		sent = "Exit Questionnaire Notification"
		if frappe.db.exists("Email Template", sent):
			mail_templates.settle()
			was = frappe.db.get_single_value("HR Settings", "exit_questionnaire_notification_template")
			frappe.db.set_single_value("HR Settings", "exit_questionnaire_notification_template", sent)
			try:
				row = next(one for one in mail_templates.templates() if one["name"] == sent)
				assert row["reference_doctype"] == "Exit Interview", row
				assert row["used_by"] and row["code"], "HR's template says who sends it and that it holds code"
				try:
					frappe.delete_doc("Email Template", sent)
					raise AssertionError("a template HR Settings sends was deleted")
				except frappe.ValidationError:
					pass
			finally:
				frappe.db.set_single_value("HR Settings", "exit_questionnaire_notification_template", was)
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
		assert frappe.db.get_value("Automation", asked, ["enabled", "requested_by"]) == (0, "rania@one.test")
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
		assert frappe.db.get_value("Automation", asked, ["enabled", "requested_by"]) == (1, None)
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

	from onedesk.one.automation import engine, flow
	from onedesk.one_mail import blocks, holders, rules
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
		steps = engine.steps_of(frappe.get_doc("Automation", sort))
		assert flow.walk(steps, rules.facts_of(message), engine.kinds_of(blocks.ARRIVES), flow.answers_of(sort, steps, set()))[0] == [{"type": "read"}], "Otherwise"
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
	mine = next(row["name"] for row in rows if row["doctype"] == "Sales Invoice" and row.get("owed"))
	other = frappe.get_all("Purchase Invoice", filters={"docstatus": 1}, pluck="name", limit=1)[0]
	assert len(theirs.records("khalid@mansour.example", f"About {other}")) == len(rows), "a name not theirs adds nothing"

	asked, looked, agent = [], [], []

	def ask(app, action, text, turns, reference=None, tools=None):
		agent.append(app)
		asked.append(text)
		reads = {fn.__name__: fn for fn in tools[0]}
		if reads:
			looked.append(reads["their_record"]("Sales Invoice", mine)["totals"])
			try:
				reads["their_record"]("Purchase Invoice", other)
				looked.append("leaked")
			except frappe.ValidationError:
				pass
		return {"said": "ok"}

	with mock.patch("onedesk.one_ai.agents.talk.ask", side_effect=ask):
		mail = frappe._dict(name=None, sender="khalid@mansour.example", subject="Invoice", content="How much do we owe?")
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer from their records.", "records": 1}, frappe._dict(mail, one_verified=0))
		rules._drafted({"instruction": "Answer from their records.", "records": 0}, frappe._dict(mail, one_verified=1))
		rules._drafted({"instruction": "Answer.", "records": 1}, frappe._dict(mail, sender="nobody@stranger.example", one_verified=1))
	assert mine in asked[0] and "Mansour & Sons" in asked[0]
	assert len(looked) == 1 and any(one.get("label") == "To pay" for one in looked[0]), "one record in full, only theirs"
	assert not frappe.flags.one_mail_sender, "the sender goes with the run"
	assert set(agent) == {"one_mail"}, "every reply is the receptionist's"
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
	"""Layla switches off Create Tasks for the workspace mailbox: OneAI
	then makes no task from its mail, while a link it still makes; once a
	rule has made a task from a message, OneAI makes no second one;
	an unknown job, or a reading from no mailbox, is never held back. Setting
	New Mail to Not Read names the rules that ask OneAI, which then show as
	not running."""
	from onedesk.one_ai.reading import act
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
	"""OneAI's cards for what OneMail's page changes (agent.REACH), each approved
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
	from onedesk.one_mail import actions, addresses, agent, api, holders, mail_templates

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
			approve(agent.change_folder("make", label="Reach Check", mailbox=email))
			folder = frappe.db.get_value("Mail Folder", {"account": account, "label": "Reach Check"}, "name")
			assert folder
			approve(agent.sort_conversations("move", [thread], mailbox=email, folder="Reach Check"))
			assert frappe.db.get_value("Communication", names[0], "one_folder") == frappe.db.get_value("Mail Folder", folder, "path")
			approve(agent.sort_conversations("star", [thread], mailbox=email))
			assert frappe.db.get_value("Communication", names[0], "one_flagged") == 1
			approve(agent.sort_conversations("move", [thread], mailbox=email, folder="Inbox"))
			assert frappe.db.get_value("Communication", names[0], "one_folder") == "INBOX"
			approve(agent.file_conversation(thread, "Project", VILLA, mailbox=email))
			assert frappe.db.exists("Communication Link", {"parent": names[0], "link_doctype": "Project", "link_name": VILLA})
			approve(agent.file_conversation(thread, "Project", VILLA, take_off=True, mailbox=email))
			assert not frappe.db.exists("Communication Link", {"parent": names[0], "link_doctype": "Project", "link_name": VILLA})
			approve(agent.change_folder("rename", label="Reach Checked", folder="Reach Check", mailbox=email))
			assert frappe.db.get_value("Mail Folder", folder, "label") == "Reach Checked"
			approve(agent.change_folder("delete", folder="Reach Checked", mailbox=email))
			assert not frappe.db.exists("Mail Folder", folder)

			approve(agent.suggest_away(True, mailbox=email, until=str(add_days(today(), 5)), message="Back on Monday."))
			assert frappe.db.get_value("Email Account", account, "one_away") == 1
			approve(agent.suggest_away(False, mailbox=email))
			assert frappe.db.get_value("Email Account", account, "one_away") == 0

			approve(agent.suggest_mail_rule("Reach Check", mailbox=email, subject_contains="reach check"))
			rule = next(one["rule"] for one in agent.mail_rules(email)["rules"] if one["title"] == "Sort mail into Reach Check")
			approve(agent.change_mail_rule(rule, "off"))
			assert frappe.db.get_value("Automation", rule, "enabled") == 0
			approve(agent.change_mail_rule(rule, "delete"))
			assert not frappe.db.exists("Automation", rule)
			actions.delete_folder(frappe.db.get_value("Mail Folder", {"account": account, "label": "Reach Check"}))

			ours = holders.workspace()
			held = {row["user"]: row["sends"] for row in holders._people(ours)}
			listed = agent.workspace_mail()
			assert any(one["workspace"] for one in listed["mailboxes"]), listed
			approve(agent.share_mailbox(ours, "huda@one.test", sends=False))
			assert frappe.db.exists("User Email", {"parent": "huda@one.test", "email_account": ours})
			approve(agent.share_mailbox(ours, "huda@one.test", reads=False))
			assert not frappe.db.exists("User Email", {"parent": "huda@one.test", "email_account": ours})
			assert {row["user"]: row["sends"] for row in holders._people(ours)} == held

			approve(agent.suggest_mail_policy(own_mailboxes=not external))
			written = frappe.db.get_value("DefaultValue", {"parent": "__default", "defkey": addresses.EXTERNAL}, "defvalue")
			assert written == str(int(not external)), (written, external)

			approve(agent.default_mail_template("Interview", "Interview Reminder"))
			assert mail_templates.default("Interview") == "Interview Reminder"
			with mock.patch("onedesk.one_mail.connect.hosted_by", return_value=None):
				card = agent.company_domain("reachcheck.example")
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
		assert agent.share_mailbox(holders.workspace(), "huda@one.test").get("error")
		assert agent.suggest_mail_policy(own_mailboxes=True).get("error")
		assert agent.company_domain("reachcheck.example").get("error")
	for one in made:
		frappe.delete_doc("AI Proposal", one, ignore_permissions=True, force=True)


@check
def onemail_a_team_works_its_shared_mailbox():
	"""The workspace's address worked by a team: who wrote and what of theirs
	is open, assigning, notes, done and opened again, snooze and reminders,
	drafts kept and found again, a scheduled mail taken back, OneAI's card,
	and nothing for somebody who doesn't hold the mailbox."""
	from frappe.utils import add_to_date, now_datetime

	from onedesk.one_ai import run as runs
	from onedesk.one_demo.checking import _Told
	from onedesk.one_mail import agent, api, drafts, holders, sender, team

	account = holders.workspace()
	email = frappe.db.get_value("Email Account", account, "email_id")
	inbox = frappe.db.get_value("Mail Folder", {"account": account, "kind": "Inbox"})
	with as_user(OWNER):
		found = api.conversations(account, search="from:marinahotels")["items"]
		assert found, "the hotel's mail is in the workspace's inbox"
		thread = found[0]["thread"]
		about = sender.about("rashid@marinahotels.example")
		assert about and about["doctype"] == "Customer" and about["title"] == "Marina Hotels Group", about
		assert {one["doctype"] for one in about["groups"]} & {"Sales Order", "Sales Invoice"}, about["groups"]
		said = team.state(account, thread)
		assert said["shared"] and "mariam@one.test" in {one["user"] for one in said["people"]}
		team.assign(account, thread, "mariam@one.test")
		conversation = frappe.db.get_value("Mail Conversation", {"account": account, "thread": thread})
		assert frappe.db.exists("ToDo", {"reference_type": "Mail Conversation", "reference_name": conversation, "allocated_to": "mariam@one.test", "status": "Open"})
		assert team.opened(conversation) == team.place(account, thread)
	with as_user("mariam@one.test"):
		assert thread in {one["thread"] for one in api.conversations(account, inbox, team="mine")["items"]}
		assert thread not in {one["thread"] for one in api.conversations(account, inbox, team="unassigned")["items"]}
		assert team.note(account, thread, "Booked the fitter for Tuesday morning.")["notes"][-1]["by"] == "Mariam Saleh"
		team.replying(account, thread, 1)
		assert thread in {one["thread"] for one in agent.mail_for_me()["given_to_me"]}
		assert team.done(account, thread)["status"] == "Done"
		assert not frappe.db.exists("ToDo", {"reference_type": "Mail Conversation", "reference_name": conversation, "status": "Open"}), "done closes its assignment"
		assert thread in {one["thread"] for one in api.conversations(account, inbox, team="done")["items"]}
	reply = frappe.get_doc("Communication", found[0]["name"]).as_dict()
	team.arrived(frappe._dict(reply, sent_or_received="Received", one_thread=thread, communication_medium="Email"))
	assert frappe.db.get_value("Mail Conversation", conversation, "status") == "Open", "a new mail from outside opens it again"

	with as_user("mariam@one.test"):
		team.snooze(account, thread, str(add_to_date(now_datetime(), hours=3)))
		assert thread not in {one["thread"] for one in api.conversations(account, inbox)["items"]}, "a snoozed conversation leaves the inbox"
		assert thread in {one["thread"] for one in api.conversations(account, search="is:snoozed")["items"]}
		team.remind(account, thread, str(add_to_date(now_datetime(), hours=1)))
	frappe.db.set_value("Mail Conversation", conversation, {"snoozed_until": add_to_date(now_datetime(), minutes=-1), "remind_at": add_to_date(now_datetime(), minutes=-1)})
	with _Told() as told:
		team.due()
	assert told.to("No Reply Yet") == {"mariam@one.test"}, told.said
	with as_user("mariam@one.test"):
		assert thread in {one["thread"] for one in api.conversations(account, inbox)["items"]}, "back in the inbox when its time comes"

		draft = drafts.save(sender=email, subject="Re: Balcony doors", recipients="rashid@marinahotels.example", content="<p>Tuesday at 9 suits us.</p>", in_reply_to=found[0]["name"], kind="Reply")
		assert draft and drafts.get(draft)["recipients"] == "rashid@marinahotels.example"
		assert api.conversation(account, thread)["draft"] == draft, "the draft waits on its conversation"
		assert drafts.replying_to(draft)["name"] == found[0]["name"]
		box_drafts = frappe.db.get_value("Mail Folder", {"account": account, "kind": "Drafts"})
		assert draft in {one.get("draft") for one in api.conversations(account, box_drafts)["items"]}
		assert drafts.save(sender="nobody@stranger.example", subject="x") is None, "nothing is kept for an address the writer doesn't hold"
		listed_to = drafts.save(sender=email, subject="List", recipients='["rashid@marinahotels.example", "hessa@bayview.example"]')
		assert frappe.db.get_value("Mail Draft", listed_to, "recipients") == "rashid@marinahotels.example, hessa@bayview.example", "the composer's list is kept as addresses"
		drafts.discard(listed_to)
		drafts.discard(draft)
		assert not frappe.db.exists("Mail Draft", draft)

		from frappe.core.doctype.communication.email import make

		later = make(
			recipients="rashid@marinahotels.example",
			subject="Fitter booked",
			content="<p>Tuesday, 9 in the morning.</p>",
			sender=email,
			send_email=True,
			send_after=str(add_to_date(now_datetime(), hours=2)),
		)["name"]
		assert drafts.scheduled([later]), "a mail scheduled for later waits in the queue"
		back = drafts.unschedule(later)
		assert frappe.db.get_value("Mail Draft", back, "subject") == "Fitter booked" and not frappe.db.exists("Communication", later)

	with as_user(OWNER):
		card = agent.work_conversation("assign", thread=thread, person="mariam@one.test", mailbox=email)
		assert agent.work_conversation("done", subject="Balcony doors").get("proposal"), "found by its subject"
		assert card.get("proposal"), card
		runs.apply(card["proposal"])
		assert "mariam@one.test" in {one["user"] for one in team.state(account, thread)["assigned"]}
	with as_user("nadia@one.test"):
		for call in (lambda: team.state(account, thread), lambda: team.done(account, thread)):
			try:
				call()
			except frappe.PermissionError:
				continue
			raise AssertionError("somebody who doesn't hold the mailbox worked its conversation")


@check
def onemail_a_connected_mailboxs_drafts_are_on_its_server():
	"""A draft written for a connected mailbox is kept in its Drafts on the
	server, with one Message-ID however often it changes, so a phone shows
	it; sent or thrown away, it leaves there too; and its copy read back is
	not listed twice. The server is stood in for."""
	from unittest import mock

	from onedesk.one_mail import api, drafts, holders

	account = holders.workspace()
	email = frappe.db.get_value("Email Account", account, "email_id")
	frappe.db.set_value("Email Account", account, "one_connected", 1, update_modified=False)
	said = []

	class Server:
		def __init__(self, *args, **kwargs):
			pass

		def __enter__(self):
			return self

		def __exit__(self, *args):
			return False

		def select(self, path, readonly=True):
			said.append(("select", path))

		def uids(self, criteria):
			said.append(("search", criteria))
			return [7] if any(one[0] == "append" for one in said) else []

		def expunge(self, uids):
			said.append(("expunge", tuple(uids)))

		def append(self, path, raw, flags):
			said.append(("append", path, flags, raw))

	with as_user(OWNER), mock.patch("frappe.enqueue"), mock.patch("onedesk.one_mail.imap.Session", Server):
		name = drafts.save(sender=email, subject="Glass samples", recipients="jordan@acme.example", content="<p>Two samples on Monday.</p>")
		message_id = frappe.db.get_value("Mail Draft", name, "message_id")
		assert message_id, "a connected mailbox's draft has a Message-ID"
		drafts.to_server(name)
		drafts.save(sender=email, name=name, subject="Glass samples", recipients="jordan@acme.example", content="<p>Three samples on Monday.</p>")
		drafts.to_server(name)
		assert frappe.db.get_value("Mail Draft", name, "message_id") == message_id, "one Message-ID however often it changes"
		appended = [one for one in said if one[0] == "append"]
		assert len(appended) == 2 and appended[-1][2] == "\\Draft \\Seen" and b"Three samples" in appended[-1][3], "kept on the server, the newest in place of the last"
		assert ("expunge", (7,)) in said, "the copy before it is taken out"
		path = frappe.db.get_value("Mail Folder", {"account": account, "kind": "Drafts"}, "path")
		copy = frappe.get_doc({"doctype": "Communication", "communication_medium": "Email", "email_account": account, "one_folder": path, "subject": "Glass samples", "message_id": message_id, "sent_or_received": "Sent", "sender": email}).insert(ignore_permissions=True)
		folder = frappe.db.get_value("Mail Folder", {"account": account, "kind": "Drafts"})
		listed = api.conversations(account, folder)["items"]
		assert name in {one.get("draft") for one in listed} and copy.name not in {one.get("name") for one in listed}, "its copy is not listed twice"
		said.clear()
		drafts.off_server(account, message_id)
		assert [one for one in said if one[0] == "expunge"] and not [one for one in said if one[0] == "append"], "thrown away, it leaves the server"


@check
def onemail_rules_are_automations_and_every_block_runs_from_automationcenter():
	"""Layla opens AutomationCenter: the workspace's mailbox is a place she
	keeps, with the demo's two rules in it as automations, its conditions and
	actions OneMail's blocks, and a new one may start from a starter. One she
	makes there with every condition OneMail declares and every action runs
	on a message as a rule did: junked, forwarded once, assigned to her, a
	task made from it and filed, linked, starred, read and told. Off, it does
	nothing; asked for, she approves it; deleted, it is gone."""
	from unittest import mock

	from onedesk.one import automation_center
	from onedesk.one.automation import kinds
	from onedesk.one_mail import blocks, holders, rules

	ours = holders.workspace()
	message = frappe.db.get_value("Communication", {"email_account": ours, "sent_or_received": "Received"}, "name")
	was = frappe.db.get_value("Communication", message, ["one_folder", "one_flagged", "seen"])
	tasks = set(frappe.get_all("Task", pluck="name"))
	made = None
	try:
		with as_user(OWNER):
			place = next(one for one in automation_center.places() if one["trigger"] == blocks.ARRIVES)
			assert any(one["scope"] == ours and one["manages"] for one in place["scopes"]), place
			listed = automation_center.automations(blocks.ARRIVES, ours)
			assert {"Supplier Invoices", "Newsletters"} <= {one["title"] for one in listed["rules"]}, "the demo's rules arrive as automations"
			offered = automation_center.blocks(blocks.ARRIVES, ours)
			assert {one["key"] for one in offered["conditions"]} == {one.key for one in kinds.conditions(blocks.ARRIVES)}
			every = {"move", "read", "star", "junk", "reply", "forward", "assign", "notify", "link", "create"}
			assert every <= {one["key"] for one in offered["actions"]}, offered["actions"]
			assert any(one["key"] == "acknowledge" for one in offered["starters"])
			assert automation_center.problems(blocks.ARRIVES, []) == [frappe._("Add at least one action.")]
			test = {
				"any": True,
				"items": [
					*({"field": one.key, "op": "contains", "value": "nothing like this"} for one in kinds.conditions(blocks.ARRIVES) if one.kind == "text"),
					*({"field": one.key, "value": True} for one in kinds.conditions(blocks.ARRIVES) if one.kind == "flag"),
					{"field": "sender_is", "op": "is", "value": "Employee"},
					{"field": "from", "op": "contains", "value": "@"},
				],
			}
			then = [
				{"type": "junk"},
				{"type": "forward", "to": "check@example.com"},
				{"type": "assign", "user": OWNER},
				{"type": "create", "doctype": "Task"},
				{"type": "link"},
				{"type": "star"},
				{"type": "read"},
				{"type": "notify", "user": OWNER},
			]
			made = automation_center.save(blocks.ARRIVES, ours, {"title": "Every Block", "priority": 1, "steps": [{"type": "if", "id": "i1", "test": test, "then": then, "else": []}, {"type": "stop"}]})
			assert automation_center.automation(made)["steps"][0]["then"] == then
		with mock.patch("frappe.core.doctype.communication.email.make") as sent:
			assert rules.run_rules(frappe.get_doc("Communication", message), headers={}) == [made], "stop: the rules after it do not run"
			rules.run_rules(frappe.get_doc("Communication", message), headers={})
		if frappe.db.get_value("Email Account", ours, "enable_outgoing"):
			assert sent.call_count == 1, "forwarded once"
		junk = frappe.db.get_value("Mail Folder", {"account": ours, "kind": "Junk"}, "path")
		if junk:
			assert frappe.db.get_value("Communication", message, "one_folder") == junk
		assert frappe.db.get_value("Communication", message, ["one_flagged", "seen"]) == (1, 1)
		assert frappe.db.exists("ToDo", {"reference_type": "Communication", "reference_name": message, "allocated_to": OWNER, "status": "Open"})
		task = frappe.db.get_value("Communication Link", {"parent": message, "link_doctype": "Task", "one_linked_by": "rule"}, "link_name")
		assert task and frappe.db.get_value("Task", task, "owner") == OWNER, "made as whoever made the rule, and filed with the message"
		with as_user(OWNER):
			automation_center.enable(made, 0)
		assert rules.run_rules(frappe.get_doc("Communication", message), headers={}) != [made], "off, it does nothing"
		frappe.db.set_value("Automation", made, "requested_by", "rania@one.test")
		with as_user(OWNER):
			automation_center.decide(made, 1)
		assert frappe.db.get_value("Automation", made, ["enabled", "requested_by"]) == (1, None)
		with as_user(OWNER):
			automation_center.delete(made)
		assert not frappe.db.exists("Automation", made)
		made = None
	finally:
		if made:
			frappe.delete_doc("Automation", made, ignore_permissions=True, force=True)
		for one in set(frappe.get_all("Task", pluck="name")) - tasks:
			frappe.db.delete("Communication Link", {"parent": message, "link_name": one})
			frappe.delete_doc("Task", one, ignore_permissions=True, force=True)
		frappe.db.delete("ToDo", {"reference_type": "Communication", "reference_name": message, "allocated_to": OWNER})
		frappe.db.set_value("Communication", message, dict(zip(("one_folder", "one_flagged", "seen"), was, strict=True)), update_modified=False)
		frappe.db.delete("Notification Log", {"for_user": ["in", [OWNER, "rania@one.test"]], "creation": [">=", frappe.utils.add_to_date(None, minutes=-5)]})


@check
def onemail_risky_mail_is_scored_warned_and_held():
	"""The mail samples in tests/samples/intake/one_mail, as they arrived in
	Layla's mailbox: the failing DMARC, the macro attachment and the
	mismatched link held as they arrived, the lookalike of Gulf Glass's
	domain warned and then held once OneAI read it as phishing, and the
	supplier's newsletter let through. Held lists them with their reasons
	and the Inbox does not; nothing held was read; released, one goes to
	OneAI and is never held again; deleted, one goes to Trash. Somebody who
	doesn't hold the mailbox releases nothing. Layla sets the levels."""
	from unittest import mock

	from onedesk.one_demo import intake, samples
	from onedesk.one_mail import api, held, lookalike, risk

	ours = {path.stem: path for path in samples.samples() if path.parent.name == "one_mail"}
	assert len(ours) == 5, ours
	by = {stem: samples.message_of(path) for stem, path in ours.items()}
	wrong = {stem: samples.risk_unmet(frappe.parse_json(path.read_text()), by[stem]) for stem, path in ours.items()}
	assert not any(wrong.values()), wrong
	assert "gulfglass.example" in lookalike.known(), "a supplier's contact's domain is known"
	found = frappe.parse_json(by["lookalike-domain"].one_risks)["found"]
	alone = risk.score([one for one in found if one["why"] != "phishing"])
	at = held.levels()
	assert at["warn"] <= alone < at["hold"], ("the lookalike alone is warned, not held", alone, at)
	for stem in ("failing-dmarc", "macro-attachment", "mismatched-link"):
		assert not samples.readings_of(ours[stem]), f"{stem} was read while held"

	account = intake.mailbox()
	thread_of = lambda name: frappe.db.get_value("Communication", name, "one_thread") or name  # noqa: E731
	with as_user(OWNER):
		box = next(one for one in api.mailboxes() if one["name"] == account)
		folder = next((one for one in box["folders"] if one["kind"] == "Held"), None)
		assert folder and folder["unread"] >= 4, box["folders"]
		subjects = {one["subject"] for one in api.conversations(account, held.FOLDER)["items"]}
		risky = {"Your payment could not be processed", "Delivery schedule for November", "Your online banking is locked", "New bank details for our invoices"}
		assert risky <= subjects, subjects
		inbox = next(one["name"] for one in box["folders"] if one["kind"] == "Inbox")
		assert not {one["subject"] for one in api.conversations(account, inbox)["items"]} & risky, "held mail is not in the Inbox"
		macro = by["macro-attachment"].name
		assert not api.conversation(account, thread_of(macro))["messages"], "a held message is shown only in Held"
		shown = api.conversation(account, thread_of(macro), held_back=1)["messages"][0]["risk"]
		assert shown["held"] and shown["reasons"], shown
		looks = by["lookalike-domain"].name
		said = api.conversation(account, thread_of(looks), held_back=1)["messages"][0]["risk"]
		assert said["imitates"] == "gulfglass.example" and any("gulfglass.example" in one for one in said["reasons"]), said

		frappe.db.savepoint("onemail_held")
		try:
			with mock.patch("onedesk.one_ai.reading.pipeline.later") as later:
				assert held.release([macro]) == 1
			assert not frappe.db.get_value("Communication", macro, "one_held")
			assert later.called, "released, it goes to OneAI's reading"
			assert held.release([macro]) == 0, "only held mail is released"
			held.judged(macro, "Phishing")
			assert not frappe.db.get_value("Communication", macro, "one_held"), "a released message is not held again"
			dmarc = by["failing-dmarc"].name
			assert held.discard([dmarc]) == 1
			trash = frappe.db.get_value("Mail Folder", {"account": account, "kind": "Trash"}, "path")
			assert frappe.db.get_value("Communication", dmarc, ["one_folder", "one_held"]) == (trash, 0)
			assert held.settings()["defaults"] == held.LEVELS
			held.set_levels(30, 60)
			assert held.levels() == {"warn": 30, "hold": 60}
			try:
				held.set_levels(60, 30)
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("Hold From below Warn From was kept")
		finally:
			from frappe.cache_manager import clear_defaults_cache

			frappe.db.rollback(save_point="onemail_held")
			clear_defaults_cache("__default")
	with as_user("rania@one.test"):
		try:
			held.release([by["mismatched-link"].name])
		except frappe.PermissionError:
			pass
		else:
			raise AssertionError("someone who doesn't hold the mailbox released its mail")


@check
def onemail_a_sample_link_and_file_are_shown_safely():
	"""The held samples' link and attachment, seen before anybody opens them,
	with the office Worker faked: the banking link opened in a throwaway
	browser shows where it ends, that it asks for a password and a picture,
	and only its address is sent; the macro workbook is checked, offered as
	a clean PDF first, and the original stays as it was. A link the message
	doesn't hold is refused, a program is never offered and nothing is sent
	for it, a failure says so and still offers the original, and somebody
	who doesn't hold the mailbox sees neither."""
	import base64
	import hashlib
	import io
	import os
	from unittest import mock

	from pypdf import PdfWriter

	from onedesk.one_admin import faults
	from onedesk.one_cloud import office
	from onedesk.one_demo import samples
	from onedesk.one_mail import risk, sandbox

	ours = {path.stem: path for path in samples.samples() if path.parent.name == "one_mail"}
	banking = samples.message_of(ours["mismatched-link"]).name
	workbook = samples.message_of(ours["macro-attachment"]).name
	attached = frappe.db.get_value(
		"File",
		{"attached_to_doctype": "Communication", "attached_to_name": workbook},
		["name", "file_name", "content_hash"],
		as_dict=True,
	)
	assert attached and attached.file_name == "Delivery Schedule November.xlsm", attached
	link = "http://203.0.113.45/enbd/login"
	assert link in sandbox.links_of(frappe.db.get_value("Communication", banking, "content"))
	plain = io.BytesIO()
	blank = PdfWriter()
	blank.add_blank_page(100, 100)
	blank.write(plain)
	sent = []
	answers = {
		"onedesk.one_admin.proxy.guard_link": {
			"final_url": "https://sign-in.example.com/login",
			"redirects": [link],
			"title": "Sign In",
			"asks_password": True,
			"picture": "AAAA",
			"failed": None,
			"credits": 1,
		},
		"onedesk.one_admin.proxy.guard_file": {
			"kind": "ooxml", "named": "xlsm", "mismatch": False, "program": None, "macros": attached.file_name, "scripts": False,
			"page": False, "inside": [], "count": 0, "unchecked": None, "office": True, "ending": "xlsm",
		},
		"onedesk.one_admin.proxy.office_convert": {"data": base64.b64encode(plain.getvalue()).decode(), "credits": 1},
	}  # fmt: skip

	def asked(endpoint, **said):
		sent.append((endpoint, said))
		return answers[endpoint]

	keys = [
		f"one_mail_looked:{hashlib.sha256(link.encode()).hexdigest()}",
		f"one_mail_checked:{attached.content_hash or attached.name}",
		f"one_cloud_office:{attached.content_hash}",
	]

	def forget():
		for key in keys:
			frappe.cache.delete_value(key)

	forget()
	frappe.db.savepoint("onemail_sandbox")
	frappe.db.set_value("File", attached.name, "one_preview_of", None, update_modified=False)
	try:
		with as_user(OWNER), mock.patch("onedesk.one.account.ask", side_effect=asked):
			seen = sandbox.link(banking, link)
			assert seen["asks_password"] and seen["moved"] and seen["site"] == "sign-in.example.com", seen
			assert seen["picture"] == "data:image/jpeg;base64,AAAA" and seen["redirects"] == 1, seen
			assert sent == [("onedesk.one_admin.proxy.guard_link", {"url": link})], "only the address goes, no session or cookie"
			sandbox.link(banking, link)
			assert len(sent) == 1, "a link seen a moment ago is not opened again"
			try:
				sandbox.link(banking, "https://example.com/anything")
			except frappe.ValidationError:
				pass
			else:
				raise AssertionError("a link the message doesn't hold was opened")

			said = sandbox.check(workbook, attached.name)
			assert said["state"] == "clean" and said["clean"], said
			assert risk.words({"why": "macro", "file": attached.file_name}) in said["reasons"], said
			assert said["original"], "the original is still offered, after the clean copy"
			endpoint, given = sent[1]
			assert endpoint == "onedesk.one_admin.proxy.guard_file" and given["name"] == attached.file_name and "exe" in given["programs"]
			assert sent[2][0] == "onedesk.one_admin.proxy.office_convert", sent
			sandbox.clean(workbook, attached.name)
			assert frappe.local.response.filecontent.startswith(b"%PDF")
			assert frappe.local.response.filename == "Delivery Schedule November.pdf"
			for key in ("type", "filecontent", "filename"):
				frappe.local.response.pop(key, None)
			assert frappe.db.get_value("File", attached.name, "content_hash") == attached.content_hash, "the original is untouched"

			program = frappe.get_doc(
				{
					"doctype": "File",
					"file_name": "Invoice 114.pdf.exe",
					"content": b"MZ" + b"\0" * 64,
					"is_private": 1,
					"attached_to_doctype": "Communication",
					"attached_to_name": workbook,
				}
			).insert(ignore_permissions=True)
			before = len(sent)
			never = sandbox.check(workbook, program.name)
			assert never["state"] == "never" and never["original"] is None and len(sent) == before, never

			forget()
			frappe.db.set_value("File", attached.name, "one_preview_of", None, update_modified=False)
			with mock.patch("onedesk.one.account.ask", side_effect=faults.Again("the account could not be reached")):
				failed = sandbox.check(workbook, attached.name)
				looked = sandbox.link(banking, link)
			assert failed["state"] == "unchecked" and failed["original"] and failed["reasons"], failed
			assert looked["failed"] == "service" and looked["warning"], looked
		with as_user("rania@one.test"):
			for tried in (lambda: sandbox.link(banking, link), lambda: sandbox.check(workbook, attached.name)):
				try:
					tried()
				except frappe.PermissionError:
					pass
				else:
					raise AssertionError("someone who doesn't hold the mailbox saw a link or a file")
	finally:
		frappe.db.rollback(save_point="onemail_sandbox")
		forget()
		if attached.content_hash and os.path.exists(office._on_disk(attached.content_hash)):
			os.remove(office._on_disk(attached.content_hash))
