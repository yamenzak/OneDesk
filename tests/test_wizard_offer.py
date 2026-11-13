"""What the signup wizard sends the browser (one_admin/wizard_offer.py)."""

from unittest import mock

from onedesk.one_admin import wizard_offer


class Lazy:
	"""Stands for frappe's _lt: translated only when made a string."""

	def __str__(self):
		return "Company Domain"


def test_a_steps_words_reach_the_browser_as_strings():
	"""A step declares its words with _lt, and a response carries only
	strings: the wizard's second screen failed on one."""
	with mock.patch.object(wizard_offer, "_", side_effect=lambda text: text):
		assert type(wizard_offer.said(Lazy())) is str
		assert wizard_offer.said(None) == ""
