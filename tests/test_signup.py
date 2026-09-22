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
	"""The other order leaves a paid customer whose request was never written."""
	source = SIGNUP.read_text(encoding="utf-8")
	start = source[source.index("def start("):]
	assert start.index(".insert(") < start.index("stripe.checkout")


def test_the_guest_endpoints_are_rate_limited():
	tree_ = ast.parse(SIGNUP.read_text(encoding="utf-8"))
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

	# The AST rather than the text, because the comment above the line explains
	# why it is not 1024 — and a guard that greps would fail on its own reason.
	source = (tree.APP / "one_admin" / "signup.py").read_text(encoding="utf-8")
	numbers = {
		node.value
		for node in ast.walk(ast.parse(source))
		if isinstance(node, ast.Constant) and isinstance(node.value, int)
	}
	assert 1024 not in numbers, "storage is sold in decimal gigabytes"
	assert 1000 in numbers
