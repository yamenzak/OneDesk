"""What OneCloud adds to the agreements. Files are the part of a workspace that
leaves its database: the bytes go to an object store, in the region the
workspace chose. See one_legal/AGENTS.md."""

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

clause(
	document="ai",
	section="modules",
	key="onecloud-makes",
	module=M,
	body="""
		In OneCloud, OneAI can make a picture, music, a short video or speech from what you describe. It is
		sent only that description, or the words to be read aloud. What it makes is saved as a file in the
		folder you asked from, where it can be moved or deleted like any other file.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="onecloud-converts",
	module=M,
	body="""
		A Word, Excel, PowerPoint or similar file can be previewed or saved as a PDF in OneCloud when somebody
		asks. The file is sent to a container we run on Cloudflare, turned into a PDF there and sent back. The
		container keeps nothing; the preview is kept in the workspace for a day, and each conversion uses 1
		credit.
	""",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Containers that turn a file a browser can't open into a PDF, when somebody asks for a preview or a PDF",
	data="The file being converted, for the seconds the conversion takes",
	where="Cloudflare's network, on the nearest location able to run the container",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

clause(
	document="privacy",
	section="modules",
	key="onecloud-oneos",
	module=M,
	body="""
		A Word, Excel, PowerPoint, OpenDocument or CSV file can be opened in OneOS, a desktop shown in the browser,
		when somebody asks. The file is copied to a container we run on Cloudflare, used only for that session.
		What is shown and typed passes between the browser and the container through Cloudflare. Each save is
		sent back to the workspace as a new version of the file. The container and its copy of the file are
		deleted when the session ends: when it is closed, after 15 minutes without use, or after 8 hours at most.
		Each minute it is open uses OneCredits.
	""",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Containers that run OneOS, the desktop in the browser, while somebody has a file open in it",
	data="The file opened, what is shown and typed while it is open, and each version saved back",
	where="Cloudflare's network, on the nearest location able to run the container",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)
