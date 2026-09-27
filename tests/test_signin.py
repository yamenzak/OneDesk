"""The Sign-in page of Settings reads what frappe keeps, and says it as a person would.
See one/signin.py."""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SIGNIN = tree.APP / "one" / "signin.py"
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


S = _load({"BROWSERS", "SYSTEMS", "device", "key"})


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
	assert '"key": key(row.sid)' in SIGNIN.read_text() and '"sid"' not in SIGNIN.read_text().split(
		"def sessions"
	)[1].split("def recent")[0].replace("select sid", "")


def test_a_password_change_goes_through_ours_and_the_notices_are_always_mailed():
	assert '"frappe.core.doctype.user.user.update_password": "onedesk.one.signin.update_password"' in HOOKS
	notices = (tree.APP / "one" / "notifications.py").read_text()
	# Each security notice is always mailed: the two here, and a new administrator.
	for name in ("Password Changed", "Passkey Added", "Administrator Added"):
		assert '"always_mailed": True' in notices.split(f'_lt("{name}")', 1)[1].split("\n\t},", 1)[0], name
