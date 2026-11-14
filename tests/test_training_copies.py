"""Training copies a workspace's administrator starts (one/copies.py, through
one_admin/proxy.py copies_* to one_admin/sessions.py): the three kinds as
asked of OneAdmin, what each copy is made from, and every refusal, with
OneAdmin and the workspace's services faked."""

import ast
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import frappe
import pytest

from onedesk.one import copies
from onedesk.one.registry import fields
from onedesk.one_admin import faults, sessions

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 11, 14, 12)
LATELY = NOW - timedelta(hours=1)
HELD = ("training_copies", "demo")
ANSWERS = {
	"owner": {"email": "layla@acme.test", "first_name": "Layla", "password": "secret"},
	"language": "en",
	"time_zone": "Asia/Dubai",
	"field": "clinic",
	"companies": [{"name": "Acme Clinic", "country": "United Arab Emirates"}],
	"apps": {"one_book": True},
	"steps": {"one_mail": {"domains": {"domain": "acme.test"}}},
	"people": [{"email": "nadia@acme.test", "first_name": "Nadia"}],
}


@pytest.fixture(autouse=True)
def english():
	"""The words as written: no site to translate them in."""
	with mock.patch("onedesk.one.copies._", side_effect=lambda text: text):
		yield


def test_a_copy_is_refused_for_each_reason_and_started_otherwise():
	assert sessions.why_not_started("fresh", "7 Days", None, HELD, LATELY, NOW, 0) is None
	assert sessions.why_not_started("demo", "1 Day", "clinic", HELD, LATELY, NOW, 2) is None
	assert sessions.why_not_started("everything", "7 Days", None, HELD, LATELY, NOW, 0) == "asked"
	assert sessions.why_not_started("fresh", "a year", None, HELD, LATELY, NOW, 0) == "asked"
	assert sessions.why_not_started("demo", "7 Days", "piracy", HELD, LATELY, NOW, 0) == "field"
	assert sessions.why_not_started("data", "7 Days", None, ("demo",), LATELY, NOW, 0) == "plan"
	assert sessions.why_not_started("data", "7 Days", None, HELD, None, NOW, 0) == "agreed"
	assert sessions.why_not_started("data", "7 Days", None, HELD, NOW - timedelta(hours=5), NOW, 0) == "agreed"
	assert sessions.why_not_started("data", "7 Days", None, HELD, LATELY, NOW, sessions.MOST_AT_ONCE) == "many"


def test_every_refusal_is_said_in_a_sentence():
	for why in ("asked", "field", "plan", "agreed", "many", "data", "answers", "room"):
		said = copies.refused(why, 3)
		assert said and said.endswith(".") and "{" not in said, why
	assert "3" in copies.refused("many", 3)


def test_a_fresh_copy_is_set_up_like_the_workspace_without_its_people():
	said = sessions.fresh_answers(ANSWERS, "Omar@Acme.test")
	assert said["owner"] == {"email": "omar@acme.test", "first_name": "Omar", "invite": False}, "the administrator who asked, invited by nobody, with no password"
	assert "people" not in said and "steps" not in said
	assert said["companies"] == ANSWERS["companies"] and said["field"] == "clinic" and said["apps"] == {"one_book": True}
	assert sessions.fresh_answers(None, "omar@acme.test") is None
	assert sessions.fresh_answers(ANSWERS, None) is None
	assert sessions.fresh_answers({"language": "en"}, "omar@acme.test") is None, "answers that would not set a site up"


def test_a_fresh_copy_a_workspace_asked_for_is_set_up_from_its_answers():
	walk = sessions.walk_of(sessions.FRESH, own=True)
	assert walk == sessions.OWN_WALK and set(walk) <= set(sessions.STEPS)
	assert walk[walk.index("configure") + 1] == "set_up" and walk[-1] == sessions.LAST_STEP
	assert sessions.after(sessions.FRESH, "agent_done", own=True) == sessions.LAST_STEP
	assert sessions.walk_of(sessions.FRESH) == sessions.WALKS[sessions.FRESH], "an operator's fresh session is empty"
	assert sessions.walk_of(sessions.DEMO, True, own=True) == sessions.READY_WALK


