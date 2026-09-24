"""Whether files are going to cloud storage, with the fix beside each. The
checks are one_storage/ready.py's."""

from onedesk.one_book.report.books_check.books_check import columns
from onedesk.one_storage import ready


def execute(filters=None):
	return columns(), ready.checks()
