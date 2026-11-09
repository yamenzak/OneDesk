"""The servers, as records every part of OneAdmin reads the same way."""

import frappe

DOCTYPE = "Workspace Server"


def rows() -> list:
	return frappe.get_all(DOCTYPE, fields="*", order_by="creation asc")


def row_of(server: str):
	return next((one for one in rows() if one.server == server), None)
