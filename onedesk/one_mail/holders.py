"""Who holds which mailbox, which of them may send from it, and which one is
the workspace's.

To hold a mailbox is to have a `User Email` row for it, which lets them read
it; the row's `one_sends` says whether they may send from it too. A
workspace administrator chooses both for the workspace's mailbox and every
shared one, in OneMail's settings (Shared Mailboxes)."""

import json
import re

import frappe
from frappe import _

from onedesk.one import registry
from onedesk.one_mail import addresses

WORKSPACE = "one_mail_workspace"
SENDS_FROM = "one_mail_sends_from"

ORDER = ("Inbox", "Drafts", "Sent", "Archive", "Junk", "Trash", "Other")


def _ability(key: str) -> dict:
	from onedesk.one_mail import access as declared

	return next(one for one in declared.ABILITIES if one["key"] == key)


def may_do(key: str, user: str | None = None) -> bool:
	"""Whether somebody's roles let them do a workspace-wide thing in
	OneMail: connect shared mailboxes, set the address policy, keep the mail
	templates (one_mail/access.py)."""
	from onedesk.one import rights
	from onedesk.one_mail.access import DOCTYPE

	return rights.held(DOCTYPE, _ability(key)["all"], user)


def _admin(*keys: str) -> None:
	"""Refuse anyone whose roles allow none of `keys`."""
	if not any(may_do(key) for key in keys):
		frappe.throw(_("Your role doesn't allow this."), frappe.PermissionError)


def may_open_others() -> bool:
	"""Whether somebody's roles reach other people's mailboxes at all: any
	ability on every mailbox, or the address policy. What opens People's
	Mailboxes."""
	from onedesk.one_mail import access as declared

	return any(may_do(key) for key in (*declared.SHARED, "policy"))


def workspace() -> str | None:
	"""The workspace's mailbox, its Default Incoming: listed first, and where
	replies to the workspace's notifications come back to (one/notify.py)."""
	chosen = frappe.db.get_default(WORKSPACE)
	if chosen and frappe.db.exists("Email Account", chosen):
		return chosen
	return addresses.ensure_workspace()


def sends_from() -> str | None:
	"""The workspace's Default Outgoing: what the composer offers first. It is
	not frappe's `default_outgoing`, which stays One's own sender, so
	notifications never go out from a customer's address."""
	chosen = frappe.db.get_default(SENDS_FROM)
	if chosen and frappe.db.get_value("Email Account", chosen, "enable_outgoing"):
		return chosen
	ours = workspace()
	if ours and frappe.db.get_value("Email Account", ours, "enable_outgoing"):
		return ours
	return None


