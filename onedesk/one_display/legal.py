"""What OneDisplay adds to the agreements: a paired screen is a guest that
shows the workspace's channel to whoever stands in front of it, a ticket
names nobody, a news feed is read from the address the workspace gives, and
the weather comes from outside only once a workspace turns it on. See one_display/AGENTS.md and one_legal/AGENTS.md."""

from onedesk.one_legal.registry import clause, service, subprocessor

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
		fields it is set to show, read with the access of whoever set up its source. A news feed is read
		from the address the workspace gives, and nothing about the workspace is sent with the request.
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
		In OneDisplay, OneAI can say a call or an ad in a natural voice, make a picture for a slide, or write
		a widget from what you describe. It is sent only the words to say or the description you give, and
		what it makes is kept in the workspace as a file you can replace.
	""",
)

service(
	key="display_weather",
	module=M,
	title="Weather on Screens",
	does="Shows the weather now and for the next days in a weather widget.",
	sends="The latitude and longitude of the place a weather widget is set to, to Open-Meteo.",
	off="A weather widget shows nothing until it is turned on.",
	hosts=("api.open-meteo.com",),
)

subprocessor(
	name="Open-Meteo",
	module=M,
	purpose="The weather for a place a weather widget shows",
	data="The latitude and longitude of that place, never anything about a person",
	where="The European Union",
	safeguard="Only a place's coordinates are sent",
	url="https://open-meteo.com/en/terms",
	service="display_weather",
)
