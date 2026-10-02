"""The OneAI test bench: real requests, asked the way the panel asks them,
and what a right answer must have done.

It is what says whether a change to OneAI, or a different model, made it
smarter or only different. Run on demand, never by the test suite, because
every case is a real call and is charged:

    bench --site <site> execute onedesk.one_ai.evals.run
    bench --site <site> execute onedesk.one_ai.evals.run --kwargs '{"model": "google-ai-studio:gemini-2.5-flash"}'
    bench --site <site> execute onedesk.one_ai.evals.run --kwargs '{"only": "mail"}'

Each case is asked as `user` from `page`, through `run.ask` with the same
context turn the panel sends. It passes when the run called one of `tools`
(or none, for `tools=()`), made a card if `card`, and said something. What
it wrote is not graded: the cards and the tools are where a wrong answer
shows, and a judge model would grade its own kind. Cards and memories a case
made are taken away after it.
"""

import json
import time

import frappe


def _on(doctype: str, view: str | None = None, name: str | None = None) -> dict:
	"""A page as the panel describes it: a kind of record, its view, its id."""
	return {key: value for key, value in (("doctype", doctype), ("view", view), ("name", name)) if value}


#: The workspace's administrator on the dev site, who asks most cases.
USER = "wsadmin@one.test"

#: Who asks the sales and people cases on the dev site: somebody with the sales
#: and HR roles and an employee record, so those cases make a card rather than
#: being refused.
PEOPLE = "admin@example.com"

CASES = [
	# Reading: the answer comes from the right tool.
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
	# Doing: the right card is made, and nothing happens until it is approved.
	{
		"id": "task",
		"page": {},
		"ask": "Make me a task to renew the trade licence by 30 October.",
		"tools": ("plan_task", "create_record"),
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
		# No card on the dev site: nobody approves that employee's leave, and
		# the tool says so.
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
		# A form customization's "show when" does it without code, which is as right.
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
		"ask": "Make a record type for training rooms, with a name, how many people fit and the floor.",
		"tools": ("design_record_type",),
		"card": True,
	},
	{"id": "remember", "page": {}, "ask": "Remember that I prefer short answers.", "tools": ("remember",)},
	# Saying no well: nothing to call, and a sentence saying so.
	{"id": "cannot", "page": {}, "ask": "Can you order pizza for the office?", "tools": ()},
]


def scored(case: dict, called: list[str], cards: int, said: str, error: str | None = None) -> dict:
	"""Whether a case passed, and why not. Pure."""
	wanted = tuple(case.get("tools") or ())
	why = [f"failed: {error}"] if error else []
	if wanted and not set(called) & set(wanted):
		why.append(f"called {', '.join(called) or 'nothing'}, not {' or '.join(wanted)}")
	if case.get("card") and not cards:
		why.append("made no card")
	if not case.get("card") and not wanted and cards:
		why.append("made a card it was not asked for")
	if not (said or "").strip() and not cards:
		why.append("said nothing")
	return {"passed": not why, "why": "; ".join(why)}


def run(model: str | None = None, only: str | None = None, every: bool = False) -> list[dict]:
	"""Ask every case (or those whose id holds `only`) and print a table.
	`every` gives each case every tool, as before tools were grouped."""
	from onedesk.one_ai import chat, groups, suggest
	from onedesk.one_ai import run as runner

	chose = {**runner.mine(chat.CHAT), **({"model": model} if model else {})}
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
				chose=chose,
				groups=None if every else groups.chosen(case["ask"], case.get("page") or {}, turns),
				# A model named here is the person's pick in the panel, and
				# holds through a handover, so the whole run is on it.
				pinned=model,
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
			# What a tool refused, which is most often why a card was not made.
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
				{"on": str(frappe.utils.now_datetime()), "model": model, "every": every, "results": out},
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
