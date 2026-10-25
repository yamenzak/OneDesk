"""Which modules are ready for live, and where each one's files are
(docs/READY.md). Pure, so the guards read it without a site.

A module's files are its folder, its static files under `public/<folder>/`
and its screens under `frontend/src/<screens>/`. OUTSIDE lists what still
sits elsewhere until it moves in; it only shrinks.
"""

from pathlib import Path

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent

MODULES = {
	"OneMail": {"folder": "one_mail", "screens": "mail", "ready": False},
}

OUTSIDE = {
	"OneMail": [
		"onedesk/public/js/onemail_settings.js",
		"onedesk/public/js/mail_compose.js",
		"onedesk/public/js/rule_builder.js",
		"onedesk/public/js/record_mail.js",
		"onedesk/public/css/onemail_settings.css",
		"onedesk/public/css/record_mail.css",
		"onedesk/one/mail_templates.py",
	],
}


def files(module: str) -> list[Path]:
	"""Every file of a module: its folder, its static files, its screens, and
	what still sits outside."""
	spec = MODULES[module]
	found = []
	for root in (APP / spec["folder"], APP / "public" / spec["folder"], ROOT / "frontend" / "src" / spec["screens"]):
		if root.exists():
			found += [path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts]
	found += [ROOT / one for one in OUTSIDE.get(module, [])]
	return sorted(found)
