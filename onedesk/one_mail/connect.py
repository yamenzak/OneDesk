"""A mailbox somebody already has, connected by its address and password.

What a person types is an address and a password. The servers are found for
them, first match wins:
1. an `Email Domain` a workspace administrator set up for the address's domain;
2. the well-known providers in `KNOWN`;
3. a guess, `imap.<domain>` then `mail.<domain>`, on the standard ports.
Anything found is tried before it is kept. Somebody whose server is none of
these types it in, and that is tried the same way.

A connected mailbox is an `Email Account` with `one_connected`, and
`enable_incoming` left off: Frappe's own pull reads one folder and marks what
it reads, and sync.py reads every folder and changes nothing. The person who
connects it holds it, through a `User Email` row, as Frappe's own inbox does.
"""

import imaplib
import ssl

import frappe
from frappe import _

from onedesk.one_mail import addresses, imap

#: Providers everyone uses: domain -> (imap host, smtp host, smtp port).
#: Ports 993 for IMAP; SMTP on 465 is SSL, on 587 is STARTTLS.
KNOWN = {
	"gmail.com": ("imap.gmail.com", "smtp.gmail.com", 587),
	"googlemail.com": ("imap.gmail.com", "smtp.gmail.com", 587),
	"outlook.com": ("outlook.office365.com", "smtp-mail.outlook.com", 587),
	"hotmail.com": ("outlook.office365.com", "smtp-mail.outlook.com", 587),
	"live.com": ("outlook.office365.com", "smtp-mail.outlook.com", 587),
	"msn.com": ("outlook.office365.com", "smtp-mail.outlook.com", 587),
	"yahoo.com": ("imap.mail.yahoo.com", "smtp.mail.yahoo.com", 465),
	"icloud.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
	"me.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
	"mac.com": ("imap.mail.me.com", "smtp.mail.me.com", 587),
	"gmx.net": ("imap.gmx.net", "mail.gmx.net", 587),
	"gmx.de": ("imap.gmx.net", "mail.gmx.net", 587),
	"gmx.com": ("imap.gmx.com", "mail.gmx.com", 587),
	"web.de": ("imap.web.de", "smtp.web.de", 587),
	"fastmail.com": ("imap.fastmail.com", "smtp.fastmail.com", 465),
	"zoho.com": ("imap.zoho.com", "smtp.zoho.com", 465),
	"yandex.com": ("imap.yandex.com", "smtp.yandex.com", 465),
}

#: SMTP servers that file what they send in Sent themselves; appending a copy
#: there would show every message twice.
FILES_ITS_OWN = {"smtp.gmail.com", "smtp-mail.outlook.com", "smtp.office365.com"}

#: Seconds each guess is given to answer.
GUESS_PATIENCE = 10


def candidates(address: str) -> list[dict]:
	"""Where the servers for an address might be, most likely first. Pure
	apart from reading Email Domain."""
	domain = address.rsplit("@", 1)[-1].lower()
	out = []
	configured = frappe.db.get_value(
		"Email Domain",
		{"domain_name": domain},
		[
			"email_server",
			"incoming_port",
			"use_ssl",
			"use_starttls",
			"smtp_server",
			"smtp_port",
			"use_tls",
			"use_ssl_for_outgoing",
		],
		as_dict=True,
	)
	if configured and configured.email_server:
		out.append(
			{
				"email_server": configured.email_server,
				"incoming_port": int(configured.incoming_port or (993 if configured.use_ssl else 143)),
				"use_ssl": int(configured.use_ssl),
				"use_starttls": int(configured.use_starttls),
				"smtp_server": configured.smtp_server,
				"smtp_port": int(configured.smtp_port or 587),
				"use_tls": int(configured.use_tls),
				"use_ssl_for_outgoing": int(configured.use_ssl_for_outgoing),
			}
		)
	return out + guesses(domain)


def guesses(domain: str) -> list[dict]:
	"""The providers' servers, or the usual names. Pure."""

	def server(incoming, outgoing, port):
		return {
			"email_server": incoming,
			"incoming_port": 993,
			"use_ssl": 1,
			"use_starttls": 0,
			"smtp_server": outgoing,
			"smtp_port": port,
			"use_tls": int(port == 587),
			"use_ssl_for_outgoing": int(port == 465),
		}

	if domain in KNOWN:
		return [server(*KNOWN[domain])]
	return [server(f"imap.{domain}", f"smtp.{domain}", 587), server(f"mail.{domain}", f"mail.{domain}", 587)]


def _stand_in(address: str, password: str, login: str | None, where: dict):
	"""An unsaved Email Account, enough for imap.Session to dial."""
	doc = frappe.new_doc("Email Account")
	doc.update({"email_id": address, "login_id": login, "use_imap": 1, **where})
	doc.get_password = lambda *args, **kwargs: password
	return doc


