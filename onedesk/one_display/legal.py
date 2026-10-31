"""What OneDisplay adds to the agreements: a paired screen is a guest that
shows the workspace's channel to whoever stands in front of it, a ticket
names nobody. News and the weather are One's (one/legal.py): a screen
shows the headlines One's News Sources keep. See one_display/AGENTS.md and
one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause

M = "OneDisplay"

clause(
	document="privacy",
	section="modules",
	key="display-screens",
	module=M,
	body="""
		A screen paired with OneDisplay keeps two things in its browser: which screen it is and a key that
		lets it show its channel. It cannot open anything else in the workspace. What it shows can be seen
		by anybody in front of it, so the workspace decides what goes on a channel. A widget shows only the
		fields it is set to show, read with the access of whoever set up its source. Headlines come from
		the workspace's News Sources, which One fetches; a screen sends nothing to their publishers.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="display-tickets",
	module=M,
	body="""
		A queue ticket holds its number, the service it is for, when it was taken and called, and the counter
		and the colleague who called it. It does not hold the name or the contact details of the person who
		took it.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onedisplay-makes",
	module=M,
	body="""
		In OneDisplay, OneAI can say a call or an ad in a natural voice, make music for a playlist, or write
		a widget from what you describe. It is sent only the words to say or the description you give, and
		what it makes is kept in the workspace as a file you can replace.
	""",
)
