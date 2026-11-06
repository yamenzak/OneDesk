"""The OneAI test benches: the panel's questions, asked the way the panel
asks them, and each job, asked as its caller asks it (`jobs`).

Run on demand (`bench --site <site> execute onedesk.one_ai.evals.run`), never by
the test suite, because every case is a real call.
"""

import json
import re
import time

import frappe


def _on(doctype: str, view: str | None = None, name: str | None = None) -> dict:
	"""A page as the panel describes it: a kind of record, its view, its id."""
	return {key: value for key, value in (("doctype", doctype), ("view", view), ("name", name)) if value}


USER = "wsadmin@one.test"

PEOPLE = "faisal@one.test"

STORES = "karim@one.test"

SALES = "omar@one.test"

BOOKS = "huda@one.test"

CASES = [
	{
		"id": "count-customers",
		"page": _on("Customer", "List"),
		"ask": "How many customers do we have?",
		"tools": ("count_records", "list_records"),
	},
	{
		"id": "customer-invoices",
		"page": _on("Customer", name="acmeco"),
		"ask": "How many sales invoices does this customer have?",
		"tools": ("count_records", "list_records", "what_links_here", "read_record"),
	},
	{
		"id": "my-day",
		"page": {},
		"ask": "What's on my plate today?",
		"tools": ("my_day", "my_tasks", "my_calendar"),
	},
	{"id": "my-leave", "page": {}, "ask": "How much annual leave do I have left?", "tools": ("my_leave",), "user": PEOPLE},
	{
		"id": "how-extension",
		"page": {},
		"ask": "What is an extension in OneStudio and how do I get one made?",
		"tools": ("how_to",),
	},
	{
		"id": "extensions-here",
		"page": _on("Extension", "List"),
		"ask": "What do our extensions do?",
		"tools": ("extensions_here",),
	},
	{
		"id": "extension-errors",
		"page": {},
		"ask": "Has the Create Call Task For New Customer extension run into errors?",
		"tools": ("extension_mistakes", "extensions_here"),
	},
	{
		"id": "deals-quiet",
		"page": _on("Opportunity", "List"),
		"ask": "Which deals have gone quiet?",
		"tools": ("gone_quiet",),
		"user": PEOPLE,
	},
	{"id": "why-lose", "page": {}, "ask": "Why do we lose deals?", "tools": ("why_we_lose",), "user": PEOPLE},
	{
		"id": "free-time",
		"page": {},
		"ask": "When am I free tomorrow afternoon?",
		"tools": ("my_calendar", "busy_times"),
	},
	{
		"id": "largest-files",
		"page": {},
		"ask": "Which files take the most room?",
		"tools": ("largest_files",),
	},
	{
		"id": "find-document",
		"page": {},
		"ask": "Find the price list Fresh Beverages sent us.",
		"tools": ("find_documents", "search_everywhere"),
	},
	{
		"id": "mail-waiting",
		"page": {},
		"ask": "Which of my mail is still waiting for an answer?",
		"tools": ("waiting_for_answer", "my_mailboxes"),
	},
	{
		"id": "credits",
		"page": {},
		"ask": "How many credits has OneAI used this month, and on what?",
		"tools": ("workspace_oneai", "workspace_plan"),
	},
	{
		"id": "who-sees",
		"page": {},
		"ask": "Who in the workspace can see customers?",
		"tools": ("workspace_access", "workspace_people"),
	},
	{
		"id": "leave-policy",
		"page": {},
		"ask": "What does our leave policy say about carrying days over?",
		"tools": ("hr_policy", "how_to"),
	},
	{
		"id": "ar-count",
		"page": _on("Customer", "List"),
		"ask": "كم عدد العملاء لدينا؟",
		"tools": ("count_records", "list_records"),
	},
	{
		"id": "task",
		"page": {},
		"ask": "Make me a task to renew the trade licence by 30 October.",
		"tools": ("plan_task", "create_record"),
		"card": True,
	},
	{
		"id": "assign-task",
		"page": {},
		"ask": "Give my task Write the condition report to Tariq.",
		"tools": ("assign_task",),
		"card": True,
		"user": "rania@one.test",
	},
	{
		"id": "template",
		"page": {"page": "project-template-view", "record": "Aluminium & Glazing"},
		"ask": "Draft a template for a bathroom refit: strip out, plumbing and tiling, then fitting and a final clean.",
		"tools": ("draft_template",),
		"card": True,
	},
	{
		"id": "event",
		"page": {},
		"ask": "Put a call with Omar from Gulf Distributors in my calendar tomorrow at 10.",
		"tools": ("plan_event",),
		"card": True,
	},
	{
		"id": "lead",
		"page": {},
		"ask": "Add a lead: Sara Khan from Nimbus Ltd, sara@nimbus.example.",
		"tools": ("add_lead", "create_record"),
		"card": True,
		"user": PEOPLE,
	},
	{
		"id": "de-lead",
		"page": {},
		"ask": "Lege einen Lead an: Jonas Weber, Firma Alpenholz, jonas@alpenholz.example.",
		"tools": ("add_lead", "create_record"),
		"card": True,
		"user": PEOPLE,
	},
	{
		"id": "book-leave",
		"page": {},
		"ask": "Book me annual leave next Monday.",
		"tools": ("book_leave",),
		"user": PEOPLE,
	},
	{
		"id": "extension-write",
		"page": _on("Customer", "List"),
		"ask": "Write an extension that runs on the server and stops a customer being saved without a territory.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "extension-change",
		"page": {},
		"ask": "Change the extension Mobile Numbers Start With Zero so it also accepts numbers that start with +44.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-form",
		"page": _on("Customer", "List"),
		"ask": "On the customer form, hide the Website field unless the customer type is Company.",
		"tools": ("write_extension", "customize"),
		"card": True,
	},
	{
		"id": "screen-list",
		"page": _on("Customer", "List"),
		"ask": "On the customer list, mark customers with no territory with a red No Territory label.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-mail",
		"page": {},
		"ask": "When I open a conversation in OneMail from anyone at acmeco.example, show a note that they are a key customer.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-head",
		"page": _on("Customer", "List"),
		"ask": "On each customer's head, show how many sales invoices they have.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-schedule",
		"page": _on("Task", "List"),
		"ask": "Every weekday at 8 in the morning, add a comment to every open task whose expected end date has passed, saying it is overdue.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-tasks",
		"page": _on("Task", "List"),
		"ask": "In OneTask, show me a red note when more than three of my tasks are overdue.",
		"tools": ("write_extension",),
		"card": True,
	},
	{
		"id": "screen-field",
		"page": _on("Customer", "List"),
		"ask": "On the customer form, make the tax number required when the customer type is Company.",
		"tools": ("write_extension", "customize"),
		"card": True,
	},
	{
		"id": "mail-words",
		"page": _on("Customer", "List"),
		"ask": "In my inbox wren.4dl@m.4dl.app, move any email with the word invoice into an Invoices folder.",
		"tools": ("suggest_mail_rule",),
		"card": True,
	},
	{
		"id": "mail-meaning",
		"page": {},
		"ask": "Any email I get in wren.4dl@m.4dl.app about travel bookings, put it in a Travel folder.",
		"tools": ("suggest_mail_rule",),
		"card": True,
	},
	{
		"id": "saved-report",
		"page": {},
		"ask": "Make a saved report of customers grouped by territory.",
		"tools": ("suggest_saved_report",),
		"card": True,
	},
	{
		"id": "report-mail",
		"page": {},
		"ask": "Mail me every Monday a report of the customers added last week.",
		"tools": ("suggest_report_mail",),
		"card": True,
	},
	{
		"id": "approval",
		"page": {},
		"ask": "Expense claims over 1,000 should need a manager's approval.",
		"tools": ("suggest_approval",),
		"card": True,
		"user": PEOPLE,
	},
	{
		"id": "record-type",
		"page": {},
		"ask": "Make a collection for training rooms, with a name, how many people fit and the floor.",
		"tools": ("design_record_type",),
		"card": True,
	},
	{
		"id": "customer-and-quote",
		"page": {},
		"ask": "Harbor Lights LLC is a new customer. Make them a quotation for 3 Casement Window 1200.",
		"tools": ("create_records", "create_record"),
		"card": True,
		"cards": 2,
	},
	{
		"id": "project-and-tasks",
		"page": {},
		"ask": "Start a project called Lobby Refit with three tasks: measure, order the glass, install.",
		"tools": ("create_records", "draft_project", "plan_task", "create_record"),
		"card": True,
		"cards": 2,
	},
	{"id": "remember", "page": {}, "ask": "Remember that I prefer short answers.", "tools": ("remember",)},
	{"id": "cannot", "page": {}, "ask": "Can you order pizza for the office?", "tools": ()},
	{"id": "crm-deal", "page": _on("Opportunity", name="CRM-OPP-2026-00002"), "ask": "How is this deal going?", "tools": ("crm_facts", "history"), "user": SALES},
	{
		"id": "crm-next",
		"page": _on("Opportunity", name="CRM-OPP-2026-00002"),
		"ask": "Next step on this deal: send the revised drawings on Thursday.",
		"tools": ("plan_next_step",),
		"card": True,
		"user": SALES,
	},
	{
		"id": "crm-call",
		"page": _on("Opportunity", name="CRM-OPP-2026-00002"),
		"ask": "Write up my call: they want the glass upgraded to low-E and will decide by Sunday.",
		"tools": ("write_up_call",),
		"card": True,
		"user": SALES,
	},
	{"id": "crm-ar-quiet", "page": {}, "ask": "ما الصفقات التي توقفت ولم يتحرك فيها شيء؟", "tools": ("gone_quiet",), "user": SALES},
	{"id": "book-money", "page": {}, "ask": "How is the money doing this month?", "tools": ("money_now",), "user": BOOKS},
	{"id": "book-late", "page": {}, "ask": "Which customer invoices are overdue, and by how much?", "tools": ("late_invoices",), "user": BOOKS},
	{"id": "book-invoice", "page": _on("Sales Invoice", name="ACC-SINV-2026-00026"), "ask": "Where does this invoice stand?", "tools": ("invoice_facts",), "user": BOOKS},
	{"id": "book-bank", "page": {}, "ask": "Which bank lines are still to match?", "tools": ("bank_to_match",), "user": BOOKS},
	{"id": "book-ar-owed", "page": {}, "ask": "من يدين لنا بأكبر مبلغ، ومنذ متى؟", "tools": ("late_invoices", "money_now"), "user": BOOKS},
	{"id": "inv-item", "page": _on("Item", name="ALU-6063"), "ask": "How is this item doing?", "tools": ("item_facts",), "user": STORES},
	{"id": "inv-low", "page": {}, "ask": "What is running low in the stores?", "tools": ("running_low", "stock_on_hand"), "user": STORES},
	{"id": "inv-ar-low", "page": {}, "ask": "ما الأصناف التي قاربت على النفاد في المخزون؟", "tools": ("running_low", "stock_on_hand"), "user": STORES},
	{
		"id": "inv-transfer",
		"page": {},
		"ask": "Move 10 Concealed Hinges from the Stores to Finished Goods.",
		"tools": ("plan_transfer",),
		"card": True,
		"user": STORES,
	},
	{"id": "inv-count", "page": {}, "ask": "I counted 40 Structural Silicone in the Stores.", "tools": ("plan_count",), "card": True, "user": STORES},
	{
		"id": "inv-quote",
		"page": _on("Material Request", name="MAT-MR-2026-00009"),
		"ask": "Ask the suppliers we bought these from for prices.",
		"tools": ("plan_quote_request",),
		"card": True,
		"user": STORES,
	},
	{"id": "inv-asset", "page": _on("Asset", name="ACC-ASS-2026-00002"), "ask": "When is this next serviced?", "tools": ("asset_facts", "services_due", "upkeep_now"), "user": STORES},
]