def test_a_copy_from_the_demo_opens_on_its_fields_company():
	for one in fields.FIELDS:
		company = sessions.opens_on(sessions.DEMO, one.id)
		assert company == fields.demo(one.id)
		assert sessions.config_for(sessions.DEMO, "https://s-1.d.x", NOW, company)["one_copy_company"] == company
	assert sessions.opens_on(sessions.DEMO, None) is None
	assert sessions.opens_on(sessions.FRESH, "clinic") is None
	assert "one_copy_company" not in sessions.config_for(sessions.COPY, "https://s-1.d.x", NOW, "Sahara Glass")


def test_the_workspace_sees_its_copies_kind_never_the_server():
	row = {"name": "WS-1", "source": sessions.COPY, "status": "Running", "link": "https://s-1.d.x", "expires_on": NOW, "server": "oracle-1", "step": None, "error": "boom", "started_by": "omar@acme.test", "creation": NOW}
	said = sessions._row_of(row)
	assert said["kind"] == "data" and said["expires_on"] == str(NOW)
	assert not {"server", "step", "error", "source", "site"} & set(said)
	assert {sessions._row_of({"source": source})["kind"] for source in sessions.KINDS.values()} == set(sessions.KINDS)


def test_the_workspace_and_oneadmin_offer_the_same_kinds_and_lengths():
	assert copies.KINDS == tuple(sessions.KINDS)
	assert copies.LASTS == tuple(sessions.LASTS)


def test_a_box_sets_a_fresh_copy_up_through_the_setup_job():
	agent = (ROOT / "deploy/server/agent.py").read_text()
	kinds = agent.split("KINDS = {", 1)[1].split("}", 1)[0]
	assert f'"{sessions.SET_UP}": session_setup' in kinds
	assert "onedesk.one.setup_job.run" in agent.split("def session_setup", 1)[1].split("def ", 1)[0]


ENDPOINTS = {"copies_start": "COPIES_AN_HOUR", "copies_listed": "CALLS_A_MINUTE", "copies_end": "CALLS_A_MINUTE", "copies_sign_in": "COPIES_AN_HOUR"}


def test_each_copies_endpoint_takes_a_tenants_token_by_post_and_is_rate_limited():
	tree = ast.parse((ROOT / "onedesk/one_admin/proxy.py").read_text())
	found = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in ENDPOINTS}
	assert set(found) == set(ENDPOINTS)
	for name, limit in ENDPOINTS.items():
		said = [ast.unparse(one) for one in found[name].decorator_list]
		assert any("whitelist" in one and "methods=['POST']" in one for one in said), name
		assert any("rate_limit" in one and "key='tenant'" in one and limit in one for one in said), name
		assert "caller()" in ast.unparse(found[name]), name


@pytest.fixture
def workspace():
	"""An administrator of a workspace whose plan has Training Copies and
	has them on, with OneAdmin faked."""
	with (
		mock.patch("onedesk.one.roles.require"),
		mock.patch("onedesk.one.account.configured", return_value=True),
		mock.patch("onedesk.trust_center.services.offered", return_value=True),
		mock.patch("onedesk.trust_center.services.on", return_value=True),
		mock.patch.object(frappe, "session", SimpleNamespace(user="omar@acme.test"), create=True),
		mock.patch("onedesk.one.account.ask", return_value={"name": "WS-1", "kind": "demo", "status": "Starting"}) as asked,
	):
		yield asked


def _thrown(fn, *args, **kwargs) -> str:
	with mock.patch.object(frappe, "throw", side_effect=lambda message, *a, **k: (_ for _ in ()).throw(frappe.ValidationError(message))):
		with pytest.raises(frappe.ValidationError) as raised:
			fn(*args, **kwargs)
	return str(raised.value)


@pytest.mark.parametrize(("kind", "field", "sent"), [("fresh", "clinic", None), ("demo", "clinic", "clinic"), ("data", None, None)])
def test_each_kind_is_asked_of_oneadmin_by_the_administrator(workspace, kind, field, sent):
	copies.start(kind, "7 Days", field)
	assert [one.args[0] for one in workspace.call_args_list] == ["onedesk.one_admin.proxy.copies_agreed", "onedesk.one_admin.proxy.copies_start"], "said on first, then asked"
	assert workspace.call_args.kwargs == {"kind": kind, "lasts": "7 Days", "field": sent, "by": "omar@acme.test"}


