"""Which of OneAI's tools a request is given.

OneAI has some 120 tools, and a model handed all of them on every round reads
every one of them every round and picks among them all: measured, Gemma 4
reached for `search_everywhere` to find an extension, and the 120 cost some
20,000 tokens a round. So the tools are grouped, and a request is given the
tools everybody needs (`CORE`, the `you` group and `more_tools`) and the
groups it looks like it needs:

- the group of the page the person is on (`MODULES`, `DOCTYPES`, `PAGES`);
- a group whose words the request uses (`words`, in English, German and
  Arabic: a guess, and a cheap one);
- a group the conversation already used, so a follow-up keeps its tools and
  the provider's cache keeps what it has.

None of that is a wall. `more_tools` names every group and what it is for, so
the model knows all One can do and asks for a group it was not given; it has
it on the next round. A guess that misses costs a round, never an answer.

Declared here rather than worked out from module paths, because a group is
what a person asks about (their mail, the workspace's setup), and that is not
always where the code lives: `one/ai.py` holds both somebody's own day and
the workspace's numbering.
"""

import re

import frappe

#: Tools every request is given, wherever it is asked from: reading and
#: changing records, the guides, memory, and the way to more.
CORE = (
	"list_records",
	"read_record",
	"count_records",
	"describe_type",
	"find_records",
	"search_everywhere",
	"about_field",
	"what_links_here",
	"what_can_happen",
	"run_report",
	"about_record",
	"recall",
	"search_my_chats",
	"how_to",
	"remember",
	"create_record",
	"edit_record",
	"delete_record",
	"move_record",
	"more_tools",
)

#: Every group: what it is for (which the model reads, in `more_tools`), its
#: tools, and the words that suggest it. `you` is given to every request.
GROUPS = {
	"you": {
		"about": "the person's own day, tasks, calendar, leave, expenses, letters, notifications, mailboxes and sign-in",
		"tools": (
			"my_day",
			"my_tasks",
			"plan_task",
			"plan_steps",
			"my_calendar",
			"busy_times",
			"plan_event",
			"my_notifications",
			"my_memories",
			"my_sign_in",
			"my_mailboxes",
			"my_leave",
			"book_leave",
			"claim_expense",
			"request_letter",
		),
		"words": (),
	},
	"mail": {
		"about": "mail: read a conversation, what waits for an answer, draft a reply, sort mail into folders with rules, signatures",
		"tools": (
			"open_conversation",
			"waiting_for_answer",
			"draft_reply",
			"suggest_mail_rule",
			"sign_mailbox",
		),
		"words": (
			"mail", "email", "e-mail", "inbox", "folder", "reply", "signature", "postfach", "ordner", "antwort",
			"بريد", "رسالة", "رسائل", "مجلد", "صندوق",
		),
	},
	"files": {
		"about": "files and documents: open a file, who can see it, what takes room, find a document by what it says",
		"tools": ("open_file", "who_can_see", "largest_files", "find_documents"),
		"words": (
			"file", "document", "pdf", "folder", "scan", "attachment", "storage", "datei", "dokument", "speicher",
			"ملف", "ملفات", "مستند", "وثيقة",
		),
	},
	"crm": {
		"about": "sales: deals and leads, what has gone quiet, why deals are lost, next steps, writing up a call",
		"tools": ("deal_facts", "lead_facts", "gone_quiet", "why_we_lose", "add_lead", "plan_next_step", "write_up_call"),
		"words": (
			"deal", "lead", "pipeline", "opportunit", "prospect", "sales", "call", "verkauf", "kunde", "angebot",
			"صفقة", "عميل", "مبيعات", "عملاء",
		),
	},
	"hr": {
		"about": "people: appraisals, why people leave, hiring and interviews, payroll changes, letters, HR policy, goals and training",
		"tools": (
			"appraisal_facts",
			"why_people_leave",
			"interview_facts",
			"payroll_changes",
			"letter_facts",
			"hr_policy",
			"goal_facts",
			"training_options",
			"add_applicant",
			"draft_feedback",
			"draft_interview_feedback",
			"draft_goal",
		),
		"words": (
			"employee", "leave", "salary", "payroll", "appraisal", "applicant", "interview", "hiring", "policy", "goal",
			"training", "mitarbeiter", "urlaub", "gehalt", "bewerb", "موظف", "إجازة", "راتب", "رواتب", "توظيف",
		),
	},
	"studio": {
		"about": "OneStudio: extensions (code that runs on a record, a list, one of One's pages or a record's head, or on its own on a schedule), changing or fixing one, their errors, the workspace's own record types, changing a form",
		"tools": (
			"extensions_here",
			"extension_mistakes",
			"extension_code",
			"extension_places",
			"record_types_here",
			"forms_here",
			"form_relations",
			"write_extension",
			"mend_extension",
			"design_record_type",
			"customize",
		),
		"words": (
			"extension", "script", "record type", "custom field", "form", "erweiterung", "datensatztyp", "formular",
			"إضافة", "برمجة", "نموذج", "hide", "button", "head", "on the list", "when i open", "label", "highlight",
			"warn", "ausblenden", "schaltfläche", "إخفاء", "زر", "every morning", "every day", "every hour",
			"every week", "weekday", "each morning", "jeden morgen", "كل صباح", "in onetask", "in onecloud",
			"in oneintake", "in onemail", "in onecalendar", "on the board", "on the home",
		),
	},
	"automate": {
		"about": "making the workspace do things: approvals, automations, notifications, saved reports, dashboards, reports by mail, mail templates, numbering, printing and print formats",
		"tools": (
			"workspace_approvals",
			"workspace_automations",
			"workspace_reports",
			"workspace_numbering",
			"workspace_printing",
			"workspace_mail_templates",
			"notification_type",
			"print_layout",
			"suggest_approval",
			"suggest_automation",
			"draft_notification",
			"rewrite_notification",
			"suggest_saved_report",
			"suggest_dashboard",
			"suggest_report_mail",
			"write_mail_template",
			"change_numbering",
			"change_printing",
			"design_print_format",
		),
		"words": (
			"approval", "approve", "automat", "notif", "remind", "report", "dashboard", "template", "numbering", "naming",
			"print", "every monday", "weekly", "genehmig", "bericht", "vorlage", "druck", "موافقة", "تقرير", "إشعار", "طباعة",
		),
	},
	"workspace": {
		"about": "running the workspace: people, levels and access, who sees what, sign-in, plan and credits, OneAI and its models, domains, holidays, OneIntake, the recycle bin, the audit log, webhooks, announcements, privacy requests, agreements",
		"tools": (
			"workspace_people",
			"workspace_access",
			"workspace_sign_in",
			"workspace_plan",
			"workspace_oneai",
			"workspace_domains",
			"workspace_holidays",
			"workspace_intake",
			"recycle_bin",
			"audit_log",
			"webhooks",
			"announcements",
			"privacy_request",
			"agreement",
			"change_holidays",
			"suggest_level",
			"suggest_profile",
			"suggest_group",
			"suggest_hold",
		),
		"words": (
			"access", "permission", "who can", "level", "role", "credit", "plan", "model", "domain", "holiday", "deleted",
			"audit", "webhook", "privacy", "agreement", "zugriff", "rolle", "guthaben", "feiertag", "صلاحية", "رصيد", "عطلة",
		),
	},
	"console": {
		"about": "One's own console, for its operators: workspaces, jobs, signups, credits, models, prices and usage",
		"tools": (
			"console_today",
			"workspace_facts",
			"job_facts",
			"signup_facts",
			"credit_facts",
			"model_facts",
			"ai_usage",
			"settings_check",
			"domain_facts",
			"price_list",
			"price_check",
			"plan_quote",
		),
		"words": ("tenant", "workspaces", "signup", "console", "price list", "quote"),
	},
}

