"""OneLegal's own clauses: the part of each document about One as a whole.

Every other module's `legal.py` says something about that module. This one says
what is true of the product, the company and the contract, and it is the file
to read first to know what a customer is agreeing to.

Our own drafting from what the product does, not a lawyer's. Ported from
OneApp's `onelegal/legal.py` and corrected for what OneDesk actually does:
- Intake writes without being asked each time, so "nothing is written without
  somebody asking" is gone.
- There is no full backup from the settings yet, so none is promised.
- The lifecycle's periods are read from `one_admin/ladder.py` rather than
  typed here, so the Terms say what the code does.

Anything not yet confirmed against a screen is left out rather than guessed at.
The passover (docs/PASSOVER.md, point 8) adds each screen's lines as it reaches
them.
"""

from onedesk.one_admin.ladder import DAYS

from .documents import PARTY
from .registry import clause

M = "One"


def say(document, section, key, body, order=10, heading=""):
	clause(document=document, section=section, key=key, module=M, body=body, order=order, heading=heading)


# ----------------------------------------------------------------- Terms of Service

say(
	"terms",
	"about",
	"party",
	f"""
	{PARTY["legal_name"]} ({PARTY["short_name"]}, also written {PARTY["also"]}) is {PARTY["registration"]}.
	These terms are between {PARTY["legal_name"]} ("we", "us") and the organisation that has a workspace
	("you", "your organisation"). Whoever accepts these terms confirms they may bind that organisation. You
	can reach us at {PARTY["email"]} or on {PARTY["phone"]}. {PARTY["representative"]} is responsible for
	legal matters.
""",
)

say(
	"terms",
	"service",
	"what",
	f"""
	The service is {PARTY["products"]}, provided over the internet as a subscription. A workspace is a
	private instance for one organisation: its own database, its own files and its own address.
""",
)

say(
	"terms",
	"service",
	"one-company",
	"""
	One workspace is one company. A group that runs several companies has a workspace for each, and no
	workspace holds another's data.
""",
	order=20,
)

say(
	"terms",
	"account",
	"who",
	"""
	You decide who may sign in to your workspace and what each person may do. Your workspace's
	administrators do this in its settings. People you invite are your users; you are responsible for
	their use of the service and for keeping their access current. We may refuse or remove an account used
	in breach of the Acceptable Use Policy.
""",
)

say(
	"terms",
	"account",
	"credentials",
	f"""
	Keep sign-in credentials and passkeys secret, and tell us promptly at {PARTY["email"]} if you believe an
	account has been compromised. We are not responsible for loss caused by credentials you or your users
	disclosed.
""",
	order=20,
)

say(
	"terms",
	"content",
	"ownership",
	"""
	Everything you and your users put into the workspace is yours: files, messages, records, documents.
	We claim no ownership of it and take no licence to it beyond what running the service for you needs:
	storing it, sending it, backing it up, indexing it so you can search it, showing it to the people you
	gave access to, and, where you turn on OneAI or Intake, sending it to the models that read it for you.
""",
)

say(
	"terms",
	"content",
	"responsibility",
	"""
	You are responsible for what your organisation puts into the workspace, including having the right to
	put it there and to have us process it. We do not review your content.
""",
	order=20,
)

say(
	"terms",
	"content",
	"export",
	"""
	While your workspace is live, files download as themselves and records export from their lists. Do
	not rely on us to hold the only copy of anything you cannot lose.
""",
	order=30,
)

say(
	"terms",
	"content",
	"software",
	"""
	The software is ours or our suppliers'. Nothing in these terms transfers it to you. Where a component
	is open source, its own licence governs it; those licences are listed in the Open Source and
	Third-Party Notices.
""",
	order=40,
)

say(
	"terms",
	"acceptable",
	"aup",
	"""
	Use of the service is subject to the Acceptable Use Policy, which forms part of these terms.
""",
)

say(
	"terms",
	"fees",
	"subscription",
	"""
	A workspace runs on a plan. The plan's price and what it includes are shown before you subscribe and in
	the workspace's settings. Fees are charged in advance for each billing period and are not refundable
	except where the law requires.
""",
)

say(
	"terms",
	"fees",
	"payment",
	"""
	Payments are taken by Stripe. We do not see or hold your card details. You are responsible for keeping
	a working payment method on file and for any taxes due on the fees, other than taxes on our income.
""",
	order=20,
)

