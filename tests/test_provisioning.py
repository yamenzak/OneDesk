"""The step list, read back without a site.

A name in `ORDER` that is not a function in the module is an `AttributeError`
in the middle of somebody's provision, two minutes after they paid — and it is
invisible until then, because nothing imports the list at migrate time. AST
rather than an import, because the module imports frappe and this suite runs
without a site.
"""

import ast
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

STEPS = tree.APP / "one_admin" / "steps.py"
RUNNER = tree.APP / "one_admin" / "runner.py"


def _module() -> ast.Module:
	return ast.parse(STEPS.read_text(encoding="utf-8"))


def _order() -> list[str]:
	for node in _module().body:
		if isinstance(node, ast.Assign) and any(
			getattr(target, "id", "") == "ORDER" for target in node.targets
		):
			return [
				child.value
				for child in ast.walk(node.value)
				if isinstance(child, ast.Constant) and isinstance(child.value, str)
			]
	raise AssertionError("steps.py declares no ORDER")


def _walks() -> dict[str, list[str]]:
	"""Every kind of job and the steps it takes.

	Read from `WALKS` the same way `ORDER` is, because a rung of the ladder
	naming a step that is not there is the same bug as a provision doing it —
	except that it happens while somebody's workspace is being archived.
	"""
	for node in _module().body:
		if isinstance(node, ast.Assign) and any(
			getattr(target, "id", "") == "WALKS" for target in node.targets
		):
			found = {}
			for key, value in zip(node.value.keys, node.value.values):
				if isinstance(value, ast.Name):  # WALKS["Provision"] is ORDER
					found[key.value] = _order()
					continue
				found[key.value] = [
					child.value
					for child in ast.walk(value)
					if isinstance(child, ast.Constant) and isinstance(child.value, str)
				]
			return found
	raise AssertionError("steps.py declares no WALKS")


def _every_step() -> list[str]:
	seen = []
	for walk in _walks().values():
		for name in walk:
			if name not in seen:
				seen.append(name)
	return seen


def _functions() -> dict[str, ast.FunctionDef]:
	return {n.name: n for n in _module().body if isinstance(n, ast.FunctionDef)}


def test_there_is_an_order_to_check():
	assert len(_order()) >= 3


def test_every_kind_of_job_has_somewhere_to_start():
	walks = _walks()
	assert walks.get("Provision") == _order()
	for kind in ("Suspend", "Restore", "Archive", "Drop"):
		assert walks.get(kind), f"{kind} is a job kind with no steps"


def test_every_step_named_in_any_walk_exists():
	missing = [name for name in _every_step() if name not in _functions()]
	assert not missing, (
		f"{missing} are named in WALKS and are not functions in steps.py. That is "
		"an AttributeError in the middle of a provision, minutes after somebody "
		"paid — or in the middle of an archive."
	)


def test_every_step_takes_the_job_and_the_tenant():
	for name in _every_step():
		args = [a.arg for a in _functions()[name].args.args]
		assert args == ["job", "tenant"], f"{name} takes {args}"


def test_no_step_is_declared_and_then_never_run():
	"""A function in steps.py that ORDER does not name is dead or forgotten.

	Helpers are named with a leading underscore, which is how the two are told
	apart — so a public one named in no walk is the interesting case.
	"""
	public = {name for name in _functions() if not name.startswith("_")}
	assert public == set(_every_step()), (
		f"in steps.py but in no walk: {sorted(public - set(_every_step()))}"
	)


def test_the_runner_stops_rather_than_retrying_forever():
	source = RUNNER.read_text(encoding="utf-8")
	assert "GIVE_UP_AFTER" in source
	assert "BACKOFF" in source


def test_a_tenant_site_runs_no_provisioning():
	"""The cron is registered on every site. It has to refuse on most of them."""
	source = RUNNER.read_text(encoding="utf-8")
	tick = source[source.index("def tick()") : source.index("def _due()")]
	assert "site.is_admin()" in tick, "tick() must ask what kind of site this is first"
