"""What a module declares, and where it declares it.

A clause or a subprocessor, registered at import time from `<module>/legal.py`,
and given out in a stable order so a document's hash moves only with its text.
"""

CLAUSES: dict[tuple[str, str], list[dict]] = {}

SUBPROCESSORS: dict[str, dict] = {}


def clause(
	*, document: str, section: str, key: str, module: str, body: str, order: int = 100, heading: str = ""
) -> None:
	"""Register one paragraph of one document.

	`key` is stable and unique within its document: it is what a translation
	keys off and what a diff of two versions is expressed in.
	"""
	body = " ".join(body.split())
	if not body:
		raise ValueError(f"{module}: clause {key} has no text")

	slot = CLAUSES.setdefault((document, section), [])
	if any(one["key"] == key for one in slot):
		raise ValueError(f"clause {key} is declared twice in {document}/{section}")
	slot.append(
		{
			"key": key,
			"module": module,
			"heading": heading,
			"body": body,
			"order": order,
		}
	)


def subprocessor(
	*, name: str, purpose: str, module: str, data: str, where: str, safeguard: str, url: str = ""
) -> None:
	"""Register a third party that receives customer data.

	One company is one row with several uses. `where` belongs to the use, and the
	safeguard to the company.
	"""
	entry = SUBPROCESSORS.get(name)
	use = {"module": module, "purpose": purpose, "data": data, "where": where}

	if entry is None:
		SUBPROCESSORS[name] = {
			"name": name,
			"url": url,
			"safeguard": safeguard,
			"uses": [use],
		}
		return

	if entry["safeguard"] != safeguard:
		raise ValueError(
			f"{name} is declared with two different safeguards; the contract with a company is one contract"
		)
	entry["uses"].append(use)


def clauses_for(document: str, section: str) -> list[dict]:
	"""One section's clauses, in the order they will be read."""
	found = CLAUSES.get((document, section), [])
	return sorted(found, key=lambda one: (one["order"], one["module"], one["key"]))


def subprocessor_rows() -> list[dict]:
	"""Every subprocessor, alphabetically, with its purposes in module order."""
	rows = []
	for entry in sorted(SUBPROCESSORS.values(), key=lambda one: one["name"].lower()):
		rows.append(
			{
				**entry,
				"uses": sorted(entry["uses"], key=lambda one: (one["module"], one["purpose"])),
			}
		)
	return rows


def reset() -> None:
	"""Empty both registries. For tests, and for nothing else."""
	CLAUSES.clear()
	SUBPROCESSORS.clear()
