"""What OneBook adds to the agreements: what OneAI reads of the books. See
one_book/agent.py and trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause

M = registry.name("one_book")

clause(
	document="ai",
	section="modules",
	key="onebook-asks",
	module=M,
	body="""
		In OneBook, when you ask OneAI about the money, it reads the books as you may see them: what is in the
		bank, what customers and suppliers owe and how late, an invoice with the payments that settled it,
		and the bank lines still to match. It drafts a payment reminder for you to send, and never posts,
		pays or changes anything in the books.
	""",
)
