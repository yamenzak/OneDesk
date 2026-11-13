"""Taking money once, read back without a site.

Three guards stop one payment becoming two workspaces, and every one of them is
invisible when it works. They are held here off the source, because the way you
find out one has gone is a customer with two invoices.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

STRIPE = tree.APP / "one_admin" / "stripe.py"
SIGNUP = tree.APP / "one_admin" / "signup.py"


def test_the_event_id_is_unique_and_that_is_the_idempotency():
	import json

	spec = json.loads(
		(
			tree.APP / "one_admin" / "doctype" / "stripe_webhook_event" / "stripe_webhook_event.json"
		).read_text()
	)
	field = next(f for f in spec["fields"] if f["fieldname"] == "event_id")
	assert field.get("unique"), "without this index a redelivery provisions a second workspace"
	assert spec["autoname"] == "field:event_id"


def test_accepting_twice_returns_the_first_workspace():
	source = SIGNUP.read_text(encoding="utf-8")
	accept = source[source.index("def accept("):source.index("def _tenant_for(")]
	assert "if asked.tenant:" in accept and "return asked.tenant" in accept


def test_the_webhook_never_rolls_back_the_whole_request():
	"""Measured: a bare rollback undid the delivery that was already working.

	A second delivery arriving before the first had committed rolled the first
	one's insert away, and then looked for the row it had just destroyed.
	"""
	source = STRIPE.read_text(encoding="utf-8")
	assert "savepoint(" in source
	assert "frappe.db.rollback()" not in source


def test_the_clock_is_real_unix_time():
	"""Measured: `now_datetime()` is site-local, and `.timestamp()` on it landed
	four hours out, which refused every delivery."""
	body = ast.parse(STRIPE.read_text(encoding="utf-8"))
	body.body = [n for n in body.body if not _is_docstring(n)]
	code = ast.unparse(body)
	assert "int(time.time())" in code
	assert "now_datetime" not in code, "the docstring may name it; the code may not"


def test_an_unhandled_event_type_still_answers_yes():
	"""A non-2xx makes Stripe redeliver, and redelivering something we ignore on
	purpose is a retry loop with no end."""
	source = STRIPE.read_text(encoding="utf-8")
	webhook = source[source.index("def webhook("):source.index("def _remember(")]
	assert 'return {"ignored"' in webhook


def test_the_request_exists_before_the_customer_is_sent_to_pay():
	"""The other order leaves a paid customer whose request was never written:
	the wizard pays only for a request it opened (wizard._open)."""
	source = (tree.APP / "one_admin" / "wizard.py").read_text(encoding="utf-8")
	pay = source[source.index("def pay("):source.index("def finish(")]
	assert pay.index("_open(") < pay.index("stripe.checkout(asked.name)")
	assert "def start(" not in SIGNUP.read_text(encoding="utf-8")


def test_the_guest_endpoints_are_rate_limited():
	for path in (SIGNUP, tree.APP / "one_admin" / "wizard.py"):
		_limited(ast.parse(path.read_text(encoding="utf-8")))


def _limited(tree_) -> None:
	for node in tree_.body:
		if not isinstance(node, ast.FunctionDef):
			continue
		decorators = [ast.unparse(d) for d in node.decorator_list]
		if any("allow_guest=True" in d for d in decorators):
			assert any("rate_limit" in d for d in decorators), f"{node.name} is open and unlimited"


def test_the_portal_pages_only_exist_on_the_admin_site():
	for page in ("start", "welcome"):
		source = (tree.APP / "www" / f"{page}.py").read_text(encoding="utf-8")
		assert "site.is_admin()" in source and "DoesNotExistError" in source


def _is_docstring(node) -> bool:
	return isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)


def test_a_plan_gives_the_gigabytes_it_advertises():
	"""Decimal, because that is what the plan says and what R2 bills in.

	1024³ gave a 25 GB plan 26.8 GB, which is generous and also a screen saying
	27 GB next to a plan called 25.
	"""
	import ast

	source = (tree.APP / "one_admin" / "signup.py").read_text(encoding="utf-8")
	numbers = {
		node.value
		for node in ast.walk(ast.parse(source))
		if isinstance(node, ast.Constant) and isinstance(node.value, int)
	}
	assert 1024 not in numbers, "storage is sold in decimal gigabytes"
	assert 1000 in numbers


OFFERING = tree.APP / "one_admin" / "doctype" / "offering" / "offering.py"
WELCOME = tree.APP / "www" / "welcome.py"


def test_a_trial_only_ever_goes_on_a_subscription():
	"""Stripe carries a trial on the subscription, so there is nowhere to put
	one on a single payment — and a session that sends the field anyway is
	refused by Stripe in front of a customer holding a card."""
	body = ast.parse(STRIPE.read_text(encoding="utf-8"))
	checkout = next(
		node
		for node in ast.walk(body)
		if isinstance(node, ast.FunctionDef) and node.name == "checkout"
	)
	guards = [
		node
		for node in ast.walk(checkout)
		if isinstance(node, ast.If)
		and "recurring" in ast.unparse(node.test)
		and "trial_days" in ast.unparse(node.test)
	]
	assert guards, "trial_period_days is not behind `recurring and trial_days`"
	assert ast.unparse(checkout).count("trial_period_days") == 1
	assert "trial_period_days" in ast.unparse(guards[0])


def test_the_price_list_refuses_a_trial_it_cannot_honour():
	"""The same rule at the other end, so the operator is told when they set it
	rather than the customer when they try to pay."""
	source = OFFERING.read_text(encoding="utf-8")
	assert "self.trial_days and not self.recurring" in source


def _sentences(source: str, name: str) -> dict[str, str]:
	"""A `{status: lambda: _("...")}` table read back as `{status: text}`."""
	table = next(
		node.value
		for node in ast.parse(source).body
		if isinstance(node, ast.Assign)
		and any(t.id == name for t in node.targets if isinstance(t, ast.Name))
	)
	said = {}
	for key, value in zip(table.keys, table.values, strict=True):
		words = [
			child.value
			for child in ast.walk(value)
			if isinstance(child, ast.Constant) and isinstance(child.value, str)
		]
		said[key.value] = " ".join(words)
	return said


def test_a_trialling_customer_is_never_told_a_payment_landed():
	"""The screen Stripe sends somebody back to. With a trial nothing was
	charged — the card was taken and the first invoice is days away — so every
	status that would otherwise claim a payment has to be answered again."""
	source = WELCOME.read_text(encoding="utf-8")
	plain, on_trial = _sentences(source, "SAYS"), _sentences(source, "ON_TRIAL")

	claims = {status for status, said in plain.items() if "Payment received" in said}
	assert claims, "SAYS no longer says this, so this guard is reading the wrong thing"
	assert claims <= set(on_trial), f"{claims - set(on_trial)} would tell a trial it paid"
	assert not any("Payment received" in said for said in on_trial.values())


def _webhook() -> str:
	source = STRIPE.read_text(encoding="utf-8")
	return source[source.index("def webhook("):source.index("def _book(")]


def test_a_signup_that_could_not_be_built_is_kept_and_answered():
	"""Raising rolled back the Failed status, the notice and the error, and
	Stripe redelivered into the same failure."""
	webhook = _webhook()
	caught = webhook[webhook.index("except signup.NotBuilt"):webhook.index("except Exception as raised:\n\t\tseen.db_set({\"error\"")]
	assert 'return {"failed": request}' in caught and "\traise\n" not in caught
	accept = SIGNUP.read_text(encoding="utf-8")
	assert "raise NotBuilt(str(raised)) from raised" in accept
	assert "class NotBuilt(frappe.ValidationError)" in accept


def test_a_checkout_naming_no_request_we_have_is_ignored():
	webhook = _webhook()
	assert webhook.index('frappe.db.exists("Account Request", request)') < webhook.index("signup.accept(")


def test_a_cancelled_subscription_moves_the_workspace():
	"""Nothing is invoiced after a cancellation, so nothing fails, and the
	workspace stayed Live for ever."""
	source = STRIPE.read_text(encoding="utf-8")
	assert 'ENDED = "customer.subscription.deleted"' in source
	assert "(OWED, SETTLED, ENDED)" in source
	assert "lifecycle.ended(tenant)" in source
	assert '{"stripe_subscription": body.get("id")}' in source


def test_the_portal_cannot_cancel_or_change_the_plan():
	source = STRIPE.read_text(encoding="utf-8")
	assert '"configuration": _portal()' in source
	assert '"features[subscription_cancel][enabled]": "false"' in source
	assert '"features[subscription_update][enabled]": "false"' in source


def test_a_payment_restores_only_once_nothing_is_left_unpaid():
	source = STRIPE.read_text(encoding="utf-8")
	assert "not _settles(tenant, body)" in source and "ladder.settled(" in source


def test_a_second_checkout_never_replaces_the_first_subscription():
	source = STRIPE.read_text(encoding="utf-8")
	remember = source[source.index("def _remember_customer("):source.index("def _ladder(")]
	assert 'held.get("stripe_subscription") or body.get("subscription")' in remember


def test_what_a_post_makes_it_makes_once():
	source = STRIPE.read_text(encoding="utf-8")
	post = source[source.index("def _post("):source.index("def _get(")]
	assert '"Idempotency-Key"' in post and "if path not in MADE_BY_POST" in post
