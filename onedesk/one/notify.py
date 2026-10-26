"""Every notification One sends, through one door (onedesk/notifications/README.md).

A notification is frappe's own Notification Log of a Notification Type, with
its type declared in `onedesk/notifications/`. `notify()` is for people in the
workspace, `mail()` for addresses outside it.
"""

import re
from contextlib import contextmanager
from functools import cache

import frappe
from frappe import _, _lt

FIELDS = (
	"one_app",
	"one_about",
	"one_subject",
	"one_message",
	"one_default_subject",
	"one_default_message",
	"one_allow_email",
	"one_allow_push",
	"one_email_default",
	"one_push_default",
	"one_outside",
)

ONEAI = "oneai@one.invalid"


def declared() -> dict[str, dict]:
	"""Every type declared, by its untranslated name, each with its `name` as
	`_lt` so the name is translated where it is shown."""
	found = {}
	for path in frappe.get_hooks("one_notification_types") or []:
		for one in frappe.get_attr(path):
			found[raw(one["name"])] = one
	return found


def raw(msgid) -> str:
	"""A declared text untranslated: `_lt` keeps it in `.msg`, and `str()` of it
	would translate it into whatever language the process happens to be in."""
	return getattr(msgid, "msg", None) or str(msgid or "")


def to(name: str) -> str:
	"""Who a declared type is sent to, in the reader's language: "Their leave
	approver". Said on the workspace's page, never on a person's own, where
	it is always them. Empty for a type not declared."""
	said = (declared().get(name) or {}).get("to")
	return str(said) if said else ""


def jinja(msgid) -> str:
	"""A default text as an administrator edits it: `{who}` becomes
	`{{ who }}`. Pure."""
	return re.sub(r"\{(\w+)\}", r"{{ \1 }}", raw(msgid))


def upstream(one: dict) -> str:
	"""Whose words a type is in when they are not ours: the product that mails
	it, or whose rule or text it carries, by the product's name. Empty for our
	own."""
	return one.get("app", "") if one.get("mailed_by") or one.get("words") else ""


def slots(name: str) -> list[str]:
	"""What a type's text may name: the slots in its default subject and
	message, in the order they first appear."""
	one = declared().get(name) or {}
	found = re.findall(r"\{(\w+)\}", raw(one.get("subject")) + " " + raw(one.get("message")))
	return list(dict.fromkeys(found))


def _forget_gone() -> None:
	"""Drop people's choices for a type that no longer exists. A type deleted
	with force (a patch, a rule taken away) leaves its rows behind, and the
	next type seeded saves every person's settings, which frappe refuses
	while one of them links to nothing."""
	pref = frappe.qb.DocType("Notification Type Preference")
	kind = frappe.qb.DocType("Notification Type")
	gone = (
		frappe.qb.from_(pref)
		.left_join(kind)
		.on(kind.name == pref.notification_type)
		.select(pref.name)
		.where((pref.parenttype == "Notification Settings") & kind.name.isnull())
		.run(pluck=True)
	)
	if gone:
		frappe.db.delete("Notification Type Preference", {"name": ("in", gone)})


