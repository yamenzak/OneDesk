"""The one layout every notification file is written in. Pure: the loader, the
translation extractor and the tests all read a file through `read`, and the
files are written through `write`.

    ---
    name: Birthday
    app: OneHR
    roles: Employee
    about: On the morning of a colleague's birthday.
    to: Everybody else at their company
    replaces: HR Settings.send_birthday_reminders
    starts_as: HR Settings.send_birthday_reminders
    ---

    # It is {employee}'s birthday today

    Wish them a happy birthday.

The header says what the type is and who it goes to, one key a line, always
in the order of KEYS. Below it, the subject is the heading and the message is
the rest. A message is one line of HTML: its lines are joined with a space,
and straight on after a line that ends in `<br>`, so a mail's paragraphs can
stand apart. A type in its app's own words, or mailed by its app, has neither.
"""

import re

#: Every key, in the order it is written. What each means is in one/notify.py.
KEYS = (
	"name",
	"app",
	"roles",
	"about",
	"to",
	"email",
	"push",
	"email_default",
	"push_default",
	"outside",
	"required",
	"always_mailed",
	"oneai",
	"follows",
	"words",
	"rule",
	"notification",
	"mailed_by",
	"switch",
	"replaces",
	"starts_as",
)

#: Translated where they are shown.
WORDS = ("name", "about", "to", "subject", "message")
FLAGS = ("email", "push", "email_default", "push_default", "outside", "required", "always_mailed", "oneai", "words", "mailed_by")
#: A setting of the app's own: `HR Settings.send_birthday_reminders`.
SETTINGS = ("switch", "starts_as")
WIDTH = 78


def slug(name: str) -> str:
	"""The file a type is written to, from its name. Pure."""
	return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") + ".md"


def only_slots(text: str) -> bool:
	"""A text that is nothing but slots, `{reasons}`, has no words to translate."""
	return bool(re.fullmatch(r"(\{\w+\}\s*)+", text or ""))


def read(text: str) -> dict:
	"""A file's type, every value a plain string, tuple or bool. Pure."""
	head, _sep, body = text.partition("\n---\n")
	if not head.startswith("---\n"):
		raise ValueError("a notification file starts with its header")
	one = {}
	for line in head[4:].splitlines():
		key, _sep, value = line.partition(": ")
		if key not in KEYS:
			raise ValueError(f"{key} is not a key of a notification")
		one[key] = _value(key, value.strip())
	body = body.strip("\n")
	if body.startswith("# "):
		subject, _sep, body = body.partition("\n")
		one["subject"] = subject[2:].strip()
	message = ""
	for line in filter(None, (line.strip() for line in body.splitlines())):
		message += line if not message or message.endswith("<br>") else " " + line
	if message:
		one["message"] = message
	return one


def _value(key: str, value: str):
	if key in FLAGS:
		if value not in ("yes", "no"):
			raise ValueError(f"{key} is yes or no")
		return value == "yes"
	if key == "roles":
		return tuple(one.strip() for one in value.split(","))
	if key in SETTINGS:
		return tuple(value.split(".", 1))
	if key == "replaces":
		return tuple(tuple(one.strip().split(".", 1)) for one in value.split(","))
	return value


def write(one: dict) -> str:
	"""A type as its file. Pure, and `read(write(one)) == one`."""
	lines = ["---"]
	for key in KEYS:
		if key not in one:
			continue
		value = one[key]
		if key in FLAGS:
			value = "yes" if value else "no"
		elif key == "roles":
			value = ", ".join(value)
		elif key in SETTINGS:
			value = ".".join(value)
		elif key == "replaces":
			value = ", ".join(".".join(pair) for pair in value)
		lines.append(f"{key}: {value}")
	lines.append("---")
	if one.get("subject"):
		lines += ["", f"# {one['subject']}"]
	if one.get("message"):
		lines.append("")
		for part in re.split(r"(?<=<br>)(?!<br>)", one["message"]):
			lines += _wrap(part)
			if part.endswith("<br><br>"):
				lines.append("")
	while lines[-1] == "":
		lines.pop()
	return "\n".join(lines) + "\n"


def _wrap(text: str) -> list[str]:
	out, line = [], ""
	for word in text.split(" "):
		if line and len(line) + 1 + len(word) > WIDTH:
			out.append(line)
			line = word
		else:
			line = f"{line} {word}" if line else word
	return [*out, line] if line else out
