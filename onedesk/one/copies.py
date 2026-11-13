"""Training Copies, this workspace's optional service: while it is on, the
workspace says so to One's account every hour (one_admin/sessions.py reads it
to decide whether a copy may be made, and to delete one that has lost it)."""

from onedesk.one import account
from onedesk.trust_center import services

KEY = "training_copies"


def said() -> None:
	"""Hourly: on, and agreed to, or nothing is sent at all."""
	if account.configured():
		services.call(KEY, account.ask, "onedesk.one_admin.proxy.copies_agreed")
