"""TrustCenter: the documents assemble, every change to them is a decision, and
every company One sends data to is in the Subprocessors list.

Pure: the registry, the documents and every module's `trust.py` import nothing
of frappe, so the documents are assembled here exactly as a site assembles them.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree  # noqa: E402

from onedesk.one import ready  # noqa: E402
from onedesk.trust_center import assemble, documents, registry  # noqa: E402

VERSIONS = {
	"terms": "13.adb8cc97",
	"aup": "1.87e4fdd0",
	"privacy": "28.6d765c4c",
	"cookies": "2.946a434c",
	"dpa": "7.a01dc637",
	"subprocessors": "5.148fd382",
	"ai": "25.4c5ce568",
	"licences": "1.c71daf62",
}

HOSTS = {
	"api.cloudflare.com": "Cloudflare, Inc.",
	"dash.cloudflare.com": "Cloudflare, Inc.",
	"gateway.ai.cloudflare.com": "Cloudflare, Inc.",
	"cloudflare-dns.com": "Cloudflare, Inc.",
	"api.stripe.com": "Stripe, Inc.",
	"checkout.stripe.com": "Stripe, Inc.",
	"billing.stripe.com": "Stripe, Inc.",
	"www.gravatar.com": "Automattic Inc.",
	"t1.gstatic.com": "Google LLC",
	"fonts.google.com": "Google LLC",
	"fonts.googleapis.com": "Google LLC",
	"fonts.gstatic.com": "Google LLC",
	"onedesk.one_admin.proxy.ai_web_search": "Exa Labs, Inc.",
	"api.openweathermap.org": "OpenWeather Ltd",
	"news.google.com": "Google LLC",
	"onedesk.one_admin.proxy.google_news": "Google LLC",
	"onedesk.one_admin.proxy.weather_reading": "OpenWeather Ltd",
	"onedesk.one_admin.proxy.weather_places": "OpenWeather Ltd",
	"onedesk.one_admin.proxy.copies_agreed": "Oracle Corporation",
	"onedesk.one_admin.proxy.copies_start": "Oracle Corporation",
	"fcm.googleapis.com": None,
	"developers.cloudflare.com": None,
	"ai.google.dev": None,
	# Google's address for a made video, rewritten onto the gateway and never called.
	"generativelanguage.googleapis.com": None,
	# Feeds the demo workspace adds: read for it, so the publisher is not ours to declare.
	"www.thenationalnews.com": None,
	"www.khaleejtimes.com": None,
	"feeds.bbci.co.uk": None,
}


def moved(found: dict, recorded: dict) -> dict:
	"""The documents whose version is not the one recorded, with both. Pure."""
	return {key: (recorded.get(key), now) for key, now in found.items() if recorded.get(key) != now}


def test_every_document_is_at_the_version_recorded():
	changed = moved({one["key"]: one["version"] for one in assemble.documents()}, VERSIONS)
	assert not changed, (
		"These documents changed: "
		+ ", ".join(f"{key} {was} → {now}" for key, (was, now) in changed.items())
		+ (
			". Material: bump its revision in trust_center/documents.py. A typo: record the new version above."
			if ready.PRODUCTION
			else ". Before production the agreements change freely: record the new version above."
		)
	)


def stray_clauses(clauses, sections: dict) -> list:
	"""The (document, section) places clauses aim at that no document has. Pure."""
	had = {(key, section) for key, rows in sections.items() for section, _heading in rows}
	return [place for place in clauses if place not in had]


def test_every_clause_is_in_a_section_its_document_has():
	assemble.documents()
	stray = stray_clauses(registry.CLAUSES, documents.SECTIONS)
	assert not stray, f"clauses aimed at sections that do not exist: {stray}"


def hosts_called(source: str) -> set[str]:
	"""The outside hosts a source calls over https, but frappe's, github's and examples. Pure."""
	return {host for host in re.findall(r"https://([a-z0-9.-]+\.[a-z]+)/", source) if not host.endswith(("frappe.io", "github.com", "example.com"))}


def unmapped(called: set, hosts: dict, declared: set) -> tuple[list, list]:
	"""The hosts HOSTS does not map, and the companies mapped but not declared. Pure."""
	unknown = sorted(host for host in called if host not in hosts)
	undeclared = sorted({hosts[host] for host in called if host in hosts and hosts[host] and hosts[host] not in declared})
	return unknown, undeclared


def test_every_company_one_calls_is_a_declared_subprocessor():
	assemble.documents()
	called = set()
	for path in tree.python():
		if "trust_center" in path.parts or path.name == "trust.py":
			continue
		called |= hosts_called(path.read_text(encoding="utf-8"))
	unknown, undeclared = unmapped(called, HOSTS, set(registry.SUBPROCESSORS))
	assert not unknown, f"One calls {unknown}: map each to its subprocessor in HOSTS, and declare it"
	assert not undeclared, f"called but not in the Subprocessors list: {undeclared}"


def unsaid_rungs(text: str, days: dict) -> list[str]:
	"""The rungs of the ladder whose days the terms do not say. Pure."""
	return [rung for rung in ("Overdue", "Suspended", "Archived") if f"{days[rung]} days" not in text]


def test_the_lifecycle_the_terms_describe_is_the_one_the_code_runs():
	from onedesk.one_admin.ladder import DAYS

	wrong = unsaid_rungs(assemble.text_of("terms"), DAYS)
	assert not wrong, wrong


def wrong_audiences(declared: dict, sections: dict) -> list[str]:
	"""What is wrong with who agrees to which document, and their order. Pure."""
	audiences = {key: one["audience"] for key, one in declared.items()}
	wrong = [key for key, who in (("privacy", "user"), ("terms", "customer"), ("aup", "both")) if audiences.get(key) != who]
	wrong += ["licences is agreed to"] if audiences.get("licences") is not None else []
	wrong += ["the documents and their sections are in different orders"] if list(declared) != list(sections) else []
	return wrong


def test_everybody_agrees_to_something_and_the_notices_to_nothing():
	wrong = wrong_audiences(documents.DOCUMENTS, documents.SECTIONS)
	assert not wrong, wrong


def promised(everything: str, ai: str) -> list[str]:
	"""What the agreements promise that is not built, or leave unsaid that is. Pure."""
	wrong = [said for said in ("full backup", "without somebody asking for it") if said in everything]
	if "turns reading on, OneAI reads the mail and files that arrive and acts on them" not in ai:
		wrong.append("OneAI's reading is not said")
	return wrong


def test_nobody_is_promised_what_is_not_built():
	"""OneApp's text promised a full backup from the settings and said nothing is
	ever written without somebody asking. Neither is true of OneDesk: OneAI's
	reading acts without being asked each time."""
	everything = " ".join(assemble.text_of(key) for key in documents.DOCUMENTS)
	wrong = promised(everything, assemble.text_of("ai"))
	assert not wrong, wrong


def stops_on_a_revision(source: str) -> list[str]:
	"""What a gate.py does that stops whoever agreed to an earlier revision,
	or no longer tells a new revision from a new hash. Pure."""
	import ast as _ast

	space = {}
	for node in _ast.parse(source).body:
		if isinstance(node, _ast.FunctionDef) and node.name in ("revision", "agreed"):
			exec(_ast.unparse(node), space)
	if "agreed" not in space:
		return ["no agreed"]
	wrong = []
	if not space["agreed"]("1.dcae3326", "1.94da7c45"):
		wrong.append("a new hash asks again")
	if space["agreed"]("1.dcae3326", "2.94da7c45"):
		wrong.append("a new revision is taken as agreed")
	if space["agreed"](None, "1.94da7c45"):
		wrong.append("nobody agreeing is taken as agreed")
	if not ('"accepted": bool(was)' in source and '"changed": bool(was) and not agreed(was, version)' in source):
		wrong.append("a later revision is not told as a change")
	return wrong


def test_only_a_first_agreement_stops_anybody():
	"""A later revision is notice, not a stop (docs/READY.md, mechanism 13):
	whoever agreed to an earlier one stands agreed, and the gate tells them
	it changed. `agreed` still tells a new revision from a new hash."""
	source = (Path(__file__).resolve().parents[2] / "onedesk" / "trust_center" / "gate.py").read_text(encoding="utf-8")
	wrong = stops_on_a_revision(source)
	assert not wrong, wrong


def badly_published(declared: dict, changes: list, baseline: dict, notice_days: int, production: bool, change_of) -> list[str]:
	"""A change published before production, a revision with no change, too
	little notice, or a change not said in one sentence. Pure."""
	import datetime

	wrong = []
	if not production and changes:
		wrong.append("Before production a change takes effect the day it is made: nothing goes in documents.CHANGES")
	for key, one in declared.items():
		if production and one["revision"] > baseline[key] and not change_of(key):
			wrong.append(f"{key} is at revision {one['revision']}: add it to documents.CHANGES")
	for change in changes:
		key = change["document"]
		published, effective = (datetime.date.fromisoformat(change[day]) for day in ("published", "effective"))
		if declared[key]["audience"] in ("customer", "both") and (effective - published).days < notice_days:
			wrong.append(f"{key} {change['revision']}: {notice_days} days' notice")
		if not (change["says"].endswith(".") and len(re.findall(r"[.!?](?:\s|$)", change["says"])) == 1):
			wrong.append(f"{key}: one sentence")
	return wrong


def test_a_change_is_published_ahead_of_the_day_it_takes_effect():
	"""From production on, every revision above the baseline is a published
	change, and one to what the workspace agrees to takes effect NOTICE_DAYS
	after it is published, at least, with what changed said in a sentence.
	Before it, the agreements change freely and nothing is published."""
	wrong = badly_published(documents.DOCUMENTS, documents.CHANGES, documents.BASELINE, documents.NOTICE_DAYS, ready.PRODUCTION, documents.change_of)
	assert not wrong, wrong


def unnamed_models(used, run_by, declared: set) -> dict:
	"""The models OneAI uses whose runner is not a subprocessor. Pure."""
	return {model: run_by(model) for model in used if run_by(model) not in declared}


def test_every_company_that_runs_a_model_is_a_declared_subprocessor():
	"""Whoever runs a model OneAI uses receives what it is sent, so each is a
	subprocessor the agreements name (one_ai/models.py RUN_BY)."""
	from onedesk.one_ai import models

	assemble.documents()
	unnamed = unnamed_models(models.used(), models.run_by, set(registry.SUBPROCESSORS))
	assert not unnamed, f"Models run by a company that is not a subprocessor: {unnamed}"


def unassembled(found: set, places) -> list[str]:
	"""The folders with a trust.py the registry does not place. Pure."""
	return sorted(found - set(places))


def test_every_modules_legal_file_is_assembled():
	from onedesk.trust_center.assemble import places

	wrong = unassembled({path.parent.name for path in tree.APP.glob("one*/trust.py")}, places())
	assert not wrong, f"not a folder or part in the registry: {wrong}"


def _sources() -> list[tuple[str, str]]:
	return [(path.name, path.read_text(encoding="utf-8")) for path in tree.python()]


def unserviced(services: dict, rows: list, hosts: dict, sources: list) -> list[str]:
	"""A service half declared, sending to nobody named, or reached without
	services.call, and a use naming a service nobody declared. Pure."""
	wrong = []
	for key, one in services.items():
		if not (one["hosts"] and one["off"] and one["sends"]):
			wrong.append(key)
		companies = {row["name"] for row in rows for use in row["uses"] if use["service"] == key}
		if not companies:
			wrong.append(f"{key} sends to nobody the Subprocessors list names")
		if not all(hosts.get(host) in companies for host in one["hosts"]):
			wrong.append(f"{key}: each host is one of its companies'")
		wrong += [
			f"{name} calls {key}'s host without services.call"
			for name, text in sources
			if name != "trust.py" and any(host in text for host in one["hosts"]) and "services.call(" not in text
		]
	uses = {use["service"] for row in rows for use in row["uses"] if use["service"]}
	if not uses <= set(services):
		wrong.append(f"a use names a service nobody declared: {sorted(uses - set(services))}")
	return wrong


def test_a_service_is_reached_only_through_services_call():
	"""An optional service's hosts are called only while a workspace has it
	on (docs/READY.md, mechanism 13): a file that names one goes through
	trust_center/services.call, each service sends to at least one declared
	company, and what it says while off is said."""
	assemble.documents()
	wrong = unserviced(registry.SERVICES, registry.subprocessor_rows(), HOSTS, _sources())
	assert not wrong, wrong


def unmet_duties(clauses: dict, laws: dict, duties) -> list[str]:
	"""The duties no clause meets, and a law or duty not said in a sentence. Pure."""
	met = {duty for rows in clauses.values() for one in rows for duty in one["meets"]}
	wrong = [f"no clause meets {duty}" for duty in duties if duty not in met]
	for law, one in laws.items():
		if not (one["title"] and one["duties"]):
			wrong.append(law)
		wrong += [
			f"{law}.{duty}: one sentence"
			for duty, said in one["duties"].items()
			if not (said.endswith((".", ")")) and len(re.findall(r"[.!?](?:\s|$)", said)) <= 2)
		]
	return wrong


def test_every_duty_a_law_puts_on_us_is_met_by_a_clause():
	"""laws.py lists the laws One answers and what each asks of us; a clause
	names the duties it meets (`meets=`), and no duty is left without one
	(docs/READY.md, mechanism 13)."""
	from onedesk.trust_center import laws

	assemble.documents()
	wrong = unmet_duties(registry.CLAUSES, laws.LAWS, laws.duties())
	assert not wrong, f"{wrong}. Write a clause, or say which clause meets a duty with meets="


LEGALESE = (
	"shall", "herein", "hereinafter", "hereby", "thereof", "whereas", "pursuant to", "notwithstanding",
	"aforementioned", "forthwith", "in no event", "the Company", "the Customer", "the Provider",
)  # fmt: skip


def legalese(clauses: dict) -> list[str]:
	"""Each word of LEGALESE a clause uses. Pure."""
	return [
		f"{one['module']} {one['key']}: {word}"
		for rows in clauses.values()
		for one in rows
		for word in LEGALESE
		if re.search(rf"\b{word}\b", one["body"], 0 if word != word.lower() else re.I)
	]


def long_sentences(texts: list, ours: set) -> list[str]:
	"""The sentences over 30 words in a module going through docs/READY.md. Pure."""
	return [
		f"{module} {key}: {len(sentence.split())} words: {sentence[:60]}…"
		for module, key, text in texts
		if module in ours
		for sentence in re.split(r"(?<=[.!?:])\s+", text)
		if len(sentence.split()) > 30
	]


def test_the_agreements_are_plain():
	"""docs/WORDING.md, The agreements: no clause in legalese, and a module
	going through docs/READY.md says one point to a sentence of 30 words at
	most, in its clauses, its subprocessors' uses and its services."""
	from onedesk.one import ready

	assemble.documents()
	found = legalese(registry.CLAUSES)
	assert not found, f"legalese: {found}"
	texts = [(one["module"], one["key"], one["body"]) for rows in registry.CLAUSES.values() for one in rows]
	texts += [(use["module"], row["name"], use["purpose"] + ". " + use["data"]) for row in registry.subprocessor_rows() for use in row["uses"]]
	texts += [(one["module"], one["key"], " ".join((one["does"], one["sends"], one["off"]))) for one in registry.SERVICES.values()]
	long = long_sentences(texts, set(ready.MODULES))
	assert not long, "one point to a sentence, 30 words at most:\n" + "\n".join(long)


