"""OneMail: addresses on the mail domain, and the mail that arrives at them."""

import ast
import hashlib
import hmac
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

import tree

MAIL = tree.APP / "one_mail"
WORKER = (tree.ROOT / "deploy" / "mail" / "worker.js").read_text()
HOOKS = tree.hooks()


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


def test_no_address_is_made_without_a_mail_domain():
	"""A site without one_tenant once gave people `<name>.None@`."""

	class Refused(Exception):
		pass

	def throw(message):
		raise Refused(message)

	conf = {"one_tenant": None}
	frappe = type("frappe", (), {"conf": conf, "throw": staticmethod(throw)})
	space = _load(MAIL / "addresses.py", ("domain", "slug", "person_address"), frappe=frappe, _=str)
	try:
		space["person_address"]("rania")
	except Refused:
		pass
	else:
		raise AssertionError("an address was made with no workspace")
	conf["one_tenant"] = "acme"
	assert space["person_address"]("rania") == "rania.acme@m.4dl.app"


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


def test_mail_is_read_from_r2_every_minute_whatever_the_notice_did():
	assert re.search(r'"\* \* \* \* \*": \[\s*(?:#[^\n]*\n\s*)*"onedesk\.one_mail\.inbound\.sweep"', HOOKS)
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
	assert '"onedesk.one_mail.outbound.file_sent"' in HOOKS.split('"Communication": {', 1)[1].split("before_insert", 1)[1].split("\n", 1)[0]
	outbound = (MAIL / "outbound.py").read_text()
	assert 'account.get("one_hosted")' in outbound and "server.session.sendmail(" in outbound


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


def test_only_the_workspaces_mailboxes_are_shared_out():
	source = (MAIL / "holders.py").read_text()
	assert 'if not frappe.db.get_value("Email Account", account, "one_shared")' in source
	assert source.count('_admin("policy")') >= 4, "replacing, restoring and the address policy are the policy's"
	assert 'must(account, "holders")' in source.split("def set_access(", 1)[1].split("\ndef ", 1)[0], "who holds a mailbox is its Who Uses ability's"
	ordered = _load(MAIL / "holders.py", ("ORDER", "ordered"))["ordered"]
	folders = [
		{"kind": "Other", "path": "b"},
		{"kind": "Trash", "path": "T"},
		{"kind": "Inbox", "path": "INBOX"},
		{"kind": "Other", "path": "A"},
	]
	assert [one["path"] for one in ordered(folders)] == ["INBOX", "T", "A", "b"]


MAIL_UI = tree.ROOT / "frontend" / "src" / "mail"
PAGE_JS = "\n".join(path.read_text() for path in sorted(MAIL_UI.glob("*")))


