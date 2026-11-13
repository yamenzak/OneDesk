"""The operator console, read back from the files rather than from a site.

Three of these are about a rail going wrong quietly. A sidebar naming a doctype
that does not exist renders an entry that 404s; a doctype nobody put in the rail
is reachable only by typing its name into the awesomebar, which is how the seven
OneAdmin doctypes were reached before this stage existed.

One is about something worse. The console is hidden by one thing and one thing
only — every OneAdmin document grants `One Operator` and `site.apply` strips
that role from every user on a workspace site. A workspace page that forgot its
`roles` would put the whole operator console in every tenant's dock.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ADMIN = tree.APP / "one_admin"
OPERATOR = "One Operator"

NOT_A_FIELD = ("Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Image")

UNRAILED = {
	"Workspace Server",
	"Health Check",
	"Workspace Session",
	"Stripe Webhook Event",
	"Credit Reservation",
	"One Admin Settings",
}

MADE_FOR_YOU = {
	"Workspace Session",
	"Workspace Error",
	"Tenant",
	"Provisioning Job",
	"Tenant Domain",
	"Tenant Event",
	"Account Request",
	"Stripe Webhook Event",
}


def _json(path: Path) -> dict:
	return json.loads(path.read_text(encoding="utf-8"))


def _sidebar() -> dict:
	return _json(ADMIN / "sidebar" / "one_admin" / "one_admin.json")


def _workspace() -> dict:
	return _json(ADMIN / "workspace" / "one_admin" / "one_admin.json")


def _owned() -> set[str]:
	"""Every doctype the OneAdmin module ships that a person can open.

	Child tables are left out throughout this file: they have no list, no rail
	entry and no permission of their own — frappe reaches one through its parent
	and checks the parent's.
	"""
	folder = ADMIN / "doctype"
	specs = [
		_json(one / f"{one.name}.json")
		for one in folder.iterdir()
		if one.is_dir() and (one / f"{one.name}.json").exists()
	]
	return {spec["name"] for spec in specs if not spec.get("istable")}


def test_the_console_is_gated_on_the_operator_role():
	"""The whole of the hiding, and the only thing standing between a tenant and it."""
	roles = [row["role"] for row in _workspace().get("roles") or []]
	assert roles == [OPERATOR], f"the OneAdmin page grants {roles}"
	assert '"onedesk.one_admin.site.offer"' in tree.hooks()
	offer = (ADMIN / "site.py").read_text().split("def offer(", 1)[1]
	assert "is_admin() and OPERATOR in frappe.get_roles()" in offer and "pop(MODULE" in offer


def test_every_rail_entry_points_at_something_real():
	rail = _sidebar()["items"]
	owned = _owned()
	for item in rail:
		if item.get("link_type") != "DocType":
			continue
		assert item["link_to"] in owned, f"the rail names {item['link_to']!r}, which OneAdmin does not own"


def test_the_rail_starts_at_home():
	first = _sidebar()["items"][0]
	assert first["link_type"] == "Page"
	assert first["link_to"] == "oneadmin"


def test_nothing_is_reachable_only_by_typing_its_name():
	rail = {i.get("link_to") for i in _sidebar()["items"] if i.get("link_type") == "DocType"}
	missing = sorted(_owned() - rail - UNRAILED)
	assert not missing, (
		f"{missing} are OneAdmin's and are in no rail entry. Add them, or say in "
		"UNRAILED why an operator should have to type the name."
	)


def test_the_home_page_names_number_cards_that_exist():
	shipped = {
		_json(one / f"{one.name}.json")["name"] for one in (ADMIN / "number_card").iterdir() if one.is_dir()
	}
	named = {row["number_card_name"] for row in _workspace().get("number_cards") or []}
	assert named <= shipped, f"the home page names cards that do not exist: {named - shipped}"
	labels = {row["label"] for row in _workspace()["number_cards"]}
	laid = {
		one["data"]["number_card_name"]
		for one in json.loads(_workspace()["content"])
		if one["type"] == "number_card"
	}
	assert laid == labels, f"the layout names cards the workspace does not carry: {laid ^ labels}"


def test_what_needs_the_operator_is_a_block_of_their_own():
	blocks = {one["name"]: one for one in _json(tree.APP / "fixtures" / "custom_html_block.json")}
	needs = blocks["OneAdmin Needs You"]
	assert [row["role"] for row in needs["roles"]] == [OPERATOR]
	assert "onedesk.one_admin.home.needs" in needs["script"]
	assert "frappe.realtime.doctype_subscribe" in needs["script"]
	assert "operator._may()" in (ADMIN / "home.py").read_text(), "Home is the operator's alone"


def test_a_record_the_machinery_makes_cannot_be_typed_by_hand():
	"""An operator-made Tenant has no site, no token and no job behind it.

	Every one of these is inserted with `ignore_permissions`, so withdrawing
	create costs the machinery nothing and closes the button that makes a record
	the rest of the code then believes.
	"""
	for name in sorted(MADE_FOR_YOU):
		folder = name.lower().replace(" ", "_")
		doc = _json(ADMIN / "doctype" / folder / f"{folder}.json")
		for perm in doc["permissions"]:
			assert not perm.get("create"), f"{name} can be created by hand"


def test_an_offering_cannot_be_typed_by_hand():
	"""The Price List is read-only: its rows come from the prices One sets."""
	doc = _json(ADMIN / "doctype" / "offering" / "offering.json")
	assert not any(perm.get("create") or perm.get("write") for perm in doc["permissions"])


def test_both_gates_are_registered_on_every_owned_doctype():
	"""One hook is not enough, and that was measured rather than assumed.

	`has_permission` is called only when Frappe has a document to judge, so on
	its own it guarded opening a record and left `get_list` wide open — with the
	operator role granted by hand and the flag off, a Tenant list still returned
	rows. `permission_query_conditions` is the seam every list, report and link
	search passes through.
	"""
	import re

	hooks = tree.hooks()
	owned = _owned()
	for hook, fn in (
		("has_permission", "refuse_on_a_tenant"),
		("permission_query_conditions", "nothing_on_a_tenant"),
	):
		block = re.search(rf"^{hook} = \{{(.*?)^\}}", hooks, re.S | re.M)
		assert block, f"{hook} is not declared in hooks.py"
		named = set(re.findall(r'"([^"]+)": "onedesk\.one_admin\.site\.' + fn, block.group(1)))
		assert owned <= named, f"{hook} misses {sorted(owned - named)}"


def test_the_console_wears_its_own_mark():
	"""OneAdmin is its own product with its own mark; `one` is a different one."""
	assert _sidebar()["header_icon"] == "oneadmin"
	assert _workspace()["icon"] == "oneadmin"
	shipped = json.loads((tree.APP / "fixtures" / "custom_icon.json").read_text(encoding="utf-8"))
	assert "oneadmin" in {one["name"] for one in shipped}


def test_the_console_has_its_own_row_in_the_dock():
	"""Reachable by clicking rather than by knowing the URL.

	It is last on purpose: the four above it are opened every day and this one
	is opened by two people.
	"""
	dock = _json(tree.APP / "dock" / "onedesk" / "onedesk.json")
	rows = {row["link_to"]: row for row in dock["items"]}
	assert "One Admin" in rows, "the dock does not offer the console"
	assert rows["One Admin"]["icon"] == "oneadmin"
	assert rows["One Admin"]["link_type"] == "Sidebar"
	assert dock["items"][-1]["link_to"] == "One Admin"


def test_nothing_on_a_workspace_is_typed():
	"""Every field is the record of something that happened, not a setting.

	The one that mattered: Status was a live Select, so an operator could drop a
	workspace from a dropdown — no job, no call to press, no R2 sweep, and a
	record saying the files were gone while the files were still there.
	"""
	doc = _json(ADMIN / "doctype" / "tenant" / "tenant.json")
	typed = [
		one["fieldname"]
		for one in doc["fields"]
		if one["fieldtype"] not in NOT_A_FIELD and not one.get("read_only")
	]
	assert not typed, f"{typed} can be typed on a Tenant"
	for perm in doc["permissions"]:
		assert not perm.get("write"), "a Tenant can be saved, so the form offers Save"
		assert not perm.get("delete"), "a Tenant can be deleted"


def test_an_operator_may_only_send_a_workspace_to_a_real_rung():
	"""Read from the AST: `operator.py` imports frappe and this suite has none.

	`ladder.py` does not, which is the point of it being pure — so the rungs
	come from the module and the buttons come from the file.
	"""
	import ast

	from onedesk.one_admin import ladder

	source = (ADMIN / "operator.py").read_text(encoding="utf-8")
	by_hand = None
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "BY_HAND":
			by_hand = {key.value: value.value for key, value in zip(node.value.keys, node.value.values)}
	assert by_hand, "operator.py declares no BY_HAND"

	assert set(by_hand) <= set(ladder.RUNGS)
	assert "Live" not in by_hand, "climbing back is `restore`, not a fall"
	for rung, warning in by_hand.items():
		if rung in ("Suspended", "Archived", "Dropped"):
			assert warning, f"{rung} costs somebody something and says nothing about it"


def test_every_step_says_what_it_is_doing():
	"""A step with no sentence falls back to its function name, silently.

	`archive_site` in a list column tells a reader nothing. The list and the
	form both read `steps.SAID` — the list through the boot, the form through
	`operator.walk` — so one missing entry is two screens showing an identifier.
	"""
	import ast

	source = (ADMIN / "steps.py").read_text(encoding="utf-8")
	found = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in (
			"ORDER",
			"WALKS",
			"SAID",
		):
			found[node.targets[0].id] = node.value

	def strings(node):
		return {n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)}

	walked = set()
	for key, value in zip(found["WALKS"].keys, found["WALKS"].values):
		walked |= strings(found["ORDER"]) if isinstance(value, ast.Name) else strings(value)

	said = {key.value for key in found["SAID"].keys}
	assert walked <= said, f"no words for {sorted(walked - said)}"
	assert said <= walked, f"words for steps that do not exist: {sorted(said - walked)}"


def test_the_operator_is_told_where_each_thing_happens():
	"""The machinery writes with db_set, which runs no hooks: each notice is
	called at the one place its thing happens."""
	for path, call in (
		("runner.py", "tell.job_failed(job)"),
		("signup.py", "tell.signup_paid(asked)"),
		("signup.py", "tell.signup_not_built(asked, str(raised))"),
		("steps.py", "tell.owing(tenant, rung, why)"),
		("domains.py", "tell.domains_waiting()"),
	):
		assert call in (ADMIN / path).read_text(), f"{path} does not call {call}"
	tell = (ADMIN / "tell.py").read_text()
	assert "frappe.log_error" in tell, "a notice that fails must not stop the job"
	assert any(one.get("roles") == ("One Operator",) for one in tree.notifications().values())


def test_oneai_reads_the_console_for_an_operator_only():
	source = (ADMIN / "ai.py").read_text()
	body = source.split("def console_today(", 1)[1]
	assert "site.is_admin()" in body and "site.OPERATOR not in frappe.get_roles()" in body
	assert "home.needs()" in body, "the panel is told what the page shows"
	assert '"onedesk.one_admin.ai.console_today"' in tree.hooks()


def test_the_owner_is_mailed_as_their_workspace_falls_and_comes_back():
	"""A suspended site cannot tell its owner anything: the admin site mails
	them, from where every rung is reached."""
	steps = (ADMIN / "steps.py").read_text()
	arrive = steps.split("def _arrive(", 1)[1].split("\ndef ", 1)[0]
	assert "was = tenant.status" in arrive and "tell.owner(tenant, rung, was, why)" in arrive
	assert '"status_since": now_datetime()' in arrive and "notify=True" in arrive
	tell = (ADMIN / "tell.py").read_text().split("def owner(", 1)[1].split("\n@", 1)[0]
	for name in ("Payment Failed", "Workspace Suspended", "Workspace Archived", "Workspace Closed", "Workspace Restored"):
		assert f'notify.mail("{name}"' in tell, name
	types = [one for one in tree.notifications().values() if one["module"] == "one_admin"]
	assert sum(bool(one.get("outside")) for one in types) == 16, (
		"Ready, Suspended, Archived, Closed, Restored, Delayed, Finish, Sign-in, Moved to, Moved away, Confirm, "
		"Changed, Payment Failed, Trial Ending, Update Waits For Terms, Auto Top-Up Failed"
	)


def test_a_workspace_is_read_by_operators_only_and_never_shared():
	tenant = json.loads((ADMIN / "doctype" / "tenant" / "tenant.json").read_text())
	assert [p["role"] for p in tenant["permissions"]] == ["One Operator"]
	assert not tenant["permissions"][0]["share"]
	assert "status_since" in (tree.APP / "patches.txt").read_text()


def test_oneai_reads_a_workspace_for_an_operator_only():
	source = (ADMIN / "ai.py").read_text()
	body = source.split("def workspace_facts(", 1)[1]
	assert body.index("if not _operator()") < body.index("frappe.get_doc")
	assert '"expects": "workspace_facts"' in source
	assert '"onedesk.one_admin.ai.workspace_facts"' in tree.hooks()


def test_our_lists_are_called_what_the_rail_calls_them():
	titles = (tree.APP / "one" / "titles.py").read_text()
	assert '"DocType"' in titles and "_ours(" in titles and "len(labels) == 1" in titles
	reports = (tree.APP / "public" / "js" / "reports.js").read_text()
	assert "onedesk.reports.lists_too();" in reports


def test_a_new_workspace_invites_its_owner_and_says_it_is_ready():
	"""The admin site cannot sign in to a site it built: the site invites
	whoever paid, once, when nobody administers it yet."""
	steps = (ADMIN / "steps.py").read_text()
	order = steps.split("ORDER = (", 1)[1].split(")", 1)[0]
	assert order.index('"push_config"') < order.index('"invite_owner"') < order.index('"live"')
	assert "onedesk.one.account.wake" in steps and "tell.ready(tenant)" in steps
	assert '"owner": known.owner_email' in (ADMIN / "proxy.py").read_text()
	owner = (tree.APP / "one_account" / "owner.py").read_text()
	assert 'if roles.administrators() or frappe.db.exists("User", email)' in owner
	assert "roles.ADMINISTRATOR" in owner and 'invite.send(user.name, inviter="One")' in owner
	account = (tree.APP / "one" / "account.py").read_text()
	assert "owner.arrive(said)" in account and "@rate_limit(" in account.split("def wake(", 1)[0][-200:]
	assert 'notify.mail(\n\t\t"Workspace Ready"' in (ADMIN / "tell.py").read_text()


def test_a_job_that_has_not_moved_is_on_home_with_run_now():
	home = (ADMIN / "home.py").read_text()
	assert "*_stalled_jobs()" in home and "operator.run_now" in home
	body = (ADMIN / "operator.py").read_text().split("def run_now(", 1)[1].split("\ndef ", 1)[0]
	assert body.index("_may()") < body.index("runner.advance(job)")


def test_jobs_are_published_and_never_shared():
	runner = (ADMIN / "runner.py").read_text()
	assert runner.count("job.db_set(") == runner.count("notify=True") - runner.count("tenant.db_set(")
	job = json.loads((ADMIN / "doctype" / "provisioning_job" / "provisioning_job.json").read_text())
	assert not job["permissions"][0]["share"] and job["title_field"] == "tenant"


def test_oneai_asks_about_a_job_only_in_the_state_it_is_in():
	source = (ADMIN / "ai.py").read_text()
	assert (
		'"when": {"status": ["Failed"]}' in source and '"when": {"status": ["Pending", "Waiting"]}' in source
	)
	body = source.split("def job_facts(", 1)[1]
	assert body.index("if not _operator()") < body.index("frappe.get_doc")
	assert '"onedesk.one_admin.ai.job_facts"' in tree.hooks()
	assert "def _holds(" in (tree.APP / "one_ai" / "suggest.py").read_text()


def test_every_log_row_goes_through_log_write():
	"""Who did it, which job, and words the list can translate: so nothing
	writes a Tenant Event but `log.py`."""
	import re

	for path in ADMIN.rglob("*.py"):
		if path.name == "log.py" or "patches" in path.parts or "doctype" in path.parts:
			continue
		text = path.read_text()
		assert not re.search(r'"doctype":\s*"Tenant Event"', text), f"{path.name} writes the log itself"
	log = (ADMIN / "log.py").read_text()
	assert "_lt(" in log and 'by or ("Operator" if operator else "One")' in log
	assert 'log.write(slug, kind, detail, by="Customer")' in (ADMIN / "billing.py").read_text()
	assert 'lifecycle.fall(held, rung, log.said("by_hand"))' in (ADMIN / "operator.py").read_text()
	assert '"Tenant": ["onedesk.one_admin.log.timeline"]' in tree.hooks()


def test_the_log_keeps_one_row_per_stretch_over_storage_and_no_dead_kinds():
	log = (ADMIN / "log.py").read_text()
	assert "AGAIN_BYTES" in log and "AGAIN_DAYS" in log
	event = json.loads((ADMIN / "doctype" / "tenant_event" / "tenant_event.json").read_text())
	kinds = [f for f in event["fields"] if f["fieldname"] == "kind"][0]["options"].split("\n")
	assert "Drifted" not in kinds and "Over Database" not in kinds
	assert not event["permissions"][0]["share"] and event["title_field"] == "tenant"
	assert "*_over_storage()" in (ADMIN / "home.py").read_text()


def test_a_domain_is_said_in_the_customers_words_and_says_what_it_needs():
	"""Domains moved to Cloudflare: no screen may still say Frappe Cloud does
	them, and the console says a state as the customer's own screen does."""
	heads = (ADMIN / "heads.py").read_text()
	said = heads.split("def domain_said(", 1)[1].split("\ndef ", 1)[0]
	assert "Frappe Cloud" not in said and "It needs a CNAME record from {0} to {1}." in said
	pills = heads.split("DOMAIN = {", 1)[1].split("}", 1)[0]
	assert (
		'"Working"' in pills
		and '"Waiting"' in pills
		and '"Not working"' in pills
		and "In Progress" not in pills
	)
	listing = (ADMIN / "doctype" / "tenant_domain" / "tenant_domain_list.js").read_text()
	assert "Frappe Cloud" not in listing and "In Progress" not in listing
	assert '_("Check Again")' in heads.split('"domain.refresh"', 1)[1][:300]
	domains = (ADMIN / "domains.py").read_text()
	assert "_mark_main(" in domains and ".notify_update()" in domains
	source = (ADMIN / "ai.py").read_text()
	domain = source.split('"Tenant Domain": [', 1)[1].split("],", 1)[0]
	assert '"expects": "workspace_facts"' in domain and "def domain_facts(" not in source
	facts = source.split("def workspace_facts(", 1)[1].split("\ndef ", 1)[0]
	assert facts.index("if not _operator()") < facts.index('"Tenant Domain"') < facts.index("frappe.get_doc")
	assert '"main_address": bool(one.is_main)' in facts and '"cname_to": held.domain' in facts and '"asked_on"' in facts


