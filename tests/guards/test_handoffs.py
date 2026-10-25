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
		titled = re.match(r"# (One\w*)\n", text)
		if titled and "\n## Under the hood" in text:
			out[titled[1]] = text
	return out


def test_every_product_says_its_connections():
	products = _products()
	assert len(products) >= 14, sorted(products)
	for title, text in products.items():
		assert "\n## Connections\n" in text, f"{title} has no Connections"
		section = text.split("\n## Connections\n", 1)[1].split("\n## ", 1)
		assert section[1].startswith("Under the hood"), f"{title}: Connections comes just before Under the hood"
		lines = [line for line in section[0].strip().splitlines() if line.startswith("- ")]
		assert lines, f"{title} names no connection"
		for line in lines:
			found = BULLET.match(line)
			assert found, f"{title}: {line[:60]}"
			assert found[2] in products and found[2] != title, f"{title}: {found[2]} is not another product"


def test_the_suite_holds_every_hand_off():
	source = tree.suite()
	assert "def every_hand_off_left_its_records" in source and "HANDOFFS = (" in source
	named = set(re.findall(r'^\t\("(One\w+)", "(One\w+)", ', source, flags=re.M))
	assert len(named) >= 10, named
	assert {one for pair in named for one in pair} <= set(_products()), "a hand-off names no product"
