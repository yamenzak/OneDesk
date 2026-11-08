from frappe import _


def dashboard(data: dict) -> dict:
	"""A non-conformance's connections: the quality actions raised for it.
	Declared here rather than as a DocType Link in the custom JSON, which a
	fresh install validates before Quality Action has the column."""
	data["fieldname"] = "one_non_conformance"
	data["transactions"] = [*(data.get("transactions") or []), {"label": _("Actions"), "items": ["Quality Action"]}]
	return data
