"""The apps a workspace turns on and off, as the wizard offers them: which
are switches, which are always on and why (`kept`), and what turning one on
brings with it (`needs`). Pure."""

from onedesk.one import registry
from onedesk.one.registry.model import App


def _offered(one: App) -> bool:
	return one.kind == "app" and bool(one.sidebar) and not one.private and not one.operators


def switches() -> tuple[App, ...]:
	"""The apps that can be turned on or off, in the rail's order."""
	return tuple(one for one in registry.apps() if _offered(one) and not (one.kept and not one.kept.held))


def always() -> tuple[App, ...]:
	"""The apps that are on whatever is chosen, each with its `kept.why`."""
	return tuple(one for one in registry.apps() if _offered(one) and one.kept and not one.kept.held)


def _needs() -> dict[str, tuple[str, ...]]:
	return {one.id: one.needs for one in registry.apps()}


def with_needs(chosen) -> dict[str, tuple[str, ...]]:
	"""Every app on once `chosen` are: each chosen one with nothing beside
	it, and each app one of them needs, with the chosen apps that brought
	it, however far down. Pure but for the registry."""
	needs = _needs()
	on: dict[str, set] = {id: set() for id in chosen}
	for id in chosen:
		waiting, seen = list(needs.get(id, ())), set()
		while waiting:
			needed = waiting.pop()
			if needed in seen:
				continue
			seen.add(needed)
			if needed not in chosen:
				on.setdefault(needed, set()).add(id)
			waiting += needs.get(needed, ())
	return {id: tuple(sorted(by)) for id, by in on.items()}


def needed_by(id: str, on) -> tuple[str, ...]:
	"""The apps among `on` that can't run without `id`, however far down:
	what refuses turning it off. Pure but for the registry."""
	return tuple(sorted(other for other in on if other != id and id in with_needs((other,))))


def answer(chosen) -> dict[str, bool]:
	"""The answers' `apps` (one/setup_answers.py) for these chosen: every
	switch, on when chosen or needed by one that is."""
	on = with_needs(chosen)
	return {one.id: one.id in on for one in switches()}
