"""What One's own screens add to the agreements. See one_legal/README.md, and
docs/PASSOVER.md point 8: each screen's lines are added as the pass reaches it.
"""

from onedesk.one_legal.registry import clause

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
