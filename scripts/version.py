"""Write a module's next version (docs/READY.md, Versions and What's New).

    python3 scripts/version.py one_mail release
    python3 scripts/version.py one_mail minor "Out of office in Arabic"

Before One is declared ready for production (ready.PRODUCTION), every
module stays at 1.0.0: `release` writes it, or brings the one there up to
date with today's date, the module's fingerprint and what it agrees on,
keeping its title and words. Change those by hand as the module changes.

From production on, the kind is major, minor or fix, picked by the biggest
change in it (docs/READY.md, Which number moves):

    major  something people already use works differently or is gone
    minor  something new they can do, and nothing they do changes; or a
           change to what the module adds to the agreements
    fix    it now does what Help already says; nothing new to learn

The new file in the module's docs/changelog/ carries today's date, the
kind, the title, the module's fingerprint and what it agrees on (its legal
stamp); its words are yours to write, for the people who use the module, in
English. tests/guards/test_ready.py fails until they are.
"""

import datetime
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.one import ready  # noqa: E402

UNWRITTEN = "Say here what people can do now, or what changed for them."


def _write(path: Path, kind: str, title: str, module: str, rest: str) -> Path:
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		"---\n"
		f"date: {datetime.date.today().isoformat()}\n"
		f"kind: {kind}\n"
		f"title: {title}\n"
		f"{rest}"
		f"fingerprint: {ready.fingerprint(module)}\n"
		f"legal: {ready.legal(module)}\n"
		"---\n\n",
		encoding="utf-8",
	)
	return path


def release(module: str) -> Path:
	"""1.0.0, written or brought up to date, before production."""
	path = ready.changelog(module) / "1.0.0.md"
	was = next((one for one in ready.versions(module) if one["version"] == "1.0.0"), None)
	docs = f"docs: {', '.join(was['docs'])}\n" if was and was["docs"] else ""
	_write(path, "major", was["title"] if was else module, module, docs)
	with path.open("a", encoding="utf-8") as out:
		out.write(f"{was['body'] if was else UNWRITTEN}\n")
	return path


def main(folder: str, kind: str, title: str = "") -> Path:
	module = next(name for name, spec in ready.MODULES.items() if spec["folder"] == folder)
	if not ready.PRODUCTION:
		if kind != "release":
			raise SystemExit("Before production every module stays at 1.0.0: python3 scripts/version.py <folder> release")
		return release(module)
	if kind not in ready.KINDS:
		raise SystemExit(f"the kind is one of {', '.join(ready.KINDS)}")
	now = ready.current(module)
	major, minor, fix = ready.number(now) if now else (0, 0, 0)
	following = {
		"major": f"{major + 1}.0.0",
		"minor": f"{major}.{minor + 1}.0",
		"fix": f"{major}.{minor}.{fix + 1}",
	}[kind]
	path = _write(ready.changelog(module) / f"{following}.md", kind, title, module, "")
	with path.open("a", encoding="utf-8") as out:
		out.write(f"{UNWRITTEN}\n")
	return path


if __name__ == "__main__":
	if len(sys.argv) not in (3, 4):
		raise SystemExit(__doc__)
	print(main(*sys.argv[1:]))
