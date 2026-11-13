"""What a plan may include, declared once: each feature's id, what it is
called, what it allows, and the optional service it opens, if any. A plan
in one_admin/price_list.py lists the ids it has, an app's manifest the ids
it needs (`plan=`), and the registry refuses an id that is not here. Pure."""

from dataclasses import dataclass

from onedesk.one.registry.model import _lt


@dataclass(frozen=True)
class Feature:
	id: str
	label: str
	allows: str
	service: str = ""


FEATURES = (
	Feature(
		"training_copies",
		_lt("Training Copies"),
		_lt("Temporary copies of the workspace for its people to train on, once its administrators turn Training Copies on."),
		service="training_copies",
	),
	Feature("demo", _lt("Demo Company"), _lt("The demo company, built into a workspace that is not set up yet.")),
	Feature("own_server", _lt("Own Server"), _lt("A server of the workspace's own, rather than one it shares.")),
)

IDS = tuple(one.id for one in FEATURES)


def get(id: str) -> Feature:
	for one in FEATURES:
		if one.id == id:
			return one
	raise KeyError(id)


def unknown(ids) -> list[str]:
	"""The ids among these that no feature has."""
	return [one for one in ids if one not in IDS]


def of_service(key: str) -> str | None:
	"""The feature that opens an optional service, if a plan must have one."""
	return next((one.id for one in FEATURES if one.service == key), None)


def missing(needs, held) -> tuple[str, ...]:
	"""What of `needs` a plan holding `held` lacks; nothing when `held` is
	None, a workspace whose account has not said."""
	if held is None:
		return ()
	return tuple(one for one in needs if one not in held)
