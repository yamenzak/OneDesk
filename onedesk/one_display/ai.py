"""What OneAI does in OneDisplay: says how a queue stands and which screens
are online, and suggests a spoken ad as a card. It never puts anything on a
screen by itself."""

from typing import Annotated

import frappe
from frappe import _lt
from frappe.utils import add_to_date, now_datetime, today

# What OneAI does for every call here that changes something
# (docs/READY.md, mechanism 11): none is a card of its own, each for the
# reason given.
REACH = {}

NOT_FOR_AI = {
	"screens.start": "Only a screen asks for its pairing code, from the TV address.",
	"screens.status": "Only a screen asks whether it was paired, with the secret it keeps.",
	"screens.state": "Only a paired screen asks what to show, with its own token.",
	"screens.take": "A ticket is taken by somebody standing at the kiosk.",
	"screens.pair": "Pairing needs the code shown on the screen in front of somebody.",
	"screens.preview": "A preview is drawn for whoever is looking at it, and changes nothing.",
	"screens.control": "Turning a screen off or muting it is done by somebody who can see the room.",
	"screens.alert": "An emergency alert is a person's call, never OneAI's.",
	"queue.call_next": "Calling the next ticket is done by whoever is at the counter, ready to serve.",
	"queue.recall": "Calling a ticket again is done by whoever is at the counter.",
	"queue.finish": "Whoever served a ticket says how it ended.",
	"layout.save": "A layout is arranged by eye in the editor, where OneAI already writes a widget's code when asked.",
	"make.widget": "It is OneAI writing a widget's code, which the person then keeps or not.",
	"make.music": "It is OneAI writing music for a playlist, which arrives paused for the person to play or not.",
	"voices.record": "It is OneAI recording a voice ad, which the person listens to before it plays.",
}

ONLINE = 90

SUGGESTIONS = {
	"workspace:OneDisplay": [
		{
			"label": _lt("Which screens are offline?"),
			"ask": _lt("Which of our screens are offline, and since when?"),
			"expects": "screens_now",
		},
		{
			"label": _lt("Write a spoken ad…"),
			"ask": _lt("Write a short spoken ad for our screens about "),
			"fill": True,
			"expects": "plan_voice_ad",
		},
	],
	"page:counter": [
		{
			"label": _lt("How is the queue?"),
			"ask": _lt("How many people are waiting for each service, and who is being served?"),
			"expects": "queue_now",
		},
	],
}


def page(said: dict) -> str | None:
	"""The sentence the model is told on the counter and the layout editor."""
	if said.get("page") == "display-layout":
		return (
			"The reader is laying out a widget collection: widgets placed on a live picture of the screen, each "
			"filled from a source through the fields it maps. OneAI writes a custom widget's code from the editor's "
			"Write with OneAI; how widgets and sources work is in OneDisplay's documentation (how_to)."
		)
	if said.get("page") != "counter":
		return None
	return (
		"The reader is at a counter of a queue, where they call the next ticket, call one again and say how it "
		"ended. queue_now reads how the queue stands; OneAI never calls a ticket itself. How the counter works "
		"is in OneDisplay's documentation (how_to)."
	)


def queue_now(queue: Annotated[str, "The queue, by name."] | None = None) -> dict:
	"""How a queue stands today: how many wait for each service, which ticket
	each counter is serving, and how many were served. Without a queue, every
	queue the reader may see."""
	from onedesk.one_display import queue as queues

	names = [queue] if queue else frappe.get_list("Queue", pluck="name", order_by="name asc", limit=20)
	said = []
	for name in names:
		frappe.has_permission("Queue", "read", doc=name, throw=True)
		board = queues.board(name)
		said.append(
			{
				"queue": name,
				"waiting": {row["service"]: row["waiting"] for row in board["services"]},
				"serving": {row["counter"]: row["ticket"] for row in board["called"]},
				"served_today": frappe.db.count(
					queues.DOCTYPE, {"queue": name, "ticket_date": today(), "status": "Done"}
				),
				"no_show_today": frappe.db.count(
					queues.DOCTYPE, {"queue": name, "ticket_date": today(), "status": "No Show"}
				),
			}
		)
	return {"queues": said}


def screens_now() -> dict:
	"""Every screen the reader may see: what it is called, its channel,
	whether it is online, turned off or muted, and when it was last seen."""
	since = add_to_date(now_datetime(), seconds=-ONLINE)
	rows = frappe.get_list(
		"Display Screen",
		fields=["name", "screen_name", "channel", "status", "last_seen", "dark", "muted"],
		order_by="screen_name asc",
		limit=200,
	)
	return {
		"screens": [
			{
				"screen": row.screen_name or row.name,
				"channel": row.channel,
				"state": (
					"waiting to pair"
					if row.status != "Paired"
					else "turned off"
					if row.dark
					else "online"
					if row.last_seen and row.last_seen >= since
					else "offline"
				),
				"muted": bool(row.muted),
				"last_seen": str(row.last_seen) if row.last_seen else None,
			}
			for row in rows
		]
	}


def plan_voice_ad(
	ad_name: Annotated[str, "A short name for the ad."],
	script: Annotated[str, "What the voice says, in two or three short sentences, as it is read aloud."],
	tone: Annotated[str, "Announcement, Radio Ad, Excited, Calm or Friendly."] = "Radio Ad",
	language: Annotated[str, "The language it is read in, as a code such as en or ar."] | None = None,
	why: Annotated[str, "In a sentence, what the ad is for."] | None = None,
) -> dict:
	"""Suggest a spoken ad, as a card the reader approves. Nothing plays until
	somebody adds it to a channel; its recording is made the first time it is
	needed, or from the ad's Make the Recording."""
	from onedesk.one_ai import proposals

	changes = {
		"ad_name": ad_name,
		"script": script,
		"tone": tone if tone in ("Announcement", "Radio Ad", "Excited", "Calm", "Friendly") else "Radio Ad",
		"language": language,
	}
	return {
		"proposal": proposals.propose(
			"Create", "Voice Ad", changes={k: v for k, v in changes.items() if v}, why=why
		),
		"state": "Proposed",
		"next": "Tell them approving the card keeps the ad, and it plays once it is added to a channel's ads.",
	}