def install(*_args) -> None:
	"""Each declared type as a Notification Type, after every migrate.

	A new type gets its defaults everywhere. For a type that exists, the
	defaults are refreshed, and the live text moves with them only while the
	administrator has not edited it. A type that defaults to email is seeded into
	everybody's email choices once, when it is first made, as frappe's own
	"Enable email for all users" does.
	"""
	from frappe.desk.doctype.notification_type.notification_type import seed_type_into_settings

	_forget_gone()
	for name, one in declared().items():
		subject, message = jinja(one.get("subject")), jinja(one.get("message") or "")
		mailed = bool(one.get("mailed_by"))
		values = {
			"one_app": one["app"],
			"one_about": raw(one["about"]),
			"one_default_subject": subject,
			"one_default_message": message,
			"one_allow_email": 0 if mailed else (1 if one.get("email", True) else 0),
			"one_allow_push": 0 if one.get("outside") or mailed else (1 if one.get("push", True) else 0),
			"one_email_default": 1 if one.get("email_default") else 0,
			"one_push_default": 1 if one.get("push_default") else 0,
			"one_outside": 1 if one.get("outside") else 0,
		}
		if not frappe.db.exists("Notification Type", name):
			doc = frappe.new_doc("Notification Type")
			doc.type_name = name
			doc.enabled = _starts(one)
			doc.update(values)
			doc.one_subject, doc.one_message = subject, message
			doc.insert(ignore_permissions=True)
			if values["one_email_default"] and not values["one_outside"]:
				seed_type_into_settings(name)
			if values["one_push_default"] and values["one_allow_push"]:
				seed_push(name)
			continue
		was = frappe.db.get_value(
			"Notification Type",
			name,
			["one_subject", "one_message", "one_default_subject", "one_default_message"],
			as_dict=True,
		)
		if not was.one_subject or was.one_subject == was.one_default_subject:
			values["one_subject"] = subject
		if not was.one_message or was.one_message == was.one_default_message:
			values["one_message"] = message
		if one.get("switch") or one.get("notification"):
			values["enabled"] = _switch(one)
		frappe.db.set_value("Notification Type", name, values, update_modified=False)
	_settle()
	_push_once()


def _starts(one: dict) -> int:
	"""Whether a type starts on: as the app's own switch for it stood, so a
	workspace that had turned birthday mails off is not told birthdays now."""
	if one.get("switch") or one.get("notification"):
		return _switch(one)
	was = one.get("starts_as")
	if was:
		return 1 if frappe.db.get_single_value(*was) else 0
	return 1


def _switch(one: dict) -> int:
	"""Whether the app's own switch for a type is on: a setting, or the
	Enabled box of the frappe Notification that sends it."""
	if one.get("notification"):
		return 1 if frappe.db.get_value("Notification", one["notification"], "enabled") else 0
	return 1 if frappe.db.get_single_value(*one["switch"]) else 0


def _settle() -> None:
	"""The apps' own switches for what we now send, off, after every migrate:
	with one on, the same thing would be sent twice. They are hidden on their
	settings (the modules' custom JSON), because Send This decides now."""
	for one in declared().values():
		for doctype, field in one.get("replaces") or ():
			if frappe.db.get_single_value(doctype, field):
				frappe.db.set_single_value(doctype, field, 0)


def switched(doc, method=None) -> None:
	"""An app's settings saved, or the Notification that sends a type: a type
	whose Send This is that switch follows it."""
	for name, one in declared().items():
		if doc.doctype == "Notification":
			if one.get("notification") != doc.name:
				continue
			field = "enabled"
		else:
			doctype, field = one.get("switch") or (None, None)
			if doctype != doc.doctype:
				continue
		on = 1 if doc.get(field) else 0
		if frappe.db.get_value("Notification Type", name, "enabled") != on:
			frappe.db.set_value("Notification Type", name, "enabled", on)
			frappe.clear_document_cache("Notification Type", name)


PUSH_FIELD = "one_push_notification_types"
EMAIL_FIELD = "email_notification_types"


def seed_push(name: str) -> None:
	"""Put a type in everybody's push choices, as frappe's
	`seed_type_into_settings` does for email. Without a device a person has
	turned push on in, the choice sends nothing."""
	have = set(
		frappe.get_all(
			"Notification Type Preference",
			filters={
				"parenttype": "Notification Settings",
				"parentfield": PUSH_FIELD,
				"notification_type": name,
			},
			pluck="parent",
		)
	)
	for person in frappe.get_all("Notification Settings", pluck="name"):
		if person in have:
			continue
		doc = frappe.get_doc("Notification Settings", person)
		doc.append(PUSH_FIELD, {"notification_type": name})
		doc.save(ignore_permissions=True)


