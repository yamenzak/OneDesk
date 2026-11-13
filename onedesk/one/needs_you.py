"""What a module's Home lists under Needs You: the first few of each kind,
and how many there are in all. Pure, the same on every Home."""

FEW = 5


def kept(rows: list) -> dict:
	"""The first FEW rows, and how many there are."""
	return {"rows": rows[:FEW], "count": len(rows)}
