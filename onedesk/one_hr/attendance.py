"""What the Attendance record links to.

hrms names its one transaction group with an empty label, which the form draws
as an unlabelled box above the connections. The groups are theirs; only the
label is ours.
"""

from frappe import _


def dashboard(data=None):
	data = data or {}
	for group in data.get("transactions") or []:
		if not group.get("label"):
			group["label"] = _("Time")
	return data
