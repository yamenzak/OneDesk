"""What happened to a workspace, in the order it happened.

Written by the machinery rather than by a person: the nightly measurement, the
lifecycle ladder, the reconcile against press. It is the answer to "why is this
workspace suspended", which is a question asked at a bad moment and deserves a
row rather than a log line.
"""

from frappe.model.document import Document


class TenantEvent(Document):
	pass
