"""A workbook's cells as Python reads them: column letters, a cell's name,
and the cells a sheet holds. README, Under the hood.
"""

import re

CELL = re.compile(r"^([A-Z]{1,3})([1-9][0-9]{0,6})$")


def letters(col: int) -> str:
	"""0 → A, 26 → AA. Pure."""
	out, col = "", col + 1
	while col:
		col, rest = divmod(col - 1, 26)
		out = chr(65 + rest) + out
	return out


def cells_of(data: dict, sheet: str) -> dict[tuple[int, int], object]:
	"""A sheet's cells by (row, col), from the saved workbook. Pure."""
	held = ((data.get("sheet") or {}).get("sheets") or {}).get(sheet) or {}
	out = {}
	for row, values in (held.get("rows") or {}).items():
		for col, value in enumerate(values or []):
			if value not in (None, ""):
				out[(int(row), col)] = value
	return out
