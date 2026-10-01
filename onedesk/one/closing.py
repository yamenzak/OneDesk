"""Closing the workspace, and taking everything in it first.

Only the person the workspace is billed to may do either: they are the
customer, and both are about the whole company's data, salaries included,
which no administrator role is meant to reach in one go. Workspace >
Plan and Credits shows everybody else who can.

**The full download** is one zip, built in the background and kept on the
site until a newer one replaces it or the site is deleted:

- `database/`: frappe's own backup of the database, which any Frappe site
  restores (`bench restore`);
- `records/`: every kind of record with rows, one CSV each, readable in
  any spreadsheet;
- `files/`: every file, under the folder it is in, from OneCloud's store.

**Closing** asks the account (one_admin/closing.py) to close it in a
fortnight, confirmed with the payer's password. Until that day it works as
before and the payer can keep it open; everybody in it is told the day,
and told again if it stays open. On the day the account archives it, and
deletes it for good once the Terms' days on Archived have run.
"""

import csv
import io
import os
import re
import zipfile

import frappe
import requests
from frappe import _
from frappe.utils import cint, formatdate, now_datetime

from onedesk.one import account, roles

PAGE = account.PAGE

#: Kept out of the CSVs: the framework's queues and caches, and anything
#: that holds a key. All of it is in the database backup regardless.
LEFT_OUT = (
	"Email Queue",
	"Email Queue Recipient",
	"Error Log",
	"Scheduled Job Log",
	"Route History",
	"Prepared Report",
	"Submission Queue",
	"RQ Job",
	"OAuth Bearer Token",
	"OAuth Authorization Code",
	"Token Cache",
	"Workspace Account",
)

#: Rows read from a table at a time, so a large one is never held whole.
BATCH = 5000

#: How long one file may take to come from the store.
PATIENCE = 600


def _held():
	return frappe.get_single("Workspace Account")


def _is_payer(user: str | None = None) -> bool:
	payer = (_held().billed_to or "").strip().lower()
	return bool(payer) and (user or frappe.session.user).strip().lower() == payer


def _payer() -> None:
	roles.require()
	if not _is_payer():
		frappe.throw(
			_("Only {0}, who pays for the workspace, can do this.").format(
				_held().billed_to or _("its payer")
			),
			frappe.PermissionError,
		)


@frappe.whitelist()
def state() -> dict:
	"""What the Plan and Credits page shows about closing and the download."""
	roles.require()
	held = _held()
	from onedesk.one_admin.ladder import NOTICE_DAYS

	return {
		"notice_days": NOTICE_DAYS,
		"payer": held.billed_to,
		"is_payer": _is_payer(),
		"closing_on": str(held.closing_on) if held.closing_on else None,
		"deleted_on": str(held.deleted_on) if held.deleted_on else None,
		"export": {
			"status": held.export_status or None,
			"on": str(held.export_on) if held.export_on else None,
			"size": _size(cint(held.export_size)) if held.export_size else "",
		},
	}


@frappe.whitelist(methods=["POST"])
def prepare() -> dict:
	"""Start the full download. One at a time; a new one replaces the last."""
	_payer()
	held = _held()
	if held.export_status == "Preparing":
		return state()
	held.db_set({"export_status": "Preparing"}, update_modified=False)
	frappe.enqueue(
		build, queue="long", timeout=6 * 60 * 60, user=frappe.session.user, enqueue_after_commit=True
	)
	frappe.publish_realtime("one_closing", after_commit=True)
	return state()


