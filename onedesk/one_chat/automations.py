"""A channel's automations (AutomationCenter, blocks.py): kept by its
members who may make channels, read by all its members, and run on each
message a person posts in it or a visitor posts in one of its rooms, in the
background once the message is saved. Nothing an automation or an agent
posts starts one, so none answers itself. What each does is OneChat's own:
a message posted as whoever made it, a person told, a record made, a room
forwarded, an agent's answer."""

import frappe
from frappe import _
from frappe.utils import strip_html_tags

from onedesk.one_chat import agents, channels, messages

POSTED = "one_chat.posted"

FIELDS = ("enabled", "priority", "title", "steps")

CREATES = ("Task", "Issue", "Lead")

SUBJECT = 140

MOST_TURNS = 20

MOST_SAID = 2000

ANSWERS_A_CONVERSATION = 20
"""How many times an automation's agent answers in one conversation a day."""

A_DAY = 24 * 3600


def manages(channel: str, user: str | None = None) -> bool:
	"""Whether somebody changes a channel's automations: a member of it who
	may make channels."""
	from onedesk.one import rights

	user = user or frappe.session.user
	if user == "Administrator":
		return True
	if frappe.db.get_value("Chat Channel", channel, "kind") != channels.CHANNEL:
		return False
	return channels.reads(channels.members_of(channel), user) and rights.held("Chat Channel", "chat_channels", user)


def _must(channel: str) -> None:
	if not manages(channel):
		frappe.throw(_("Your role doesn't allow changing this."), frappe.PermissionError)


def scopes() -> list[dict]:
	"""The channels whose automations the reader changes, by title."""
	me = frappe.session.user
	inside = frappe.get_all("Chat Channel Member", filters={"parenttype": "Chat Channel", "user": me}, pluck="parent")
	if not inside:
		return []
	rows = frappe.get_all(
		"Chat Channel",
		filters={"name": ["in", inside], "kind": channels.CHANNEL},
		fields=["name", "title", "private"],
		order_by="title asc",
	)
	return [{"scope": one.name, "label": one.title, "manages": 1, "asks": 0} for one in rows if manages(one.name, me)]


def offers(channel: str) -> dict:
	"""What a channel's automations may name: its people, the other channels
	the reader is in, and whether OneAI may answer; `names` says each in
	words."""
	from onedesk.one import apps

	doc = channels.opened(channel)
	people = [one.user for one in doc.members if one.user and not one.agent]
	names = {one: frappe.utils.get_fullname(one) for one in people}
	inside = frappe.get_all("Chat Channel Member", filters={"parenttype": "Chat Channel", "user": frappe.session.user}, pluck="parent")
	others = frappe.get_all(
		"Chat Channel",
		filters={"name": ["in", inside or [""]], "kind": channels.CHANNEL},
		fields=["name", "title"],
		order_by="title asc",
	)
	others = [one for one in others if one.name != doc.name]
	names.update({one.name: one.title for one in others})
	return {
		"where": doc.title,
		"people": [{"value": one, "label": names[one]} for one in people],
		"channels": [{"value": one.name, "label": one.title} for one in others],
		"creates": [{"value": one, "label": _(one)} for one in CREATES],
		"names": names,
		"ai": int(apps.ai_on()),
		"reads": 0,
	}



def listed(channel: str) -> dict:
	"""A channel's automations in the order they run, for AutomationCenter."""
	from onedesk.one.automation import engine

	channels.opened(channel)
	rows = frappe.get_all(
		"Automation",
		filters={"trigger": POSTED, "scope": channel},
		fields=["name", "requested_by", *FIELDS],
		order_by="priority asc, creation asc",
	)
	offered = offers(channel)
	for one in rows:
		one["steps"] = engine.steps_of(one)
		one["when"], one["then"] = engine.summary(POSTED, one["steps"], offered)
		one["needs_ai"] = 0
		one["requested_by_name"] = None
	return {"may": True, "manages": int(manages(channel)), "asks": 0, "rules": rows, "reads": 1}


