"""Telling the administrators about OneStudio's extensions and collections
(notifications/one_studio/)."""

from onedesk.one import notify, roles


def extension_turned_on(told: dict) -> None:
	"""An extension turned on by a person: the other administrators hear."""
	notify.notify("Extension Turned On", roles.administrators(), **told)


def extension_turned_off(told: dict) -> None:
	"""An extension turned off by a person: the other administrators hear."""
	notify.notify("Extension Turned Off", roles.administrators(), **told)


def extension_deleted(told: dict) -> None:
	"""An extension deleted: the other administrators hear."""
	notify.notify("Extension Deleted", roles.administrators(), **told)


def extensions_failing(people: list, extensions: str) -> None:
	"""The extensions that tripped yesterday, told to the administrators."""
	notify.notify(
		"Extensions Failing",
		people,
		link="/desk/extension?enabled=1",
		sender="Administrator",
		extensions=extensions,
	)


def collection_added(told: dict) -> None:
	"""A collection added: the other administrators hear."""
	notify.notify("Collection Added", roles.administrators(), **told)


def collection_changed(told: dict) -> None:
	"""A collection changed or moved to another app: the other administrators hear."""
	notify.notify("Collection Changed", roles.administrators(), **told)


def collection_deleted(told: dict) -> None:
	"""A collection deleted: the other administrators hear."""
	notify.notify("Collection Deleted", roles.administrators(), **told)
