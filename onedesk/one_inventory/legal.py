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
		In OneInventory, when you ask OneAI about an item, the stores, an order, a receipt, a delivery, a
		movement, a count, a work order or a piece of equipment, it reads them as you see them: what is held
		and where, what is ordered and from which supplier at what price, what the workshop is making, who
		holds a piece of equipment, its services and its repairs. A receipt, a delivery, a transfer, a request
		for quotation, a work order, a handover or a change to an item it suggests is made only when you
		approve it, and stays a draft until it is submitted.
	""",
)
