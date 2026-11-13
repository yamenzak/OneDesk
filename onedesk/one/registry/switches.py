"""The apps a workspace turns on and off, as the wizard and Apps offer them:
which are switches, which are always on and why (`kept`), what turning one
on brings with it (`needs`), and what refuses turning one off. Pure."""

from onedesk.one import registry
from onedesk.one.registry.model import App


def _offered(one: App) -> bool:
	return one.kind == "app" and bool(one.sidebar) and not one.private and not one.operators


def switches() -> tuple[App, ...]:
	"""The apps that can be turned on or off, in the rail's order."""
	return tuple(one for one in registry.apps() if _offered(one) and not (one.kept and one.kept.always()))


def always() -> tuple[App, ...]:
	"""The apps that are on whatever is chosen, each with its `kept.why`."""
	return tuple(one for one in registry.apps() if _offered(one) and one.kept and one.kept.always())


def _needs() -> dict[str, tuple[str, ...]]:
	return {one.id: one.needs for one in registry.apps()}


def with_needs(chosen, needs: dict | None = None) -> dict[str, tuple[str, ...]]:
	"""Every app on once `chosen` are: each chosen one with nothing beside
	it, and each app one of them needs, with the chosen apps that brought
	it, however far down. `needs` adds the private apps' to the registry's.
	Pure but for the registry."""
	needs = {**_needs(), **(needs or {})}
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


def needed_by(id: str, on, needs: dict | None = None) -> tuple[str, ...]:
	"""The apps among `on` that can't run without `id`, however far down:
	what refuses turning it off. Pure but for the registry."""
	return tuple(sorted(other for other in on if other != id and id in with_needs((other,), needs)))


def held(one: App, submitted) -> str | None:
	"""Why `one` can't be turned off now, or None: its `kept.why` when it is
	kept always, or once `submitted(record_type)` says one of its `kept.when`
	has a submitted record. Pure: `submitted` asks the site."""
	if not one.kept:
		return None
	return one.kept.why if one.kept.always() or any(submitted(doctype) for doctype in one.kept.when) else None


def refused(turning_off, on, held_now: dict, needs: dict | None = None) -> dict[str, tuple[str, object]]:
	"""Why each of `turning_off` can't go, by id: ("kept", why) when
	`held_now` says it holds what it is kept for, ("needed", ids) when an
	app among `on` that stays on needs it. One with neither is left out.
	Pure but for the registry."""
	found: dict[str, tuple[str, object]] = {}
	for id in sorted(turning_off):
		staying = [one for one in on if one not in turning_off]
		if held_now.get(id):
			found[id] = ("kept", held_now[id])
		elif needed_by(id, staying, needs):
			found[id] = ("needed", needed_by(id, staying, needs))
	return found


def answer(chosen) -> dict[str, bool]:
	"""The answers' `apps` (one/setup_answers.py) for these chosen: every
	switch, on when chosen or needed by one that is."""
	on = with_needs(chosen)
	return {one.id: one.id in on for one in switches()}
