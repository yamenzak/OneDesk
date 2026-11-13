"""What OneStudio adds to the agreements: OneAI writes code that runs in a
workspace, an administrator decides whether it runs, and a workspace's own
custom collections are its content. See one_studio/AGENTS.md and
trust_center/AGENTS.md."""

from onedesk.trust_center.registry import clause

M = "OneStudio"

clause(
	document="terms",
	section="modules",
	key="onestudio-extensions",
	module=M,
	body="""
		In OneStudio, OneAI writes extensions for your workspace when one of your administrators asks:
		code that runs when your people open or save a record, when they use one of the service's own
		pages, or on its own on a schedule. Before an extension is kept, its code is tried once on one of
		your records and what it changed is undone at once. A second reading checks each against what
		it says it does before it can be turned on, and nothing runs until an administrator turns it
		on. Turning one on is your decision, and what it does in your workspace is your
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
		A custom collection your administrators make in OneStudio, and every record in it, is your
		content. It is under the same terms as any other record in your workspace, and is in the full
		download.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onestudio-asks",
	module=M,
	body="""
		In OneStudio, when an administrator asks, OneAI writes an extension, or designs a custom
		collection from what they describe. The code of an extension is read a second time by a
		separate model, shown the code and what it says it does and nothing of the conversation. An
		extension it does not pass cannot be turned on. Before it is kept, the code is tried once on
		one of your records and undone. What happened, which can include that record's name and a
		message it showed, is told to OneAI so it can mend the code. Neither runs until an
		administrator approves it. OneAI can write code that is wrong; an extension that runs into an
		error is written down, the work goes on, and your administrators are told. When an
		administrator asks OneAI to mend one, a separate model is shown its code and its recent
		errors, which can include what was in the records it ran on. It writes the extension again,
		read a second time and kept off like any other.
	""",
)
