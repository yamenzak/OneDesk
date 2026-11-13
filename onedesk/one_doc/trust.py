"""What OneDoc adds to the agreements: what OneAI is sent when it is asked
about the document that is open, and for a picture. A document is a file in
OneCloud, so what OneCloud's agreements say of a file holds for it. See
one_doc/AGENTS.md and trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause

M = registry.name("one_doc")

clause(
	document="ai",
	section="modules",
	key="onedoc-asks",
	module=M,
	body="""
		In OneDoc, OneAI can answer about the document you have open. It is sent the document's name, the
		start of what it says, and what you selected or the paragraph your cursor is in. For a document on a
		record, it is also sent which record and the names of its fields. It reads more of a document, or
		another one, only to answer you, and only one you may open. What it writes is a card, and the
		document changes only when you approve it. To make a picture, it is sent only the description you
		give, and the picture is kept in the document.
	""",
)
