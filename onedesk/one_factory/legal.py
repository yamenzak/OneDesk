"""What OneFactory adds to the agreements: what OneAI reads and drafts in it.
See one_factory/ai.py and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneFactory"

clause(
	document="ai",
	section="modules",
	key="onefactory-asks",
	module=M,
	body="""
		In OneFactory, OneAI reads bills of materials, work orders, job cards, workstations and subcontracting
		orders as you see them. That covers what is being made, how far each step has got, who is on it, and
		what is out with which supplier. A work order it suggests is made only when you approve it. It stays
		a draft until it is submitted.
	""",
)
