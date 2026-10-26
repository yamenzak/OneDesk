"""OneCRM's lists, kept in its ControlCenter (one/lists.py)."""

from frappe import _lt

LISTS = (
	("Customer Group", _lt("Customer Groups"), _lt("Customer Group")),
	("Territory", _lt("Territories"), _lt("Territory")),
	("Industry Type", _lt("Industries"), _lt("Industry")),
	("Market Segment", _lt("Market Segments"), _lt("Market Segment")),
	("UTM Source", _lt("Lead Sources"), _lt("Lead Source")),
	("Opportunity Lost Reason", _lt("Lost Reasons"), _lt("Lost Reason")),
	("Issue Type", _lt("Issue Types"), _lt("Issue Type")),
	("Issue Priority", _lt("Issue Priorities"), _lt("Issue Priority")),
)
