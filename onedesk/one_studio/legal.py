"""What OneStudio adds to the agreements: OneAI writes code that runs in a
workspace, an administrator decides whether it runs, and a workspace's own
record types are its content. See one_studio/README.md and
one_legal/README.md."""

from onedesk.one_legal.registry import clause

M = "OneStudio"

clause(
	document="terms",
	section="modules",
	key="onestudio-extensions",
	module=M,
	body="""
		In OneStudio, OneAI writes extensions for your workspace when one of your administrators asks:
		code that runs when your people open or save a record. A second reading checks each against
		what it says it does before it can be turned on, and nothing runs until an administrator turns
		it on. Turning one on is your decision, and what it does in your workspace is your
		responsibility, as any setting your administrators choose is. We keep its code, and may read it
		to keep the service safe or to help you. We may turn off an extension that endangers the
		service or other customers, and tell your administrators why.
	""",
)

clause(
	document="terms",
	section="modules",
	key="onestudio-record-types",
	module=M,
	body="""
		A record type your administrators make in OneStudio, and every record of it, is your content,
		under the same terms as any other record in your workspace, and is in the full download.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onestudio-asks",
	module=M,
	body="""
		In OneStudio, when an administrator asks, OneAI writes an extension, or designs a record type
		from what they describe. The code of an extension is read a second time by a separate model,
		shown the code and what it says it does and nothing of the conversation, and an extension it
		does not pass cannot be turned on. Neither runs until an administrator approves it. OneAI can
		write code that is wrong; an extension that runs into a mistake is written down and the record
		still saves, and your administrators are told.
	""",
)
