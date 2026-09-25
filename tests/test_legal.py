"""OneLegal: the documents assemble, every change to them is a decision, and
every company One sends data to is in the Subprocessors list.

Pure: the registry, the documents and every module's `legal.py` import nothing
of frappe, so the documents are assembled here exactly as a site assembles them.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree  # noqa: E402

from onedesk.one_legal import assemble, documents, registry  # noqa: E402

#: The version of every document. When a clause changes, this fails, and there
#: are two ways out and no third: if the change is material, bump the
#: document's `revision` in one_legal/documents.py, so everybody agrees again;
#: if it is a typo, write the new hash here.
VERSIONS = {
	"terms": "1.4ca1a130",
	"aup": "1.94da7c45",
	"privacy": "1.47d1f4e9",
	"cookies": "1.32b1addc",
	"dpa": "1.75b9b74d",
	"subprocessors": "1.7d7069d8",
	"ai": "1.327d5f92",
	"licences": "1.c71daf62",
}

#: Every outside host One's Python calls, and whose it is: a declared
#: subprocessor's name, or None for a host that receives no customer data.
HOSTS = {
	"api.cloudflare.com": "Cloudflare, Inc.",
	"gateway.ai.cloudflare.com": "Cloudflare, Inc.",
	"api.stripe.com": "Stripe, Inc.",
	"www.gravatar.com": "Automattic Inc.",
	"t1.gstatic.com": "Google LLC",
	# Pricing pages, read by the operator's price check; nothing is sent.
	"developers.cloudflare.com": None,
	"ai.google.dev": None,
}


def test_every_document_is_at_the_version_recorded():
	found = {one["key"]: one["version"] for one in assemble.documents()}
	changed = {key: (VERSIONS.get(key), now) for key, now in found.items() if VERSIONS.get(key) != now}
	assert not changed, (
		"These documents changed: "
		+ ", ".join(f"{key} {was} → {now}" for key, (was, now) in changed.items())
		+ ". Material: bump its revision in one_legal/documents.py. A typo: record the new version above."
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
	ever written without somebody asking. Neither is true of OneDesk: Intake
	acts without being asked each time."""
	everything = " ".join(assemble.text_of(key) for key in documents.DOCUMENTS)
	assert "full backup" not in everything
	assert "without somebody asking for it" not in everything
	assert "Intake" in assemble.text_of("ai")


def test_only_a_new_revision_asks_again():
	"""The README's rule, held: a new hash is a clarification and asks nobody
	again; a new revision asks everybody."""
	import ast as _ast

	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_legal" / "gate.py").read_text(encoding="utf-8")
	space = {}
	for node in _ast.parse(source).body:
		if isinstance(node, _ast.FunctionDef) and node.name in ("revision", "agreed"):
			exec(_ast.unparse(node), space)
	assert space["agreed"]("1.dcae3326", "1.94da7c45")
	assert not space["agreed"]("1.dcae3326", "2.94da7c45")
	assert not space["agreed"](None, "1.94da7c45")
	assert '"accepted": agreed(was, version)' in source