def test_the_price_list_says_who_has_an_offering_and_shows_only_what_its_kind_carries():
	operator = (ADMIN / "operator.py").read_text().split("def sold(", 1)[1].split("\ndef ", 1)[0]
	assert '"Tenant Add-on"' in operator, "an add-on's workspaces are counted"
	heads = (ADMIN / "heads.py").read_text().split("def offering_sold(", 1)[1].split("\ndef ", 1)[0]
	assert "does not change theirs" not in heads and "next time they change their plan or add-ons" in heads
	offering = json.loads((ADMIN / "doctype" / "offering" / "offering.json").read_text())
	fields = {f["fieldname"]: f for f in offering["fields"]}
	assert fields["trial_days"]["depends_on"].startswith("eval:doc.kind=='Plan'")
	assert fields["storage_gb"]["depends_on"] == "eval:doc.kind!='Credit Pack'"
	assert offering["sort_field"] == "sort_key" and not offering["permissions"][0]["share"]
	assert '"onedesk.one_admin.ai.price_list"' in tree.hooks()


def test_price_check_says_its_findings_in_words_and_warns_on_save():
	"""plans.check stays frappe-free; each finding names its rule, and the
	screens say it through offerings.RULES."""
	import re

	plans_py = (ADMIN / "plans.py").read_text()
	assert "import frappe" not in plans_py
	rules = set(re.findall(r'"(margin|fewer|no_upgrade|thin_upgrade|addon_dear|per_unit)",\n\t*\{', plans_py))
	offerings = (ADMIN / "offerings.py").read_text()
	for rule in ("margin", "fewer", "no_upgrade", "thin_upgrade", "addon_dear", "per_unit"):
		assert f'"{rule}": _lt(' in offerings, rule
	assert rules, "each finding carries its rule"
	hooks = tree.hooks()
	assert '"onedesk.one_admin.offerings.warn"' in hooks
	assert "*_mispriced()" in (ADMIN / "home.py").read_text()
	report = (ADMIN / "report" / "price_check" / "price_check.py").read_text()
	assert "_holds" not in report and '"gives"' in report and "include_disabled" in report
	ai = (ADMIN / "ai.py").read_text()
	assert '"report:Price Check"' in ai and '"expects": "run_report"' in ai.split('"report:Price Check"', 1)[1][:600]


