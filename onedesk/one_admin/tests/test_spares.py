from onedesk.one_admin import spares


def test_a_spare_is_started_when_there_is_room_and_none_is_building():
	assert spares.wants_one(0, [], 5)
	assert spares.wants_one(3, [{"site": "a"}], 5)
	assert not spares.wants_one(4, [{"site": "a"}], 5), "a spare counts towards the limit"
	assert not spares.wants_one(0, [{"site": "a", "task": "t"}], 5), "one at a time"
	assert not spares.wants_one(0, [{"site": "a"}, {"site": "b"}], 5), "two are enough"
	assert spares.wants_one(50, [], 0), "no limit set"


def test_a_spare_the_agent_is_making_counts_as_building_until_it_reports():
	asked = {"site": "a", "asked": "1-spare", "at": 100}
	assert spares.building(asked) and not spares.wants_one(0, [asked], 5)
	assert not spares.overdue(asked, 100 + spares.AGENT_LASTS)
	assert spares.overdue(asked, 101 + spares.AGENT_LASTS)
	assert not spares.overdue({"site": "a", "task": "t"}, 10**10), "Pilot's own tasks say when they fail"
