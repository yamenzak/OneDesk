"""OneMail: addresses on the mail domain, and the mail that arrives at them."""

import ast
import hashlib
import hmac
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

MAIL = tree.APP / "one_mail"
WORKER = (tree.ROOT / "deploy" / "mail" / "worker.js").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def _load(path: Path, names: tuple, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_an_address_belongs_to_the_workspace_after_its_last_dot():
	space = _load(MAIL / "addresses.py", ("NAME", "RESERVED", "is_name", "is_workspace_name"), re=re)
	mine = space["is_workspace_name"]
	assert mine("acme", "acme") and mine("ahmad.acme", "acme") and mine("AHMAD.acme", "acme")
	assert not mine("ahmad.other", "acme")
	assert not mine("x.ahmad.acme", "acme"), "a person's part has no dot"
	assert not mine("postmaster.acme", "acme"), "reserved"
	assert not mine("acme", ""), "no workspace, no address"
	assert not mine(".acme", "acme")


def test_a_notice_is_believed_only_signed_and_fresh():
	space = _load(
		MAIL / "inbound.py",
		("SKEW", "signed", "fresh", "name_in"),
		hmac=hmac,
		hashlib=hashlib,
		time=__import__("time"),
	)
	body = b'{"key":"mail/in/1~acme.eml"}'
	expected = hmac.new(b"s", b"100." + body, hashlib.sha256).hexdigest()
	assert space["signed"]("s", "100", body) == expected
	assert space["fresh"]("1000", now=1100) and not space["fresh"]("1000", now=2000)
	assert not space["fresh"]("soon") and not space["fresh"](None)


def test_the_key_says_which_address_a_message_came_to():
	name_in = _load(MAIL / "inbound.py", ("name_in",))["name_in"]
	assert name_in("mail/in/20260924-uuid~ahmad.acme.eml") == "ahmad.acme"
	assert name_in("tenants/acme/mail/in/1-u~acme.eml") == "acme"
	assert name_in("mail/in/1-u.eml") is None
	assert "~${bare}.eml" in WORKER, "the Worker writes what name_in reads"


def test_a_thread_is_a_message_id_never_a_subject():
	space = _load(MAIL / "threads.py", ("MESSAGE_ID", "ids", "pick"), re=re)
	assert space["ids"]("<a@x> <b@y>\n <c@z>") == ["a@x", "b@y", "c@z"]
	assert space["pick"](["a@x", "b@y"], {"b@y": "root@x"}) == "root@x"
	assert space["pick"](["a@x"], {}) is None
	assert "subject" not in (MAIL / "threads.py").read_text().split('"""', 2)[2].lower()


def test_mail_is_read_from_r2_every_minute_whatever_the_notice_did():
	assert '"* * * * *": ["onedesk.one_mail.inbound.sweep"' in HOOKS
	source = (MAIL / "inbound.py").read_text()
	assert "raise frappe.PermissionError" in source and "hmac.compare_digest" in source
	assert '{"one_raw_key": key}' in source, "taking one twice is taking it once"


def test_admin_names_only_a_workspaces_own_addresses():
	proxy = (tree.APP / "one_admin" / "proxy.py").read_text()
	assert "addresses.is_workspace_name(one, tenant.slug)" in proxy
	assert "storage.mail_waiting(_tenant_doc(caller()), after)" in proxy


def test_kv_values_are_sent_as_multipart_not_a_form():
	source = (tree.APP / "one_admin" / "cloudflare.py").read_text()
	assert 'files={"value": (None, data), "metadata": (None, "{}")}' in source
	assert 'data={"value": data' not in source


def test_a_reply_carries_its_whole_ancestry_in_references():
	threads = _load(MAIL / "threads.py", ("MESSAGE_ID", "ids"), re=re)
	space = _load(
		MAIL / "outbound.py", ("KEPT", "chain"), threads=type("T", (), {"ids": staticmethod(threads["ids"])})
	)
	assert space["chain"]("c@x", "<a@x> <b@x>") == ["a@x", "b@x", "c@x"]
	assert space["chain"]("c@x", None) == ["c@x"]
	assert space["chain"]("b@x", "<a@x> <b@x>") == ["a@x", "b@x"], "the parent once"
	long = " ".join(f"<{n}@x>" for n in range(40))
	assert len(space["chain"]("z@x", long)) == space["KEPT"]


def test_a_workspace_sends_only_as_itself():
	import types

	addresses = _load(MAIL / "addresses.py", ("NAME", "RESERVED", "is_name", "is_workspace_name"), re=re)
	fake = types.ModuleType("onedesk.one_mail.addresses")
	fake.is_workspace_name = addresses["is_workspace_name"]
	stood_in = {
		name: sys.modules.get(name) for name in ("onedesk", "onedesk.one_mail", "onedesk.one_mail.addresses")
	}
	sys.modules.setdefault("onedesk", types.ModuleType("onedesk"))
	sys.modules.setdefault("onedesk.one_mail", types.ModuleType("onedesk.one_mail"))
	sys.modules["onedesk.one_mail.addresses"] = fake
	try:
		_check_allowed()
	finally:
		for name, was in stood_in.items():
			if was is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = was


def _check_allowed():
	allowed = _load(tree.APP / "one_admin" / "mailing.py", ("allowed",))["allowed"]
	assert allowed("acme@m.4dl.app", "acme", "m.4dl.app")
	assert allowed("Ahmad.Acme@M.4dl.app", "acme", "m.4dl.app")
	assert not allowed("ceo@m.4dl.app", "acme", "m.4dl.app")
	assert not allowed("acme@4dl.app", "acme", "m.4dl.app")
	assert not allowed("acme@m.4dl.app.evil.com", "acme", "m.4dl.app")


def test_sends_are_counted_atomically_and_refused_softly():
	source = (tree.APP / "one_admin" / "mailing.py").read_text()
	assert "frappe.cache.incrby(key, 1)" in source and "raise faults.Again(" in source
	assert "LARGEST = 5 * 1024 * 1024" in source


def test_every_email_goes_through_our_transport():
	assert 'override_email_send = "onedesk.one_mail.outbound.send"' in HOOKS
	assert '"before_insert": "onedesk.one_mail.outbound.file_sent"' in HOOKS
	outbound = (MAIL / "outbound.py").read_text()
	assert 'account.get("one_hosted")' in outbound and "server.session.sendmail(" in outbound


# ------------------------------------------------------------------ connected mailboxes

IMAP_NAMES = (
	"LISTED",
	"SPECIAL",
	"REPEATS",
	"BY_NAME",
	"parse_list",
	"kind_of",
	"repeats",
	"decode",
	"encode",
	"quoted",
)


def _imap():
	import base64

	space = _load(
		MAIL / "imap.py",
		(*IMAP_NAMES, "FETCHED", "FLAGS", "MODSEQ", "parse_fetch", "COPYUID", "_expand", "copied"),
		re=re,
		base64=base64,
	)
	return space


def test_a_folder_is_known_by_its_flag_then_its_name_in_three_languages():
	space = _imap()
	listed = space["parse_list"](b'(\\HasNoChildren \\Sent) "/" "Sent Items"')
	assert listed == {"flags": {"\\hasnochildren", "\\sent"}, "delimiter": "/", "path": "Sent Items"}
	kind = space["kind_of"]
	assert kind({"\\sent"}, "Whatever") == "Sent"
	assert kind(set(), "inbox") == "Inbox"
	assert kind(set(), "INBOX.Gelöschte Elemente", ".") == "Trash"
	assert kind(set(), "المسودات") == "Drafts"
	assert kind(set(), "Projects") == "Other"
	assert (
		space["repeats"]({"\\all"}) and space["repeats"]({"\\noselect"}) and not space["repeats"]({"\\sent"})
	)
	literal = space["parse_list"]((b'(\\HasNoChildren) "/" {5}', b"Caf&AOk-"))
	assert literal["path"] == "Caf&AOk-"


def test_folder_names_travel_in_modified_utf7_both_ways():
	space = _imap()
	for text in ("Café", "Kunden Ä", "المرسلة", "A&B", "plain"):
		assert space["decode"](space["encode"](text)) == text
	assert space["encode"]("Café") == "Caf&AOk-"
	assert space["encode"]("A&B") == "A&-B"


def test_a_fetch_is_read_by_uid_and_a_move_by_copyuid():
	space = _imap()
	data = [
		(b"1 (UID 7 FLAGS (\\Seen \\Flagged) MODSEQ (12) BODY[] {3}", b"abc"),
		b")",
		b"2 (UID 9 FLAGS ())",
	]
	read = space["parse_fetch"](data)
	assert read[7] == {"flags": {"\\seen", "\\flagged"}, "body": b"abc", "modseq": 12}
	assert read[9]["flags"] == set() and read[9]["body"] is None
	assert space["copied"]([b"[COPYUID 1 4:6,9 20:23] Done"]) == {4: 20, 5: 21, 6: 22, 9: 23}
	assert space["copied"]([b"Done"]) == {}


def test_a_message_is_matched_by_its_message_id():
	message_id_of = _load(MAIL / "sync.py", ("message_id_of",))["message_id_of"]
	assert message_id_of(b"Subject: x\r\nMessage-ID: <a@b>\r\n\r\nMessage-ID: <body@x>") == "a@b"
	assert message_id_of(b"message-id:   <c@d>\n\nbody") == "c@d"
	assert message_id_of(b"Subject: none\r\n\r\n") is None
	source = (MAIL / "sync.py").read_text()
	assert '"message_id": message_id' in source, "a message moved elsewhere is found, not doubled"


def test_references_are_kept_bare_because_frappe_strips_angle_brackets():
	space = _load(MAIL / "threads.py", ("MESSAGE_ID", "ids", "stored"), re=re)
	assert space["stored"]("<a@x> <b@y>") == "a@x b@y"
	assert space["ids"]("a@x b@y") == ["a@x", "b@y"], "read back from one_references"
	assert space["stored"](None) is None
	assert "threads.stored(" in (MAIL / "inbound.py").read_text()
	assert "onedesk.one_mail.threads.adopt" in HOOKS, "a reply read before its parent joins it later"


def test_servers_are_found_for_the_usual_providers_and_guessed_for_the_rest():
	space = _load(MAIL / "connect.py", ("KNOWN", "guesses"))
	gmail = space["guesses"]("gmail.com")
	assert gmail[0]["email_server"] == "imap.gmail.com" and gmail[0]["use_tls"] == 1
	other = space["guesses"]("acme.example")
	assert [one["email_server"] for one in other] == ["imap.acme.example", "mail.acme.example"]
	assert all(one["incoming_port"] == 993 and one["use_ssl"] for one in other)


def test_a_connected_mailbox_is_read_by_us_not_by_frappes_pull():
	source = (MAIL / "connect.py").read_text()
	assert '"enable_incoming": 0' in source and '"one_connected": 1' in source
	assert "onedesk.one_mail.sync.sync_all" in HOOKS
	sync = (MAIL / "sync.py").read_text()
	assert "BODY.PEEK[]" in sync, "reading a message must not mark it read"
	assert 'job_id=f"one_mail_sync:{account}"' in sync, "one job per account at a time"


def test_changes_go_to_the_server_before_they_are_kept_here():
	source = (MAIL / "actions.py").read_text()
	for name in ("mark", "star", "move", "delete", "create_folder", "rename_folder", "delete_folder"):
		assert f"def {name}(" in source
	assert source.count("require(") >= 3, "only a holder changes a mailbox"
	assert "roles.administers" not in source, "an administrator does not see into somebody's own mailbox"
	assert '"User Email"' in source, "holding is Frappe's own User Email row"


def test_a_sent_copy_is_filed_once_and_not_where_the_server_files_its_own():
	space = _load(MAIL / "outbound.py", ("_last",))
	queue = type("Q", (), {"recipients": [type("R", (), {"recipient": one})() for one in ("a@x", "b@x")]})()
	assert not space["_last"](queue, "a@x") and space["_last"](queue, "b@x")
	assert "smtp.gmail.com" in _load(MAIL / "connect.py", ("FILES_ITS_OWN",))["FILES_ITS_OWN"]


# ------------------------------------------------------------------ holders


def test_everyone_gets_an_address_named_by_whoever_adds_them():
	import unicodedata

	space = _load(
		MAIL / "addresses.py", ("NAME", "RESERVED", "is_name", "suggested"), re=re, unicodedata=unicodedata
	)
	suggested = space["suggested"]
	assert suggested("Ülrich", "u@x.com") == "ulrich"
	assert suggested("أمل", "amal.k@x.com") == "amal-k", "a name in another script falls back to the login"
	assert suggested("Admin", "admin@x.com") == "member", "reserved names are never suggested"
	assert "onedesk.one_mail.addresses.for_person" in HOOKS
	custom = (MAIL / "custom" / "user.json").read_text()
	assert '"one_mail_name"' in custom
	assert "and it stays" in (MAIL / "addresses.py").read_text(), "an address, once given, is not renamed"


def test_only_the_workspaces_mailboxes_are_shared_out():
	source = (MAIL / "holders.py").read_text()
	assert 'if not frappe.db.get_value("Email Account", account, "one_shared")' in source
	assert source.count("_admin()") >= 4, "holders, replacing and restoring are an administrator's"
	ordered = _load(MAIL / "holders.py", ("ORDER", "ordered"))["ordered"]
	folders = [
		{"kind": "Other", "path": "b"},
		{"kind": "Trash", "path": "T"},
		{"kind": "Inbox", "path": "INBOX"},
		{"kind": "Other", "path": "A"},
	]
	assert [one["path"] for one in ordered(folders)] == ["INBOX", "T", "A", "b"]


# ------------------------------------------------------------------ the page

PAGE_JS = (tree.APP / "public" / "js" / "onemail.js").read_text()


def test_a_message_is_drawn_without_scripts_or_pictures_from_elsewhere():
	sandbox = re.search(r'sandbox="([^"]*)"', PAGE_JS).group(1)
	assert "allow-scripts" not in sandbox, "a message never runs code"
	assert "default-src 'none'" in PAGE_JS
	assert "Show pictures" in PAGE_JS and "this.pictures.has(" in PAGE_JS, (
		"remote pictures wait to be asked for"
	)
	assert 'querySelectorAll("script' in PAGE_JS


def test_the_page_reads_only_as_a_holder():
	source = (MAIL / "api.py").read_text()
	for name in ("conversations", "conversation", "names"):
		body = source.split(f"def {name}(", 1)[1].split("\ndef ", 1)[0]
		assert "actions.require(account)" in body, f"{name} checks the reader holds the mailbox"
	live = (MAIL / "live.py").read_text()
	assert "user=user" in live, "an event goes to holders, not to everyone"


def test_the_page_is_in_the_rail():
	sidebar = (MAIL / "sidebar" / "onemail" / "onemail.json").read_text()
	assert '"link_to": "onemail"' in sidebar and '"header_icon": "onemail"' in sidebar
	assert (MAIL / "page" / "onemail" / "onemail.json").exists()


# ------------------------------------------------------------------ mail in OneCloud


def test_a_message_opens_only_for_its_holders_and_a_link_never_grants_read():
	assert '"Communication": "onedesk.one_mail.access.allowed"' in HOOKS
	source = (MAIL / "access.py").read_text()
	body = source.split("def allowed", 1)[1]
	assert '"User Email"' in body and "reference_doctype" not in body, "being filed on a record opens nothing"
	assert "Inbox User" in (MAIL / "addresses.py").read_text(), "holders can open a message at all"


def test_attachments_are_in_onecloud_by_mailbox_not_under_records():
	ns = (tree.APP / "one_storage" / "namespace.py").read_text()
	assert 'virtual(MAIL, _("Mail")' in ns
	unlisted = ns.split("UNLISTED = frozenset(", 1)[1].split("# fmt: skip", 1)[0]
	assert '"Communication"' in unlisted, "a message's files are not listed again under Records"
	cloud = (MAIL / "cloud.py").read_text()
	assert "if account not in _held()" in cloud, "a mailbox's folder is its holders'"


def test_a_message_too_large_sends_its_largest_attachments_as_links():
	from email import message_from_bytes
	from email.mime.application import MIMEApplication
	from email.mime.multipart import MIMEMultipart
	from email.mime.text import MIMEText

	space = _load(MAIL / "outbound.py", ("ROOMY", "shrink", "_say"), message_from_bytes=message_from_bytes)
	message = MIMEMultipart()
	message.attach(MIMEText("hello", "plain"))
	for name, size in (("big.bin", 300_000), ("small.txt", 100)):
		part = MIMEApplication(b"x" * size)
		part["Content-Disposition"] = f'attachment; filename="{name}"'
		message.attach(part)
	raw = message.as_bytes()
	out = message_from_bytes(space["shrink"](raw, lambda name: f"https://x/s/{name}", most=100_000))
	kept = [one.get_filename() for one in out.walk() if one.get_content_disposition() == "attachment"]
	assert kept == ["small.txt"], "only as many as it takes, largest first"
	text = (
		next(one for one in out.walk() if one.get_content_type() == "text/plain")
		.get_payload(decode=True)
		.decode()
	)
	assert "big.bin: https://x/s/big.bin" in text
	assert space["shrink"](raw, lambda name: None, most=100_000) == raw, (
		"a file it cannot find stays attached"
	)
	assert space["shrink"](raw, lambda name: "u") == raw, "a message that fits is not touched"


# ------------------------------------------------------------------ faces and logos


def _faces():
	import hashlib
	from urllib.parse import quote, urlparse

	names = (
		"PROVIDERS",
		"EXTENSIONS",
		"domain_of",
		"keys_for",
		"is_person",
		"gravatar",
		"favicon",
		"file_name",
	)
	return _load(MAIL / "faces.py", names, hashlib=hashlib, quote=quote, urlparse=urlparse)


def test_a_sender_is_looked_for_as_a_person_then_as_an_organisation():
	space = _faces()
	keys_for = space["keys_for"]
	assert keys_for("Ana@Client.Example") == ["ana@client.example", "client.example"]
	assert keys_for("someone@gmail.com") == ["someone@gmail.com"], "gmail's logo is not the sender's"
	assert keys_for("ahmad.acme@m.4dl.app", ours="m.4dl.app") == ["ahmad.acme@m.4dl.app"]
	assert keys_for("not an address") == []
	domain_of = space["domain_of"]
	assert domain_of("https://www.Stripe.com/pricing") == "stripe.com"
	assert domain_of("stripe.com") == "stripe.com" and domain_of("x@mail.acme.co") == "mail.acme.co"
	assert domain_of("") is None and domain_of("localhost") is None


def test_pictures_are_asked_for_so_that_none_means_none():
	space = _faces()
	assert space["gravatar"]("A@B.c").endswith("?d=404&s=128"), (
		"Gravatar's default would be a picture of nobody"
	)
	assert "fallback_opts=TYPE,SIZE,URL" in space["favicon"]("acme.com"), "Google answers 404 with no logo"
	assert space["file_name"]("acme.com", "image/png; charset=binary") == "acme.com.png"
	source = (MAIL / "faces.py").read_text()
	assert "requests.get(" in source and "enqueue_after_commit=True" in source, (
		"fetched by the server, in the background"
	)
	for doctype in ("Contact", "Customer", "Supplier", "Bank"):
		assert f'"{doctype}": {{' in HOOKS and "faces.dress_later" in HOOKS


# ------------------------------------------------------------------ mail and records


def _linking():
	return _load(MAIL / "linking.py", ("QUOTED", "fresh_part", "prefixes", "candidates"), re=re)


def test_documents_are_found_by_the_naming_series_this_site_issues():
	space = _linking()
	assert space["prefixes"]("ACC-SINV-.YYYY.-\nACC-SINV-RET-.YYYY.-\n.#####") == [
		"ACC-SINV-",
		"ACC-SINV-RET-",
	]
	found = space["candidates"](
		"see ACC-SINV-2026-00002, and ACC-SINV-RET-2026-00001.", ["ACC-SINV-", "ACC-SINV-RET-"]
	)
	assert found == ["ACC-SINV-2026-00002", "ACC-SINV-RET-2026-00001"]
	assert space["candidates"]("XACC-SINV-1 ACC-SINV-", ["ACC-SINV-"]) == [], (
		"a word that starts elsewhere, or has no number"
	)
	assert space["candidates"]("anything", []) == []


def test_the_quoted_history_of_a_reply_is_not_read_again():
	fresh = _linking()["fresh_part"]
	assert fresh("New PO-1\n\nOn Mon, Ana wrote:\n> old PO-2") == "New PO-1\n\n"
	assert fresh("ok<blockquote>PO-2</blockquote>") == "ok"
	assert fresh("> only quoted") == ""
	assert fresh(None) == ""


def test_links_say_how_they_were_made_and_the_timeline_is_narrowed():
	source = (MAIL / "linking.py").read_text()
	for by in ('"thread"', '"address"', '"text"', '"manual"'):
		assert by in source
	assert "one_linked_by" in (MAIL / "custom" / "communication_link.json").read_text()
	for method in ("getdoc", "get_docinfo", "get_communications"):
		assert f'"frappe.desk.form.load.{method}": "onedesk.one_mail.linking.{method}"' in HOOKS
	assert "linking.arrived(" in (MAIL / "inbound.py").read_text(), "linked after Frappe's own second save"
