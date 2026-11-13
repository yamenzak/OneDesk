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


def high(text: str) -> list[int]:
	"""The lines of a source that set a z-index of 100 or more. Pure."""
	return [n for n, line in enumerate(text.splitlines(), 1) if NUMBER.search(line)]


def test_a_z_index_is_a_layer_or_local():
	found = {}
	for path in sources():
		name = path.relative_to(ROOT).as_posix()
		if name in CANVAS:
			continue
		lines = high(path.read_text(encoding="utf-8", errors="ignore"))
		if lines:
			found[name] = lines
	assert not found, f"use var(--one-layer-*) from tokens.css, or a local order under 100: {found}"


LAYERS = ["sticky", "panel", "frame", "backdrop", "dialog", "menu", "tooltip", "toast", "tour"]


def climbs(tokens: str) -> bool:
	"""Whether tokens.css names the layers in their order, each above the last. Pure."""
	order = re.findall(r"--one-layer-([a-z]+):\s*(\d+);", tokens)
	values = [int(value) for _, value in order]
	return [name for name, _ in order] == LAYERS and values == sorted(values) and len(set(values)) == len(values)


def test_the_layers_climb():
	assert climbs(TOKENS.read_text(encoding="utf-8"))


def gone(names, root: Path) -> list[str]:
	return sorted(name for name in names if not (root / name).exists())


def test_the_canvas_list_is_real():
	assert not gone(CANVAS, ROOT)


def test_the_layer_rules_catch_their_examples(tmp_path):
	assert high(".bar {\n\tz-index: 1050;\n}\n.tip { z-index: 5; }\n<div class='z-[999]'>") == [2, 5]
	assert high(".bar { z-index: var(--one-layer-dialog); }") == []
	good = "".join(f"--one-layer-{name}: {100 * n};" for n, name in enumerate(LAYERS, 1))
	assert climbs(good)
	assert not climbs(good.replace("--one-layer-tour: 900", "--one-layer-tour: 150"))
	(tmp_path / "here.vue").write_text("")
	assert gone({"here.vue", "gone.vue"}, tmp_path) == ["gone.vue"]
