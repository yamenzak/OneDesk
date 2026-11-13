import base64
from datetime import datetime, timedelta

from onedesk.one import errors
from onedesk.one_admin import boxes, servers, sessions
from onedesk.one_admin import errors as heard


def test_every_walk_ends_by_giving_the_session_its_address():
	for source, walk in sessions.WALKS.items():
		assert walk[-1] == sessions.LAST_STEP, source
		assert walk[0] == "create", source
		assert set(walk) <= set(sessions.STEPS), source
		assert sessions.after(source, walk[-2]) == sessions.LAST_STEP
		assert sessions.after(source, walk[-1]) is None


def test_a_copy_stays_quiet_and_only_a_demo_may_build_the_demo_company():
	copy = sessions.config_for(sessions.COPY, "https://s-1.d.x")
	demo = sessions.config_for(sessions.DEMO, "https://s-1.d.x")
	assert copy["mute_emails"] == 1 and copy["pause_scheduler"] == 1 and "one_dev" not in copy
	assert demo["one_dev"] == 1 and demo["pause_scheduler"] == 0
	assert "one_dev" not in sessions.config_for(sessions.FRESH, "https://s-1.d.x")


def test_a_copy_needs_a_workspace_that_has_said_so_lately():
	now = datetime(2026, 11, 10, 12)
	assert sessions.agreed(now - timedelta(hours=2), now)
	assert not sessions.agreed(now - timedelta(hours=4), now)
	assert not sessions.agreed(None, now)
	assert sessions.agreed(now - timedelta(hours=40), now, within_hours=sessions.LAPSED_AFTER_HOURS)
	assert not sessions.agreed(now - timedelta(hours=49), now, within_hours=sessions.LAPSED_AFTER_HOURS)


def test_a_connected_server_is_named_before_its_cloud_is_known_and_keeps_it():
	assert servers.next_name(["oracle-1"], servers.CONNECTED_NAME) == "machine-1"
	assert servers.next_name(["oracle-1", "machine-1"], servers.CONNECTED_NAME) == "machine-2"


TRACE = '''Traceback (most recent call last):
  File "/home/frappe/pilot/benches/main/apps/onedesk/onedesk/one_book/x.py", line 41, in pay
    raise frappe.ValidationError("Invoice ACME-00123 is wrong for a@b.co")
frappe.exceptions.ValidationError: Invoice ACME-00123 is wrong for a@b.co
'''


def test_only_the_kind_of_error_and_the_place_leave_a_workspace():
	assert errors.kind_of(TRACE) == "frappe.exceptions.ValidationError"
	assert errors.where_of(TRACE) == "onedesk/onedesk/one_book/x.py:pay"
	assert "@" not in errors.scrubbed("Payment for a@b.co failed") and "00123456" not in errors.scrubbed("Row 00123456 failed")


def test_the_same_fault_on_another_record_is_the_same_kind():
	one = errors.fingerprint_of("KeyError", "onedesk/a.py:x", errors.scrubbed("Saving 00123456 failed"))
	two = errors.fingerprint_of("KeyError", "onedesk/a.py:x", errors.scrubbed("Saving 00999888 failed"))
	assert one == two


RELATIVE = '''Traceback with variables (most recent call last):
  File "apps/frappe/frappe/handler.py", line 85, in execute_cmd
  File "apps/onedesk/onedesk/one_project/contacts.py", line 78, in contacts
  File "apps/frappe/frappe/__init__.py", line 767, in has_permission
  File "env/lib/python3.14/site-packages/requests/models.py", line 1167, in raise_for_status
builtins.TypeError: has_permission() got an unexpected keyword argument
'''


def test_where_is_our_own_last_place_even_on_a_relative_path():
	assert errors.where_of(RELATIVE) == "onedesk/onedesk/one_project/contacts.py:contacts"
	assert errors.where_of('  File "apps/frappe/frappe/app.py", line 1, in application\n') == "frappe/frappe/app.py:application"


def test_an_error_names_the_part_of_one_it_was_in():
	assert heard.part_of("onedesk/onedesk/one_project/contacts.py:contacts") == "OneProject"
	assert heard.part_of("onedesk/onedesk/one_cloud/file.py:get_content") == "OneCloud"
	assert heard.part_of("", "onedesk.one_admin.backups.config_copy") == "OneAdmin"
	assert heard.part_of("frappe/frappe/app.py:application") == "Frappe"
	assert heard.part_of("", "Weather for Dubai") == "One"


def test_a_workspaces_errors_are_counted_by_kind():
	rows = [
		{"method": "Payment failed", "error": TRACE, "creation": "2026-11-10 09:00:00"},
		{"method": "Payment failed", "error": TRACE, "creation": "2026-11-10 10:00:00"},
		{"method": "Something else", "error": "KeyError: 'x'", "creation": "2026-11-10 09:30:00"},
	]
	made = errors.summaries(rows)
	assert len(made) == 2
	payment = next(one for one in made if one["title"] == "Payment failed")
	assert payment["count"] == 2 and payment["first_seen"] == "2026-11-10 09:00:00" and payment["last_seen"] == "2026-11-10 10:00:00"
	assert "traceback" not in " ".join(str(value) for value in payment.values()).lower()


def test_the_connect_script_carries_the_first_boot_and_the_memory_limit():
	class Tunnels:
		def tunnel_token(self, _tunnel):
			return "token"

	keys = {"github_token": "g", "r2_endpoint": "e", "assets_bucket": "b", "assets_read_key": "k", "assets_read_secret": "s"}
	made = {"tunnel": "t", "host": "h", "pilot_password": "p", "agent": "a"}
	real = boxes.release_of
	boxes.release_of = lambda _keys, _release: {"frappe": "f", "erpnext": "e", "hrms": "h"}
	try:
		script = boxes.connect_script(keys, Tunnels(), "oracle-1", made, "abc", "https://admin.x")
	finally:
		boxes.release_of = real
	assert "ONE_MEMORY=5g" in script and "--memory=\"$ONE_MEMORY\"" in script
	assert "one-copies" in script and "podman create" in script
	box = base64.b64decode(script.split("ONE_BOX=")[1].split("\n")[0].strip("'")).decode()
	assert "ONE_IN_CONTAINER=1" in box and "ONE_TUNNEL_TOKEN=token" in box and "ONE_PILOT_PASSWORD=p" in box
	assert "ONE_SERVER=oracle-1\n" in script and "ONE_AGENT=a\n" in script and "ONE_ADMIN=https://admin.x\n" in script
	assert "servers.located" in script and "X-One-Agent" in script