def early_core(rows: list, in_effect, production: bool, declared_switchovers) -> list[str]:
	"""A company One can't work without, new to the agreements in effect,
	used before its switchover, and a use starting with one nobody declared. Pure."""
	wrong = []
	for row in rows:
		core = [use for use in row["uses"] if not use["service"]]
		if not production or row["name"] in in_effect or not core:
			continue
		early = [use["purpose"] for use in core if not use.get("starts")]
		if early:
			wrong.append(f"{row['name']} is new and One can't work without it, so it waits for its notice: give {early} starts= a switchover")
	wrong += [
		f"{row['name']} starts with {use['starts']}, which nobody declared"
		for row in rows
		for use in row["uses"]
		if use.get("starts") and use["starts"] not in declared_switchovers
	]
	return wrong


def switchover_wrong(one: dict, rows: list, hosts: dict, sources: list, today) -> list[str]:
	"""A switchover whose hosts are not its companies', reached without
	switchovers.when, or past its clean-by day. Pure."""
	key = one["key"]
	companies = {row["name"] for row in rows for use in row["uses"] if use.get("starts") == key}
	wrong = [] if all(hosts.get(host) in companies for host in one["hosts"]) else [f"{key}: each host is one of the companies it starts"]
	wrong += [
		f"{name} calls {key}'s host before its day; go through switchovers.when"
		for name, text in sources
		if name != "trust.py" and any(host in text for host in one["hosts"]) and "switchovers.when(" not in text
	]
	if today > one["clean_by"]:
		wrong.append(
			f"{key} took effect on {one['effective']}: remove the old way and the switchover, drop starts= from its "
			f"companies' uses and add them to documents.IN_EFFECT"
		)
	return wrong