def build(user: str) -> None:
	"""The zip: the database, every record as CSV, every file."""
	folder = frappe.get_site_path("private", "closing")
	os.makedirs(folder, exist_ok=True)
	name = f"{frappe.scrub(_held().workspace_name or frappe.local.site)}-{now_datetime():%Y-%m-%d}.zip"
	path = os.path.join(folder, name)
	# Written under a name of its own and moved into place whole, so a
	# download never meets a zip half made, or two made at once.
	part = os.path.join(folder, f".{name}.{os.getpid()}.part")
	missing = []
	try:
		with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zipped:
			_database(zipped)
			counts = _records(zipped)
			missing = _files(zipped)
			zipped.writestr("README.txt", _readme(counts, missing))
		os.replace(part, path)
	except Exception:
		if os.path.exists(part):
			os.remove(part)
		frappe.log_error(title="The full download")
		frappe.db.rollback()
		_held().db_set({"export_status": "Failed"}, update_modified=False)
		frappe.db.commit()
		frappe.publish_realtime("one_closing")
		return
	for old in os.listdir(folder):
		if old != name and not old.endswith(".part"):
			os.remove(os.path.join(folder, old))
	_held().db_set(
		{
			"export_status": "Ready",
			"export_on": now_datetime(),
			"export_size": os.path.getsize(path),
			"export_file": name,
		},
		update_modified=False,
	)
	frappe.db.commit()
	from onedesk.one import notify

	notify.notify(
		"Full Download Ready",
		user,
		link=PAGE,
		sender="Administrator",
		size=frappe.utils.cstr(_size(os.path.getsize(path))),
		missing=_("{0} files could not be read and are listed in it.").format(len(missing))
		if missing
		else "",
	)
	frappe.publish_realtime("one_closing")


def _size(value: int) -> str:
	from onedesk.one.heads import size

	return size(value)


def _database(zipped) -> None:
	"""frappe's own backup, moved into the zip."""
	from frappe.utils.backups import new_backup

	made = new_backup(ignore_files=True, force=True)
	zipped.write(made.backup_path_db, f"database/{os.path.basename(made.backup_path_db)}")
	os.remove(made.backup_path_db)


def _doctypes() -> list[str]:
	return frappe.get_all(
		"DocType",
		filters={"issingle": 0, "is_virtual": 0, "name": ["not in", list(LEFT_OUT)]},
		pluck="name",
		order_by="name asc",
	)


def _records(zipped) -> dict:
	"""One CSV per kind of record with rows, read in batches."""
	counts = {}
	tables = set(frappe.db.get_tables())
	for doctype in _doctypes():
		table = f"tab{doctype}"
		if table not in tables or not frappe.db.sql(f"select 1 from `{table}` limit 1"):
			continue
		written = 0
		with zipped.open(f"records/{_safe(doctype)}.csv", "w", force_zip64=True) as raw:
			out = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
			sheet = csv.writer(out)
			columns = frappe.db.get_table_columns(doctype)
			sheet.writerow(columns)
			start = 0
			while True:
				rows = frappe.db.sql(
					f"select * from `{table}` order by `name` limit %s offset %s",
					(BATCH, start),
					as_list=True,
				)
				sheet.writerows(rows)
				written += len(rows)
				if len(rows) < BATCH:
					break
				start += BATCH
			out.flush()
			out.detach()
		counts[doctype] = written
	return counts


def _files(zipped) -> list[str]:
	"""Every file under its folder, one copy per name; the ones that could
	not be read are returned and listed in the README."""
	from onedesk.one_storage import store

	missing, seen = [], set()
	for one in frappe.get_all(
		"File",
		filters={"is_folder": 0},
		fields=["name", "file_name", "file_url", "folder", "content_hash"],
		order_by="creation asc",
	):
		where = "/".join(_safe(part) for part in (one.folder or "Home").split("/"))
		arcname = f"files/{where}/{_safe(one.file_name or one.name)}"
		if (arcname, one.content_hash) in seen:
			continue
		stem, dot, ext = arcname.rpartition(".")
		taken = {name for name, _hash in seen}
		number = 1
		while arcname in taken:
			number += 1
			arcname = f"{stem} ({number}).{ext}" if dot else f"{arcname} ({number})"
		try:
			if store.is_stored(one.file_url):
				with requests.get(
					store.signed(store.key_of(one.file_url), inline=False), stream=True, timeout=PATIENCE
				) as answer:
					answer.raise_for_status()
					with zipped.open(arcname, "w", force_zip64=True) as into:
						for chunk in answer.iter_content(1024 * 1024):
							into.write(chunk)
			elif one.file_url and not one.file_url.startswith("http"):
				zipped.write(frappe.get_doc("File", one.name).get_full_path(), arcname)
			else:
				# A link to somewhere else: its address is in the File records.
				continue
			seen.add((arcname, one.content_hash))
		except Exception:
			missing.append(f"{arcname} ({one.name})")
	return missing


