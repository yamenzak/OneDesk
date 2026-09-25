"""Rules: notifications a workspace builds for itself (docs/NOTIFICATIONS.md,
stage 5).

A rule is frappe's own Notification: what it watches, when it fires, who is
told, and what it says. It goes to the bell with a notification type of its
own, so everything else follows from the hub: it is mailed or pushed to each
person as they chose, and an administrator decides its channels as for any
other type.

**Frappe trusts whoever writes a Notification**, because only its own roles
may: the text is rendered with frappe's template globals, a condition or a
recipient's condition is Python, a rule can set a field on the record after it
sends, attach its print, and mail any address. A workspace administrator is
not frappe's administrator, so a rule saved by anybody without frappe's own
Notification roles is a **workspace rule** (`one_rule`), held to this:

- it watches a kind of record they may read themselves, on one of `EVENTS`;
- its condition is filters, never Python;
- its text names only fields of that record, `{{ doc.field }}`, and nothing
  else (`check_text`);
- it is told to people by role, by a person field of the record, or to its
  assignees, with no conditions, copies or addresses of its own;
- it goes to the bell only, sets nothing and attaches nothing;
- and when it fires, only the people who may read the record are told
  (`Rule.get_list_of_recipients`), so a rule never shows anybody what their
  own permissions would not.

**The rules erpnext and hrms ship mail whoever they name**, whatever those
people chose. A module that declares one as a type (`rule` in its
`notifications.py`) has it carried: the people in the workspace are told
through the hub, in the rule's own words, and only an address that is nobody
here is still mailed (`Rule.send_an_email`). The rule itself is not changed,
so a new version of it arrives with the app.
"""

import json

import frappe
from frappe import _, _lt
from frappe.email.doctype.notification.notification import Notification

#: What a workspace rule may fire on.
EVENTS = ("New", "Save", "Submit", "Cancel", "Days After", "Days Before", "Value Change")

#: The app a rule's notification type is listed under, translated where shown.
APP = "Rules"
_lt("Rules")

#: Fields every record has, besides its own.
STANDARD = ("name", "owner", "creation", "modified", "modified_by")


def blank():
	"""A new rule. Rules are the workspace's own layer, as a tenant's
	arrangement is, not app content (tests/test_declarative.py)."""
	return frappe.new_doc("Notification")


def get(name: str):
	return frappe.get_doc("Notification", name)


class Rule(Notification):
	"""frappe's Notification, with a workspace rule held to what it may do."""

	def before_validate(self):
		if _workspace_rule(self):
			self.one_rule = 1
			_hold(self)
			_type_for(self)

	def validate(self):
		super().validate()
		if self.one_rule:
			for label, text in ((_("Subject"), self.subject), (_("Message"), self.message)):
				wrong = check_text(self.document_type, text)
				if wrong:
					frappe.throw(_("{0}: {1}").format(label, wrong))

	def on_trash(self):
		if self.one_rule:
			for name in frappe.get_all("Notification Type", filters={"one_rule": self.name}, pluck="name"):
				frappe.delete_doc("Notification Type", name, ignore_permissions=True, force=True)

	def get_list_of_recipients(self, doc, context):
		recipients, cc, bcc = super().get_list_of_recipients(doc, context)
		if self.flags.one_outside_only:
			inside = {key for one in _people(recipients + cc + bcc, both=True) for key in one}
			return [[one for one in each if one not in inside] for each in (recipients, cc, bcc)]
		if not self.one_rule:
			return recipients, cc, bcc
		return [one for one in recipients if _may_read(one, doc)], [], []

	def send_an_email(self, doc, context):
		name = carried(self)
		if not name:
			return super().send_an_email(doc, context)
		from markupsafe import Markup

		from onedesk.one import notify

		recipients, cc, bcc = super().get_list_of_recipients(doc, context)
		inside = _people(recipients + cc + bcc)
		if inside:
			# A standard rule's text, rendered as frappe renders it for mail.
			said = [
				Markup(frappe.render_template(text or "", context, restrict_globals=True))
				for text in (self.subject, self.message)
			]
			notify.notify(name, inside, record=(doc.doctype, doc.name), words=tuple(said))
		self.flags.one_outside_only = True
		try:
			super().send_an_email(doc, context)
		finally:
			self.flags.one_outside_only = False