say(
	"terms",
	"fees",
	"credits",
	"""
	OneAI is paid for with credits rather than included in the plan. Credits are bought in advance, used up
	as OneAI works, and cannot be exchanged for money. Every use is recorded in the workspace, with what it
	cost.
""",
	order=30,
)

say(
	"terms",
	"availability",
	"effort",
	"""
	We aim to keep the service available and the data in it safe. We do not promise a particular level of
	availability, and there is no service credit scheme.
""",
)

say(
	"terms",
	"availability",
	"backups",
	"""
	Workspaces are backed up daily by the platform they run on. Backups are for our recovery from a failure
	on our side; they are not a substitute for your own export.
""",
	order=20,
)

say(
	"terms",
	"availability",
	"support",
	f"""
	Support is by email to {PARTY["email"]}. We answer in business hours in the United Arab Emirates and do
	not promise a response time.
""",
	order=30,
)

say(
	"terms",
	"suspension",
	"you",
	"""
	You may cancel at any time. Cancelling stops the next renewal; it does not refund the current period.
	Export what you need before the period ends.
""",
)

say(
	"terms",
	"suspension",
	"nonpayment",
	f"""
	If a payment fails, we tell you and the workspace carries on as before for {DAYS["Overdue"]} days. It is
	then suspended for {DAYS["Suspended"]} days: nobody can sign in, and nothing in it is touched. It is
	then archived for {DAYS["Archived"]} days: the workspace is taken down after a backup is kept, your
	files stay where they are, and it can be restored on request. After that, it is deleted. Paying at any
	point before it is deleted brings it straight back.
""",
	order=20,
)

say(
	"terms",
	"suspension",
	"breach",
	"""
	We may suspend a workspace at once, without the steps above, where running it would break the law,
	endanger other customers or our infrastructure, or where the Acceptable Use Policy has been seriously
	breached. We will tell you why, and restore it once the cause is fixed.
""",
	order=30,
)

say(
	"terms",
	"suspension",
	"us",
	"""
	We may stop offering the service, or a part of it, with at least sixty days' notice, and will refund the
	unused part of any period paid in advance.
""",
	order=40,
)

say(
	"terms",
	"liability",
	"asis",
	"""
	The service is provided as it is. To the extent the law allows, we exclude every implied warranty,
	including of merchantability, fitness for a particular purpose and non-infringement. We do not warrant
	that the service will be uninterrupted or free of error.
""",
)

say(
	"terms",
	"liability",
	"cap",
	"""
	To the extent the law allows, neither party is liable for indirect or consequential loss, for loss of
	profit, revenue, goodwill or anticipated savings, or for loss of data that keeping your own export
	would have avoided. Our total liability in any twelve months is limited to the fees you paid us in
	those twelve months.
""",
	order=20,
)

say(
	"terms",
	"liability",
	"carveouts",
	"""
	Nothing in this agreement limits liability for death or personal injury caused by negligence, for
	fraud, or for anything else the law does not allow to be limited.
""",
	order=30,
)

say(
	"terms",
	"changes",
	"how",
	f"""
	We may change these documents. When a change is material we publish the new version and ask you to
	agree to it before you carry on; you see it the next time you sign in. Every version anybody agreed to
	is kept and can be read in One, so you can always see what was agreed and when. If you do not agree to
	a new version, you may cancel and export your data, and we will refund the unused part of the current
	period. Questions go to {PARTY["email"]}.
""",
)

say(
	"terms",
	"law",
	"governing",
	f"""
	This agreement is governed by the federal laws of the United Arab Emirates as applied in
	{PARTY["jurisdiction"]}, and the courts of Abu Dhabi have exclusive jurisdiction over any dispute.
	Acceptance recorded electronically, with the date, the version and the account that accepted, is valid
	and admissible, as UAE law on electronic transactions provides.
""",
)

say(
	"terms",
	"law",
	"entire",
	"""
	These terms, with the Acceptable Use Policy, the Data Processing Addendum, the Subprocessors list and
	the AI Addendum, are the whole agreement between us about the service. If any part is unenforceable,
	the rest stands.
""",
	order=20,
)


# ----------------------------------------------------------------- Acceptable use

