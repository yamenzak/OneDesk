"""Push every shipped screen document into a site.

**`bench migrate` does not do this, and that is the whole reason this exists.**
A Workspace, Sidebar, Number Card or Dashboard Chart that ships as JSON is
imported the first time and then left alone: edit the file, migrate, and the
site still shows what it showed before — no error, no warning, nothing. Bumping
`modified` does not help either; it was tried. Only a forced reload re-reads the
file.

So an afternoon can go into wondering why a rail label will not change. Run
this after editing anything under a module's `workspace/`, `sidebar/`,
`number_card/` or `dashboard_chart/` folder.

    python scripts/reload.py                     every module
    python scripts/reload.py one_admin one_hr    only these
"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tree

SITE = "onedesk.localhost"
BENCH = Path("/home/frappe/bench1")

#: The folders that hold a screen document, and the doctype each one is.
KINDS = {
	"workspace": "Workspace",
	"sidebar": "Sidebar",
	"number_card": "Number Card",
	"dashboard_chart": "Dashboard Chart",
}


def shipped(only: list[str]) -> list[tuple[str, str, str]]:
	"""Every (module, kind, name) this app ships a screen document for."""
	found = []
	for module in sorted(p.name for p in tree.APP.iterdir() if p.is_dir()):
		if only and module not in only:
			continue
		for kind in KINDS:
			folder = tree.APP / module / kind
			if not folder.is_dir():
				continue
			for one in sorted(folder.iterdir()):
				if one.is_dir() and (one / f"{one.name}.json").exists():
					found.append((module, kind, one.name))
	return found


def main() -> int:
	only = [a for a in sys.argv[1:] if not a.startswith("-")]
	work = shipped(only)
	if not work:
		print("nothing to reload")
		return 0

	lines = [
		"import frappe",
		f"frappe.init(site={SITE!r})",
		"frappe.connect()",
		# Without this the reload refuses: frappe will not overwrite a standard
		# document outside a migration.
		"frappe.flags.in_migrate = True",
	]
	for module, kind, name in work:
		lines.append(f"frappe.reload_doc({module!r}, {kind!r}, {name!r}, force=True)")
	lines.append("frappe.db.commit()")

	script = BENCH / "sites" / "_one_reload.py"
	script.write_text("\n".join(lines) + "\n")
	try:
		done = subprocess.run(
			["su", "frappe", "-c", f"cd {BENCH}/sites && {BENCH}/env/bin/python {script}"],
			capture_output=True,
			text=True,
		)
	finally:
		script.unlink(missing_ok=True)

	if done.returncode:
		print(done.stdout[-2000:], done.stderr[-2000:], sep="\n")
		return 1
	for module, kind, name in work:
		print(f"  {module}/{kind}/{name}")
	print(f"reloaded {len(work)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
