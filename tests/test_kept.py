"""Needs and kept (one/registry/switches.py, one/apps.py `settled`): an app
is kept by the rule, once others' records need its records or the law needs
them reachable; turning one off is refused while it is kept or an app left
on needs it, and turning one on brings what it needs. Pure, with the
site's counts mocked."""

from onedesk.one import registry
from onedesk.one.registry import switches
from onedesk.one.registry.model import App, Kept

NONE = lambda doctype: False  # noqa: E731


def test_onebook_is_kept_once_it_has_an_entry_and_onecrm_never():
	book, crm = registry.get("one_book"), registry.get("one_crm")
	assert switches.held(book, NONE) is None, "a new workspace may still turn its books off"
	assert switches.held(book, lambda doctype: doctype == "GL Entry") == book.kept.why
	assert switches.held(book, lambda doctype: doctype == "Sales Invoice") == book.kept.why
	assert crm.kept is None and switches.held(crm, lambda doctype: True) is None


def test_each_kept_app_says_why_and_from_which_records():
	"""The rule applied to every app: the books and the law (OneBook's
	entries, OneHR's payslips), others' records (OneInventory's stock moves
	behind the books' stock value), and the two always on."""
	kept = {one.id: one.kept.when for one in registry.apps() if one.kept}
	assert kept == {
		"one": (),
		"one_admin": (),
		"one_book": ("GL Entry", "Sales Invoice", "Purchase Invoice"),
		"one_inventory": ("Stock Ledger Entry",),
		"one_hr": ("Salary Slip",),
	}
	assert all(registry.get(id).kept.why.endswith(".") for id in kept)


def test_kept_always_is_never_a_switch():
	assert "one" in {one.id for one in switches.always()}
	assert "one_book" in {one.id for one in switches.switches()}, "kept by its records, so a switch until it holds them"
	assert switches.held(App(id="x", name="X", kind="app", module="X", kept=Kept("Why.")), NONE) == "Why."


def test_turning_off_is_refused_while_kept_or_needed(monkeypatch):
	monkeypatch.setattr(switches, "_needs", lambda: {"factory": ("inventory",), "inventory": (), "crm": (), "books": ()})
	on = {"factory", "books"}
	said = switches.refused({"inventory", "books", "crm"}, on - {"books"}, {"books": "Books are the law.", "inventory": None, "crm": None})
	assert said == {"books": ("kept", "Books are the law."), "inventory": ("needed", ("factory",))}
	assert switches.refused({"inventory", "factory"}, set(), {}) == {}, "both off together is fine"


def test_a_private_app_left_on_holds_what_it_needs(monkeypatch):
	monkeypatch.setattr(switches, "_needs", lambda: {"crm": ()})
	assert switches.refused({"crm"}, {"rua"}, {}, {"rua": ("crm",)}) == {"crm": ("needed", ("rua",))}


def test_turning_on_brings_what_it_needs(monkeypatch):
	monkeypatch.setattr(switches, "_needs", lambda: {"factory": ("inventory",), "inventory": (), "studio": ("ai",), "ai": ()})
	assert switches.with_needs({"factory", "studio"}) == {"factory": (), "studio": (), "inventory": ("factory",), "ai": ("studio",)}


def test_ones_apps_need_what_they_cannot_run_without():
	assert registry.get("one_factory").needs == ("one_inventory",)
	assert registry.get("one_studio").needs == ("one_ai",)
	assert registry.get("one_crm").needs == ()
