"""Layers (onedesk/one_interface/AGENTS.md, Layers): what stacks over the page
says which layer it is on, so a bar, a dialog, a menu and a tour cannot end up
in each other's place. A z-index of ours is a `--one-layer-*` token (tokens.css)
or a local order inside its own part, which stays under 100."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHERE = [ROOT / "onedesk" / "public" / "css", ROOT / "onedesk" / "public" / "js", ROOT / "frontend" / "src"]
SUFFIXES = {".css", ".js", ".vue", ".ts"}
TOKENS = ROOT / "onedesk" / "public" / "css" / "one_interface" / "tokens.css"
# The slide canvas: a slide's own elements number one per element, inside the
# slide's stacking context (transform, z-index 0), and the handles sit above
# any count of them. Nothing here reaches past the canvas.
CANVAS = {
	"frontend/src/slide/components/ConnectorPorts.vue",
	"frontend/src/slide/components/MarqueeOverlay.vue",
	"frontend/src/slide/components/OverflowContentOverlay.vue",
	"frontend/src/slide/components/ResizeIndicator.vue",
	"frontend/src/slide/components/SelectionBox.vue",
	"frontend/src/slide/components/ShapeDrawOverlay.vue",
	"frontend/src/slide/components/SnapGuides.vue",
	"frontend/src/slide/utils/constants.js",
}
NUMBER = re.compile(r"(?:z-index\s*:|zIndex\s*[:=])\s*['\"`]?(\d{3,})|\bz-\[(\d{3,})\]")


def sources():
	for base in WHERE:
		for path in base.rglob("*"):
			if path.suffix in SUFFIXES and "node_modules" not in path.parts and path != TOKENS and ".bundle." not in path.name:
				yield path


def test_a_z_index_is_a_layer_or_local():
	found = {}
	for path in sources():
		name = path.relative_to(ROOT).as_posix()
		if name in CANVAS:
			continue
		lines = [n for n, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1) if NUMBER.search(line)]
		if lines:
			found[name] = lines
	assert not found, f"use var(--one-layer-*) from tokens.css, or a local order under 100: {found}"


def test_the_layers_climb():
	order = re.findall(r"--one-layer-([a-z]+):\s*(\d+);", TOKENS.read_text(encoding="utf-8"))
	assert [name for name, _ in order] == ["sticky", "panel", "frame", "backdrop", "dialog", "menu", "tooltip", "toast", "tour"], order
	values = [int(value) for _, value in order]
	assert values == sorted(values) and len(set(values)) == len(values), order


def test_the_canvas_list_is_real():
	assert all((ROOT / name).exists() for name in CANVAS)
