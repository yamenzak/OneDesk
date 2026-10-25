"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under
`public/js/<folder>/` and `public/css/<folder>/`, and its screens under
`frontend/src/<screens>/`. OUTSIDE lists what still
sits elsewhere until it moves in; it only shrinks.
"""

import hashlib
import re
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

MODULES = {
	"OneMail": {
		"folder": "one_mail",
		"screens": "mail",
		"names": ("one_mail", "onemail"),
		"ready": False,
		# Its help pages in reading order, each with its icon (docs/).
		"help": (
			("overview", "info"),
			("your-addresses", "at-sign"),
			("reading-and-writing", "mail"),
			("connecting-a-mailbox", "plug"),
			("rules-and-out-of-office", "workflow"),
			("mail-on-records", "link"),
			("attachments-and-pictures", "paperclip"),
			("asking-oneai", "sparkles"),
			("who-can-do-what", "shield"),
			("settings", "settings"),
		),
	},
}

# Files named for a module that are not its own, and why.
SHARED = {
	"brand/onemail.svg": "every product's mark is drawn in brand/, into one sprite",
	"onedesk/templates/emails/one_mail.html": "the frame every mail One sends is laid in, OneMail's or not",
}

OUTSIDE = {
	"OneMail": [],
}


def files(module: str) -> list[Path]:
	"""Every file of a module: its folder, its static files, its screens, and
	what still sits outside."""
	found = []
	for root in places(module):
		if root.exists():
			found += [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
	found += [ROOT / one for one in OUTSIDE.get(module, [])]
	return sorted(found)


def places(module: str) -> list[Path]:
	"""Where a module's files may be: its folder, its static folders and its
	screens."""
	spec = MODULES[module]
	return [
		APP / spec["folder"],
		APP / "public" / "js" / spec["folder"],
		APP / "public" / "css" / spec["folder"],
		ROOT / "frontend" / "src" / spec["screens"],
	]


# What a version is taken over: what the module ships and its help pages,
# not what only we read or run (AGENTS.md, SCRATCHPAD.md, its versions, its
# tests, its checks and its part of the demo).
UNSHIPPED = ("AGENTS.md", "SCRATCHPAD.md", "checks.py", "demo.py")
KINDS = ("major", "minor", "fix")
HEAD = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def shipped(module: str) -> list[Path]:
	"""The files a module's version is taken over."""
	return [
		path
		for path in files(module)
		if path.name not in UNSHIPPED
		and "tests" not in path.parts
		and "changelog" not in path.parts
		and path.suffix not in (".pyc",)
	]


def fingerprint(module: str) -> str:
	"""Twelve hex characters over every shipped file's path and bytes, so it
	moves with any change to the module and nothing else."""
	digest = hashlib.sha256()
	for path in shipped(module):
		digest.update(str(path.relative_to(ROOT)).encode() + b"\0" + path.read_bytes() + b"\0")
	return digest.hexdigest()[:12]


def changelog(module: str) -> Path:
	return APP / MODULES[module]["folder"] / "docs" / "changelog"


def number(version: str) -> tuple[int, int, int]:
	major, minor, fix = (int(one) for one in version.split("."))
	return major, minor, fix


def versions(module: str) -> list[dict]:
	"""Every version of a module, newest first: its front matter (version,
	date, kind, title, fingerprint) and its words, read from
	docs/changelog/<version>.md."""
	found = []
	for path in changelog(module).glob("*.md"):
		text = path.read_text(encoding="utf-8")
		head = HEAD.match(text)
		if not head:
			raise ValueError(f"{path} has no front matter")
		said = dict(line.split(": ", 1) for line in head.group(1).splitlines())
		said["docs"] = [one.strip() for one in said.get("docs", "").split(",") if one.strip()]
		found.append({**said, "version": path.stem, "body": text[head.end() :].strip(), "path": path})
	return sorted(found, key=lambda one: number(one["version"]), reverse=True)


def current(module: str) -> str | None:
	"""A module's version: its newest changelog entry's."""
	found = versions(module)
	return found[0]["version"] if found else None


def help_pages(module: str) -> list[dict]:
	"""A module's help pages in reading order: id, icon, title (its first
	heading), the rest of its words, and where it is, which its pictures sit
	beside."""
	folder = APP / MODULES[module]["folder"] / "docs"
	found = []
	for page, icon in MODULES[module].get("help", ()):
		text = (folder / f"{page}.md").read_text(encoding="utf-8")
		title, _, body = text.partition("\n")
		found.append(
			{"id": page, "icon": icon, "title": title.lstrip("# ").strip(), "body": body.strip(), "path": folder / f"{page}.md"}
		)
	return found
