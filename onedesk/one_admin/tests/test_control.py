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