def _push_once() -> None:
	"""When push first arrived, the types already made were seeded once, as a
	new type is when it is made; after that a person's choices are theirs."""
	if frappe.db.get_default("onedesk_push_seeded"):
		return
	for name in frappe.get_all(
		"Notification Type", filters={"one_push_default": 1, "one_allow_push": 1, "enabled": 1}, pluck="name"
	):
		seed_push(name)
	frappe.db.set_default("onedesk_push_seeded", "1")


def validate(doc, method=None) -> None:
	"""Notification Type validate: an administrator's text names only its own
	slots and is Jinja that parses, a required type stays on, and a type that
	goes outside the workspace is never pushed."""
	one = declared().get(doc.name)
	if not one:
		return
	if one.get("required") and not doc.enabled:
		frappe.throw(_("{0} can't be turned off. Shared links depend on it.").format(_(doc.name)))
	if one.get("outside") or one.get("mailed_by"):
		doc.one_allow_push = doc.one_push_default = 0
	if one.get("mailed_by"):
		doc.one_allow_email = 0
		if not (one.get("switch") or one.get("notification")) and not doc.enabled:
			frappe.throw(_("{0} always sends this. It can't be turned off.").format(one["app"]))
	if one.get("switch"):
		doctype, field = one["switch"]
		if (1 if frappe.db.get_single_value(doctype, field) else 0) != (1 if doc.enabled else 0):
			frappe.db.set_single_value(doctype, field, 1 if doc.enabled else 0)
	if one.get("notification") and _switch(one) != (1 if doc.enabled else 0):
		frappe.db.set_value("Notification", one["notification"], "enabled", 1 if doc.enabled else 0)
		frappe.clear_document_cache("Notification", one["notification"])
	if upstream(one):
		doc.one_subject = doc.one_message = ""
	if not doc.one_allow_email:
		doc.one_email_default = 0
	if not doc.one_allow_push:
		doc.one_push_default = 0
	for label, text in ((_("Subject"), doc.one_subject), (_("Message"), doc.one_message)):
		wrong = check(doc.name, text)
		if wrong:
			frappe.throw(_("{0}: {1}").format(label, wrong))


def changed(doc, method=None) -> None:
	"""Notification Type on_update: a channel turned off for a type is off for
	everybody, because frappe mails (and we push to) whoever chose it whatever
	the type says. Turned back on, it goes to everybody again if it is on for
	new people."""
	from frappe.desk.doctype.notification_type.notification_type import seed_type_into_settings

	before = doc.get_doc_before_save()
	if not before or not doc.get("one_app"):
		return
	if before.one_allow_email and not doc.one_allow_email:
		_take_out(doc.name, EMAIL_FIELD)
	elif not before.one_allow_email and doc.one_allow_email and doc.one_email_default:
		seed_type_into_settings(doc.name)
	if before.one_allow_push and not doc.one_allow_push:
		_take_out(doc.name, PUSH_FIELD)
	elif not before.one_allow_push and doc.one_allow_push and doc.one_push_default:
		seed_push(doc.name)


def _take_out(name: str, field: str) -> None:
	"""A type out of everybody's choices for one channel."""
	where = {"parenttype": "Notification Settings", "parentfield": field, "notification_type": name}
	chose = frappe.get_all("Notification Type Preference", filters=where, pluck="parent")
	frappe.db.delete("Notification Type Preference", where)
	for user in chose:
		frappe.clear_document_cache("Notification Settings", user)


def new_person(doc, method=None) -> None:
	"""Notification Settings before_insert: a new person is mailed our types
	only where the administrator said so, and pushed the ones marked for new
	people. Frappe starts everybody on email for every enabled type; for ours,
	"Email for New People" and "Push for New People" decide."""
	ours = frappe.get_all(
		"Notification Type",
		filters={"one_app": ["is", "set"]},
		fields=["name", "enabled", "one_allow_email", "one_email_default", "one_outside"],
	)
	mailed = {
		one.name
		for one in ours
		if one.enabled and one.one_allow_email and one.one_email_default and not one.one_outside
	}
	left_out = {one.name for one in ours} - mailed
	wanted = [
		row for row in doc.get("email_notification_types") or [] if row.notification_type not in left_out
	]
	doc.set("email_notification_types", wanted)
	pushed = frappe.get_all(
		"Notification Type",
		filters={"one_app": ["is", "set"], "enabled": 1, "one_allow_push": 1, "one_push_default": 1},
		pluck="name",
	)
	doc.set(PUSH_FIELD, [{"notification_type": name} for name in pushed])


