"""Close a piece of work: everything the guards check that a machine can write.

    python3 scripts/close.py                      # the modules this change touches
    python3 scripts/close.py one one_mail         # these modules, by folder
    python3 scripts/close.py --looked one:copy,interface one_mail:copy

It regenerates docs/ (scripts/docs.py) and the overrides ledger
(scripts/overrides.py). For each module it touches, a version not yet
committed, or one dated today, takes the module's fingerprint and legal stamp
as they now are: a day's work in a module is one version (the changelog
skill), so an edit after `scripts/version.py`, or after today's version was
committed, no longer fails the version guard; add what changed to its words.
A module changed since an older version is named, with the command that
writes its next one. It says how many strings still want Arabic and German
(scripts/translate.py todo), when `bench` is on the path.

`--looked` is for after the commit: it records that you looked at those hand
points (ready.HAND) of a ready module on the commit now at HEAD, today. Only
name a point you looked at.
"""

import argparse
import datetime
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from onedesk.one import ready



def _git(*args: str) -> str:
	return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def changed() -> set[Path]:
	"""Every file this work changes: staged, unstaged and new."""
	out = set()
	for line in _git("status", "--porcelain", "--untracked-files=all").splitlines():
		path = line[3:].split(" -> ")[-1].strip('"')
		out.add((ROOT / path).resolve())
	return out


def by_folder() -> dict[str, str]:
	return {spec["folder"]: name for name, spec in ready.MODULES.items()}


def touched(paths: set[Path]) -> list[str]:
	"""The modules a change reaches, by name: any shipped file, or its changelog."""
	found = []
	for name, spec in ready.MODULES.items():
		folder = (ROOT / "onedesk" / spec["folder"]).resolve()
		if any(path.is_relative_to(folder) for path in paths) or any(
			path in paths for path in map(Path.resolve, ready.shipped(name))
		):
			found.append(name)
	return found


def committed(path: Path) -> bool:
	rel = str(path.relative_to(ROOT))
	return (
		bool(_git("ls-tree", "HEAD", "--", rel).strip())
		and not _git("status", "--porcelain", "--", rel).strip()
	)


def settle(name: str) -> str:
	"""The module's newest version, settled if it is not committed yet."""
	versions = ready.versions(name)
	if not versions:
		return f'{name}: no version yet; python3 scripts/version.py {ready.MODULES[name]["folder"]} minor "<title>"'
	newest = versions[0]
	now, stamp = ready.fingerprint(name), ready.legal(name)
	if newest["fingerprint"] == now and newest.get("legal", "") == stamp:
		return f"{name}: {newest['version']} is current"
	if committed(newest["path"]) and str(newest.get("date")) != datetime.date.today().isoformat():
		return (
			f"{name}: changed since {newest['version']}; "
			f'python3 scripts/version.py {ready.MODULES[name]["folder"]} <major|minor|fix> "<title>", then this again'
		)
	text = newest["path"].read_text(encoding="utf-8")
	text = re.sub(r"^fingerprint: .*$", f"fingerprint: {now}", text, count=1, flags=re.M)
	if "\nlegal: " in text.split("\n---\n", 1)[0] + "\n":
		text = re.sub(r"^legal: .*$", f"legal: {stamp}", text, count=1, flags=re.M)
	newest["path"].write_text(text, encoding="utf-8")
	if committed(newest["path"]) or _git("status", "--porcelain", "--", str(newest["path"].relative_to(ROOT))).startswith(" M"):
		return f"{name}: today's {newest['version']} takes fingerprint {now}; say what else changed in its words"
	return f"{name}: {newest['version']} takes fingerprint {now}"


def looked(pairs: list[str]) -> list[str]:
	"""Re-date the named hand looks to HEAD, today, keeping who looked: in
	each module's manifest.py, where its readiness is declared."""
	head = _git("rev-parse", "--short=12", "HEAD").strip()
	today = datetime.date.today().isoformat()
	folders = by_folder()
	said = []
	for pair in pairs:
		folder, _, points = pair.partition(":")
		name = folders.get(folder, folder)
		if name not in ready.MODULES:
			sys.exit(f"no module {folder}")
		manifest = ROOT / "onedesk" / ready.MODULES[name]["folder"] / "manifest.py"
		source = manifest.read_text(encoding="utf-8")
		for point in filter(None, points.split(",")):
			if point not in ready.HAND:
				sys.exit(f"{point} is not a hand point: {sorted(ready.HAND)}")
			pattern = re.compile(rf'("{point}": \{{"on": )"[\d-]+", "commit": "\w+"')
			if not pattern.search(source):
				sys.exit(f"{name} has no look at {point} to re-date")
			source = pattern.sub(rf'\1"{today}", "commit": "{head}"', source, count=1)
			said.append(f"{name}: looked at {point} on {head}")
		manifest.write_text(source, encoding="utf-8")
	return said


def run(*command: str) -> None:
	result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
	if result.returncode:
		print(result.stdout + result.stderr)
		sys.exit(f"{' '.join(command)} failed")


def untranslated() -> str:
	if not shutil.which("bench"):
		return "translations: bench is not on the path; run bench generate-pot-file and scripts/translate.py todo"
	subprocess.run(
		["bench", "generate-pot-file", "--app", "onedesk"], cwd=ROOT.parents[1], capture_output=True
	)
	out = subprocess.run(
		[sys.executable, "scripts/translate.py", "todo"], cwd=ROOT, capture_output=True, text=True
	)
	todo = Path("/tmp/one-todo.json")
	todo.write_text(out.stdout, encoding="utf-8")
	count = out.stdout.count('"msgid"')
	return (
		f"translations: {count} to write in {todo}, then scripts/translate.py apply"
		if count
		else "translations: none left"
	)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
	parser.add_argument(
		"modules", nargs="*", help="module folders; the ones this change touches when left out"
	)
	parser.add_argument(
		"--looked", nargs="+", metavar="FOLDER:POINT,POINT", help="re-date these hand looks to HEAD"
	)
	args = parser.parse_args()
	if args.looked:
		print("\n".join(looked(args.looked)))
		return
	run(sys.executable, "scripts/overrides.py")
	folders = by_folder()
	names = [folders.get(one, one) for one in args.modules] or touched(changed())
	for name in names:
		print(settle(name))
	run(sys.executable, "scripts/docs.py")
	print("docs/ and the overrides ledger: current")
	print(untranslated())


if __name__ == "__main__":
	main()
