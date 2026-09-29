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

#: Fieldtypes nobody can type into: the ones that arrange a form and the ones
#: that only draw. `read_only` on them means nothing, so a guard that demands it
#: fails on a layout choice rather than on a mistake.
NOT_A_FIELD = ("Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Image")

#: OneAdmin's own doctypes that are deliberately not in the rail, and why.
#: Anything else missing from it is an oversight rather than a decision.
UNRAILED = {
	# Stripe's deliveries and the unique index that makes a redelivery harmless.
	# There is nothing to do on this screen; it is read when a payment is being
	# chased, by somebody who will type its name.
	"Stripe Webhook Event",
	# A hold lives for the length of one model call. The only question anybody
	# asks about one — how much of a balance is promised — is answered on the
	# balance itself, and a stale one is let go nightly rather than by hand.
	"Credit Reservation",
}

#: Records made by the machinery that also fills them in. An operator typing one
#: gets a half-record every screen then reads as though it were real.
MADE_FOR_YOU = {
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
	# frappe offers every workspace to Workspace Manager whatever its roles say,
	# so the boot is told of OneAdmin only for an operator on the admin site.
	assert '"onedesk.one_admin.site.offer"' in (tree.APP / "hooks.py").read_text()
	offer = (ADMIN / "site.py").read_text().split("def offer(", 1)[1]
	assert "is_admin() and OPERATOR in frappe.get_roles()" in offer and 'pop(MODULE' in offer


def test_every_rail_entry_points_at_something_real():
	rail = _sidebar()["items"]
	owned = _owned()
	for item in rail:
		if item.get("link_type") != "DocType":
			continue
		assert item["link_to"] in owned, (
			f"the rail names {item['link_to']!r}, which OneAdmin does not own"
		)


def test_the_rail_starts_at_home():
	first = _sidebar()["items"][0]
	assert first["link_type"] == "Workspace"
	assert first["link_to"] == "One Admin"


def test_nothing_is_reachable_only_by_typing_its_name():
	rail = {i.get("link_to") for i in _sidebar()["items"] if i.get("link_type") == "DocType"}
	missing = sorted(_owned() - rail - UNRAILED)
	assert not missing, (
		f"{missing} are OneAdmin's and are in no rail entry. Add them, or say in "
		"UNRAILED why an operator should have to type the name."
	)


def test_the_home_page_names_number_cards_that_exist():
	shipped = {
		_json(one / f"{one.name}.json")["name"]
		for one in (ADMIN / "number_card").iterdir()
		if one.is_dir()
	}
	named = {row["number_card_name"] for row in _workspace().get("number_cards") or []}
	assert named <= shipped, f"the home page names cards that do not exist: {named - shipped}"
	# The layout names a card by the workspace's own row label, not the card.
	labels = {row["label"] for row in _workspace()["number_cards"]}
	laid = {one["data"]["number_card_name"] for one in json.loads(_workspace()["content"]) if one["type"] == "number_card"}
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


def test_an_offering_can_be_typed_by_hand():
	"""The exception, and the reason the rule above is a list rather than a sweep.

	A price list is exactly the thing an operator writes.
	"""
	doc = _json(ADMIN / "doctype" / "offering" / "offering.json")
	assert any(perm.get("create") for perm in doc["permissions"])


def test_both_gates_are_registered_on_every_owned_doctype():
	"""One hook is not enough, and that was measured rather than assumed.

	`has_permission` is called only when Frappe has a document to judge, so on
	its own it guarded opening a record and left `get_list` wide open — with the
	operator role granted by hand and the flag off, a Tenant list still returned
	rows. `permission_query_conditions` is the seam every list, report and link
	search passes through.
	"""
	import re

	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
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
	shipped = json.loads(
		(tree.APP / "fixtures" / "custom_icon.json").read_text(encoding="utf-8")
	)
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


def test_no_screen_text_reads_like_a_commit_message():
	"""Field help is written the way frappe and erpnext write it.

	Theirs runs to a median of 68 characters, plain and instructional — "Zero
	means unlimited", "If enabled, changes to the document are tracked". Mine
	started as paragraphs lifted from the reasoning: four lines about ladder.py
	under a Select, on a screen somebody opens to find out whether a customer is
	paying. The reasoning belongs in docs/ and in the docstrings, which is what
	CLAUDE.md already says.

	Three things are checked, all of them proxies for the same thing. Length,
	because a paragraph is the usual symptom. First person, because "we" and
	"our" are the voice of an argument rather than of a field label. And the
	word `press`, because that is the name of Frappe Cloud's own app: correct
	in code, meaningless to the person reading the form.
	"""
	import re

	LONGEST = 130
	VOICE = re.compile(r"\b(we|our|us|ours)\b", re.I)
	THEIR_APP = re.compile(r"\bpress\b", re.I)

	wrong = []
	for folder in sorted(one.name for one in (ADMIN / "doctype").iterdir() if one.is_dir()):
		path = ADMIN / "doctype" / folder / f"{folder}.json"
		if not path.exists():
			continue
		doc = _json(path)
		said = [("[doctype]", doc.get("description") or "")]
		said += [(one["fieldname"], one.get("description") or "") for one in doc["fields"]]
		for where, text in said:
			if not text:
				continue
			if len(text) > LONGEST:
				wrong.append(f"{folder}.{where}: {len(text)} characters")
			if VOICE.search(text):
				wrong.append(f"{folder}.{where}: first person")
			if THEIR_APP.search(text):
				wrong.append(f"{folder}.{where}: says press rather than Frappe Cloud")
	assert not wrong, "screen text out of register:\n  " + "\n  ".join(wrong)


def test_every_operator_verb_is_gated():
	"""Both gates, on every whitelisted method, without exception.

	`_may` is `require_admin` plus `only_for`. A verb that forgot it would be a
	workspace anybody with a desk login could archive.
	"""
	import ast

	source = (ADMIN / "operator.py").read_text(encoding="utf-8")
	for node in ast.parse(source).body:
		if not isinstance(node, ast.FunctionDef):
			continue
		whitelisted = any(
			isinstance(one, ast.Attribute) and one.attr == "whitelist"
			for one in node.decorator_list
		)
		if not whitelisted:
			continue
		calls = {
			one.func.id
			for one in ast.walk(node)
			if isinstance(one, ast.Call) and isinstance(one.func, ast.Name)
		}
		assert "_may" in calls, f"{node.name} is whitelisted and does not call _may()"


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
	assert '"roles": ("One Operator",)' in (ADMIN / "notifications.py").read_text()
	assert '"onedesk.one_admin.notifications.TYPES"' in (tree.APP / "hooks.py").read_text()


def test_oneai_reads_the_console_for_an_operator_only():
	source = (ADMIN / "ai.py").read_text()
	body = source.split("def console_today(", 1)[1]
	assert "site.is_admin()" in body and "site.OPERATOR not in frappe.get_roles()" in body
	assert "home.needs()" in body, "the panel is told what the page shows"
	assert '"onedesk.one_admin.ai.console_today"' in (tree.APP / "hooks.py").read_text()


def test_the_owner_is_mailed_as_their_workspace_falls_and_comes_back():
	"""A suspended site cannot tell its owner anything: the admin site mails
	them, from where every rung is reached."""
	steps = (ADMIN / "steps.py").read_text()
	arrive = steps.split("def _arrive(", 1)[1].split("\ndef ", 1)[0]
	assert "was = tenant.status" in arrive and "tell.owner(tenant, rung, was)" in arrive
	assert '"status_since": now_datetime()' in arrive and "notify=True" in arrive
	tell = (ADMIN / "tell.py").read_text().split("def owner(", 1)[1].split("\n@", 1)[0]
	for name in ("Workspace Suspended", "Workspace Archived", "Workspace Restored"):
		assert f'notify.mail("{name}"' in tell, name
	types = (ADMIN / "notifications.py").read_text()
	assert types.count('"outside": True') == 5, "Ready, Suspended, Archived, Restored, Delayed"


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
	assert '"onedesk.one_admin.ai.workspace_facts"' in (tree.APP / "hooks.py").read_text()


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
	owner = (tree.APP / "one" / "owner.py").read_text()
	assert "if roles.administrators() or frappe.db.exists(\"User\", email)" in owner
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
	assert '"when": {"status": ["Failed"]}' in source and '"when": {"status": ["Pending", "Waiting"]}' in source
	body = source.split("def job_facts(", 1)[1]
	assert body.index("if not _operator()") < body.index("frappe.get_doc")
	assert '"onedesk.one_admin.ai.job_facts"' in (tree.APP / "hooks.py").read_text()
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
	assert '"Tenant": ["onedesk.one_admin.log.timeline"]' in (tree.APP / "hooks.py").read_text()


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
	assert '"Working"' in pills and '"Waiting"' in pills and '"Not working"' in pills and "In Progress" not in pills
	listing = (ADMIN / "doctype" / "tenant_domain" / "tenant_domain_list.js").read_text()
	assert "Frappe Cloud" not in listing and "In Progress" not in listing
	assert '_("Check Again")' in heads.split('"domain.refresh"', 1)[1][:300]
	domains = (ADMIN / "domains.py").read_text()
	assert "_mark_main(" in domains and ".notify_update()" in domains
	source = (ADMIN / "ai.py").read_text()
	assert '"expects": "domain_facts"' in source
	assert source.split("def domain_facts(", 1)[1].index("if not _operator()") < source.split("def domain_facts(", 1)[1].index("frappe.get_doc")


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
	assert '"onedesk.one_admin.ai.price_list"' in (tree.APP / "hooks.py").read_text()


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
	hooks = (tree.APP / "hooks.py").read_text()
	assert '"onedesk.one_admin.offerings.warn"' in hooks
	assert "*_mispriced()" in (ADMIN / "home.py").read_text()
	report = (ADMIN / "report" / "price_check" / "price_check.py").read_text()
	assert "_holds" not in report and '"gives"' in report and "include_disabled" in report
	assert '"report:Price Check"' in (ADMIN / "ai.py").read_text()


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
	assert '"onedesk.one_admin.ai.plan_quote"' in (tree.APP / "hooks.py").read_text()
	assert "## Plan Calculator" in (ADMIN / "README.md").read_text()


def test_a_signup_moves_on_its_own_and_lets_an_unpaid_name_go():
	"""Paid on payment, Done when its workspace goes live, Abandoned nightly;
	the list and the head say its state in the same words; the customer is
	told once when it cannot be built."""
	import re

	signup = (ADMIN / "signup.py").read_text()
	assert '"Abandoned"' not in signup.split("HOLDING =")[1].split("\n")[0]
	assert 'db_set("status", "Paid"' in signup and "def built(" in signup and "def abandon(" in signup
	assert "signup.built(tenant)" in (ADMIN / "steps.py").read_text()
	assert '"onedesk.one_admin.signup.abandon"' in (tree.APP / "hooks.py").read_text()
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
	assert '"onedesk.one_admin.ai.signup_facts"' in (tree.APP / "hooks.py").read_text()
	assert "## Signups" in (ADMIN / "README.md").read_text()
