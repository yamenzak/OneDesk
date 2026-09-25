"""The workspace's own account screen, read back from the files.

Everything on it is a copy of what the administrator said. The workspace holds
one secret and no authority: it cannot change its plan, its quota or its
status, and the only thing it can *do* is ask for a domain — which goes to the
administrator, which goes to Frappe Cloud.

So the guards here are about two things. That nothing on the screen can be
typed, because a workspace that could edit its own storage limit is a workspace
that could raise it. And that every call which changes something asks who is
asking first.
"""

import ast
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

ONE = tree.APP / "one"
ACCOUNT = ONE / "doctype" / "workspace_account" / "workspace_account.json"
DOMAIN = ONE / "doctype" / "workspace_domain" / "workspace_domain.json"

#: Fieldtypes nobody types into.
NOT_A_FIELD = ("Section Break", "Column Break", "Tab Break", "HTML", "Heading", "Image")

#: The calls a workspace administrator makes, and the guard each one runs
#: first. Reading is gated too: the plan and the quota are nobody's business
#: but the people who run the workspace.
GATED = (
	"domains",
	"domains_refresh",
	"domain_check",
	"domain_add",
	"domain_drop",
	"domain_primary",
)


def _json(path):
	return json.loads(path.read_text(encoding="utf-8"))


def test_the_account_is_a_copy_and_not_a_form():
	"""A workspace that could edit its own limit is a workspace that could raise it."""
	doc = _json(ACCOUNT)
	typed = [
		one["fieldname"]
		for one in doc["fields"]
		if one["fieldtype"] not in NOT_A_FIELD and not one.get("read_only")
	]
	assert not typed, f"{typed} can be typed on a Workspace Account"
	for perm in doc["permissions"]:
		assert not perm.get("write"), "the account can be saved"


def test_the_addresses_are_a_copy_too():
	doc = _json(DOMAIN)
	assert doc.get("istable"), "Workspace Domain is a child table"
	typed = [
		one["fieldname"]
		for one in doc["fields"]
		if one["fieldtype"] not in NOT_A_FIELD and not one.get("read_only")
	]
	assert not typed, f"{typed} can be typed on a Workspace Domain"


def test_every_call_that_changes_an_address_asks_who_is_asking():
	"""`_may_rename` is the whole of it: a domain change moves the login page."""
	source = (ONE / "account.py").read_text(encoding="utf-8")
	found = {
		node.name: node
		for node in ast.parse(source).body
		if isinstance(node, ast.FunctionDef)
	}
	for name in GATED:
		assert name in found, f"{name} is gone from one/account.py"
		calls = {
			one.func.id
			for one in ast.walk(found[name])
			if isinstance(one, ast.Call) and isinstance(one.func, ast.Name)
		}
		assert "_may_rename" in calls, f"{name} does not ask who is asking"


def test_the_account_is_in_the_rail():
	"""Otherwise it is reachable only by typing its name, which is where it was.
	It is Settings' Plan and Credits and Domains now, and Settings is in the rail."""
	rail = _json(ONE / "sidebar" / "one" / "one.json")
	assert any(item.get("link_to") == "settings" for item in rail["items"]), "the One rail does not offer Settings"
	assert '"Workspace Account"' in (ONE / "settings.py").read_text(), "Settings does not show the account"


def test_the_screen_text_is_in_register():
	"""The same rule as the operator console: plain, short, no first person.

	`press` is checked here too. A workspace administrator has no idea what
	press is, and on this screen even less than on the operator's.
	"""
	LONGEST = 130
	VOICE = re.compile(r"\b(we|our|us|ours)\b", re.I)
	THEIR_APP = re.compile(r"\bpress\b", re.I)

	wrong = []
	for path in (ACCOUNT, DOMAIN):
		doc = _json(path)
		said = [("[doctype]", doc.get("description") or "")]
		said += [(one["fieldname"], one.get("description") or "") for one in doc["fields"]]
		for where, text in said:
			if not text:
				continue
			if len(text) > LONGEST:
				wrong.append(f"{path.stem}.{where}: {len(text)} characters")
			if VOICE.search(text) or THEIR_APP.search(text):
				wrong.append(f"{path.stem}.{where}: out of register")
	assert not wrong, "screen text out of register:\n  " + "\n  ".join(wrong)
