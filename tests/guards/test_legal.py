"""OneLegal: the documents assemble, every change to them is a decision, and
every company One sends data to is in the Subprocessors list.

Pure: the registry, the documents and every module's `legal.py` import nothing
of frappe, so the documents are assembled here exactly as a site assembles them.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree  # noqa: E402

from onedesk.one import ready  # noqa: E402
from onedesk.one_legal import assemble, documents, registry  # noqa: E402

VERSIONS = {
	"terms": "12.ce9140c8",
	"aup": "1.87e4fdd0",
	"privacy": "27.2db9ccba",
	"cookies": "2.946a434c",
	"dpa": "7.a01dc637",
	"subprocessors": "5.9ff8c642",
	"ai": "25.59452c8c",
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


def test_every_document_is_at_the_version_recorded():
	found = {one["key"]: one["version"] for one in assemble.documents()}
	changed = {key: (VERSIONS.get(key), now) for key, now in found.items() if VERSIONS.get(key) != now}
	assert not changed, (
		"These documents changed: "
		+ ", ".join(f"{key} {was} → {now}" for key, (was, now) in changed.items())
		+ (
			". Material: bump its revision in one_legal/documents.py. A typo: record the new version above."
			if ready.PRODUCTION
			else ". Before production the agreements change freely: record the new version above."
		)
	)


def test_every_clause_is_in_a_section_its_document_has():
	sections = {(key, section) for key, rows in documents.SECTIONS.items() for section, _heading in rows}
	assemble.documents()
	stray = [place for place in registry.CLAUSES if place not in sections]
	assert not stray, f"clauses aimed at sections that do not exist: {stray}"


def test_every_company_one_calls_is_a_declared_subprocessor():
	assemble.documents()
	declared = set(registry.SUBPROCESSORS)
	called = set()
	for path in tree.python():
		if "one_legal" in path.parts or path.name == "legal.py":
			continue
		called |= set(re.findall(r"https://([a-z0-9.-]+\.[a-z]+)/", path.read_text(encoding="utf-8")))
	outside = {host for host in called if not host.endswith(("frappe.io", "github.com", "example.com"))}
	unknown = sorted(host for host in outside if host not in HOSTS)
	assert not unknown, f"One calls {unknown}: map each to its subprocessor in HOSTS, and declare it"
	undeclared = sorted({HOSTS[host] for host in outside if HOSTS[host] and HOSTS[host] not in declared})
	assert not undeclared, f"called but not in the Subprocessors list: {undeclared}"


def test_the_lifecycle_the_terms_describe_is_the_one_the_code_runs():
	from onedesk.one_admin.ladder import DAYS

	text = assemble.text_of("terms")
	for rung in ("Overdue", "Suspended", "Archived"):
		assert f"{DAYS[rung]} days" in text, rung


def test_everybody_agrees_to_something_and_the_notices_to_nothing():
	audiences = {key: one["audience"] for key, one in documents.DOCUMENTS.items()}
	assert audiences["privacy"] == "user" and audiences["terms"] == "customer" and audiences["aup"] == "both"
	assert audiences["licences"] is None
	assert list(documents.DOCUMENTS) == [key for key in documents.SECTIONS]


def test_nobody_is_promised_what_is_not_built():
	"""OneApp's text promised a full backup from the settings and said nothing is
	ever written without somebody asking. Neither is true of OneDesk: OneAI's
	reading acts without being asked each time."""
	everything = " ".join(assemble.text_of(key) for key in documents.DOCUMENTS)
	assert "full backup" not in everything
	assert "without somebody asking for it" not in everything
	assert "turns reading on, OneAI reads the mail and files that arrive and acts on them" in assemble.text_of("ai")


def test_only_a_first_agreement_stops_anybody():
	"""A later revision is notice, not a stop (docs/READY.md, mechanism 13):
	whoever agreed to an earlier one stands agreed, and the gate tells them
	it changed. `agreed` still tells a new revision from a new hash."""
	import ast as _ast

	source = (Path(__file__).resolve().parents[2] / "onedesk" / "one_legal" / "gate.py").read_text(encoding="utf-8")
	space = {}
	for node in _ast.parse(source).body:
		if isinstance(node, _ast.FunctionDef) and node.name in ("revision", "agreed"):
			exec(_ast.unparse(node), space)
	assert space["agreed"]("1.dcae3326", "1.94da7c45")
	assert not space["agreed"]("1.dcae3326", "2.94da7c45")
	assert not space["agreed"](None, "1.94da7c45")
	assert '"accepted": bool(was)' in source and '"changed": bool(was) and not agreed(was, version)' in source


def test_a_change_is_published_ahead_of_the_day_it_takes_effect():
	"""From production on, every revision above the baseline is a published
	change, and one to what the workspace agrees to takes effect NOTICE_DAYS
	after it is published, at least, with what changed said in a sentence.
	Before it, the agreements change freely and nothing is published."""
	import datetime

	if not ready.PRODUCTION:
		assert not documents.CHANGES, "Before production a change takes effect the day it is made: nothing goes in documents.CHANGES"
	for key, one in documents.DOCUMENTS.items():
		if ready.PRODUCTION and one["revision"] > documents.BASELINE[key]:
			change = documents.change_of(key)
			assert change, f"{key} is at revision {one['revision']}: add it to documents.CHANGES"
	for change in documents.CHANGES:
		key = change["document"]
		published, effective = (datetime.date.fromisoformat(change[day]) for day in ("published", "effective"))
		if documents.DOCUMENTS[key]["audience"] in ("customer", "both"):
			assert (effective - published).days >= documents.NOTICE_DAYS, f"{key} {change['revision']}: {documents.NOTICE_DAYS} days' notice"
		assert change["says"].endswith(".") and len(re.findall(r"[.!?](?:\s|$)", change["says"])) == 1, f"{key}: one sentence"


def test_every_company_that_runs_a_model_is_a_declared_subprocessor():
	"""Whoever runs a model OneAI uses receives what it is sent, so each is a
	subprocessor the agreements name (one_ai/models.py RUN_BY)."""
	from onedesk.one_ai import models

	assemble.documents()
	declared = set(registry.SUBPROCESSORS)
	unnamed = {model: models.run_by(model) for model in models.used() if models.run_by(model) not in declared}
	assert not unnamed, f"Models run by a company that is not a subprocessor: {unnamed}"


def test_every_modules_legal_file_is_assembled():
	from onedesk.one_legal.assemble import places

	found = {path.parent.name for path in tree.APP.glob("one*/legal.py") if path.parent.name != "one_legal"}
	assert found <= set(places()), f"not a folder or part in the registry: {sorted(found - set(places()))}"


def test_a_service_is_reached_only_through_services_call():
	"""An optional service's hosts are called only while a workspace has it
	on (docs/READY.md, mechanism 13): a file that names one goes through
	one_legal/services.call, each service sends to at least one declared
	company, and what it says while off is said."""
	assemble.documents()
	for key, one in registry.SERVICES.items():
		assert one["hosts"] and one["off"] and one["sends"], key
		companies = {row["name"] for row in registry.subprocessor_rows() for use in row["uses"] if use["service"] == key}
		assert companies, f"{key} sends to nobody the Subprocessors list names"
		assert all(HOSTS.get(host) in companies for host in one["hosts"]), f"{key}: each host is one of its companies'"
		for path in tree.python():
			text = path.read_text(encoding="utf-8")
			if path.name != "legal.py" and any(host in text for host in one["hosts"]):
				assert "services.call(" in text, f"{path.name} calls {key}'s host without services.call"
	uses = [use["service"] for row in registry.subprocessor_rows() for use in row["uses"] if use["service"]]
	assert set(uses) <= set(registry.SERVICES), f"a use names a service nobody declared: {sorted(set(uses) - set(registry.SERVICES))}"


def test_every_duty_a_law_puts_on_us_is_met_by_a_clause():
	"""laws.py lists the laws One answers and what each asks of us; a clause
	names the duties it meets (`meets=`), and no duty is left without one
	(docs/READY.md, mechanism 13)."""
	from onedesk.one_legal import laws

	assemble.documents()
	met = {duty for rows in registry.CLAUSES.values() for one in rows for duty in one["meets"]}
	unmet = [duty for duty in laws.duties() if duty not in met]
	assert not unmet, f"no clause meets these: {unmet}. Write one, or say which clause does with meets="
	for law, one in laws.LAWS.items():
		assert one["title"] and one["duties"], law
		for duty, said in one["duties"].items():
			assert said.endswith((".", ")")) and len(re.findall(r"[.!?](?:\s|$)", said)) <= 2, f"{law}.{duty}: one sentence"


LEGALESE = (
	"shall", "herein", "hereinafter", "hereby", "thereof", "whereas", "pursuant to", "notwithstanding",
	"aforementioned", "forthwith", "in no event", "the Company", "the Customer", "the Provider",
)  # fmt: skip


def test_the_agreements_are_plain():
	"""docs/WORDING.md, The agreements: no clause in legalese, and a module
	going through docs/READY.md says one point to a sentence of 30 words at
	most, in its clauses, its subprocessors' uses and its services."""
	from onedesk.one import ready

	assemble.documents()
	ours = set(ready.MODULES)
	found = []
	for rows in registry.CLAUSES.values():
		for one in rows:
			found += [
				f"{one['module']} {one['key']}: {word}"
				for word in LEGALESE
				if re.search(rf"\b{word}\b", one["body"], 0 if word != word.lower() else re.I)
			]
	assert not found, f"legalese: {found}"
	texts = [(one["module"], one["key"], one["body"]) for rows in registry.CLAUSES.values() for one in rows]
	texts += [(use["module"], row["name"], use["purpose"] + ". " + use["data"]) for row in registry.subprocessor_rows() for use in row["uses"]]
	texts += [(one["module"], one["key"], " ".join((one["does"], one["sends"], one["off"]))) for one in registry.SERVICES.values()]
	long = [
		f"{module} {key}: {len(sentence.split())} words: {sentence[:60]}…"
		for module, key, text in texts
		if module in ours
		for sentence in re.split(r"(?<=[.!?:])\s+", text)
		if len(sentence.split()) > 30
	]
	assert not long, "one point to a sentence, 30 words at most:\n" + "\n".join(long)


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

	from onedesk.one_legal import switchovers

	assemble.documents()
	for row in registry.subprocessor_rows():
		core = [use for use in row["uses"] if not use["service"]]
		if not ready.PRODUCTION or row["name"] in documents.IN_EFFECT or not core:
			continue
		early = [use["purpose"] for use in core if not use.get("starts")]
		assert not early, f"{row['name']} is new and One can't work without it, so it waits for its notice: give {early} starts= a switchover"
	for row in registry.subprocessor_rows():
		for use in row["uses"]:
			assert not use.get("starts") or use["starts"] in registry.SWITCHOVERS, f"{row['name']} starts with {use['starts']}, which nobody declared"
	today = datetime.date.today()
	for one in switchovers.all_of(today):
		key = one["key"]
		companies = {row["name"] for row in registry.subprocessor_rows() for use in row["uses"] if use.get("starts") == key}
		assert all(HOSTS.get(host) in companies for host in one["hosts"]), f"{key}: each host is one of the companies it starts"
		for path in tree.python():
			text = path.read_text(encoding="utf-8")
			if path.name != "legal.py" and any(host in text for host in one["hosts"]):
				assert "switchovers.when(" in text, f"{path.name} calls {key}'s host before its day; go through switchovers.when"
		assert today <= one["clean_by"], (
			f"{key} took effect on {one['effective']}: remove the old way and the switchover, drop starts= from its "
			f"companies' uses and add them to documents.IN_EFFECT"
		)


def test_a_switchover_runs_the_old_way_until_its_day():
	"""switchovers.when is old before the published change's day and new on
	it, read from documents.CHANGES alone."""
	import datetime

	from onedesk.one_legal import switchovers

	assemble.documents()
	change = {"document": "ai", "revision": 999, "published": "2026-01-01", "effective": "2026-01-31", "says": "A test."}
	documents.CHANGES.append(change)
	registry.SWITCHOVERS["test-switch"] = {"key": "test-switch", "module": "one", "document": change["document"], "revision": change["revision"], "does": "", "hosts": ()}
	try:
		day = datetime.date.fromisoformat(change["effective"])
		assert not switchovers.live("test-switch", day - datetime.timedelta(days=1))
		assert switchovers.live("test-switch", day)
		assert switchovers.effective("test-switch") == day
	finally:
		del registry.SWITCHOVERS["test-switch"]
		documents.CHANGES.remove(change)
