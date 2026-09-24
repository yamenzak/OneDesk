"""The one door every Intake write goes through (docs/INTAKE.md §15.3).

A planner says what should happen as an `Action`; `apply` decides whether it
happens, and is the only code in Intake that writes. In order:

1. **the key.** An action already written under this key, done, proposed,
   dismissed or undone, is not done again. A copy, a retry and a re-run find
   the key and stop there; so does something a person dismissed or undid;
2. **on whose behalf.** The person who switched the folder or mailbox on must
   be allowed to do this themselves (§4.3). If not, it is written down as
   refused and nothing happens;
3. **the level.** Done, or proposed for a person to look at: an overwrite, the
   end of somebody's employment, and anything below the confidence floor or
   from a reading whose facts did not check out (§4.1). Nothing is submitted,
   so posting stays a draft whatever the level;
4. **the flow.** A record whose making has a door of its own (`make_employee`,
   OneCRM's `capture`) is made through it, named by `flow`;
5. **the write**, as the OneAI user, with what was there before kept for Undo;
6. **the mark** on a record OneAI made (mark.py), and the `Intake Action` row.

`undo` takes an action back, and says why when it cannot: a record a person
has since checked, submitted or built on stays.
"""

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass, field

import frappe
from frappe import _
from frappe.utils import cint, flt

from onedesk.one_hr.hiring import AUTHOR
from onedesk.one_intake import mark

KINDS = ("Create", "Update", "Link", "Attach", "Rename", "Move", "Tag", "Comment")

#: What the person on whose behalf OneAI acts must be allowed on the target.
NEEDS = {
	"Create": "create",
	"Update": "write",
	"Link": "read",
	"Attach": "write",
	"Rename": "write",
	"Move": "write",
	"Tag": "read",
	"Comment": "read",
}

#: The confidence under which a record or a change waits for a person.
FLOOR = 70

#: Kinds whose record OneAI makes or changes; the rest only file and label.
CHANGES = ("Create", "Update")


@dataclass
class Action:
	kind: str
	doctype: str
	name: str | None = None
	values: dict = field(default_factory=dict)
	key: str = ""
	why: str = ""
	confidence: float = 1.0
	ends_employment: bool = False
	#: Nothing was judged: a batch scan cut where its pages say, a file
	#: named. The reading's doubts do not hold it back.
	sure: bool = False
	#: A dotted path to the flow's own function, which takes the values and
	#: answers the record it made.
	flow: str | None = None


# ------------------------------------------------------------------ deciding


def level(action: Action, reading: dict, before: dict, floor: float = FLOOR) -> tuple[str, str, list]:
	"""Done or Proposed, why it waits (a word `waits` says in full), and the
	fields it would overwrite. Pure."""
	if action.ends_employment:
		return "Proposed", "employment", []
	if action.kind == "Update":
		overwritten = sorted(key for key, value in (action.values or {}).items() if _filled(before.get(key)) and not _same(before.get(key), value))
		if overwritten:
			return "Proposed", "overwrite", overwritten
	if action.kind in CHANGES and not action.sure:
		if flt(action.confidence, 1) * 100 < floor:
			return "Proposed", "unsure", []
		if cint(reading.get("unsure")):
			return "Proposed", "dropped", []
	return "Done", "", []


def waits(why: str, fields: list, doctype: str) -> str:
	"""Why an action waits for a person, in their words."""
	if why == "overwrite":
		meta = frappe.get_meta(doctype)
		return _("It would change what {0} already says.").format(", ".join(_(meta.get_label(one)) for one in fields))
	return {
		"employment": _("It would end somebody's employment."),
		"unsure": _("OneAI is not sure enough."),
		"dropped": _("Some of what OneAI read is not in the document."),
	}.get(why, "")


def key_of(reading_key: str, action: Action) -> str:
	"""The key an action is written under when its planner gave none. Pure."""
	if action.key:
		return action.key[:140]
	said = json.dumps(action.values, sort_keys=True, default=str)
	digest = hashlib.md5(f"{action.kind}|{action.doctype}|{action.name or ''}|{said}".encode()).hexdigest()[:12]
	return f"{reading_key[:100]}|{action.kind}|{digest}"


def _filled(value) -> bool:
	return value not in (None, "", 0, 0.0, [])


def _same(one, other) -> bool:
	if isinstance(one, int | float) or isinstance(other, int | float):
		return flt(one) == flt(other)
	return str(one or "").strip() == str(other or "").strip()


# ------------------------------------------------------------------ the door


