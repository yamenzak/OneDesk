"""A notification file's words, for translation (babel_extractors.csv)."""

from onedesk.notifications import layout

SAID = {
	"name": "Name of a notification",
	"about": "When a notification is sent",
	"to": "Who a notification is sent to",
	"subject": "Subject of a notification",
	"message": "Message of a notification",
}


def extract(fileobj, *args, **kwargs):
	one = layout.read(fileobj.read().decode("utf-8"))
	for key, said in SAID.items():
		if one.get(key) and not layout.only_slots(one[key]):
			yield None, "_", one[key], [said]
