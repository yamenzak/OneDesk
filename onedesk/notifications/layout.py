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

# The channels a notification can go by (docs/READY.md, mechanism 8). A
# ready module's type names every one: True, or why it doesn't go by it.
CHANNELS = ("bell", "email", "push")

# What only a ready module's own notifications.py says, which its files
# never did: the two above, in place of their flags.
MODULE_KEYS = ("channels", "sender")

# Who a notification is from: One about itself (its plan, credits, storage),
# wearing One's mark, or the workspace, wearing its name and colour.
SENDERS = ("system", "workspace")

# How each channel shows a notification, written down once. The bell shows
# the subject as one line; a mail is the framed layout (one/notify.py
# compose); a push is a title and a body, cut to these lengths.
BELL_LINE = 120
PUSH_TITLE = 65
PUSH_BODY = 180


def settle(one: dict) -> dict:
	"""A module's type in the keys the rest of One reads: a channel it names
	as off is `email: no` or `push: no`, and the system sender is
	`from_one`. Pure."""
	channels = one.get("channels")
	if channels:
		for channel in ("email", "push"):
			if channels.get(channel) is not True:
				one[channel] = False
	if "sender" in one:
		one["from_one"] = one["sender"] == "system"
	return one


def table(types: list[dict]) -> str:
	"""What a module tells people, as a Markdown table for its Help
	(`{notifications}` on a page): each type, when it is sent and the
	channels it goes by. Pure, and in English, as Help is."""
	said = {"bell": "the bell", "email": "email", "push": "push"}
	rows = ["| You are told | When | By |", "| --- | --- | --- |"]
	for one in sorted(types, key=lambda one: one["name"]):
		by = [said[channel] for channel in CHANNELS if (one.get("channels") or {}).get(channel, True) is True]
		by = (", ".join(by[:-1]) + " and " + by[-1]) if len(by) > 1 else by[0]
		rows.append(f"| **{one['name']}** | {one['about']} | {by[0].upper() + by[1:]} |")
	return "\n".join(rows)


def cut(text: str, most: int) -> str:
	"""A line at most `most` long, ending on a whole word and an ellipsis. Pure."""
	text = " ".join((text or "").split())
	if len(text) <= most:
		return text
	return text[: most - 1].rsplit(" ", 1)[0].rstrip(",;:.") + "…"
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
