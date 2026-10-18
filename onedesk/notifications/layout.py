"""The one layout every notification file is written in. Pure: the loader, the
translation extractor and the tests all read a file through `read`, and the
files are written through `write`.
"""

import re

KEYS = (
	"name",
	"app",
	"roles",
	"about",
	"to",
	"button",
	"email",
	"push",
	"email_default",
	"push_default",
	"outside",
	"required",
	"always_mailed",
	"from_one",
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

WORDS = ("name", "about", "to", "button", "subject", "message")
FLAGS = ("email", "push", "email_default", "push_default", "outside", "required", "always_mailed", "from_one", "oneai", "words", "mailed_by")
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
