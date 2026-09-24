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
	assert "has_permission('read')" in fetch
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
