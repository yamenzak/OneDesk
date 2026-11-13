"""The servers, as records every part of OneAdmin reads the same way."""

import frappe

DOCTYPE = "Workspace Server"
RELEASING = "Releasing"
RELEASED = "Released"


def rows() -> list:
	return frappe.get_all(DOCTYPE, fields="*", order_by="creation asc")


def row_of(server: str):
	return next((one for one in rows() if one.server == server), None)


def in_eu(row) -> bool:
	"""Whether a server is in the EU, read from its region. Pure."""
	return (row.region or "").startswith("eu-")
