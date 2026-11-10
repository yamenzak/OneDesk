"""The release build's base: frappe, erpnext and hrms as a bench, kept by
build.sh between releases on the same upstream commits. Run in Pilot's own
Python. `apps` prints the apps a base's bench.toml lists, `settle` makes a
bench unpacked from a base what `pilot init` would have left, without
cloning or building anything."""

import json
import sys
from pathlib import Path

from pilot.config import BenchConfig
from pilot.core.bench import Bench
from pilot.core.bench.initializer import BenchInitializer
from pilot.managers.environment import PythonEnvManager


def apps(path: Path) -> list[dict]:
	with BenchConfig.open(path, mode="raw") as raw:
		return [dict(one) for one in raw.get("apps", [])]


def settle(path: Path, held: list[dict]) -> None:
	with BenchConfig.open(path, mode="raw") as raw:
		listed = raw.setdefault("apps", [])
		listed.extend(one for one in held if not any(had.get("name") == one["name"] for had in listed))
	bench = Bench(path)
	bench.config.validate()
	start = BenchInitializer(bench)
	start._ensure_admin_password()
	start._ensure_database_credentials()
	start._install_system_packages()
	start._create_bench_structure()
	PythonEnvManager(bench).install_node()
	start._configure_redis()
	if bench.config.admin.enabled:
		start._ensure_admin_frontend(print)
	start._generate_process_config()
	bench.write_apps_txt()


if __name__ == "__main__":
	if sys.argv[1] == "apps":
		print(json.dumps(apps(Path(sys.argv[2]))))
	else:
		settle(Path(sys.argv[2]), json.loads(Path(sys.argv[3]).read_text()))
