"""The agents' foundation (docs/ARC-AI.md, P8.1): an agent user per app with
its manifest's User roles alone, the token the Worker and a workspace sign
their calls with, the Worker Set Up Cloudflare deploys, the receptionist's
look at a mail and the 50-invoice gate's scoring. No site needed."""

import ast
import json
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

from onedesk.one import registry  # noqa: E402
from onedesk.one.registry import agents, hooks  # noqa: E402
from onedesk.one_ai.agents import evaluate, token  # noqa: E402

WORKER = ROOT / "deploy" / "agents"
SETUP = (tree.APP / "one_admin" / "setup.py").read_text()
NOW = 1_800_000_000
SOURCE_RUN = SETUP.split("def run(self)", 1)[1].split("return self.said", 1)[0]


def test_every_app_with_user_roles_has_an_agent_with_those_alone():
	listed = {one.app: one for one in agents.listed()}
	assert {"one_mail", "one_book"} <= set(listed)
	for app in registry.apps():
		if app.roles.user:
			assert listed[app.id].roles == app.roles.user + app.agent_roles, app.id
			assert listed[app.id].only == app.agent_roles, app.id
			assert not set(listed[app.id].roles) & (set(app.roles.manager) | set(agents.NEVER)), app.id
	assert len({one.email for one in listed.values()}) == len(listed)
	assert all(one.email.endswith("@" + agents.DOMAIN) for one in listed.values())


def test_an_agent_never_holds_a_manager_s_role():
	book = registry.get("one_book")
	with pytest.raises(agents.Invalid):
		agents.of(replace(book, roles=replace(book.roles, user=("Accounts User", "System Manager"))))
	assert agents.of(replace(book, agent="")) is None
	for role in ("Accounts Manager", "System Manager"):
		with pytest.raises(agents.Invalid):
			agents.of(replace(book, agent_roles=(role,)))


def test_an_agent_s_own_role_is_never_a_person_s():
	book = registry.get("one_book")
	for role in ("Accounts User", "OneMail User", "Mail Manager"):
		with pytest.raises(agents.Invalid):
			agents.of(replace(book, agent_roles=(role,)))
	assert agents.of(replace(book, agent_roles=("OneBook Clerk",))).roles == (*book.roles.user, "OneBook Clerk")
	assert agents.only()["OneMail Receptionist"] == agents.email("one_mail")
	users = (tree.APP / "one_ai" / "agents" / "users.py").read_text()
	assert "_only(agent)" in users and '"!=", agent.email' in users
	assert "agents.only()" in (tree.APP / "one_ai" / "checks.py").read_text()


def test_the_receptionist_s_role_reads_mail_and_is_made_by_migrate():
	from onedesk.one_mail import access

	from onedesk.one_mail import linking

	assert set(access.GIVEN) == {"Communication", *linking.LINKED}
	assert all(by_role == {"OneMail Receptionist": ("read",)} for by_role in access.GIVEN.values())
	settles = hooks.settles(install=False)
	assert settles.index("onedesk.one_mail.access.settle") < settles.index("onedesk.one_ai.agents.users.ensure")
	assert "rights.made(RECEPTIONIST, desk=False)" in (tree.APP / "one_mail" / "access.py").read_text()


def test_the_receptionist_opens_only_the_mail_of_a_mailbox_oneai_reads(monkeypatch):
	from frappe import _dict

	from onedesk.one_mail import access, gate

	monkeypatch.setattr(gate, "reads", lambda account: account == "Sales")
	receptionist = agents.email("one_mail")

	def opens(**values) -> bool:
		return access.allowed(_dict({"communication_medium": "Email", "email_account": "Sales", **values}), "read", receptionist)

	assert opens()
	assert not opens(email_account="Accounts")
	assert not opens(email_account=None)
	assert not opens(communication_medium="Phone")
	assert not opens(communication_medium="Other", email_account=None)


def test_agent_users_are_made_on_every_migrate_and_are_nobody_s_seat():
	assert "onedesk.one_ai.agents.users.ensure" in hooks.settles(install=False)
	users = (tree.APP / "one_ai" / "agents" / "users.py").read_text()
	assert '"enabled": 0' in users and "set(agent.roles)" in users
	assert "agents.listed()" in (tree.APP / "one" / "people.py").read_text().split("NOT_PEOPLE =", 1)[1].split("\n", 1)[0]


