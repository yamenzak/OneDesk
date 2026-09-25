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
"""

import re

import frappe
from frappe import _

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
	said = []
	for own, live, default, msgid in zip(
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
			said.append(_(raw(msgid), lang=lang).format(**safe))
		else:
			said.append(frappe.render_template(live, safe))
	return said[0], said[1]


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