def _held(name: str):
	doc = frappe.get_doc("Automation", name)
	if doc.trigger != POSTED:
		frappe.throw(_("That automation is not in this channel."))
	return doc


def save(channel: str, values: dict | str, name: str | None = None) -> str:
	"""Make or change one of a channel's automations."""
	_must(channel)
	values = frappe.parse_json(values) if isinstance(values, str) else values
	doc = _held(name) if name else frappe.new_doc("Automation")
	if name and doc.scope != channel:
		frappe.throw(_("That automation is not in this channel."))
	doc.update({key: values.get(key) for key in FIELDS if key in values})
	if isinstance(doc.steps, list):
		doc.steps = frappe.as_json(doc.steps, indent=None)
	doc.trigger, doc.scope_type, doc.scope = POSTED, "Chat Channel", channel
	doc.flags.ignore_permissions = True
	doc.save() if name else doc.insert()
	return doc.name


def enable(name: str, enabled: int = 1) -> None:
	doc = _held(name)
	_must(doc.scope)
	doc.enabled = int(enabled)
	doc.flags.ignore_permissions = True
	doc.save()


def delete(name: str) -> None:
	doc = _held(name)
	_must(doc.scope)
	frappe.delete_doc("Automation", name, ignore_permissions=True)


def decide(name: str, approve: int = 1) -> None:
	"""Nobody asks for a channel's automation: whoever may change it does."""
	frappe.throw(_("Nobody asked for this automation."))


def allowed(doc, ptype=None, user=None) -> bool:
	"""A channel's automations are read by its members and changed by
	whoever `manages` it."""
	user = user or frappe.session.user
	if user == "Administrator" or not doc.scope:
		return True
	if ptype in (None, "read", "select", "print", "report"):
		return channels.reads(channels.members_of(doc.scope), user)
	return manages(doc.scope, user)


def query(user=None) -> str:
	user = user or frappe.session.user
	if user == "Administrator":
		return ""
	return (
		"`tabAutomation`.scope in (select parent from `tabChat Channel Member` "
		f"where parenttype = 'Chat Channel' and user = {frappe.db.escape(user)})"
	)


def validate(doc, steps: list) -> None:
	"""What a channel's automation must be beyond its steps: in a channel,
	telling only its people, posting or forwarding only where whoever made it
	is a member,
	and an agent only one they may talk to while OneAI is on."""
	from onedesk.one import apps, registry
	from onedesk.one.automation import flow

	if frappe.db.get_value("Chat Channel", doc.scope, "kind") != channels.CHANNEL:
		frappe.throw(_("Automations run in a channel only."))
	owner = doc.owner or frappe.session.user
	inside = set(channels.members_of(doc.scope))
	for one in flow.actions_in(steps):
		kind = one.get("type")
		if kind == "chat_notify" and one.get("user") not in inside:
			frappe.throw(_("{0} isn't in this channel.").format(frappe.utils.get_fullname(one.get("user"))))
		if kind in ("chat_share", "chat_forward") and not channels.reads(channels.members_of(one.get("channel")), owner):
			frappe.throw(_("You aren't a member of this conversation."), frappe.PermissionError)
		if kind == "chat_answer":
			if not apps.ai_on():
				frappe.throw(_("{0} is turned off for this workspace.").format(registry.name("one_ai")))
			if not agents.reaches(one.get("agent"), owner):
				frappe.throw(_("Your role doesn't allow talking to {0}.").format(agents.name_of(one.get("agent"))), frappe.PermissionError)



def scope_of(channel) -> str | None:
	"""The channel whose automations run on a message: its own, or for a
	room the channel that answers it."""
	if channel.kind == channels.CHANNEL:
		return channel.name
	if channel.kind == channels.ROOM:
		return channel.desk
	return None