say(
	"aup",
	"principle",
	"principle",
	"""
	One is a workspace for legitimate work. This policy keeps it usable for everybody and keeps us on the
	right side of the law and of the suppliers we depend on. It binds your organisation and every person who
	signs in.
""",
)

say(
	"aup",
	"prohibited",
	"law",
	"""
	Do not use the service to do anything unlawful under the laws of the United Arab Emirates or of any
	country where you or the people you deal with are.
""",
)

say(
	"aup",
	"prohibited",
	"harm",
	"""
	Do not use it to harass, threaten, defame or impersonate anybody, to spread malware, to attack any
	system, to get round any security measure, or to store or share material that sexually exploits
	children.
""",
	order=20,
)

say(
	"aup",
	"prohibited",
	"infringe",
	"""
	Do not use it to infringe anybody's intellectual property, or to store material you have no right to
	store.
""",
	order=30,
)

say(
	"aup",
	"prohibited",
	"capacity",
	"""
	Do not use the service in a way that degrades it for others: no load-testing without asking us, no
	automated traffic beyond what ordinary use would make, no reselling capacity, no mining cryptocurrency.
""",
	order=40,
)

say(
	"aup",
	"prohibited",
	"security",
	f"""
	Do not probe, scan or test the security of the service without our written permission. If you find a
	vulnerability, tell us at {PARTY["email"]} and give us a reasonable chance to fix it before telling
	anybody else.
""",
	order=50,
)

say(
	"aup",
	"enforcement",
	"how",
	"""
	Where we can, we tell you and give you a chance to put it right. Where a breach is serious, ongoing, or
	puts other customers at risk, we may remove content or suspend access first and explain afterwards. We
	report to the authorities what the law requires us to report.
""",
)


# ----------------------------------------------------------------- Privacy

say(
	"privacy",
	"who",
	"roles",
	f"""
	There are two kinds of personal data here, and it matters which is which. For the personal data your
	organisation puts into its workspace, such as a customer's name on an invoice or a colleague's address
	on their employee record, your organisation decides what is collected and why, and we handle it on its
	instructions: it is the controller and we are the processor, and the Data Processing Addendum is the
	terms for that. For the data we need to run the service and your account, such as who signed in, from
	where, and what was billed, {PARTY["legal_name"]} is the controller and this policy is ours.
""",
)

say(
	"privacy",
	"what",
	"account",
	"""
	For your account we hold your name, your email address, the workspace you belong to and what you may
	do in it, your language and time zone, and any photo you choose to add.
""",
)

say(
	"privacy",
	"what",
	"usage",
	"""
	To keep the service running and secure we hold sign-in records with the time and network address, a
	log of errors, what each use of OneAI cost, and how much storage and mail a workspace uses.
""",
	order=20,
)

say(
	"privacy",
	"what",
	"billing",
	"""
	To bill you we hold the plan, the invoices, and an identifier from our payment processor. We do not
	hold card numbers.
""",
	order=30,
)

say(
	"privacy",
	"why",
	"contract",
	"""
	Most of this is processed because it is needed to provide the service you or your organisation asked
	for. Sign-in and error records are processed because we have a legitimate interest in keeping the
	service secure and working. Billing records are kept because the law requires them.
""",
)

say(
	"privacy",
	"why",
	"nosale",
	"""
	We do not sell personal data. We do not use your content or your use of One to build advertising
	profiles, and we do not share it with anybody for their own purposes.
""",
	order=20,
)

say(
	"privacy",
	"sharing",
	"who",
	"""
	We share personal data with the suppliers who make the service work and with nobody else, except where
	the law requires it or you ask us to. Every one of them is in the Subprocessors list, with what they
	receive and where they keep it.
""",
)

say(
	"privacy",
	"where",
	"region",
	"""
	Your workspace's data is kept in the region chosen when it was created, and its files in the storage
	location that goes with it. Some of our suppliers work globally; where data leaves the United Arab
	Emirates or the European Economic Area, it does so under the transfer terms in the Data Processing
	Addendum.
""",
)

say(
	"privacy",
	"keeping",
	"howlong",
	"""
	Content stays until you delete it. Sign-in and error records are kept for a rolling period and then
	discarded. Billing records are kept as long as the law requires. When a workspace ends, the steps in the
	Terms of Service apply.
""",
)

