"""frappe's calls used as frappe takes them (point 8).

A dialog's or a step's form is a FieldGroup, whose `set_value` takes one field
and a value. Given a dict it sets nothing and says nothing, so several fields
go through `set_values`. A form's `frm.set_value` takes either. A desk button
is frappe's `frappe.ui.button`, and its look changes through frappe's calls.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DICT_TO_FIELD_GROUP = re.compile(r"\b(?:dialog|d|dlg|form|fields?|group)\.set_value\(\s*\{")

HAND_BUTTON = re.compile(r"""class=["'](?:[^"']*\s)?btn(?:\s[^"']*)?["']|(?:add|remove|toggle)Class\(\s*["']btn-""")


def _sources():
	for folder in ("onedesk/public/js", "frontend/src"):
		for path in sorted((ROOT / folder).rglob("*")):
			if path.suffix in (".js", ".vue", ".ts") and "dist" not in path.parts:
				yield path


def test_a_field_group_is_given_one_value_at_a_time():
	found = [
		f"{path.relative_to(ROOT)}:{n}"
		for path in _sources()
		for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
		if DICT_TO_FIELD_GROUP.search(line)
	]
	assert not found, f"set_values for several fields: {found}"


def _desk_sources():
	for path in sorted((ROOT / "onedesk").rglob("*.js")):
		if not {"dist", "node_modules", "www"} & set(path.parts):
			yield path


def test_a_button_is_frappes():
	assert HAND_BUTTON.search('`<button class="btn btn-xs btn-default">`')
	assert HAND_BUTTON.search('add_custom_button(label, fn).addClass("btn-primary")')
	assert not HAND_BUTTON.search('`<button class="btn-reset os-photo">`')
	found = [
		f"{path.relative_to(ROOT)}:{n}"
		for path in _desk_sources()
		for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
		if HAND_BUTTON.search(line)
	]
	assert not found, f"frappe.ui.button for a button, change_custom_button_type or button.dress for its look: {found}"
