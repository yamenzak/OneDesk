"""What OneCloud adds to the agreements. Files are the part of a workspace that
leaves its database: the bytes go to an object store, in the region the
workspace chose. See one_legal/README.md."""

from onedesk.one_legal.registry import clause, subprocessor

M = "OneCloud"

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Object storage (R2) for every file",
	data="File contents and names, and whatever personal data the files contain",
	where="The storage location chosen when the workspace was created",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

clause(
	document="privacy",
	section="modules",
	key="onecloud-files",
	module=M,
	body="""
		OneCloud keeps the files your organisation uploads and the ones One makes, such as a message's
		attachments. The files themselves are kept in Cloudflare R2 in the workspace's region; what a file is
		called, who owns it and who it is shared with stays in the workspace's own database.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="onecloud-outside",
	module=M,
	body="""
		A file or folder in OneCloud can be shared with people outside your organisation by a link, which
		its maker may limit to invited addresses, protect with a password or code, and let expire. A file
		request asks people outside to send files through their own link; what they send is kept in the
		workspace like any other file, and your organisation is responsible for it. A server connected under
		Network is reached with the address and password given for it, kept encrypted in the workspace and
		used only to reach that server for the people it is shared with.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onecloud-asks",
	module=M,
	body="""
		In OneCloud, when you ask OneAI about a file, to summarise it or answer a question about it, the text
		of that file is sent to the model to answer you. Only when you ask, only a file you may open, and
		nothing of it is kept but the answer. OneAI changes nothing in OneCloud: sharing, moving and deleting
		stay yours. Read with OneAI on a file reads that one file as a folder OneAI reads would.
	""",
)
