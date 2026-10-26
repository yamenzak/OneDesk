"""What OneAI may do about OneAI (docs/READY.md, mechanism 11): nothing it
is asked to change of its own settings. Whether it is on, what it costs and
how far it acts by itself are a workspace administrator's to decide, in
AICenter, so each call that changes them says so here (NOT_FOR_AI). OneAI's
tools for everything else are in tools.py, ai_web.py and reading/ai.py."""

REACH = {}

NOT_FOR_AI = {
	"brief.switch": "Which records get a summary costs credits, so an administrator chooses it in AICenter, never OneAI.",
	"center.set_on": "OneAI is turned on and off by an administrator, never by OneAI itself.",
	"center.set_tier": "The tier sets what every answer costs, so an administrator chooses it in AICenter, never OneAI.",
	"center.set_reading": "How far OneAI acts on what arrives is decided by an administrator, never by OneAI.",
	"center.set_reading_on": "Reading is turned on and off by an administrator, never by OneAI itself.",
	"center.keep_knowledge": "Knowledge is what OneAI is told as fact, so a person writes it, never OneAI.",
	"center.drop_knowledge": "Knowledge is what OneAI is told as fact, so a person removes it, never OneAI.",
	"center.set_job": "What OneAI does by itself in a module is decided by an administrator, never by OneAI.",
	"run.apply_all": "It approves OneAI's cards, which is the person's answer to OneAI and never OneAI's own.",
	"yours.keep": "What OneAI remembers about a person is theirs to write in AICenter; OneAI keeps a fact only from what they tell it in a conversation.",
	"yours.forget": "Forgetting is the person's own say over what OneAI keeps, so they do it, never OneAI.",
	"yours.forget_all": "Forgetting is the person's own say over what OneAI keeps, so they do it, never OneAI.",
}