def test_plan_calculator_quotes_as_the_customer_is_quoted():
	"""The calculator counts add-ons as billing.quote does, never credit
	packs; says the needs back in its summary; and a workspace fills them."""
	report = (ADMIN / "report" / "plan_calculator" / "plan_calculator.py").read_text()
	assert 'one.kind == "Add-on"' in report
	assert "def needs_of(" in report and "frappe.only_for(site.OPERATOR)" in report
	assert "_summary(needs" in report and '"gives"' in report and '"dearer_by"' in report
	script = (ADMIN / "report" / "plan_calculator" / "plan_calculator.js").read_text()
	assert 'fieldname: "workspace"' in script and "needs_of" in script
	ai = (ADMIN / "ai.py").read_text()
	assert '"report:Plan Calculator"' in ai and '"expects": "plan_quote"' in ai
	assert "def plan_quote(" in ai and "if not _operator():" in ai.split("def plan_quote(")[1]
	assert '"onedesk.one_admin.ai.plan_quote"' in tree.hooks()
	assert "## Plan Calculator" in (ADMIN / "AGENTS.md").read_text()


def test_a_signup_moves_on_its_own_and_lets_an_unpaid_name_go():
	"""Paid on payment, Done when its workspace goes live, Abandoned nightly;
	the list and the head say its state in the same words; the customer is
	told once when it cannot be built."""
	import re

	signup = (ADMIN / "signup.py").read_text()
	assert '"Abandoned"' not in signup.split("HOLDING =")[1].split("\n")[0]
	assert 'db_set("status", "Paid"' in signup and "def built(" in signup and "def abandon(" in signup
	assert "signup.built(tenant)" in (ADMIN / "steps.py").read_text()
	assert '"onedesk.one_admin.signup.abandon"' in tree.hooks()
	heads = (ADMIN / "heads.py").read_text().split("REQUEST = {")[1].split("}")[0]
	listed = (ADMIN / "doctype" / "account_request" / "account_request_list.js").read_text()
	head_words = dict(re.findall(r'"(\w+)": \("\w+", _lt\("([^"]+)"\)\)', heads))
	list_words = dict(re.findall(r'(\w+): \["\w+", __\("([^"]+)"\)\]', listed))
	assert head_words == list_words and "Abandoned" in head_words
	assert "hide_name_column: true" in listed
	assert '"Workspace Delayed"' in (ADMIN / "tell.py").read_text()
	request = json.loads((ADMIN / "doctype" / "account_request" / "account_request.json").read_text())
	assert not request["permissions"][0]["share"]
	ai = (ADMIN / "ai.py").read_text()
	assert '"expects": "signup_facts"' in ai and "if not _operator():" in ai.split("def signup_facts(")[1]
	assert '"onedesk.one_admin.ai.signup_facts"' in tree.hooks()
	assert "## Signups" in (ADMIN / "AGENTS.md").read_text()