def _safe(text: str) -> str:
	return re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", str(text)).strip() or "_"


def _readme(counts: dict, missing: list) -> str:
	held = _held()
	lines = [
		f"{held.workspace_name or frappe.local.site}, as it was on {now_datetime():%Y-%m-%d %H:%M}.",
		"",
		"database/  The whole database, as Frappe backs it up. Any Frappe site restores it",
		"           with `bench --site <site> restore <file>`.",
		"records/   Every kind of record that has any, one CSV each. Open them in any spreadsheet.",
		"files/     Every file, under the folder it was in.",
		"",
		f"{len(counts)} kinds of record, {sum(counts.values())} rows.",
	]
	if missing:
		lines += ["", "These files could not be read when this was made:", *missing]
	return "\n".join(lines) + "\n"


@frappe.whitelist()
def download():
	"""The zip, for the payer only."""
	_payer()
	held = _held()
	if held.export_status != "Ready" or not held.export_file:
		frappe.throw(_("There is no full download yet."))
	from frappe.utils.response import send_private_file

	return send_private_file(f"closing/{held.export_file}")


@frappe.whitelist(methods=["POST"])
def close(password: str) -> dict:
	"""Ask the account to close the workspace in a fortnight. Everybody in it
	is told the day."""
	from frappe.utils.password import check_password

	_payer()
	try:
		check_password(frappe.session.user, password or "")
	except frappe.AuthenticationError:
		frappe.throw(_("That is not your password."), title=_("Not closed"))
	try:
		account.ask("onedesk.one_admin.proxy.close", by=frappe.utils.get_fullname())
	except account.faults.Refused as refused:
		frappe.throw(account._plainly(refused), title=_("Not closed"))
	account.refresh()
	held = _held()
	from onedesk.one import notify

	# Everybody, the payer too: the sender is One, not them.
	notify.notify(
		"Workspace Closing",
		_everybody(),
		link=PAGE,
		sender="Administrator",
		by=frappe.utils.get_fullname(),
		date=formatdate(held.closing_on),
		deleted=formatdate(held.deleted_on) if held.deleted_on else _("later"),
	)
	frappe.publish_realtime("one_closing", after_commit=True)
	return state()


@frappe.whitelist(methods=["POST"])
def keep() -> dict:
	"""Keep it open after all, before its day."""
	_payer()
	try:
		account.ask("onedesk.one_admin.proxy.withdraw_closing", by=frappe.utils.get_fullname())
	except account.faults.Refused as refused:
		frappe.throw(account._plainly(refused), title=_("Still closing"))
	account.refresh()
	from onedesk.one import notify

	notify.notify(
		"Workspace Staying Open",
		_everybody(),
		link=PAGE,
		sender="Administrator",
		by=frappe.utils.get_fullname(),
	)
	frappe.publish_realtime("one_closing", after_commit=True)
	return state()


def _everybody() -> list[str]:
	"""Everybody who signs in to the workspace, the payer included."""
	from onedesk.one.settings import NOT_PEOPLE

	return frappe.get_all(
		"User",
		filters={"enabled": 1, "user_type": "System User", "name": ["not in", list(NOT_PEOPLE)]},
		pluck="name",
	)
