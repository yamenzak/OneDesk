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
		"ready": True,
		# The points a guard can't settle, each as a person last looked at it
		# (HAND).
		"checked": {
			"copy": {"on": "2026-10-25", "commit": "064ce911f4ed", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-10-25", "commit": "064ce911f4ed", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-10-25", "commit": "064ce911f4ed", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-10-25", "commit": "064ce911f4ed", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-10-25", "commit": "064ce911f4ed", "by": "Claude, for Yamen"},
		},
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

# The fourteen points a module is held to before it is marked ready
# (docs/READY.md, The fourteen points), in that order: what each is called,
# and the guards that hold every module to it on every run.
READY = "tests/guards/test_ready.py::"
POINTS = {
	"home": {
		"title": "One home",
		"guards": (
			READY + "test_nothing_of_a_module_is_left_outside",
			READY + "test_nothing_outside_a_module_is_named_for_it",
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
		),
	},
	"versioned": {
		"title": "Versioned",
		"guards": (
			READY + "test_every_change_to_a_module_is_a_version",
			READY + "test_versions_follow_one_another",
			READY + "test_a_version_is_written_for_the_people_using_it",
		),
	},
	"whats_new": {
		"title": "What's New in the app",
		"guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",),
	},
	"documented": {
		"title": "Documented",
		"guards": (
			READY + "test_a_module_writes_only_agents_scratchpad_and_docs",
			READY + "test_every_help_page_is_listed_and_every_link_lands",
			READY + "test_a_help_page_names_no_code",
			READY + "test_a_help_page_is_headed_pictured_and_linked_soundly",
		),
	},
	"copy": {
		"title": "Copy",
		"guards": (
			"tests/guards/test_copy.py::test_a_heading_is_five_words_or_fewer",
			"tests/guards/test_copy.py::test_a_description_is_one_sentence",
			"tests/guards/test_copy.py::test_no_banned_word_is_shown",
		),
	},
	"roles": {
		"title": "Roles",
		"guards": (
			READY + "test_a_module_ships_its_roles",
			READY + "test_a_module_grants_through_abilities_alone",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"oneai": {
		"title": "OneAI",
		"guards": (READY + "test_a_module_reaches_every_change_through_oneai_or_says_why_not",),
	},
	"demo": {
		"title": "Demo and tests",
		"guards": (
			"tests/guards/test_coverage.py::test_no_module_has_more_left_to_cover_than_it_had",
			"tests/guards/test_demo.py::test_every_step_is_built_and_written_down",
		),
	},
	"notifications": {
		"title": "Notifications",
		"guards": (
			READY + "test_a_module_says_how_and_from_whom_it_tells_people",
			"tests/guards/test_notifications.py::test_every_type_sent_is_declared",
			READY + "test_a_module_leaves_roles_and_notifications_to_their_centers",
		),
	},
	"interface": {"title": "OneInterface pass", "guards": ()},
	"setup": {"title": "Setup steps", "guards": (READY + "test_a_module_says_what_setting_it_up_takes",)},
	"tour": {"title": "Tour", "guards": (READY + "test_a_module_ships_a_tour_of_its_screen",)},
	"settings": {"title": "Settings", "guards": (READY + "test_a_module_has_one_settings_dialog_and_one_foot",)},
	"legal": {
		"title": "Legal",
		"guards": (
			READY + "test_a_change_to_what_a_module_agrees_on_is_said",
			"tests/guards/test_legal.py::test_every_modules_legal_file_is_assembled",
		),
	},
}

# The points a guard holds only in part, and what a person looks at: before
# a module is marked ready, and again after a version that adds to it.
HAND = {
	"copy": "every heading, description and message it shows reads as the copy rules say, in English, Arabic and German",
	"demo": "the demo company uses every part of it and nothing in the demo makes it look wrong",
	"notifications": "it tells people what they need, on the channels that make sense, only to the roles that should hear it",
	"interface": "each screen, as each role, on a desktop and a phone: tokens only, frappe's controls, live where data changes, and the reader's formats",
	"legal": "what it does with data, read against what its clauses, subprocessors and optional services say",
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


def legal(module: str) -> str:
	"""What a module agrees on, as a version of it records it
	(one_legal/assemble.py `stamp`)."""
	from onedesk.one_legal import assemble

	return assemble.stamp(module)


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


def registry(module: str) -> list[dict]:
	"""Where a module stands on each point: the guards that hold it, and, for
	a point a person must look at, when they last did."""
	checked = MODULES[module].get("checked", {})
	return [
		{
			"point": key,
			"title": point["title"],
			"guards": point["guards"],
			"look": HAND.get(key),
			"checked": checked.get(key),
		}
		for key, point in POINTS.items()
	]
