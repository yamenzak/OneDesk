"""OneCloud's passover: what OneAI is offered there, the Records counts, and
where requested files land.

The panel is told the folder and the chosen file by the explorer itself
(`OneCloud.here`), and offers a file's suggestions only with one chosen: the
section `file` is what keys them. Records never counts a file on a record the
reader may not open, and never lists a conversation's uploads or an
assignment's as records.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

AI = tree.APP / "one_storage" / "ai.py"
NAMESPACE = tree.APP / "one_storage" / "namespace.py"
REQUESTS = tree.APP / "one_storage" / "file_requests.py"
HOOKS = tree.APP / "hooks.py"
LAUNCHER = tree.APP / "public" / "js" / "oneai.js"
EXPLORER = tree.APP / "public" / "js" / "onecloud.js"


def _function(where: Path, name: str) -> str:
	for node in ast.walk(ast.parse(where.read_text(encoding="utf-8"))):
		if isinstance(node, ast.FunctionDef) and node.name == name:
			return ast.unparse(node)
	raise AssertionError(f"{name} is not in {where.name}")


def test_the_panel_is_offered_a_file_only_with_one_chosen():
	source = AI.read_text(encoding="utf-8")
	assert '"page:onecloud"' in source and '"page:onecloud/file"' in source
	launcher = LAUNCHER.read_text(encoding="utf-8")
	assert 'cloud && cloud.file ? "file" : ""' in launcher
	assert "static here()" in EXPLORER.read_text(encoding="utf-8")


def test_every_onecloud_tool_is_registered():
	hooks = HOOKS.read_text(encoding="utf-8")
	for name in ("open_file", "who_can_see", "largest_files"):
		assert f"onedesk.one_storage.ai.{name}" in hooks
	assert "onedesk.one_storage.ai.SUGGESTIONS" in hooks
	assert "onedesk.one_storage.ai.page" in hooks


def test_a_file_is_read_only_after_the_explorers_own_rule():
	"""Each tool about a file goes through `_file`, which is `namespace.may`."""
	assert "ns.may(item)" in _function(AI, "_file")
	for name in ("open_file", "who_can_see"):
		assert "_file(file)" in _function(AI, name)


def test_records_counts_only_what_the_reader_may_open():
	counted = _function(NAMESPACE, "_readable_files")
	assert "frappe.get_list" in counted
	assert "count(*)" not in _function(NAMESPACE, "record_doctypes")
	unlisted = NAMESPACE.read_text(encoding="utf-8")
	assert '"AI Chat", "ToDo"' in unlisted


def test_requested_files_get_a_folder_of_their_own():
	assert "api.make_folder(folder or ns.MY" in _function(REQUESTS, "_where")
	assert "_called(person.email)" in _function(REQUESTS, "_their_folder")


def test_the_explorer_uses_frappes_menus():
	explorer = EXPLORER.read_text(encoding="utf-8")
	assert "new frappe.ui.ContextMenu(" in explorer and "new frappe.ui.Dropdown(" in explorer
	assert 'class="es-menu' not in explorer and 'class="es-button"' not in explorer
