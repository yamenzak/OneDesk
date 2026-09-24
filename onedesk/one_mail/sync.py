"""Connected mailboxes: the server is the truth, and this keeps up with it.

Every minute each connected account is read by one background job (its job
id keeps two from running at once). For each folder the server lists:

1. **Folders.** `LIST` is read every quarter of an hour and on first sync.
   Each folder becomes or stays a `Mail Folder`, its kind from its RFC 6154
   flag or its name. Folders that only repeat others (Gmail's All Mail,
   Starred, Important) are kept but not read, so no message is read twice.
2. **New mail.** Everything from the folder's UIDNEXT onward. A changed
   UIDVALIDITY means the server renumbered the folder. Its uids are then
   forgotten, and messages are matched again by Message-ID as they are read,
   so nothing is doubled.
3. **Older mail.** A folder is read newest first, `BATCH` at a time below the
   oldest uid read so far, until there is none: the last weeks arrive in the
   first minute, and years of history arrive over the following ones.
4. **Flags.** Read and starred are read back: with CONDSTORE, only what
   changed since the folder's HIGHESTMODSEQ; without it, the newest
   `WATCHED` messages.
5. **Gone.** When the server holds fewer messages than we think, the missing
   uids are found. Their Communications leave the folder but are not
   deleted: a message moved on a phone appears in its new folder with the same
   Message-ID and is matched to the one we have, keeping its links to
   records.

A message is matched to one we hold by Message-ID in the same mailbox, so a
move made here, a move made elsewhere and a renumbered folder all end with one
Communication, not two.
"""

import frappe
from frappe.utils import cint, now_datetime

from onedesk.one_mail import imap
from onedesk.one_mail.inbound import Arrival

#: Messages read per folder per run, in each direction.
BATCH = 100

#: Without CONDSTORE, how many of the newest messages have their flags read.
WATCHED = 500

#: How often the folder list is read again.
RELIST_EVERY = 15  # minutes

#: Kinds whose messages are the mailbox's own.
OWN = ("Sent", "Drafts")


def connected() -> list[str]:
	return frappe.get_all("Email Account", filters={"one_connected": 1}, pluck="name")


def sync_all() -> None:
	"""Scheduled every minute: one job per connected account."""
	for account in connected():
		frappe.enqueue(
			"onedesk.one_mail.sync.sync_account",
			queue="long",
			job_id=f"one_mail_sync:{account}",
			deduplicate=True,
			account=account,
		)


def sync_account(account: str) -> dict:
	doc = frappe.get_doc("Email Account", account)
	read = {"new": 0, "old": 0, "flags": 0, "gone": 0}
	try:
		with imap.Session(doc) as session:
			if _relist_due(account):
				discover(session, doc)
			for folder in frappe.get_all(
				"Mail Folder", filters={"account": account, "hidden": 0}, pluck="name", order_by="kind asc"
			):
				for key, count in sync_folder(session, doc, frappe.get_doc("Mail Folder", folder)).items():
					read[key] += count
				frappe.db.commit()
		if doc.one_error:
			frappe.db.set_value("Email Account", account, "one_error", None, update_modified=False)
	except Exception as error:
		frappe.db.rollback()
		frappe.db.set_value("Email Account", account, "one_error", imap.refused(error), update_modified=False)
		frappe.db.commit()
		raise
	return read


def _relist_due(account: str) -> bool:
	listed = frappe.db.exists("Mail Folder", {"account": account})
	return not listed or not frappe.cache.get_value(f"one_mail_listed:{account}")


def discover(session, doc) -> list[str]:
	"""The server's folders, as Mail Folder rows."""
	held = {
		row.path: row.name
		for row in frappe.get_all("Mail Folder", filters={"account": doc.name}, fields=["name", "path"])
	}
	seen = []
	for one in session.folders():
		path = one["path"]
		seen.append(path)
		values = {
			"kind": imap.kind_of(one["flags"], path, one["delimiter"]),
			"hidden": int(imap.repeats(one["flags"])),
			"delimiter": one["delimiter"],
			"label": imap.decode(path.split(one["delimiter"])[-1] if one["delimiter"] else path),
		}
		if path in held:
			frappe.db.set_value("Mail Folder", held[path], values, update_modified=False)
		else:
			folder = frappe.get_doc({"doctype": "Mail Folder", "account": doc.name, "path": path, **values})
			folder.insert(ignore_permissions=True)
	for path, name in held.items():
		if path not in seen:
			# Gone from the server: its messages leave with it.
			frappe.db.set_value(
				"Communication",
				{"email_account": doc.name, "one_folder": path},
				{"one_folder": None, "uid": 0},
			)
			frappe.delete_doc("Mail Folder", name, ignore_permissions=True, force=True)
	frappe.cache.set_value(f"one_mail_listed:{doc.name}", 1, expires_in_sec=RELIST_EVERY * 60)
	return seen


