"""Point 3: every product's README says what it hands to the others and
what it takes from them, and the demo suite holds each hand-off to the
records it leaves (`every_hand_off_left_its_records`). These read the files."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
sys.path.insert(0, str(ROOT / "scripts"))

import tree  # noqa: E402

BULLET = re.compile(r"^- \*\*(From|To) (\w+)\*\*: \S", re.M)


def _products() -> dict[str, str]:
	"""Each product README (a One title, a manual and its Under the hood), by its title.
	The demo's and the notifications' READMEs have an Under the hood but are no product."""
	out = {}
	for path in sorted([*APP.glob("*/README.md"), *APP.glob("*/AGENTS.md")]):
		text = path.read_text()
		titled = re.match(r"# (One\w*|\w+Center)\n", text)
		if titled and "\n## Under the hood" in text:
			out[titled[1]] = text
	return out


def unsaid(products: dict[str, str]) -> list[str]:
	"""Each product whose README says no Connections, says them out of place,
	or names something that is not another product. Pure."""
	out = []
	for title, text in products.items():
		if "\n## Connections\n" not in text:
			out.append(f"{title} has no Connections")
			continue
		section = text.split("\n## Connections\n", 1)[1].split("\n## ", 1)
		if len(section) < 2 or not section[1].startswith("Under the hood"):
			out.append(f"{title}: Connections comes just before Under the hood")
		lines = [line for line in section[0].strip().splitlines() if line.startswith("- ")]
		out += [] if lines else [f"{title} names no connection"]
		for line in lines:
			found = BULLET.match(line)
			if not found:
				out.append(f"{title}: {line[:60]}")
			elif found[2] not in products or found[2] == title:
				out.append(f"{title}: {found[2]} is not another product")
	return out


def test_every_product_says_its_connections():
	products = _products()
	assert len(products) >= 14, sorted(products)
	found = unsaid(products)
	assert not found, found


def handed(suite: str) -> set[tuple[str, str]]:
	"""The hand-offs the suite holds, as (from, to). Pure."""
	if "def every_hand_off_left_its_records" not in suite or "HANDOFFS = (" not in suite:
		return set()
	return set(re.findall(r'^\t\("(One\w+)", "(One\w+)", ', suite, flags=re.M))


def test_the_suite_holds_every_hand_off():
	named = handed(tree.suite())
	assert len(named) >= 10, named
	assert {one for pair in named for one in pair} <= set(_products()), "a hand-off names no product"


def test_the_hand_off_rules_catch_their_examples():
	book = "# OneBook\n\n## Connections\n\n- **From OneCRM**: a won deal's invoice.\n\n## Under the hood\n"
	crm = "# OneCRM\n\n## Connections\n\n- **To OneNowhere**: a lead.\n- what it gives\n\n## Under the hood\n"
	assert unsaid({"OneBook": book, "OneCRM": crm}) == ["OneCRM: OneNowhere is not another product", "OneCRM: - what it gives"]
	assert unsaid({"OneBook": book, "OneCRM": "# OneCRM\n\n## Under the hood\n"}) == ["OneCRM has no Connections"]
	suite = 'def every_hand_off_left_its_records():\n\tpass\n\nHANDOFFS = (\n\t("OneCRM", "OneBook", "x"),\n)\n'
	assert handed(suite) == {("OneCRM", "OneBook")}
	assert handed(suite.replace("def every_hand_off_left_its_records", "def other")) == set()