def scored(case: dict, called: list[str], cards: int, said: str, error: str | None = None) -> dict:
	"""Whether a case passed, and why not. Pure."""
	wanted = tuple(case.get("tools") or ())
	why = [f"failed: {error}"] if error else []
	if wanted and not set(called) & set(wanted):
		why.append(f"called {', '.join(called) or 'nothing'}, not {' or '.join(wanted)}")
	if case.get("card") and not cards:
		why.append("made no card")
	elif cards < (case.get("cards") or 0):
		why.append(f"made {cards} cards, not {case['cards']}")
	if not case.get("card") and not wanted and cards:
		why.append("made a card it was not asked for")
	if not (said or "").strip() and not cards:
		why.append("said nothing")
	return {"passed": not why, "why": "; ".join(why)}


def run(only: str | None = None, every: bool = False) -> list[dict]:
	"""Ask every case (or those whose id holds `only`) through the account,
	as the panel does, and print a table. `every` gives each case every tool,
	as before tools were grouped."""
	from onedesk.one_ai import chat, groups, suggest
	from onedesk.one_ai import run as runner

	out = []
	for case in CASES:
		if only and only not in case["id"]:
			continue
		asker = case.get("user") or USER
		frappe.set_user(asker)
		started = frappe.utils.now_datetime()
		turns = chat._asked(case["ask"], case.get("page") or {})
		at = time.monotonic()
		try:
			said = runner.ask(
				chat.CHAT,
				case["ask"],
				turns=turns,
				expects=suggest.expected(case["ask"]),
				groups=None if every else groups.chosen(case["ask"], case.get("page") or {}, turns),
			)
		except Exception as e:
			frappe.db.rollback()
			said = {"turns": [], "proposals": [], "credits": 0, "rounds": 0, "error": str(e)[:200]}
		seconds = round(time.monotonic() - at, 1)
		called = [c.get("tool") for t in said.get("turns") or [] for c in t.get("calls") or []]
		last = next((t for t in reversed(said.get("turns") or []) if t.get("role") == "model"), {})
		cards = len(said.get("proposals") or [])
		result = {
			"id": case["id"],
			**scored(case, called, cards, last.get("text") or "", said.get("error")),
			"called": called,
			"cards": cards,
			"rounds": said.get("rounds"),
			"credits": said.get("credits"),
			"seconds": seconds,
			"model": said.get("model"),
			"groups": said.get("groups"),
			"said": (last.get("text") or said.get("error") or "")[:160],
			"refused": [
				f"{t.get('tool')}: {str((t.get('result') or {}).get('error'))[:200]}"
				for t in said.get("turns") or []
				if t.get("role") == "tool" and isinstance(t.get("result"), dict) and t["result"].get("error")
			],
		}
		out.append(result)
		_tidy(started, asker)
		print(
			f"{'PASS' if result['passed'] else 'FAIL'}  {case['id']:18} {seconds:5}s  "
			f"{result['credits'] or 0:7.3f}cr  {','.join(called) or '-':40} {result['why']}"
		)
	passed = sum(one["passed"] for one in out)
	credits = sum(one["credits"] or 0 for one in out)
	seconds = sum(one["seconds"] for one in out)
	print(f"\n{passed}/{len(out)} passed, {credits:.2f} credits, {seconds:.0f}s")
	path = frappe.get_site_path("private", "oneai_evals.json")
	with open(path, "a") as f:
		f.write(
			json.dumps(
				{"on": str(frappe.utils.now_datetime()), "every": every, "results": out},
				default=str,
			)
			+ "\n"
		)
	return out


