"""A tool's JSON Schema, read off its signature rather than written twice.

`Annotated` carries the description, a union with `None` or a default says a
parameter may be left out, and `Literal` is a closed list.
"""

import inspect
import typing

#: What a Python type is called in JSON Schema. Anything not here is refused
#: rather than guessed at, so no parameter has to be told about in prose.
CALLED = {
	str: "string",
	int: "integer",
	float: "number",
	bool: "boolean",
	dict: "object",
}


class Unreadable(Exception):
	"""A signature this cannot turn into a schema. Raised at import, not at a call."""


def of(fn) -> dict:
	"""One tool, as a provider's function declaration."""
	hints = typing.get_type_hints(fn, include_extras=True)
	signature = inspect.signature(fn)

	properties, required = {}, []
	for name, parameter in signature.parameters.items():
		if name in ("self", "cls"):
			continue
		if name not in hints:
			raise Unreadable(f"{fn.__name__}({name}) has no type on it")
		said, optional = _one(fn.__name__, name, hints[name])
		properties[name] = said
		if not optional and parameter.default is inspect.Parameter.empty:
			required.append(name)

	return {
		"name": fn.__name__,
		"description": _about(fn),
		"parameters": {"type": "object", "properties": properties, "required": required},
	}


def _about(fn) -> str:
	"""The first paragraph of the docstring, which is what a model reads.

	The rest is for whoever maintains the tool. A model given four paragraphs
	about why a tool is written the way it is has been given four paragraphs of
	nothing it can act on.
	"""
	said = inspect.getdoc(fn) or ""
	first = said.split("\n\n", 1)[0].strip()
	if not first:
		raise Unreadable(f"{fn.__name__} has no docstring, so a model is told nothing about it")
	return " ".join(first.split())


def _one(tool: str, name: str, hint) -> tuple[dict, bool]:
	"""One parameter, and whether it may be left out.

	Unwrapped in a loop rather than in an order, because both orders are written
	in practice: `Annotated[dict, "..."] | None` and `Optional[Annotated[...]]`
	mean the same thing and only one of them survives a single pass.
	"""
	about, optional = "", False
	for _ in range(4):
		hint, said = _described(hint)
		about = about or said
		hint, maybe = _maybe(hint)
		optional = optional or maybe
		if not said and not maybe:
			break

	said = _typed(tool, name, hint)
	if about:
		said["description"] = about
	return said, optional


def _described(hint) -> tuple[object, str]:
	"""`Annotated[str, "..."]` — the type, and the sentence beside it."""
	if typing.get_origin(hint) is not typing.Annotated:
		return hint, ""
	args = typing.get_args(hint)
	said = next((one for one in args[1:] if isinstance(one, str)), "")
	return args[0], said


def _maybe(hint) -> tuple[object, bool]:
	"""`X | None` — the type without the None, and that it may be left out."""
	args = typing.get_args(hint)
	if type(None) not in args:
		return hint, False
	rest = [one for one in args if one is not type(None)]
	return (rest[0] if len(rest) == 1 else hint), True


def _typed(tool: str, name: str, hint) -> dict:
	if typing.get_origin(hint) is typing.Literal:
		values = list(typing.get_args(hint))
		kinds = {CALLED.get(type(one)) for one in values}
		if len(kinds) != 1 or None in kinds:
			raise Unreadable(f"{tool}({name}) is a Literal of mixed kinds")
		return {"type": kinds.pop(), "enum": values}

	# `list[str]` and a bare `list` both land here. Google refuses an array without
	# `items` while OpenAI accepts it, so the stricter reading is the one written.
	if typing.get_origin(hint) is list or hint is list:
		inside = typing.get_args(hint)
		# A list of lists (a filter's [field, operator, value]) nests.
		if inside and (inside[0] is list or typing.get_origin(inside[0]) is list):
			return {"type": "array", "items": _typed(tool, name, inside[0])}
		of = CALLED.get(inside[0]) if inside else "string"
		if of is None:
			raise Unreadable(f"{tool}({name}) is a list of {inside[0]!r}, which has no name in JSON Schema")
		return {"type": "array", "items": {"type": of}}

	if hint in CALLED:
		return {"type": CALLED[hint]}
	raise Unreadable(f"{tool}({name}) is a {hint!r}, which has no name in JSON Schema")