def test_a_core_change_waits_for_its_day():
	"""A company One can't work without is used only from the day the notice
	of it said (docs/READY.md, mechanism 13). One the agreements in effect
	don't name comes in through a switchover: its uses say `starts`, the
	switchover names a published change, and its hosts are reached only
	through switchovers.when, which runs the old way until that day. A
	switchover in effect for longer than CLEAN_DAYS is due to go, with the
	old way, and its companies join documents.IN_EFFECT. Before production
	every company declared is in effect the day it is declared."""
	import datetime

	from onedesk.trust_center import switchovers

	assemble.documents()
	rows = registry.subprocessor_rows()
	wrong = early_core(rows, documents.IN_EFFECT, ready.PRODUCTION, registry.SWITCHOVERS)
	today = datetime.date.today()
	running = switchovers.all_of(today)
	sources = _sources() if running else []
	for one in running:
		wrong += switchover_wrong(one, rows, HOSTS, sources, today)
	assert not wrong, wrong


def misread_day(live, effective, key: str, day) -> list[str]:
	"""What a switchover's `live` and `effective` get wrong about its day. Pure."""
	import datetime

	wrong = []
	if live(key, day - datetime.timedelta(days=1)):
		wrong.append("new before its day")
	if not live(key, day):
		wrong.append("old on its day")
	if effective(key) != day:
		wrong.append("its day misread")
	return wrong


