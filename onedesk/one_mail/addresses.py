"""Addresses on the mail domain: `<slug>@m.4dl.app` for the workspace, and
`<name>.<slug>@m.4dl.app` for a person in it.

Each is an `Email Account` with `one_hosted` set. It has no server, because
there is none: the mail Worker stores what arrives, `inbound.py` files it, and
sending goes through admin to Cloudflare (stage 2). The workspace's address
sends and receives, and a person's only receives.

A slug has no dot, so the part after the last dot of a local part is always
the workspace, and `is_workspace_name` is the whole rule. The Worker and admin
apply the same one.
"""

import re
import unicodedata

import frappe
from frappe import _

from onedesk.one_mail import actions

#: A person's part: letters, digits, dash and underscore, no dot, as a slug is.
NAME = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,38}[a-z0-9])?$")

#: Names nobody may take, because mail servers and people expect them to mean
#: something else.
RESERVED = frozenset(
	(
		"abuse", "admin", "administrator", "billing", "bounce", "bounces", "hostmaster",
		"info", "mailer-daemon", "no-reply", "noreply", "postmaster", "root", "security",
		"support", "webmaster",
	)
)  # fmt: skip


def is_workspace_name(local: str, slug: str) -> bool:
	"""Whether a local part is this workspace's: its own, or one of its
	people's. Pure."""
	local = (local or "").lower()
	if not slug:
		return False
	if local == slug:
		return True
	suffix = "." + slug
	return local.endswith(suffix) and is_name(local[: -len(suffix)])


def is_name(name: str) -> bool:
	"""Whether a person's part may be used. Pure."""
	return bool(NAME.match(name or "")) and name not in RESERVED


def domain() -> str:
	return frappe.conf.get("one_mail_domain") or "m.4dl.app"


def slug() -> str | None:
	return frappe.conf.get("one_tenant")


def workspace_address() -> str | None:
	return f"{slug()}@{domain()}" if slug() else None


def person_address(name: str) -> str:
	return f"{name}.{slug()}@{domain()}"


def hosted() -> list[dict]:
	return frappe.get_all(
		"Email Account", filters={"one_hosted": 1}, fields=["name", "email_id", "enable_outgoing"]
	)


def account_for(local: str) -> str | None:
	"""The hosted account a local part arrived at."""
	address = f"{(local or '').lower()}@{domain()}"
	return frappe.db.get_value("Email Account", {"one_hosted": 1, "email_id": address}, "name")


def ensure_workspace() -> str | None:
	"""The workspace's own address, made the first time it is needed."""
	address = workspace_address()
	if not address:
		return None
	found = frappe.db.get_value("Email Account", {"email_id": address}, "name")
	if found:
		return found
	made = _make(address, sends=True)
	# The workspace's mailbox, held at first by whoever administers it; they
	# choose who else holds it (holders.py).
	frappe.db.set_value("Email Account", made, "one_shared", 1, update_modified=False)
	from onedesk.one import roles

	for user in frappe.get_all(
		"Has Role", filters={"role": roles.ADMINISTRATOR, "parenttype": "User"}, pluck="parent"
	):
		if user not in ("Administrator", "Guest"):
			hold(made, user)
	publish()
	return made


@frappe.whitelist(methods=["POST"])
def give(user: str, name: str) -> str:
	"""A person's own address, `<name>.<slug>@`, chosen by a workspace
	administrator. It only receives; they write from the workspace's address
	or one they hold."""
	from onedesk.one import roles

	frappe.only_for(roles.ADMINISTRATOR)
	return _give(user, name)


def _give(user: str, name: str, holder=None) -> str:
	"""`holder` is the User being saved, when this runs inside its save."""
	name = (name or "").strip().lower()
	if not is_name(name):
		frappe.throw(_("{0} cannot be a name in an address. Use letters, digits, - and _.").format(name))
	address = person_address(name)
	if frappe.db.exists("Email Account", {"email_id": address}):
		frappe.throw(_("{0} is already somebody's.").format(address))
	made = _make(address, sends=False)
	if holder is not None:
		holder.append("user_emails", {"email_account": made})
	else:
		hold(made, user)
	publish()
	return made


