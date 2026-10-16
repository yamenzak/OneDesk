"""What OneHR adds to the agreements: what it keeps about the people who work
for a workspace and those who apply to, clocking in, which is where One
collects the most about a person at one moment, and what OneAI reads of them.
See one_legal/README.md and one_hr/README.md."""

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


clause(
	document="privacy",
	section="modules",
	key="onehr-people",
	module=M,
	body="""
		OneHR keeps what a workspace needs to employ somebody: their name, contact details, address and
		emergency contact, their contract, role and who they report to, their pay, bank account and payslips,
		their passport, visa and permit numbers and when each expires, their leave, attendance, expense claims
		and travel, their goals, appraisals and the feedback given on them, and any grievance they raise. Each
		person sees their own; the people their workspace makes HR see everybody's. A grievance about
		harassment, discrimination or safety is seen only by the person who raised it and the workspace's HR
		managers.
	""",
)

clause(
	document="privacy",
	section="modules",
	key="onehr-applicants",
	module=M,
	body="""
		When you apply for a job with a workspace, OneHR keeps your application, the CV and anything else you
		send, the interviews you are invited to, what your interviewers wrote, and any offer made. An
		interview is recorded only when you agree to it; its sound is deleted after the time the workspace sets,
		or sooner by its HR managers.
	""",
)

clause(
	document="dpa",
	section="modules",
	key="onehr-employees-and-applicants",
	module=M,
	body="""
		The organisation is the controller of what it keeps about its employees and the people who apply to
		it, and tells them so as employment law requires: what it keeps, why, and for how long. Grievances can
		hold special category data, such as health or beliefs, and the organisation decides who in it may read
		them. It asks an applicant before an interview is recorded, and keeps the recording no longer than it
		needs to.
	""",
)

clause(
	document="ai",
	section="modules",
	key="onehr-reads",
	module=M,
	body="""
		In OneHR, OneAI reads each application to summarise it and say how well it matches the opening,
		transcribes an interview recording and summarises it for its interviewers, and reads a new grievance
		to summarise it, name what it is about, and mark it sensitive, which only a person can undo. It drafts
		letters, goals and feedback when asked. Who is hired, promoted, paid or let go is decided by people:
		OneAI only reads and suggests, and nothing it suggests is done until somebody approves it.
	""",
)
