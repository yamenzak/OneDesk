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
		if isinstance(node, ast.Assign) and any(
			isinstance(t, ast.Name) and t.id.isupper() for t in node.targets
		):
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
	product = _load(RUA / "setup.py", {"kind"})["kind"]
	assert product("Aluminum Curtainwall Fix Panel With Sliding Window") == "Curtain Wall"
	assert product("ACP cladding to the facade") == "ACP Cladding"
	assert product("Metallic Bronze Colour Aluminum Composite Panel") == "ACP Cladding"
	assert product("Steel Floor Mounted Handrail ( Staircase 1 & Staircase 2 )") == "Steel Handrail"
	assert product("120cm Glass Handrail at Balcony Area (8mm+1.52pvb+8mm)") == "Glass Handrail"
	assert product("Aluminum Double Leaf Louver at L.V. Room") == "Louver"
	assert product("Something nobody named") == "Aluminium Works"


def test_the_costing_template_asks_the_same_question_as_the_importer():
	space = _load(RUA / "setup.py", {"kind_formula", "_on_item"})
	said = space["kind_formula"]()
	assert said.startswith('=IF(Costing!A6:A="","",IF(ISNUMBER(SEARCH("louv",Costing!B6:B)),"Louver",')
	assert 'IF(ISNUMBER(SEARCH("steel",Costing!B6:B))*ISNUMBER(SEARCH("handrail",Costing!B6:B)),"Steel Handrail",' in said
	assert said.endswith('"Aluminium Works"' + ")" * (len(space["KINDS"]) + 1))


def test_a_costing_template_is_headers_and_formulas_only():
	space = _load(RUA / "setup.py", {"kind_formula", "costing_items"})
	for spec in space["COSTINGS"]:
		assert all(one is None or not one[:1].isdigit() for one in spec["head"]), "headers, not figures"
		assert all(formula.startswith("=") for formula in spec["line"].values()), "nothing typed, only formulas"
		marked = set("".join(spec["kinds"].values()))
		assert marked <= {chr(65 + at) for at in range(len(spec["head"]))}, "every marked column is a column"
		assert set(spec["kinds"]["key"]) <= set(spec["kinds"]["money"])
	items = space["costing_items"](6, 10)
	assert items["one_length"] == '=IF(Costing!A6:A="","",IF(ISNUMBER(Costing!D6:D),Costing!D6:D*10,""))', "centimetres to millimetres"
	assert items["rate"] == '=IF(Costing!A6:A="","",Costing!P6:P/Costing!C6:C)'


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


def _projects():
	space = _load(IMPORTER / "projects.py", {"clean", "folded", "home", "own_contracts"})
	space["clean"] = lambda text: " ".join(str(text or "").split())
	return space


def test_an_original_contract_is_the_main_projects_own_work():
	space = _projects()
	assert space["folded"]({"name": "Original Contract: School", "parent1": "School"})
	assert space["folded"]({"name": "Original Scope : Court", "parent1": "Court"})
	assert not space["folded"]({"name": "Aluminum Variation: School", "parent1": "School"})
	assert not space["folded"]({"name": "Original Contract", "parent1": None})


def test_a_main_contract_that_totals_its_parts_is_not_ordered_twice():
	own, beyond = _projects()["own_contracts"](
		[
			{"name": "School", "contract_value": 6314437.5},
			{"name": "Original Contract: School", "parent1": "School", "contract_value": 6065259.45},
			{"name": "Variation: School", "parent1": "School", "contract_value": 245437.5},
			{"name": "Termination: School", "parent1": "School", "contract_value": 366712.5},
			{"name": "Villa", "contract_value": 300000},
			{"name": "Extra Doors: Villa", "parent1": "Villa", "contract_value": 36750},
		]
	)
	assert own["School"] == 6065259.45, "the main project keeps only the work folded into it"
	assert own["Variation: School"] == 245437.5 and own["Termination: School"] == 366712.5
	assert own["Villa"] == 300000 and own["Extra Doors: Villa"] == 36750, (
		"an add-on is not inside its main contract"
	)
	assert "School" in beyond and "Villa" not in beyond


def test_a_main_contract_above_its_parts_is_right_and_the_rest_is_its_own_work():
	own, beyond = _projects()["own_contracts"](
		[
			{"name": "Court", "contract_value": 1314550.66},
			{"name": "Original Scope: Court", "parent1": "Court", "contract_value": 1034652.15},
			{"name": "Grill: Court", "parent1": "Court", "contract_value": 221812.5},
			{"name": "Curtain Wall: Court", "parent1": "Court", "contract_value": 42738.16},
		]
	)
	assert round(own["Court"], 2) == 1050000.0, "the main's total stands; its own work takes the difference"
	assert round(beyond["Court"], 2) == 15347.85
	assert round(sum(own.values()), 2) == 1314550.66