def test_a_message_is_drawn_without_scripts_or_pictures_from_elsewhere():
	sandbox = re.search(r'sandbox="([^"]*)"', PAGE_JS).group(1)
	assert "allow-scripts" not in sandbox, "a message never runs code"
	assert "default-src 'none'" in PAGE_JS
	assert "Show pictures" in PAGE_JS and "framePage(props.content, allowed.value" in PAGE_JS, (
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


def test_a_message_opens_only_for_its_holders_and_a_link_never_grants_read():
	assert '"Communication": "onedesk.one_mail.access.allowed"' in HOOKS
	source = (MAIL / "access.py").read_text()
	body = source.split("def allowed", 1)[1]
	assert '"User Email"' in body and "reference_doctype" not in body, "being filed on a record opens nothing"


def test_attachments_are_in_onecloud_by_mailbox_not_under_records():
	ns = (tree.APP / "one_cloud" / "namespace.py").read_text()
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


def _faces():
	import hashlib
	from urllib.parse import quote, urlparse

	sys.path.insert(0, str(tree.ROOT))
	from onedesk.one_ai.reading.identifiers import PROVIDERS

	names = (
		"EXTENSIONS",
		"domain_of",
		"keys_for",
		"is_person",
		"gravatar",
		"favicon",
		"file_name",
		"sources",
	)
	return _load(
		MAIL / "faces.py",
		names,
		hashlib=hashlib,
		sha256_hash=lambda text: hashlib.sha256(text.encode() if isinstance(text, str) else text).hexdigest(),
		quote=quote,
		urlparse=urlparse,
		PROVIDERS=PROVIDERS,
	)


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
	assert "services.call(service_of(key), requests.get," in source and "enqueue_after_commit=True" in source, (
		"fetched by the server, in the background, and only while its optional service is on"
	)
	for doctype in (
		"Contact",
		"Lead",
		"User",
		"Employee",
		"Customer",
		"Supplier",
		"Manufacturer",
		"Company",
		"Bank",
	):
		assert f'"{doctype}": {{' in HOOKS and "faces.dress_later" in HOOKS
	assert "onedesk.one_mail.patches.dress_existing" in (tree.APP / "patches.txt").read_text()


def test_a_record_tries_both_services_in_the_order_that_fits_it():
	sources = _faces()["sources"]
	assert sources("person", "Ana@Stripe.com", None) == ["ana@stripe.com", "stripe.com"], (
		"a face, then the company's logo"
	)
	assert sources("person", "me@gmail.com", "https://acme.example") == ["me@gmail.com", "acme.example"]
	assert sources("organisation", "info@stripe.com", "https://www.stripe.com") == [
		"stripe.com",
		"info@stripe.com",
	]
	assert sources("organisation", "hello@gmail.com", None) == ["hello@gmail.com"], "never gmail's logo"
	assert sources("bank", "x@hsbc.com", "hsbc.com") == ["hsbc.com"]
	assert sources("organisation", None, None) == []
	assert sources("face", "ana@ourco.example", None) == ["ana@ourco.example"]
	assert sources("face", None, None) == []


def test_a_user_and_their_employee_share_a_photo_and_nobody_is_dressed():
	source = (MAIL / "faces.py").read_text()
	for doctype, field in (
		("User", "user_image"),
		("Employee", "image"),
		("Company", "company_logo"),
		("Manufacturer", "logo"),
	):
		assert f'"{doctype}": ("{field}",' in source
	assert 'NOBODY = ("Administrator", "Guest")' in source
	assert "borrowed(doc) or next(" in source, "an uploaded photo on the other record comes first"
	assert "letter_heads.redraw()" in source, "a dressed company's letter heads show the logo"
	assert "onedesk.one_mail.patches.dress_people_and_company" in (tree.APP / "patches.txt").read_text()


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


def _rules():
	import email as email_module

	names = ("MACHINES", "automatic", "failures", "bounced_id")
	return _load(MAIL / "rules.py", names, re=re, email=email_module)


def _flow():
	names = (
		"TEXT", "FLAGS", "KINDS", "ACTIONS", "CREATES", "ONCE", "test", "holds", "said", "walk", "_answered",
		"asks", "needs_ai", "topics", "answers_of", "actions_in", "conditions_in", "problems", "from_fields",
	)
	return _load(MAIL / "flow.py", names, re=re, _=lambda text: text)


def test_conditions_nest_in_groups_of_all_or_any():
	flow = _flow()
	facts = {"from": "News news@shop.example", "subject": "Weekly Newsletter", "attachment": False, "sender_is": {"Customer"}, "outside": True}
	both = {"items": [{"field": "from", "value": "shop.example"}, {"field": "subject", "value": "newsletter"}]}
	assert flow["test"](both, facts)
	assert not flow["test"]({"items": [{"field": "from", "value": "shop"}, {"field": "attachment", "value": True}]}, facts), "all, by default"
	nested = {"items": [{"field": "outside", "value": True}, {"any": True, "items": [{"field": "subject", "value": "invoice"}, {"field": "sender_is", "op": "is", "value": "Customer"}]}]}
	assert flow["test"](nested, facts)
	assert flow["test"]({"items": []}, facts), "no conditions: every message"
	assert flow["holds"]({"field": "subject", "op": "not_contains", "value": "invoice, quote"}, facts)
	assert flow["holds"]({"field": "sender_is", "op": "is_not", "value": "Supplier"}, facts)
	assert flow["said"]("Order 12", "starts_with", "order") and not flow["said"]("Order 12", "is", "order")


def test_steps_branch_stop_and_take_oneai_s_answer():
	flow = _flow()
	steps = [
		{"type": "if", "id": "i", "test": {"items": [{"field": "outside", "value": True}]}, "then": [{"type": "star"}], "else": [{"type": "read"}]},
		{"type": "ask", "id": "a", "ask": "pick", "labels": [{"label": "Quote", "then": [{"type": "stop"}]}, {"label": "Complaint", "then": [{"type": "notify", "user": "x"}]}], "else": [{"type": "junk"}]},
		{"type": "move", "folder": "F"},
	]
	assert flow["needs_ai"](steps) and not flow["needs_ai"](steps[:1])
	assert flow["topics"]("R", steps) == [("R#a#0", "Quote"), ("R#a#1", "Complaint")]
	done, stopped = flow["walk"](steps, {"outside": True}, flow["answers_of"]("R", steps, {"R#a#0"}))
	assert [one["type"] for one in done] == ["star"] and stopped, "Quote says stop"
	done, stopped = flow["walk"](steps, {"outside": False}, flow["answers_of"]("R", steps, {"R#a#1"}))
	assert [one["type"] for one in done] == ["read", "notify", "move"] and not stopped
	done, _ = flow["walk"](steps, {}, flow["answers_of"]("R", steps, set()))
	assert [one["type"] for one in done] == ["read", "junk", "move"], "nothing found: Otherwise"


def test_a_rule_must_do_something_and_old_rules_become_steps():
	flow = _flow()
	assert flow["problems"]([{"type": "if", "test": {}, "then": [], "else": []}]) == ["Add at least one action."]
	assert "Choose the folder to move to." in flow["problems"]([{"type": "move"}])
	assert "Write the address to forward to." in flow["problems"]([{"type": "forward", "to": "nobody"}])
	empty = [{"type": "if", "test": {"items": [{"any": True, "items": [{"field": "domain", "op": "is", "value": " "}]}]}, "then": [{"type": "junk"}]}]
	assert "Write what each condition looks for." in flow["problems"](empty), "an empty blank would match all mail"
	assert flow["problems"]([{"type": "reply", "text": "Thanks", "once": "conversation"}]) == [], "an auto reply needs no If"
	assert "Give OneAI at least two labels to pick from." in flow["problems"]([{"type": "ask", "ask": "pick", "labels": [{"label": "A"}], "then": [{"type": "star"}]}])
	old = {"from_contains": "shop", "subject_contains": "news", "match": "Any Condition", "move_to": "F", "star": 1, "stop": 1}
	steps = flow["from_fields"](old)
	assert steps[0]["test"] == {"any": True, "items": [{"field": "from", "op": "contains", "value": "shop"}, {"field": "subject", "op": "contains", "value": "news"}]}
	assert [one["type"] for one in steps[0]["then"]] == ["move", "star", "stop"]
	about = flow["from_fields"]({"about": "soft drinks", "move_to": "F"})
	assert about[0]["type"] == "ask" and about[0]["question"] == "soft drinks" and flow["needs_ai"](about)


def test_nothing_automatic_gets_an_away_reply():
	automatic = _rules()["automatic"]
	assert not automatic({}, "rana@supplier.example")
	assert automatic({"List-Id": "<weekly.shop.example>"}, "news@shop.example")
	assert automatic({"Auto-Submitted": "auto-replied"}, "ana@client.example")
	assert automatic({"Precedence": "bulk"}, "ana@client.example")
	for sender in ("noreply@x.com", "no-reply@x.com", "MAILER-DAEMON@mx.example", "postmaster@x.com", ""):
		assert automatic({}, sender), sender


def test_a_permanent_bounce_is_read_and_a_temporary_one_is_not():
	from email import message_from_string

	space = _rules()
	report = (
		'Content-Type: multipart/report; report-type=delivery-status; boundary="B"\n\n'
		"--B\nContent-Type: text/plain\n\nFailed.\n"
		"--B\nContent-Type: message/delivery-status\n\nReporting-MTA: dns; mx.example\n\n"
		"Final-Recipient: rfc822; Gone@Client.Example\nAction: failed\nStatus: 5.1.1\nDiagnostic-Code: smtp; 550 user unknown\n\n"
		"Final-Recipient: rfc822; later@client.example\nAction: delayed\nStatus: 4.4.1\n\n"
		"--B\nContent-Type: text/rfc822-headers\n\nMessage-ID: <abc@acme.com>\n\n--B--\n"
	)
	parsed = message_from_string(report)
	assert space["failures"](parsed) == [("gone@client.example", "5.1.1", "550 user unknown")]
	assert space["bounced_id"](parsed) == "abc@acme.com"
	assert space["failures"](message_from_string("Subject: hi\n\nhello")) == []


def test_rules_and_away_run_on_new_mail_only():
	sync = (MAIL / "sync.py").read_text()
	assert sync.count("fresh=False") == 2, "a first read and history are not new mail"
	assert "rules.after(" in (MAIL / "inbound.py").read_text()
	assert '"Mail Rule": "onedesk.one_mail.rules.rule_allowed"' in HOOKS


def test_a_search_understands_the_usual_operators():
	space = _load(MAIL / "api.py", ("OPERATORS", "WORD", "operators"), re=re)
	asked = space["operators"]('from:ana subject:"price list" is:unread has:attachment invoice http://x.com')
	assert asked["from"] == ["ana"] and asked["subject"] == ["price list"]
	assert asked["is"] == {"unread"} and asked["has"] == {"attachment"}
	assert asked["words"] == ["invoice", "http://x.com"], "an unknown key: is searched for as written"


def test_a_move_or_a_delete_to_trash_can_be_taken_back():
	source = (MAIL / "actions.py").read_text()
	assert "def put_back(" in source and '"was": was' in source
	assert "HEADER Message-ID" in source, "a message moved without its new uid is found again"
	assert "put_back" in PAGE_JS and "Undo" in PAGE_JS


def test_a_message_is_signed_as_the_address_it_is_sent_from():
	assert "doc.flags.skip_add_signature = True" in (MAIL / "outbound.py").read_text(), (
		"Frappe's signature after the composer closed"
	)
	compose = (tree.APP / "public" / "js" / "one_mail" / "mail_compose.js").read_text()
	assert "holders.signature_for" in compose
	assert "/assets/onedesk/js/one_mail/mail_compose.js" in HOOKS


def test_a_signature_keeps_its_layout_and_carries_its_logo():
	"""The editor flattens a drawn signature, so it stays out of it and goes
	in as the mail is sent; the logo goes inside the mail, not as a link."""
	import types

	compose = (tree.APP / "public" / "js" / "one_mail" / "mail_compose.js").read_text()
	assert "if (!this.one_sending || !this.one_signature) return said;" in compose, "drafts don't carry it"
	assert 'return "";' in compose.split("Composer.prototype.get_signature", 1)[1].split("};", 1)[0], (
		"nothing is put in the editor"
	)
	assert "said.slice(0, at) + signature + said.slice(at)" in compose, "above the quoted mail"
	assert "onedesk.one_mail.signatures.inline_logo" in HOOKS
	logo = "/files/sahara.png"
	company = types.SimpleNamespace(company=lambda: {"logo": logo})
	inline = _load(MAIL / "signatures.py", ("inline_logo",), re=re, letter_heads=company)["inline_logo"]
	doc = types.SimpleNamespace(
		communication_medium="Email",
		sent_or_received="Sent",
		content=f'<p>Hi</p><img src="{logo}" height="44"><img src="https://x.test{logo}">',
	)
	inline(doc)
	assert doc.content == '<p>Hi</p><img embed="files/sahara.png" height="44"><img embed="files/sahara.png">'
	received = types.SimpleNamespace(communication_medium="Email", sent_or_received="Received", content=f'<img src="{logo}">')
	inline(received)
	assert "embed" not in received.content, "only what is sent"


def test_a_person_s_mailbox_answers_while_they_are_away():
	"""The mailbox's own switch wins, within its dates; else the leave's
	message; else the mailbox's; else the day they are back. Whoever covers
	is named, unless the message names them already; the half day of a half-day leave answers
	nothing."""
	import datetime
	import types

	today = datetime.date(2026, 10, 24)
	space = _load(
		MAIL / "rules.py",
		("away_message", "switched_on", "standard_away", "cover_line", "default_away", "half_day_today"),
		_=lambda text, lang=None: f"[{lang}] {text}" if lang else text,
		getdate=lambda value: value if isinstance(value, datetime.date) else today,
		today=lambda: today,
		formatdate=lambda day: day.isoformat(),
	)
	said = space["away_message"]
	box = lambda **values: types.SimpleNamespace(get=lambda key: values.get(key))  # noqa: E731
	back = datetime.date(2026, 11, 2)
	leave = {"back": back, "one_away_message": None, "covering": None}
	samir = {"name": "Samir", "email": "samir@one.test"}
	assert said(box(), None) is None, "nobody away, no reply"
	assert said(box(one_away=1, one_away_message="Back Monday."), leave) == "Back Monday."
	assert said(box(one_away=1, one_away_until=datetime.date(2026, 10, 1)), None) is None, "a switch past its date"
	assert said(box(one_away=1, one_away_from=datetime.date(2026, 10, 25)), None) is None, "a switch not begun"
	assert said(box(), {**leave, "one_away_message": "On a site visit."}) == "On a site visit."
	assert said(box(one_away_message="Away."), leave) == "Away."
	assert said(box(), leave) == "I'm on leave and back on 2026-11-02. I'll reply then."
	covered = said(box(), {**leave, "covering": samir})
	assert covered.endswith("write to Samir at samir@one.test."), covered
	assert said(box(), {**leave, "covering": samir, "one_away_message": "Ask samir@one.test."}) == "Ask samir@one.test."
	assert said(box(one_away_message="Away."), {**leave, "covering": samir}).startswith("Away.\n\n")
	assert said(box(one_away=1), None, "ar") == "[ar] I'm away and will reply when I'm back.", "in their language"
	half = space["half_day_today"]
	assert half({"half_day": 1, "from_date": today, "to_date": today, "half_day_date": None})
	assert half({"half_day": 1, "from_date": today, "to_date": back, "half_day_date": today})
	assert not half({"half_day": 1, "from_date": today, "to_date": back, "half_day_date": back})
	assert not half({"half_day": 0, "from_date": today, "to_date": today})
	rules = (MAIL / "rules.py").read_text()
	assert '"status": "Approved"' in rules.split("def on_leave(", 1)[1].split("\ndef ", 1)[0]
	away = rules.split("def away(", 1)[1].split("\ndef ", 1)[0]
	assert 'if account.get("one_shared"):' in away, "a shared mailbox answers with Auto Reply"
	assert "reaches(account, sender)" in away and "period" in away


def test_whoever_covers_reads_but_never_owns():
	"""A covering person's row is marked, and what decides who a mailbox
	belongs to and who may change it ignores marked rows."""
	actions = (MAIL / "actions.py").read_text()
	assert '"one_cover_until": ["is", "not set"]' in actions.split("def owns(", 1)[1].split("\ndef ", 1)[0]
	holders = (MAIL / "holders.py").read_text()
	assert "holds = actions.owns(account, user)" in holders.split("def may(", 1)[1].split("\ndef ", 1)[0]
	signatures = (MAIL / "signatures.py").read_text()
	assert '"one_cover_until": ["is", "not set"]' in signatures.split("def person_of(", 1)[1].split("\ndef ", 1)[0]
	rules = (MAIL / "rules.py").read_text()
	covered = rules.split("def covered(", 1)[1].split("\ndef ", 1)[0]
	assert '"one_sends": 0' in covered, "never sends from their address"


def test_a_rule_on_an_issued_address_waits_for_a_mail_manager():
	rules = (MAIL / "rules.py").read_text()
	save = rules.split("def save_rule(", 1)[1].split("\ndef ", 1)[0]
	assert "doc.enabled = 0" in save and "doc.requested_by = frappe.session.user" in save
	assert "tell.rule_requested(doc)" in save
	assert 'holders.must(doc.account, "rules")' in rules.split("def decide_rule(", 1)[1]
	holders = (MAIL / "holders.py").read_text()
	assert 'not may(account, "rules")' in holders.split("def issued_to_them(", 1)[1].split("\ndef ", 1)[0]


def test_a_signature_is_shown_by_its_first_line(monkeypatch):
	import types

	strip = types.SimpleNamespace(strip_html=lambda text: re.sub(r"<[^>]+>", "", text))
	monkeypatch.setitem(sys.modules, "frappe.utils", strip)
	space = _load(MAIL / "holders.py", ("first_line",), re=re)
	first = space["first_line"]
	assert first("<p>Samir Aoun<br>Operations Lead</p>") == "Samir Aoun"
	assert first("<div><b>Samir</b></div><div>Lead</div>") == "Samir"
	assert first("") == "" and first(None) == ""


def test_who_may_change_a_mailbox_is_its_holder_a_role_or_a_share():
	holders = (MAIL / "holders.py").read_text()
	may = holders.split("def may(", 1)[1].split("\ndef ", 1)[0]
	assert "owner" not in may, "the workspace's, not the connector's"
	assert "if holds and not shared and not hosted:\n\t\treturn True" in may, "a mailbox of one's own is its holder's"
	assert may.index("addresses.is_private(email)") < may.index("roles.administers(user)"), "a private one is its holder's alone"
	assert "rights.may(DOCTYPE, one[\"all\"], account, user)" in may, "a role, or a share of this mailbox"
	assert "holds and hosted and not shared and rights.held(DOCTYPE, one[\"own\"], user)" in may, "their own address"
	assert "enable_outgoing" in holders.split("def may_sign(", 1)[1].split("\ndef ", 1)[0]
	setter = holders.split("def set_signature(", 1)[1].split("\ndef ", 1)[0]
	assert 'must(account, "signature")' in setter, "the server holds the line, not only the page"
	rules = (MAIL / "rules.py").read_text()
	assert 'holders.must(account, "away")' in rules.split("def set_away(", 1)[1].split("\ndef ", 1)[0]
	assert "one.may_sign ?" in PAGE_JS


def test_a_mailbox_that_breaks_is_told_once_and_can_be_given_its_password_again():
	sync = (MAIL / "sync.py").read_text()
	assert "if not doc.one_error:\n\t\t\tbroke(doc, said)" in sync, "once, when it breaks"
	assert "tell.mailbox_not_reachable(doc, said, holders)" in sync
	told = (MAIL / "tell.py").read_text()
	assert '"Mailbox Not Reachable"' in told and "Mailbox Not Reachable" in tree.notifications()
	connect = (MAIL / "connect.py").read_text()
	again = connect.split("def reconnect(", 1)[1].split("\ndef ", 1)[0]
	assert 'holders.must(account, "connection")' in again, "whoever may change its connection"
	assert "reach(doc.email_id, password, login, {key: doc.get(key) for key in WHERE})" in again


def test_oneai_suggests_a_mail_rule_as_a_card():
	"""Asked to sort mail into a folder, OneAI writes a rule card: the folder
	is made, and Intake switched on for a rule about meaning, only when a
	holder of the mailbox approves it."""
	hooks = tree.hooks()
	assert '"onedesk.one_mail.agent.suggest_mail_rule"' in hooks
	ai = (MAIL / "agent.py").read_text()
	make = ai.split("def make_rule(", 1)[1]
	assert "actions.require(account)" in make and "actions.create_folder(" in make
	assert "switches.set_mailbox(account, 1)" in make
	assert "rules.save_rule(account" in make, "saved as the page saves one, so an asked-for rule waits"
	setup = (MAIL.parent / "one_studio" / "ai_setup.py").read_text()
	assert "if what in mail_ai.APPROVED:" in setup and 'if what == "mail_rule":\n\t\treturn make_rule(changes)' in ai


def test_a_new_conversation_from_a_person_is_what_acknowledging_means():
	space = _load(MAIL / "rules.py", ("MACHINES", "automatic", "starts_conversation"), re=re)
	assert space["starts_conversation"]({})
	assert not space["starts_conversation"]({"In-Reply-To": "<a@x>"}), "a reply in a thread gets none"
	assert not space["starts_conversation"]({"References": "<a@x>"})
	assert space["automatic"]({"Auto-Submitted": "auto-replied"}, "a@x.com"), "never answer a machine"
	source = (MAIL / "rules.py").read_text()
	assert "if not frappe.local.one_rule_replied:\n\t\t\t\taway(" in source, "a rule's reply stands in for out of office"
	assert "def acknowledge(" not in source and "def set_auto_reply(" not in source, "Auto Reply is a rule"


def test_a_rule_replies_once_never_to_a_machine_and_oneai_sends_as_it_is():
	source = (MAIL / "rules.py").read_text()
	said = source.split("def answer(", 1)[1].split("\ndef ", 1)[0]
	assert "automatic(headers or {}, sender)" in said, "never answer a machine"
	assert "one_rule_reply:" in said and "RULE_REPLY_ONCE_IN" in said, "once per conversation"
	assert 'if not text or "[" in text:' in said and "_card(" not in source, "sent as it is, or not at all"
	assert "gate.over(held)" in said and "held.one_ai_off" in said, "OneAI replies only where it may read and spend"
	assert '"day": 24 * 3600' in source and 'once == "conversation"' in said, "once per conversation, or per sender"


def _theirs():
	return _load(MAIL / "theirs.py", ("verified", "_results", "_aligned"), re=re)


def test_a_sender_is_verified_only_by_the_receiving_servers_own_results():
	theirs = _theirs()

	class Mail(list):
		def items(self):
			return self

	passed = "mx.google.com; dkim=pass header.i=@shop.example header.s=s1; spf=pass (google.com: designates) smtp.mailfrom=ana@shop.example; dmarc=pass (p=NONE) header.from=shop.example"
	assert theirs["verified"](Mail([("Authentication-Results", passed)]), "ana@shop.example")
	assert theirs["verified"](Mail([("ARC-Authentication-Results", "i=1; mx.cloudflare.net; dkim=pass header.d=mail.shop.example")]), "ana@shop.example")
	assert not theirs["verified"](Mail([("Authentication-Results", "mx.google.com; spf=pass smtp.mailfrom=x@other.example")]), "ana@shop.example"), "SPF for another domain"
	assert not theirs["verified"](Mail([("Authentication-Results", "mx; dkim=pass header.d=shop.example; dmarc=fail header.from=shop.example")]), "ana@shop.example"), "DMARC fail wins"
	forged = Mail([("Authentication-Results", "mx.google.com; dkim=fail header.d=shop.example; spf=softfail"), ("Authentication-Results", passed)])
	assert not theirs["verified"](forged, "ana@shop.example"), "only the topmost, the receiving server's own"
	assert not theirs["verified"](Mail([]), "ana@shop.example") and not theirs["verified"](None, "ana@shop.example")


def test_every_reading_action_belongs_to_a_job_a_mailbox_can_switch_off():
	gate = _load(MAIL / "gate.py", ("HEADS", "TWO", "job_of"))
	intake = MAIL.parent / "one_ai" / "reading"
	keys = set()
	for name in ("filing.py", "plans.py", "money.py"):
		keys |= set(re.findall(r'key=f?"([^"{|]+(?:\|[^"{|]+)?)', (intake / name).read_text()))
	unknown = {key for key in keys if gate["job_of"](key) is None}
	assert not unknown, f"a planner's key no switch covers: {sorted(unknown)}"
	assert gate["job_of"]("mail-abc|agent|Create|Task||x") == "agent"
	assert gate["job_of"]("MAT-0001|task|renew|A123") == "hr" and gate["job_of"]("MAT-0001|task") == "tasks"
	assert gate["job_of"]("mail-abc|cut") == "tidy" and gate["job_of"]("mail-abc|back|Customer|X") == "link"
	assert gate["job_of"]("mail-abc|Create|0f3e") is None, "a key no switch covers is always allowed"
	assert "_does(reading, key)" in (intake / "act.py").read_text(), "act.apply asks the mailbox"
