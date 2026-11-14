"""The first agents' gate (docs/ARC-AI.md, Build order): of 50 invoices
that arrive by mail, the accountant drafts each and a person corrects at
most 2. `run` scores the samples on a site, `tally` real use
(one_ai/AGENTS.md, The agents, says how each is run)."""

import json
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from frappe.utils import flt, getdate

FIELDS = ("supplier_name", "bill_no", "bill_date", "grand_total", "currency", "due_date")
GATE = 50
MOST_CORRECTED = 2
SAMPLES = Path(__file__).resolve().parents[3] / "tests" / "samples"
REAL = SAMPLES / "agents" / "invoices"
BILL = "Purchase Invoice"


def expected(spec: dict) -> dict:
	"""What the draft must say: the sample's `expect`, else what the
	invoice itself says, as its reading answer gives it. Pure."""
	if spec.get("expect"):
		return dict(spec["expect"])
	read = (spec.get("answers") or {}).get("intake_read") or {}
	money = read.get("money") or {}
	sender = next((one.get("name") for one in read.get("parties") or [] if one.get("role") == "Sender"), None)
	due = next((one.get("date") for one in read.get("dates") or [] if one.get("what") == "Due"), None)
	said = {"supplier_name": sender, "bill_no": read.get("number"), "bill_date": read.get("issued"), "grand_total": money.get("gross"), "currency": money.get("currency"), "due_date": due}
	made = next((one.get("values") or {} for one in spec.get("makes") or [] if one.get("doctype") == BILL), {})
	return {key: value for key, value in {**said, **made}.items() if key in FIELDS and value not in (None, "")}


def corrections(expect: dict, drafted: dict | None) -> list[str]:
	"""The fields a person would have to correct, or ["no draft"]. Pure."""
	if not drafted:
		return ["no draft"]
	return [key for key, value in expect.items() if not _same(key, value, drafted.get(key))]


def _same(key: str, want, got) -> bool:
	if key == "grand_total":
		return abs(flt(want) - flt(got)) < 0.01
	if key.endswith("_date"):
		return bool(got) and getdate(want) == getdate(got)
	return str(want or "").strip().casefold() == str(got or "").strip().casefold()


def scored(results: list[dict]) -> dict:
	"""How many samples, drafted, corrected (a missing draft counts), and
	whether the gate is passed: 50 or more, at most 2 corrected. Pure."""
	corrected = [one for one in results if one["corrections"]]
	return {
		"samples": len(results),
		"drafted": sum(1 for one in results if one["corrections"] != ["no draft"]),
		"corrected": len(corrected),
		"passed": len(results) >= GATE and len(corrected) <= MOST_CORRECTED,
		"wrong": {one["sample"]: one["corrections"] for one in corrected},
	}


def invoice_samples() -> list[Path]:
	"""Every sample of an invoice: the real ones, then Intake's that make a bill."""
	intake = [path for path in sorted((SAMPLES / "intake").glob("*/*.json")) if any(one.get("doctype") == BILL for one in json.loads(path.read_text()).get("makes") or [])]
	return [*sorted(REAL.glob("*.json")), *intake]


def run(live: int = 0) -> dict:
	"""Every invoice sample through the agents on this site, scored."""
	import frappe

	results = [{"sample": f"{path.parent.name}/{path.stem}", "corrections": corrections(expected(json.loads(path.read_text())), _drafted(path, bool(int(live))))} for path in invoice_samples()]
	frappe.set_user("Administrator")
	return scored(results)


def _drafted(path: Path, live: bool) -> dict | None:
	import frappe

	from onedesk.one_ai.agents import connect, work
	from onedesk.one_ai.reading import matters
	from onedesk.one_demo import samples

	spec = json.loads(path.read_text())
	content = path.with_name(spec["file"]).read_bytes()
	with ExitStack() as held:
		if live:
			held.enter_context(patch("onedesk.one_ai.reading.pipeline.later", lambda *a, **k: None))
		else:
			held.enter_context(samples._answered(path.name, spec.get("answers") or {}, []))
		held.enter_context(samples.unkept())
		held.enter_context(patch.object(connect, "on", lambda: True))
		held.enter_context(patch.object(connect, "wake", work.here))
		samples._arrive(spec["file"], content)
		readings = samples.readings_of(path)
		for name in frappe.get_all("Reading", filters={"name": ["in", readings or [""]], "state": "Understood"}, pluck="name"):
			matters.act_now(name)
		return drafted_for(samples.readings_of(path))


def drafted_for(readings: list[str]) -> dict | None:
	"""The accountant's draft for these readings, in the fields scored."""
	import frappe

	from onedesk.one.registry import agents

	made = frappe.db.get_value("Reading Action", {"reading": ["in", readings or [""]], "agent": agents.email("one_book"), "target_doctype": BILL, "kind": "Create", "level": "Done"}, "target_name")
	if not made or not frappe.db.exists(BILL, made):
		return None
	held = frappe.db.get_value(BILL, made, ["supplier", "bill_no", "bill_date", "grand_total", "currency", "due_date"], as_dict=True)
	return {**held, "supplier_name": frappe.db.get_value("Supplier", held.supplier, "supplier_name")}


def tally(since: str | None = None) -> dict:
	"""The gate on real use: every draft the accountant made since a day,
	and those a person changed in a scored field or took back."""
	import frappe

	from onedesk.one.registry import agents

	accountant = agents.email("one_book")
	filters = {"agent": accountant, "target_doctype": BILL, "kind": "Create", "level": ["in", ("Done", "Undone")]}
	if since:
		filters["creation"] = [">=", since]
	rows = frappe.get_all("Reading Action", filters=filters, fields=["name", "level", "target_name"])
	results = [{"sample": one.target_name, "corrections": ["taken back"] if one.level == "Undone" else changed(one.target_name, accountant)} for one in rows]
	return scored(results)


def changed(name: str, agent: str) -> list[str]:
	"""The scored fields, and the lines, anyone but the agent changed on a bill."""
	import frappe

	found = set()
	for data in frappe.get_all("Version", filters={"ref_doctype": BILL, "docname": name, "owner": ["!=", agent]}, pluck="data"):
		said = json.loads(data or "{}")
		found |= {one[0] for one in said.get("changed") or [] if one[0] in ("supplier", *FIELDS)}
		if said.get("added") or said.get("removed") or said.get("row_changed"):
			found.add("items")
	return sorted(found)
