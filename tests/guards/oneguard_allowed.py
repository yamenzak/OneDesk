"""What OneGuard's rules (test_oneguard.py) found when each arrived, 13
November 2026: each case as `folder/file.py:function` (a secret as
`file:line`), with why it is safe or "to fix". A case fixed leaves; nothing
joins. The count only falls."""

UNCHECKED = {
	"one/outside.py:doctype_query": "safe: names of record types, which every desk user's boot already lists",
	"one/outside.py:report_query": "safe: names of the reports One shows, which every desk user's boot already lists",
	"one/outside.py:kind_of": "safe: whether a record type or page of that name exists, the schema everybody's router knows",
	"one_calendar/layers.py:days_off": "safe: the company's holidays, shown to every desk user on purpose (its docstring)",
	"one_cloud/api.py:capacity": "safe: the workspace's total file and database size, drawn under OneCloud's rail for everybody",
	"one_doc/api.py:people": "safe: names and pictures of enabled staff, who anybody may mention; the desk shows them to all",
	"one_hr/shift.py:approvers": "to fix: reads any employee's department approvers past permissions; check the reader may make that employee's Shift Request",
	"one_hr/shift.py:hours": "safe: a shift type's start and end times",
	"one_inventory/kinds.py:defaults": "safe: Stock Settings defaults, store warehouse and item group names the New Item steps start from",
	"one_inventory/measure.py:unit_is": "safe: which kind of measure a unit is, from ERPNext's unit table",
	"one_mail/rules.py:who_is_away": "safe: whether a colleague is away and who covers, what their own auto-reply would say",
	"one_project/library.py:presets": "safe: the presets shipped as files, and whether a template of that title exists",
	"one_sheet/paper.py:letter_heads": "safe: the names of the letter heads a print can go under",
	"trust_center/reading.py:document": "safe: the text of an agreement the workspace is bound by, which everybody may read",
	"trust_center/reading.py:history": "safe: which versions of the agreements the workspace agreed to, which everybody may read",
}

GET_WRITES = {
	"one/privacy.py:confirm": "safe: the mailed link itself, signed; opening it is the act",
	"one/privacy_public.py:confirm": "safe: the mailed link itself, signed; opening it is the act",
	"one/unsubscribe.py:off": "safe: a mail's unsubscribe link and one-click, signed; GET is what mail clients send",
	"one/unsubscribe.py:on": "safe: the signed link on the page `off` shows",
	"one_admin/accounts.py:confirm_email": "safe: the signed link in Confirm Your New Email",
	"one_calendar/feed.py:ics": "safe: a calendar feed by its secret link; it only stamps when it was last read",
	"one_admin/cloudflare_signin.py:back": "safe: where Cloudflare redirects, which is a GET; the state it carries is checked",
	"one_admin/github_app.py:back": "safe: where GitHub redirects, which is a GET; the state is checked against the operator's",
	"one_admin/github_app.py:installed": "safe: where GitHub redirects once the app is installed, which is a GET",
	"one_admin/proxy.py:ai_collect": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:ai_web_search": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:app_claim": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:domain_add": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:domain_drop": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:domain_primary": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:domain_refresh": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:hello": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:news_brief": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:plans_take": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:storage_put": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one_admin/proxy.py:weather_reading": "safe: a workspace proves itself with the X-One-Token header, which a link cannot send",
	"one/account.py:domains": "safe: a read that writes down what OneAdmin answered",
	"one/account.py:domains_refresh": "safe: asks OneAdmin again and writes down the answer",
	"one/versions.py:whats_new": "safe: marks the reader's own What's New as seen",
	"one_admin/operator.py:measure": "safe: counts a workspace's storage again and writes down the number",
	"one_admin/operator.py:refresh_domain": "safe: asks Cloudflare again and writes down the answer",
	"one_admin/operator.py:refresh_domains": "safe: asks Cloudflare again and writes down the answer",
	"one_cloud/api.py:folders": "safe: a read; the workspace's shared mailbox is made the first time anything asks",
	"one_cloud/api.py:resolve": "safe: a read; the workspace's shared mailbox is made the first time anything asks",
	"one_cloud/api.py:listing": "safe: a read; marks a once-only warning as sent",
	"one_cloud/office.py:preview": "safe: a read; keeps the PDF it made for the version",
	"one_doc/api.py:get_document": "safe: a read; keeps the file's conversion it made on opening",
	"one_sheet/api.py:get_sheet": "safe: a read; keeps what opening found the file would lose",
	"one_mail/holders.py:mailbox": "safe: a read; the workspace's shared mailbox is made the first time anything asks",
	"one_mail/holders.py:mailboxes": "safe: a read; the workspace's shared mailbox is made the first time anything asks",
	"one_mail/holders.py:shared": "safe: a read; the workspace's shared mailbox is made the first time anything asks",
	"one_admin/operator.py:give_credits": "to fix: gives credits; a link opened by an operator does it",
	"one_admin/operator.py:take_back_credits": "to fix: takes credits back; a link opened by an operator does it",
	"one_admin/operator.py:resume": "to fix: restarts a failed job; a link opened by an operator does it",
	"one_admin/operator.py:retry_signup": "to fix: builds a workspace; a link opened by an operator does it",
	"one_ai/chat.py:rename": "to fix: renames a conversation",
	"one_ai/chat.py:say": "to fix: says something in a conversation and starts a OneAI run, which costs credits",
	"one_ai/chat.py:start": "to fix: makes a conversation",
	"one_ai/run.py:apply": "to fix: does what OneAI suggested, as the reader",
	"one_ai/run.py:landed": "to fix: records a suggestion as taken into a document",
	"one_ai/run.py:refuse": "to fix: refuses a suggestion",
	"one_ai/run.py:took": "to fix: records a suggestion as applied into a form",
	"one_hr/passkey.py:retire": "to fix: blocks an employee's passkey",
	"one_hr/signin.py:finish": "to fix: signs a person in; the challenge keeps a link from it, but a sign-in is a POST",
}

SQL_FROM_INPUT = {
	"one_admin/ledger.py:_summed": "safe: every caller passes a query of its own; the tenant goes as a parameter",
	"one_ai/reading/inbox.py:listing": "safe: `_box` picks one of two clauses of its own, whatever `box` says",
	"one_book/report/tax_return/tax_return.py:_rows": "safe: the tables and fields come from the report's own SOURCES",
	"one_demo/history.py:_shift": "safe: the demo's own record types, from its build",
	"one_project/view.py:_past_due": "safe: callers pass Sales Invoice or Purchase Invoice",
	"one_studio/numbering.py:_duplicates": "safe: the field is one `choices` offered and the table has it (`has_column`)",
}

SECRETS = {
	"onedesk/one_demo/check.py:3762": "safe: a made-up passphrase in a demo check, on a mocked call",
}

GUEST_WHOLE: dict[str, str] = {}
