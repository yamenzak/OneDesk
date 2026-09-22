"""One app on every site, and one switch deciding which kind of site it is.

The whole of the operator side is reachable on a tenant workspace unless two
things stay true, and neither is enforced by anything at runtime — a doctype
that quietly grants System Manager is a Tenant list on a customer's own desk,
and nobody would see it happen.

So both are held here, off the shipped JSON:

* every doctype in the One Admin module grants exactly `One Operator` and
  grants it to nobody else;
* the switch is read from `site_config` and from nowhere a request can write.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

MODULE = "One Admin"
OPERATOR = "One Operator"

#: Read off the module rather than typed, so a doctype added without a
#: permission block is a failure rather than a thing this file forgot.
def admin_doctypes() -> list[tuple[str, dict]]:
	found = []
	for path in tree.fixtures():
		if path.parent.parent.name != "doctype" or path.stem != path.parent.name:
			continue
		spec = json.loads(path.read_text())
		if spec.get("module") == MODULE:
			found.append((spec.get("name", path.stem), spec))
	return found


def test_the_module_has_doctypes_to_hold_to_the_rule():
	assert admin_doctypes(), "no One Admin doctypes found — this file is guarding nothing"


def test_every_operator_doctype_grants_one_role_and_it_is_the_operator():
	for name, spec in admin_doctypes():
		roles = [row.get("role") for row in spec.get("permissions") or []]
		assert roles == [OPERATOR], (
			f"{name} grants {roles!r}. Every One Admin doctype grants exactly "
			f"{OPERATOR!r}, because that role is the only thing keeping the "
			"operator side off a tenant's own desk."
		)


def test_the_module_is_registered():
	assert MODULE in tree.modules()


def test_the_switch_is_read_from_site_config_and_nowhere_else():
	source = (tree.APP / "one_admin" / "site.py").read_text()
	assert 'FLAG = "one_admin"' in source
	assert "frappe.conf.get(FLAG)" in source
	for writable in ("System Settings", "get_single_value", "db.get_value"):
		assert writable not in source, (
			f"site.py reads {writable}. The switch has to be something a "
			"request cannot write, or a tenant administrator can flip it."
		)


def test_refusing_is_the_default_for_anything_that_bills():
	source = (tree.APP / "one_admin" / "site.py").read_text()
	assert "def require_admin()" in source
	assert "PermissionError" in source


def test_nothing_mirrors_frappe_cloud():
	"""No doctype stores what press already knows.

	A table of somebody else's state is wrong between syncs, and the way you
	find out is a customer who cannot be placed on a bench that exists. What we
	store is what we asked press for, which is ours.
	"""
	mirrors = [name for name, _ in admin_doctypes() if name.lower().startswith("press ")]
	assert not mirrors, (
		f"{mirrors} mirror press. Ask press instead — onedesk/one_admin/press.py "
		"reads benches, clusters and plans live and caches for a minute."
	)


def test_the_press_client_holds_nothing():
	source = (tree.APP / "one_admin" / "press.py").read_text()
	for writing in ("frappe.get_doc(", "insert(", ".save(", "db.set_value"):
		assert writing not in source, (
			f"press.py calls {writing}. It asks press and caches; it does not "
			"write, because the moment it writes there is a copy to go stale."
		)
