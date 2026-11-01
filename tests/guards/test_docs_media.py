"""Help's and What's New's pictures and clips (one/media.py, the docs skill):
each one a page or a version shows, none left over, every one there, a
picture small enough to open at once and a clip no longer than nine
seconds."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "onedesk"
SOURCE = (APP / "one" / "media.py").read_text()
KINDS = set(re.findall(r'"(\.\w+)": "image/', SOURCE))
LONGEST = float(re.search(r"^LONGEST_CLIP = ([\d.]+)", SOURCE, re.M).group(1))
PICTURE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
LARGEST_PICTURE = 1024 * 1024
LARGEST_CLIP = 4 * 1024 * 1024


def docs() -> list[Path]:
	return sorted(path for path in APP.glob("*/docs") if path.is_dir())


def media() -> list[Path]:
	return sorted(path for folder in docs() for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in KINDS)


def named() -> dict[Path, list[str]]:
	"""Every picture a page or a version names: where it is, by whom."""
	found = {}
	for folder in docs():
		for page in folder.rglob("*.md"):
			for one in PICTURE.finditer(page.read_text(encoding="utf-8")):
				found.setdefault((page.parent / one.group(2)).resolve(), []).append(str(page.relative_to(ROOT)))
	return found


def seconds(path: Path) -> float:
	"""How long a GIF plays once: the sum of its frames' delays, read from
	each frame's graphic control extension. Pure."""
	data = path.read_bytes()
	total, at = 0, 0
	while True:
		at = data.find(b"\x21\xf9\x04", at)
		if at < 0:
			return total / 100
		total += int.from_bytes(data[at + 4 : at + 6], "little") or 10
		at += 8


def test_every_picture_a_page_names_is_there():
	missing = [f"{by[0]} names {path.relative_to(APP) if path.is_relative_to(APP) else path}" for path, by in named().items() if not path.exists()]
	assert not missing, "\n".join(missing)


def test_every_picture_is_shown_somewhere():
	shown = set(named())
	left = [str(path.relative_to(ROOT)) for path in media() if path.resolve() not in shown]
	assert not left, "Nothing shows these; delete them or name them in a page:\n" + "\n".join(left)


def test_pictures_are_small_and_of_a_kind_every_browser_shows():
	for folder in docs():
		strange = [str(path.relative_to(ROOT)) for path in folder.rglob("*") if path.suffix.lower() in {".mp4", ".webm", ".mov", ".bmp", ".tiff", ".svg"}]
		assert not strange, "Help shows .png, .jpg, .webp and .gif only:\n" + "\n".join(strange)
	big = [
		f"{path.relative_to(ROOT)}: {path.stat().st_size // 1024} KB"
		for path in media()
		if path.stat().st_size > (LARGEST_CLIP if path.suffix.lower() == ".gif" else LARGEST_PICTURE)
	]
	assert not big, "Too large (a picture 1 MB, a clip 4 MB):\n" + "\n".join(big)


def test_a_clip_plays_for_nine_seconds_at_most():
	long = [f"{path.relative_to(ROOT)}: {seconds(path):.1f} s" for path in media() if path.suffix.lower() == ".gif" and seconds(path) > LONGEST]
	assert not long, f"A clip is {LONGEST:g} seconds at most:\n" + "\n".join(long)


def test_reading_a_clip_s_length():
	frame = b"\x21\xf9\x04\x00\x32\x00\x00\x00"  # 0.5 s
	path = Path(__file__).with_name("_clip.gif")
	try:
		path.write_bytes(b"GIF89a" + frame * 3)
		assert seconds(path) == 1.5
	finally:
		path.unlink(missing_ok=True)