def system_sender() -> str | None:
	"""The address notifications go out from: frappe's default outgoing."""
	return frappe.db.get_value("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "email_id")


def may(account: str, key: str, user: str | None = None) -> bool:
	"""Whether somebody may change one part of a mailbox (`key`, one of
	one_mail/access.py SHARED): a mailbox they connected for themselves is
	theirs; any other through their roles (every mailbox, or for an ability
	with a scope, the address the workspace issued them), or through a share
	of that one mailbox. Workspace administrators may do everything, except
	in a private mailbox (addresses.is_private), which only its holder may."""
	from onedesk.one import rights, roles
	from onedesk.one_mail import actions
	from onedesk.one_mail.access import DOCTYPE

	user = user or frappe.session.user
	shared, hosted, email = frappe.db.get_value(
		"Email Account", account, ["one_shared", "one_hosted", "email_id"]
	) or (0, 0, "")
	holds = actions.owns(account, user)
	if not shared and not hosted and addresses.is_private(email):
		return bool(holds) or user == "Administrator"
	if user == "Administrator" or roles.administers(user):
		return True
	if holds and not shared and not hosted:
		return True
	one = _ability(key)
	if rights.may(DOCTYPE, one["all"], account, user):
		return True
	return bool(one.get("own") and holds and hosted and not shared and rights.held(DOCTYPE, one["own"], user))


def must(account: str, key: str) -> None:
	"""Refuse a reader who may not change this part of the mailbox."""
	if not may(account, key):
		email = frappe.db.get_value("Email Account", account, "email_id") or account
		frappe.throw(_("Your role doesn't allow changing this on {0}.").format(email), frappe.PermissionError)


def may_manage(account: str) -> bool:
	"""Whether the reader may change any part of a mailbox: what opens its
	settings to them."""
	from onedesk.one_mail.access import SHARED

	return any(may(account, key) for key in SHARED)


def mays(account: str) -> dict:
	"""{key: 0/1} for every part of a mailbox, for its settings' tabs."""
	from onedesk.one_mail.access import SHARED

	return {key: int(may(account, key)) for key in SHARED}


def issued_to_them(account: str) -> bool:
	"""Whether the mailbox is the reader's own address from the workspace,
	whose rules they may not change: a rule they make on it waits for
	whoever may (rules.save_rule)."""
	from onedesk.one_mail import actions

	shared, hosted = frappe.db.get_value("Email Account", account, ["one_shared", "one_hosted"]) or (0, 0)
	return bool(hosted and not shared and actions.holds(account) and not may(account, "rules"))


def sees(account: str):
	"""Refuse a reader who neither holds nor may change this mailbox."""
	from onedesk.one_mail import actions

	if not (actions.holds(account) or may_manage(account)):
		actions.require(account)


def may_sign(account: str) -> bool:
	"""Whether the reader may change how a mailbox signs: one that sends."""
	return bool(frappe.db.get_value("Email Account", account, "enable_outgoing")) and may(account, "signature")


def sending_rows(user: str | None = None) -> dict:
	"""The mailboxes `user` holds, and whether each holding lets them send."""
	return {
		row.email_account: row.one_sends is None or bool(row.one_sends)
		for row in frappe.get_all(
			"User Email", filters={"parent": user or frappe.session.user}, fields=["email_account", "one_sends"]
		)
	}


def may_send(account: str, user: str | None = None) -> bool:
	"""Whether `user` may send from `account`: it sends, they hold it, and
	their holding lets them."""
	if not frappe.db.get_value("Email Account", account, "enable_outgoing"):
		return False
	return bool(sending_rows(user).get(account))


def first_line(html: str | None) -> str:
	"""A signature's first line of text, to show what a mailbox signs with.
	Pure."""
	from frappe.utils import strip_html

	text = re.sub(r"<\s*/?(br|p|div|li)\b[^>]*>", "\n", html or "", flags=re.I)
	return next((line.strip() for line in strip_html(text).splitlines() if line.strip()), "")


def ordered(folders: list[dict]) -> list[dict]:
	"""The usual folders first, then the rest by path. Pure."""
	return sorted(
		folders, key=lambda one: (ORDER.index(one.get("kind") or "Other"), (one.get("path") or "").lower())
	)


@frappe.whitelist()
def mailboxes() -> list[dict]:
	"""The reader's mailboxes, with their folders: the workspace's first, then
	the other shared ones, then their own."""
	rows = sending_rows()
	held = list(rows)
	if not held:
		return []
	ours, sends = workspace(), sends_from()
	accounts = frappe.get_all("Email Account", filters={"name": ["in", held]}, fields=BOX_FIELDS)
	folders: dict[str, list] = {}
	for row in frappe.get_all(
		"Mail Folder",
		filters={"account": ["in", held], "hidden": 0},
		fields=["name", "account", "path", "label", "kind", "unread", "total", "delimiter"],
	):
		folders.setdefault(row.account, []).append(row)
	out = []
	for account in accounts:
		listed = ordered(folders.get(account.name, []))
		out.append(_box(account, rows, ours, listed, sends))
	return sorted(out, key=lambda one: (-one["workspace"], -one["shared"], one["email"]))


BOX_FIELDS = [
	"name",
	"email_id",
	"one_hosted",
	"one_connected",
	"one_shared",
	"enable_outgoing",
	"one_error",
	"one_intake",
	"signature",
]


def _box(account, rows: dict, ours: str | None, listed: list, sends: str | None = None) -> dict:
	"""What OneMail shows of one mailbox to the reader."""
	from onedesk.one_mail import rules

	return {
		"name": account.name,
		"email": account.email_id,
		"hosted": account.one_hosted,
		"connected": account.one_connected,
		"shared": account.one_shared,
		"private": int(bool(account.one_connected and not account.one_shared and addresses.is_private(account.email_id))),
		"workspace": int(account.name == ours),
		"sends": int(bool(account.enable_outgoing and rows.get(account.name))),
		"sends_default": int(account.name == sends),
		"error": account.one_error,
		"intake": account.one_intake,
		"receives_only": int(bool(account.one_hosted and not account.enable_outgoing)),
		"may_sign": int(may_sign(account.name)),
		"replies": int(rules.replies(account.name)),
		"signed": first_line(account.signature),
		"may": (held := mays(account.name)),
		"may_manage": int(any(held.values())),
		"may_reconnect": int(bool(account.one_connected) and held["connection"]),
		"unread": sum(one.unread or 0 for one in listed if one.kind in ("Inbox", "Other")),
		"folders": listed,
		"away": None if account.one_shared else rules.away_state(account.name),
		"covering_until": frappe.db.get_value(
			"User Email", {"parent": frappe.session.user, "email_account": account.name}, "one_cover_until"
		),
	}


@frappe.whitelist()
def mailbox(account: str) -> dict:
	"""One mailbox as mailboxes() describes it, also to an administrator
	who manages a shared one without holding it."""
	sees(account)
	row = frappe.db.get_value("Email Account", account, BOX_FIELDS, as_dict=True)
	return _box(row, sending_rows(), workspace(), [], sends_from())


def _by_role(user: str) -> dict:
	"""A person's OneMail role (one/access.py), and the parts of any mailbox
	(one_mail/access.py SHARED) it already lets them change, which a
	share of one mailbox can add nothing to."""
	from onedesk.one import access, rights, roles
	from onedesk.one.people import level_of
	from onedesk.one_mail.access import DOCTYPE, SHARED

	cache = frappe.local.flags.setdefault("one_mail_by_role", {})
	if user not in cache:
		if roles.administers(user):
			cache[user] = {"role": _("Administrator"), "covered": list(SHARED)}
		else:
			used, managed = access._apps()[registry.name("one_mail")]
			tier = level_of(set(frappe.get_roles(user)), used, managed, access.levels_of(registry.name("one_mail")))
			cache[user] = {
				"role": _(tier) if tier in ("User", "Manager", "None") else tier,
				"covered": [key for key in SHARED if rights.held(DOCTYPE, _ability(key)["all"], user)],
			}
	return cache[user]


@frappe.whitelist()
def shared() -> dict:
	"""The workspace's mailboxes, who reads and who sends from each, and
	whether people may send from their own address: OneMail's settings,
	for whoever's role reaches the workspace's mailboxes."""
	if not (may_do("connect_shared") or may_open_others()):
		_admin("connect_shared", "policy")
	accounts = frappe.get_all(
		"Email Account",
		filters={"one_shared": 1},
		fields=["name", "email_id", "one_hosted", "one_connected", "enable_outgoing"],
		order_by="email_id asc",
	)
	from onedesk.one import rights

	ours, sends = workspace(), sends_from()
	names = dict(frappe.get_all("User", filters={"user_type": "System User"}, fields=["name", "full_name"], as_list=True))
	for account in accounts:
		given = rights.grants(registry.name("one_mail"), account.name)
		account["people"] = [
			{
				"user": row.parent,
				"name": names.get(row.parent) or row.parent,
				"sends": int(row.one_sends is None or bool(row.one_sends)),
				"may": given.get(row.parent, []),
				**_by_role(row.parent),
			}
			for row in frappe.get_all(
				"User Email",
				filters={"email_account": account.name},
				fields=["parent", "one_sends"],
				order_by="parent asc",
			)
		]
		account["workspace"] = int(account.name == ours)
		account["sends_default"] = int(account.name == sends)
	accounts.sort(key=lambda one: -one["workspace"])
	from onedesk.one_mail import access as declared

	return {
		"mailboxes": accounts,
		"abilities": [
			{"key": one["key"], "label": str(one["label"])} for one in declared.ABILITIES if one["key"] in declared.SHARED
		],
		"personal_sends": int(addresses.personal_sends()),
		"allowed_domains": addresses.allowed_domains(),
		"external": int(addresses.external()),
		"mail_domain": addresses.domain(),
		"slug": addresses.slug(),
		"system_sender": system_sender(),
	}


@frappe.whitelist()
def addresses_of_people() -> list[dict]:
	"""Every person's System and Organization mailboxes, the address the
	workspace issued them and those they connected at the company's domains,
	with whose it is: what a Mail Manager opens to set a signature, a sender
	name or an away reply for somebody. A private one (addresses.is_private)
	is never listed."""
	if not may_open_others():
		_admin("policy")
	held = {
		row.email_account: row.parent
		for row in frappe.get_all("User Email", fields=["email_account", "parent"], order_by="parent asc")
	}
	names = dict(frappe.get_all("User", filters={"user_type": "System User"}, fields=["name", "full_name"], as_list=True))
	out = []
	company = addresses.company_domains()
	for account in frappe.get_all(
		"Email Account",
		filters={"one_shared": 0, "name": ["in", list(held) or [""]]},
		fields=["name", "email_id", "one_hosted", "one_connected", "enable_outgoing"],
		order_by="email_id asc",
	):
		if not account.one_hosted and addresses.domain_of(account.email_id) not in company:
			continue
		user = held[account.name]
		out.append(
			{
				"name": account.name,
				"email": account.email_id,
				"issued": int(bool(account.one_hosted)),
				"sends": int(bool(account.enable_outgoing)),
				"user": user,
				"full_name": names.get(user) or user,
			}
		)
	return sorted(out, key=lambda one: (one["full_name"].lower(), -one["issued"]))


@frappe.whitelist(methods=["POST"])
def set_access(account: str, people) -> list[dict]:
	"""Exactly these people hold one of the workspace's mailboxes, each
	reading it and, where `sends`, sending from it: [{user, sends}]. Who
	no longer holds it loses what they were given in it too."""
	must(account, "holders")
	if not frappe.db.get_value("Email Account", account, "one_shared"):
		frappe.throw(_("{0} is a personal mailbox and can't be shared.").format(account))
	rows = json.loads(people) if isinstance(people, str) else people or []
	wanted = {row["user"]: int(bool(row.get("sends"))) for row in rows if row.get("user")}
	for user in wanted:
		if not frappe.db.get_value("User", {"name": user, "enabled": 1, "user_type": "System User"}):
			frappe.throw(_("{0} isn't in this workspace.").format(user))
	now = set(frappe.get_all("User Email", filters={"email_account": account}, pluck="parent"))
	for user in set(wanted) - now:
		addresses.hold(account, user)
	from onedesk.one import rights

	for user in now - set(wanted):
		frappe.db.delete("User Email", {"parent": user, "email_account": account})
		rights.grant(registry.name("one_mail"), account, user, [])
	for user, sends in wanted.items():
		frappe.db.set_value("User Email", {"parent": user, "email_account": account}, "one_sends", sends, update_modified=False)
	from onedesk.one_mail import tell

	tell.mailbox_shared(account, sorted(set(wanted) - now))
	frappe.publish_realtime("one_mailbox", after_commit=True)
	return [{"user": user, "sends": sends} for user, sends in sorted(wanted.items())]


@frappe.whitelist(methods=["POST"])
def give(account: str, user: str, keys: str | list) -> list[str]:
	"""What one person who holds a mailbox may change in it, beyond what
	their role allows: [key, ...] of one_mail/access.py SHARED, kept as a
	share of the mailbox (one/rights.py grant)."""
	from onedesk.one import rights

	must(account, "holders")
	if not frappe.db.exists("User Email", {"parent": user, "email_account": account}):
		frappe.throw(_("{0} doesn't use this mailbox.").format(user))
	keys = frappe.parse_json(keys) if isinstance(keys, str) else keys or []
	return rights.grant(registry.name("one_mail"), account, user, list(keys))


@frappe.whitelist(methods=["POST"])
def grant(account: str, user: str, sends: int = 1) -> None:
	"""One person reads one of the workspace's mailboxes, and with `sends`
	sends from it too; given again, only `sends` changes."""
	rows = {row["user"]: row["sends"] for row in _people(account)}
	rows[user] = int(bool(int(sends)))
	set_access(account, [{"user": one, "sends": on} for one, on in rows.items()])


@frappe.whitelist(methods=["POST"])
def revoke(account: str, user: str) -> None:
	"""One person no longer reads one of the workspace's mailboxes."""
	set_access(account, [row for row in _people(account) if row["user"] != user])


def _people(account: str) -> list[dict]:
	return [
		{"user": row.parent, "sends": int(row.one_sends is None or bool(row.one_sends))}
		for row in frappe.get_all("User Email", filters={"email_account": account}, fields=["parent", "one_sends"])
	]


@frappe.whitelist(methods=["POST"])
def set_personal_sends(on: int) -> int:
	"""Whether the address given to each new person sends as well as
	receives. An address already given keeps its own (set_sends)."""
	_admin("policy")
	on = int(bool(int(on)))
	frappe.db.set_default(addresses.PERSONAL_SENDS, str(on))
	return on


@frappe.whitelist(methods=["POST"])
def set_sends(account: str, on: int) -> int:
	"""Whether one person's workspace address sends as well as receives."""
	_admin("policy")
	if not frappe.db.get_value("Email Account", account, "one_hosted") or frappe.db.get_value(
		"Email Account", account, "one_shared"
	):
		frappe.throw(_("{0} is not a workspace address.").format(account))
	on = int(bool(int(on)))
	frappe.db.set_value("Email Account", account, "enable_outgoing", on, update_modified=False)
	frappe.publish_realtime("one_mailbox", after_commit=True)
	return on


@frappe.whitelist(methods=["POST"])
def set_external(on: int) -> int:
	"""Whether people may connect a mailbox of their own. Mailboxes already
	connected stay connected."""
	_admin("policy")
	on = int(bool(int(on)))
	frappe.db.set_default(addresses.EXTERNAL, str(on))
	return on


@frappe.whitelist(methods=["POST"])
def set_allowed_domains(domains) -> list[str]:
	"""The domains people may connect a personal mailbox at; an empty list
	lets them connect any. A shared mailbox, an administrator's, is not held
	to it."""
	_admin("policy")
	rows = json.loads(domains) if isinstance(domains, str) else domains or []
	clean = []
	for one in rows:
		domain = addresses.domain_of(one)
		if not re.fullmatch(r"[a-z0-9-]+(\.[a-z0-9-]+)+", domain):
			frappe.throw(_("{0} isn't a domain, such as gmail.com.").format(one))
		if domain not in clean:
			clean.append(domain)
	frappe.db.set_default(addresses.ALLOWED_DOMAINS, ",".join(clean))
	return clean


def sending(doc, method=None) -> None:
	"""Communication before_insert: a person sends only from a mailbox they
	may send from. Mail the workspace sends on its own (no person behind the
	request) is not theirs to refuse."""
	if doc.communication_medium != "Email" or doc.sent_or_received != "Sent":
		return
	user = frappe.session.user
	if user in ("Administrator", "Guest") or not getattr(frappe.local, "request", None) or frappe.flags.in_import:
		return
	account = doc.email_account
	if not account and doc.sender:
		from email.utils import parseaddr

		account = frappe.db.get_value("Email Account", {"email_id": parseaddr(doc.sender)[1]}, "name")
	if not account:
		return
	managed = frappe.db.get_value("Email Account", account, ["one_hosted", "one_connected"]) or (0, 0)
	if any(managed) and not may_send(account, user):
		frappe.throw(
			_("You don't have Send access to {0}.").format(
				frappe.db.get_value("Email Account", account, "email_id")
			),
			frappe.PermissionError,
		)


@frappe.whitelist(methods=["POST"])
def set_defaults(incoming: str | None = None, outgoing: str | None = None) -> dict:
	"""The workspace's Default Incoming and Default Outgoing, each one of its
	shared mailboxes. Neither moves frappe's `default_outgoing`."""
	_admin("policy")
	for account in (incoming, outgoing):
		if account and not frappe.db.get_value("Email Account", account, "one_shared"):
			frappe.throw(_("{0} is not a shared mailbox.").format(account))
	if outgoing and not frappe.db.get_value("Email Account", outgoing, "enable_outgoing"):
		frappe.throw(_("Enable Outgoing is disabled for {0}.").format(outgoing))
	if incoming:
		frappe.db.set_default(WORKSPACE, incoming)
	if outgoing:
		frappe.db.set_default(SENDS_FROM, outgoing)
	return {"incoming": workspace(), "outgoing": sends_from()}


@frappe.whitelist()
def signature_of(account: str) -> str | None:
	"""A mailbox's signature: the address's, whoever writes from it."""
	sees(account)
	return frappe.db.get_value("Email Account", account, "signature")


@frappe.whitelist(methods=["POST"])
def set_signature(account: str, signature: str | None = None) -> None:
	"""Change a mailbox's signature: whoever may (may, "signature")."""
	if not frappe.db.get_value("Email Account", account, "enable_outgoing"):
		frappe.throw(_("Enable Outgoing is disabled for {0}.").format(account))
	must(account, "signature")
	frappe.db.set_value(
		"Email Account",
		account,
		{"signature": signature or None, "add_signature": int(bool((signature or "").strip()))},
		update_modified=False,
	)


def signed(doc, method=None) -> None:
	"""Email Account validate: a mailbox with a signature signs its mail, and
	one without signs nothing, however the signature was changed."""
	doc.add_signature = int(bool((doc.signature or "").strip()))


@frappe.whitelist()
def signature_for(email: str) -> str | None:
	"""The signature of the address the composer sends from, if the writer
	holds it. Email Account itself is not readable to them."""
	account = frappe.db.get_value(
		"Email Account", {"email_id": email, "add_signature": 1}, ["name", "signature"], as_dict=True
	)
	if not account or not frappe.db.exists(
		"User Email", {"parent": frappe.session.user, "email_account": account.name}
	):
		return None
	from onedesk.one_mail import signatures

	return signatures.written(account.signature) or None
