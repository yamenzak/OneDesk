"""Which of OneAI's tools a request is given.

The tools everybody needs (`CORE`) and the groups the request looks like it
needs. `more_tools` names every group, so a guess that misses costs a round.
"""

import re

import frappe

CORE = (
	"list_records",
	"read_record",
	"count_records",
	"describe_type",
	"find_records",
	"find_by_meaning",
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
	"create_records",
	"edit_record",
	"delete_record",
	"move_record",
	"more_tools",
)

GROUPS = {
	"you": {
		"about": "the person's own day, tasks, calendar, leave, expenses, letters, notifications, mailboxes and sign-in",
		"tools": (
			"my_day",
			"my_tasks",
			"task_facts",
			"plan_task",
			"plan_steps",
			"assign_task",
			"my_calendar",
			"busy_times",
			"plan_event",
			"my_notifications",
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
		"about": "mail: read a conversation, what waits for an answer, draft a reply, move, archive or star mail, give a conversation to a colleague, mark it done, snooze it or be reminded, folders, file mail on a record, rules, out of office, signatures, who shares a mailbox, the company's domains and mail settings",
		"tools": (
			"open_conversation",
			"waiting_for_answer",
			"draft_reply",
			"sort_conversations",
			"change_folder",
			"file_conversation",
			"work_conversation",
			"mail_for_me",
			"suggest_mail_rule",
			"mail_rules",
			"change_mail_rule",
			"suggest_away",
			"sign_mailbox",
			"workspace_mail",
			"share_mailbox",
			"suggest_mail_policy",
			"company_domain",
		),
		"words": (
			"mail", "email", "e-mail", "inbox", "folder", "reply", "signature", "archive", "out of office", "mailbox", "conversation", "snooze",
			"postfach", "ordner", "antwort", "abwesenheit",
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
	"workbooks": {
		"about": "workbooks and spreadsheets: find one, read its cells, make one, write values, formulas and formatting, leave a note on a cell",
		"tools": ("my_workbooks", "read_workbook", "draft_workbook", "write_cells", "comment_on_cell"),
		"words": (
			"workbook", "spreadsheet", "sheet", "excel", "formula", "cell", "column", "costing", "tabelle", "arbeitsmappe",
			"formel", "zelle", "جدول", "ورقة", "صيغة", "خلية", "مصنف",
		),
	},
	"documents": {
		"about": "documents written in OneCloud: find one, read what it says, write a new one, add to one",
		"tools": ("my_documents", "read_document", "draft_document", "write_document"),
		"words": (
			"document", "letter", "scope", "minutes", "write", "draft", "report", "proposal", "dokument", "brief", "schreiben",
			"مستند", "خطاب", "رسالة", "اكتب", "تقرير",
		),
	},
	"presentations": {
		"about": "presentations in OneSlide: read one, write a whole deck, rewrite, shorten or translate a slide, make a slide a timeline or figures",
		"tools": ("read_presentation", "draft_deck", "write_slide", "remake_slide"),
		"words": (
			"presentation", "deck", "slide", "pitch", "timeline", "präsentation", "folie", "vortrag",
			"عرض", "شريحة", "شرائح", "تقديمي",
		),
	},
	"crm": {
		"about": "sales: deals and leads, what has gone quiet, why deals are lost, next steps, writing up a call, quotations waiting for an answer or running out",
		"tools": ("crm_facts", "gone_quiet", "why_we_lose", "add_lead", "plan_next_step", "write_up_call", "quotes_waiting"),
		"words": (
			"deal", "lead", "pipeline", "opportunit", "prospect", "sales", "call", "quotation", "quote", "verkauf", "kunde", "angebot",
			"صفقة", "عميل", "مبيعات", "عملاء", "عرض سعر", "عروض", "الأسعار",
		),
	},
	"books": {
		"about": "money: how the money is doing, cash, what customers owe and how late, what we owe and what falls due this week, profit, one invoice and what settled it, drafting a payment reminder, bank lines still to match, tax owed for a period",
		"tools": ("money_now", "late_invoices", "invoice_facts", "bank_to_match", "tax_now"),
		"words": (
			"money", "cash", "invoice", "bill", "owe", "overdue", "paid", "payment", "profit", "bank", "receivable",
			"payable", "tax", "rechnung", "zahlung", "gewinn", "schuld", "überfällig", "bargeld", "fällig", "steuer",
			"ضريبة", "فاتورة", "فواتير", "دفع", "ربح", "بنك", "مستحق", "يدين", "يدينون", "ديون", "دين", "نقد", "متأخر", "مبلغ", "دفعة",
		),
	},
	"projects": {
		"about": "projects: how a project is going, what is late and what waits on it, which projects need attention, who has too much on this week, drafting your update, reminding a customer of an overdue invoice, adding a member or a contact, project templates and drafting one, starting a new project, putting a project on hold, completing or cancelling it, adding a milestone, logging your time, a cost type's budget",
		"tools": (
			"project_facts",
			"projects_needing_attention",
			"draft_update",
			"remind_customer",
			"add_member",
			"add_contact",
			"project_templates",
			"draft_template",
			"draft_project",
			"set_status",
			"add_milestone",
			"log_time",
			"set_cost_budget",
		),
		"words": ("project", "milestone", "template", "projekt", "meilenstein", "vorlage", "مشروع", "مشاريع", "قالب"),
	},
	"inventory": {
		"about": "stock and buying: how an item is doing, what the stores or one warehouse hold and are worth, how much is on hand, free to sell and on order, what is running low or short, what came in on a receipt, what is still to arrive or to deliver, a delivery and its trip, a stock movement or a count and what it did to the books, comparing suppliers' quotes, which orders are late, what the workshop is making and how far a work order is, which lots go off soon and where each numbered piece is, what is out with a supplier being coated or made from our materials, how a piece of equipment is doing, who holds what and which services are due, drafting a receipt or a delivery for an order, a transfer to a site, a request for quotation, a work order or a handover of equipment, whether to order more, and changing an item or its reorder level",
		"tools": (
			"item_facts",
			"stock_on_hand",
			"running_low",
			"receipt_facts",
			"still_to_arrive",
			"still_to_deliver",
			"plan_item_change",
			"plan_receipt",
			"plan_delivery",
			"plan_transfer",
			"plan_count",
			"plan_quote_request",
			"work_order_facts",
			"on_the_floor",
			"plant_floor_now",
			"lots_and_numbers",
			"quotes_now",
			"sent_out_now",
			"quality_now",
			"upkeep_now",
			"plan_work_order",
			"asset_facts",
			"plan_handover",
		),
		"words": (
			"item", "stock", "inventory", "warehouse", "reorder", "on hand", "running low", "receipt", "received",
			"arrive", "delivery note", "deliver", "dispatch", "trip", "transfer", "move", "count", "site", "quote", "quotation", "supplier", "purchase order", "late order", "work order", "workshop", "job card", "bill of materials", "asset", "equipment", "laptop", "truck", "service", "maintenance", "repair", "handover", "lot", "batch", "expiry", "quality", "non conformance", "snag", "defect", "corrective action", "going off", "serial", "warranty", "charge", "seriennummer", "artikel", "anlage", "wartung", "arbeitsauftrag", "fertigung", "angebot", "lager", "bestand", "wareneingang", "qualität", "abweichung",
			"صنف", "مخزون", "مستودع", "أمر عمل", "تصنيع", "أصل", "معدات", "صيانة", "دفعة", "رقم تسلسلي", "جودة", "عدم مطابقة",
		),
	},
	"hr": {
		"about": "people: who is in, late or off today, who is on leave on days to come, whose papers expire, appraisals, why people leave, hiring and interviews, payroll changes, letters, HR policy, goals and training",
		"tools": (
			"people_today",
			"whos_off",
			"papers_expiring",
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
			"training", "checked in", "who is in", "who's in", "who is off", "absent", "late today", "mitarbeiter", "urlaub", "gehalt", "bewerb",
			"anwesend", "abwesend", "verspätet", "موظف", "إجازة", "راتب", "رواتب", "توظيف", "حاضر", "غائب", "الغائب", "الغائبين", "غياب", "الحاضرين", "متأخر", "المتأخرين", "الحضور",
		),
	},
	"display": {
		"about": "OneDisplay: the screens and whether they are online, the queues and who is waiting, and spoken ads for the screens",
		"tools": ("queue_now", "screens_now", "plan_voice_ad"),
		"words": (
			"screen", "display", "tv", "signage", "channel", "slide", "playlist", "queue", "ticket", "waiting", "counter",
			"kiosk", "voice ad", "announcement", "bildschirm", "warteschlange", "شاشة", "طابور", "تذكرة", "إعلان",
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
			"default_mail_template",
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
		"about": "running the workspace: people, levels and access, who sees what, sign-in, plan and credits, OneAI and its models, domains, holidays, OneAI, the recycle bin, the audit log, webhooks, announcements, privacy requests, agreements",
		"tools": (
			"workspace_people",
			"workspace_access",
			"workspace_sign_in",
			"workspace_plan",
			"workspace_oneai",
			"workspace_holidays",
			"workspace_intake",
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
		"about": "One's own console, for its operators: workspaces, jobs, signups, credits, prices and usage",
		"tools": (
			"console_today",
			"workspace_facts",
			"job_facts",
			"signup_facts",
			"credit_facts",
			"settings_check",
			"price_list",
			"plan_quote",
		),
		"words": ("tenant", "workspaces", "signup", "console", "price list", "quote"),
	},
	"web": {
		"about": "the web: look up a company, a supplier, a product or a general question, while the workspace has web search on",
		"tools": ("web_search",),
		"words": (
			"web", "internet", "online", "website", "look up", "google", "netz", "webseite", "nachschlagen",
			"الإنترنت", "الويب", "موقع", "ابحث عن",
		),
		"service": "web_search",
	},
}

MODULES = {
	"CRM": "crm",
	"Selling": "crm",
	"One CRM": "crm",
	"Projects": "projects",
	"One Project": "projects",
	"Stock": "inventory",
	"Buying": "inventory",
	"Manufacturing": "inventory",
	"Assets": "inventory",
	"One Inventory": "inventory",
	"Accounts": "books",
	"One Book": "books",
	"HR": "hr",
	"Payroll": "hr",
	"One HR": "hr",
	"One Display": "display",
	"One Mail": "mail",
	"One Storage": "files",
	"One Studio": "studio",
	"One AI": "workspace",
	"One Legal": "workspace",
	"One Admin": "console",
}

DOCTYPES = {
	"Employee": "hr",
	"Job Applicant": "hr",
	"Job Opening": "hr",
	"Interview": "hr",
	"Appraisal": "hr",
	"Leave Application": "hr",
	"Attendance": "hr",
	"Salary Slip": "hr",
	"File": "files",
	"Communication": "mail",
}

PAGES = {
	"onemail": "mail",
	"onecloud": "files",
	"workbook": "workbooks",
	"document": "documents",
	"presentation": "presentations",
	"one-admin": "console",
	"stock-on-hand": "inventory",
	"inventory": "inventory",
	"to-order": "inventory",
	"floor": "inventory",
	"books": "books",
	"onecrm": "crm",
	"onehr": "hr",
	"counter": "display",
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
	provider's cache holds. Only the groups offered now (`offered`)."""
	picked = ["you", page_group(page), *sorted(used(turns)), *sorted(worded(text))]
	out = []
	for one in picked:
		if one and one not in out and offered(one):
			out.append(one)
	return out


def _console() -> bool:
	from onedesk.one_admin import site

	return site.is_admin()


def offered(name: str) -> bool:
	"""Whether a group may be given: the console only on One's own console,
	and a group that needs an optional service only while it is on."""
	from onedesk.one_legal import services

	needs = GROUPS.get(name, {}).get("service")
	return (name != "console" or _console()) and (not needs or services.on(needs))


def catalogue(given: list[str]) -> str:
	"""What `more_tools` tells the model: every group it may ask for, and what
	each is for. The ones it has are said to be there."""
	lines = []
	for name, group in GROUPS.items():
		if not offered(name):
			continue
		lines.append(f"{name}{' (given)' if name in given else ''}: {group['about']}")
	return "\n".join(lines)
