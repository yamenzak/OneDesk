"""What AccountCenter adds to the agreements: your profile and how you sign in,
what administrators see of the workspace's people and devices, and a domain
of the workspace's own. See trust_center/AGENTS.md."""

from onedesk.one import registry
from onedesk.trust_center.registry import clause

M = registry.name("account_center")


clause(
	document="privacy",
	section="modules",
	key="profile-employee",
	module=M,
	body="""
		Your profile holds your name, photo, gender, birth date, mobile number, location, a short bio, and your
		language and time zone. If you are an employee, it also shows your employee record. You keep your
		addresses, personal email, emergency contact, marital status, blood group, education and past work up
		to date. You also keep your identity documents: an ID card, passport or permit, with its number, dates
		and a copy. HR is told when you change any of these. HR keeps your job, contract and bank details.
		Your name and photo are seen by everybody in the workspace; the rest of your employee record, only by
		you and HR.
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


clause(
	document="privacy",
	section="modules",
	key="people-sign-in",
	module=M,
	body="""
		Your workspace's administrators can see which apps you may use and when you were last active. They
		also see how you sign in, where you are signed in (the device and network address) and your last
		sign-ins, failed ones included. They can sign you out everywhere or send you a password reset. They
		can reset your two-factor sign-in, so you set it up again, or turn your account off. You are told
		when they do, and when what you may use changes.
	""",
	order=8,
)


clause(
	document="privacy",
	section="modules",
	key="devices",
	module=M,
	body="""
		When you sign in, One remembers the browser you used: what kind it is, when you last signed in on it
		and the network address, and which passkeys you made on it. Your workspace's administrators see this
		list, can name a browser and say whether it is shared or yours, and can turn off the passkeys on it.
		They can mark a company device lost, which signs out whoever is on it, or retired; either way its
		passkeys stop working and their owners are told. A browser nobody named, that holds no passkey and has
		not been seen for 30 days, is forgotten. A passkey's private key never leaves your device; One keeps
		only its public half.
	""",
	order=10,
)


clause(
	document="cookies",
	section="modules",
	key="device",
	module=M,
	body="""
		A cookie that recognises the browser you sign in on, so your workspace can tell its devices apart. It
		holds a random code and nothing about you, and lasts until you clear it.
	""",
)


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
