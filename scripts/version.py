"""Write a module's next version (docs/READY.md, Versions and What's New).

    python3 scripts/version.py one_mail minor "Out of office in Arabic"

The kind is major, minor or fix, picked by the biggest change in it
(docs/READY.md, Which number moves):

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


def main(folder: str, kind: str, title: str) -> Path:
	module = next(name for name, spec in ready.MODULES.items() if spec["folder"] == folder)
	if kind not in ready.KINDS:
		raise SystemExit(f"the kind is one of {', '.join(ready.KINDS)}")
	now = ready.current(module)
	major, minor, fix = ready.number(now) if now else (0, 0, 0)
	following = {
		"major": f"{major + 1}.0.0",
		"minor": f"{major}.{minor + 1}.0",
		"fix": f"{major}.{minor}.{fix + 1}",
	}[kind]
	path = ready.changelog(module) / f"{following}.md"
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(
		"---\n"
		f"date: {datetime.date.today().isoformat()}\n"
		f"kind: {kind}\n"
		f"title: {title}\n"
		f"fingerprint: {ready.fingerprint(module)}\n"
		f"legal: {ready.legal(module)}\n"
		"---\n\n"
		f"{UNWRITTEN}\n",
		encoding="utf-8",
	)
	return path


if __name__ == "__main__":
	if len(sys.argv) != 4:
		raise SystemExit(__doc__)
	print(main(*sys.argv[1:]))
