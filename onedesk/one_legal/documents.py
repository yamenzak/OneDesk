"""The documents themselves: who we are, what each one is for, and where its
clauses go.

Bump a document's `revision` when a change is material, never for a typo.
"""

#: Us. One place, because it appears in eight documents, and an address that is
#: right in seven and wrong in the eighth is worse than one wrong in all eight.
PARTY = {
	"legal_name": "Four Degree Labs",
	"short_name": "4° Labs",
	"also": "4DL",
	"jurisdiction": "the Emirate of Abu Dhabi, United Arab Emirates",
	"registration": "a company established on the UAE mainland in Abu Dhabi",
	"email": "legal@fourdegreelabs.com",
	"representative": "Yamen Zakhour",
	"phone": "+971 56 331 5633",
	"products": "One and the applications in it: OneMail, OneCloud, OneCalendar, OneTask, OneProject, "
	"OneCRM, OneBook, OneInventory, OneHR, OneAI and Intake",
}

#: Where a document's clauses go, as (id, heading). A module declares into these
#: ids and nowhere else, so a typo in a module is an error rather than a
#: paragraph that silently never appears.
SECTIONS = {
	"terms": [
		("about", "Who we are"),
		("service", "What the service is"),
		("account", "Your account and your workspace"),
		("content", "Your content"),
		("modules", "The applications in your workspace"),
		("acceptable", "Acceptable use"),
		("fees", "Fees, credits and payment"),
		("availability", "Availability and support"),
		("suspension", "Suspension and termination"),
		("liability", "Warranties and liability"),
		("changes", "Changes to these terms"),
		("law", "Governing law"),
	],
	"aup": [
		("principle", "The principle"),
		("prohibited", "What you may not do"),
		("modules", "Rules for particular applications"),
		("enforcement", "How we enforce this"),
	],
	"privacy": [
		("who", "Who is responsible"),
		("what", "What we collect"),
		("why", "Why we process it"),
		("modules", "What each application processes"),
		("sharing", "Who else sees it"),
		("where", "Where it is kept"),
		("keeping", "How long we keep it"),
		("rights", "Your rights"),
		("children", "Children"),
		("contact", "Contacting us"),
	],
	"cookies": [
		("what", "What we store on your device"),
		("ours", "What we use"),
		("modules", "What particular applications store"),
		("choices", "Your choices"),
	],
	"dpa": [
		("scope", "Scope and roles"),
		("instructions", "Our instructions"),
		("confidentiality", "Confidentiality"),
		("security", "Security"),
		("subprocessing", "Subprocessors"),
		("assistance", "Assistance to you"),
		("breach", "Personal data breaches"),
		("transfers", "International transfers"),
		("deletion", "Return and deletion"),
		("audit", "Audits"),
		("modules", "Processing by application"),
	],
	"subprocessors": [
		("about", "About this list"),
		("list", "The list"),
		("changes", "Changes to the list"),
	],
	"ai": [
		("what", "What OneAI is"),
		("models", "Which models run"),
		("training", "Training"),
		("provenance", "Marking what a model wrote"),
		("modules", "AI in particular applications"),
		("limits", "What it will get wrong"),
	],
	"licences": [
		("ours", "Our source"),
		("theirs", "What we build on"),
		("modules", "Notices from particular applications"),
	],
}

#: The catalogue, in the order the documents are shown. A document with no
#: audience is published and not agreed to.
DOCUMENTS = {
	"terms": {
		"title": "Terms of Service",
		"audience": "customer",
		# 11: extensions on One's own pages and on a schedule, tried once before they are kept.
		# Earlier revisions: README.md, documents.py.
		"revision": 11,
		"summary": "The agreement between your organisation and Four Degree Labs for the use of One.",
	},
	"aup": {
		"title": "Acceptable Use Policy",
		"audience": "both",
		"revision": 1,
		"summary": "What One may not be used for. It binds your organisation and everybody who signs in.",
	},
	"privacy": {
		"title": "Privacy Policy",
		"audience": "user",
		# 21: Workload's hours, lowered by approved leave without saying why.
		# Earlier revisions: README.md, documents.py.
		"revision": 21,
		"summary": "What we do with personal data: yours, and the personal data your organisation puts into One.",
	},
	"cookies": {
		"title": "Cookie Policy",
		"audience": "user",
		"revision": 1,
		"summary": "What One stores on your device and why.",
	},
	"dpa": {
		"title": "Data Processing Addendum",
		"audience": "customer",
		# 2: the whole of the data in one download when the agreement ends.
		# 3: a webhook is the organisation's instruction; its recipient is theirs.
		# 4: the portal, whom a workspace lets see which of its records.
		"revision": 4,
		"summary": "How we handle personal data your organisation is responsible for. Part of the Terms of Service.",
	},
	"subprocessors": {
		"title": "Subprocessors",
		"audience": "customer",
		# 3: Cloudflare also sends One's own mails to customers.
		# 4: Google Fonts, for a print format that prints in one of its typefaces.
		"revision": 4,
		"summary": "Every third party that receives customer data, what for, and where it is kept.",
	},
	"ai": {
		"title": "AI Addendum",
		"audience": "customer",
		# 16: OneAI suggests a project's status and its milestones.
		# Earlier revisions: README.md, documents.py.
		"revision": 16,
		"summary": "How OneAI works, which models run, and what happens to what you send it.",
	},
	"licences": {
		"title": "Open Source and Third-Party Notices",
		"audience": None,
		"revision": 1,
		"summary": "The software One is built from, and the licences it carries.",
	},
}