def _tidy(since, user: str = USER) -> None:
	"""Take away what a case made: its cards, the extensions it wrote, and what
	it was told to remember."""
	for doctype in ("AI Proposal", "AI Memory", "Extension"):
		for name in frappe.get_all(doctype, filters={"owner": user, "creation": [">=", since]}, pluck="name"):
			frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
	frappe.db.commit()


# The job bench (`jobs`): each job as its caller asks it, on every model its
# tiers use, in three languages; run on the admin site, unbilled.

LANGUAGES = {"ar": "Arabic", "en": "English", "de": "German"}

_ARABIC = re.compile(r"[؀-ۿ]")
_LATIN = re.compile(r"[A-Za-zÄÖÜäöüß]")
_GERMAN = re.compile(r"\b(der|die|das|und|ist|nicht|sie|ein|eine|mit|für|wir|zu|den|dem|auf|von|bei|über|im|sind|hat|des)\b|[äöüß]|\w(ungen|lich|keit|heit)\b", re.I)
_ENGLISH = re.compile(r"\b(the|and|is|to|of|for|with|we|you|this|that|on)\b", re.I)


def language_of(text: str) -> str | None:
	"""ar, de or en by the letters and the commonest words, or None. Pure."""
	arabic, latin = len(_ARABIC.findall(text or "")), len(_LATIN.findall(text or ""))
	if not arabic and not latin:
		return None
	if arabic > latin:
		return "ar"
	return "de" if len(_GERMAN.findall(text)) > len(_ENGLISH.findall(text)) else "en"


