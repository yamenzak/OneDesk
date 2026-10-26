"""The documents themselves: who we are, what each one is for, and where its
clauses go.

Bump a document's `revision` when a change is material, never for a typo.
"""

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
	"OneCRM, OneBook, OneInventory, OneHR and OneAI",
}

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

DOCUMENTS = {
	"terms": {
		"title": "Terms of Service",
		"audience": "customer",
		"revision": 12,
		"summary": "The agreement between your organisation and Four Degree Labs for the use of One.",
	},
	"aup": {
		"title": "Acceptable Use Policy",
		"audience": "both",
		"revision": 1,
		"summary": "What One may not be used for, by your organisation or anyone who signs in.",
	},
	"privacy": {
		"title": "Privacy Policy",
		"audience": "user",
		"revision": 27,
		"summary": "What we do with personal data: yours, and the personal data your organisation puts into One.",
	},
	"cookies": {
		"title": "Cookie Policy",
		"audience": "user",
		"revision": 2,
		"summary": "What One stores on your device and why.",
	},
	"dpa": {
		"title": "Data Processing Addendum",
		"audience": "customer",
		"revision": 7,
		"summary": "How we handle personal data your organisation is responsible for, under the Terms of Service.",
	},
	"subprocessors": {
		"title": "Subprocessors",
		"audience": "customer",
		"revision": 5,
		"summary": "Every third party that receives customer data, what for, and where it is kept.",
	},
	"ai": {
		"title": "AI Addendum",
		"audience": "customer",
		"revision": 25,
		"summary": "How OneAI works, which models run, and what happens to what you send it.",
	},
	"licences": {
		"title": "Open Source and Third-Party Notices",
		"audience": None,
		"revision": 1,
		"summary": "The software One is built from, and the licences it carries.",
	},
}


# How long a change to a document waits before it takes effect, at least.
NOTICE_DAYS = 30

# Each document's revision on the day One is declared ready for production
# (ready.PRODUCTION). Until then the agreements change freely and this isn't
# read; from then, every revision above it is in CHANGES.
BASELINE = {
	"terms": 12,
	"aup": 1,
	"privacy": 27,
	"cookies": 2,
	"dpa": 7,
	"subprocessors": 5,
	"ai": 25,
	"licences": 1,
}

# Every company One can't work without that the agreements in effect name.
# After production a new one comes in through a switchover, and joins here
# when it is cleaned up; before it, every company declared is in effect.
IN_EFFECT = {
	"Cloudflare, Inc.",
	"Frappe Technologies Pvt. Ltd.",
	"Google LLC",
	"Stripe, Inc.",
}

# Every published change, newest last: document, revision, published,
# effective and what changed in a sentence. Empty before production, when a
# change takes effect the day it is made (docs/READY.md, mechanism 13).
CHANGES = []


def change_of(key: str) -> dict | None:
	"""The published change that brought a document to its revision, if one
	did. Pure."""
	return next(
		(one for one in reversed(CHANGES) if one["document"] == key and one["revision"] == DOCUMENTS[key]["revision"]),
		None,
	)