def test_a_token_opens_one_way_one_body_one_workspace_once():
	secret = token.secret_for("master", "acme")
	signed = token.mint(secret, {"aud": "workspace", "ws": "acme", "agent": "one_book", "tool": "draft_purchase_invoice"}, "{}", NOW)
	used = set()

	def seen(jti, until):
		was = jti in used
		used.add(jti)
		return was

	assert token.verify(secret, signed, "workspace", "{}", NOW + 30, seen)["agent"] == "one_book"
	for args in (
		(secret, signed, "workspace", "{}", NOW + 30, seen),
		(secret, signed, "agents", "{}", NOW),
		(secret, signed, "workspace", '{"x":1}', NOW),
		(secret, signed, "workspace", "{}", NOW + 61),
		(token.secret_for("master", "other"), signed, "workspace", "{}", NOW),
		(secret, signed.split(".")[0] + ".00", "workspace", "{}", NOW),
		("", signed, "workspace", "{}", NOW),
	):
		with pytest.raises(token.Refused):
			token.verify(*args)
	long = token.mint(secret, {"aud": "agents", "ws": "acme", "agent": "one_mail"}, "", NOW, lasts=3600)
	with pytest.raises(token.Refused):
		token.verify(secret, long, "agents", "", NOW + token.LONGEST + 1)


@pytest.mark.skipif(not shutil.which("node"), reason="no node here")
def test_the_worker_s_token_is_one_this_workspace_reads():
	script = 'import {mint, secretFor} from "./token.ts"; console.log(await mint(await secretFor("master", "acme"), {aud: "workspace", ws: "acme", agent: "one_book", tool: "draft_purchase_invoice"}, "{}", Math.floor(Date.now() / 1000)));'
	said = subprocess.run(["node", "--input-type=module", "-e", script], cwd=WORKER, capture_output=True, text=True, timeout=60)
	assert said.returncode == 0, said.stderr
	import time

	claims = token.verify(token.secret_for("master", "acme"), said.stdout.strip(), "workspace", "{}", int(time.time()))
	assert claims["tool"] == "draft_purchase_invoice"


@pytest.mark.skipif(not shutil.which("node"), reason="no node here")
def test_the_worker_s_own_tests_pass():
	said = subprocess.run(["node", "--test", "token.test.ts"], cwd=WORKER, capture_output=True, text=True, timeout=60)
	assert said.returncode == 0, said.stdout + said.stderr


def _tools(folder: str) -> tuple:
	for node in ast.parse((tree.APP / folder / "agent.py").read_text()).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "TOOLS":
			return ast.literal_eval(node.value)
	return ()


def test_the_worker_runs_any_agent_as_the_workspace_says():
	import re

	from onedesk.one_ai.agents import levels, work

	worker = (WORKER / "worker.ts").read_text()
	assert "JOBS" not in worker and set(re.findall(r"\bone_[a-z]+", worker)) == {"one_ai"}, "the Worker names no agent and no job"
	assert 'const TOOL = "/api/method/onedesk.one_ai.agents.api.tool";' in worker
	assert "answer?.next" in worker and f"export const MOST_STEPS = {work.MOST_STEPS};" in worker
	assert "this.fresh(claims, now)" in worker, "a wake is used once"
	assert work.job("one_mail", "mail") == "incoming" and "incoming" in _tools("one_mail")
	assert work.job("one_book", "handed") == "draft_purchase_invoice" in _tools("one_book")
	assert work.job("one_quality", "record") == "watched" and work.job("one_crm", "handed") == "plan"
	assert set(levels.EVERY_AGENT) == set(work.HANDED.values())
	assert work.handing("one_book", {"reading": "R"}) == {"to": "one_book", "tool": "draft_purchase_invoice", "args": {"reading": "R"}}