def fire(message, channel) -> None:
	"""A person's or a visitor's message starts its channel's automations,
	after it is saved and in the background, so sending never waits."""
	scope = scope_of(channel)
	if not scope or message.automation or message.agent:
		return
	if not frappe.db.exists("Automation", {"trigger": POSTED, "scope": scope, "enabled": 1}):
		return
	frappe.enqueue(f"{__name__}.run", queue="short", enqueue_after_commit=True, message=message.name, scope=scope)


def run(message: str, scope: str) -> list[str]:
	from onedesk.one.automation import engine

	if not frappe.db.exists("Chat Message", message):
		return []
	return engine.run(POSTED, scope, message, facts_of(message))


def facts_of(message: str) -> dict:
	"""What a channel automation's conditions are tested against: the
	message's words and who wrote it, whether it is in a thread or carries a
	file, whether a visitor wrote it, opening a room, and from which page of
	the website, and whether it came after hours or on a holiday."""
	from onedesk.one.automation import hours

	held, channel = _said(message)
	visitor = held.sender == channels.VISITOR
	return {
		"text": held.text or "",
		"from": _from(held, channel),
		"thread": bool(held.thread),
		"file": bool(frappe.db.exists("Chat File", {"parent": message, "parenttype": "Chat Message"})),
		"visitor": visitor,
		"opens": visitor and channel.kind == channels.ROOM and not _earlier(channel.name, held),
		"page": (channel.page or "") if channel.kind == channels.ROOM else "",
		"after_hours": hours.after_hours(),
		"holiday": hours.holiday_today(),
	}


def _from(held, channel) -> str:
	if held.sender == channels.VISITOR:
		return f"{channel.visitor_name or ''} {channel.visitor_email or ''}"
	return f"{frappe.utils.get_fullname(held.sender) if held.sender else ''} {held.sender or ''}"


def _earlier(channel: str, held) -> bool:
	return bool(frappe.db.exists("Chat Message", {"channel": channel, "sender": channels.VISITOR, "name": ["!=", held.name], "creation": ["<=", held.creation]}))


def _said(message: str):
	held = frappe.db.get_value("Chat Message", message, ["name", "channel", "thread", "sender", "text", "creation"], as_dict=True)
	return held, frappe.get_doc("Chat Channel", held.channel)


def _still_in(channel, user: str) -> bool:
	return channels.reads(channels.readers(channel), user)


def _who(held, channel) -> str:
	return channel.visitor_name if held.sender == channels.VISITOR else frappe.utils.get_fullname(held.sender)


def reply(automation, message: str, step: dict) -> None:
	"""The automation's words posted in the conversation, or in the message's
	thread, as whoever made it, while they still read it. In a room the
	conversation is what the visitor reads, and a thread is the team's."""
	held, channel = _said(message)
	if not _still_in(channel, automation.owner):
		return
	text = (step.get("text") or "").replace("{sender_name}", (_who(held, channel) or "").split(" ")[0])
	thread = held.thread or (held.name if step.get("thread") else None)
	messages.post(channel, text, thread=thread, sender=automation.owner, automation=automation.name)


def share(automation, message: str, step: dict) -> None:
	"""The message posted in another channel, with who said it and where,
	while whoever made the automation reads both."""
	held, channel = _said(message)
	target = frappe.get_doc("Chat Channel", step["channel"])
	if not (_still_in(channel, automation.owner) and _still_in(target, automation.owner)):
		return
	said = _("{0} in {1}").format(_who(held, channel), channel.title)
	quoted = "\n".join(f"> {line}" for line in (held.text or "").splitlines()) or "> …"
	messages.post(target, f"{said}\n\n{quoted}", sender=automation.owner, automation=automation.name)


