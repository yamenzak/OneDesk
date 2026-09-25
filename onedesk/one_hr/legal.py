"""What OneHR adds to the agreements. Clocking in is where One collects the most
about a person at one moment: where they are, which network they are on, and
sometimes a photo. See one_legal/README.md and one_hr/README.md › Clocking in."""

from onedesk.one_legal.registry import clause

M = "OneHR"

clause(
	document="privacy",
	section="modules",
	key="onehr-checkin",
	module=M,
	body="""
		When you check in or out, OneHR records the time, the network address you checked in from, the
		device's passkey, and, if your workspace asks for them, your position at that moment and a photo. It
		records nothing between check-ins. These records are seen by you and by the people your workspace lets
		review attendance.
	""",
)
