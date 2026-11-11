from onedesk.one_admin import control


def test_each_step_lands_in_its_area_and_the_worst_state_shows():
	said = [
		{"step": "sign-in", "state": "ours", "detail": "Signed in"},
		{"step": "account", "state": "ours", "detail": "FOURDEGREE LABS"},
		{"step": "token [one-prod] OneAdmin", "state": "created", "detail": ""},
		{"step": "test mail routing", "state": "ours", "detail": "test.4dl.app"},
		{"step": "sender account", "state": "failed", "detail": "noreply@4dl.app"},
		{"step": "bucket backups", "state": "ours", "detail": "one-backups"},
		{"step": "worker one-keeper", "state": "created", "detail": "deployed"},
	]
	tiles = {one["key"]: one for one in control.areas_of(said)}
	assert [one["key"] for one in control.areas_of(said)] == ["account", "mail", "storage", "services"]
	assert tiles["account"]["state"] == "ready"
	assert tiles["account"]["found"] == ["Signed in", "FOURDEGREE LABS"]
	assert tiles["mail"]["state"] == "failed"
	assert len(tiles["mail"]["steps"]) == 2
	assert tiles["services"]["steps"][0]["step"] == "worker one-keeper"


def test_nothing_run_is_no_tiles():
	assert control.areas_of([]) == []


def test_the_pasted_address_gives_its_code_only_to_its_own_sign_in():
	import pytest

	from onedesk.one_admin import cloudflare_signin

	back = "https://admin.example.com/api/method/onedesk.one_admin.cloudflare_signin.back?code=abc&state=s1"
	assert cloudflare_signin.code_in(back, "s1") == "abc"
	with pytest.raises(ValueError):
		cloudflare_signin.code_in(back, "s2")
	with pytest.raises(ValueError):
		cloudflare_signin.code_in("https://admin.example.com/x?error=access_denied&state=s1", "s1")


def test_routing_is_missing_when_cloudflare_names_a_missing_record():
	from onedesk.one_admin import setup

	needed = {"type": "MX", "name": "m.example.com", "content": "route1.mx.cloudflare.net"}
	assert setup.routing_missing({"errors": [{"code": "missing", "missing": needed}], "record": [needed]})
	assert not setup.routing_missing({"errors": [], "record": [needed]})
	assert setup.routing_missing(None)
	assert setup.routing_missing([{**needed, "missing": True}])
