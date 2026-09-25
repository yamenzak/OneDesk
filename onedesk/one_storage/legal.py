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