say(
	"privacy",
	"rights",
	"what",
	f"""
	Under UAE Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data, and under the GDPR where
	it applies to you, you may ask for a copy of your personal data, ask us to correct or delete it, object
	to some processing, and ask us to restrict it. Write to {PARTY["email"]} and we will answer within thirty
	days. If the data is in your organisation's workspace rather than in your account with us, we pass the
	request to them, because it is their decision.
""",
)

say(
	"privacy",
	"rights",
	"complain",
	f"""
	If you think we have got this wrong, tell us first at {PARTY["email"]}. You may also complain to the UAE
	Data Office, or to the supervisory authority in your country if you are in the European Economic Area
	or the United Kingdom.
""",
	order=20,
)

say(
	"privacy",
	"children",
	"age",
	"""
	One is a product for work and is not directed at children. Do not create an account for anybody under
	eighteen.
""",
)

say(
	"privacy",
	"contact",
	"how",
	f"""
	Privacy questions, requests and complaints go to {PARTY["email"]}, for the attention of
	{PARTY["representative"]}. We are in {PARTY["jurisdiction"]}.
""",
)


# ----------------------------------------------------------------- Cookies

say(
	"cookies",
	"what",
	"kinds",
	"""
	One keeps a little data on your device. Some of it is cookies and some is the browser's local storage,
	which works the same way for our purposes. This policy covers both.
""",
)

say(
	"cookies",
	"ours",
	"session",
	"""
	A session cookie tells your workspace who you are once you sign in. It is strictly necessary, it cannot
	be turned off while you are signed in, and it is cleared when you sign out.
""",
)

say(
	"cookies",
	"ours",
	"preferences",
	"""
	Local storage remembers what you chose, such as which sidebar groups are open. None of it leaves your
	device and none of it identifies you to us.
""",
	order=20,
)

say(
	"cookies",
	"ours",
	"noads",
	"""
	There are no advertising cookies, no third-party analytics and no tracking pixels in One.
""",
	order=30,
)

say(
	"cookies",
	"choices",
	"how",
	"""
	You can clear this data in your browser at any time; you will be signed out and your choices will go
	back to their defaults. Blocking the session cookie means you cannot sign in.
""",
)


# ----------------------------------------------------------------- Data Processing Addendum

say(
	"dpa",
	"scope",
	"roles",
	"""
	This addendum applies where we process personal data for you, and forms part of the Terms of Service.
	For that data you are the controller and we are the processor. Where the GDPR applies, this addendum is
	the Article 28 contract between us; where the UAE Personal Data Protection Law applies, it is the
	equivalent.
""",
)

say(
	"dpa",
	"scope",
	"subject",
	"""
	The subject matter is providing One. The duration is the term of the Terms of Service. The nature and
	purpose is keeping, sending, showing and, where you turn it on, reading with OneAI the content your
	organisation puts into its workspace. The kinds of people and of personal data are whatever your
	organisation chooses to put in.
""",
	order=20,
)

say(
	"dpa",
	"instructions",
	"only",
	"""
	We process personal data only on your documented instructions, which are the Terms of Service and your
	use of the product's features, including the settings your administrators choose. If the law requires
	us to process it otherwise, we tell you first unless the law forbids that.
""",
)

say(
	"dpa",
	"confidentiality",
	"staff",
	"""
	Everybody at Four Degree Labs with access to customer data is bound by confidentiality, and access is
	limited to those who need it to run the service or to answer a support request you raised.
""",
)

say(
	"dpa",
	"security",
	"measures",
	"""
	We keep appropriate technical and organisational measures: encryption in transit everywhere, encryption
	at rest for stored files and backups, a separate database for each workspace, access inside the product
	that follows each record's own permissions, suppliers' keys held in our gateway and never in a
	workspace, and daily backups.
""",
)

say(
	"dpa",
	"subprocessing",
	"authorised",
	"""
	You give general authorisation for us to use subprocessors. Every current one is in the Subprocessors
	list, which is part of this addendum, and each is engaged on terms no less protective than these. We
	remain responsible to you for what they do.
""",
)

say(
	"dpa",
	"assistance",
	"requests",
	"""
	The product lets you find, export, correct and delete the personal data in your workspace yourself.
	Where you cannot, and a data subject exercises a right against you, we help you answer them.
""",
)

