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
	name="Cloudflare, Inc.",
	module=M,
	purpose="Sending One's own mails to customers: sign-in links, signup and billing notices",
	data="The recipient's address and the mail",
	where="Cloudflare's network",
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


clause(
	document="privacy",
	section="modules",
	key="oneadmin-signup",
	module=M,
	body="""
		When somebody asks for a workspace on our signup page, we keep what they type (their email address,
		the workspace's name and address, the plan and their country) whether or not they go on to pay. It
		becomes a lead and a deal in our own records, so we can follow up a signup that was not finished. A
		signup not paid for within seven days lets its workspace name go; what was typed is kept with our
		sales records. We write to that address once, a day after, if payment was not finished, and if
		payment is taken and the workspace cannot be made yet, we write to say so.
	""",
)


clause(
	document="privacy",
	section="modules",
	key="oneadmin-account",
	module=M,
	body="""
		Whoever pays for a workspace has a One account with us, under the email address they paid with. It
		keeps that address and which workspaces it holds, so the account can list them in one place. You sign
		in to it with a link we mail to that address, which works once and for a few minutes; there is no
		password to keep. Each sign-in to the account is logged with its time and the network address it came
		from, to keep the account safe. The account is separate from your sign-in to each workspace. A workspace's
		administrator can make another address the one who pays; that address gets an account, and both
		addresses are told. A new address for your account is used only once a link mailed to it is followed.
	""",
)


clause(
	document="terms",
	section="account",
	key="oneadmin-signup-agree",
	module=M,
	body="""
		You first agree to these terms and the Privacy Policy when you continue
		to payment on our signup page, where each is linked and can be read in full. The first time you sign
		in to the workspace you are asked again, and that acceptance, with its date, version and account, is
		the one recorded.
	""",
)


clause(
	document="terms",
	section="fees",
	key="oneadmin-given-credits",
	module=M,
	order=31,
	body="""
		We may also give your workspace credits ourselves, for example to make up for a problem. Those
		credits expire on the date we tell your workspace's administrators when we give them, or never if we
		give none. If we give credits by mistake, we may take back what is left of them unused.
	""",
)
