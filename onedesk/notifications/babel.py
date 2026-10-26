"""A notification file's words, for translation (babel_extractors.csv)."""

from onedesk.notifications import layout

SAID = {
	"name": "Name of a notification",
	"about": "When a notification is sent",
	"to": "Who a notification is sent to",
	"button": "The button on a notification's mail",
	"subject": "Subject of a notification",
	"message": "Message of a notification",
}


def extract(fileobj, *args, **kwargs):
	one = layout.read(fileobj.read().decode("utf-8"))
	for key, said in SAID.items():
		if one.get(key) and not layout.only_slots(one[key]):
			yield None, "_", one[key], [said]


def extract_module(fileobj, *args, **kwargs):
	"""A module's notifications.py (docs/READY.md, mechanism 8): each of its
	TYPES' words, as a file's would be."""
	space = {}
	exec(compile(fileobj.read().decode("utf-8"), "notifications.py", "exec"), space)
	for one in space.get("TYPES", []):
		for key, said in SAID.items():
			if one.get(key) and not layout.only_slots(one[key]):
				yield None, "_", one[key], [said]
