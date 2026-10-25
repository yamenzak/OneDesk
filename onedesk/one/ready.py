"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under
`public/js/<folder>/` and `public/css/<folder>/`, and its screens under
`frontend/src/<screens>/`. OUTSIDE lists what still
sits elsewhere until it moves in; it only shrinks.
"""

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

MODULES = {
	"OneMail": {"folder": "one_mail", "screens": "mail", "names": ("one_mail", "onemail"), "ready": False},
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