def hold(account: str, user: str) -> None:
	"""`user` holds `account`: a User Email row, which is also what Frappe's
	own Communication permission reads."""
	if frappe.db.exists("User Email", {"parent": user, "email_account": account}):
		return
	holder = frappe.get_doc("User", user)
	holder.append("user_emails", {"email_account": account})
	holder.flags.ignore_permissions = True
	holder.save()


def suggested(first_name: str | None, email: str | None) -> str:
	"""A name for somebody's address, before anyone chooses one: their first
	name, else the start of their login address, as far as either is letters
	and digits. Pure."""
	for source in (first_name, (email or "").split("@")[0]):
		plain = unicodedata.normalize("NFKD", source or "").encode("ascii", "ignore").decode()
		name = re.sub(r"[^a-z0-9_-]+", "-", plain.strip().lower()).strip("-_")[:40].strip("-_")
		if is_name(name):
			return name
	return "member"


def free(name: str) -> str:
	"""`name`, or `name2`, `name3`… whichever nobody has."""
	taken = {
		row.split("@")[0].rsplit(".", 1)[0]
		for row in frappe.get_all("Email Account", filters={"one_hosted": 1}, pluck="email_id")
	}
	if name not in taken:
		return name
	at = 2
	while f"{name}{at}" in taken:
		at += 1
	return f"{name}{at}"


def for_person(doc, method=None) -> None:
	"""User before_save: everyone who works here has an address. The name is the one a workspace administrator typed in Mail Name
	when adding them, or one made from their first name."""
	if doc.user_type != "System User" or doc.name in ("Administrator", "Guest") or not doc.enabled:
		return
	if not (slug() and frappe.conf.get("one_mail_secret")):
		return
	own = f".{slug()}@{domain()}"
	held = [
		row.email_account for row in doc.get("user_emails") or [] if (row.email_account or "").endswith(own)
	]
	if held:
		# Set once: the address is what people already write to.
		name = held[0].split("@")[0].rsplit(".", 1)[0]
		if doc.one_mail_name and doc.one_mail_name != name:
			frappe.throw(_("{0} already has the address {1}, and it stays.").format(doc.name, held[0]))
		doc.one_mail_name = name
		return
	name = (doc.one_mail_name or "").strip().lower() or free(suggested(doc.first_name, doc.email))
	_give(doc.name, name, holder=doc)
	doc.one_mail_name = name


def _make(address: str, sends: bool) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "Email Account",
			"email_account_name": address,
			"email_id": address,
			"one_hosted": 1,
			"enable_incoming": 0,
			"enable_outgoing": int(sends),
			# The workspace's own address sends for it, unless somebody has set up
			# another account to; replacing it is a workspace setting (stage 4).
			"default_outgoing": int(sends and not frappe.db.exists("Email Account", {"default_outgoing": 1})),
			# Sending goes through override_email_send (outbound.py), so no SMTP
			# server is ever dialled. Frappe's queue still builds an SMTPServer
			# for the account and refuses one with no host, so the mail domain
			# stands in for it; the session it would open is never asked for.
			"smtp_server": domain(),
			"no_smtp_authentication": 1,
			"always_use_account_email_id_as_sender": 1,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	actions.standard(doc.name)
	return doc.name


def publish() -> None:
	"""Tell the Worker, through admin, which names this workspace receives
	for, so it refuses the rest while the sender is still connected."""
	from onedesk.one import account

	if not account.configured():
		return
	names = sorted({row.email_id.split("@")[0] for row in hosted() if row.email_id.endswith("@" + domain())})
	if names:
		account.ask("onedesk.one_admin.proxy.mail_names", names=frappe.as_json(names))