def test_here_runs_each_step_an_answer_names_as_its_agent(monkeypatch):
	import frappe

	from onedesk.one_ai.agents import api, work

	ran = []
	answers = {
		("one_mail", "incoming"): {"next": [{"tool": "hand_on", "args": {"reading": "R"}}]},
		("one_mail", "hand_on"): {"next": [work.handing("one_book", {"reading": "R"})]},
		("one_book", "draft_purchase_invoice"): {"drafts": []},
	}
	users = []
	monkeypatch.setattr(frappe, "session", frappe._dict(user="Administrator"), raising=False)
	monkeypatch.setattr(frappe, "set_user", lambda user: users.append(user))

	def tool_of(app, name):
		return lambda asked_by=None, **args: ran.append((app, name, args, asked_by)) or answers[(app, name)]

	monkeypatch.setattr(api, "tool_of", tool_of)
	assert work.here("one_mail", "mail", {"message": "M"}, "huda@one.test") is True
	assert [(app, name) for app, name, _args, _by in ran] == list(answers)
	assert ran[-1][2:] == ({"reading": "R"}, "huda@one.test")
	assert users == [agents.email("one_mail"), agents.email("one_mail"), agents.email("one_book"), "Administrator"]


def test_a_job_and_a_wait_are_declared_with_a_level_and_a_label():
	from onedesk.one_ai.agents import levels

	good = """from frappe import _lt
WATCH = {"raise_it": ("Quality Inspection", "on_submit", "onedesk.one_quality.watch.rejected")}
LEVELS = {"raise_it": "Draft"}
LABELS = {"raise_it": _lt("Raise It")}
"""
	assert levels.unlevelled(good) == []
	assert levels.unlevelled(good.replace("on_submit", "on_a_whim")) == ["raise_it runs 'on_a_whim', which is not one of " + str(levels.WHEN)]
	assert levels.unlevelled(good + 'WAITS = {"raise_it": "Supplier"}\n') == ["raise_it waits but is no planner in PLANS"]
	assert levels.unlevelled(good + 'WAKES = {"handed": "nothing"}\n') == ["a handed wakes 'nothing', which is no tool it has"]
	assert levels.unlevelled(good + 'WAKES = {"record": "watched"}\n') == []
	assert "raise_non_conformance" in levels.actions("one_quality") and "draft_work_orders" in levels.actions("one_factory")
	assert "report_screen_at_risk" in levels.actions("one_display")
	assert levels.declared("one_display")["report_screen_at_risk"] == "Draft"


def test_a_watched_record_wakes_its_agents_beside_what_hooks_there():
	said = hooks.watched({"Sales Order": {"on_submit": ["a.b"]}, "Quality Inspection": {"on_submit": "c.d"}})
	assert said["Sales Order"]["on_submit"] == ["a.b", hooks.HEARD]
	assert said["Quality Inspection"]["on_submit"] == ["c.d", hooks.HEARD]
	assert "Display Screen" not in said, "a job on the round is the scheduler's"
	assert hooks.watched(said) == said
	listed = (tree.APP / "hooks.py").read_text()
	assert "onedesk.one_ai.agents.work.rounds" in listed and "doc_events = watched({" in listed
	assert '"on_change": "onedesk.one_ai.agents.work.approved"' in listed


def test_only_an_approved_card_that_makes_a_record_wakes_what_waited(monkeypatch):
	import frappe

	from onedesk.one_ai.agents import work

	queued = []
	monkeypatch.setattr(frappe, "enqueue", lambda method, **kwargs: queued.append(kwargs["action"]))
	monkeypatch.setattr(work, "working", lambda: [agents.get("one_book")])

	def row(level="Done", was="Proposed", **values):
		before = frappe._dict(level=was) if was else None
		said = frappe._dict(name="RA-1", kind="Create", level=level, reading="R", target_doctype="Supplier")
		said.update(values)
		said.get_doc_before_save = lambda: before
		return said

	for left in (row(level="Dismissed"), row(was="Done"), row(was=None), row(kind="Update"), row(target_doctype="Customer"), row(reading=None)):
		work.approved(left)
	assert queued == []
	work.approved(row())
	assert queued == ["RA-1"]
	assert work.waits("one_book") == {"draft_purchase_invoice": "Supplier"}


