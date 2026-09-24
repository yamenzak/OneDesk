"""OneCloud's store: every file's content in R2, through admin's signed URLs,
behind a URL of the workspace's own."""

import ast
import re
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

STORE = tree.APP / "one_storage" / "store.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _load(path: Path, names: tuple, **extra) -> dict:
	space = dict(extra)
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in names:
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def _body(path: Path, name: str) -> str:
	for node in ast.parse(path.read_text(encoding="utf-8")).body:
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(name)


def test_a_key_is_the_content_and_whether_it_is_private():
	import os
	import re

	key_for = _load(STORE, ("key_for",), os=os, re=re)["key_for"]
	assert key_for("abc123", "Invoice March.PDF", 1) == "files/private/abc123.pdf"
	assert key_for("abc123", "logo.png", 0) == "files/public/abc123.png"
	assert key_for("abc123", "no-extension", 1) == "files/private/abc123"
	assert key_for("abc123", "evil.p/../hp", 1).startswith("files/private/abc123"), "an extension cannot carry a path"
	assert "/" not in key_for("abc123", "x.a/b", 1).split("abc123", 1)[1]


def test_a_stored_url_carries_its_key_and_nothing_else():
	space = _load(STORE, ("FETCH", "is_stored", "key_of", "url_for"), parse_qs=parse_qs, urlparse=urlparse, quote=quote)
	url = space["url_for"]("files/private/abc.pdf")
	assert url == "/api/method/onedesk.one_storage.store.fetch?key=files/private/abc.pdf"
	assert space["key_of"](url) == "files/private/abc.pdf"
	assert space["key_of"]("/private/files/abc.pdf") is None
	assert url.startswith("/api/method/"), "Frappe counts it as remote, so its disk checks pass it by"


def test_content_goes_through_frappes_own_hooks_and_is_read_back_by_the_file_class():
	assert 'write_file = "onedesk.one_storage.store.write"' in HOOKS
	assert 'delete_file_data_content = "onedesk.one_storage.store.delete"' in HOOKS
	assert '"File": "onedesk.one_storage.file.CloudFile"' in HOOKS
	assert "save_file_on_filesystem()" in _body(STORE, "write"), "no account, the disk as before"


def test_an_object_goes_only_when_the_last_file_naming_it_does_and_only_on_commit():
	delete = _body(STORE, "delete")
	assert "_named_elsewhere" in delete and "after_commit" in delete


def test_the_door_checks_the_reader_and_does_not_say_whether_a_file_exists():
	fetch = _body(STORE, "fetch")
	assert "namespace.may(" in fetch
	assert "raise NotFound" in fetch and "PermissionError" not in fetch


def test_the_filename_travels_to_the_download_for_every_browser():
	storage = tree.APP / "one_admin" / "storage.py"
	disposition = _load(storage, ("disposition",))["disposition"]
	assert disposition("Invoice March.pdf", False) == (
		'attachment; filename="Invoice March.pdf"; filename*=UTF-8\'\'Invoice%20March.pdf'
	)
	said = disposition('فاتورة "آذار".pdf')
	assert said.startswith('inline; filename="') and '"' not in said.split('filename="', 1)[1].split('";', 1)[0]


def test_onecloud_is_in_the_dock_and_owns_files():
	dock = json.loads((tree.APP / "dock" / "onedesk" / "onedesk.json").read_text())
	assert "OneCloud" in [row["link_to"] for row in dock["items"]]
	rail = json.loads((tree.APP / "one_storage" / "sidebar" / "onecloud" / "onecloud.json").read_text())
	assert rail["header_icon"] == "onestorage", "the mark is read by its id"
	files = next(item for item in rail["items"] if item.get("label") == "Files")
	assert files["is_default_module"]
	assert (files["link_type"], files["link_to"]) == ("Page", "onecloud"), "Files is the explorer"


NAMESPACE = tree.APP / "one_storage" / "namespace.py"
API = tree.APP / "one_storage" / "api.py"


