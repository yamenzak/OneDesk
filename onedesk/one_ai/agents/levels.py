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
	"""The level an app's agent works at for one action: as declared, else
	Ask First. A workspace raising one comes with AICenter (P8.2)."""
	level = declared(app).get(action)
	return level if level in LEVELS else CAUTIOUS


def unlevelled(source: str) -> list[str]:
	"""Given an agent.py: a REACH call or a TOOLS entry without a level, a
	level that is none of the three, a level on something that is neither,
	one on a call NOT_FOR_AI keeps from OneAI, or a tool agent.py lacks. Pure."""
	said = _said(source)
	reach, refused, tools, levels = said.get("REACH", {}), said.get("NOT_FOR_AI", {}), said.get("TOOLS", ()), said.get("LEVELS", {})
	functions = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
	actions = set(reach) | set(tools)
	wrong = [f"{one} has no level" for one in sorted(actions - set(levels))]
	wrong += [f"{one}'s level {levels[one]!r} is not one of {LEVELS}" for one in sorted(levels) if levels[one] not in LEVELS]
	wrong += [f"{one} has a level but is no action" for one in sorted(set(levels) - actions)]
	wrong += [f"{one} is not for OneAI, so it has no level" for one in sorted(set(levels) & set(refused))]
	wrong += [f"the tool {one} is not in agent.py" for one in sorted(set(tools) - functions)]
	return wrong


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