def apply(action: Action, reading) -> str | None:
	"""Do, propose or refuse one action for a reading. Answers the Intake
	Action row's name, or None when there is nobody to act for."""
	if action.kind not in KINDS:
		raise ValueError(f"Intake cannot {action.kind}")
	person = reading.on_behalf_of
	if not person or cint(reading.history):
		return None
	key = key_of(reading.key, action)
	held = frappe.db.get_value("Intake Action", {"key": key}, "name")
	if held:
		return held

	row = frappe.new_doc("Intake Action")
	row.update(
		{
			"kind": action.kind,
			"target_doctype": action.doctype,
			"target_name": action.name,
			"reading": reading.name,
			"key": key,
			"on_behalf_of": person,
			"confidence": min(100, flt(action.confidence, 1) * 100),
			"why": action.why[:1000] if action.why else None,
			"after": json.dumps(action.values, default=str),
		}
	)
	if not allowed(action, person):
		row.level = "Refused"
		row.why = _join(row.why, _("{0} may not do this themselves.").format(person))
		return _insert(row)

	before = _before(action)
	row.level, why, fields = level(action, reading.as_dict(), before, _floor())
	row.before = json.dumps(before, default=str) if before else None
	if why:
		row.why = _join(row.why, waits(why, fields, action.doctype))
	if row.level == "Done":
		frappe.db.savepoint("one_intake_act")
		try:
			with as_oneai():
				done = _write(action, before)
		except Exception as raised:
			frappe.db.rollback(save_point="one_intake_act")
			row.level = "Refused"
			row.why = _join(row.why, str(raised)[:500] or type(raised).__name__)
			return _insert(row)
		row.target_name = done.get("name") or action.name
		row.after = json.dumps(done, default=str)
		if action.kind == "Create":
			mark.mark(action.doctype, row.target_name, reading.name)
	return _insert(row)


def _insert(row) -> str:
	try:
		row.insert(ignore_permissions=True)
	except frappe.DuplicateEntryError:
		# The same key, written by another job a moment ago.
		return frappe.db.get_value("Intake Action", {"key": row.key}, "name")
	return row.name


def _join(said: str | None, more: str) -> str:
	return f"{said}\n{more}" if said else more


def _floor() -> float:
	return flt(frappe.db.get_single_value("Intake Settings", "floor")) or FLOOR


@contextmanager
def as_oneai():
	"""Write as the OneAI user, so every record, version and comment says who
	made it, with the person's permission already checked."""
	from onedesk.one_hr.hiring import ensure

	ensure()
	was, writing = frappe.session.user, frappe.flags.one_intake_writing
	frappe.flags.one_intake_writing = True
	frappe.set_user(AUTHOR)
	try:
		yield
	finally:
		frappe.set_user(was)
		frappe.flags.one_intake_writing = writing


def allowed(action: Action, person: str) -> bool:
	"""May the person OneAI acts for do this themselves?"""
	ptype = NEEDS[action.kind]
	if action.kind == "Create":
		return bool(frappe.has_permission(action.doctype, "create", user=person))
	if not action.name or not frappe.db.exists(action.doctype, action.name):
		return False
	if action.doctype == "File":
		from onedesk.one_storage import namespace as ns

		item = ns.row(action.name)
		if not item or not ns.may(item, "write" if ptype == "write" else "read", user=person):
			return False
	elif not frappe.has_permission(action.doctype, ptype, action.name, user=person):
		return False
	# Filing a file on a record: the person must be able to open the file too.
	held = action.values.get("file")
	if held and action.kind in ("Link", "Attach"):
		from onedesk.one_storage import namespace as ns

		item = ns.row(held)
		return bool(item and ns.may(item, "read", user=person))
	return True


# ------------------------------------------------------------------ the writes


def _before(action: Action) -> dict:
	"""What the target says now, for the level and for Undo."""
	if action.kind in ("Create", "Link", "Tag", "Comment") or not action.name:
		return {}
	if action.kind == "Update":
		held = frappe.db.get_value(action.doctype, action.name, list(action.values), as_dict=True) or {}
		return dict(held)
	if action.kind == "Rename":
		return {"file_name": frappe.db.get_value("File", action.name, "file_name")}
	if action.kind == "Move" and action.doctype == "File":
		return {"folder": frappe.db.get_value("File", action.name, "folder")}
	if action.kind == "Move":
		held = frappe.db.get_value("Communication", action.name, ["email_account", "one_folder"], as_dict=True) or {}
		return {"one_folder": held.get("one_folder")}
	if action.kind == "Attach":
		held = frappe.db.get_value("File", action.values.get("file"), ["attached_to_doctype", "attached_to_name", "attached_to_field", "folder"], as_dict=True) or {}
		return dict(held)
	return {}