def test_a_switchover_runs_the_old_way_until_its_day():
	"""switchovers.when is old before the published change's day and new on
	it, read from documents.CHANGES alone."""
	import datetime

	from onedesk.trust_center import switchovers

	assemble.documents()
	change = {"document": "ai", "revision": 999, "published": "2026-01-01", "effective": "2026-01-31", "says": "A test."}
	documents.CHANGES.append(change)
	registry.SWITCHOVERS["test-switch"] = {"key": "test-switch", "module": "one", "document": change["document"], "revision": change["revision"], "does": "", "hosts": ()}
	try:
		wrong = misread_day(switchovers.live, switchovers.effective, "test-switch", datetime.date.fromisoformat(change["effective"]))
		assert not wrong, wrong
	finally:
		del registry.SWITCHOVERS["test-switch"]
		documents.CHANGES.remove(change)


def test_the_legal_rules_catch_their_examples():
	import datetime

	assert moved({"terms": "2.b", "aup": "1.a"}, {"terms": "1.a", "aup": "1.a"}) == {"terms": ("1.a", "2.b")}
	assert stray_clauses({("terms", "gone"): [], ("terms", "use"): []}, {"terms": [("use", "Use")]}) == [("terms", "gone")]
	assert hosts_called('x = "https://api.stripe.com/v1" + "https://github.com/a/"') == {"api.stripe.com"}
	assert unmapped({"api.new.com", "api.stripe.com"}, {"api.stripe.com": "Stripe, Inc."}, set()) == (["api.new.com"], ["Stripe, Inc."])
	assert unmapped({"api.stripe.com"}, {"api.stripe.com": "Stripe, Inc."}, {"Stripe, Inc."}) == ([], [])
	assert unsaid_rungs("Overdue after 7 days, suspended after 30 days.", {"Overdue": 7, "Suspended": 30, "Archived": 90}) == ["Archived"]
	good = {"privacy": {"audience": "user"}, "terms": {"audience": "customer"}, "aup": {"audience": "both"}, "licences": {"audience": None}}
	assert wrong_audiences(good, dict.fromkeys(good)) == []
	assert wrong_audiences({**good, "licences": {"audience": "user"}}, dict.fromkeys(reversed(good))) == [
		"licences is agreed to",
		"the documents and their sections are in different orders",
	]
	reading = "When an administrator turns reading on, OneAI reads the mail and files that arrive and acts on them."
	assert promised("Take a full backup from the settings.", reading) == ["full backup"]
	assert promised("", "") == ["OneAI's reading is not said"]
	gate = 'def revision(v):\n\treturn v.split(".", 1)[0] if v else None\n\ndef agreed(was, now):\n\treturn bool(was) and revision(was) == revision(now)\n'
	told = 'row = {"accepted": bool(was), "changed": bool(was) and not agreed(was, version)}\n'
	assert stops_on_a_revision(gate + told) == []
	assert stops_on_a_revision(gate.replace("revision(was) == revision(now)", "was == now") + told) == ["a new hash asks again"]
	assert stops_on_a_revision(gate) == ["a later revision is not told as a change"]
	docs = {"terms": {"revision": 2, "audience": "customer"}}
	change = {"document": "terms", "revision": 2, "published": "2026-01-01", "effective": "2026-01-10", "says": "We changed it. Twice."}
	assert badly_published(docs, [change], {"terms": 1}, 30, True, lambda _key: change) == ["terms 2: 30 days' notice", "terms: one sentence"]
	assert badly_published(docs, [], {"terms": 1}, 30, True, lambda _key: None) == ["terms is at revision 2: add it to documents.CHANGES"]
	assert badly_published(docs, [change], {"terms": 1}, 30, False, lambda _key: None)[0].startswith("Before production")
	assert unnamed_models(["m1", "m2"], {"m1": "Anthropic", "m2": "Nobody"}.get, {"Anthropic"}) == {"m2": "Nobody"}
	assert unassembled({"one_hr", "one_new"}, ["one_hr"]) == ["one_new"]
	service = {"hosts": ("api.exa.ai",), "off": "Off.", "sends": "A query."}
	rows = [{"name": "Exa Labs, Inc.", "uses": [{"service": "search"}]}]
	hosts = {"api.exa.ai": "Exa Labs, Inc."}
	assert unserviced({"search": service}, rows, hosts, [("a.py", "services.call('search', 'https://api.exa.ai/')")]) == []
	assert unserviced({"search": service}, rows, hosts, [("a.py", "get('https://api.exa.ai/')")]) == ["a.py calls search's host without services.call"]
	assert unserviced({}, rows, hosts, []) == ["a use names a service nobody declared: ['search']"]
	laws = {"gdpr": {"title": "GDPR", "duties": {"notice": "Say what is kept.", "erase": "Erase on request"}}}
	clauses = {("privacy", "use"): [{"meets": ["notice"]}]}
	assert unmet_duties(clauses, laws, ["notice", "erase"]) == ["no clause meets erase", "gdpr.erase: one sentence"]
	assert legalese({("terms", "use"): [{"module": "one", "key": "use", "body": "Then the Customer shall pay."}]}) == ["one use: shall", "one use: the Customer"]
	assert long_sentences([("one", "use", " ".join(["word"] * 31) + ".")], {"one"}) == ["one use: 31 words: " + ("word " * 12)[:60] + "…"]
	assert long_sentences([("one", "use", " ".join(["word"] * 31) + ".")], set()) == []
	new = [{"name": "New Co", "uses": [{"service": "", "purpose": "Runs it", "starts": ""}]}]
	assert early_core(new, set(), True, {}) == ["New Co is new and One can't work without it, so it waits for its notice: give ['Runs it'] starts= a switchover"]
	assert early_core(new, set(), False, {}) == []
	assert early_core([{"name": "New Co", "uses": [{"service": "", "purpose": "Runs it", "starts": "x"}]}], set(), True, {}) == ["New Co starts with x, which nobody declared"]
	day = datetime.date(2026, 1, 31)
	switch = {"key": "x", "hosts": ("api.new.com",), "clean_by": day, "effective": day}
	started = [{"name": "New Co", "uses": [{"starts": "x"}]}]
	assert switchover_wrong(switch, started, {"api.new.com": "New Co"}, [("a.py", "switchovers.when('x', 'https://api.new.com/')")], day) == []
	assert switchover_wrong(switch, started, {"api.new.com": "New Co"}, [("a.py", "get('https://api.new.com/')")], day + datetime.timedelta(days=1)) == [
		"a.py calls x's host before its day; go through switchovers.when",
		"x took effect on 2026-01-31: remove the old way and the switchover, drop starts= from its companies' uses and add them to documents.IN_EFFECT",
	]
	assert misread_day(lambda _key, on: on >= day, lambda _key: day, "x", day) == []
	assert misread_day(lambda _key, _on: True, lambda _key: day, "x", day) == ["new before its day"]
