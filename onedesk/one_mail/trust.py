"""What OneMail adds to the agreements: who carries the mail, and the two
lookups it makes to draw people's faces and organisations' logos
(one_mail/faces.py). See trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause, service, subprocessor

M = registry.name("one_mail")

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
	service="gravatar",
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
	service="logos",
)

service(
	key="gravatar",
	module=M,
	title="Pictures from Gravatar",
	does="Shows the picture a person chose on Gravatar beside their mail and on their contact.",
	sends="A one-way hash of each email address that appears in the workspace, once, to Automattic.",
	off="A person shows as their initials. Pictures already found stay until somebody removes them.",
	hosts=("www.gravatar.com",),
)

service(
	key="logos",
	module=M,
	title="Logos from Google",
	does="Shows an organisation's logo beside its mail, its customers and its suppliers.",
	sends="The web domain of each organisation that appears in the workspace, once, to Google.",
	off="An organisation shows without a logo. Logos already found stay until somebody removes them.",
	hosts=("t1.gstatic.com",),
)

clause(
	document="privacy",
	section="modules",
	key="onemail-faces",
	module=M,
	body="""
		To show who a message is from, One can draw a picture of a person or the logo of an organisation.
		Pictures from Gravatar receive a one-way hash of a person's email address, never the address itself.
		Logos from Google receive an organisation's web domain, your own company's included. Each is an
		optional service, off until your workspace's administrators turn it on. Each is asked once, by our
		server and never by your browser. The answer is kept in the workspace, so nobody outside learns when
		a message is opened. A picture uploaded to a record always comes first.
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

clause(
	document="privacy",
	section="modules",
	key="onemail-risky-mail",
	module=M,
	body="""
		OneMail checks each message that arrives for signs of fraud. It reads what the receiving server
		found of the sender, the message's links and attachments, and whether the sender's domain imitates
		one your workspace knows. The check runs in your workspace, and nothing of it is sent out. What it
		found is kept with the message for as long as the message is kept. A message it holds back is seen
		only by the people who use its mailbox. No rule or AI agent sees it until one of them releases it.
	""",
	order=30,
)

clause(
	document="privacy",
	section="modules",
	key="onemail-previews",
	module=M,
	body="""
		Before you open a link in a message, OneMail can preview it. Only the link's address is sent to a
		browser we run on Cloudflare, which opens it without your sign-in or cookies. A picture of the page,
		where it ended and whether it asks for a password come back, and the browser is closed. Each preview
		uses credits. Before you open an attachment, it is sent to a service we run on Cloudflare. That
		service reads what the file is and what an archive holds, and keeps nothing. A Word, Excel or
		PowerPoint file is also turned into a PDF without macros, in the containers OneCloud uses. That PDF
		is kept with the file in the workspace. The original is never changed. This happens only when
		somebody who uses the mailbox opens the link or the file.
	""",
	order=40,
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="A throwaway browser that opens a link from a message, when somebody asks to preview it",
	data="The link's address, and the page it opens, for the seconds the preview takes",
	where="Cloudflare's network",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Checking an attachment before it is opened, and turning an Office file into a PDF without macros",
	data="The attachment, for the seconds the check takes",
	where="Cloudflare's network, on the nearest location able to run the check",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)


clause(
	document="ai",
	section="modules",
	key="onemail-asks",
	module=M,
	body="""
		In OneMail, you can ask OneAI to summarise a conversation, say what waits for an answer, or draft a
		reply. To answer, the text of that conversation is sent to the model. This happens only when you ask,
		and only for a conversation in a mailbox you hold. Nothing of it is kept but the answer. What you ask
		for is never sent on its own: approving a reply opens it in the email window, where you read it, change
		it and send it yourself. You can also ask OneAI to improve, shorten, translate or change the tone of an email you are
		writing. Then what you have written, its subject, its recipients and the message it answers are sent
		to the model. Your signature is not. The suggestion goes into your email window only when you approve
		it.
	""",
)


clause(
	document="ai",
	section="modules",
	key="onemail-answers",
	module=M,
	meets=("ai_act.50",),
	body="""
		A mailbox's Automation can also answer mail by itself. Someone allowed to set its rules says what a reply
		should say, and OneAI writes it and sends it from the mailbox. It answers once per conversation or per
		sender, as the rule says, and never an automatic address. Every such reply says an AI agent may have
		written it entirely and automatically, and that it may be wrong or inaccurate. When the rule allows it, OneAI reads the records of the sender's own company to answer. It does
		so only for a sender whose mail the receiving server verified, and only that company's records.
	""",
	order=20,
)
