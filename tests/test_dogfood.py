"""Our own sales and books, kept from signups and Stripe (one_admin/sales.py,
one_admin/books.py), read back without a site.

What would go wrong here goes wrong quietly: an invoice booked twice because
Stripe redelivered, a workspace not made because our own CRM refused a lead,
a webhook answering an error so Stripe retries a ladder move forever.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ADMIN = tree.APP / "one_admin"


def _read(name: str) -> str:
	return (ADMIN / name).read_text(encoding="utf-8")


def test_every_paid_thing_stripe_tells_us_of_is_booked_without_getting_in_the_way():
	stripe = _read("stripe.py")
	for what in ('_book("invoiced"', '_book("pack_bought"', '_book("refunded"'):
		assert what in stripe, what
	body = stripe.split("def _book", 1)[1].split("\ndef ", 1)[0]
	assert "rollback(save_point=" in body and "log_error" in body, (
		"a failed booking must not fail the webhook"
	)


def test_a_stripe_object_is_booked_once():
	books = _read("books.py")
	for name in ("def invoiced", "def pack_bought"):
		body = books.split(name, 1)[1].split("\ndef ", 1)[0]
		assert "_booked(" in body, name
	assert '"one_stripe_invoice"' in books
	custom = (tree.APP / "one_book" / "custom" / "sales_invoice.json").read_text(encoding="utf-8")
	assert '"one_stripe_invoice"' in custom


def test_our_crm_never_stops_a_signup():
	sales = _read("sales.py")
	for name in ("def signed_up", "def paid"):
		body = sales.split(name, 1)[1].split("\ndef ", 1)[0]
		assert "except Exception" in body and "log_error" in body, name
	assert "sales.signed_up(" in _read("signup.py")
	assert "sales.paid(" in _read("stripe.py")


def test_the_books_run_on_the_admin_site_only():
	for name, functions in (
		("books.py", ("def ensure", "def synced", "def catch_up")),
		("sales.py", ("def signed_up", "def paid", "def abandoned")),
	):
		source = _read(name)
		for function in functions:
			body = source.split(function, 1)[1].split("\ndef ", 1)[0]
			assert "site.is_admin()" in body, f"{name} {function}"