def test_a_node_id_says_what_it_names():
	constants = dict(
		ROOT="@root", MY="@my", SHARED="@shared", COMPANY="@company", RECORDS="@records", BIN="@bin",
		LIBRARIES="@libraries", RECENT="@recent", STARRED="@starred", MOUNTS="@mounts", REQUESTS="@requests",
		MAIL="@mail",
	)  # fmt: skip
	space = _load(NAMESPACE, ("parse",), **constants)
	parse = space["parse"]
	assert parse("@mail") == ("@mail",) and parse("@mail/sales@acme.com") == ("@mail", "sales@acme.com")
	assert parse("") == ("@root",) and parse("@my") == ("@my",)
	assert parse("@libraries") == ("@libraries",) and parse("@starred") == ("@starred",)
	assert parse("@mounts") == ("@mounts",) and parse("@mount/abc/docs") == ("mount", "@mount/abc/docs")
	assert parse("@records") == ("@records",)
	assert parse("@records/Sales Invoice") == ("@records", "Sales Invoice")
	assert parse("@records/Sales Invoice/ACC-SINV-2026-00001") == ("@records", "Sales Invoice", "ACC-SINV-2026-00001")
	assert parse("@records/File/a/b") == ("@records", "File", "a/b"), "a record name may have a slash"
	assert parse("Home/someone@x.com/Projects") == ("file", "Home/someone@x.com/Projects")


def test_two_things_with_one_name_are_kept_apart_the_way_an_explorer_does():
	unique = _load(NAMESPACE, ("unique_name",))["unique_name"]
	assert unique("Report.pdf", set()) == "Report.pdf"
	assert unique("Report.pdf", {"Report.pdf"}) == "Report (2).pdf"
	assert unique("Report.pdf", {"Report.pdf", "Report (2).pdf"}) == "Report (3).pdf"
	assert unique("New folder", {"New folder"}) == "New folder (2)"
	assert unique(".env", {".env"}) == ".env (2)"


def test_a_folder_cannot_go_inside_itself():
	loops = _load(NAMESPACE, ("would_loop",))["would_loop"]
	assert loops("A", ["A/B", "A", "Home"], "A/B/C")
	assert loops("A", [], "A")
	assert not loops("A", ["Home"], "Home/X")


def test_a_name_has_no_slashes():
	clean = _load(API, ("_clean",))["_clean"]
	assert clean("  a/b\\c  ") == "a b c"
	assert clean(None) == ""


def test_who_may_is_decided_in_one_place():
	may = _body(NAMESPACE, "may")
	assert "_staff(user)" in may, "a portal user sees nothing of the staff's"
	assert "'record'" in may and "has_permission" in may, "a record's file answers to the record"
	for verb in ("rename", "move", "delete"):
		assert "_need(" in _body(API, verb) or "_target(" in _body(API, verb)


def test_between_a_record_and_a_folder_is_a_copy_and_a_copy_moves_no_bytes():
	assert "copy([node_id], target)" in _body(API, "move")
	copied = _body(API, "_copy")
	assert "'file_url': item.file_url" in copied and "get_content" not in copied


def test_a_record_file_is_in_records_not_in_the_folder_frappe_filed_it_in():
	assert "attached_to_doctype and one.attached_to_name" in _body(NAMESPACE, "children")


def test_the_recycle_bin_keeps_thirty_days_and_is_emptied_daily():
	assert '"onedesk.one_storage.api.purge_old"' in HOOKS
	assert "KEPT_DAYS = 30" in API.read_text()


UPLOAD = tree.APP / "one_storage" / "upload.py"
PAGE = tree.APP / "public" / "js"


def test_a_dropped_folder_keeps_its_folders_and_nothing_climbs_out():
	import os

	class api:
		@staticmethod
		def _clean(name):
			return " ".join((name or "").replace("/", " ").replace("\\", " ").split())[:140]

	class ns:
		DEEPEST = 64

	split = _load(UPLOAD, ("split_path",), api=api, ns=ns, os=os)["split_path"]
	assert split("report.pdf") == []
	assert split("Trip/Day 1/photo.jpg") == ["Trip", "Day 1"]
	assert split("../../etc/passwd") == ["etc"], "no parent steps"
	assert split("a\\b\\c.txt") == ["a", "b"], "a Windows path is a path too"
	assert split(None) == []


def test_an_upload_goes_to_r2_and_the_ticket_is_the_whole_of_the_trust():
	begin, done = _body(UPLOAD, "begin"), _body(UPLOAD, "done")
	assert "api._target(node)" in begin, "where it goes is checked before anything is signed"
	assert "account.put_url" in begin
	assert "held.get('user') != frappe.session.user" in done, "a ticket is only its asker's"
	assert "delete_value" in done, "a ticket is used once"
	assert "'Range'" in done, "the object is checked to have arrived before a row names it"
	assert "copy_from_existing_file" in _body(UPLOAD, "_place"), "the bytes are not read back through this server"


