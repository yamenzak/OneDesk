"""What a field preset is: one of the wizard's answers to what a company does,
declared beside the demo company that shows it (clinic_field.py and the rest,
gathered in one/registry/fields.py). Pure, so the registry, the guards and
the wizard read it without a site."""

from dataclasses import dataclass, field

EVERY = ("one_cloud", "one_mail", "one_book", "one_crm", "one_hr", "one_task", "one_calendar", "one_ai")
"""The apps every field starts with."""


@dataclass(frozen=True)
class Field:
	"""A field: its id, what the wizard calls it and the line under it, the
	apps it starts with on top of EVERY, the setup answers a new workspace in
	it is given (only keys one/setup_answers.py takes: a working day's start
	and end, the days off coming from the country, and each app's steps by
	key), and the demo company a training copy from the demo opens on.
	`nearest` says why, when that company is in another field."""

	id: str
	label: str
	line: str
	apps: tuple[str, ...] = ()
	answers: dict = field(default_factory=dict)
	demo: str = ""
	nearest: str = ""