def forward(automation, message: str, step: dict) -> None:
	"""A room handed to another channel, whose people join it, while whoever
	made the automation reads both."""
	held, channel = _said(message)
	if channel.kind != channels.ROOM or channel.desk == step.get("channel"):
		return
	target = frappe.get_doc("Chat Channel", step["channel"])
	if not (_still_in(channel, automation.owner) and _still_in(target, automation.owner)):
		return
	was = frappe.session.user
	frappe.set_user(automation.owner)
	try:
		channels.forward(channel.name, target.name)
	finally:
		frappe.set_user(was)


def notify(automation, message: str, step: dict) -> None:
	"""Somebody who reads the conversation told on the bell, by email or push
	as they chose."""
	from onedesk.one import notify as hub

	held, channel = _said(message)
	if not _still_in(channel, step["user"]):
		return
	hub.notify(
		"Chat Automation Notice",
		step["user"],
		link=f"/app/onechat?channel={channel.name}" + (f"&thread={held.thread}" if held.thread else ""),
		sender="Administrator",
		who=_who(held, channel),
		conversation=channel.title,
		text=messages.short(held.text),
		automation=automation.title or automation.name,
	)


def create(automation, message: str, step: dict) -> str | None:
	"""A task, an issue or a lead made from the message, owned by whoever
	made the automation and said in the message's thread with a link to it.
	A lead is a visitor's, never made twice for one address; in a room the
	record made is the room's record, if it has none."""
	kind = step.get("doctype")
	if kind not in CREATES:
		return None
	held, channel = _said(message)
	values = made(kind, strip_html_tags(held.text or "").strip(), held.sender, channel)
	if values is None:
		return None
	doc = frappe.get_doc({"doctype": kind, **values})
	doc.flags.ignore_permissions = True
	doc.flags.ignore_mandatory = True
	doc.insert()
	frappe.db.set_value(kind, doc.name, "owner", automation.owner, update_modified=False)
	if channel.kind == channels.ROOM and not channel.reference_name:
		frappe.db.set_value("Chat Channel", channel.name, {"reference_doctype": kind, "reference_name": doc.name}, update_modified=False)
	link = f"[{doc.name}]({frappe.utils.get_url_to_form(kind, doc.name)})"
	messages.post(channel, _("{0} {1} created.").format(_(kind), link), thread=held.thread or held.name, sender=automation.owner, automation=automation.name)
	return doc.name


def made(kind: str, text: str, sender: str, channel) -> dict | None:
	"""The values of the record a message makes, or None where it makes none."""
	subject = (text.splitlines() or [""])[0][:SUBJECT] or _("(no subject)")
	visitor = sender == channels.VISITOR
	email = (channel.visitor_email or "").lower() if visitor else ""
	if kind == "Lead":
		if not email or frappe.db.exists("Lead", {"email_id": email}) or frappe.db.exists("Contact Email", {"email_id": email}):
			return None
		return {"lead_name": channel.visitor_name or email.split("@")[0], "email_id": email}
	values = {"subject": subject, "description": text}
	if kind == "Issue":
		values["raised_by"] = email if visitor else sender
	return values


def answer(automation, message: str, step: dict) -> None:
	"""An agent answers the message, after the run is saved, from the
	conversation and the automation's instruction alone."""
	frappe.enqueue(
		f"{__name__}.answered",
		queue="long",
		enqueue_after_commit=True,
		message=message,
		agent=step["agent"],
		instruction=step.get("instruction") or "",
		owner=automation.owner,
		automation=automation.name,
	)