def test_credits_say_what_is_left_and_an_operator_can_take_back_a_gift():
	"""A grant says what is left of it; an operator's grant can be taken back
	as a spend of the rest; the customer hears the operator's note; the list
	opens on what people did rather than on calls."""
	ledger = (ADMIN / "ledger.py").read_text()
	assert "def left_of(" in ledger and "def take_back(" in ledger and "def last_gift(" in ledger
	take = ledger.split("def take_back(")[1].split("\ndef ")[0]
	assert '"kind": "Spend"' in take and 'held.source != "Operator"' in take
	assert '"gift": ledger.last_gift(' in (ADMIN / "proxy.py").read_text()
	assert '_once("gift"' in (tree.APP / "one" / "account.py").read_text()
	assert any("{note}" in one.get("message", "") for one in tree.notifications().values())
	heads = (ADMIN / "heads.py").read_text()
	assert '"credit.said": credit_said' in heads and '"credit.take_back": {' in heads
	listed = (tree.APP / "public" / "js" / "one_admin" / "credit_ledger_entry_list.js").read_text()
	assert 'filters: [["source", "!=", "Run"]]' in listed and "hide_name_filter: true" in listed
	entry = json.loads((ADMIN / "doctype" / "credit_ledger_entry" / "credit_ledger_entry.json").read_text())
	assert not entry["permissions"][0]["share"] and entry["title_field"] == "tenant"
	assert {f["fieldname"]: f for f in entry["fields"]}["model"]["fieldtype"] == "Data"
	ai = (ADMIN / "ai.py").read_text()
	assert '"expects": "credit_facts"' in ai and "if not _operator():" in ai.split("def credit_facts(")[1]
	assert "## Credits" in (ADMIN / "AGENTS.md").read_text()


