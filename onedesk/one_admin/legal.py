"""What running a workspace adds to the agreements: where it runs, and who
takes the money. See one_legal/README.md."""

from onedesk.one_legal.registry import subprocessor

M = "One Admin"

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
	name="Stripe, Inc.",
	module=M,
	purpose="Taking payment and holding the payment method",
	data="The billing contact, company name and address, and the card details you give Stripe directly, "
	"which we never see",
	where="The United States and Ireland",
	safeguard="Standard Contractual Clauses and Stripe's data processing agreement",
	url="https://stripe.com/legal/dpa",
)
