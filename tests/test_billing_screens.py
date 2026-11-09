"""What OneAdmin's Billing Home and Releases add up, from their pure parts."""

from types import SimpleNamespace as Row

from frappe import _dict

from onedesk.one_admin import earnings, rollout


def test_billing_adds_up_only_what_there_is():
	"""Billing's Home draws no month before the first with anything in it, and
	shows no margin rather than a false one when nothing is billed."""
	assert earnings.from_first(["a", "b", "c"], [0, 0, 5]) == 2
	assert earnings.from_first(["a", "b"], [0, 0]) == 2
	assert earnings.margin(0, {"servers": 10}) is None
	assert earnings.margin(100, {"servers": 30, "stripe": 10}) == 60.0
	sold = {"team": Row(label="Team", amount=299, currency="AED", recurring=1), "seats": Row(label="Seats", amount=20, currency="AED", recurring=1), "old": Row(label="Old", amount=70, currency="USD", recurring=1)}
	live = [Row(name="a", offering="team"), Row(name="b", offering=None)]
	billed = earnings.bills(live, [Row(parent="a", offering="seats", quantity=2)], sold)
	assert billed == [{"tenant": "a", "plan": "Team", "amount": 339.0}]
	assert earnings.bills([Row(name="c", offering="old")], [], sold) == [{"tenant": "c", "plan": "Old", "amount": 257.075}]
	spent = earnings.month_cost([339.0], 24, 0, 0, 0)
	assert spent["servers"] > 0 and spent["oneai"] == 0 and spent["stripe"] > 0


def _tenant(name: str, bench: str, **more) -> _dict:
	return _dict({"name": name, "workspace_name": name, "server": "se-1", "bench": bench, "update_at": None, "update_moving": 0, "terms_pending": 0, **more})


def test_releases_read_each_version_across_the_servers():
	"""A release counts its workspaces on every server holding it; a server's
	newest ready bench is current, and a workspace behind it waits."""
	held = [
		{"server": "se-1", "benches": [{"bench": "b1", "release": "old", "state": "ready"}, {"bench": "b2", "release": "new", "state": "ready"}]},
		{"server": "se-2", "benches": [{"bench": "b3", "release": "new", "state": "preparing"}]},
	]
	work = [{"server": "se-1", "bench": "b1"}, {"server": "se-1", "bench": "b2"}, {"server": "se-2", "bench": "b3"}]
	made = rollout.by_release(held, work)
	assert [one["release"] for one in made] == ["new", "old"]
	assert made[0]["workspaces"] == 2 and made[0]["current"] and rollout.state_of(made[0]) == "preparing"
	assert made[1]["workspaces"] == 1 and not made[1]["current"]
	waiting = rollout.waiting(
		[_tenant("t", "b1", update_at="2026-11-20 01:00:00", terms_pending=1), _tenant("m", "b1", update_moving=1), _tenant("done", "b2")],
		{"se-1": "b2"},
		{"b1": "old", "b2": "new"},
	)
	assert [one["name"] for one in waiting] == ["m", "t"]
	assert waiting[1]["moves_by"].startswith("2026-12-20") and waiting[1]["to"] == "new" and waiting[1]["kind"] == "terms"