def test_the_operator_has_no_models_to_manage():
	"""Models are code (one_ai/models.py, docs/AICENTER.md): an action runs on
	its kind of work at the workspace's tier, and the console has no catalogue,
	no preferred provider, no withdrawn-model notice and no model to fix."""
	actions = (ADMIN / "actions.py").read_text()
	assert "gateway.call(\n\t\tjob.kind," in actions and "default_model" not in actions
	assert not (ADMIN / "catalogue.py").exists() and not (ADMIN / "doctype" / "ai_model").exists()
	settings = json.loads((ADMIN / "doctype" / "one_admin_settings" / "one_admin_settings.json").read_text())
	assert not {"prefer_models_from", "persona"} & {f["fieldname"] for f in settings["fields"]}
	assert "models_gone" not in (ADMIN / "tell.py").read_text()
	assert "_unmodelled" not in (ADMIN / "home.py").read_text()
	assert "model_facts" not in (ADMIN / "ai.py").read_text()


def test_ai_usage_says_what_a_call_cost_us_and_counts_it_once():
	"""A call keeps what the provider charged; the report sets it against what
	was charged, cuts by action too, and has one total, its own."""
	ledger = (ADMIN / "ledger.py").read_text()
	assert "SUM(usd) AS usd" in ledger and '"usd": usd or 0' in ledger
	gateway = (ADMIN / "gateway.py").read_text()
	assert "ledger.commit(holding, spent.credits, spent.usd, model=model)" in gateway
	report = json.loads((ADMIN / "report" / "ai_usage" / "ai_usage.json").read_text())
	assert not report["add_total_row"]
	usage = (ADMIN / "report" / "ai_usage" / "ai_usage.py").read_text()
	assert '"Action": ["action"]' in usage and '"cost_us"' in usage and "_summary(whole)" in usage
	ai = (ADMIN / "ai.py").read_text()
	assert '"expects": "run_report"' in ai.split('"report:AI Usage"', 1)[1][:600] and "def ai_usage(" not in ai
	assert report["roles"] == [{"role": "One Operator"}], "run_report reads it for an operator only"
	assert "## AI Usage" in (ADMIN / "AGENTS.md").read_text()


