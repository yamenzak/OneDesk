"""What OneAI adds to the agreements: which companies run the models, and what
they receive. Every model call goes through one_admin/gateway.py, which holds
no provider key; the keys are in Cloudflare's AI Gateway. See
trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause, service, subprocessor

M = registry.name("one_ai")

CLOUDFLARE = "Standard Contractual Clauses and Cloudflare's data processing addendum"

clause(
	document="privacy",
	section="modules",
	key="oneai-search-index",
	module=M,
	body="""
		So that OneAI and search find things by what they mean, the text of documents, mail and records is cut
		into pieces. Each piece is turned into numbers by a model. The pieces and their numbers are kept in
		Cloudflare R2, in the workspace's region and its own folder. What OneAI was asked to remember is kept
		the same way. Only your workspace's search reaches that folder, with a key that lasts an hour. A piece
		goes when what it came from is deleted, and the folder goes when the workspace is closed.
	""",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Object storage (R2) for the workspace's search index",
	data="Pieces of the text of documents, mail and records, and of what OneAI was asked to remember, each with its vector",
	where="The storage location chosen when the workspace was created",
	safeguard=CLOUDFLARE,
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="AI Gateway, which every model call passes through, and Workers AI, which runs the open-weight "
	"models in our catalogue",
	data="What OneAI sends a model, including records and documents it was asked to read, and the answer",
	where="Cloudflare's network, on the nearest location able to run the model",
	safeguard=CLOUDFLARE,
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

subprocessor(
	name="Google LLC",
	module=M,
	purpose="The Gemini models in our catalogue, through Google's API",
	data="What OneAI sends a model, including records and documents it was asked to read, and the answer",
	where="The United States and Google's regional endpoints",
	safeguard="Standard Contractual Clauses and Google's data processing terms",
	url="https://cloud.google.com/terms/data-processing-addendum",
)

clause(
	document="privacy",
	section="modules",
	key="oneai-reads",
	module=M,
	body="""
		When you ask OneAI something, it reads the records it needs to answer, as you: it cannot read anything
		you could not open yourself. What it read and what it answered is kept as your conversation, which you
		can see and delete. What OneAI remembers about how you work is listed in your settings, and you can
		remove any of it.
	""",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Web search, which passes each question OneAI looks up to the search provider",
	data="The question OneAI searches the web for, never a record",
	where="Cloudflare's network",
	safeguard=CLOUDFLARE,
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
	service="web_search",
)

subprocessor(
	name="Exa Labs, Inc.",
	module=M,
	purpose="Web search, which answers the questions OneAI looks up on the web",
	data="The question OneAI searches the web for, never a record",
	where="The United States",
	safeguard="Standard Contractual Clauses",
	url="https://exa.ai/privacy-policy",
	service="web_search",
)

service(
	key="web_search",
	module=M,
	title="Web Search",
	does="Lets OneAI look things up on the web: a new lead's company, a supplier, a product or a general question.",
	sends="Only the question OneAI searches for, through Cloudflare to Exa. Never a record, a document or a message.",
	off="OneAI answers from the workspace alone and says when it would need the web.",
	hosts=("onedesk.one_admin.proxy.ai_web_search",),
)

clause(
	document="privacy",
	section="modules",
	key="oneai-web-search",
	module=M,
	body="""
		Web search is off until your workspace's administrators turn it on. While it is on, OneAI can look
		something up on the web. Only the question it searches for leaves your workspace, through Cloudflare
		to Exa, and never a record, a document or a message. Each search is charged to your credits.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneai-agents",
	module=M,
	body=f"""
		Each app's agent, such as {registry.name("one_book")}'s accountant, works for your workspace from Cloudflare Workers. It
		reads and changes your records only through your workspace, as a user of its own with its app's roles.
		{registry.name("one_mail")}'s receptionist may also read the records a mail is linked to, and only the mail
		of a mailbox your administrator lets {registry.name("one_ai")} read. Every call it makes back is signed for your workspace alone and lasts two minutes at most. Cloudflare
		keeps, for each agent, the work waiting for it and which mail and documents it was handed, by their
		names in your workspace.
	""",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="Workers and Durable Objects, where each app's agent runs and keeps the work it was handed",
	data="The names of the mail and documents an agent was handed, and the work waiting for it",
	where="Cloudflare's network, in the location nearest the workspace's server when the agent first worked",
	safeguard=CLOUDFLARE,
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)