def _write(action: Action, before: dict) -> dict:
	return WRITES[action.kind](action, before)


def _create(action: Action, before: dict) -> dict:
	if action.flow:
		doc = frappe.get_attr(action.flow)(dict(action.values))
	else:
		doc = frappe.get_doc({"doctype": action.doctype, **action.values})
		doc.flags.ignore_permissions = True
		doc.insert()
	return {"name": doc.name}


def _update(action: Action, before: dict) -> dict:
	doc = frappe.get_doc(action.doctype, action.name)
	doc.update(action.values)
	doc.flags.ignore_permissions = True
	doc.save()
	from onedesk.one_ai import touch

	# A field OneAI filled on a record a person made gets the field badge.
	touch.wrote(action.doctype, action.name, action.values)
	return {"name": action.name, **action.values}


def _link(action: Action, before: dict) -> dict:
	if action.values.get("message"):
		from onedesk.one_mail import linking

		linking.add(action.values["message"], action.doctype, action.name, "oneai")
		return {"name": action.name, "message": action.values["message"]}
	held = frappe.db.get_value("File Link", {"file": action.values["file"], "for_doctype": action.doctype, "for_name": action.name})
	if held:
		return {"name": action.name, "file_link": held, "held": 1}
	doc = frappe.get_doc(
		{"doctype": "File Link", "file": action.values["file"], "for_doctype": action.doctype, "for_name": action.name, "reading": action.values.get("reading")}
	)
	doc.insert(ignore_permissions=True)
	return {"name": action.name, "file_link": doc.name}


def _attach(action: Action, before: dict) -> dict:
	"""A file in the record's Files tab. A mail's attachment stays on the mail,
	and the record gets a copy of the same stored file."""
	source = frappe.get_doc("File", action.values["file"])
	if source.attached_to_doctype == "Communication":
		if action.values.get("file_name"):
			source.file_name = action.values["file_name"]
		copy = source.create_attachment_copy(action.doctype, action.name, ignore_permissions=True)
		return {"name": action.name, "file": copy.name, "copied": 1}
	source.attached_to_doctype, source.attached_to_name, source.attached_to_field = action.doctype, action.name, None
	source.flags.ignore_permissions = True
	source.save()
	return {"name": action.name, "file": source.name}


def _rename(action: Action, before: dict) -> dict:
	frappe.db.set_value("File", action.name, "file_name", action.values["file_name"])
	return {"name": action.name, "file_name": action.values["file_name"]}


def _move(action: Action, before: dict) -> dict:
	if action.doctype == "File":
		doc = frappe.get_doc("File", action.name)
		doc.folder = action.values.get("folder") or folder_at(action.values["under"], action.values["path"])
		doc.flags.ignore_permissions = True
		doc.save()
		return {"name": action.name, "folder": doc.folder}
	from onedesk.one_mail import actions

	frappe.flags.one_mail_rules = True
	try:
		target = action.values.get("mail_folder") or _mail_folder(action.name, action.values["mail_folder_label"])
		moved = actions.move([action.name], target)
	finally:
		frappe.flags.one_mail_rules = False
	return {"name": action.name, "mail_folder": target, "was": moved.get("was")}


def folder_at(under: str, path: list[str]) -> str:
	"""The folder at a path below another, made where it is missing."""
	at = under
	for label in path:
		label = str(label).replace("/", "-").strip()
		if not label:
			continue
		held = frappe.db.get_value("File", {"folder": at, "file_name": label, "is_folder": 1}, "name")
		if not held:
			made = frappe.get_doc({"doctype": "File", "is_folder": 1, "file_name": label, "folder": at})
			made.flags.ignore_permissions = True
			made.insert()
			held = made.name
		at = held
	return at


def _mail_folder(message: str, label: str) -> str:
	from onedesk.one_mail import actions

	account = frappe.db.get_value("Communication", message, "email_account")
	held = frappe.db.get_value("Mail Folder", {"account": account, "label": label}, "name")
	return held or actions.create_folder(account, label)


