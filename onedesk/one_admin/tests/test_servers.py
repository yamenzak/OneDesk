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


def test_a_server_is_called_down_once_and_back_once():
	assert servers.after_a_check(0, False) == (1, None)
	assert servers.after_a_check(1, False) == (2, None)
	assert servers.after_a_check(2, False) == (3, "down")
	assert servers.after_a_check(3, False) == (4, None), "said once"
	assert servers.after_a_check(4, True) == (0, "back")
	assert servers.after_a_check(1, True) == (0, None), "a blip is not news"
