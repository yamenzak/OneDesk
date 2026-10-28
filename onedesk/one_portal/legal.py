"""What OnePortal adds to the agreements. See one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OnePortal"


clause(
	document="dpa",
	section="modules",
	key="portal",
	module=M,
	body="""
		Your workspace can let its customers' and suppliers' contacts sign in to its portal, by inviting them
		as users from their contact. Each sees only the records linked to their own customer or supplier: a
		customer's quotations, orders, invoices, shipments, addresses, projects and timesheets; a supplier's
		requests for quotation, quotes, purchase orders and purchase invoices. Your organisation decides whom
		to invite and is responsible for what those records say. A link sent from a record opens that one
		record, without an account, to whoever holds it, until it expires or your workspace revokes it.
	""",
	order=40,
)
