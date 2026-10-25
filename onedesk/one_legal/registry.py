"""What a module declares, and where it declares it.

A clause or a subprocessor, registered at import time from `<module>/legal.py`,
and given out in a stable order so a document's hash moves only with its text.
"""

CLAUSES: dict[tuple[str, str], list[dict]] = {}

SUBPROCESSORS: dict[str, dict] = {}

SERVICES: dict[str, dict] = {}


def clause(
	*,
	document: str,
	section: str,
	key: str,
	module: str,
	body: str,
	order: int = 100,
	heading: str = "",
	meets: tuple = (),
) -> None:
	"""Register one paragraph of one document.

	`key` is stable and unique within its document: it is what a translation
	keys off and what a diff of two versions is expressed in. `meets` names
	the duties in laws.py it is there for.
	"""
	from .laws import duties

	body = " ".join(body.split())
	if not body:
		raise ValueError(f"{module}: clause {key} has no text")
	unknown = sorted(set(meets) - set(duties()))
	if unknown:
		raise ValueError(f"{module}: clause {key} meets duties laws.py doesn't have: {unknown}")

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
			"meets": tuple(meets),
		}
	)


def subprocessor(
	*,
	name: str,
	purpose: str,
	module: str,
	data: str,
	where: str,
	safeguard: str,
	url: str = "",
	service: str = "",
) -> None:
	"""Register a third party that receives customer data.

	One company is one row with several uses. `where` belongs to the use, and the
	safeguard to the company. A use that only happens while an optional
	`service` is on names it, so a workspace that hasn't turned it on sees it
	struck through.
	"""
	entry = SUBPROCESSORS.get(name)
	use = {"module": module, "purpose": purpose, "data": data, "where": where, "service": service}

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


def service(*, key: str, module: str, title: str, does: str, sends: str, off: str, hosts: tuple) -> None:
	"""Register something a module sends out only once a workspace
	administrator turns it on and agrees to it (docs/READY.md, mechanism 13):
	what it does, what it sends, what happens while it is off, and the hosts
	it calls, which only `services.call` may reach. Its companies are the
	subprocessor uses that name it."""
	if key in SERVICES:
		raise ValueError(f"service {key} is declared twice")
	SERVICES[key] = {
		"key": key,
		"module": module,
		"title": title,
		"does": " ".join(does.split()),
		"sends": " ".join(sends.split()),
		"off": " ".join(off.split()),
		"hosts": tuple(hosts),
	}


def services_of(module: str | None = None) -> list[dict]:
	"""The optional services, a module's or all, each with the companies it
	sends to, in the order they are declared."""
	return [
		{
			**one,
			"companies": [
				{"name": row["name"], **use}
				for row in subprocessor_rows()
				for use in row["uses"]
				if use["service"] == one["key"]
			],
		}
		for one in SERVICES.values()
		if module is None or one["module"] == module
	]


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
	SERVICES.clear()