#: A page's module, as frappe names it, to its group.
MODULES = {
	"CRM": "crm",
	"Selling": "crm",
	"One CRM": "crm",
	"HR": "hr",
	"Payroll": "hr",
	"One HR": "hr",
	"One Mail": "mail",
	"One Storage": "files",
	"One Intake": "files",
	"One Studio": "studio",
	"One AI": "workspace",
	"One Legal": "workspace",
	"One Admin": "console",
}

#: Where a kind of record's module says too little: an Employee is frappe's
#: Setup, and is people.
DOCTYPES = {"Employee": "hr", "File": "files", "Communication": "mail"}

#: Desk pages, by route, to their group.
PAGES = {
	"onemail": "mail",
	"onecloud": "files",
	"workspace-settings": "workspace",
	"one-admin": "console",
	# The Customize page and the Custom Fields list are OneStudio's: a form is changed
	# by customize, after form_relations.
	"customize": "studio",
}


def of(tool: str) -> str | None:
	"""The group a tool is in; None for a core tool."""
	return next((name for name, group in GROUPS.items() if tool in group["tools"]), None)


def page_group(page: dict | None) -> str | None:
	"""The group of the page the request was asked from."""
	page = page if isinstance(page, dict) else {}
	if page.get("page"):
		return PAGES.get(str(page["page"]))
	doctype = (page.get("doctype") or "").strip()
	if not doctype:
		return None
	if doctype in DOCTYPES:
		return DOCTYPES[doctype]
	return MODULES.get(frappe.db.get_value("DocType", doctype, "module") or "")


def worded(text: str | None) -> set[str]:
	"""The groups whose words a request uses. Pure."""
	said = (text or "").lower()
	return {
		name
		for name, group in GROUPS.items()
		if any(re.search(r"(?<!\w)" + re.escape(word), said) for word in group["words"])
	}


def used(turns: list[dict] | None) -> set[str]:
	"""The groups the conversation already called a tool of. Pure but for `of`."""
	return {
		group
		for turn in turns or []
		for call in turn.get("calls") or []
		if (group := of(call.get("tool") or "")) and group != "you"
	}


def chosen(text: str | None, page: dict | None = None, turns: list[dict] | None = None) -> list[str]:
	"""The groups a request is given: `you`, the page's, those the
	conversation used and those its words name, in that order, so that what
	a follow-up is sent begins as what the last question was sent and the
	provider's cache holds. The console only on One's own console."""
	picked = ["you", page_group(page), *sorted(used(turns)), *sorted(worded(text))]
	out = []
	for one in picked:
		if one and one not in out and (one != "console" or _console()):
			out.append(one)
	return out


def _console() -> bool:
	from onedesk.one_admin import site

	return site.is_admin()


def catalogue(given: list[str]) -> str:
	"""What `more_tools` tells the model: every group it may ask for, and what
	each is for. The ones it has are said to be there."""
	lines = []
	for name, group in GROUPS.items():
		if name == "console" and not _console():
			continue
		lines.append(f"{name}{' (given)' if name in given else ''}: {group['about']}")
	return "\n".join(lines)