def carried(rule) -> str:
	"""The type a standard rule of erpnext's or hrms's is carried to the bell
	as, or nothing: only one a module declared, and only while it mails."""
	if not rule.is_standard or rule.channel != "Email":
		return ""
	from onedesk.one import notify

	for name, one in notify.declared().items():
		if one.get("rule") == rule.name:
			return name
	return ""


def _people(addresses, both: bool = False) -> list:
	"""Of these addresses, the ones that are somebody in the workspace: their
	emails, or with `both` each one's name and email."""
	addresses = [one for one in addresses if one]
	if not addresses:
		return []
	found = frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User"},
		or_filters={"name": ["in", addresses], "email": ["in", addresses]},
		fields=["name", "email"],
	)
	return [(one.name, one.email) for one in found] if both else [one.email for one in found]


def _frappe_owns() -> bool:
	"""Whether the person saving holds one of the roles frappe itself gives
	Notification to, and so writes rules as frappe trusts them to."""
	owners = set(frappe.get_all("DocPerm", filters={"parent": "Notification", "write": 1}, pluck="role"))
	return frappe.session.user == "Administrator" or bool(owners & set(frappe.get_roles()))


def _workspace_rule(doc) -> bool:
	return bool(doc.one_rule) or not _frappe_owns()


def _hold(doc) -> None:
	"""A workspace rule, made to be one. Refuses what cannot be put right."""
	if not doc.document_type or not frappe.db.exists("DocType", doc.document_type):
		frappe.throw(_("Choose what the rule watches."))
	meta = frappe.get_meta(doc.document_type)
	if meta.istable or meta.issingle or not frappe.has_permission(doc.document_type, "read"):
		frappe.throw(_("A rule can only watch records you can open yourself."))
	if doc.event not in EVENTS:
		frappe.throw(
			_("A rule fires when a record is made, saved, submitted, cancelled or changed, or on a date.")
		)
	# Frappe's default condition type is Python even with nothing written: only
	# code is refused, and the type becomes filters.
	if (doc.condition or "").strip():
		frappe.throw(_("A rule's condition is chosen from the record's fields, not written as code."))
	doc.condition_type, doc.condition = "Filters", None
	doc.channel, doc.send_system_notification = "System Notification", 0
	doc.set_property_after_alert = doc.property_value = None
	doc.attach_print, doc.attach_files, doc.print_format = 0, None, None
	doc.is_standard = 0
	people = set(person_fields(doc.document_type))
	for row in doc.recipients or []:
		if row.condition or row.cc or row.bcc:
			frappe.throw(
				_(
					"A rule tells people by role, by a person on the record, or its assignees, and nobody else."
				)
			)
		if row.receiver_by_document_field and row.receiver_by_document_field not in people:
			frappe.throw(_("{0} is not a person on the record.").format(row.receiver_by_document_field))
	told = any(row.receiver_by_role or row.receiver_by_document_field for row in doc.recipients or [])
	if not (told or doc.send_to_all_assignees):
		frappe.throw(_("Say who the rule tells: a role, a person on the record, or its assignees."))
	doc.notification_type = doc.name


def _type_for(doc) -> None:
	"""The rule's notification type: what people choose its channels by."""
	values = {
		"one_app": APP,
		"one_rule": doc.name,
		"one_about": said(doc),
		"enabled": 1 if doc.enabled else 0,
	}
	if frappe.db.exists("Notification Type", doc.name):
		frappe.db.set_value("Notification Type", doc.name, values)
		return
	kind = frappe.new_doc("Notification Type")
	kind.type_name = doc.name
	kind.update({**values, "one_allow_email": 1, "one_allow_push": 1})
	kind.insert(ignore_permissions=True)


def _may_read(email: str, doc) -> bool:
	user = frappe.db.get_value("User", {"email": email, "enabled": 1}, "name")
	return bool(user) and frappe.has_permission(doc.doctype, "read", doc, user=user)


# ------------------------------------------------------------------ what a rule may say


def readable(doctype: str) -> list[str]:
	"""The fields of a record a rule's text may name: its own, at the first
	permission level, and the ones every record has. Pure but for the meta."""
	from frappe.model import no_value_fields

	meta = frappe.get_meta(doctype)
	own = [f.fieldname for f in meta.fields if f.fieldtype not in no_value_fields and not f.permlevel]
	return [*own, *STANDARD]


