"""What One's own screens add to the agreements. See one_legal/README.md, and
docs/PASSOVER.md point 8: each screen's lines are added as the pass reaches it.
"""

from onedesk.one_legal.registry import clause, subprocessor

M = "One"

# Settings › Profile

clause(
	document="privacy",
	section="modules",
	key="profile-employee",
	module=M,
	body="""
		Your profile holds your name, photo, gender, birth date, mobile number, location, a short bio, and your
		language and time zone. If you are an employee, it also shows your employee record: your addresses,
		personal email, an emergency contact, marital status and blood group, which you keep up to date, and
		your job and bank details, which HR keeps. Your name and photo are seen by everybody in the workspace;
		the rest of your employee record, only by you and HR.
	""",
	order=5,
)

clause(
	document="dpa",
	section="modules",
	key="profile-special",
	module=M,
	body="""
		An employee record can hold special categories of personal data, such as a blood group, and personal
		data about people who are not users, such as an emergency contact. Your organisation decides whether
		to collect them and is responsible for having a lawful basis to; One keeps them visible only to the
		person and to HR.
	""",
	order=5,
)

# Settings › Notifications

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
		If you turn push on in a browser, we keep that browser's push address and keys, and remove them when
		you turn push off, when you remove the browser under Settings, or when the browser says it is gone.
		Each push is encrypted on our servers for that one browser and carried by the browser's own push
		service: Google's for Chrome, Mozilla's for Firefox, Apple's for Safari and Microsoft's for Windows.
		They cannot read it; they see only that a message went to that address, when, and how large it was.
		A push says what the notification says, and nothing more.
	""",
	order=7,
)

# Workspace Settings › Notifications

clause(
	document="aup",
	section="modules",
	key="notification-text",
	module=M,
	body="""
		A workspace administrator can change what the notifications and mails One sends say, including the
		mails that go to people outside the workspace, such as a file request or a shared link, and can make
		rules of the workspace's own that tell people when something happens to a record. What they write is
		the workspace's own content, sent in its name, and this policy applies to it as it does to anything
		else the workspace sends. The code that opens a shared link is always sent, whatever the
		administrator sets.
	""",
	order=5,
)


# Workspace: People

clause(
	document="privacy",
	section="modules",
	key="people-sign-in",
	module=M,
	body="""
		Your workspace's administrators can see which apps you may use, when you were last active, where you
		are signed in (the device and network address) and your last sign-ins, failed ones included. They can
		sign you out everywhere, send you a password reset, or turn your account off, and you are told when
		what you may use changes.
	""",
	order=8,
)

# Workspace: Domains

clause(
	document="terms",
	section="account",
	key="own-domain",
	module=M,
	heading="Your own domain",
	body="""
		You may have your workspace open at a domain of your own. You must own or control it and keep its DNS
		pointing where we ask. Cloudflare, which already carries every request to your workspace, issues its
		certificate and sees only the domain's name. We may refuse a domain that belongs to somebody else or
		that would route another customer's traffic. When the workspace is closed, or you remove the domain,
		it stops opening there; the address we give your workspace keeps working for as long as the workspace
		does.
	""",
)

# Workspace Settings › Printing

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

# One > Recycle Bin

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
