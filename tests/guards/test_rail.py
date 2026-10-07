"""Every app of ours has a tile on the rail.

frappe's rail lists exactly what an app's Dock record names, so a sidebar the
record leaves out still opens by its address but has no tile, and nothing on
the rail is lit while it is open. OneMail was left out this way.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import tree

DOCK = tree.APP / "dock" / "onedesk" / "onedesk.json"


def test_every_sidebar_of_ours_has_a_tile_on_the_rail():
	named = {row["link_to"] for row in json.loads(DOCK.read_text())["items"] if row["link_type"] == "Sidebar"}
	ours = {json.loads(path.read_text())["name"] for path in tree.APP.glob("*/sidebar/*/*.json")}
	assert not ours - named, f"sidebars with no tile on the rail: {sorted(ours - named)}"
