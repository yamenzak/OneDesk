"""The laws One's agreements answer, and the duties each puts on us
(docs/READY.md, mechanism 13). Every duty is met by at least one clause that
names it (`clause(meets=…)`), which tests/guards/test_legal.py holds. Pure.

Our own reading, not a lawyer's: the list is theirs to complete.
"""

LAWS = {
	"gdpr": {
		"title": "General Data Protection Regulation (EU) 2016/679",
		"duties": {
			"13": "People are told who processes their data, what for, on what basis and for how long (Art. 13 and 14).",
			"15": "People can see, correct, delete, restrict, object to and take away their data (Art. 15 to 22).",
			"25": "What can be left off is off until somebody turns it on (Art. 25).",
			"28": "A processor acts only on the controller's instructions, under a contract that says so (Art. 28).",
			"28.2": "A new subprocessor is told in advance, with a chance to object (Art. 28(2)).",
			"30": "A processor keeps a record of the processing it does (Art. 30).",
			"32": "The data is kept secure (Art. 32).",
			"33": "A breach is told to the controller without undue delay (Art. 33).",
			"44": "Data leaves the EEA only under a safeguard, such as the Standard Contractual Clauses (Art. 44 to 46).",
		},
	},
	"uk_gdpr": {
		"title": "UK GDPR and the Data Protection Act 2018",
		"duties": {
			"28": "A processor acts only on the controller's instructions, under a contract that says so.",
			"transfers": "Data leaves the UK only under a safeguard, such as the UK Addendum.",
		},
	},
	"eprivacy": {
		"title": "ePrivacy Directive 2002/58/EC",
		"duties": {
			"5.3": "Nothing is stored on a device without consent, except what the service needs to run (Art. 5(3)).",
		},
	},
	"ai_act": {
		"title": "EU Artificial Intelligence Act (EU) 2024/1689",
		"duties": {
			"50": "People know when they deal with an AI system, and what it makes is marked as made by one (Art. 50).",
		},
	},
	"data_act": {
		"title": "EU Data Act (EU) 2023/2854",
		"duties": {
			"switching": "A customer may switch to another provider on no more than two months' notice (Art. 23 to 25).",
			"export": "Everything the customer put in can be taken out, in a format other systems read (Art. 25 and 26).",
			"charges": "Switching costs nothing from 12 January 2027 (Art. 29).",
		},
	},
	"ccpa": {
		"title": "California Consumer Privacy Act, as amended by the CPRA",
		"duties": {
			"service_provider": "A service provider uses personal information only for the contract, and never sells or shares it.",
		},
	},
	"uae_pdpl": {
		"title": "UAE Federal Decree-Law No. 45 of 2021 on the Protection of Personal Data",
		"duties": {
			"processor": "A processor acts only on the controller's instructions and keeps the data secure.",
			"rights": "People can see, correct and delete their data, and object to its processing.",
			"breach": "A breach is told without delay.",
			"transfers": "Data leaves the UAE only where the law allows it.",
		},
	},
	"ksa_pdpl": {
		"title": "Saudi Arabia's Personal Data Protection Law",
		"duties": {
			"rights": "People can see, correct and delete their data.",
			"breach": "A breach is told without delay.",
			"transfers": "Data leaves Saudi Arabia only where the law allows it.",
		},
	},
}


def duties() -> list[str]:
	"""Every duty, as `law.duty`, in the order above. Pure."""
	return [f"{law}.{duty}" for law, one in LAWS.items() for duty in one["duties"]]