def test_the_explorer_calls_only_verbs_that_exist():
	import re

	js = (PAGE / "onecloud.js").read_text()
	api = "".join(
		(tree.APP / "one_storage" / name).read_text() for name in ("api.py", "upload.py", "share.py", "library.py", "history.py", "file_requests.py")
	)
	called = set(re.findall(r'OneCloud\.(?:API|UPLOAD) \+ "(\w+)"', js)) | set(re.findall(r'\bcall\("(\w+)"', js))
	assert {"listing", "folders", "make_folder", "rename", "move", "copy", "delete", "restore", "purge", "empty_bin", "begin", "done", "resolve"} <= called
	for name in called:
		assert re.search(rf"@frappe\.whitelist\([^)]*\)\n(?:@[^\n]+\n)*def {name}\(", api), name
	assert "onedesk.one_storage.upload.here" in js, "and the way through this server when R2 is out of reach"


def test_the_explorer_has_the_keys_everybody_knows():
	js = (PAGE / "onecloud.js").read_text()
	for key in ('"F2"', '"Delete"', '"Enter"', '"Backspace"', '"F5"', 'ctrl && k === "a"', 'ctrl && k === "c"', 'ctrl && k === "x"', 'ctrl && k === "v"'):
		assert key in js, key
	assert "webkitGetAsEntry" in js, "a whole folder can be dropped"
	assert 'frappe.set_route("onecloud", { node })' in js, "the place is in the address"


SHARE = tree.APP / "one_storage" / "share.py"


def test_a_share_on_a_folder_reaches_everything_in_it_and_edit_beats_view():
	held = {"Home/a/Projects": "read", "Home/a/Projects/Plans": "write"}
	space = _load(NAMESPACE, ("granted",), grants=lambda user: held, chain=lambda folder: {
		"Home/a/Projects/Plans": ["Home/a/Projects/Plans", "Home/a/Projects", "Home/a", "Home"],
		"Home/a/Projects": ["Home/a/Projects", "Home/a", "Home"],
		"Home/a": ["Home/a", "Home"],
	}.get(folder, []))
	granted = space["granted"]
	assert granted({"name": "f1", "folder": "Home/a/Projects"}, "b") == "read", "a file in a shared folder"
	assert granted({"name": "f2", "folder": "Home/a/Projects/Plans"}, "b") == "write", "the nearer edit share wins"
	assert granted({"name": "Home/a/Projects", "folder": "Home/a"}, "b") == "read", "the folder itself"
	assert granted({"name": "f3", "folder": "Home/a"}, "b") is None, "and nothing beside it"


def test_a_share_is_read_before_a_home_says_no_and_never_for_a_portal_user():
	body = _body(NAMESPACE, "may")
	assert body.index("_staff(user)") < body.index("granted(item, user)") < body.index("where[0] == 'home'"), (
		"a portal user gets nothing from a share; staff get what was shared before My Files is theirs alone"
	)


def test_what_was_shared_can_be_copied_out_but_not_taken():
	assert "_leaves_its_owner(item, where[1])" in _body(API, "move")
	assert "source[0] == 'home' and (source[1] != user)" in _body(API, "_leaves_its_owner")


def test_sharing_is_for_the_team_and_a_records_file_goes_with_its_record():
	body = _body(SHARE, "share")
	assert "'user_type': 'System User'" in body, "a customer gets a link, not a seat"
	assert "ignore_share_permission" in body, "our rule decided, so Frappe's is not asked again"
	assert "Share the record instead" in _body(SHARE, "_shareable")
	assert "ns.may(item, 'write')" in _body(SHARE, "_shareable"), "whoever may change it may share it"
	assert "/desk/onecloud?node=" in _body(SHARE, "_tell"), "the notification opens the explorer"


LINKS = tree.APP / "one_storage" / "links.py"