def reach(address: str, password: str, login: str | None = None, where: dict | None = None) -> dict:
	"""The first of the candidates that lets this address in. Raises with what
	to tell the person when none does."""
	tried = [where] if where else candidates(address)
	last = None
	for one in tried:
		try:
			with imap.Session(
				_stand_in(address, password, login, one), patience=GUESS_PATIENCE if not where else None
			):
				return one
		except (imaplib.IMAP4.error, OSError, ssl.SSLError) as error:
			last = error
			# A server that answered and refused the password is the right
			# server: trying the next guess would only hide why.
			if isinstance(error, imaplib.IMAP4.error):
				break
	frappe.throw(imap.refused(last) if last else _("No mail server was found for {0}.").format(address))


@frappe.whitelist(methods=["POST"])
def connect(
	email: str,
	password: str,
	login: str | None = None,
	email_server: str | None = None,
	incoming_port: int | None = None,
	use_ssl: int = 1,
	smtp_server: str | None = None,
	smtp_port: int | None = None,
	sends: int = 1,
	shared: int = 0,
) -> str:
	"""Connect a mailbox the reader holds. With no server named, one is found.
	With `shared`, it is the workspace's, such as sales@, and a workspace
	administrator chooses who else holds it (holders.py)."""
	from frappe.utils import validate_email_address

	from onedesk.one import roles

	if int(shared):
		frappe.only_for(roles.ADMINISTRATOR)
	email = (validate_email_address(email or "", throw=True) or "").strip().lower()
	if frappe.db.exists("Email Account", {"email_id": email}):
		frappe.throw(_("{0} is already connected.").format(email))
	where = None
	if email_server:
		ssl_in = int(use_ssl)
		port_out = int(smtp_port or 587)
		where = {
			"email_server": email_server,
			"incoming_port": int(incoming_port or (993 if ssl_in else 143)),
			"use_ssl": ssl_in,
			"use_starttls": 0,
			"smtp_server": smtp_server or email_server,
			"smtp_port": port_out,
			"use_tls": int(port_out == 587),
			"use_ssl_for_outgoing": int(port_out == 465),
		}
	found = reach(email, password, login, where)
	doc = frappe.get_doc(
		{
			"doctype": "Email Account",
			"email_account_name": email,
			"email_id": email,
			"login_id_is_different": int(bool(login)),
			"login_id": login,
			"password": password,
			"one_connected": 1,
			"one_shared": int(bool(int(shared))),
			"use_imap": 1,
			"enable_incoming": 0,
			"enable_outgoing": int(sends),
			"append_emails_to_sent_folder": int(found["smtp_server"] not in FILES_ITS_OWN),
			**found,
		}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	addresses.hold(doc.name, frappe.session.user)
	frappe.enqueue(
		"onedesk.one_mail.sync.sync_account",
		queue="long",
		job_id=f"one_mail_sync:{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
		account=doc.name,
	)
	return doc.name


#: What an Email Account keeps of where its servers are, as `reach` takes it.
WHERE = (
	"email_server",
	"incoming_port",
	"use_ssl",
	"use_starttls",
	"smtp_server",
	"smtp_port",
	"use_tls",
	"use_ssl_for_outgoing",
)


@frappe.whitelist(methods=["POST"])
def reconnect(account: str, password: str, login: str | None = None) -> str:
	"""A connected mailbox that stopped letting us in, given its password
	again: tried on the servers it already has before it is kept, then read
	again at once. The workspace's are a workspace administrator's, as
	connecting one is."""
	from onedesk.one import roles
	from onedesk.one_mail import actions

	actions.require(account)
	doc = frappe.get_doc("Email Account", account)
	if not doc.one_connected:
		frappe.throw(_("Only a mailbox connected from another provider has a password to give again."))
	if doc.one_shared:
		frappe.only_for(roles.ADMINISTRATOR)
	login = (login or "").strip() or (doc.login_id if doc.login_id_is_different else None)
	reach(doc.email_id, password, login, {key: doc.get(key) for key in WHERE})
	doc.update({"password": password, "login_id_is_different": int(bool(login)), "login_id": login})
	doc.one_error = None
	doc.flags.ignore_permissions = True
	doc.save()
	frappe.enqueue(
		"onedesk.one_mail.sync.sync_account",
		queue="long",
		job_id=f"one_mail_sync:{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
		account=doc.name,
	)
	from onedesk.one_mail import sync

	sync.told(doc.name)
	return doc.name


@frappe.whitelist(methods=["POST"])
def disconnect(account: str) -> None:
	"""Stop reading a connected mailbox. What was read stays, linked to what
	it was linked to; only the account and its folders go."""
	from onedesk.one_mail import actions

	actions.require(account)
	connected, shared = frappe.db.get_value("Email Account", account, ["one_connected", "one_shared"])
	if shared:
		from onedesk.one import roles

		frappe.only_for(roles.ADMINISTRATOR)
	if not connected:
		frappe.throw(_("Only a connected mailbox can be disconnected."))
	frappe.db.set_value("Communication", {"email_account": account}, {"uid": 0}, update_modified=False)
	frappe.db.delete("Mail Folder", {"account": account})
	frappe.delete_doc("Email Account", account, ignore_permissions=True, force=True)
