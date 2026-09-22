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
	"dock": "Dock",
	"workspace": "Workspace",
	"sidebar": "Sidebar",
	"number_card": "Number Card",
	"dashboard_chart": "Dashboard Chart",
}


def shipped(only: list[str]) -> list[Path]:
	"""Every screen document this app ships, as a path to its JSON.

	Two shapes, because Frappe has two. A workspace, sidebar, number card or
	chart lives under its module — `one_admin/workspace/one_admin/`. A dock does
	not: it is one per app and sits at the app root, which is why an earlier
	version of this that only walked modules reloaded everything except the dock
	and said nothing about it.
	"""
	found = []
	for kind in KINDS:
		for folder in [tree.APP / kind, *(p / kind for p in sorted(tree.APP.iterdir()) if p.is_dir())]:
			if not folder.is_dir():
				continue
			owner = folder.parent.name
			if only and owner not in only and owner != tree.APP.name:
				continue
			for one in sorted(folder.iterdir()):
				if one.is_dir() and (one / f"{one.name}.json").exists():
					found.append(one / f"{one.name}.json")
	return sorted(set(found))


def main() -> int:
	only = [a for a in sys.argv[1:] if not a.startswith("-")]
	work = shipped(only)
	if not work:
		print("nothing to reload")
		return 0

	lines = [
		"import frappe",
		"from frappe.modules.import_file import import_file_by_path",
		f"frappe.init(site={SITE!r})",
		"frappe.connect()",
		# Without this the import refuses: frappe will not overwrite a standard
		# document outside a migration.
		"frappe.flags.in_migrate = True",
	]
	for path in work:
		lines.append(f"import_file_by_path({str(path)!r}, force=True, reset_permissions=False)")
	lines.append("frappe.cache.delete_value('dock_layers')")
	lines.append("frappe.clear_cache()")
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
	for path in work:
		print(f"  {path.relative_to(tree.APP)}")
	print(f"reloaded {len(work)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