def check_text(doctype: str | None, text: str | None) -> str | None:
	"""What is wrong with a rule's subject or message, or None. Only
	`{{ doc.field }}`, of a field the record has, and text around it."""
	from jinja2 import TemplateSyntaxError, nodes
	from jinja2.sandbox import SandboxedEnvironment

	if not text:
		return None
	try:
		tree = SandboxedEnvironment().parse(text)
	except TemplateSyntaxError as e:
		return _("This does not read as a template: {0}").format(e.message)
	allowed = set(readable(doctype)) if doctype else set()
	for node in tree.find_all(nodes.Node):
		if isinstance(node, (nodes.Template, nodes.Output, nodes.TemplateData)):
			continue
		if isinstance(node, nodes.Getattr) and isinstance(node.node, nodes.Name) and node.node.name == "doc":
			if node.attr not in allowed:
				return _("The record has no field {0}.").format(node.attr)
			continue
		if isinstance(node, nodes.Name) and node.name == "doc":
			continue
		return _("A rule's text can name a field of the record, as {{ doc.field }}, and nothing else.")
	return None


# ------------------------------------------------------------------ what a rule is, in words


def person_fields(doctype: str) -> list[str]:
	"""Fields of a record that name a person a rule can tell: who made it, and
	any field linking a user or holding an email address."""
	meta = frappe.get_meta(doctype)
	found = ["owner"]
	for f in meta.fields:
		if (f.fieldtype == "Link" and f.options == "User") or (
			f.fieldtype == "Data" and f.options == "Email"
		):
			found.append(f.fieldname)
	return found


def said(doc) -> str:
	"""When a rule fires, as a sentence: "When a Sales Invoice is submitted"."""
	kind = _(doc.document_type or "")
	if doc.event in ("Days After", "Days Before"):
		field = _label(doc.document_type, doc.date_changed)
		days = doc.days_in_advance or 0
		return (
			_("{0} days after a {1}'s {2}").format(days, kind, field)
			if doc.event == "Days After"
			else _("{0} days before a {1}'s {2}").format(days, kind, field)
		)
	if doc.event == "Value Change":
		return _("When a {0}'s {1} changes").format(kind, _label(doc.document_type, doc.value_changed))
	return {
		"New": _("When a {0} is made"),
		"Save": _("When a {0} is saved"),
		"Submit": _("When a {0} is submitted"),
		"Cancel": _("When a {0} is cancelled"),
	}.get(doc.event, _("When a {0} changes")).format(kind)


def _label(doctype: str | None, fieldname: str | None) -> str:
	if not doctype or not fieldname:
		return ""
	field = frappe.get_meta(doctype).get_field(fieldname)
	return _(field.label) if field and field.label else fieldname


@frappe.whitelist()
@frappe.read_only()
def fields_of(doctype: str) -> dict:
	"""What the rule form offers once it knows what the rule watches."""
	from onedesk.one import roles

	roles.require()
	if not frappe.db.exists("DocType", doctype) or not frappe.has_permission(doctype, "read"):
		frappe.throw(_("A rule can only watch records you can open yourself."))
	meta = frappe.get_meta(doctype)

	def option(f):
		return {"value": f.fieldname, "label": _(f.label or f.fieldname)}

	return {
		"dates": [option(f) for f in meta.fields if f.fieldtype in ("Date", "Datetime")],
		"values": [option(f) for f in meta.fields if f.fieldname in readable(doctype) and f.label],
		"people": [
			{"value": name, "label": _("Created By") if name == "owner" else _label(doctype, name)}
			for name in person_fields(doctype)
		],
		"text": [{"value": name, "label": _label(doctype, name) or name} for name in readable(doctype)],
	}


@frappe.whitelist()
@frappe.read_only()
def watchable(
	doctype: str, txt: str, searchfield: str, start: int, page_len: int, filters: dict | None = None
):
	"""The kinds of record a rule may watch: ones the person can read, that are
	records in their own right."""
	from onedesk.one import roles

	roles.require()
	names = frappe.get_all(
		"DocType",
		filters={"istable": 0, "issingle": 0, "name": ["like", f"%{txt}%"]},
		pluck="name",
		order_by="name asc",
		# Frappe hands a translated doctype's query an empty search and filters
		# by the translated name itself, so every name has to come back.
		limit=0,
	)
	readable_names = [name for name in names if frappe.has_permission(name, "read")]
	return [[name] for name in readable_names[int(start) : int(start) + int(page_len)]]


def filters_of(doc) -> list:
	return json.loads(doc.filters) if doc.filters and doc.filters != "[]" else []
