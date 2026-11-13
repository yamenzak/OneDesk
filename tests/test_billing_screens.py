"""What OneAdmin's Billing Home and Releases add up, from their pure parts."""

from types import SimpleNamespace as Row

from frappe import _dict

from onedesk.one_admin import console, earnings, rollout, wizard_answers


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


def test_a_release_says_when_it_was_ready_and_how_long_it_took():
	"""A release is ready when its first server is, and takes as long as its
	slowest server; a bench from before either was kept says nothing."""
	release = {
		"servers": [
			{"prepared_at": "2026-11-11 10:00:00", "ready_at": "2026-11-11 10:12:30"},
			{"prepared_at": "2026-11-11 10:00:00", "ready_at": "2026-11-11 10:05:00"},
			{"prepared_at": None, "ready_at": None},
		]
	}
	assert rollout.prepared(release) == {"ready_at": "2026-11-11 10:05:00", "prepared_in": 750}
	assert rollout.prepared({"servers": [{"state": "ready"}]}) == {"ready_at": None, "prepared_in": None}
	assert rollout.about("main") == {}
	held = [{"server": "se-1", "benches": [{"bench": "b1", "release": "new", "state": "ready"}]}]
	made = rollout.by_release(held, [{"server": "se-1", "bench": "b1", "name": "t", "workspace": "Acme"}])
	assert made[0]["held"] == [{"name": "t", "workspace": "Acme"}]


def test_home_follows_each_signup_as_far_as_it_got():
	"""Each stage of the wizard counts those that reached it or one after it,
	and every month is drawn."""
	asked = [
		_dict(name="a", status="New", tenant=None, stripe_session=None, creation="2026-10-02"),
		_dict(name="b", status="Abandoned", tenant=None, stripe_session="cs_1", creation="2026-11-02"),
		_dict(name="c", status="Done", tenant="live", stripe_session="cs_2", creation="2026-11-03"),
		_dict(name="d", status="Failed", tenant="gone", stripe_session="cs_3", creation="2026-11-04"),
	]
	steps = {"a": [{"step": "you", "event": "Reached"}, {"step": "company", "event": "Reached"}], "b": [{"step": "payment", "event": "Reached"}]}
	funnel = {one["stage"]: one["signups"] for one in wizard_answers.funnel(console.signups(asked, steps, {"live"}))}
	assert (funnel["you"], funnel["company"], funnel["payment"], funnel["paid"], funnel["live"]) == (4, 4, 3, 2, 1)
	months = console.by_month(asked, ["2026-09-01", "2026-10-01", "2026-11-01"])
	assert months == [{"month": "2026-09-01", "started": 0, "paid": 0}, {"month": "2026-10-01", "started": 1, "paid": 0}, {"month": "2026-11-01", "started": 3, "paid": 2}]
