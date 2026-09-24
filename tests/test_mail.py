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
	assert "roles.administers" in source and "System Manager" not in source


def test_a_sent_copy_is_filed_once_and_not_where_the_server_files_its_own():
	space = _load(MAIL / "outbound.py", ("_last",))
	queue = type("Q", (), {"recipients": [type("R", (), {"recipient": one})() for one in ("a@x", "b@x")]})()
	assert not space["_last"](queue, "a@x") and space["_last"](queue, "b@x")
	assert "smtp.gmail.com" in _load(MAIL / "connect.py", ("FILES_ITS_OWN",))["FILES_ITS_OWN"]
