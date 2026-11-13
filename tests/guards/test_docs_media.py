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
	return sorted(path for kind in ("help", "updates") for path in APP.glob(f"*/{kind}") if path.is_dir())


def media() -> list[Path]:
	return sorted(path for folder in docs() for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in KINDS)


def named() -> dict[Path, list[str]]:
	"""Every picture a page or a version names: where it is, by whom."""
	found = {}
	for folder in docs():
		for page in folder.rglob("*.md"):
			for picture in pictures_in(page, page.read_text(encoding="utf-8")):
				found.setdefault(picture, []).append(str(page.relative_to(ROOT)))
	return found


def pictures_in(page: Path, text: str) -> list[Path]:
	"""The pictures a page's Markdown names, where they would be. Pure."""
	return [(page.parent / one.group(2)).resolve() for one in PICTURE.finditer(text)]


def missing(named: dict[Path, list[str]]) -> list[str]:
	"""The pictures named that are not there, with the first page naming
	each."""
	return [f"{by[0]} names {path.relative_to(APP) if path.is_relative_to(APP) else path}" for path, by in named.items() if not path.exists()]


def left_over(media: list[Path], shown: set[Path]) -> list[Path]:
	"""The pictures and clips nothing shows. Pure."""
	return [path for path in media if path.resolve() not in shown]


STRANGE = {".mp4", ".webm", ".mov", ".bmp", ".tiff", ".svg"}


def too_large(path: Path, size: int) -> bool:
	"""Whether a picture is over 1 MB, or a clip over 4 MB. Pure."""
	return size > (LARGEST_CLIP if path.suffix.lower() == ".gif" else LARGEST_PICTURE)


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
	gone = missing(named())
	assert not gone, "\n".join(gone)


def test_every_picture_is_shown_somewhere():
	left = [str(path.relative_to(ROOT)) for path in left_over(media(), set(named()))]
	assert not left, "Nothing shows these; delete them or name them in a page:\n" + "\n".join(left)


def test_pictures_are_small_and_of_a_kind_every_browser_shows():
	for folder in docs():
		strange = [str(path.relative_to(ROOT)) for path in folder.rglob("*") if path.suffix.lower() in STRANGE]
		assert not strange, "Help shows .png, .jpg, .webp and .gif only:\n" + "\n".join(strange)
	big = [
		f"{path.relative_to(ROOT)}: {path.stat().st_size // 1024} KB"
		for path in media()
		if too_large(path, path.stat().st_size)
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


def test_the_picture_rules_catch_their_examples(tmp_path):
	page = tmp_path / "help" / "stock.md"
	page.parent.mkdir()
	(tmp_path / "help" / "there.png").write_bytes(b"x")
	(tmp_path / "help" / "unshown.png").write_bytes(b"x")
	said = pictures_in(page, "![The list](there.png) and ![The form](gone.png)")
	assert said == [tmp_path / "help" / "there.png", tmp_path / "help" / "gone.png"]
	assert missing({path: ["help/stock.md"] for path in said}) == [f"help/stock.md names {tmp_path / 'help' / 'gone.png'}"]
	assert left_over([tmp_path / "help" / "there.png", tmp_path / "help" / "unshown.png"], set(said)) == [tmp_path / "help" / "unshown.png"]
	assert ".svg" in STRANGE and ".png" not in STRANGE
	assert too_large(Path("a.png"), LARGEST_PICTURE + 1) and not too_large(Path("a.gif"), LARGEST_PICTURE + 1)
	assert too_large(Path("a.gif"), LARGEST_CLIP + 1)