def test_a_copy_is_refused_before_oneadmin_is_asked(workspace):
	with mock.patch("onedesk.trust_center.services.offered", return_value=False):
		assert _thrown(copies.start, "fresh", "7 Days") == copies.refused("plan")
	with mock.patch("onedesk.trust_center.services.on", return_value=False):
		assert _thrown(copies.start, "fresh", "7 Days") == copies.refused("agreed")
	with mock.patch("onedesk.one.account.configured", return_value=False):
		assert "isn't connected" in _thrown(copies.start, "fresh", "7 Days")
	assert _thrown(copies.start, "everything", "7 Days") == copies.refused("asked")
	assert not workspace.called


def test_oneadmins_refusal_is_said_in_the_readers_words(workspace):
	workspace.return_value = {"refused": "many", "most": 3}
	assert _thrown(copies.start, "data", "1 Day") == copies.refused("many", 3)
	workspace.side_effect = faults.Refused("onedesk.one_admin.proxy.copies_start: This workspace has no such training copy.", 417, "This workspace has no such training copy.")
	assert _thrown(copies.end, "WS-9") == "This workspace has no such training copy."


def test_only_an_administrator_starts_opens_or_ends_a_copy(workspace):
	with mock.patch("onedesk.one.roles.require", side_effect=frappe.PermissionError):
		for fn, args in ((copies.start, ("fresh", "7 Days")), (copies.end, ("WS-1",)), (copies.open_copy, ("WS-1",)), (copies.section, ())):
			with pytest.raises(frappe.PermissionError):
				fn(*args)
	assert not workspace.called


def test_why_no_copy_can_be_made_from_here():
	assert copies.why_not(True, True, True) is None
	assert copies.why_not(True, True, False) == "linked"
	assert copies.why_not(False, True, True) == "plan"
	assert copies.why_not(True, False, True) == "agreed"


def _tenant(features_held=HELD, agreed_on=LATELY, live=0, answers=ANSWERS, backup=True):
	held = SimpleNamespace(name="acme", slug="acme", workspace_name="Acme", copies_agreed_on=agreed_on)
	return (
		mock.patch.object(frappe, "get_doc", return_value=held),
		mock.patch("onedesk.one_admin.features.of_tenant", return_value=features_held),
		mock.patch("onedesk.one_admin.sessions.now_datetime", return_value=NOW),
		mock.patch("onedesk.one_admin.sessions._live_of", return_value=live),
		mock.patch("onedesk.one_admin.answers.of", return_value=answers),
		mock.patch("onedesk.one_admin.sessions._kept_backup", return_value={"parts": {}} if backup else None),
		mock.patch("onedesk.one_admin.sessions._roomy", return_value=(SimpleNamespace(server="oracle-1"), None)),
		mock.patch("onedesk.one_admin.sessions._begin", return_value=SimpleNamespace(name="WS-1")),
		mock.patch("onedesk.one_admin.sessions._said_of", side_effect=lambda name: {"name": name, "kind": "demo", "status": "Starting"}),
	)


def _start(kind, field=None, **given):
	patches = _tenant(**given)
	with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7] as begun, patches[8]:
		said = sessions.start_for(SimpleNamespace(name="acme"), kind, "7 Days", field, "omar@acme.test")
	return said, begun


def test_oneadmin_starts_each_kind_for_the_workspace_that_asked():
	for kind, field in (("fresh", None), ("demo", "real_estate"), ("data", None)):
		said, begun = _start(kind, field)
		assert said["name"] == "WS-1" and "refused" not in said, kind
		assert begun.call_args.args[2:] == (sessions.KINDS[kind], "7 Days", "acme", field, "omar@acme.test"), kind


def test_oneadmin_refuses_with_a_key_the_workspace_says():
	assert _start("data", features_held=("demo",))[0] == {"refused": "plan", "most": sessions.MOST_AT_ONCE}
	assert _start("data", agreed_on=None)[0]["refused"] == "agreed"
	assert _start("data", live=sessions.MOST_AT_ONCE)[0]["refused"] == "many"
	assert _start("fresh", answers=None)[0]["refused"] == "answers"
	assert _start("data", backup=False)[0]["refused"] == "data"
	said, begun = _start("demo", "piracy")
	assert said["refused"] == "field" and not begun.called
