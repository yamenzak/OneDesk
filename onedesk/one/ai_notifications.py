"""OneAI on NotificationCenter (one/agent.py lists these tools): what each
notification One sends says and where it goes, the reader's own, and a
notification's words or a rule drafted as a card."""

import json
from typing import Annotated

import frappe


def notification_type(
	name: Annotated[
		str, "The notification type, as it is listed, such as Letter Requested. Leave out for all."
	]
	| None = None,
) -> dict:
	"""What a notification One sends says, which slots its text may use, and
	which channels it may go out on. Without a name, every type, briefly.
	Workspace administrators only."""
	from onedesk.one import notify, roles

	if not roles.administers():
		return {"error": "Only a workspace administrator decides what notifications say."}
	declared = notify.declared()
	if not name:
		rows = frappe.get_all(
			"Notification Type",
			filters={"name": ["in", list(declared)]},
			fields=["name", "enabled", *notify.FIELDS],
		)
		return {
			"types": [
				{
					"name": one.name,
					"app": one.one_app,
					"about": one.one_about,
					"sent_to": notify.to(one.name) or None,
					"on": bool(one.enabled),
					"email_allowed": bool(one.one_allow_email),
					"email_for_new_people": bool(one.one_email_default),
					"outside": bool(one.one_outside),
					"words_of": notify.upstream(declared.get(one.name) or {}) or None,
					"mailed_by": one.one_app if (declared.get(one.name) or {}).get("mailed_by") else None,
				}
				for one in rows
			]
		}
	if name not in declared or not frappe.db.exists("Notification Type", name):
		return {"error": f"There is no notification type {name}. Call this without a name for the list."}
	doc = frappe.get_doc("Notification Type", name)
	return {
		"name": doc.name,
		"app": doc.one_app,
		"about": doc.one_about,
		"sent_to": notify.to(doc.name) or None,
		"on": bool(doc.enabled),
		"subject": doc.one_subject,
		"message": doc.one_message,
		"default_subject": doc.one_default_subject,
		"default_message": doc.one_default_message,
		"slots": notify.slots(name),
		"email_allowed": bool(doc.one_allow_email),
		"push_allowed": bool(doc.one_allow_push),
		"outside": bool(doc.one_outside),
		"next": "The text is Jinja and may use only these slots, as {{ slot }}. The subject is one line; the "
		"message may be simple HTML. It is sent as written, in one language: write it in the workspace's.",
		**_whose(declared[name]),
	}


def _whose(one: dict) -> dict:
	"""For a type whose words are another product's: whose, and what can be
	changed instead."""
	from onedesk.one import notify

	if one.get("mailed_by"):
		return {
			"mailed_by": one["app"],
			"next": f"{one['app']} mails this itself; only whether it is sent can be changed, where it has a switch.",
		}
	if notify.upstream(one):
		return {
			"words_of": notify.upstream(one),
			"next": "Its words are the app's own and cannot be rewritten here; its channels can be changed.",
		}
	return {}


def rewrite_notification(
	name: Annotated[str, "The notification type, as notification_type named it."],
	subject: Annotated[str, "The new subject: one line, Jinja, using only the type's slots as {{ slot }}."],
	message: Annotated[
		str, "The new message, or the current one unchanged. Simple HTML and Jinja; may be empty."
	]
	| None = None,
	why: Annotated[str, "In a sentence, what the new text does better."] | None = None,
) -> dict:
	"""Suggest new text for a notification One sends, as a card the
	administrator applies. Read it with notification_type first. Nothing
	changes until they approve it."""
	from onedesk.one import notify
	from onedesk.one_ai import proposals

	if name not in notify.declared():
		return {"error": f"There is no notification type {name}."}
	if notify.upstream(notify.declared()[name]):
		whose = notify.upstream(notify.declared()[name])
		return {"error": f"{name} is in {whose}'s own words; its text cannot be changed here."}
	for text in (subject, message):
		wrong = notify.check(name, text)
		if wrong:
			return {"error": str(wrong)}
	changes = {"one_subject": (subject or "").strip()}
	if message is not None:
		changes["one_message"] = message.strip()
	return {
		"proposal": proposals.propose("Edit", "Notification Type", changes=changes, record=name, why=why),
		"state": "Proposed",
	}