def test_a_link_cookie_opens_its_own_link_for_its_own_time_and_nothing_else():
	import hashlib
	import hmac

	space = _load(LINKS, ("seal", "unseal"), hmac=hmac, hashlib=hashlib)
	seal, unseal = space["seal"], space["unseal"]
	key = b"site key"
	value = seal("abc", "guest@example.org", 2000, key)
	assert unseal("abc", value, key, 1000) == "guest@example.org"
	assert unseal("abc", seal("abc", "", 2000, key), key, 1000) == "", "a password opens it for anybody"
	assert unseal("xyz", value, key, 1000) is None, "another link's cookie"
	assert unseal("abc", value, b"another site", 1000) is None, "another site's cookie"
	assert unseal("abc", value, key, 3000) is None, "run out"
	assert unseal("abc", value.replace("guest@", "boss@"), key, 1000) is None, "an address swapped in"
	assert unseal("abc", "rubbish", key, 1000) is None and unseal("abc", None, key, 1000) is None


def test_a_guest_reaches_the_links_item_or_what_is_inside_its_folder_now():
	body = _body(LINKS, "_within")
	assert "link.file not in above" in body and "_binned(item.folder)" in body
	for verb in ("get", "put"):
		assert "_within(link" in _body(LINKS, verb), verb
		assert "opened_as(link) is None" in _body(LINKS, verb), verb


def test_the_table_alone_opens_nothing_and_the_guest_doors_are_rate_limited():
	link = json.loads((tree.APP / "one_storage" / "doctype" / "cloud_link" / "cloud_link.json").read_text())
	fields = {one["fieldname"]: one for one in link["fields"]}
	assert fields["token"]["fieldtype"] == "Password", "kept encrypted, for the owner to copy again"
	assert fields["token_hash"].get("unique"), "and found by its hash"
	source = LINKS.read_text()
	for verb in ("unlock", "ask_code", "enter_code", "put"):
		assert re.search(rf"@rate_limit\([^)]*\)\ndef {verb}\(", source), verb


def test_asking_for_a_code_does_not_say_who_was_invited():
	body = _body(LINKS, "ask_code")
	assert body.rstrip().endswith("return _back(token, 'sent')"), "the same answer either way"


def test_a_link_lives_at_s_and_goes_when_its_file_does():
	assert '"from_route": "/s/<token>", "to_route": "s"' in HOOKS
	assert "onedesk.one_storage.links.forget_file" in HOOKS
	assert (tree.APP / "www" / "s.py").exists() and (tree.APP / "www" / "s.html").exists()


LIBRARY = tree.APP / "one_storage" / "library.py"
HISTORY = tree.APP / "one_storage" / "history.py"


def test_a_library_is_its_members_and_its_roles_are_share_bits():
	body = _body(NAMESPACE, "may")
	assert body.index("_library_may(") < body.index("item.get('owner') == user"), (
		"belonging is the only way in: having made a file there is nothing once you have left"
	)
	roles = _load(NAMESPACE, ("ROLES",))["ROLES"]
	assert roles == {"Reader": (0, 0), "Member": (1, 0), "Owner": (1, 1)}
	lib = _body(NAMESPACE, "_library_may")
	assert "role_in(item['name'], user) == 'Owner'" in lib, "only an owner renames or deletes the library itself"
	assert "roles.ADMINISTRATOR" in lib, "a library whose owners left is not lost"


def test_a_library_keeps_an_owner_and_only_owners_say_who_is_in_it():
	assert "owners == [user]" in _body(LIBRARY, "remove")
	assert "_manages(item.name)" in _body(LIBRARY, "add")
	assert "LIBRARY_ROOT" in _body(NAMESPACE, "children"), "Company does not show the libraries' folder"


def test_replacing_a_file_keeps_what_it_held_and_its_bytes():
	assert "keep(item)" in _body(HISTORY, "replace") and "keep(item)" in _body(HISTORY, "restore")
	assert "Cloud File Version" in _body(STORE, "_named_elsewhere"), "a version's object is not dropped under it"
	assert "Cloud File Version" in _body(STORE, "fetch"), "an old version opens for whoever may open the file"
	assert "onedesk.one_storage.history.forget" in HOOKS, "and goes when the file does"


def test_a_star_is_nobodys_business_but_the_readers():
	body = _body(HISTORY, "star")
	assert "_liked_by" in body and "toggle_like" not in body, "Frappe's like comments and notifies"


def test_recent_is_short_and_losing_it_loses_nothing():
	assert "ltrim(key, 0, RECENT - 1)" in _body(HISTORY, "seen")
	assert "except Exception" in _body(HISTORY, "seen") and "except Exception" in _body(HISTORY, "recent")


