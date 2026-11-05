"""What OneQuality adds to the agreements: who raised what went wrong, and
what OneAI reads in it. See one_quality/tell.py and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneQuality"

clause(
	document="privacy",
	section="modules",
	key="onequality-problems",
	module=M,
	body="""
		OneQuality keeps who raised each non conformance and who owns each procedure, by name. The quality
		managers are told when a non conformance is raised, and see who raised it. Customer feedback names
		the customer it came from.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onequality-asks",
	module=M,
	body="""
		In OneQuality, OneAI reads procedures, goals, reviews, non conformances, actions, meetings and
		feedback as you see them. It changes none of them.
	""",
)
