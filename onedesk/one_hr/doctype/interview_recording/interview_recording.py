"""One sitting of one interview, recorded with the candidate's agreement.

Written to by `one_hr/hiring.py` and by nothing a person types: the recorder
adds parts as they are uploaded, and OneAI writes their transcripts. See
`docs/HIRING.md`.
"""

import frappe
from frappe.model.document import Document


class InterviewRecording(Document):
	def validate(self):
		if not self.agreed:
			frappe.throw(frappe._("An interview is only recorded once the candidate has agreed."))
