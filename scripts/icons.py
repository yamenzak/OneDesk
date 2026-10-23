"""The One marks, as Custom Icon records the desk sprite can resolve.

`Custom Icon` turns an `<svg>` into `<symbol id="icon-NAME">` and injects every
one of them into the single sprite the desk already carries, so a mark becomes
usable anywhere an Icon field is — a dock row, a sidebar header, a workspace.

The reason this is generated rather than typed: each mark inlines the same four
gradients and filters under the same ids, and in one sprite the last one loaded
wins for everybody. Ids are rewritten per mark here, which is what
`gen_brand.py` does per render in the SPA.

Every mark in `brand/` also gets a `NAME-flat` twin: the same shapes in two
inks, for the rail on a workspace's frame colour, where a full-colour mark
fights the frame. A paint near white becomes the ground the mark sits on and
every other paint becomes ink, so the envelope's flap and the beacon's dot stay
cut out of the shape rather than lost in it. The inks are classes, not colours
— `one-fill-ink`, `one-stroke-ground` — because the sanitizer drops a style
attribute and an attribute cannot read a variable; `window/chrome.css` paints
them, and a class rule reaches a `<use>` of the sprite.

    python scripts/icons.py            write onedesk/fixtures/custom_icon.json
    python scripts/icons.py --check    fail if it is stale
"""

import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tree

MARKS = tree.ROOT / "brand"

OTHERS = MARKS / "others"
FIXTURE = tree.APP / "fixtures" / "custom_icon.json"

NAME = re.compile(r"^[a-zA-Z0-9_-]+$")

_DEFINED = re.compile(r'\bid="([^"]+)"')


def unique_ids(svg: str, prefix: str) -> str:
	"""Prefix every id the mark declares, and every url(#…) that points at one."""
	for ident in sorted(set(_DEFINED.findall(svg)), key=len, reverse=True):
		svg = svg.replace(f'id="{ident}"', f'id="{prefix}-{ident}"')
		svg = svg.replace(f"url(#{ident})", f"url(#{prefix}-{ident})")
	return svg


SVG = "http://www.w3.org/2000/svg"
ElementTree.register_namespace("", SVG)

# the OKLab lightness above which a paint reads as white — the flap, the dot, an edge
GROUND = 0.9
DROPPED = {"filter", "linearGradient", "radialGradient"}
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_URL = re.compile(r"^url\(#([^)]+)\)$")


def lightness(colour: str) -> float:
	"""OKLab L of a hex colour: the lightness a person sees, not the one sRGB stores."""
	digits = _HEX.match(colour).group(1)
	if len(digits) == 3:
		digits = "".join(c * 2 for c in digits)
	r, g, b = (int(digits[i : i + 2], 16) / 255 for i in (0, 2, 4))
	r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b))
	l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
	m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
	s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
	return 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s


def flat(svg: str, prefix: str) -> str:
	"""The mark in two inks, ground and ink, with its shadows and gradients gone."""
	root = ElementTree.fromstring(svg)
	tag = lambda node: node.tag.rsplit("}", 1)[-1]
	gradients = {}
	for node in root.iter():
		if tag(node) in ("linearGradient", "radialGradient"):
			stops = [s for s in node if tag(s) == "stop"]
			gradients[node.get("id")] = (
				sum(lightness(s.get("stop-color")) for s in stops) / len(stops),
				sum(float(s.get("stop-opacity", 1)) for s in stops) / len(stops),
			)
	for parent in list(root.iter()):
		for child in list(parent):
			if tag(child) in DROPPED:
				parent.remove(child)
	for node in root.iter():
		node.attrib.pop("filter", None)
		if node is root:
			continue
		classes = []
		for paint in ("fill", "stroke"):
			value = node.get(paint)
			if not value or value == "none":
				continue
			if gradient := _URL.match(value):
				light, alpha = gradients[gradient.group(1)]
				if alpha < 1:
					node.set(f"{paint}-opacity", f"{float(node.get(f'{paint}-opacity', 1)) * alpha:.2f}")
			else:
				light = lightness(value)
			classes.append(f"one-{paint}-{'ground' if light >= GROUND else 'ink'}")
			node.set(paint, "currentColor")
		if classes:
			node.set("class", " ".join(classes))
	return unique_ids(ElementTree.tostring(root, encoding="unicode"), prefix)


def icons() -> list[dict]:
	found = []
	for path in sorted(MARKS.glob("*.svg")) + sorted(OTHERS.glob("*.svg")):
		name = path.stem
		if not NAME.match(name):
			raise SystemExit(f"{path.name}: an icon name is letters, numbers, - and _ only")
		found.append({
			"doctype": "Custom Icon",
			"icon_name": name,
			"name": name,
			"svg": unique_ids(path.read_text().strip(), name),
		})
		if path.parent == MARKS:
			found.append({
				"doctype": "Custom Icon",
				"icon_name": f"{name}-flat",
				"name": f"{name}-flat",
				"svg": flat(path.read_text().strip(), f"{name}-flat"),
			})
	return found


def main() -> int:
	want = json.dumps(icons(), indent=1, sort_keys=True) + "\n"
	if "--check" in sys.argv:
		if not FIXTURE.exists() or FIXTURE.read_text() != want:
			print("onedesk/fixtures/custom_icon.json is stale. Run `python scripts/icons.py`.")
			return 1
		return 0
	FIXTURE.parent.mkdir(parents=True, exist_ok=True)
	FIXTURE.write_text(want)
	print(f"wrote {FIXTURE.relative_to(tree.ROOT)} ({len(icons())} marks)")
	return 0


if __name__ == "__main__":
	sys.exit(main())
