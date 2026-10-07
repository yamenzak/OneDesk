"""frappe's calls used as frappe takes them (point 8).

A dialog's or a step's form is a FieldGroup, whose `set_value` takes one field
and a value. Given a dict it sets nothing and says nothing, so several fields
go through `set_values`. A form's `frm.set_value` takes either.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: A FieldGroup handed a dict: a dialog, a step's form, or a field group.
DICT_TO_FIELD_GROUP = re.compile(r"\b(?:dialog|d|dlg|form|fields?|group)\.set_value\(\s*\{")


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
