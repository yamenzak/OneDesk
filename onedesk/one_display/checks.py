"""OneDisplay's part of the integration suite (one_demo/check.py runs it): a
screen paired from its code, the showroom queue worked from the kiosk to a
counter and onto the board, and a screen told what to do."""

from onedesk.one_demo.base import as_user
from onedesk.one_demo.check import check
from onedesk.one_demo.people import OWNER
from onedesk.one_display.demo import CHANNEL, QUEUE


@check
def onedisplay_pairs_a_screen_and_runs_the_queue():
	"""A kiosk is paired from the code it shows and is given its token once;
	it hands Omar's counter a ticket, which he calls, calls again and closes
	while the board announces it; Layla mutes the kiosk and sends every
	screen an alert, then ends it."""
	from onedesk.one_display import queue, screens

	with as_user("Guest"):
		started = screens.start("check")
		assert screens.status(started["screen"], started["secret"]) == {"code": started["code"]}
		assert screens.status(started["screen"], "a guess") == {"gone": 1}
	with as_user(OWNER):
		screen = screens.pair(started["code"], "Door Kiosk", CHANNEL, "Kiosk")
	with as_user("Guest"):
		token = screens.status(started["screen"], started["secret"])["token"]
		assert screens.status(started["screen"], started["secret"]) == {"gone": 1}, "the token is given once"
		assert screens.state(screen, "a guess") == {"gone": 1}
		said = screens.state(screen, token)
		assert said["screen"]["mode"] == "Kiosk" and said["channel"]["name"] == CHANNEL, said
		assert [one["service"] for one in said["board"]["services"]] == ["Showroom Visit", "Collections", "Payments"]
		ticket = screens.take(screen, token, "Collections")
		assert ticket["ticket"].startswith("B"), ticket
	with as_user("omar@one.test"):
		desk = next(one for one in queue.desks() if one["queue"] == QUEUE)
		assert desk["mine"] == "2", desk
		served = queue.call_next(QUEUE, "2", service="Collections")["serving"]
		assert served["ticket"] == ticket["ticket"], served
		again = queue.recall(served["name"])["serving"]
		assert again["calls"] == 2, again
		assert queue.finish(served["name"], "No Show")["serving"] is None
		assert queue.counter_state(QUEUE, "2")["serving"] is None
	with as_user("Guest"):
		called = screens.state(screen, token)["board"]["called"]
		assert ticket["ticket"] not in [one["ticket"] for one in called], "a closed ticket leaves the board"
	with as_user(OWNER):
		screens.control(screen, "mute")
		screens.alert("Please leave the building by the nearest exit.")
	with as_user("Guest"):
		said = screens.state(screen, token)
		assert said["screen"]["muted"] == 1 and said["command"]["name"] == "mute", said
		assert said["alert"] == "Please leave the building by the nearest exit."
	with as_user(OWNER):
		screens.alert("")
	with as_user("Guest"):
		assert screens.state(screen, token)["alert"] is None
