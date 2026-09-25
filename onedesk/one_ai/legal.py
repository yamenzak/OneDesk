"""What OneAI adds to the agreements: which companies run the models, and what
they receive. Every model call goes through one_admin/gateway.py, which holds
no provider key; the keys are in Cloudflare's AI Gateway. See
one_legal/README.md."""

from onedesk.one_legal.registry import clause, subprocessor

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
