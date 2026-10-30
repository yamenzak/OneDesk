import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from onedesk.one_display import sizes, widgets


class WidgetCollection(Document):
	def validate(self):
		sizes.settle(self)
		for row in self.widgets:
			spec = widgets.TYPES.get(row.widget_type)
			if not spec:
				frappe.throw(_("There is no widget called {0}.").format(row.widget_type))
			if row.source:
				kind = frappe.db.get_value("Display Source", row.source, "kind")
				if kind not in spec["sources"]:
					frappe.throw(_("A {0} cannot show {1}.").format(_(spec["label"]), row.source))
			elif spec["sources"] and not spec["slots"] and row.widget_type != "Custom":
				frappe.throw(_("Choose what the {0} shows.").format(_(spec["label"])))
			for key in ("mapping", "settings"):
				row.set(key, _object(row.get(key)))
			row.w = min(max(flt(row.w), 1), 100)
			row.h = min(max(flt(row.h), 1), 100)
			row.x = min(max(flt(row.x), 0), 100 - row.w)
			row.y = min(max(flt(row.y), 0), 100 - row.h)


def _object(text) -> str:
	try:
		said = json.loads(text or "{}")
	except ValueError:
		frappe.throw(_("A widget's settings could not be read."))
	if not isinstance(said, dict):
		frappe.throw(_("A widget's settings could not be read."))
	return json.dumps(said, ensure_ascii=False)
