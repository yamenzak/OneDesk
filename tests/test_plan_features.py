"""Plan features (onedesk/one/registry/features.py): declared once, named by
the price list's plans and by manifests, carried from the plan to its
Offering, the Tenant, `proxy.hello` and the workspace's boot, and a plan
without Training Copies can't start one."""

import ast
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.account_center import plan  # noqa: E402
from onedesk.one import apps  # noqa: E402
from onedesk.one.registry import Invalid, features  # noqa: E402
from onedesk.one.registry import private as manifest  # noqa: E402
from onedesk.one.registry.model import App  # noqa: E402
from onedesk.one_admin import features as carried  # noqa: E402
from onedesk.one_admin import offerings, price_list, sessions  # noqa: E402

NOW = datetime(2026, 11, 13, 12)


def test_every_plan_names_only_declared_features_and_keeps_what_it_had():
	for one in price_list.PLANS:
		assert not features.unknown(one.features), one.key
		assert {"training_copies", "demo"} <= set(one.features), one.key
	assert [one.label for one in price_list.PLANS if one.own_server] == ["Business", "Scale"]
	assert price_list.features_of("gone@2020-01") == price_list.EVERY_PLAN


def test_a_feature_is_declared_once_and_opens_its_service():
	assert len(features.IDS) == len(set(features.IDS))
	assert features.of_service("training_copies") == "training_copies"
	assert features.of_service("gravatar") is None
	assert all(one.label and one.allows for one in features.FEATURES)


def test_the_plan_carries_its_features_to_its_offering():
	business = next(one for one in price_list.PLANS if one.label == "Business")
	row = offerings._row(business)
	assert [one["feature"] for one in row["features"]] == list(business.features)
	assert carried.rows(("demo",)) == [{"feature": "demo"}]


def test_hello_says_the_tenants_features_and_the_workspace_keeps_them():
	tree = ast.parse((ROOT / "onedesk/one_admin/proxy.py").read_text())
	hello = next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == "hello")
	assert "features.of_tenant" in ast.unparse(hello)
	assert "plan_features" in (ROOT / "onedesk/one/account.py").read_text()
	assert plan.said('["demo", "own_server"]') == ("demo", "own_server")
	assert plan.said("[]") == ()
	assert plan.said(None) is None and plan.said("nonsense") is None


def test_a_workspace_nobody_holds_to_a_plan_lacks_nothing():
	assert features.missing(("own_server",), None) == ()
	assert features.missing(("own_server",), ("demo",)) == ("own_server",)
	assert features.missing(("demo",), ("demo",)) == ()


def test_a_plan_without_copies_cant_start_one():
	lately = NOW - timedelta(hours=1)
	assert sessions.why_not_copied((), lately, NOW) == "plan"
	assert sessions.why_not_copied(("demo",), lately, NOW) == "plan"
	assert sessions.why_not_copied(("training_copies",), None, NOW) == "agreed"
	assert sessions.why_not_copied(("training_copies",), NOW - timedelta(hours=5), NOW) == "agreed"
	assert sessions.why_not_copied(("training_copies",), lately, NOW) is None


def test_an_app_that_needs_a_feature_leaves_the_rail_without_it():
	needs = App(id="one_x", name="OneX", kind="app", module="One X", ui="bespoke", sidebar="OneX", plan=("own_server",))
	free = App(id="one_y", name="OneY", kind="app", module="One Y", ui="bespoke", sidebar="OneY")
	assert apps.short((needs, free), ("demo",)) == ["OneX"]
	assert apps.short((needs, free), ("own_server",)) == []


def test_a_private_manifest_names_only_declared_features():
	said = 'APP = App(id="rua_x", name="Rua X", module="Rua X", plan=("{}",))'
	assert manifest.parsed(said.format("own_server")).plan == ("own_server",)
	with pytest.raises(Invalid, match="plan"):
		manifest.parsed(said.format("nowhere"))
