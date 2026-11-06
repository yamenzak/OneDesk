"""Write a module's next version (docs/READY.md, Versions and What's New).

    python3 scripts/version.py one_mail minor "Out of office in Arabic"

The kind is major, minor or fix, picked by the biggest
change in it (docs/READY.md, Which number moves):

    major  something people already use works differently or is gone
    minor  something new they can do, and nothing they do changes; or a
           change to what the module adds to the agreements
    fix    it now does what Help already says; nothing new to learn

A day's work in a module is one version: when the module already has one
dated today, a smaller or equal kind is refused (add to its words instead),
and a bigger kind renumbers today's, keeping its words.

The new file in the module's docs/changelog/ carries today's date, the
kind, the title, the module's fingerprint and what it agrees on (its legal
stamp); its words are yours to write, for the people who use the module, in
English. tests/guards/test_ready.py fails until they are.
"""

import datetime
import re
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


def main(folder: str, kind: str, title: str) -> Path:
	module = next(name for name, spec in ready.MODULES.items() if spec["folder"] == folder)
	if kind not in ready.KINDS:
		raise SystemExit(f"the kind is one of {', '.join(ready.KINDS)}")
	versions = ready.versions(module)
	today = datetime.date.today().isoformat()
	todays = versions[0] if versions and str(versions[0].get("date")) == today else None
	if todays and ready.KINDS.index(kind) >= ready.KINDS.index(todays["kind"]):
		raise SystemExit(
			f"{module} already has today's version, {todays['version']} ({todays['kind']}): a day's work is one version. "
			f"Add what changed to its words, then python3 scripts/close.py."
		)
	before = versions[1] if todays and len(versions) > 1 else (None if todays else (versions[0] if versions else None))
	now = before["version"] if before else None
	major, minor, fix = ready.number(now) if now else (0, 0, 0)
	following = {
		"major": f"{major + 1}.0.0",
		"minor": f"{major}.{minor + 1}.0",
		"fix": f"{major}.{minor}.{fix + 1}",
	}[kind]
	if todays:
		text = todays["path"].read_text(encoding="utf-8")
		text = re.sub(r"^kind: .*$", f"kind: {kind}", text, count=1, flags=re.M)
		text = re.sub(r"^title: .*$", f"title: {title}", text, count=1, flags=re.M)
		path = ready.changelog(module) / f"{following}.md"
		path.write_text(text, encoding="utf-8")
		todays["path"].unlink()
		return path
	path = _write(ready.changelog(module) / f"{following}.md", kind, title, module, "")
	with path.open("a", encoding="utf-8") as out:
		out.write(f"{UNWRITTEN}\n")
	return path


if __name__ == "__main__":
	if len(sys.argv) != 4:
		raise SystemExit(__doc__)
	print(main(*sys.argv[1:]))