def test_settings_say_what_is_missing_and_tell_the_other_operators():
	"""Tabs, a head naming what is not set and what it stops, a notice on
	save that never carries a key, and AI Usage pricing a credit at a pack's
	price rather than at the provider-cost rate."""
	spec = json.loads((ADMIN / "doctype" / "one_admin_settings" / "one_admin_settings.json").read_text())
	tabs = [f["label"] for f in spec["fields"] if f["fieldtype"] == "Tab Break"]
	assert tabs == ["Connections", "Grace Periods"] and not spec["permissions"][0]["share"]
	settings = (ADMIN / "doctype" / "one_admin_settings" / "one_admin_settings.py").read_text()
	assert "tell.settings_changed(" in settings and 'df.fieldtype == "Password"' in settings
	assert '"settings.said": settings_said' in (ADMIN / "heads.py").read_text()
	usage = (ADMIN / "report" / "ai_usage" / "ai_usage.py").read_text()
	assert "offerings.credit_price()" in usage and "credits_per_dollar" not in usage
	ai = (ADMIN / "ai.py").read_text()
	assert '"expects": "settings_check"' in ai and "if not _operator():" in ai.split("def settings_check(")[1]
	assert "## Settings" in (ADMIN / "AGENTS.md").read_text()


def test_our_own_workspace_is_never_billed_or_refused_or_sold():
	"""Four Degree Labs' own workspace: marked ours, never refused for
	credits, not a live customer on Home, and not charged in AI Usage."""
	house = (ADMIN / "house.py").read_text()
	assert 'NAME = "Four Degree Labs"' in house and 'update_site_config("one_tenant", held)' in house
	tenant = json.loads((ADMIN / "doctype" / "tenant" / "tenant.json").read_text())
	assert {f["fieldname"]: f for f in tenant["fields"]}["is_house"]["read_only"]
	reserve = (ADMIN / "ledger.py").read_text().split("def reserve(")[1].split("\ndef ")[0]
	assert "if not ours and not credits.enough(" in reserve
	assert '"live": ("Tenant", {"status": "Live", "is_house": 0, "is_test": 0})' in (ADMIN / "home.py").read_text()
	assert "_ours(start, end, by, filters)" in (ADMIN / "report" / "ai_usage" / "ai_usage.py").read_text()
	assert "## Our own workspace" in (ADMIN / "AGENTS.md").read_text()


def test_the_admin_site_links_itself_after_every_migrate():
	"""The house patch runs once, at install, before the site is flagged as
	the admin site; site.apply runs after every migrate and links it then,
	once, and on https so the call to itself is not redirected."""
	apply = (ADMIN / "site.py").read_text().split("def apply(")[1].split("\ndef ")[0]
	assert "house.link()" in apply
	house = (ADMIN / "house.py").read_text()
	link = house.split("def link(")[1].split("\ndef ")[0]
	assert 'frappe.conf.get("one_tenant") == held' in link and "ensure()" in link
	assert 'update_site_config("one_admin_url", own_url())' in house and '"https://"' in house
