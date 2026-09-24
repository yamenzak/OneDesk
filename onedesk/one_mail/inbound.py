"""Mail arriving at an address on the mail domain.

The Worker (deploy/mail/worker.js) has already stored the message, as it
arrived, in R2 under this workspace's prefix, at `mail/in/<time>-<id>~<name>.eml`,
before anything here runs. Two things bring it in:
- **the notice** the Worker posts, signed with this workspace's secret, which
  only says "look now";
- **the sweep** every minute, which asks admin for anything after the last key
  read, and is what actually does the work.

A missed notice costs a minute, not a message.

Each message is parsed by Frappe's own `InboundMail` — charsets, inline
images, attachments, the reply chain — into a Communication on the hosted
account its name belongs to. The attachments are Files on it, in R2 like
every file. The original stays where the Worker put it, and the
Communication says where (`one_raw_key`), so "show original" and a re-parse
are always possible.
"""

import hashlib
import hmac
import time

import frappe
import requests
from frappe.email.receive import InboundMail, SentEmailInInboxError
from frappe.rate_limiter import rate_limit

from onedesk.one_mail import addresses, threads

#: Seconds a notice's timestamp may be off by.
SKEW = 300

#: Where the last key read is kept, so the sweep asks only for what is new.
LAST = "one_mail_last_key"


def signed(secret: str, at: str, body: bytes) -> str:
	"""The signature the Worker puts on a notice. Pure."""
	return hmac.new(secret.encode(), f"{at}.".encode() + body, hashlib.sha256).hexdigest()


def fresh(at: str, now: float | None = None) -> bool:
	"""Whether a notice's timestamp is recent enough to believe. Pure."""
	try:
		return abs((now or time.time()) - int(at)) <= SKEW
	except (TypeError, ValueError):
		return False


def name_in(key: str) -> str | None:
	"""The address name the Worker wrote into a key after the ~. Pure."""
	tail = (key or "").rsplit("/", 1)[-1]
	if "~" not in tail or not tail.endswith(".eml"):
		return None
	return tail.rsplit("~", 1)[1][: -len(".eml")] or None


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=600, seconds=60)
def notice():
	"""The Worker's "look now". Believed only with this workspace's signature;
	what it says is not trusted beyond that, since the sweep reads R2 itself."""
	secret = frappe.conf.get("one_mail_secret")
	body = frappe.request.get_data(cache=True)
	at = frappe.get_request_header("X-One-Timestamp") or ""
	offered = frappe.get_request_header("X-One-Signature") or ""
	if not secret or not fresh(at) or not hmac.compare_digest(signed(secret, at, body), offered):
		raise frappe.PermissionError
	frappe.enqueue(
		"onedesk.one_mail.inbound.sweep",
		queue="short",
		job_id="one_mail_sweep",
		deduplicate=True,
		enqueue_after_commit=True,
	)
	return "ok"


def sweep() -> int:
	"""Everything the Worker stored that has not been read, oldest first.
	Scheduled every minute, and enqueued by a notice."""
	from onedesk.one import account

	if not (account.configured() and frappe.conf.get("one_mail_secret")):
		return 0
	addresses.ensure_workspace()
	taken = 0
	while True:
		waiting = account.ask("onedesk.one_admin.proxy.mail_waiting", after=frappe.db.get_default(LAST))
		for item in waiting:
			try:
				take(item["key"])
				taken += 1
			except Exception:
				# One message that cannot be read must not hold up the rest. The
				# original is still in R2, and the error says which it was.
				frappe.db.rollback()
				frappe.log_error(title=f"OneMail could not read {item['key']}")
			frappe.db.set_default(LAST, item["key"])
			frappe.db.commit()
		if len(waiting) < 100:
			return taken


def take(key: str) -> str | None:
	"""One stored message, into a Communication. Taking it twice is taking it
	once."""
	from onedesk.one import account

	found = frappe.db.get_value("Communication", {"one_raw_key": key}, "name")
	if found:
		return found
	box = addresses.account_for(name_in(key) or "") or addresses.ensure_workspace()
	url = account.ask("onedesk.one_admin.proxy.storage_get", key=key)["url"]
	raw = requests.get(url, timeout=60)
	raw.raise_for_status()
	mail = Arrival(raw.content, frappe.get_doc("Email Account", box), key)
	try:
		made = mail.process()
	except SentEmailInInboxError:
		return None
	return made.name if made else None


class Arrival(InboundMail):
	"""Frappe's inbound mail, filed into OneMail's folder and thread."""

	def __init__(self, content, email_account, key: str):
		super().__init__(content, email_account)
		self.key = key

	def as_dict(self):
		data = super().as_dict()
		# References is oldest first; In-Reply-To, the parent, goes after it.
		references = " ".join(
			one for one in (self.mail.get("References"), self.mail.get("In-Reply-To")) if one
		)
		data.update(
			one_folder="INBOX",
			one_raw_key=self.key,
			one_references=references or None,
			one_thread=threads.thread_of(self.message_id, references),
		)
		return data
