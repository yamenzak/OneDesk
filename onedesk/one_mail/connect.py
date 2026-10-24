"""A mailbox somebody already has, connected by its address and password.
The servers are found for them, and each is tried before it is kept."""

import imaplib
import smtplib
import ssl

import frappe
from frappe import _

from onedesk.one_mail import addresses, imap

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

FILES_ITS_OWN = {"smtp.gmail.com", "smtp-mail.outlook.com", "smtp.office365.com"}

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
			if isinstance(error, imaplib.IMAP4.error):
				break
	frappe.throw(imap.refused(last) if last else _("Couldn't find a mail server for {0}.").format(address))


def _smtp(address: str, password: str, login: str | None, where: dict):
	"""Sign in to the outgoing server and leave. Raises smtplib's errors."""
	dial = smtplib.SMTP_SSL if int(where["use_ssl_for_outgoing"]) else smtplib.SMTP
	with dial(where["smtp_server"], int(where["smtp_port"]), timeout=GUESS_PATIENCE) as session:
		if int(where["use_tls"]):
			session.starttls(context=ssl.create_default_context())
		session.login(login or address, password)


def sends_through(address: str, password: str, login: str | None, where: dict, guessed: bool = True) -> dict:
	"""The outgoing server that lets this address send. A guessed server is
	also tried on the other usual port. Raises with what to tell the person
	when none does, rather than frappe's own check on save failing later."""
	tried = [where]
	if guessed:
		other = 465 if int(where["smtp_port"]) == 587 else 587
		tried.append({**where, "smtp_port": other, "use_tls": int(other == 587), "use_ssl_for_outgoing": int(other == 465)})
	last = None
	for one in tried:
		try:
			_smtp(address, password, login, one)
			return one
		except smtplib.SMTPAuthenticationError as error:
			last = error
			break
		except (smtplib.SMTPException, OSError, ssl.SSLError) as error:
			last = error
	reason = (
		_("The server rejected the email address or password.")
		if isinstance(last, smtplib.SMTPAuthenticationError)
		else imap.refused(last)
	)
	frappe.throw(
		_("Couldn't send through {0}. {1} Fill in Server, or turn off Enable Outgoing.").format(
			where["smtp_server"], reason
		)
	)


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

	if int(shared):
		from onedesk.one_mail import holders

		holders._admin("connect_shared")
	email = (validate_email_address(email or "", throw=True) or "").strip().lower()
	allowed = addresses.allowed_domains()
	if not int(shared) and not addresses.external():
		frappe.throw(_("External mailboxes are disabled in this workspace."))
	if not int(shared) and allowed and addresses.domain_of(email) not in allowed:
		frappe.throw(_("Only mailboxes at {0} can be connected.").format(", ".join("@" + one for one in allowed)))
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
	if int(sends):
		found = sends_through(email, password, login, found, guessed=not where)
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
	again at once: whoever may (holders.may, "connection")."""
	from onedesk.one_mail import holders

	holders.must(account, "connection")
	doc = frappe.get_doc("Email Account", account)
	if not doc.one_connected:
		frappe.throw(_("Only a connected mailbox has a password to update."))
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
	from onedesk.one_mail import holders

	connected = frappe.db.get_value("Email Account", account, "one_connected")
	holders.must(account, "connection")
	if not connected:
		frappe.throw(_("Only a connected mailbox can be disconnected."))
	frappe.db.set_value("Communication", {"email_account": account}, {"uid": 0}, update_modified=False)
	frappe.db.delete("Mail Folder", {"account": account})
	frappe.delete_doc("Email Account", account, ignore_permissions=True, force=True)