def _tag(action: Action, before: dict) -> dict:
	"""Frappe's own tags. `DocTags.add` checks write permission for whoever is
	signed in, and the OneAI user holds none, so the same two writes it makes
	are made here, with the person's permission already checked."""
	there = [one.strip() for one in (frappe.db.get_value(action.doctype, action.name, "_user_tags") or "").split(",") if one.strip()]
	added = [tag for tag in dict.fromkeys(action.values.get("tags") or []) if tag and tag.lower() not in {one.lower() for one in there}]
	if added:
		_set_tags(action.doctype, action.name, there + added)
		title = frappe.get_lazy_doc(action.doctype, action.name).get_title() or ""
		for tag in added:
			if not frappe.db.exists("Tag", tag):
				frappe.get_doc({"doctype": "Tag", "name": tag}).insert(ignore_permissions=True)
			frappe.get_doc({"doctype": "Tag Link", "document_type": action.doctype, "document_name": action.name, "title": title, "tag": tag}).insert(ignore_permissions=True)
	return {"name": action.name, "tags": added}


def _set_tags(doctype: str, name: str, tags: list[str]) -> None:
	frappe.db.set_value(doctype, name, "_user_tags", ",".join(tags), update_modified=False)


def _comment(action: Action, before: dict) -> dict:
	doc = frappe.get_doc(action.doctype, action.name)
	made = doc.add_comment(action.values.get("comment_type") or "Comment", action.values.get("content"))
	return {"name": action.name, "comment": made.name}


WRITES = {
	"Create": _create,
	"Update": _update,
	"Link": _link,
	"Attach": _attach,
	"Rename": _rename,
	"Move": _move,
	"Tag": _tag,
	"Comment": _comment,
}


# ------------------------------------------------------------------ a person decides


