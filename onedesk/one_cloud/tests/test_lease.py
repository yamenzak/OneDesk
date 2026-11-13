"""One lease per File (one_cloud/lease.py), and saves in one sitting merged
into one version (history.merges)."""

from datetime import datetime, timedelta

from onedesk.one_cloud import history, lease

NOW = datetime(2026, 11, 12, 9, 0, 0)
T = 1_800_000_000.0


def _alone(user="samir@one.test", kind=lease.ONEOS, seconds=60):
	return {"one_lease_user": user, "one_lease_kind": kind, "one_lease_lock": "k1", "one_lease_until": NOW + timedelta(seconds=seconds)}


def test_an_alone_lease_holds_until_its_time():
	assert lease.holding(_alone(), NOW)
	assert not lease.holding(_alone(seconds=0), NOW)
	assert not lease.holding({"one_lease_user": None}, NOW)
	assert not lease.holding(None, NOW)


def test_a_live_holder_is_kept_two_minutes_after_their_editor_last_spoke():
	seen = {
		b"huda@one.test|s1": {"seen": T - 30, "write": True, "app": "workbook"},
		"karim@one.test|s2": {"seen": T - lease.LIVE_SECONDS, "write": True, "app": "workbook"},
		"omar@one.test|s3": {"seen": T - 10, "write": False, "app": "document"},
	}
	assert lease.present(seen, T) == {
		"huda@one.test": {"write": True, "app": "workbook"},
		"omar@one.test": {"write": False, "app": "document"},
	}, "karim's editor went quiet two minutes ago"


def test_a_person_in_two_tabs_writes_if_either_may():
	seen = {"huda@one.test|s1": {"seen": T, "write": False, "app": "workbook"}, "huda@one.test|s2": {"seen": T, "write": True, "app": "workbook"}}
	assert lease.present(seen, T)["huda@one.test"]["write"]


def test_alone_is_refused_while_anybody_may_write_live():
	live = {"huda@one.test": {"write": True, "app": "workbook"}}
	assert lease.refused(None, live, "samir@one.test", lease.ONEOS, NOW) == {"user": "huda@one.test", "app": "workbook"}
	assert lease.refused(None, live, "huda@one.test", lease.ONEOS, NOW) == {"user": "huda@one.test", "app": "workbook"}, "nor by the person in the editor themselves"
	assert lease.refused(None, {"omar@one.test": {"write": False, "app": "workbook"}}, "samir@one.test", lease.ONEOS, NOW) is None, "somebody reading does not stop it"
	assert lease.refused(None, {}, "samir@one.test", lease.ONEOS, NOW) is None


def test_somebody_elses_writer_is_named_before_the_asker():
	live = {"samir@one.test": {"write": True, "app": "workbook"}, "huda@one.test": {"write": True, "app": "document"}}
	assert lease.refused(None, live, "samir@one.test", lease.ONEOS, NOW)["user"] == "huda@one.test"


def test_alone_is_one_holder_one_way():
	assert lease.refused(_alone(), {}, "huda@one.test", lease.ONEOS, NOW) == {"user": "samir@one.test", "kind": lease.ONEOS}
	assert lease.refused(_alone(), {}, "samir@one.test", lease.ONEOS, NOW) is None, "their own session opens again"
	assert lease.refused(_alone(), {}, "samir@one.test", lease.DAV, NOW)["kind"] == lease.ONEOS, "not also on the drive"
	assert lease.refused(_alone(seconds=-1), {}, "huda@one.test", lease.ONEOS, NOW) is None, "a lapsed lease is nobody's"


def test_while_alone_is_held_the_editors_read():
	assert lease.reading(_alone(), "huda@one.test", NOW) == {"user": "samir@one.test", "kind": lease.ONEOS, "mine": False}
	assert lease.reading(_alone(), "samir@one.test", NOW)["mine"], "the holder's own editor reads too"
	assert lease.reading(_alone(seconds=-1), "huda@one.test", NOW) is None
	assert lease.reading(None, "huda@one.test", NOW) is None


def _last(**more):
	return {"sitting": "editor", "by": "huda@one.test", "url": "/files/b.xlsx", "on": T - 60, **more}


def test_saves_in_one_sitting_are_one_version():
	assert history.merges(_last(), "/files/b.xlsx", "huda@one.test", "editor", T)


def test_a_new_version_when_the_sitting_is_not_the_same():
	assert not history.merges(_last(), "/files/b.xlsx", "karim@one.test", "editor", T), "somebody else"
	assert not history.merges(_last(), "/files/b.xlsx", "huda@one.test", "drive", T), "another way in"
	assert not history.merges(_last(), "/files/c.xlsx", "huda@one.test", "editor", T), "the file holds something else since"
	assert not history.merges(_last(on=T - history.SITTING_SECONDS), "/files/b.xlsx", "huda@one.test", "editor", T), "ten minutes later"
	assert not history.merges(None, "/files/b.xlsx", "huda@one.test", "editor", T), "the first save keeps what came before"
	assert not history.merges(_last(sitting=None), "/files/b.xlsx", "huda@one.test", None, T), "an upload is always a version"
