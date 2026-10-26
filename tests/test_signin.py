"""The Sign-in page of Settings reads what frappe keeps, and says it as a person would.
See one_account/signin.py."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SIGNIN = tree.APP / "one_account" / "signin.py"
HOOKS = (tree.APP / "hooks.py").read_text(encoding="utf-8")


def _load(names):
	space = {"_": lambda s: s, "hashlib": __import__("hashlib")}
	for node in ast.parse(SIGNIN.read_text()).body:
		named = getattr(node, "name", None) or (
			getattr(node.targets[0], "id", None) if isinstance(node, ast.Assign) else None
		)
		if named in names:
			exec(ast.unparse(node), space)
	return space


S = _load({"BROWSERS", "SYSTEMS", "device", "key", "grouped"})


def test_a_device_is_named_as_a_person_says_it():
	chrome_mac = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"
	edge = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36 Edg/128.0"
	iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 Version/17.5 Mobile/15E148 Safari/604.1"
	chrome_iphone = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 CriOS/128.0 Mobile/15E148 Safari/604.1"
	assert S["device"](chrome_mac) == "Chrome on Mac"
	assert S["device"](edge) == "Edge on Windows"
	assert S["device"](iphone) == "Safari on iPhone"
	assert S["device"](chrome_iphone) == "Chrome on iPhone"
	assert S["device"](None) == "An unknown device"


def test_the_page_never_sees_a_session_id():
	assert S["key"]("abc") != "abc" and len(S["key"]("abc")) == 16
	rows = S["grouped"]([{"sid": "s1", "device": "Chrome on Mac", "address": "1.2.3.4", "last_used": 1}], "s1")
	assert "sid" not in rows[0] and "s1" not in str(rows)


def test_sessions_are_shown_a_device_at_a_time():
	"""288 sessions from one test run read as one row, not 288."""
	places = [{"sid": f"s{n}", "device": "Chrome on Linux", "address": "127.0.0.1", "last_used": n} for n in range(288)]
	places += [
		{"sid": "phone", "device": "Safari on iPhone", "address": "5.6.7.8", "last_used": 500},
		{"sid": "here", "device": "Chrome on Mac", "address": "1.2.3.4", "last_used": 10},
	]
	rows = S["grouped"](places, "here")
	assert [(row["device"], row["count"]) for row in rows] == [
		("Chrome on Mac", 1),
		("Safari on iPhone", 1),
		("Chrome on Linux", 288),
	]
	assert rows[0]["here"] and not rows[1]["here"]
	assert rows[2]["last_used"] == 287
	assert len({row["key"] for row in rows}) == 3


def test_a_password_change_goes_through_ours_and_the_notices_are_always_mailed():
	assert '"frappe.core.doctype.user.user.update_password": "onedesk.one_account.signin.update_password"' in HOOKS
	notices = tree.notifications()
	for name in ("Password Changed", "Passkey Added", "Administrator Added"):
		assert notices[name].get("always_mailed"), name