def check(name: str, text: str | None) -> str | None:
	"""What is wrong with a text, or None: Jinja that does not parse, or a name
	that is not one of the type's slots."""
	from jinja2 import TemplateSyntaxError, meta

	if not text:
		return None
	try:
		named = meta.find_undeclared_variables(_sandbox().parse(text))
	except TemplateSyntaxError as e:
		return _("Template error: {0}").format(e.message)
	unknown = sorted(named - set(slots(name)))
	if unknown:
		have = ", ".join(f"{{{{ {one} }}}}" for one in slots(name)) or _("nothing")
		return _("{0} is not something this notification knows. It can use {1}.").format(
			", ".join(unknown), have
		)
	return None


@cache
def _sandbox():
	"""Jinja with nothing in it but what it is handed."""
	from jinja2.sandbox import SandboxedEnvironment

	return SandboxedEnvironment(autoescape=False)


class _Slots(dict):
	"""A translation that dropped a slot, or a sender that did not fill one,
	says nothing there rather than failing the notification."""

	def __missing__(self, key):
		return ""


FRAPPE_KINDS = {
	"Mention": _lt("When someone mentions you in a comment."),
	"Assignment": _lt("When someone assigns you something, or it changes."),
	"Share": _lt("When someone shares a record with you."),
}


def choosable(user: str | None = None) -> list[dict]:
	"""Every kind this person can receive, in the order the page lists them: ours
	by app, frappe's after, each with whether it may be mailed (`allowed`), is
	always mailed (`always`), and may be pushed (`push`)."""
	user = user or frappe.session.user
	held = set(frappe.get_roles(user))
	declared_types = declared()
	twins: dict[str, list] = {}
	for name, one in declared_types.items():
		if one.get("follows"):
			twins.setdefault(one["follows"], []).append(name)
	rows = frappe.get_all(
		"Notification Type",
		filters={"enabled": 1},
		fields=[
			"name",
			"one_app",
			"one_about",
			"one_allow_email",
			"one_allow_push",
			"one_outside",
			"one_rule",
		],
		order_by="one_app asc, name asc",
	)
	out = []
	for row in rows:
		one = declared_types.get(row.name)
		if one:
			if (
				row.one_outside
				or one.get("mailed_by")
				or one.get("follows")
				or (one.get("roles") and not held & set(one["roles"]))
			):
				continue
			always = bool(one.get("always_mailed"))
			kind = {
				"about": _(row.one_about) if row.one_about else "",
				"allowed": bool(row.one_allow_email) and not always,
				"always": always,
				"push": bool(row.one_allow_push),
				"oneai": bool(one.get("oneai")),
				"twins": twins.get(row.name, []),
			}
		elif row.one_rule:
			said = row.one_about or ""
			kind = {
				"about": said + "." if said and not said.endswith(".") else said,
				"allowed": bool(row.one_allow_email),
				"always": False,
				"push": bool(row.one_allow_push),
			}
		elif row.name in FRAPPE_KINDS:
			kind = {"about": str(FRAPPE_KINDS[row.name]), "allowed": True, "always": False, "push": True}
		else:
			continue
		out.append({"name": row.name, "label": _(row.name), "app": row.one_app or "", **kind})
	return sorted(out, key=lambda one: (not one["app"], one["app"], one["label"]))


def _type(name: str) -> dict:
	row = frappe.get_cached_value("Notification Type", name, ["enabled", *FIELDS], as_dict=True)
	if not row:
		frappe.throw(_("There is no notification type {0}.").format(name))
	return row


