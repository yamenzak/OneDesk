"""What OneInventory tells people, as notification types (one/notify.py).

One is ours, a supplier's quote from the portal. The rest are ERPNext's: one
it mailed and now tells here (tell.py), one of its rules carried to the bell,
the quote request it mails a supplier, and the reports its nightly jobs mail
when they fail, which nothing lets us send in its place.
"""

from frappe import _lt

TYPES = [
	# tell: a Material Request raised by reordering.
	{
		"name": _lt("Material Request Raised"),
		"app": "OneInventory",
		"roles": ("Purchase Manager", "Stock Manager"),
		"about": _lt("When items fall to their reorder level and a material request is raised for them."),
		"to": _lt("Purchasing"),
		"subject": _lt("Reordering raised {request}"),
		"message": _lt("For what fell to its reorder level: {items}."),
		"email_default": True,
		"replaces": (("Stock Settings", "reorder_email_notify"),),
		"starts_as": ("Stock Settings", "reorder_email_notify"),
	},
	# ours: a supplier answered a quote request on the portal (one/portal.py).
	{
		"name": _lt("Quote Received"),
		"app": "OneInventory",
		"roles": ("Purchase Manager", "Purchase User"),
		"about": _lt("When a supplier sends a quote for your request."),
		"to": _lt("Whoever made the request"),
		"subject": _lt("{supplier} sent a quote for {request}"),
		"message": _lt("{total} for {items}."),
		"email_default": True,
	},
	# What ERPNext mails a supplier when a request is sent to them, with the
	# link to answer it on the portal.
	{
		"name": _lt("Quote Request Sent"),
		"app": "OneInventory",
		"about": _lt("When a quote request is sent to a supplier, with the link to answer it."),
		"to": _lt("The supplier's contact"),
		"mailed_by": True,
	},
	# ERPNext's own rule, carried to the bell in its words (one/rules.py).
	{
		"name": _lt("Material Request Received"),
		"app": "OneInventory",
		"about": _lt("When what your material request asked for is received."),
		"to": _lt("Whoever made the request"),
		"words": True,
		"rule": "Material Request Receipt Notification",
		"email_default": True,
	},
	# What ERPNext mails itself when a job fails, listed so everything sent is
	# on one page.
	{
		"name": _lt("Depreciation Not Posted"),
		"app": "OneInventory",
		"about": _lt("When the nightly job cannot post depreciation."),
		"to": _lt("The role Accounts Settings names"),
		"mailed_by": True,
	},
	{
		"name": _lt("Reposting Failed"),
		"app": "OneInventory",
		"about": _lt("When stock values cannot be recalculated after a back-dated entry."),
		"to": _lt("Stock managers"),
		"mailed_by": True,
	},
	{
		"name": _lt("Stock Account Wrong"),
		"app": "OneInventory",
		"about": _lt("When a warehouse's account is not a stock account, so stock and books disagree."),
		"to": _lt("Stock managers"),
		"mailed_by": True,
	},
	{
		"name": _lt("Reordering Failed"),
		"app": "OneInventory",
		"about": _lt("When reordering cannot raise a material request."),
		"to": _lt("The site's administrators"),
		"mailed_by": True,
	},
]
