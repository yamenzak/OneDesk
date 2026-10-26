"""What OneAI adds to the agreements: which companies run the models, and what
they receive. Every model call goes through one_admin/gateway.py, which holds
no provider key; the keys are in Cloudflare's AI Gateway. See
one_legal/README.md."""

from onedesk.one_legal.registry import clause, service, subprocessor

M = "OneAI"

CLOUDFLARE = "Standard Contractual Clauses and Cloudflare's data processing addendum"

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
