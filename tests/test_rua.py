"""Rua's private app: the importer reads the old app's numbers the way the
old app meant them. See private/rua/README.md."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

RUA = tree.APP.parent / "private" / "rua" / "rua"
IMPORTER = RUA / "importer"


def flt(value, places=None):
	number = float(value or 0)
	return round(number, places) if places is not None else number


def _load(path, names, **space):
	space = {"flt": flt, "re": re, **space}
	for node in ast.parse(path.read_text()).body:
		if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.isupper() for t in node.targets):
			exec(ast.unparse(node), space)
		if isinstance(node, ast.FunctionDef) and node.name in names:
			exec(ast.unparse(node), space)
	return space


def test_a_size_is_read_in_millimetres_whatever_unit_the_old_app_wrote():
	millimetres = _load(IMPORTER / "quotations.py", {"millimetres"})["millimetres"]
	assert millimetres("200.0 cm") == 2000
	assert millimetres("697.5 cm") == 6975
	assert millimetres("6 m") == 6000
	assert millimetres("1500 mm") == 1500
	assert millimetres("0 cm") == 0
	assert millimetres(None) == 0


def test_a_line_goes_under_the_product_its_words_name():
	product = _load(IMPORTER / "quotations.py", {"product"})["product"]
	assert product("Aluminum Curtainwall Fix Panel With Sliding Window") == "Curtain Wall"
	assert product("ACP cladding to the facade") == "ACP Cladding"
	assert product("Something nobody named") == "Aluminium Works"


def test_a_trn_is_fifteen_digits_or_nothing():
	trn = _load(IMPORTER / "parties.py", {"trn"})["trn"]
	assert trn("104172052300003") == "104172052300003"
	assert trn("0") is None and trn("") is None and trn(None) is None


def test_the_retention_an_invoice_held_is_read_from_its_amounts():
	held = _load(IMPORTER / "sales.py", {"held"})["held"]
	assert held({"amount": 83250, "amount_after_retention": 74925, "retention_percentage": 0}) == 10
	assert held({"amount": 137500, "amount_after_retention": 137500, "retention_percentage": 0}) == 0


def test_numbers_go_on_from_the_highest_the_old_app_gave():
	counted = _load(IMPORTER / "numbers.py", {"counted"})["counted"]
	top = counted(["RC-INV-2500001", "RC-INV-2500037", "RC-INV-2600019", "RC-EMP-00071", "PROJ-0001", None])
	assert top == {"RC-INV-25": 37, "RC-INV-26": 19, "RC-EMP-": 71}


def test_a_roll_call_line_says_one_thing():
	state = _load(IMPORTER / "attendance.py", {"state"})["state"]
	assert state({"present": True, "late": False, "absent": False}) == "Present"
	assert state({"present": False, "late": True, "absent": False}) == "Present"
	assert state({"present": False, "late": False, "absent": True}) == "Absent"
	assert state({"present": False, "late": False, "absent": False, "status": "leave"}) == "On Leave"
	assert state({"present": False, "late": False, "absent": False}) is None


def test_a_formatted_report_figure_reads_back_as_a_number():
	number = _load(IMPORTER / "check.py", {"number"})["number"]
	assert number("AED 18,413,592.45") == 18413592.45
	assert number(12.5) == 12.5


def test_the_import_reads_and_never_writes():
	source = (RUA / "source.py").read_text()
	assert ".get(" in source and not re.search(r"\.(post|put|delete|patch)\(", source)


def test_rua_is_a_private_app_that_needs_one():
	hooks = (RUA / "hooks.py").read_text()
	assert 'required_apps = ["onedesk"]' in hooks
	assert "one_private_app = {" in hooks