DAV = tree.APP / "one_storage" / "dav.py"


def test_a_drive_path_has_no_parent_steps_and_litter_is_refused():
	space = _load(DAV, ("split", "litter", "LITTER"))
	split, litter = space["split"], space["litter"]
	assert split("/My Files/Projects/") == ["My Files", "Projects"]
	assert split("/My Files/../Company/./x") == ["My Files", "Company", "x"], "no climbing out"
	assert split("") == [] and split("/") == []
	assert litter(".DS_Store") and litter("._report.pdf") and litter("Thumbs.db") and litter("~$budget.xlsx")
	assert not litter("report.pdf")


def test_the_drive_is_frappes_sign_in_and_the_explorers_verbs():
	serve = _body(DAV, "serve")
	assert "frappe.session.user in ('Guest', '')" in serve and "WWW-Authenticate" in serve, "no key, a Basic challenge"
	assert "frappe.local.flags.commit = True" in serve, "Frappe rolls back PROPPATCH, MKCOL, MOVE and LOCK otherwise"
	source = DAV.read_text()
	for verb in ("api.make_folder(", "api.delete(", "api.move(", "api.copy(", "api.rename(", "upload._place("):
		assert verb in source, verb
	assert "ns.children(" in _body(DAV, "_children"), "a drive lists exactly what the explorer lists"


def test_a_drive_is_found_by_its_client():
	assert 'after_request = ["onedesk.one_storage.dav.headers"]' in HOOKS
	head = _body(DAV, "headers")
	assert "DAV" in head and "response.status_code = 200" in head, "OPTIONS answers whoever asks"
	assert "response_headers" in head, "applied after Frappe offers OAuth"
	assert "wsgidav" in (tree.ROOT / "pyproject.toml").read_text()


def test_an_empty_file_is_not_kept_as_a_version():
	assert "if item.file_size:" in _body(HISTORY, "replace")


MOUNTS = tree.APP / "one_storage" / "mounts.py"


def test_a_server_path_stays_inside_the_mounts_folder():
	import posixpath

	space = _load(MOUNTS, ("PREFIX", "split", "join", "node_id"), posixpath=posixpath)
	split, join, node_id = space["split"], space["join"], space["node_id"]
	assert split("@mount/abc/docs/plan.md") == ("abc", "docs/plan.md")
	assert split("@mount/abc/../../etc/passwd") == ("abc", "etc/passwd"), "no parent steps"
	assert split("@mount/abc") == ("abc", "")
	assert join("/srv/share", "../../etc/passwd") == "/srv/share/etc/passwd"
	assert join("/srv/share", "") == "/srv/share"
	assert node_id("abc", "/docs/") == "@mount/abc/docs" and node_id("abc") == "@mount/abc"


def test_a_webdav_listing_is_read_without_the_folder_itself():
	from urllib.parse import unquote, urlparse
	from xml.etree import ElementTree

	space = _load(
		MOUNTS, ("parse_propfind", "_from_http_date"), ElementTree=ElementTree, unquote=unquote, urlparse=urlparse
	)
	xml = b"""<?xml version="1.0"?><D:multistatus xmlns:D="DAV:">
	<D:response><D:href>/dav/My%20Files/</D:href><D:propstat><D:prop><D:resourcetype><D:collection/></D:resourcetype></D:prop></D:propstat></D:response>
	<D:response><D:href>/dav/My%20Files/Plans/</D:href><D:propstat><D:prop><D:resourcetype><D:collection/></D:resourcetype></D:prop></D:propstat></D:response>
	<D:response><D:href>/dav/My%20Files/a%20b.txt</D:href><D:propstat><D:prop><D:resourcetype/><D:getcontentlength>12</D:getcontentlength>
	<D:getlastmodified>Thu, 24 Sep 2026 07:43:00 GMT</D:getlastmodified></D:prop></D:propstat></D:response></D:multistatus>"""
	found = space["parse_propfind"](xml, "/dav/My%20Files/")
	assert [(one["name"], one["folder"], one["size"]) for one in found] == [("Plans", True, 0), ("a b.txt", False, 12)]
	assert found[1]["modified"] == "2026-09-24 07:43:00"


