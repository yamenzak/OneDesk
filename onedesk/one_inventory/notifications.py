"""What OneInventory tells people, as notification types (one/notify.py).

All of them are ERPNext's: one it mailed and now tells here (tell.py), one of
its rules carried to the bell, and the reports its nightly jobs mail when
they fail, which nothing lets us send in its place.
"""

from frappe import _lt

TYPES = [
	# tell: a Material Request raised by reordering.
	{
		"name": _lt("Material Request Raised"),
		"app": "OneInventory",
		"roles": ("Purchase Manager", "Stock Manager"),
		"about": _lt(
			"Items fell to their reorder level and a material request was raised for them. Sent to Purchasing."
		),
		"subject": _lt("Reordering raised {request}"),
		"message": _lt("For what fell to its reorder level: {items}."),
		"email_default": True,
		"replaces": (("Stock Settings", "reorder_email_notify"),),
		"starts_as": ("Stock Settings", "reorder_email_notify"),
	},
	# ERPNext's own rule, carried to the bell in its words (one/rules.py).
	{
		"name": _lt("Material Request Received"),
		"app": "OneInventory",
		"about": _lt("What a material request asked for was received. Sent to whoever made the request."),
		"words": "ERPNext",
		"rule": "Material Request Receipt Notification",
		"email_default": True,
	},
	# What ERPNext mails itself when a job fails, listed so everything sent is
	# on one page.
	{
		"name": _lt("Depreciation Not Posted"),
		"app": "OneInventory",
		"about": _lt(
			"Depreciation the nightly job could not post. Mailed to the role Accounts Settings names."
		),
		"mailed_by": "ERPNext",
	},
	{
		"name": _lt("Reposting Failed"),
		"app": "OneInventory",
		"about": _lt(
			"Stock values could not be recalculated after a back-dated entry. Mailed to Stock Managers."
		),
		"mailed_by": "ERPNext",
	},
	{
		"name": _lt("Stock Account Wrong"),
		"app": "OneInventory",
		"about": _lt(
			"A warehouse's account is not a stock account, so stock and books disagree. Mailed to Stock Managers."
		),
		"mailed_by": "ERPNext",
	},
	{
		"name": _lt("Reordering Failed"),
		"app": "OneInventory",
		"about": _lt("Reordering could not raise a material request. Mailed to the site's administrators."),
		"mailed_by": "ERPNext",
	},
]
