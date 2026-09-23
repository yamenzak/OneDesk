"""The One marks, as Custom Icon records the desk sprite can resolve.

`Custom Icon` turns an `<svg>` into `<symbol id="icon-NAME">` and injects every
one of them into the single sprite the desk already carries, so a mark becomes
usable anywhere an Icon field is — a dock row, a sidebar header, a workspace.

The reason this is generated rather than typed: each mark inlines the same four
gradients and filters under the same ids, and in one sprite the last one loaded
wins for everybody. Ids are rewritten per mark here, which is what
`gen_brand.py` does per render in the SPA.

    python scripts/icons.py            write onedesk/fixtures/custom_icon.json
    python scripts/icons.py --check    fail if it is stale
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tree

MARKS = tree.ROOT / "brand"

#: Other companies' marks, for a button that opens their app. See its README.
OTHERS = MARKS / "others"
FIXTURE = tree.APP / "fixtures" / "custom_icon.json"

#: `CustomIcon.validate` refuses anything else, and the name becomes a DOM id.
NAME = re.compile(r"^[a-zA-Z0-9_-]+$")

_DEFINED = re.compile(r'\bid="([^"]+)"')


def unique_ids(svg: str, prefix: str) -> str:
	"""Prefix every id the mark declares, and every url(#…) that points at one."""
	for ident in sorted(set(_DEFINED.findall(svg)), key=len, reverse=True):
		svg = svg.replace(f'id="{ident}"', f'id="{prefix}-{ident}"')
		svg = svg.replace(f"url(#{ident})", f"url(#{prefix}-{ident})")
	return svg


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