def answered(message: str, agent: str, instruction: str, owner: str, automation: str) -> str | None:
	"""The agent's answer, as whoever made the automation asked it: with no
	tools, so it says only what the instruction and the conversation say,
	never what a record holds. In a channel it answers in the message's
	thread; in a room, to the visitor, from what the visitor reads, until
	somebody of the team answers there. Nothing while OneAI or the agent is
	off, once the owner may no longer talk to it, or past its answers for
	the day."""
	from onedesk.one import apps
	from onedesk.one_admin import faults
	from onedesk.one_ai.agents import talk, workspace

	if not apps.ai_on() or workspace.refusal(agent) or not frappe.db.exists("Chat Message", message):
		return None
	held, channel = _said(message)
	room = channel.kind == channels.ROOM
	thread = held.thread if room else held.thread or held.name
	if room and (held.thread or taken_over(channel.name)):
		return None
	if not _counted(channel.name, automation):
		return None
	was = frappe.session.user
	frappe.set_user(owner)
	try:
		if not agents.reaches(agent) or not _still_in(channel, owner):
			return None
		turns = told(talk.who(agent), instruction, _conversation(channel, thread), agents.user_of(agent))
		try:
			out = talk.ask(agent, "chat", held.text or "", turns, reference=channel.name, tools=((), ()), most=1)
		except (faults.Again, faults.Refused, frappe.PermissionError):
			return None
		said = last_words(out)
		if not said:
			return None
		return messages.post(channel, said, thread=thread, sender=agents.user_of(agent) or "", agent=agent, automation=automation).name
	finally:
		frappe.set_user(was)


def taken_over(room: str) -> bool:
	"""Whether somebody of the team has answered the visitor in a room."""
	return bool(
		frappe.db.exists(
			"Chat Message",
			{"channel": room, "thread": ("is", "not set"), "sender": ["not in", [channels.VISITOR, ""]], "agent": ("is", "not set"), "automation": ("is", "not set")},
		)
	)


def _counted(channel: str, automation: str) -> bool:
	key = frappe.cache.make_key(f"one_chat_answers:{automation}:{channel}")
	frappe.cache.set(key, 0, ex=A_DAY, nx=True)
	return frappe.cache.incrby(key, 1) <= ANSWERS_A_CONVERSATION


def _conversation(channel, thread: str | None) -> list[dict]:
	"""What the agent answers from, oldest first, words only: a thread's
	first message and every reply, or a room's conversation without its
	threads, which are the team's."""
	fields = ["sender", "agent", "text"]
	rows = frappe.get_all(
		"Chat Message",
		filters={"channel": channel.name, "thread": thread or ("is", "not set")},
		fields=fields,
		order_by="creation desc",
		limit=MOST_TURNS - 1,
	)
	rows = list(reversed(rows))
	if thread:
		rows.insert(0, frappe.db.get_value("Chat Message", thread, fields, as_dict=True))
	visitor = channel.visitor_name if channel.kind == channels.ROOM else ""
	return [{**one, "visitor": visitor} if one.get("sender") == channels.VISITOR else one for one in rows]


def told(who: str, instruction: str, said: list, user: str | None) -> list[dict]:
	"""The turns the agent is asked: who it is and the instruction, then the
	conversation, its own words as its own and everybody else's as words
	with their name. Pure but for names."""
	turns = [
		{
			"role": "user",
			"text": f"{who} Answer the last message in this conversation in a few sentences, from these instructions "
			f"and the conversation alone; you cannot look anything up. Instructions: {instruction}",
			"calls": [],
			"context": True,
		}
	]
	for one in said:
		text = str(one.get("text") or "").strip()[:MOST_SAID]
		if not text:
			continue
		if user and one.get("sender") == user:
			turns.append({"role": "model", "text": text, "calls": []})
		else:
			turns.append({"role": "user", "text": f"{_name_of(one)}: {text}", "calls": []})
	return turns


def _name_of(one) -> str:
	if one.get("visitor"):
		return one["visitor"]
	if one.get("agent"):
		return agents.name_of(one["agent"])
	return frappe.utils.get_fullname(one.get("sender")) if one.get("sender") else ""


def last_words(out: dict) -> str:
	"""What the agent said last. Pure."""
	said = [one for one in out.get("turns") or [] if one.get("role") == "model"]
	return (said[-1].get("text") or "").strip() if said else ""
