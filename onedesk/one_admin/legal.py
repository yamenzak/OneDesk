"""What running a workspace adds to the agreements: where it runs, how it is
reached, and who takes the money. See one_legal/README.md."""

from onedesk.one_legal.registry import clause, subprocessor

M = "OneAdmin"

subprocessor(
	name="Frappe Technologies Pvt. Ltd.",
	module=M,
	purpose="Frappe Cloud, the managed platform each workspace runs on: the site, its database and its daily "
	"backups",
	data="Everything in the workspace's database",
	where="The region chosen when the workspace was created",
	safeguard="Standard Contractual Clauses and Frappe's data processing addendum",
	url="https://frappecloud.com/policies",
)

subprocessor(
	name="Cloudflare, Inc.",
	module=M,
	purpose="The network every workspace is reached through: its addresses, their certificates, and the router "
	"that sends each request to the workspace",
	data="Every request to the workspace and its answer, as they pass through",
	where="The Cloudflare data centre nearest the person, then the region the workspace runs in",
	safeguard="Standard Contractual Clauses and Cloudflare's data processing addendum",
	url="https://www.cloudflare.com/cloudflare-customer-dpa/",
)

subprocessor(
	name="Stripe, Inc.",
	module=M,
	purpose="Taking payment and holding the payment method",
	data="The billing contact, company name and address, and the card details you give Stripe directly, "
	"which we never see",
	where="The United States and Ireland",
	safeguard="Standard Contractual Clauses and Stripe's data processing agreement",
	url="https://stripe.com/legal/dpa",
)

clause(
	document="privacy",
	section="modules",
	key="oneadmin-asks",
	module=M,
	body="""
		The people who run One can ask OneAI what needs their attention in the console. To answer, it reads
		your organisation's account as the console shows it: the workspace's name, its contact's email
		address, what is owed and since when, and why a job or a domain has stopped. OneAI changes nothing
		from there, and what it reads is handled as the AI Addendum says.
	""",
)
