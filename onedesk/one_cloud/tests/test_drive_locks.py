"""A drive lock is the File's lease (dav_locks.py), and a save from an app
that does not lock never lands over somebody else's work (dav_saves.py)."""

from datetime import datetime, timedelta

from onedesk.one_cloud import dav_locks, dav_saves, lease

NOW = datetime(2026, 11, 12, 9, 0, 0)
T = 1_800_000_000.0


def test_a_lock_lasts_what_the_app_asked_from_a_minute_to_an_hour():
	assert dav_locks.seconds(600) == 600
	assert dav_locks.seconds("3600") == 3600
	assert dav_locks.seconds(5) == dav_locks.SHORTEST
	assert dav_locks.seconds(604800) == dav_locks.LONGEST, "an app asking a week holds it an hour, renewing"
	assert dav_locks.seconds(-1) == dav_locks.LONGEST, "infinite"
	assert dav_locks.seconds(None) == dav_locks.LONGEST
	assert dav_locks.seconds("Infinite") == dav_locks.LONGEST


def test_a_lock_is_refused_while_somebody_else_has_it_alone_or_writes_live():
	oneos = {"one_lease_user": "samir@one.test", "one_lease_kind": lease.ONEOS, "one_lease_until": NOW + timedelta(minutes=1)}
	assert lease.refused(oneos, {}, "huda@one.test", lease.DAV, NOW)["kind"] == lease.ONEOS
	assert lease.refused(oneos, {}, "samir@one.test", lease.DAV, NOW), "not on the drive while in OneOS, even by Samir"
	live = {"huda@one.test": {"write": True, "app": "workbook"}}
	assert lease.refused(None, live, "samir@one.test", lease.DAV, NOW)["user"] == "huda@one.test"
	mine = {"one_lease_user": "huda@one.test", "one_lease_kind": lease.DAV, "one_lease_until": NOW + timedelta(minutes=1)}
	assert lease.refused(mine, {}, "huda@one.test", lease.DAV, NOW) is None, "a second app of hers on the drive"
	assert lease.refused(None, {"omar@one.test": {"write": False, "app": "document"}}, "huda@one.test", lease.DAV, NOW) is None


def test_the_app_is_told_who_holds_it_another_way():
	names = {"samir@one.test": "Samir Haddad"}
	assert dav_locks.shown({"user": "samir@one.test", "kind": lease.ONEOS}, names) == ("Samir Haddad", "OneOS")
	assert dav_locks.shown({"user": "samir@one.test", "app": "workbook"}, names) == ("Samir Haddad", "OneWorkbook")
	assert dav_locks.shown({"user": "samir@one.test", "kind": lease.DAV}, names) is None, "wsgidav lists a drive lock itself"
	assert dav_locks.shown(None, names) is None
	assert dav_locks.owner("Samir & Co", "OneOS") == b'<D:owner xmlns:D="DAV:"><D:href>Samir &amp; Co (OneOS)</D:href></D:owner>'


def test_everybody_with_the_file_open_is_told_of_its_deletion():
	alone = {"one_lease_user": "samir@one.test", "one_lease_until": NOW + timedelta(minutes=1)}
	live = {"huda@one.test": {"write": True}, "samir@one.test": {"write": False}}
	assert lease.holders(alone, live, NOW) == ["samir@one.test", "huda@one.test"]
	assert lease.holders({**alone, "one_lease_until": NOW}, {}, NOW) == []


def test_a_files_tag_follows_its_content_not_its_name():
	one = {"id": "f1", "url": "/private/files/a.docx", "size": 10, "name": "A.docx", "modified": "2026-11-12 09:00:00"}
	assert dav_saves.tag(one) == dav_saves.tag({**one, "name": "B.docx", "modified": "2026-11-12 10:00:00"})
	assert dav_saves.tag(one) != dav_saves.tag({**one, "url": "/private/files/a1.docx"})


def test_if_match_names_the_version():
	assert dav_saves.matches('"f1-abc-10"', "f1-abc-10")
	assert dav_saves.matches('W/"f1-abc-10", "x"', "f1-abc-10")
	assert dav_saves.matches("*", "anything")
	assert not dav_saves.matches('"f1-old-9"', "f1-abc-10")


def test_a_save_from_an_older_version_is_a_copy_unless_its_app_holds_the_lock():
	assert dav_saves.stale("f1-old", "f1-new", locked=False)
	assert not dav_saves.stale("f1-old", "f1-new", locked=True), "the lock holder saves over"
	assert not dav_saves.stale("f1-new", "f1-new", locked=False)
	assert not dav_saves.stale(None, "f1-new", locked=False), "nothing says where it started: as before"


COPY = "{0} ({1}'s copy)"


def test_the_copy_is_named_for_whoever_saved_it():
	assert dav_saves.copy_name("Budget.xlsx", "Huda", COPY) == "Budget (Huda's copy).xlsx"
	assert dav_saves.copy_name("Notes", "Huda", COPY) == "Notes (Huda's copy)"
	assert dav_saves.copy_name("Report.final.docx", "Samir", COPY) == "Report.final (Samir's copy).docx"
	assert dav_saves.copy_name(".env", "Samir", COPY) == ".env (Samir's copy)"


def test_safe_save_names_are_temporary():
	for name in ("~WRL0001.tmp", "~WRD0000.tmp", "Word Work File L_123.tmp", "Budget.xlsx.sb-8a1c-Qx", "notes.txt~", "Book1.bak"):
		assert dav_saves.temporary(f"/@my/{name}"), name
	assert dav_saves.temporary("/@my/(A Document Being Saved By Pages)/Report.pages")
	for name in ("Budget.xlsx", "Report (Huda's copy).docx", "Notes"):
		assert not dav_saves.temporary(f"/@my/{name}"), name


def test_a_name_left_moments_ago_is_taken_back_only_by_the_same_person():
	gone = {"file": "f1", "by": "huda@one.test", "on": T - 30}
	assert dav_saves.claims(gone, "huda@one.test", T)
	assert not dav_saves.claims(gone, "samir@one.test", T), "somebody else's file of the same name is new"
	assert not dav_saves.claims({**gone, "on": T - dav_saves.GONE_SECONDS}, "huda@one.test", T)
	assert not dav_saves.claims(None, "huda@one.test", T)
