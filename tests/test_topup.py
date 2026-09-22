"""Credit arriving, and the two ways it could arrive twice.

Both are invisible when they work. A webhook Stripe redelivers granting a second
pack, and a nightly job granting the same month's allowance every night, are the
same failure wearing different clothes — and the same field stops both.
"""

import ast
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

TOPUP = tree.APP / "one_admin" / "topup.py"
STRIPE = tree.APP / "one_admin" / "stripe.py"
ENTRY = tree.APP / "one_admin" / "doctype" / "credit_ledger_entry" / "credit_ledger_entry.json"
OFFERING = tree.APP / "one_admin" / "doctype" / "offering" / "offering.json"


def _function(path: Path, name: str) -> ast.FunctionDef:
	body = ast.parse(path.read_text(encoding="utf-8"))
	return next(n for n in body.body if isinstance(n, ast.FunctionDef) and n.name == name)


def test_a_redelivered_webhook_grants_once():
	"""Stripe delivers more than once by design. The key is the session's own
	id, so the second delivery finds the first delivery's entry."""
	source = ast.unparse(_function(TOPUP, "bought"))
	assert "key=" in source and "stripe:" in source
	field = next(
		f for f in json.loads(ENTRY.read_text(encoding="utf-8"))["fields"] if f["fieldname"] == "key"
	)
	assert field.get("unique"), "without the index the key is a check somebody remembered"


def test_the_monthly_allowance_is_keyed_by_its_month():
	"""Run nightly rather than on the first, so a workspace built on the twelfth
	does not wait nineteen days. Which only works if running it again is free."""
	source = ast.unparse(_function(TOPUP, "allowance"))
	assert "key=" in source and "plan:" in source
	assert "%Y-%m" in source, "a key without the month would grant once, ever"
	hooks = (tree.APP / "hooks.py").read_text(encoding="utf-8")
	assert "onedesk.one_admin.topup.monthly" in hooks


def test_the_monthly_allowance_expires_at_the_end_of_its_month():
	"""It does not roll over. Which is the case the ledger's draw order exists
	for: the soonest-expiring grant goes first, so nobody loses credit they paid
	for while a free allowance sits unused beside it."""
	source = ast.unparse(_function(TOPUP, "allowance"))
	assert "expires_on=get_last_day" in source


def test_nothing_is_granted_where_the_money_is_not_known_to_have_moved():
	"""The grant is the webhook's, after Stripe says so. A workspace that could
	grant itself credit by opening a page is a workspace that never pays."""
	source = ast.unparse(_function(TOPUP, "buy"))
	assert "ledger" not in source and "grant" not in source
	assert "checkout_for_credits" in source


def test_a_top_up_and_a_signup_are_told_apart_by_the_session():
	"""Both complete a checkout. A signup names the request it came from; a
	top-up names the workspace and the pack."""
	webhook = ast.unparse(_function(STRIPE, "webhook"))
	assert 'metadata' in webhook and 'pack' in webhook
	made = ast.unparse(_function(STRIPE, "checkout_for_credits"))
	assert "metadata[tenant]" in made and "metadata[pack]" in made
	assert "'mode': 'payment'" in made, "a pack is bought once, not subscribed to"


def test_a_pack_and_a_plan_do_not_share_a_field():
	"""A lump granted once and an allowance granted monthly under one name is a
	nightly job granting somebody's one-off purchase every night."""
	spec = json.loads(OFFERING.read_text(encoding="utf-8"))
	names = {f["fieldname"] for f in spec["fields"]}
	assert {"credits", "credits_a_month"} <= names
	controller = (
		tree.APP / "one_admin" / "doctype" / "offering" / "offering.py"
	).read_text(encoding="utf-8")
	assert '"Credit Pack": ("credits",)' in controller


def test_a_pack_with_nothing_in_it_is_refused():
	controller = (
		tree.APP / "one_admin" / "doctype" / "offering" / "offering.py"
	).read_text(encoding="utf-8")
	assert "sells nothing" in controller


def test_an_overdue_workspace_still_gets_its_allowance():
	"""Overdue is defined as nothing happening to the workspace. Cutting off its
	credit would be the grace period not existing — the same reason
	`proxy.SERVING` carries it."""
	source = TOPUP.read_text(encoding="utf-8")
	table = next(
		n.value
		for n in ast.parse(source).body
		if isinstance(n, ast.Assign)
		and any(t.id == "GRANTED_ON" for t in n.targets if isinstance(t, ast.Name))
	)
	assert set(ast.literal_eval(table)) == {"Live", "Overdue"}