def test_a_server_is_never_this_machine_or_its_network():
	body = _body(MOUNTS, "reachable")
	for check in ("is_private", "is_loopback", "is_link_local", "is_reserved"):
		assert check in body, check
	assert "reachable(doc.host)" in MOUNTS.read_text()
	assert "reachable(urlparse(base).hostname" in MOUNTS.read_text()


def test_a_mount_is_its_makers_until_an_administrator_shares_it_and_keeps_its_secrets():
	controller = (tree.APP / "one_storage" / "doctype" / "cloud_mount" / "cloud_mount.py").read_text()
	assert "roles.ADMINISTRATOR not in frappe.get_roles()" in controller
	assert "doc.owner == user" in _body(MOUNTS, "may") and "doc.shared" in _body(MOUNTS, "may")
	shown = _body(MOUNTS, "settings")
	assert "password" not in shown and "private_key" not in shown, "a secret is never sent to a browser"


def test_the_explorers_verbs_reach_a_server():
	api = API.read_text()
	for hook in ("mounts.make_folder(", "mounts.rename(", "mounts.delete(", "_across(nodes, target, move=True)", "_across(nodes, target, move=False)"):
		assert hook in api, hook
	assert "mounts.move_within(" in _body(API, "_across"), "within one server, the server's own rename"


def test_a_drive_password_is_read_from_basic_auth_and_nothing_else():
	import base64
	import binascii

	basic = _load(DAV, ("basic",), base64=base64, binascii=binascii)["basic"]
	token = base64.b64encode(b"ana@example.com:abcd-efgh-ijkl-mnop").decode()
	assert basic(f"Basic {token}") == ("ana@example.com", "abcd-efgh-ijkl-mnop")
	assert basic(f"token {token}") is None and basic("Basic !!!") is None and basic(None) is None
	assert basic("Basic " + base64.b64encode(b"no-colon").decode()) is None


def test_a_drive_password_opens_the_drive_and_nothing_else():
	assert 'before_request = ["onedesk.one_storage.dav.sign_in"]' in HOOKS
	body = _body(DAV, "sign_in")
	assert "request.path.startswith(MOUNT)" in body, "anywhere else it is only a wrong API key"
	assert "'@' not in found[0]" in body, "an email, which an API key never is"
	assert "row.user.lower() != email.strip().lower()" in body, "the password is that person's"
	assert "HTTP_AUTHORIZATION" in body, "taken away before Frappe's own check refuses it"
	assert "api_secret" not in DAV.read_text(), "making one no longer changes the person's API secret"


def test_a_tenant_is_limited_by_storage_not_by_file_size():
	largest = _load(STORE, ("LARGEST",))["LARGEST"]
	assert largest == 5 * 1024**3, "what R2 takes in one PUT"
	steps = (tree.APP / "one_admin" / "steps.py").read_text()
	assert '"key": "max_file_size", "value": store.LARGEST' in steps, "every request's limit, set when the site is built"
	assert HOOKS.count('"onedesk.one_storage.store.unlimit"') == 2, "the attach button's, on install and every migrate"


def test_the_explorer_is_its_own_navigation():
	js = (PAGE / "onecloud.js").read_text()
	page = (tree.APP / "one_storage" / "page" / "onecloud" / "onecloud.js").read_text()
	assert "hide_sidebar: true" in page, "the panel starts closed; the tree takes its place"
	assert '"storage-check"' in js and 'has_role("Workspace Administrator")' in js


REQUESTS = tree.APP / "one_storage" / "file_requests.py"
REQUEST = tree.APP / "one_storage" / "doctype" / "cloud_file_request" / "cloud_file_request.py"


def test_a_requested_file_is_one_of_the_kinds_asked_for():
	import os

	accepted = _load(REQUESTS, ("accepted",), os=os)["accepted"]
	assert accepted("Licence.PDF", "pdf")
	assert accepted("scan.png", "jpg, png")
	assert not accepted("scan.exe", "jpg, png")
	assert not accepted("noextension", "pdf")
	assert accepted("anything.bin", "")
	assert accepted("anything.bin", None)


def test_a_request_link_is_kept_only_as_its_hash():
	source = REQUEST.read_text(encoding="utf-8")
	assert "sha256" in source
	assert "one.token_hash = hashed(token)" in source
	assert "'token_hash': hashed(token)" in _body(REQUESTS, "live")
	fields = {f["fieldname"]: f for f in json.loads((REQUEST.parent.parent / "cloud_file_request_recipient" / "cloud_file_request_recipient.json").read_text())["fields"]}
	assert fields["token"]["fieldtype"] == "Password"