def render(name: str, context: dict, lang: str | None = None, words=None) -> tuple[str, str]:
	"""A type's subject and message for one reader, in their language when the
	text is still ours, as the administrator wrote it when it is theirs.

	`words` is a record's own subject and message, where the record has them
	(a project's own question): each is used over the type's text when given,
	as its owner wrote it. Words that are `Markup` are a standard rule's,
	rendered as frappe renders them, and go as they are."""
	from markupsafe import Markup

	row, one = _type(name), declared().get(name) or {}
	safe = {key: _escaped(_said(value, lang)) for key, value in context.items()}
	strong = {key: f"<b>{value}</b>" if _named(value) else value for key, value in safe.items()}
	said = []
	for values, own, live, default, msgid in zip(
		(strong, safe),
		words or (None, None),
		(row.one_subject, row.one_message),
		(row.one_default_subject, row.one_default_message),
		(one.get("subject"), one.get("message")),
		strict=True,
	):
		if own:
			said.append(own if isinstance(own, Markup) else frappe.utils.escape_html(own))
		elif not live:
			said.append("")
		elif live == default and msgid:
			said.append(_(raw(msgid), lang=lang).format_map(_Slots(values)))
		else:
			said.append(_sandbox().from_string(live).render(values))
	return said[0], said[1]


def _said(value, lang):
	"""A value that is `_lt`, a status or a doctype's name, in the reader's
	language rather than the process's."""
	msgid = getattr(value, "msg", None)
	return _(msgid, lang=lang) if msgid else value


def _named(value) -> bool:
	"""A name, a title: text the sender filled in, not a number and not HTML
	it built itself."""
	from markupsafe import Markup

	return isinstance(value, str) and not isinstance(value, Markup) and bool(value)


def _escaped(value):
	"""A value as it may go into HTML: text escaped, numbers as they are. A
	value that is already HTML, built by the sender, is passed as `Markup`."""
	from markupsafe import Markup

	if isinstance(value, Markup):
		return value
	if isinstance(value, (int, float)):
		return value
	return frappe.utils.escape_html(str(value if value is not None else ""))


def notify(
	name: str,
	users,
	record: tuple[str, str] | None = None,
	link: str | None = None,
	sender: str | None = None,
	dedupe_on: list[str] | None = None,
	words: tuple[str | None, str | None] | None = None,
	mailed: bool = True,
	**context,
) -> None:
	"""Tell people in the workspace, through the hub: each in their own language,
	on the bell, and by email or push as they chose. `users` are user names or
	emails; the sender is not told about their own action. `context` fills the
	type's slots. An `always_mailed` type is mailed here too, unless the
	sender mails it its own way (`mailed=False`)."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	row = _type(name)
	if not row.enabled or row.one_outside:
		return
	if dedupe_on and "type" not in dedupe_on:
		dedupe_on = ["type", *dedupe_on]
	people = [users] if isinstance(users, str) else list(filter(None, users or []))
	found = (
		frappe.get_all(
			"User", or_filters={"name": ["in", people], "email": ["in", people]}, fields=["email", "language"]
		)
		if people
		else []
	)
	always = mailed and bool((declared().get(name) or {}).get("always_mailed"))
	fallback = frappe.db.get_single_value("System Settings", "language") or "en"
	by_language: dict[str, list[str]] = {}
	for person in found:
		if person.email:
			by_language.setdefault(person.language or fallback, []).append(person.email)
	for lang, emails in by_language.items():
		subject, message = render(name, context, lang, words)
		doc = {
			"type": name,
			"subject": subject,
			"email_content": message or None,
			"from_user": sender or frappe.session.user,
			"link": link,
		}
		if record:
			doc["document_type"], doc["document_name"] = record
		enqueue_create_notification(emails, doc, dedupe_on=dedupe_on)
		if always:
			for email in emails:
				with unsent():
					_send(email, lang, name, subject, message, link, record, always=True)


def mail(name: str, recipients, lang: str | None = None, words=None, **kwargs) -> None:
	"""Mail an address outside the workspace, or a mail meant to be replied to,
	in the type's text. `kwargs` are the values for the text, and any of
	frappe.sendmail's own arguments, passed on as they are. A `required` type
	(a sign-in code) is sent even when switched off, or nobody could get in."""
	row = _type(name)
	if not row.enabled and not (declared().get(name) or {}).get("required"):
		return
	passed = {key: kwargs.pop(key) for key in list(kwargs) if key in SENDMAIL}
	ones = bool((declared().get(name) or {}).get("from_one"))
	if not ones and not passed.get("reply_to"):
		passed["reply_to"] = replies_to()
	lang = lang or frappe.db.get_single_value("System Settings", "language")
	subject, message = render(name, kwargs, lang, words)
	link = next((kwargs[key] for key in ("link", "url", "account") if kwargs.get(key)), None)
	frappe.sendmail(
		recipients=[recipients] if isinstance(recipients, str) else list(recipients),
		subject=plain(subject),
		message=compose(
			subject,
			message,
			link,
			button(name, kwargs, lang) if link else None,
			lang=lang,
			ones=ones,
		),
		with_container=True,
		**passed,
	)


def replies_to() -> str | None:
	"""Where an answer to the workspace's own mail goes: its Default Incoming
	(one_mail/holders.py), since the mail itself comes from One's sender."""
	from onedesk.one_mail import holders

	account = holders.workspace()
	return frappe.db.get_value("Email Account", account, "email_id") if account else None