def test_a_sub_project_merged_into_the_main_contract_adds_nothing():
	space = _projects()
	projects = [
		{"name": "School", "contract_value": 6314437.5},
		{"name": "Original Contract: School", "parent1": "School", "contract_value": 6065259.45},
		{"name": "Variation: School", "parent1": "School", "contract_value": 245437.5},
		{"name": "Termination: School", "parent1": "School", "contract_value": 366712.5},
	]
	merged = {"Variation: School"}
	own, beyond = space["own_contracts"](projects, merged)
	assert own == {"School": 6065259.45, "Termination: School": 366712.5}, "the variation is in the main LPO"
	assert beyond["School"] < 0, "the main said less than its parts, which stand"
	assert (
		space["folded"](projects[2], merged)
		and space["home"](projects, "Variation: School", merged) == "School"
	)


def _payments():
	return _load(IMPORTER / "payments.py", {"references", "copies"})


def test_a_bank_reference_reads_the_same_however_it_was_typed():
	references = _payments()["references"]
	assert references("002031, 002419") == {"2031", "2419"}
	assert references(" 033IPP227642975 ") == {"33IPP227642975"}
	assert references("") == set() and references(None) == set()


def test_a_payment_entered_again_on_another_part_of_the_job_is_a_copy():
	copies = _payments()["copies"]
	top = {"School": "School", "Main: School": "School", "Villa": "Villa"}
	pay = lambda name, project, amount, ref, date, linked=None, made="2026-01-01": {  # noqa: E731
		"name": name,
		"project": project,
		"type": "Receive",
		"amount": amount,
		"ref_number": ref,
		"date": date,
		"related_docname": linked,
		"creation": made,
	}
	found = copies(
		[
			pay("R1", "School", 800000, "002031", "2026-03-10", "INV-1"),
			pay("R2", "School", 800000, "002419", "2026-03-11", "INV-2"),
			pay("R3", "Main: School", 1600000, "002031, 002419", "2026-03-10", made="2026-04-14"),
			pay("R4", "Main: School", 500000, "002743", "2026-06-26", made="2026-06-26"),
			pay("R5", "School", 500000, "002743", "2026-06-26", "INV-3"),
			pay("R6", "Main: School", 78671.25, "000472", "2025-01-22", made="2026-04-08"),
			pay("R7", "School", 78671.25, None, "2025-01-22", "INV-4"),
			pay("R8", "Villa", 50000, "009999", "2026-02-01"),
			pay("R9", "Villa", 50000, "009998", "2026-02-01"),
		],
		top,
	)
	assert found == {"R3": "R1", "R4": "R5", "R6": "R7"}, "the copy goes, the one linked to an invoice stays"


def _figures():
	space = {"flt": flt}
	for node in ast.parse((RUA / "settle.py").read_text()).body:
		if isinstance(node, ast.FunctionDef) and node.name == "figures":
			exec(ast.unparse(node), space)
	return space["figures"]


def test_retention_kept_off_what_was_typed_in_is_added_on_top():
	found = {name: (now, after) for name, now, after in _figures()(1000, 50, 0, 0, 100)}
	assert found == {"billed": (1000, 1100), "vat": (50, 50), "owed": (0, 0), "held": (0, 100)}


def test_retention_inside_an_invoice_comes_off_it_with_its_vat():
	taken = {"net_total": 1000, "total_taxes_and_charges": 50}
	found = {name: (now, after) for name, now, after in _figures()(1000, 50, 0, 0, 100, taken)}
	assert found == {"billed": (1000, 1000), "vat": (50, 45), "owed": (0, -105), "held": (0, 100)}


def test_an_lpo_line_whose_total_is_not_its_quantity_times_its_price_keeps_the_total():
	rest = _load(IMPORTER / "buying.py", {"rest"})["rest"]
	assert rest(3369, 80, 269572.8) == 52.8, "3,369.66 m2 kept as 3,369"
	assert rest(3369, 80, 269520) == 0 and rest(2, 10.005, 20.01) == 0
	assert rest(5, 100, 0) == 0, "a line with no total says nothing"


def test_rua_says_which_sub_projects_were_merged_into_their_main_contract():
	source = (IMPORTER / "projects.py").read_text()
	assert "Aluminum Variation: Al-Ittihad Private School" in source, (
		"folds on Rua's site with nothing to set"
	)
