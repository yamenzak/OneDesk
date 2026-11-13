"""What running a workspace adds to the agreements: where it runs, how it is
reached, and who takes the money. See trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause, service, subprocessor

M = registry.name("one_admin")

subprocessor(
	name="Amazon Web Services EMEA SARL",
	module=M,
	purpose="The servers we rent for One on Amazon Lightsail: each workspace's site, its database, and a daily "
	"snapshot of each server kept for seven days",
	data="Everything in the workspace's database",
	where="Sweden (Stockholm)",
	safeguard="Standard Contractual Clauses and the AWS data processing addendum",
	url="https://d1.awsstatic.com/legal/aws-dpa/aws-dpa.pdf",
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
	purpose="Object storage (R2) for each workspace's backups, in a bucket locked for 30 days",
	data="A copy of the workspace's database, settings and files",
	where="One bucket for every workspace, whichever storage location the workspace chose",
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

service(
	key="training_copies",
	module=M,
	title="Training Copies",
	does="Lets us make a temporary copy of your workspace's database, on a separate server, for your people to train on.",
	sends="A copy of your workspace's database, not its files, to a server we rent from Oracle.",
	off="No copy can be made. Copies already made are deleted within 48 hours.",
	hosts=("onedesk.one_admin.proxy.copies_agreed",),
)

subprocessor(
	name="Oracle Corporation",
	module=M,
	purpose="A temporary copy of a workspace's database, on a separate server, for the people who train on it",
	data="A copy of the workspace's database, never its files",
	where="Germany (Frankfurt)",
	safeguard="Standard Contractual Clauses and Oracle's data processing agreement",
	url="https://www.oracle.com/corporate/contracts/cloud-services/",
	service="training_copies",
)

clause(
	document="privacy",
	section="modules",
	key="oneadmin-training-copies",
	module=M,
	body="""
		Training Copies is off until your workspace's administrators turn it on. While it is on, we can make a
		copy of your workspace's newest nightly database backup, without its files, on a separate server we rent
		from Oracle. Its mail and scheduled jobs are off. We do not sign in to a copy. Your people sign in with
		their own passwords. We delete a copy when its time ends, at most 30 days after it was made, and within
		48 hours of your administrators turning Training Copies off.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="oneadmin-error-summaries",
	module=M,
	body="""
		Each workspace sends us a summary of its own errors every hour: the kind of error, where in One's code
		it happened, how often and when. It sends no traceback and none of the data the error was working on.
		We read these summaries to find and fix faults in One.
	""",
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
		When somebody asks for a workspace on our signup page, we keep what they type, whether or not they
		go on to pay. That is their email address, the workspace's name and address, the plan and their
		country. It becomes a lead and a deal in our own records, so we can follow up a signup that was not
		finished. A signup not paid for within seven days lets its workspace name go; what was typed is kept
		with our sales records. We write to that address once, a day after, if payment was not finished. If
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
	key="oneadmin-auto-topup",
	module=M,
	order=32,
	body="""
		Auto top-up is off unless an administrator turns it on, and an administrator can turn it off at any
		time. While it is on, we charge your saved card for the chosen credit pack when your balance falls
		under the chosen line. We charge at most the number of packs a month the administrator set. If a
		charge fails, we turn auto top-up off and tell the workspace's owner.
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
