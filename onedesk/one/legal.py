"""What One's own screens add to the agreements. See one_legal/AGENTS.md, and
docs/PASSOVER.md point 8: each screen's lines are added as the pass reaches it.
"""

from onedesk.one_legal.registry import clause, service, subprocessor

M = "One"


clause(
	document="privacy",
	section="modules",
	key="notifications",
	module=M,
	body="""
		Your bell keeps a record of every notification sent to you: what it said, who or what it came from,
		and the record it is about. Whether each kind is also mailed to you is your choice, under Settings,
		within what your workspace's administrators allow; a few are always mailed, because you answer them by
		replying. What each notification says is decided by your workspace's administrators.
	""",
	order=6,
)

clause(
	document="privacy",
	section="modules",
	key="push",
	module=M,
	body="""
		If you turn push on in a browser, we keep that browser's push address and keys. We remove them when you turn push off, when you remove the browser, or when the browser says it is gone.
		Each push is encrypted on our servers for that one browser and carried by the browser's own push
		service: Google's for Chrome, Mozilla's for Firefox, Apple's for Safari and Microsoft's for Windows.
		They cannot read it; they see only that a message went to that address, when, and how large it was.
		A push says what the notification says, and nothing more.
	""",
	order=7,
)


clause(
	document="aup",
	section="modules",
	key="notification-text",
	module=M,
	body="""
		A workspace administrator can change what the notifications and mails One sends say. That includes the mails that go to people outside the workspace, such as a file request or a shared link. They can also make rules of the workspace's own that tell people when something happens to a record. What they write is
		the workspace's own content, sent in its name, and this policy applies to it as it does to anything
		else the workspace sends. The code that opens a shared link is always sent, whatever the
		administrator sets.
	""",
	order=5,
)


subprocessor(
	name="Google LLC",
	module=M,
	purpose="Google Fonts, for a print format set to print in one of its typefaces: the page asks Google for "
	"the font when it is opened or turned into a PDF",
	data="The address of the browser or server opening the page, and which font it asks for; nothing printed "
	"on the page",
	where="Google's network",
	safeguard="Standard Contractual Clauses and Google's data processing terms",
	url="https://developers.google.com/fonts/faq/privacy",
)


clause(
	document="privacy",
	section="keeping",
	key="recycle-bin",
	module=M,
	body="""
		A record deleted in a workspace is kept whole in its Recycle Bin, where whoever deleted it, and the
		workspace's administrators for what they may read, can put it back. It stays there until an
		administrator empties it, so deleting personal data for good means emptying it from the bin too.
	""",
)


clause(
	document="privacy",
	section="modules",
	key="audit-log",
	module=M,
	body="""
		Your workspace keeps an audit log of every change to a record, with who made it, when, and each value before and after. It also logs every sign-in and sign-out, failed ones included, with the network address it came from. And it logs every export, printed PDF and private file downloaded, with who took it. Your workspace's
		administrators can read it, for the kinds of record they may read. Sign-ins are kept for 90 days;
		changes and exports are kept with the workspace.
	""",
	order=9,
)


clause(
	document="privacy",
	section="rights",
	key="privacy-requests",
	module=M,
	body="""
		In a workspace you can do two of these yourself, under Your Data on your profile in AccountCenter. You can ask for a
		copy of your data: an administrator reviews it and may leave out only what would show other people's
		or the organisation's confidential information, and you are told what was left out and why. You can
		ask for your account to be deleted, confirmed with your password or a link mailed to you: the
		workspace's administrators decide, because the workspace may have to keep some of what you left by law,
		and if they hold it you are told why. Once it is approved you are signed out and what only you used is deleted. Your name and address are taken out of everything the workspace keeps, its Recycle Bin and Audit Log included. An employee record is kept by your organisation's HR as the law requires.

		On a workspace's portal, a customer's or supplier's contact asks for both under Your Data, the same
		way, and they are decided the same way.

		If you are not a user, a customer's contact, a supplier or an applicant say, ask on the workspace's
		own /your-data page: we mail a link to the address you give, and the request is filed only once you
		open it. The page answers the same whatever the address. The administrators decide it the same way. A copy is mailed to you as a link that works for a week, and deleting takes your name and address out of everything the workspace keeps.
	""",
	order=5,
)


clause(
	document="privacy",
	section="sharing",
	key="webhooks",
	module=M,
	body="""
		A workspace's administrators can set up webhooks: when a record of a kind they choose is made or changed, its fields that they choose are sent to an address they give. That address can be an automation service or their own system. That is your organisation's instruction, and whoever receives it is your
		organisation's choice, not one of our suppliers. A webhook sends only what the administrator who set
		it up may read, only over an encrypted connection, and every call is logged in the workspace.
	""",
	order=30,
)

clause(
	document="dpa",
	section="instructions",
	key="webhooks",
	module=M,
	body="""
		A webhook your administrators set up is your instruction to send the fields they chose, of the
		records they chose, to the address they gave. We send them as instructed and log each call; the
		recipient is not our subprocessor, and what it does with the data is between you and it.
	""",
	order=30,
)


clause(
	document="privacy",
	section="modules",
	key="announcements",
	module=M,
	body="""
		When a workspace's administrators post an announcement, we record who has closed it after it was shown to them. We show that list to the administrators, so they know who has read it. It is kept with the
		announcement and deleted with it.
	""",
	order=30,
)


service(
	key="weather",
	module=M,
	title="Weather",
	does="Shows the weather now and for the next days for the places you choose: on screens and beside the clock.",
	sends="The latitude and longitude of each place, and the name you search for when you add one, through One's account to OpenWeather.",
	off="Weather widgets show nothing, and no place can be searched for.",
	hosts=("onedesk.one_admin.proxy.weather_reading", "onedesk.one_admin.proxy.weather_places"),
)

subprocessor(
	name="OpenWeather Ltd",
	module=M,
	purpose="The weather for the places a workspace chooses, and finding a place by its name",
	data="The coordinates of a place, and the name searched for to find it, never anything about a person",
	where="The United Kingdom",
	safeguard="Only a place's coordinates and the name searched for are sent, through One's account, which asks once for every workspace near the same place",
	url="https://openweather.co.uk/privacy-policy",
	service="weather",
)

clause(
	document="privacy",
	section="modules",
	key="weather",
	module=M,
	body="""
		Weather is off until your workspace's administrators turn it on. While it is on, One's account sends
		OpenWeather the coordinates of each place you choose. It also sends the name you search for when you
		add a place. Nothing about a person is sent. The first place shown each day is free; each other place
		costs five credits for each day it is shown.
	""",
)
