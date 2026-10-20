"""A line's size, in whatever length it is typed in: what it comes to and how
it reads (one_inventory/measure.py)."""

import ast
from pathlib import Path

MEASURE = Path(__file__).resolve().parent.parent / "onedesk" / "one_inventory" / "measure.py"


def _pure(*names):
	body = ast.parse(MEASURE.read_text(encoding="utf-8"))
	kept = [
		node
		for node in body.body
		if (isinstance(node, ast.FunctionDef) and node.name in names)
		or (isinstance(node, ast.Assign) and any(getattr(t, "id", None) in names for t in node.targets))
	]
	room = {"cint": lambda v: int(float(v or 0)), "flt": lambda v: float(v or 0)}
	exec(compile(ast.Module(body=kept, type_ignores=[]), str(MEASURE), "exec"), room)
	return room


def test_a_size_counts_in_its_own_length():
	room = _pure("POWER", "amount", "size", "described")
	amount, size, described = room["amount"], room["size"], room["described"]
	assert round(amount("Area", 4, 1200, 800), 4) == 3.84, "millimetres, as before"
	assert round(amount("Length", 6, 240, metre=0.01), 4) == 14.4, "centimetres"
	assert round(amount("Volume", 2, 100, 50, 20, metre=0.01), 4) == 0.2, "a volume is three sides"
	assert round(amount("Area", 1, 48, 96, metre=0.0254), 4) == 2.9729, "inches"
	assert amount("No", 1, 1, 1) == 0.0
	assert size("Volume", 2, 100, 50, 20, unit="cm") == "2 × 100 × 50 × 20 cm"
	assert size("Area", 1, 1200, 800, 30) == "1200 × 800 mm", "a height an area doesn't use isn't said"
	assert described(20525, 3500) == "20525 × 3500 mm" and described(600, 400, 300, "in") == "600 × 400 × 300 in"
	assert described(0, 10) is None
