"""One walk through the provisioning steps, resumable.

The work is in `one_admin/steps.py` and the driving is in `one_admin/runner.py`.
This is the record they read and write, and the only thing it decides for itself
is that a job nobody has scheduled runs now.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from onedesk.one_admin import site, steps


class ProvisioningJob(Document):
	def validate(self) -> None:
		site.require_admin()
		# Made by the machinery, never typed, so none of these is starred on
		# the form; a job for nobody is still refused.
		if not self.tenant:
			frappe.throw(_("A job is for a workspace."))
		self.kind = self.kind or "Provision"
		self.status = self.status or "Pending"
		if not self.step and self.status in ("Pending", "Waiting"):
			self.step = steps.ORDER[0]
		if not self.next_run_at:
			self.next_run_at = now_datetime()