def sync_folder(session, doc, folder) -> dict:
	now = session.select(folder.path, readonly=True)
	read = {"new": 0, "old": 0, "flags": 0, "gone": 0}
	if folder.uidvalidity and folder.uidvalidity != now["uidvalidity"]:
		# Renumbered: forget the uids, keep the messages; they are matched
		# again by Message-ID as they are read.
		frappe.db.set_value("Communication", {"email_account": doc.name, "one_folder": folder.path}, "uid", 0)
		folder.uidnext = 0
		folder.oldest_uid = 0
		folder.backfilled = 0
		folder.modseq = None
	own = folder.kind in OWN

	if now["exists"]:
		everything = None
		first = not folder.uidnext
		if first:
			everything = session.uids("ALL")
			newest = everything[-BATCH:]
			read["new"] += _take(session, doc, folder, newest, own)
			folder.oldest_uid = newest[0] if newest else 0
			folder.backfilled = int(len(everything) <= BATCH)
		elif now["uidnext"] > cint(folder.uidnext):
			fresh = [one for one in session.uids(f"UID {folder.uidnext}:*") if one >= cint(folder.uidnext)]
			read["new"] += _take(session, doc, folder, fresh, own)
		if not folder.backfilled and folder.oldest_uid:
			everything = everything or session.uids("ALL")
			older = [one for one in everything if one < folder.oldest_uid][-BATCH:]
			read["old"] += _take(session, doc, folder, older, own)
			if older:
				folder.oldest_uid = older[0]
			folder.backfilled = int(not [one for one in everything if one < folder.oldest_uid])
		if not first:
			# Not on a folder's first read: its flags were just read with it.
			read["flags"] += _flags(session, doc, folder, now)
		read["gone"] += _gone(session, doc, folder, now)
	folder.uidvalidity = now["uidvalidity"]
	folder.uidnext = now["uidnext"]
	folder.modseq = str(now["modseq"]) if now["modseq"] else folder.modseq
	folder.total = now["exists"]
	folder.unread = frappe.db.count(
		"Communication", {"email_account": doc.name, "one_folder": folder.path, "seen": 0}
	)
	folder.last_synced = now_datetime()
	folder.flags.ignore_permissions = True
	folder.save()
	return read


def _take(session, doc, folder, uids: list[int], own: bool) -> int:
	"""Read these messages, newest first, in fetches of a few at a time."""
	taken = 0
	for at in range(len(uids), 0, -25):
		chunk = uids[max(0, at - 25) : at]
		for uid, row in sorted(session.fetch(chunk, "(UID FLAGS BODY.PEEK[])").items(), reverse=True):
			if row["body"] is None:
				continue
			try:
				if file(doc, folder.path, uid, row["body"], row["flags"], own):
					taken += 1
			except Exception:
				frappe.log_error(title=f"OneMail could not read uid {uid} in {folder.path} of {doc.name}")
	return taken


def message_id_of(raw: bytes) -> str | None:
	"""The Message-ID, as Frappe stores it, without its brackets. Pure."""
	for line in raw.split(b"\r\n\r\n", 1)[0].replace(b"\r\n", b"\n").split(b"\n"):
		if line.lower().startswith(b"message-id:"):
			return line.split(b":", 1)[1].strip().strip(b"<>").decode(errors="replace") or None
	return None


def file(doc, path: str, uid: int, raw: bytes, flags: set, own: bool) -> str | None:
	"""One message from the server, into a Communication, or into the one we
	already hold with its Message-ID."""
	seen, flagged = int("\\seen" in flags), int("\\flagged" in flags)
	message_id = message_id_of(raw)
	if message_id:
		held = frappe.db.get_value(
			"Communication", {"email_account": doc.name, "message_id": message_id}, "name"
		)
		if held:
			frappe.db.set_value(
				"Communication",
				held,
				{"one_folder": path, "uid": uid, "seen": seen, "one_flagged": flagged},
				update_modified=False,
			)
			return None
	made = Arrival(raw, doc, folder=path, uid=uid, seen=seen, flagged=flagged, sent=own).process()
	return made.name if made else None


def _flags(session, doc, folder, now) -> int:
	if session.can("CONDSTORE") and folder.modseq:
		if now["modseq"] and int(now["modseq"]) <= int(folder.modseq):
			return 0
		changed = _changed_since(session, int(folder.modseq))
	else:
		recent = frappe.get_all(
			"Communication",
			filters={"email_account": doc.name, "one_folder": folder.path, "uid": [">", 0]},
			pluck="uid",
			order_by="uid desc",
			limit=WATCHED,
		)
		changed = session.fetch(sorted(recent), "(UID FLAGS)") if recent else {}
	updated = 0
	for uid, row in changed.items():
		values = {"seen": int("\\seen" in row["flags"]), "one_flagged": int("\\flagged" in row["flags"])}
		name = frappe.db.get_value(
			"Communication", {"email_account": doc.name, "one_folder": folder.path, "uid": uid}, "name"
		)
		if name:
			frappe.db.set_value("Communication", name, values, update_modified=False)
			updated += 1
	return updated


def _changed_since(session, modseq: int) -> dict:
	status, data = session.imap.uid("FETCH", "1:*", "(UID FLAGS)", f"(CHANGEDSINCE {modseq})")
	return imap.parse_fetch(data) if status == "OK" else {}


def _gone(session, doc, folder, now) -> int:
	held = frappe.db.count(
		"Communication", {"email_account": doc.name, "one_folder": folder.path, "uid": [">", 0]}
	)
	if held <= now["exists"]:
		return 0
	there = set(session.uids("ALL"))
	missing = frappe.get_all(
		"Communication",
		filters={"email_account": doc.name, "one_folder": folder.path, "uid": ["not in", list(there) or [0]]},
		pluck="name",
	)
	for name in missing:
		frappe.db.set_value("Communication", name, {"one_folder": None, "uid": 0}, update_modified=False)
	return len(missing)
