"""Every notification One sends, through one door (docs/NOTIFICATIONS.md).

**The hub is frappe's own.** A notification to somebody in the workspace is a
Notification Log of a Notification Type. That rings their bell, and frappe
emails it to them if they chose email for that type. We add what frappe's type
lacks, as custom fields on Notification Type: the app it belongs to, what it is
about, its text, and which channels it may use.

**A type is declared by the module that sends it**, in its `notifications.py`,
and named in `hooks.py` under `one_notification_types`. `install()` makes each
one a Notification Type after every migrate. From then on the workspace's
administrator owns its text and its channels.

**Two texts, and whose words they are.** A type's default subject and message
are translatable strings with named slots, `_lt("{who} shared {file} with you")`.
They are sent in each reader's own language, because they are ours and are
translated. Once an administrator edits a text, it is theirs: Jinja in their
own words (`{{ who }} shared {{ file }} with you`), sent as they wrote it.
Resetting a text makes it the default again, and translated again.

**Two ways out:**
- `notify()`, for people in the workspace: the bell, and whatever else they
  chose. The bell is always on, because it is the record of what was sent.
- `mail()`, for addresses outside the workspace (a file request, a shared
  link, a sign-in code), or a mail somebody replies to. It is still the type's
  text, so an administrator can still change it.

Nothing else in OneDesk calls `frappe.sendmail` or writes a Notification Log;
`tests/test_notify.py` holds that.

Every value put into a text is escaped first, because the text is HTML in the
bell and in the mail, and a file or person's name is not ours to trust.

**An administrator's Jinja sees its slots and nothing else.** Frappe's own
`render_template` hands a template `frappe.db` and the rest of its safe
globals, which would let whoever edits a text read any record into it. A
workspace administrator is not everybody's HR or accounts, so their text is
rendered in a sandbox with no globals at all, and saving a text that names
anything but its own slots is refused.
"""

import re
from functools import cache

import frappe
from frappe import _, _lt

#: The custom fields on Notification Type (one/custom/notification_type.json).
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

#: Who OneAI writes as, when a notification is its own.
ONEAI = "oneai@one.invalid"


# ------------------------------------------------------------------ the types


def declared() -> dict[str, dict]:
	"""Every type the modules declare, by its untranslated name. A module
	declares a list, each with its `name` as `_lt` so the name is translated
	where it is shown."""
	found = {}
	for path in frappe.get_hooks("one_notification_types") or []:
		for one in frappe.get_attr(path):
			found[raw(one["name"])] = one
	return found


def raw(msgid) -> str:
	"""A declared text untranslated: `_lt` keeps it in `.msg`, and `str()` of it
	would translate it into whatever language the process happens to be in."""
	return getattr(msgid, "msg", None) or str(msgid or "")


def jinja(msgid) -> str:
	"""A default text as an administrator edits it: `{who}` becomes
	`{{ who }}`. Pure."""
	return re.sub(r"\{(\w+)\}", r"{{ \1 }}", raw(msgid))


def slots(name: str) -> list[str]:
	"""What a type's text may name: the slots in its default subject and
	message, in the order they first appear."""
	one = declared().get(name) or {}
	found = re.findall(r"\{(\w+)\}", raw(one.get("subject")) + " " + raw(one.get("message")))
	return list(dict.fromkeys(found))


def install(*_args) -> None:
	"""Each declared type as a Notification Type, after every migrate.

	A new type gets its defaults everywhere. For a type that exists, the
	defaults are refreshed, and the live text moves with them only while the
	administrator has not edited it. A type that defaults to email is seeded into
	everybody's email choices once, when it is first made, as frappe's own
	"Enable email for all users" does.
	"""
	from frappe.desk.doctype.notification_type.notification_type import seed_type_into_settings

	for name, one in declared().items():
		subject, message = jinja(one["subject"]), jinja(one.get("message") or "")
		values = {
			"one_app": one["app"],
			"one_about": raw(one["about"]),
			"one_default_subject": subject,
			"one_default_message": message,
			"one_allow_email": 1 if one.get("email", True) else 0,
			"one_allow_push": 0 if one.get("outside") else (1 if one.get("push", True) else 0),
			"one_email_default": 1 if one.get("email_default") else 0,
			"one_push_default": 1 if one.get("push_default") else 0,
			"one_outside": 1 if one.get("outside") else 0,
		}
		if not frappe.db.exists("Notification Type", name):
			doc = frappe.new_doc("Notification Type")
			doc.type_name = name
			doc.enabled = 1
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
		frappe.db.set_value("Notification Type", name, values, update_modified=False)
	_grant()
	_push_once()


#: Where a person's push choices are kept: beside frappe's own email list on
#: their Notification Settings, in the same child doctype.
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


def _grant() -> None:
	"""A workspace administrator may read and edit Notification Types, which is
	how OneAI's suggested rewrite is applied as them. Written once: a doctype
	with Custom DocPerm rows has been decided by the workspace."""
	from frappe.permissions import add_permission, setup_custom_perms, update_permission_property

	from onedesk.one import roles

	if frappe.db.exists("Custom DocPerm", {"parent": "Notification Type", "role": roles.ADMINISTRATOR}):
		return
	setup_custom_perms("Notification Type")
	add_permission("Notification Type", roles.ADMINISTRATOR, 0)
	for ptype in ("read", "write"):
		update_permission_property("Notification Type", roles.ADMINISTRATOR, 0, ptype, 1, validate=False)


