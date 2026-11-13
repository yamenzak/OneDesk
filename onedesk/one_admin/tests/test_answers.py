from onedesk.one_admin import answers

ZONES = {"Asia/Dubai": "United Arab Emirates"}


def test_a_signup_is_set_up_in_the_country_it_said():
	said = answers.from_signup("Acme", "sam@acme.test", "Germany", "Europe/Berlin", ZONES)
	assert said["companies"] == [{"name": "Acme", "country": "Germany"}]
	assert said["owner"] == {"email": "sam@acme.test", "first_name": "sam"}
	assert said["time_zone"] == "Europe/Berlin"


def test_a_signup_without_a_country_takes_its_time_zones():
	said = answers.from_signup("Acme", "sam@acme.test", None, "Asia/Dubai", ZONES)
	assert said["companies"][0]["country"] == "United Arab Emirates"


def test_a_signup_with_no_country_to_tell_is_left_to_the_wizard():
	assert answers.from_signup("Acme", "sam@acme.test", None, "UTC", ZONES) is None


def test_the_wizards_answers_are_set_up_from_with_the_workspaces_owner():
	typed = {"owner": {"email": "someone@else.test", "first_name": "Sam"}, "language": "en", "time_zone": "Asia/Dubai", "companies": [{"name": "Acme", "country": "United Arab Emirates"}]}
	said = answers.from_wizard(typed, "sam@acme.test")
	assert said["owner"] == {"email": "sam@acme.test", "first_name": "Sam"}
	assert answers.from_wizard({**typed, "language": ""}, "sam@acme.test") is None
	assert answers.from_wizard({}, "sam@acme.test") is None