SENDMAIL = frozenset(
	{
		"now",
		"delayed",
		"reference_doctype",
		"reference_name",
		"reply_to",
		"attachments",
		"cc",
		"bcc",
		"sender",
	}
)


@contextmanager
def unsent():
	"""A mail that could not go, because the workspace has no outgoing account
	yet, logged rather than raised: what it was about still happened.

	frappe throws with a message, and catching the throw leaves the message
	behind, so whoever pressed the button was told to set up an email account
	in a red dialog over a check-in that had worked.
	"""
	said = len(frappe.local.message_log)
	try:
		yield
	except frappe.OutgoingEmailError:
		del frappe.local.message_log[said:]
		frappe.log_error(title=_("Failed to send notification email"))


def compose(
	subject: str,
	message: str,
	link: str | None = None,
	button: str | None = None,
	reason: str = "",
	lang: str | None = None,
	ones: bool = False,
) -> str:
	"""A mail's body as One draws it (templates/emails/one_mail.html): what
	happened as its heading, the message, one button, and why it came,
	right to left for a reader of Arabic, and marked when One sends it about
	itself. frappe frames it
	(templates/emails/standard.html, ours)."""
	from markupsafe import Markup

	return frappe.get_template("templates/emails/one_mail.html").render(
		{
			"subject": Markup(subject or ""),
			"message": Markup(message or ""),
			"link": frappe.utils.get_url(link) if link else None,
			"button": button,
			"reason": Markup(reason),
			"rtl": (lang or "").split("-")[0] in RTL,
			"ones": ones,
		},
	)


RTL = frozenset({"ar", "fa", "he", "ku", "ps", "ur"})


def button(name: str, context: dict, lang: str | None) -> str | None:
	"""The type's own words for its mail's button, in the reader's language,
	with any slot filled (`{button}` for a portal link's)."""
	said = (declared().get(name) or {}).get("button")
	if not said:
		return None
	return _(raw(said), lang=lang).format_map(
		_Slots({key: _said(value, lang) for key, value in context.items()})
	)


def plain(subject: str | None) -> str:
	"""A subject as a mail's subject line: no tags, and `&amp;` as `&`."""
	import html

	return html.unescape(frappe.utils.strip_html(subject or ""))