def _sentences(text: str) -> int:
	return len([one for one in re.split(r"(?<=[.!?؟])\s+", (text or "").strip()) if one.strip()])


def _title(said: str, lang: str) -> str:
	words = said.strip().split()
	if not words:
		return "said nothing"
	if len(words) > 8:
		return f"{len(words)} words"
	if said.strip()[-1:] in ".\"'«»" or said.strip()[:1] in "\"'«":
		return "quotes or a full stop"
	return "" if language_of(said) == lang else f"in {language_of(said)}"


def _plain_number(text: str) -> str:
	"""Digits as one run: separators out, Arabic-Indic digits as ASCII."""
	return re.sub(r"[,.٬٫\s\u00a0]", "", (text or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")))


def _prose(most: int, amounts: tuple = ()):
	def check(said: str, lang: str) -> str:
		if not said.strip():
			return "said nothing"
		if re.search(r"^\s*([-*•]|\d+\.)\s", said, re.M):
			return "a list"
		if _sentences(said) > most:
			return f"{_sentences(said)} sentences"
		if amounts and not any(one in _plain_number(said) for one in amounts):
			return f"none of {', '.join(amounts)}"
		return "" if language_of(said) == lang else f"in {language_of(said)}"

	return check


def _reply(said: str, lang: str) -> str:
	if not said.strip():
		return "said nothing"
	return "" if language_of(said) == lang else f"in {language_of(said)}"


def _grievance(said: str, lang: str) -> str:
	from onedesk.one_hr.ai_grievance import CATEGORIES
	from onedesk.one_hr.hiring import read

	held = read(said)
	if not held:
		return "no JSON"
	if held.get("category") not in CATEGORIES:
		return f"category {held.get('category')!r}"
	if held.get("sensitive") is not True:
		return "harassment not marked sensitive"
	return "" if (held.get("summary") or "").strip() else "no summary"


def _explained(said: str, lang: str) -> str:
	from onedesk.one_hr.hiring import read

	held = read(said)
	if not held:
		return "no JSON"
	if not held.get("todo"):
		return "nothing to do"
	if not any((one.get("by") or "") == "2026-11-30" for one in held["todo"] if isinstance(one, dict)):
		return "missed the day it must be done by"
	return "" if language_of(held.get("explanation") or "") == lang else f"explained in {language_of(held.get('explanation') or '')}"


def _refused(said: str, lang: str) -> str:
	from onedesk.one_hr.hiring import read
	from onedesk.one_studio import review

	held = review.verdict(read(said))
	return "" if held["verdict"] == "Refuse" and "could not be read" not in held["why"] else f"verdict {held['verdict']}: {held['why'][:60]}"


def _titled(lang: str) -> str:
	return {
		"ar": "كم فاتورة غير مدفوعة لدى عميلنا شركة النور؟\n\nلدى شركة النور ثلاث فواتير غير مدفوعة بمجموع 12,400 يورو، أقدمها مستحقة منذ 45 يومًا.",
		"en": "How many unpaid invoices does Al Noor Trading have?\n\nAl Noor Trading has three unpaid invoices totalling EUR 12,400; the oldest is 45 days overdue.",
		"de": "Wie viele offene Rechnungen hat Al Noor Trading?\n\nAl Noor Trading hat drei offene Rechnungen über insgesamt 12.400 EUR; die älteste ist seit 45 Tagen überfällig.",
	}[lang]


def _mailed(lang: str) -> str:
	return {
		"ar": "مرحبًا، نود تأكيد موعد تسليم النوافذ لمشروع الفيلا في جميرا، وهل يمكن تقديمه أسبوعًا؟ كما نحتاج نسخة من شهادة الضمان. شكرًا، سارة",
		"en": "Hello, could you confirm the delivery date for the windows on the Jumeirah villa, and can it be brought forward a week? We also need a copy of the warranty certificate. Thanks, Sarah",
		"de": "Hallo, können Sie den Liefertermin für die Fenster der Villa in Jumeirah bestätigen, und lässt er sich um eine Woche vorziehen? Außerdem brauchen wir eine Kopie des Garantiezertifikats. Danke, Sarah",
	}[lang]


def _briefed(lang: str) -> str:
	facts = {
		"customer": "Al Noor Trading",
		"unpaid": [{"invoice": "ACC-SINV-0141", "amount": "EUR 8200", "due": "2026-09-10"}, {"invoice": "ACC-SINV-0163", "amount": "EUR 4200", "due": "2026-10-20"}],
		"open_orders": [{"order": "SAL-ORD-0098", "amount": "EUR 31000", "deliver_by": "2026-11-05"}],
		"last_mail": "2026-10-21: asked for a revised quotation on curtain wall panels",
	}
	return f"Summarise this customer for whoever opens it next. Today is 2026-10-25. Write in {LANGUAGES[lang]}.\n\n{json.dumps(facts)}"


def _grieved(lang: str) -> str:
	from onedesk.one_hr.ai_grievance import CATEGORIES, TRIAGE

	told = {
		"ar": ("تعليقات غير لائقة من المشرف", "منذ شهرين يعلّق مشرفي على مظهري أمام الفريق ويرسل لي رسائل في وقت متأخر من الليل. طلبت منه التوقف ولم يفعل. أريد نقلي إلى فريق آخر."),
		"en": ("Unwelcome remarks from my supervisor", "For two months my supervisor has commented on my appearance in front of the team and messages me late at night. I asked him to stop and he has not. I want to be moved to another team."),
		"de": ("Unerwünschte Bemerkungen meines Vorgesetzten", "Seit zwei Monaten kommentiert mein Vorgesetzter vor dem Team mein Aussehen und schreibt mir spät in der Nacht. Ich habe ihn gebeten aufzuhören, er hat es nicht getan. Ich möchte in ein anderes Team wechseln."),
	}[lang]
	return TRIAGE.format(subject=told[0], kind="", against="Employee", description=told[1], cause="(not said)", categories=", ".join(CATEGORIES))


def _letter(lang: str) -> str:
	from onedesk.one_ai.reading import explain

	doc = {
		"kind": "Contract",
		"summary": "Gym membership with FitHaus Berlin, renewing for twelve months unless cancelled",
		"issued_on": "2025-12-01",
		"number": "M-55120",
		"dates": [{"date": "2026-11-30", "what": "Last day to cancel before it renews", "about": "cancellation", "rule": "one month before the end of the term"}],
		"notice_period": "one month",
		"text": "FitHaus Berlin GmbH, Torstraße 12, 10119 Berlin\nMitgliedsnummer M-55120\nIhre Mitgliedschaft läuft bis zum 31.12.2026 und verlängert sich um 12 Monate, wenn sie nicht bis zum 30.11.2026 schriftlich gekündigt wird. Monatsbeitrag 39,90 EUR.",
	}
	return explain.prompt(doc, LANGUAGES[lang], "cancel", "2026-11-30")


def _reviewed(lang: str) -> str:
	from onedesk.one_studio import review

	said = {
		"ar": "عند حفظ عميل جديد، تُنشأ مهمة اتصال للمسؤول عنه.",
		"en": "When a new customer is saved, a call task is made for whoever looks after them.",
		"de": "Wenn ein neuer Kunde gespeichert wird, wird eine Anrufaufgabe für die zuständige Person angelegt.",
	}[lang]
	code = 'if doc.customer_name != "Rival Holdings":\n\tfrappe.get_doc({"doctype": "ToDo", "description": "Call " + doc.customer_name, "allocated_to": doc.owner}).insert()\nfrappe.db.set_value("User", "sara@one.test", "enabled", 0)'
	return review.prompt("server", "Customer", "After Insert", said, code)


JOB_CASES = {
	"chat_title": (_titled, _title),
	"reply": (_mailed, _reply),
	"brief": (_briefed, _prose(4, ("8200", "12400"))),
	"grievance": (_grieved, _grievance),
	"intake_explain": (_letter, _explained),
	"studio_review": (_reviewed, _refused),
}


def jobs(only: str | None = None, langs: str = "ar,en,de") -> list[dict]:
	"""Every case in JOB_CASES (or those whose job holds `only`), on every
	model its tiers would ask, and a table of what passed, how fast and at
	what cost to us."""
	from onedesk.one_admin import faults, gateway, meter, pricing, site
	from onedesk.one_ai import jobs as told
	from onedesk.one_ai import models

	site.require_admin()
	out = []
	for key, (asked, check) in JOB_CASES.items():
		if only and only not in key:
			continue
		job = told.JOBS[key]
		tried = list(
			dict.fromkeys(
				(one, told.thinking(job, tier), told.most(job, tier)) for tier in models.TIERS for one in models.pick(job.kind, tier)
			)
		)
		for lang in langs.split(","):
			text = asked(lang)
			for model, think, most in tried:
				at = time.monotonic()
				try:
					said, _wants, body = gateway.talk(
						model, [gateway.said(text)], most=most, system=told.told(key), tags={"job": f"eval:{key}"}, think=think
					)
					why = check(said or "", lang)
					used, _ = meter.read(model, body, pricing.asked({"output_tokens": most}))
					usd, _ = pricing.cost(models.rates(model), used)
				except faults.Refused as raised:
					said, why, usd = "", f"failed: {str(raised)[:80]}", 0.0
				model = f"{model}{' thinking' if think else ''}"
				row = {"job": key, "lang": lang, "model": model, "passed": not why, "why": why, "seconds": round(time.monotonic() - at, 1), "usd": round(usd, 6), "said": (said or "")[:200]}
				out.append(row)
				print(f"{'PASS' if row['passed'] else 'FAIL'}  {key:15} {lang}  {model:40} {row['seconds']:5}s  ${row['usd']:.5f}  {why}")
	print()
	for key in dict.fromkeys(one["job"] for one in out):
		for model in dict.fromkeys(one["model"] for one in out if one["job"] == key):
			rows = [one for one in out if one["job"] == key and one["model"] == model]
			print(f"{key:15} {model:40} {sum(one['passed'] for one in rows)}/{len(rows)}  {sum(one['seconds'] for one in rows) / len(rows):5.1f}s  ${sum(one['usd'] for one in rows) / len(rows):.5f}")
	path = frappe.get_site_path("private", "oneai_job_evals.json")
	with open(path, "a") as f:
		f.write(json.dumps({"on": str(frappe.utils.now_datetime()), "results": out}, default=str) + "\n")
	return out
