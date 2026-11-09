from onedesk.one_admin import boxes, servers


def test_the_next_box_takes_the_lowest_free_number():
	assert servers.next_name([]) == "box-1"
	assert servers.next_name(["box-1", "box-3"]) == "box-2"


def test_a_box_answers_for_its_addresses_and_nothing_else():
	rules = boxes.ingress(["a.x", "*.d.x"])
	assert rules[0] == {"hostname": "a.x", "service": "http://localhost:80"} and rules[-1] == {"service": "http_status:404"}


def test_the_run_token_asks_only_for_what_a_server_needs():
	groups = [{"name": name, "id": name, "scopes": [scope]} for name, scope in boxes.NEEDS]
	made = boxes.wanted_policies(groups, "acct")
	assert sorted(one["id"] for policy in made for one in policy["permission_groups"]) == sorted(name for name, _ in boxes.NEEDS)