def validate(doc, method=None) -> None:
	"""Notification Type validate: an administrator's text names only its own
	slots and is Jinja that parses, a required type stays on, and a type that
	goes outside the workspace is never pushed."""
	one = declared().get(doc.name)
	if not one:
		return
	if one.get("required") and not doc.enabled:
		frappe.throw(_("{0} cannot be turned off, or nobody could open a shared link.").format(_(doc.name)))
	if one.get("outside"):
		doc.one_allow_push = doc.one_push_default = 0
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
		return _("This does not read as a template: {0}").format(e.message)
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


# ------------------------------------------------------------------ a person's choices

#: Frappe's own kinds, said as a person would. Its "Alert" never mails, and
#: energy points left frappe with gamification, so neither is offered.
FRAPPE_KINDS = {
	"Mention": _lt("Somebody mentioned you in a comment."),
	"Assignment": _lt("Somebody gave you something to do, or it changed."),
	"Share": _lt("Somebody shared a record with you."),
}


def choosable(user: str | None = None) -> list[dict]:
	"""Every kind this person can receive, in the order the page lists them:
	ours by app, frappe's after. A kind declared for some roles is theirs only;
	one that goes outside the workspace is nobody's to choose. For each, whether
	it may be mailed (`allowed`), is always mailed (`always`), and may be
	pushed (`push`)."""
	user = user or frappe.session.user
	held = set(frappe.get_roles(user))
	declared_types = declared()
	rows = frappe.get_all(
		"Notification Type",
		filters={"enabled": 1},
		fields=["name", "one_app", "one_about", "one_allow_email", "one_allow_push", "one_outside"],
		order_by="one_app asc, name asc",
	)
	out = []
	for row in rows:
		one = declared_types.get(row.name)
		if one:
			if row.one_outside or (one.get("roles") and not held & set(one["roles"])):
				continue
			always = bool(one.get("always_mailed"))
			kind = {
				"about": _(row.one_about) if row.one_about else "",
				"allowed": bool(row.one_allow_email) and not always,
				"always": always,
				"push": bool(row.one_allow_push),
			}
		elif row.name in FRAPPE_KINDS:
			kind = {"about": str(FRAPPE_KINDS[row.name]), "allowed": True, "always": False, "push": True}
		else:
			continue
		out.append({"name": row.name, "label": _(row.name), "app": row.one_app or "", **kind})
	return sorted(out, key=lambda one: (not one["app"], one["app"], one["label"]))


# ------------------------------------------------------------------ the text


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
	as its owner wrote it."""
	row, one = _type(name), declared().get(name) or {}
	safe = {key: _escaped(value) for key, value in context.items()}
	# In the subject the names stand out, as frappe's own notifications bold
	# them, so neither our text nor an administrator's has to say <b>.
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
			said.append(frappe.utils.escape_html(own))
		elif not live:
			said.append("")
		elif live == default and msgid:
			said.append(_(raw(msgid), lang=lang).format_map(_Slots(values)))
		else:
			said.append(_sandbox().from_string(live).render(values))
	return said[0], said[1]


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


# ------------------------------------------------------------------ the two ways out


def notify(
	name: str,
	users,
	record: tuple[str, str] | None = None,
	link: str | None = None,
	sender: str | None = None,
	dedupe_on: list[str] | None = None,
	words: tuple[str | None, str | None] | None = None,
	**context,
) -> None:
	"""Tell people in the workspace, through the hub: each in their own language,
	on the bell, and by email or push as they chose. `users` are user names or
	emails; the sender is not told about their own action. `context` fills the
	type's slots."""
	from frappe.desk.doctype.notification_log.notification_log import enqueue_create_notification

	row = _type(name)
	if not row.enabled or row.one_outside:
		return
	people = [users] if isinstance(users, str) else list(filter(None, users or []))
	found = (
		frappe.get_all(
			"User", or_filters={"name": ["in", people], "email": ["in", people]}, fields=["email", "language"]
		)
		if people
		else []
	)
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


def mail(name: str, recipients, lang: str | None = None, words=None, **kwargs) -> None:
	"""Mail an address outside the workspace, or a mail meant to be replied to,
	in the type's text. `kwargs` are the values for the text, and any of
	frappe.sendmail's own arguments, passed on as they are. A `required` type
	(a sign-in code) is sent even when switched off, or nobody could get in."""
	row = _type(name)
	if not row.enabled and not (declared().get(name) or {}).get("required"):
		return
	passed = {key: kwargs.pop(key) for key in list(kwargs) if key in SENDMAIL}
	lang = lang or frappe.db.get_single_value("System Settings", "language")
	subject, message = render(name, kwargs, lang, words)
	frappe.sendmail(
		recipients=[recipients] if isinstance(recipients, str) else list(recipients),
		subject=frappe.utils.strip_html(subject),
		message=message,
		**passed,
	)


#: What `mail()` passes on to frappe.sendmail rather than into the text.
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