def _may_decide(row) -> None:
	from onedesk.one.roles import administers

	if frappe.session.user != row.on_behalf_of and not administers():
		frappe.throw(_("Only {0} or an administrator of this workspace can decide this.").format(row.on_behalf_of), frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def settle(action: str, take: int = 1) -> dict:
	"""Apply or dismiss something OneAI proposed. Applied, it is done as the
	person pressing Apply, under their own permission, and carries no mark:
	a person decided to make it."""
	row = frappe.get_doc("Intake Action", action)
	_may_decide(row)
	if row.level != "Proposed":
		frappe.throw(_("This was already {0}.").format(_(row.level).lower()))
	if not cint(take):
		row.db_set({"level": "Dismissed", "checked_by": frappe.session.user})
		return {"level": "Dismissed"}
	planned = Action(kind=row.kind, doctype=row.target_doctype, name=row.target_name, values=json.loads(row.after or "{}"))
	if not allowed(planned, frappe.session.user):
		frappe.throw(_("You may not do this yourself."), frappe.PermissionError)
	before = _before(planned)
	frappe.flags.one_intake_writing = True
	try:
		done = _write(planned, before)
	finally:
		frappe.flags.one_intake_writing = False
	row.db_set(
		{
			"level": "Done",
			"checked_by": frappe.session.user,
			"target_name": done.get("name") or row.target_name,
			"before": json.dumps(before, default=str) if before else None,
			"after": json.dumps(done, default=str),
		}
	)
	return {"level": "Done", "target": [row.target_doctype, row.target_name]}


# ------------------------------------------------------------------ undo


@frappe.whitelist(methods=["POST"])
def undo(reading: str) -> dict:
	"""Take back everything done because of one document, and its parts,
	newest first. Answers what was undone and what was kept, and why."""
	names = [reading, *frappe.get_all("Reading", filters={"part_of": reading}, pluck="name")]
	rows = frappe.get_all("Intake Action", filters={"reading": ["in", names], "level": "Done"}, pluck="name", order_by="creation desc")
	undone, kept = 0, []
	for name in rows:
		row = frappe.get_doc("Intake Action", name)
		_may_decide(row)
		why = take_back(row)
		if why:
			kept.append({"kind": _(row.kind), "target": [row.target_doctype, row.target_name], "why": why})
		else:
			undone += 1
	return {"undone": undone, "kept": kept}


@frappe.whitelist(methods=["POST"])
def undo_one(action: str) -> dict:
	row = frappe.get_doc("Intake Action", action)
	_may_decide(row)
	if row.level != "Done":
		frappe.throw(_("This was already {0}.").format(_(row.level).lower()))
	why = take_back(row)
	return {"undone": 0 if why else 1, "why": why}


def take_back(row) -> str | None:
	"""Undo one done action. None when it is undone, else why it stays."""
	after = json.loads(row.after or "{}")
	before = json.loads(row.before or "{}")
	try:
		with as_oneai():
			why = UNDO[row.kind](row, before, after)
	except frappe.LinkExistsError:
		why = _("something else uses it now")
	if not why:
		row.db_set({"level": "Undone", "undone_by": frappe.session.user})
	return why


def _undo_create(row, before, after) -> str | None:
	if not frappe.db.exists(row.target_doctype, row.target_name):
		return None
	doc = frappe.get_doc(row.target_doctype, row.target_name)
	if not mark.is_marked(row.target_doctype, row.target_name):
		return _("a person has checked it since")
	if cint(doc.get("docstatus")) != 0:
		return _("it has been submitted")
	frappe.delete_doc(row.target_doctype, row.target_name, ignore_permissions=True)
	return None


def _undo_update(row, before, after) -> str | None:
	if not frappe.db.exists(row.target_doctype, row.target_name):
		return None
	doc = frappe.get_doc(row.target_doctype, row.target_name)
	if cint(doc.get("docstatus")) != 0:
		return _("it has been submitted")
	back = {key: before.get(key) for key, value in after.items() if key != "name" and _same(doc.get(key), value)}
	if not back:
		return _("a person has changed it since")
	doc.update(back)
	doc.flags.ignore_permissions = True
	doc.save()
	return None


def _undo_link(row, before, after) -> str | None:
	if after.get("message"):
		frappe.db.delete("Communication Link", {"parent": after["message"], "link_doctype": row.target_doctype, "link_name": row.target_name, "one_linked_by": "oneai"})
	elif after.get("file_link") and not after.get("held"):
		frappe.db.delete("File Link", {"name": after["file_link"]})
	return None


def _undo_attach(row, before, after) -> str | None:
	name = after.get("file")
	if not name or not frappe.db.exists("File", name):
		return None
	if after.get("copied"):
		frappe.delete_doc("File", name, ignore_permissions=True)
		return None
	doc = frappe.get_doc("File", name)
	if (doc.attached_to_doctype, doc.attached_to_name) != (row.target_doctype, row.target_name):
		return _("a person has moved it since")
	doc.update({"attached_to_doctype": before.get("attached_to_doctype"), "attached_to_name": before.get("attached_to_name"), "attached_to_field": before.get("attached_to_field"), "folder": before.get("folder") or doc.folder})
	doc.flags.ignore_permissions = True
	doc.save()
	return None


def _undo_rename(row, before, after) -> str | None:
	if frappe.db.get_value("File", row.target_name, "file_name") != after.get("file_name"):
		return _("a person has renamed it since")
	frappe.db.set_value("File", row.target_name, "file_name", before.get("file_name"))
	return None


def _undo_move(row, before, after) -> str | None:
	if row.target_doctype == "File":
		doc = frappe.get_doc("File", row.target_name)
		if doc.folder != after.get("folder"):
			return _("a person has moved it since")
		doc.folder = before.get("folder")
		doc.flags.ignore_permissions = True
		doc.save()
		return None
	from onedesk.one_mail import actions

	frappe.flags.one_mail_rules = True
	try:
		actions.put_back(after.get("was") or [])
	finally:
		frappe.flags.one_mail_rules = False
	return None


def _undo_tag(row, before, after) -> str | None:
	gone = {one.lower() for one in after.get("tags") or []}
	there = [one.strip() for one in (frappe.db.get_value(row.target_doctype, row.target_name, "_user_tags") or "").split(",") if one.strip()]
	_set_tags(row.target_doctype, row.target_name, [one for one in there if one.lower() not in gone])
	for tag in after.get("tags") or []:
		frappe.db.delete("Tag Link", {"document_type": row.target_doctype, "document_name": row.target_name, "tag": tag})
	return None


def _undo_comment(row, before, after) -> str | None:
	if after.get("comment") and frappe.db.exists("Comment", after["comment"]):
		frappe.delete_doc("Comment", after["comment"], ignore_permissions=True)
	return None


UNDO = {
	"Create": _undo_create,
	"Update": _undo_update,
	"Link": _undo_link,
	"Attach": _undo_attach,
	"Rename": _undo_rename,
	"Move": _undo_move,
	"Tag": _undo_tag,
	"Comment": _undo_comment,
}


# ------------------------------------------------------------------ who sees them


def query(user=None) -> str:
	"""Intake Action list: a person sees what OneAI did on their behalf; an
	administrator sees all of it."""
	from onedesk.one.roles import administers

	user = user or frappe.session.user
	if administers(user):
		return ""
	return f"`tabIntake Action`.on_behalf_of = {frappe.db.escape(user)}"


def has_permission(doc, ptype=None, user=None, debug=False) -> bool:
	from onedesk.one.roles import administers

	user = user or frappe.session.user
	return administers(user) or doc.on_behalf_of == user