def test_set_up_cloudflare_deploys_the_agents_with_their_own_secret():
	assert "self.agents," in SOURCE_RUN
	space = {}
	for node in ast.parse(SETUP).body:
		named = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else getattr(node, "name", "")
		if named in ("COMPATIBILITY_AGENTS", "AGENTS_FILES", "agents_config"):
			exec(ast.unparse(node), space)
	config = space["agents_config"]("one-agents-dev")
	assert config["main"] == "worker.ts" and "nodejs_compat" in config["compatibility_flags"]
	assert config["durable_objects"] == {"bindings": [{"name": "AGENT", "class_name": "ModuleAgent"}]}
	assert config["migrations"] == [{"tag": "v1", "new_sqlite_classes": ["ModuleAgent"]}]
	assert all((WORKER / one).exists() for one in space["AGENTS_FILES"])
	assert '"agents_secret"' in (tree.APP / "one_admin" / "vault.py").read_text()
	assert "token.secret_for(master, tenant.name)" in (tree.APP / "one_admin" / "proxy.py").read_text()



def test_the_way_back_in_checks_the_token_before_it_acts():
	source = (tree.APP / "one_ai" / "agents" / "api.py").read_text()
	body = source.split("def tool(", 1)[1]
	assert "allow_guest=True" in source and "@rate_limit(" in source
	assert body.index("token.verify(") < body.index("frappe.set_user(agent.email)") < body.index("run(**")
	assert 'claims.get("tool") != tool' in body and 'claims.get("ws") != said.get("workspace")' in body
	assert "nx=True" in source, "a token is used once"


def test_the_receptionist_hands_on_only_invoices_worth_acting_on():
	from onedesk.one_mail.agent import is_invoice

	bill = {"kind": "Invoice", "verdict": "Action", "history": 0, "state": "Understood"}
	assert is_invoice(bill) and is_invoice({**bill, "kind": "Credit Note"})
	assert not is_invoice({**bill, "kind": "Contract"})
	assert not is_invoice({**bill, "verdict": "Phishing"})
	assert not is_invoice({**bill, "history": 1})
	assert not is_invoice({**bill, "state": "Read"})


def test_the_gate_scores_each_draft_against_the_invoice():
	spec = json.loads((ROOT / "tests" / "samples" / "intake" / "one_book" / "new-supplier-invoice.json").read_text())
	want = evaluate.expected(spec)
	assert want == {"supplier_name": "Gulf Sealants Trading LLC", "bill_no": "GS-11873", "bill_date": "2026-10-04", "grand_total": 4032.0, "currency": "AED", "due_date": "2026-11-03"}
	right = {**want, "supplier_name": "gulf sealants trading llc ", "grand_total": 4032.004, "bill_date": "2026-10-04"}
	assert evaluate.corrections(want, right) == []
	assert evaluate.corrections(want, {**right, "grand_total": 3840.0, "due_date": None}) == ["grand_total", "due_date"]
	assert evaluate.corrections(want, None) == ["no draft"]
	assert evaluate.expected({"expect": {"bill_no": "A1"}}) == {"bill_no": "A1"}
	fine = [{"sample": str(n), "corrections": []} for n in range(48)]
	two = [{"sample": "a", "corrections": ["no draft"]}, {"sample": "b", "corrections": ["bill_no"]}]
	assert evaluate.scored(fine + two) == {"samples": 50, "drafted": 49, "corrected": 2, "passed": True, "wrong": {"a": ["no draft"], "b": ["bill_no"]}}
	assert not evaluate.scored(fine + two + [{"sample": "c", "corrections": ["currency"]}])["passed"]
	assert not evaluate.scored(fine)["passed"], "fewer than 50 is no gate"
	assert len(evaluate.invoice_samples()) >= 5


def test_a_draft_never_carries_a_submit():
	from onedesk.one_ai.agents import door
	from onedesk.one_ai.reading.act import Action

	made = door.drafted(Action("Create", "Purchase Invoice", values={"supplier": "S", "docstatus": 1}, key="k"))
	assert made.values == {"supplier": "S"} and made.key == "k" and made.kind == "Create"
