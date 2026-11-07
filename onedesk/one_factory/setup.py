"""OneFactory's setup steps (one/setup_steps.py, docs/READY.md mechanism 9):
the account workshop time is costed to and the warehouses a new work order
takes, both on the Workshop tab of its settings (control.py)."""

from frappe import _lt

from onedesk.one_factory import control

STEPS = [
	{
		"key": "costed",
		"title": _lt("Workshop Time Is Costed"),
		"about": _lt("Making goods that take workshop time fails until the company names an account for it."),
		"needs": "costs",
		"tab": "workshop",
		"done": control.costed,
	},
	{
		"key": "placed",
		"title": _lt("Work Order Warehouses"),
		"about": _lt("Choose where a new work order takes its materials and puts what it makes, so nobody is asked each time."),
		"needs": "costs",
		"tab": "workshop",
		"done": control.placed,
	},
]