def my_notifications() -> dict:
	"""Every kind of notification the person asking can receive, what it is
	about, and whether it is also mailed and pushed to them, and in how many
	browsers push is on. Their own choices only."""
	from onedesk.one import notify

	user = frappe.session.user
	settings = frappe.db.get_value(
		"Notification Settings", user, ["enabled", "enable_email_notifications"], as_dict=True
	) or frappe._dict(enabled=1, enable_email_notifications=1)

	def chosen(field: str) -> set:
		return set(
			frappe.get_all(
				"Notification Type Preference",
				filters={"parenttype": "Notification Settings", "parentfield": field, "parent": user},
				pluck="notification_type",
			)
		)

	mailed, pushed = chosen(notify.EMAIL_FIELD), chosen(notify.PUSH_FIELD)
	return {
		"notifications_on": bool(settings.enabled),
		"email_on": bool(settings.enable_email_notifications),
		"push_browsers": frappe.db.count("Push Device", {"user": user}),
		"kinds": [
			{
				"name": one["label"],
				"app": one["app"],
				"about": one["about"],
				"by_email": bool(one["always"] or (one["allowed"] and one["name"] in mailed)),
				"by_push": bool(one["push"] and one["name"] in pushed),
				"email_may_change": one["allowed"],
				"push_may_change": one["push"],
			}
			for one in notify.choosable(user)
		],
		"next": "Everything reaches the bell. Push reaches only the browsers counted in push_browsers. "
		"Advise; the person ticks and saves the page themselves.",
	}


def draft_notification(
	name: Annotated[str, "A short name people will know it by, such as Overdue Invoice."],
	watches: Annotated[str, "The record type, by its name, such as Sales Invoice."],
	when: Annotated[str, "New, Save, Submit, Cancel, Days After, Days Before or Value Change."],
	subject: Annotated[str, "A single line. Fields of the record as {{ doc.fieldname }}, and nothing else."],
	message: Annotated[str, "The detail under the bell and in the mail, the same way. May be empty."]
	| None = None,
	roles: Annotated[list[str], "Roles whose people are told."] | None = None,
	person: Annotated[str, "A field of the record naming a person to tell, such as owner."] | None = None,
	assignees: Annotated[bool, "Whether whoever the record is assigned to is told."] = False,
	days: Annotated[int, "For Days After or Days Before: how many days."] | None = None,
	date_field: Annotated[str, "For Days After or Days Before: the date field it counts from."] | None = None,
	value_field: Annotated[str, "For Value Change: the field whose change it watches."] | None = None,
	only_when: Annotated[list[list], "Conditions on the record's fields, each [field, operator, value]."]
	| None = None,
	why: Annotated[str, "In a sentence, what the rule is for."] | None = None,
) -> dict:
	"""Suggest a notification rule for the workspace, as a card the
	administrator applies: when something happens to a kind of record, tell
	somebody, and nothing else. Telling together with anything else (assign
	it, set a field, make a record, wait), or anything asked on the
	automations list, is an automation: suggest_automation. Only people who
	can open the record are ever told. Nothing is made until they approve it.
	Workspace administrators only."""
	from onedesk.one import roles as workspace
	from onedesk.one import rules
	from onedesk.one_ai import proposals

	if not workspace.administers():
		return {"error": "Only a workspace administrator makes notification rules."}
	if when not in rules.EVENTS:
		return {"error": f"When must be one of: {', '.join(rules.EVENTS)}.", "mend": "draft_notification"}
	if not frappe.db.exists("DocType", watches):
		return {"error": f"There is no kind of record called {watches}.", "mend": "draft_notification"}
	for text in (subject, message):
		wrong = rules.check_text(watches, text)
		if wrong:
			return {
				"error": f"{wrong} The fields it may use: {', '.join(rules.readable(watches))}.",
				"mend": "draft_notification",
			}
	recipients = [{"receiver_by_role": one} for one in roles or [] if one]
	if person:
		recipients.append({"receiver_by_document_field": person})
	if not recipients and not assignees:
		return {
			"error": "Say who is told: roles, a person on the record, or its assignees.",
			"mend": "draft_notification",
		}
	changes = {
		"name": (name or "").strip(),
		"enabled": 1,
		"one_rule": 1,
		"channel": "System Notification",
		"document_type": watches,
		"event": when,
		"subject": subject,
		"message": message or "",
		"condition_type": "Filters",
		"filters": json.dumps([[watches, *one] for one in only_when or []]),
		"send_to_all_assignees": 1 if assignees else 0,
		"recipients": recipients,
	}
	if when in ("Days After", "Days Before"):
		changes.update({"date_changed": date_field, "days_in_advance": days or 0})
	if when == "Value Change":
		changes["value_changed"] = value_field
	return {
		"proposal": proposals.propose("Create", "Notification", changes=changes, why=why),
		"state": "Proposed",
		"next": "Tell them it appears in NotificationCenter, under Words and Rules, once they approve it.",
	}




draft_notification.action = "workspace_setup"
