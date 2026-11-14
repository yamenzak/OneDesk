"""How far an agent goes with each action, a call REACH names, a tool
TOOLS lists, a planner PLANS names or a job WATCH names: Do it, Draft or
Ask First, declared in each app's agent.py as LEVELS, and Ask First where
it is not (one_ai/AGENTS.md, The agents)."""

import ast
import importlib
from pathlib import Path

DO_IT, DRAFT, ASK_FIRST = "Do it", "Draft", "Ask First"
LEVELS = (DO_IT, DRAFT, ASK_FIRST)
CAUTIOUS = ASK_FIRST

STAGES = ("parties", "money", "rest")
"""Intake's passes over an understood reading (reading/matters.py act_now),
at which a planner in PLANS runs (work.py)."""

ROUNDS = ("hourly",)
"""When a job in WATCH runs without a record: on the scheduler's round."""

WHEN = ("after_insert", "on_update", "on_submit", "on_cancel", *ROUNDS)
"""When a job in WATCH runs: a record's own event, or a round."""

EVERY_AGENT = ("plan", "watched")
"""The tools every agent has beside its own TOOLS (work.py): its planners on
a document handed to it, and one of its jobs."""


def declared(app: str) -> dict:
	try:
		agent = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return {}
	return dict(getattr(agent, "LEVELS", {}) or {})


def of(app: str, action: str) -> str:
	"""The level an app's agent works at for one action: as the workspace
	chose in AICenter (workspace.py), else as declared, else Ask First."""
	from onedesk.one_ai.agents import workspace

	level = workspace.chosen_level(app, action) if action in actions(app) else None
	if level in LEVELS:
		return level
	level = declared(app).get(action)
	return level if level in LEVELS else CAUTIOUS


def actions(app: str) -> tuple[str, ...]:
	"""Every action an app's agent has: each call REACH names, then each
	tool, each planner and each job."""
	try:
		agent = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return ()
	return tuple(dict.fromkeys([*getattr(agent, "REACH", {}), *getattr(agent, "TOOLS", ()), *getattr(agent, "PLANS", {}), *getattr(agent, "WATCH", {})]))


def label(app: str, action: str) -> str:
	"""An action as people read it, in their language: its LABELS entry."""
	try:
		agent = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return action
	held = (getattr(agent, "LABELS", {}) or {}).get(action)
	return str(held) if held else action


def unlevelled(source: str) -> list[str]:
	"""Given an agent.py: a REACH call, a TOOLS entry, a PLANS planner or a
	WATCH job without a level or a label, a level that is none of the three,
	a level or a label on something that is no action, a level on a call
	NOT_FOR_AI keeps from OneAI, a tool agent.py lacks, a planner at no
	stage of STAGES or outside onedesk, a job at no time of WHEN or outside
	onedesk, a wait on no planner, or a wake on no tool it has. Pure."""
	said = _said(source)
	labels = _labelled(source)
	reach, refused, tools, levels = said.get("REACH", {}), said.get("NOT_FOR_AI", {}), said.get("TOOLS", ()), said.get("LEVELS", {})
	plans, watch, waits, wakes = said.get("PLANS", {}), said.get("WATCH", {}), said.get("WAITS", {}), said.get("WAKES", {})
	functions = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
	actions = set(reach) | set(tools) | set(plans) | set(watch)
	wrong = [f"{one} has no level" for one in sorted(actions - set(levels))]
	wrong += [f"{one}'s level {levels[one]!r} is not one of {LEVELS}" for one in sorted(levels) if levels[one] not in LEVELS]
	wrong += [f"{one} has a level but is no action" for one in sorted(set(levels) - actions)]
	wrong += [f"{one} is not for OneAI, so it has no level" for one in sorted(set(levels) & set(refused))]
	wrong += [f"the tool {one} is not in agent.py" for one in sorted(set(tools) - functions)]
	wrong += [f"{one} has no label in LABELS" for one in sorted(actions - set(labels))]
	wrong += [f"{one} has a label but is no action" for one in sorted(set(labels) - actions)]
	wrong += [f"{one}'s stage {plans[one][0]!r} is not one of {STAGES}" for one in sorted(plans) if plans[one][0] not in STAGES]
	wrong += [f"{one}'s planner {plans[one][1]!r} is not in onedesk" for one in sorted(plans) if not str(plans[one][1]).startswith("onedesk.")]
	wrong += [f"{one} runs {watch[one][1]!r}, which is not one of {WHEN}" for one in sorted(watch) if watch[one][1] not in WHEN]
	wrong += [f"{one}'s job {watch[one][2]!r} is not in onedesk" for one in sorted(watch) if not str(watch[one][2]).startswith("onedesk.")]
	wrong += [f"{one} waits but is no planner in PLANS" for one in sorted(set(waits) - set(plans))]
	wrong += [f"a {kind} wakes {tool!r}, which is no tool it has" for kind, tool in sorted(wakes.items()) if tool not in (*tools, *EVERY_AGENT)]
	return wrong


def _labelled(source: str) -> set[str]:
	"""The actions LABELS names, each beside its words (_lt)."""
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "LABELS" and isinstance(node.value, ast.Dict):
			return {ast.literal_eval(key) for key in node.value.keys if key is not None}
	return set()


def _said(source: str) -> dict:
	found = {}
	for node in ast.parse(source).body:
		if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
			try:
				found[node.targets[0].id] = ast.literal_eval(node.value)
			except ValueError:
				continue
	return found


def every(folders: Path) -> dict[str, list[str]]:
	"""What is wrong with each app's levels, by folder, and each planner
	PLANS or job WATCH names that is no function of ours."""
	out = {}
	for path in sorted(folders.glob("*/agent.py")):
		source = path.read_text(encoding="utf-8")
		said = _said(source)
		wrong = unlevelled(source) + [f"{one}'s planner {at} is no function" for one, (_stage, at) in sorted(said.get("PLANS", {}).items()) if not _defined(folders, at)]
		wrong += [f"{one}'s job {at} is no function" for one, (_doctype, _when, at) in sorted(said.get("WATCH", {}).items()) if not _defined(folders, at)]
		if wrong:
			out[path.parent.name] = wrong
	return out


def _defined(folders: Path, dotted: str) -> bool:
	module, _dot, function = str(dotted).rpartition(".")
	path = folders.parent / (module.replace(".", "/") + ".py")
	return path.exists() and function in {node.name for node in ast.parse(path.read_text(encoding="utf-8")).body if isinstance(node, ast.FunctionDef)}
