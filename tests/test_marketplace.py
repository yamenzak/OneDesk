"""OneMarketplace (onedesk/one/marketplace.py): every app's page is read from
its manifest, a manifest's buyer's words, pictures and credits are checked,
and the page's data says what Install and Turn Off may do."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.one import marketplace, registry  # noqa: E402
from onedesk.one.registry import credits  # noqa: E402
from onedesk.one.registry.model import Kept  # noqa: E402
from onedesk.one_admin import price_list  # noqa: E402

PLANS = (("Starter", ("demo",)), ("Business", ("demo", "own_server")))


def _shown():
	return [one for one in registry.apps() if marketplace.shown(one)]


def test_every_app_sells_itself_in_words():
	"""Every app with a page has a pitch of two or three sentences and a few
	lines of what it brings."""
	for one in _shown():
		assert one.line and one.pitch and 3 <= len(one.brings) <= 6, one.id
		sentences = one.pitch.count(". ") + 1
		assert 2 <= sentences <= 3 and one.pitch.endswith("."), f"{one.id}: {sentences} sentences"
		assert not [line for line in one.brings if line.endswith(".")], f"{one.id}: a line it brings is not a sentence"


def test_the_kinds_of_credits_are_the_price_lists():
	assert set(credits.IDS) == set(price_list.MARKUP)
	assert price_list.MAIL_CREDITS == 1 and "one credit" in credits.get("mail").said, "the mail line says the price list's number"


@pytest.mark.parametrize(
	"change, said",
	[
		({"pitch": ("Two", "words")}, "pitch is words"),
		({"brings": ["A list"]}, "brings is a tuple"),
		({"brings": ("",)}, "brings is a tuple"),
		({"credits": ("gold",)}, "credits names"),
		({"media": ("one.png", "two.png")}, "media lists 2"),
		({"media": tuple(f"{n}.png" for n in range(7))}, "media lists 7"),
		({"media": ("a.png", "b.png", "c.bmp")}, "ending in one of"),
		({"media": ("a.png", "b.png", "../c.png")}, "ending in one of"),
		({"media": ("a.png", "b.png", "c.png")}, "is not in one_crm/media/"),
	],
)
def test_a_wrong_buyers_page_is_refused_by_name(change, said):
	apps = list(registry.apps())
	crm = next(one for one in apps if one.id == "one_crm")
	apps[apps.index(crm)] = replace(crm, **change)
	with pytest.raises(registry.Invalid, match=said):
		registry._check(apps)


def test_media_in_the_apps_folder_is_held(tmp_path):
	folder = tmp_path / "one_crm"
	(folder / "media").mkdir(parents=True)
	for named in ("home.png", "lead.webp", "pipeline.gif", "quote.mp4"):
		(folder / "media" / named).write_bytes(b"x")
	crm = replace(registry.get("one_crm"), media=("home.png", "lead.webp", "pipeline.gif", "quote.mp4"))
	registry._check_market(crm, "one_crm/manifest.py", folder)


def test_the_least_plan_with_every_feature_is_named():
	assert marketplace.least_plan(("own_server",), PLANS) == "Business"
	assert marketplace.least_plan((), PLANS) == "Starter"
	assert marketplace.least_plan(("nothing",), PLANS) is None


def _pages(**said):
	given = {"off": set(), "held": None, "kept_now": {}, "steps": set(), "plans": PLANS, **said}
	return {one["id"]: one for one in marketplace.pages(_shown(), **given)}


def test_every_app_has_a_page_in_the_rails_order():
	pages = marketplace.pages(_shown(), off=set(), held=None, kept_now={}, steps=set(), plans=PLANS)
	assert [one["id"] for one in pages] == [one.id for one in _shown()]
	assert "one_admin" not in {one["id"] for one in pages}, "the operators' app has no page"
	assert all(one["pitch"] and "{" not in one["pitch"] + "".join(one["brings"]) for one in pages), "names are filled in"


def test_an_app_off_may_be_installed_and_one_on_turned_off():
	pages = _pages(off={"one_crm"}, steps={"one_crm"})
	assert pages["one_crm"]["may_install"] and not pages["one_crm"]["may_turn_off"] and pages["one_crm"]["steps"]
	assert pages["one_task"]["may_turn_off"] and not pages["one_task"]["may_install"]
	assert not pages["one"]["may_turn_off"] and pages["one"]["always"], "One is always on"


def test_kept_or_needed_is_not_turned_off_and_says_why():
	pages = _pages(kept_now={"one_book": "Ledger entries are the books."})
	assert pages["one_book"]["kept"] == "Ledger entries are the books." and not pages["one_book"]["may_turn_off"]
	assert pages["one_inventory"]["needed_by"] == [registry.name("one_factory")] and not pages["one_inventory"]["may_turn_off"]
	assert pages["one_factory"]["needs"] == [registry.name("one_inventory")]
	off = _pages(off={"one_factory"})
	assert off["one_inventory"]["needed_by"] == [] and off["one_inventory"]["may_turn_off"], "an app off needs nothing"
	private = _pages(private={"acme": ("one_crm",)}, names={**registry.names(), "acme": "Acme Fleet"})
	assert private["one_crm"]["needed_by"] == ["Acme Fleet"], "a private app is always on"


def test_a_plan_without_the_feature_names_the_plan_and_offers_no_install():
	apps = [replace(one, plan=("own_server",)) if one.id == "one_crm" else one for one in _shown()]
	pages = {one["id"]: one for one in marketplace.pages(apps, off={"one_crm"}, held=("demo",), kept_now={}, steps=set(), plans=PLANS)}
	assert pages["one_crm"]["plan"] == {"included": False, "needs": "Business"} and not pages["one_crm"]["may_install"]
	assert pages["one_task"]["plan"] == {"included": True, "needs": None}
	unsaid = {one["id"]: one for one in marketplace.pages(apps, off={"one_crm"}, held=None, kept_now={}, steps=set(), plans=PLANS)}
	assert unsaid["one_crm"]["plan"]["included"], "a workspace whose account has not said is held to nothing"


def test_credits_are_said_in_words_with_names_filled():
	pages = _pages()
	assert pages["one_cloud"]["credits"] == [credits.get("oneos").said.replace("{oneos}", registry.name("oneos")), credits.get("office").said]
	assert pages["one_task"]["credits"] == []


def test_a_field_lists_the_apps_it_starts_with():
	pages = _pages()
	assert "manufacturer" in pages["one_factory"]["fields"] and "clinic" not in pages["one_factory"]["fields"]
	assert "clinic" in pages["one_book"]["fields"], "every field starts with OneBook"


def test_one_always_on_says_so_without_a_switch():
	kept = replace(registry.get("one_task"), kept=Kept("Always."))
	pages = {one["id"]: one for one in marketplace.pages([kept], off=set(), held=None, kept_now={"one_task": "Always."}, steps=set(), plans=PLANS)}
	assert pages["one_task"]["always"] and pages["one_task"]["kept"] == "Always." and not pages["one_task"]["may_turn_off"]
