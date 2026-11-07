"""A non conformance or a quality action saved with no company, by OneAI, an
import or a script, is the reader's default company's, as the form would
have filled it."""

import erpnext


def fill(doc, method=None) -> None:
	"""before_validate on Non Conformance and Quality Action."""
	if not doc.get("company"):
		doc.company = erpnext.get_default_company()