def test_a_field_item_needs_a_record_and_one_person():
	people = REQUEST.read_text(encoding="utf-8")
	assert "fills a record's field, so the request needs a record" in people
	assert "goes to one person" in people
	assert "one.several = 0" in people
	assert 'ATTACH = ("Attach", "Attach Image")' in people


def test_a_request_is_answered_by_anyone_with_the_link_but_not_endlessly():
	source = REQUESTS.read_text(encoding="utf-8")
	head = source[source.index("@frappe.whitelist(allow_guest=True"): source.index("def send(")]
	assert 'methods=["POST"]' in head and "rate_limit" in head
	send = _body(REQUESTS, "send")
	assert "doc.status != 'Open'" in send and "accepted(" in send
	assert "frappe.set_user('Guest')" in send


def test_a_request_has_its_page_and_its_reminders():
	assert '"/r/<token>"' in HOOKS
	assert "onedesk.one_storage.file_requests.remind_due" in HOOKS
	assert (tree.APP / "www" / "r.py").exists() and (tree.APP / "www" / "r.html").exists()


def test_a_search_everywhere_knows_where_each_file_is_without_asking():
	space = _load(
		NAMESPACE, ("placed",), HOME="Home", ATTACHMENTS="Home/Attachments", DEEPEST=64
	)  # fmt: skip
	placed = space["placed"]
	folders = {
		"Home": {"folder": None},
		"Home/Attachments": {"folder": "Home"},
		"mine": {"folder": "Home", "one_home_of": "a@x.com"},
		"sub": {"folder": "mine"},
		"lib": {"folder": "Home/Libraries", "one_library": 1},
		"Home/Libraries": {"folder": "Home"},
		"shelf": {"folder": "lib"},
		"team": {"folder": "Home"},
		"binned": {"folder": "team", "one_deleted": 1},
		"inside": {"folder": "binned"},
	}
	assert placed("sub", folders) == ("home", "a@x.com")
	assert placed("shelf", folders) == ("library", "lib")
	assert placed("team", folders) == ("company",)
	assert placed("Home/Attachments", folders) == ("attachments",)
	assert placed("inside", folders) is None, "a file in a binned folder is not found"


def test_a_search_everywhere_asks_may_and_leaves_servers_alone():
	body = _body(NAMESPACE, "everywhere")
	assert "may(one, where=where)" in body
	assert "mount" not in body.replace("Servers on the Network are not searched", "")
	assert "everywhere(text, most)" in _body(NAMESPACE, "search"), "the top of OneCloud searches everywhere"
	assert "ns.everywhere(search)" in (tree.APP / "one_storage" / "api.py").read_text()


def test_a_search_can_be_widened_and_a_result_found_where_it_lives():
	js = (PAGE / "onecloud.js").read_text()
	assert "everywhere: this.search && this.everywhere ? 1 : 0" in js
	assert '"open-location"' in js and "this.reveal" in js
	assert 'ctrl && e.shiftKey && k.toLowerCase() === "f"' in js


RECORD_FILES = tree.APP / "public" / "js" / "record_files.js"


def test_every_record_has_a_files_tab_on_its_own_room():
	js = RECORD_FILES.read_text()
	assert "Layout.prototype.get_doctype_fields" in js
	assert '"Tab Break"' in js and '"HTML"' in js
	for kept_out in ("meta.istable", "meta.issingle", 'frm.doctype !== "File"', "layout.is_child_table"):
		assert kept_out in js, kept_out
	assert "`@records/${frm.doctype}/${frm.doc.name}`" in js
	assert 'frappe.ui.form.on("*"' in js
	assert "/assets/onedesk/js/record_files.js" in HOOKS


def test_the_explorer_is_loaded_when_first_opened_and_shared_by_both_hosts():
	page = (tree.APP / "one_storage" / "page" / "onecloud" / "onecloud.js").read_text()
	tab = RECORD_FILES.read_text()
	for host in (page, tab):
		assert '"/assets/onedesk/js/onecloud.js"' in host and "frappe.require" in host
	assert "/assets/onedesk/js/onecloud.js" not in HOOKS, "not on every desk load"
	explorer = (PAGE / "onecloud.js").read_text()
	assert "if (this.room && node !== this.room)" in explorer, "a room never walks out of itself"


