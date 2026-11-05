"""What OneInventory adds to the agreements: who holds which of the company's
equipment, and what OneAI reads and drafts in it. See one_inventory/custody.py,
one_inventory/ai.py and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneInventory"

clause(
	document="privacy",
	section="modules",
	key="oneinventory-equipment",
	module=M,
	body="""
		OneInventory keeps which of the organisation's equipment each person holds, from when, and every
		handover. Whoever keeps the stores and whoever works in HR can see it, and a person's own page says
		how much they hold. A person given something is told in One, and may be asked to sign a printed
		handover naming them, their job and department. When somebody leaves, what they hold is listed for
		them to give back. A service on a piece of equipment names whoever does it, and they are told when
		it is due or late.
	""",
)

clause(
	document="ai",
	section="modules",
	key="oneinventory-asks",
	module=M,
	body="""
		In OneInventory, OneAI reads items, the stores, orders, receipts, deliveries, counts and equipment as
		you see them. That covers what is held and where, and what is ordered from which supplier at what
		price. It also covers who holds each piece of equipment with its services and repairs. Anything it suggests, such as a receipt, a transfer or a
		change to an item, is made only when you approve it. It stays a draft until it is submitted.
	""",
)