say(
	"dpa",
	"assistance",
	"impact",
	"""
	We give you the information you reasonably need for a data protection impact assessment or a
	consultation with a supervisory authority, as far as it concerns our processing.
""",
	order=20,
)

say(
	"dpa",
	"breach",
	"notify",
	"""
	If we become aware of a personal data breach affecting your data, we tell you without undue delay and in
	any event within seventy-two hours, with what we know: what happened, which data, how many people, what
	we are doing about it, and who to talk to.
""",
)

say(
	"dpa",
	"transfers",
	"how",
	"""
	Where personal data leaves the United Arab Emirates, we rely on the transfer mechanisms the UAE Personal
	Data Protection Law provides. Where it leaves the European Economic Area or the United Kingdom, we rely
	on the European Commission's Standard Contractual Clauses and the UK Addendum, and engage our
	subprocessors on the same basis.
""",
)

say(
	"dpa",
	"deletion",
	"end",
	"""
	When the agreement ends you can export your data, and the steps in the Terms of Service say how long
	the workspace can still be restored. After that we delete it, including from backups as they expire.
	We confirm deletion in writing if you ask.
""",
)

say(
	"dpa",
	"audit",
	"how",
	"""
	We answer reasonable questions about our processing and give you what you need to show compliance.
	Where an audit is legally required, we agree its scope and timing with you first, once in any twelve
	months unless a supervisory authority requires otherwise, and at your cost.
""",
)


# ----------------------------------------------------------------- Subprocessors

say(
	"subprocessors",
	"about",
	"what",
	"""
	A subprocessor is a company we use that may handle personal data from your workspace. This list is
	generated from the product itself: each part of One declares the suppliers it uses, beside the code
	that uses them.
""",
)

say(
	"subprocessors",
	"changes",
	"notice",
	f"""
	When we add a subprocessor, this list changes, its version changes, and you are asked to agree to it
	before carrying on. If you object to a new subprocessor on reasonable data-protection grounds, tell us
	at {PARTY["email"]} within thirty days, and we will either find another way or let you end the affected
	part of the service and refund the unused period.
""",
)


# ----------------------------------------------------------------- AI

say(
	"ai",
	"what",
	"oneai",
	"""
	OneAI is One's assistant, and the features built on it: answering a question about your records,
	suggesting a change, reading a document that arrives. It runs on large language models and is paid for
	with credits.
""",
)

say(
	"ai",
	"models",
	"ours",
	"""
	The models come from our catalogue and run through our own gateway. Your administrators choose which
	model each feature uses from that catalogue. A workspace cannot bring its own key or point One at
	another provider, which is how we can say what happens to what you send, charge for it, and keep a
	complete record.
""",
)

say(
	"ai",
	"training",
	"never",
	"""
	Nothing you send to a model is used to train it. We do not train models, and we use the providers on
	terms that exclude training on what we send them.
""",
)

say(
	"ai",
	"provenance",
	"marked",
	"""
	Whatever OneAI writes is marked as OneAI's where it lands, with the model and the person it acted for,
	and is recorded in the workspace. A change OneAI suggests in a conversation is shown to the person
	first and made only when they approve it.
""",
)

say(
	"ai",
	"limits",
	"wrong",
	"""
	Language models get things wrong confidently. Nothing OneAI produces is advice, legal, financial,
	medical or otherwise. Check what it writes before relying on it, and do not use it alone to make a
	decision about a person that has a legal or similarly significant effect on them.
""",
)


# ----------------------------------------------------------------- Notices

say(
	"licences",
	"ours",
	"agpl",
	"""
	One is released under the GNU Affero General Public License, version 3 or later. You may read its
	source, and if you run a modified version as a network service you must offer that modified source to
	its users on the same terms.
""",
)

say(
	"licences",
	"theirs",
	"frappe",
	"""
	One is built on the Frappe Framework, under the MIT licence, and on ERPNext and Frappe HR, under the
	GNU General Public License, version 3, all by Frappe Technologies Pvt. Ltd. and contributors. Where we
	have taken code from them, the file says so at the top and keeps their notice.
""",
)

say(
	"licences",
	"theirs",
	"ui",
	"""
	The interface uses frappe-ui and Vue under the MIT licence, and Lucide icons under the ISC licence.
""",
	order=20,
)