def test_the_sidebar_attachments_are_one_row_into_the_files_tab():
	js = RECORD_FILES.read_text()
	css = (tree.APP / "public" / "css" / "desk.css").read_text()
	assert "one-files-side" in js and '.off("click")' in js and "tab.set_active()" in js
	for gone in (".one-files-side .attachment-row", ".one-files-side .show-all-btn", ".one-files-side .add-attachment-btn"):
		assert gone in css, gone


LIVE = tree.APP / "one_storage" / "live.py"


def test_a_change_is_told_as_keys_that_name_nothing():
	import hashlib
	import hmac

	space = _load(
		LIVE, ("key", "record_key", "keys_of"), hmac=hmac, hashlib=hashlib, get_encryption_key=lambda: "site-secret"
	)  # fmt: skip
	keys = space["keys_of"]({"folder": "Home/alice@x.com/Salaries", "attached_to_doctype": "Employee", "attached_to_name": "HR-EMP-1"})
	assert len(keys) == 2
	for one in keys:
		assert len(one) == 16 and "alice" not in one and "Salaries" not in one
	assert space["key"]("Home/a") != space["record_key"]("Home", "a"), "a folder and a record never share a key"
	other = _load(LIVE, ("key",), hmac=hmac, hashlib=hashlib, get_encryption_key=lambda: "another")["key"]
	assert other("Home/a") != space["key"]("Home/a"), "keyed by the site's own secret"


def test_every_way_a_file_changes_is_told():
	hooks = HOOKS[HOOKS.index('"File": {') :]
	hooks = hooks[: hooks.index("},")]
	assert '"on_update": "onedesk.one_storage.live.changed"' in hooks
	assert "onedesk.one_storage.live.changed" in hooks[hooks.index('"on_trash"') :]
	api = (tree.APP / "one_storage" / "api.py").read_text()
	for verb in ("rename", "move", "delete", "restore"):
		assert "live.announce(" in _body(tree.APP / "one_storage" / "api.py", verb), verb
	assert '"watch": live.watch(node, bool(search))' in api
	assert "live.announce(item)" in _body(tree.APP / "one_storage" / "history.py", "replace")
	assert "live.announce(item)" in _body(tree.APP / "one_storage" / "history.py", "restore")


def test_the_explorer_listens_on_its_own_event_not_list_update():
	js = (PAGE / "onecloud.js").read_text()
	assert 'frappe.realtime.doctype_subscribe("File")' in js
	assert 'frappe.realtime.on("onecloud_change"' in js
	assert "list_update" not in js, "the list view unbinds every list_update listener"
	source = LIVE.read_text()
	assert "after_commit.add(_send)" in source and 'room=get_doctype_room("File")' in source


PICKER = tree.APP / "public" / "js" / "onecloud_picker.js"


def test_the_upload_dialog_chooses_from_onecloud_instead_of_its_library():
	js = PICKER.read_text()
	assert "Uploader.UploadOptions.push(" in js, "Frappe's own extension point"
	assert "disable_file_browser: true" in js, "Frappe's Library asked Frappe's File permission"
	assert '"onedesk.one_storage.api.attach"' in js and "on_success" in js
	assert 'frappe.require("file_uploader.bundle.js")' in js
	assert "/assets/onedesk/js/onecloud_picker.js" in HOOKS
	explorer = (PAGE / "onecloud.js").read_text()
	assert "if (this.picker) return this.picker.on_pick(" in explorer
	assert "if (this.picker) return; // nothing is moved from inside a dialog" in explorer


def test_a_file_chosen_is_allowed_by_onecloud_and_copies_no_bytes():
	body = _body(tree.APP / "one_storage" / "api.py", "attach")
	assert "ns.may(item)" in body and "check_write_permission(doctype, docname)" in body
	assert "'file_url': item.file_url" in body and "copy_from_existing_file = True" in body
	api = (tree.APP / "one_storage" / "api.py").read_text()
	assert re.search(r'@frappe\.whitelist\(methods=\["POST"\]\)\ndef attach\(', api)


def test_an_upload_that_belongs_to_no_record_lands_in_my_files():
	body = (tree.APP / "one_storage" / "file.py").read_text()
	assert 'endswith("/upload_file")' in body, "only Frappe's dialog, not OneCloud's own verbs"
	assert "self.folder = ns.home()" in body
