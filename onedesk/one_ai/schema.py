"""A tool's JSON Schema, read off its signature rather than written twice.

Pure, and small on purpose. The alternative is a schema beside every function,
and the failure mode of that is not an error: it is a model told a parameter is
a string when it is a list, calling the tool correctly according to what it was
told, and being refused. Nobody finds that by reading either half.

So the signature is the schema. `Annotated` carries the description, a union
with `None` or a default says a parameter may be left out, and `Literal` is a
closed list — which is the one that matters most, because a model given an open
string where three values are allowed will eventually invent a fourth.
"""

import inspect
import typing

#: What a Python type is called in JSON Schema. Anything not here is refused
#: rather than guessed at: a parameter whose type nobody wrote down is a
#: parameter a model has to be told about in prose, and prose is the thing this
#: module exists to avoid.
CALLED = {
	str: "string",
	int: "integer",
	float: "number",
	bool: "boolean",
	dict: "object",
	list: "array",
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

	if hint in CALLED:
		return {"type": CALLED[hint]}
	raise Unreadable(f"{tool}({name}) is a {hint!r}, which has no name in JSON Schema")
