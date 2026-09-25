"""What OneMail adds to the agreements: who carries the mail, and the two
lookups it makes to draw people's faces and organisations' logos
(one_mail/faces.py). See one_legal/README.md."""

from onedesk.one_legal.registry import clause, subprocessor

M = "OneMail"

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Sending mail from addresses on the workspace's own mail domain",
	data="The messages sent, their attachments, and their senders' and recipients' addresses",
	where="Cloudflare's network",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

subprocessor(
	name="Automattic Inc.",
	module=M,
	purpose="Gravatar, asked once for the picture of a person whose address appears in the workspace",
	data="A one-way hash of the person's email address, never the address itself",
	where="The United States",
	safeguard="Standard Contractual Clauses and Automattic's data processing addendum",
	url="https://automattic.com/privacy/",
)

subprocessor(
	name="Google LLC",
	module=M,
	purpose="Google's favicon service, asked once for the logo of an organisation that appears in the "
	"workspace",
	data="The organisation's web domain, never a person's address",
	where="The United States and Google's regional endpoints",
	safeguard="Standard Contractual Clauses and Google's data processing terms",
	url="https://cloud.google.com/terms/data-processing-addendum",
)

clause(
	document="privacy",
	section="modules",
	key="onemail-faces",
	module=M,
	body="""
		To show who a message is from, One asks Gravatar for a person's picture, sending only a one-way hash
		of their address, and asks Google for an organisation's logo, sending only its web domain. Each is
		asked once, by our server and never by your browser, and the answer is kept in the workspace, so
		nobody outside learns when a message is opened.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="onemail-mailboxes",
	module=M,
	body="""
		A mailbox connected from another provider is read and sent through that provider, with the sign-in
		details you give, which are kept encrypted in the workspace. That provider is yours, not ours, and its
		own terms apply to it.
	""",
	order=20,
)
