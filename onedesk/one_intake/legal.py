"""What Intake adds to the agreements. It is the one part of One that acts
without being asked each time, so the AI Addendum has to say so plainly. See
one_legal/README.md and one_intake/README.md."""

from onedesk.one_legal.registry import clause

M = "Intake"

clause(
	document="ai",
	section="modules",
	key="intake-acts",
	module=M,
	body="""
		When a workspace turns Intake on, OneAI reads the mail and files that arrive and acts on them without
		being asked each time: it files them, links them to the records they are about, and drafts what they
		call for. It acts only as far as the workspace's Intake settings allow, and as the person the document
		was read for. A second model checks what the first did. Every action is recorded and marked as OneAI's,
		anything uncertain waits for a person, and whatever it did can be undone.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="intake-reads",
	module=M,
	body="""
		With Intake on, the text of arriving mail and files, and anything in them, is sent to the models in the
		AI Addendum to be read. What was read is kept in the workspace with the document, for the people it
		was read for.
	""",
)
