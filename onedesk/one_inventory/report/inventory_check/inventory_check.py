"""What will fail the first time somebody receives stock, counts it or
registers an asset, with the fix beside it. The checks are
one_inventory/ready.py's."""

from onedesk.one_book.report.books_check.books_check import columns
from onedesk.one_inventory import ready


def execute(filters=None):
	return columns(), ready.checks()
