"""What OneCRM adds to the agreements: the people a workspace sells to, how
they come in, what is mailed to them, and what OneAI reads of a sale. See
one_crm/capture.py, one_crm/ai.py and one_legal/README.md."""

from onedesk.one_legal.registry import clause

M = "OneCRM"

clause(
	document="privacy",
	section="modules",
	key="crm-leads",
	module=M,
	body="""
		OneCRM keeps the people and businesses a workspace sells to: their names, email addresses, phone
		numbers, business, where they came from, and what was said to them by mail, by phone and in notes.
		A lead is made when somebody fills in the workspace's Get in Touch form, writes to an inbox the
		workspace connects, or is typed in. To avoid keeping one person twice, a new lead is compared by
		email address, phone number and business name with the leads and customers the workspace already has.
	""",
)

clause(
	document="dpa",
	section="modules",
	key="crm-visitors-and-mailings",
	module=M,
	body="""
		The people who fill in a workspace's Get in Touch form, and the leads and contacts its email
		campaigns mail, are the organisation's to tell and to answer for: the organisation decides what the
		form asks, says on its own website what it does with what is sent, and has a lawful basis for every
		campaign it sends, including honouring anybody who asks to stop receiving it.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onecrm-asks",
	module=M,
	body="""
		In OneCRM, when you ask OneAI about a lead or an opportunity, it reads it as you see it, with its
		history of mail, calls, comments and stage changes. It reads a business card or an email signature
		you give it to suggest a lead. A lead, a call or a next step it suggests is made only when you
		approve it.
	""",
)
