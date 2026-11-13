"""How far an agent goes with each action, a call REACH names or a tool
TOOLS lists: Do it, Draft or Ask First, declared in each app's agent.py as
LEVELS, and Ask First where it is not (one_ai/AGENTS.md, The agents)."""

import ast
import importlib
from pathlib import Path

DO_IT, DRAFT, ASK_FIRST = "Do it", "Draft", "Ask First"
LEVELS = (DO_IT, DRAFT, ASK_FIRST)
CAUTIOUS = ASK_FIRST


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
	"""Every action an app's agent has: each call REACH names, then each tool."""
	try:
		agent = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return ()
	return tuple(dict.fromkeys([*getattr(agent, "REACH", {}), *getattr(agent, "TOOLS", ())]))


def label(app: str, action: str) -> str:
	"""An action as people read it, in their language: its LABELS entry."""
	try:
		agent = importlib.import_module(f"onedesk.{app}.agent")
	except ModuleNotFoundError:
		return action
	held = (getattr(agent, "LABELS", {}) or {}).get(action)
	return str(held) if held else action


def unlevelled(source: str) -> list[str]:
	"""Given an agent.py: a REACH call or a TOOLS entry without a level or
	a label, a level that is none of the three, a level or a label on
	something that is no action, a level on a call NOT_FOR_AI keeps from
	OneAI, or a tool agent.py lacks. Pure."""
	said = _said(source)
	labels = _labelled(source)
	reach, refused, tools, levels = said.get("REACH", {}), said.get("NOT_FOR_AI", {}), said.get("TOOLS", ()), said.get("LEVELS", {})
	functions = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
	actions = set(reach) | set(tools)
	wrong = [f"{one} has no level" for one in sorted(actions - set(levels))]
	wrong += [f"{one}'s level {levels[one]!r} is not one of {LEVELS}" for one in sorted(levels) if levels[one] not in LEVELS]
	wrong += [f"{one} has a level but is no action" for one in sorted(set(levels) - actions)]
	wrong += [f"{one} is not for OneAI, so it has no level" for one in sorted(set(levels) & set(refused))]
	wrong += [f"the tool {one} is not in agent.py" for one in sorted(set(tools) - functions)]
	wrong += [f"{one} has no label in LABELS" for one in sorted(actions - set(labels))]
	wrong += [f"{one} has a label but is no action" for one in sorted(set(labels) - actions)]
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
	"""What is wrong with each app's levels, by folder."""
	return {path.parent.name: wrong for path in sorted(folders.glob("*/agent.py")) if (wrong := unlevelled(path.read_text(encoding="utf-8")))}