def one_mail_brand(ones: bool = False) -> dict:
	"""Above every framed mail, and the colour of its button: the workspace's
	name, its company's logo when a mail can show it (an SVG is shown by
	almost no client) and its company's Brand Colour. A mail One sends about
	itself (`from_one`), and every mail from the admin site, wears One's."""
	from onedesk.one.privacy_public import workspace
	from onedesk.one_admin.site import is_admin

	if ones or is_admin():
		return {"name": "One", "logo": frappe.utils.get_url(ONE_MARK), "colour": INK, "ink": "#ffffff"}
	company = frappe.defaults.get_global_default("company")
	logo, colour = (
		frappe.db.get_value("Company", company, ["company_logo", "one_brand_colour"])
		if company
		else (None, None)
	)
	shown = logo and not logo.lower().split("?")[0].endswith(".svg")
	colour = colour if re.fullmatch(r"#[0-9a-fA-F]{6}", colour or "") else INK
	return {
		"name": workspace(),
		"logo": frappe.utils.get_url(logo) if shown else None,
		"colour": colour,
		"ink": ink(colour),
	}


ONE_MARK = "/assets/onedesk/images/one-mail.png"
INK = "#171717"


def ink(colour: str) -> str:
	"""White on a dark colour, ink on a light one: whichever reads better
	against it, by WCAG's contrast. Pure."""

	def lum(hex_):
		c = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
		c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
		return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]

	behind = lum(colour)
	return "#ffffff" if 1.05 / (behind + 0.05) >= (behind + 0.05) / (lum(INK) + 0.05) else INK


def mail_log(log) -> None:
	"""A notification mailed to its person, as frappe's send_notification_email
	does, but drawn as One draws a mail: its own heading rather than "New
	Notification", a button named for what it opens, and which notification
	it is with where to change that. An `always_mailed` type was mailed when
	it was sent."""
	if (declared().get(log.type) or {}).get("always_mailed"):
		return
	user = frappe.db.get_value("User", log.for_user, ["email", "language"], as_dict=True)
	if not user or not user.email:
		return
	record = (log.document_type, log.document_name) if log.document_type and log.document_name else None
	_send(user.email, user.language, log.type, log.subject, log.email_content, log.link, record)


def _send(email, lang, kind, subject, message, link=None, record=None, always=False) -> None:
	from frappe.utils import get_url_to_form

	lang = lang or frappe.db.get_single_value("System Settings", "language")
	label = _("Open", lang=lang, context="Go to it")
	if record:
		link = link or get_url_to_form(*record)
		label = _("Open {0}", lang=lang).format(_(record[0], lang=lang))
	label = button(kind, {}, lang) or label
	one = declared().get(kind) or {}
	said = f"<b>{frappe.utils.escape_html(_(kind, lang=lang))}</b>" if kind else ""
	if one.get("about"):
		said += f" · {frappe.utils.escape_html(_(raw(one['about']), lang=lang))}"
	if always:
		reason = f"{said}<br>{_('Mailed to everybody it concerns, whatever they chose.', lang=lang)}"
	else:
		change = frappe.utils.get_url("/desk/one?center=notifications")
		reason = f'{said}<br><a href="{change}">{_("Change what you get by mail", lang=lang)}</a>'
	frappe.sendmail(
		recipients=email,
		subject=plain(subject),
		message=compose(subject, message, link, label, reason, lang, bool(one.get("from_one"))),
		with_container=True,
		now=frappe.in_test,
	)


from frappe.desk.doctype.notification_log.notification_log import (
	NotificationLog as _NotificationLog,
)


class NotificationLog(_NotificationLog):
	"""frappe's Notification Log, mailed through `mail_log` (hooks.py
	override_doctype_class)."""

	def after_insert(self):
		from frappe.desk.doctype.notification_log.notification_log import set_notifications_as_unseen
		from frappe.desk.doctype.notification_settings.notification_settings import (
			is_email_notifications_enabled_for_type,
		)

		frappe.publish_realtime("notification", after_commit=True, user=self.for_user)
		set_notifications_as_unseen(self.for_user)
		if is_email_notifications_enabled_for_type(self.for_user, self.type):
			with unsent():
				mail_log(self)
