"""OneCloud's store: every file's content in R2, through admin's signed URLs,
behind a URL of the workspace's own."""

import ast
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
	files = next(item for item in rail["items"] if item.get("link_to") == "File")
	assert files["is_default_module"]


NAMESPACE = tree.APP / "one_storage" / "namespace.py"
API = tree.APP / "one_storage" / "api.py"


def test_a_node_id_says_what_it_names():
	constants = dict(ROOT="@root", MY="@my", SHARED="@shared", COMPANY="@company", RECORDS="@records", BIN="@bin")
	space = _load(NAMESPACE, ("parse",), **constants)
	parse = space["parse"]
	assert parse("") == ("@root",) and parse("@my") == ("@my",)
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
