"""Every private app under `private/` made an app of a bench, installed on no
site. Each is copied to the bench's `private-apps/<app>` with a repository
of its own and linked into `apps/` the way Pilot links a local checkout, so
Pilot lists it and never updates it; it is installed into the bench's
Python, listed in apps.txt and bench.toml, and its assets built. A
workspace's Install App job installs it on that workspace's site.

Run in Pilot's Python by build.sh, by first-boot.sh and by the box's agent
when it builds a release from its commits. Before anything is installed it
refuses a private app that would break the bench (`checked`). It globs the
folder and names none of them."""

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from upload import HOOK, assigned

HELD = "private-apps"
LEFT_OUT = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "node_modules")


def scrub(name: str) -> str:
	"""A module name as frappe.scrub keys `frappe.local.module_app`. Pure."""
	return name.strip().replace(" ", "_").replace("-", "_").lower()


def found(root: Path) -> list[Path]:
	"""Every folder under `root/private`, sorted."""
	folder = root / "private"
	return sorted(path for path in folder.iterdir() if path.is_dir()) if folder.is_dir() else []


def modules(app: Path) -> set[str]:
	"""An app's Frappe modules, from its modules.txt, scrubbed."""
	listed = app / app.name / "modules.txt"
	return {scrub(line) for line in listed.read_text(encoding="utf-8").splitlines() if line.strip()} if listed.is_file() else set()


def project(app: Path) -> str:
	"""The package name its pyproject.toml gives, as Python imports it."""
	try:
		return scrub(tomllib.loads((app / "pyproject.toml").read_text(encoding="utf-8")).get("project", {}).get("name") or "")
	except (OSError, tomllib.TOMLDecodeError):
		return ""


def problems(app: Path, python: set, held: set) -> list[str]:
	"""What stops this private app joining a bench whose Python packages are
	`python` and whose Frappe modules are `held`: a module name is
	bench-wide, so one already taken breaks the other app's imports on every
	site. Empty when it may join."""
	name = app.name
	hooks = app / name / "hooks.py"
	if not (name[:1].isalpha() and name.isidentifier() and name == name.lower()):
		return [f"private/{name}: an app's folder is its Python package, so it is lower case letters, digits and underscores"]
	if not hooks.is_file():
		return [f"private/{name} is not a Frappe app: there is no {name}/hooks.py"]
	wrong = []
	about = assigned(hooks.read_text(encoding="utf-8")).get(HOOK)
	if not isinstance(about, dict) or not about.get("title"):
		wrong.append(f"private/{name}: its hooks.py has no {HOOK} with a title, so it would be an app nobody could claim")
	if project(app) != name:
		wrong.append(f"private/{name}: its pyproject.toml must name the project {name}, not {project(app) or 'nothing'}")
	if name in python:
		wrong.append(f"private/{name}: {name} is already a Python package on the bench")
	if not modules(app):
		wrong.append(f"private/{name}: {name}/modules.txt lists no module")
	clash = sorted(modules(app) & held)
	if clash:
		wrong.append(f"private/{name}: its modules {', '.join(clash)} are already another app's on the bench, and a module name is bench-wide")
	return wrong


def checked(apps: list[Path], python: set, held: set) -> list[str]:
	"""Every private app against the bench and against the ones before it. Pure over the tree."""
	python, held, wrong = set(python), set(held), []
	for app in apps:
		wrong += problems(app, python, held)
		python.add(app.name)
		held |= modules(app)
	return wrong


def taken(bench: Path, leaving: set) -> tuple[set, set]:
	"""The Python packages and Frappe modules a bench already has, but for the
	private apps about to be placed."""
	apps = [path for path in sorted((bench / "apps").iterdir()) if path.is_dir() and path.name not in leaving]
	python = {path.name for path in apps}
	for packages in (bench / "env").glob("lib/python*/site-packages"):
		python |= {path.name.removesuffix(".py") for path in packages.iterdir() if not path.name.endswith((".dist-info", ".pth", ".egg-info")) and not path.name.startswith("_")}
	held = set().union(*(modules(path) for path in apps))
	return python, held


def place(bench, app: Path, skip_assets: bool) -> None:
	from pilot.config import AppConfig, BenchConfig
	from pilot.core.app import App
	from pilot.core.app.validator import Validator
	from pilot.managers.environment import PythonEnvManager

	name = app.name
	source = bench.path / HELD / name
	shutil.rmtree(source, ignore_errors=True)
	shutil.copytree(app, source, ignore=LEFT_OUT)
	git = ["git", "-C", str(source), "-c", "user.name=One", "-c", "user.email=hello@4dl.app"]
	for step in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", f"{name} as this release holds it"]):
		subprocess.run([*git, *step], check=True)
	with BenchConfig.open(bench.path, mode="raw") as raw:
		listed = raw.setdefault("apps", [])
		listed[:] = [one for one in listed if one.get("name") != name] + [{"name": name, "path": str(source)}]
	linked = App(AppConfig(name=name, repo="", branch="", path=str(source)), bench)
	try:
		linked.link()
		Validator(linked).validate()
		linked._install_into_environment()
		linked._register()
		if not skip_assets and (source / name / "public").is_dir():
			PythonEnvManager(bench).build_assets_for_app(linked)
	except Exception as raised:
		raise SystemExit(f"private app refused: private/{name} does not install on the bench: {raised}") from raised
	print(f"{name}: on the bench, installed on no site")


def make(bench_path: Path, root: Path, skip_assets: bool) -> None:
	from pilot.core.bench import Bench

	apps = found(root)
	wrong = checked(apps, *taken(bench_path, {app.name for app in apps}))
	if wrong:
		raise SystemExit("\n".join(f"private app refused: {one}" for one in wrong))
	bench = Bench(bench_path)
	for app in apps:
		place(bench, app, skip_assets)


if __name__ == "__main__":
	make(Path(sys.argv[1]), Path(sys.argv[2]), "--skip-assets" in sys.argv[3:])
