# Derived from frappe/suite@2831a5d (suite/slides/doctype/presentation/presentation.py). Copyright (c) Frappe Technologies Pvt. Ltd. AGPL-3.0.
"""A presentation's slides. The File in OneCloud is what people see, move,
share and delete; this is only what it holds. AGENTS.md, api.py.
"""

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, flt

from onedesk.one_cloud import editors


class Presentation(Document):
	def before_insert(self):
		editors.making(self)

	def before_save(self):
		self.slug = (self.title or "").lower().replace(" ", "-")

	def validate(self):
		for row in self.slides:
			if row.advance_after in (None, ""):
				continue
			if not re.fullmatch(r"[0-9]+(\.[0-9]+)?", cstr(row.advance_after)) or not 1 <= flt(row.advance_after) <= 3600:
				frappe.throw(
					_("Slide {0}: Advance After must be between 1 and 3600 seconds, not {1}").format(row.idx, row.advance_after)
				)
