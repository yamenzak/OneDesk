"""frappe's Activity Log and Access Log, kept to what the Audit Log shows.

frappe keeps both logs in the site's SQLite log store, whose list runs no
permission query, so the limits one/audit.py puts on the database's list are
put on the store's here, as filters, for every list and count the desk and
One ask of it.
"""

import frappe
from frappe.core.doctype.access_log.access_log import AccessLog as FrappeAccessLog
from frappe.core.doctype.activity_log.activity_log import ActivityLog as FrappeActivityLog

from onedesk.one import audit, roles


def _listed(filters) -> list:
	filters = frappe.parse_json(filters) if isinstance(filters, str) else filters
	if not filters:
		return []
	if isinstance(filters, dict):
		return [
			[key, *(value if isinstance(value, list | tuple) else ("=", value))] for key, value in filters.items()
		]
	return list(filters)


def held(doctype: str, filters, or_filters, ignore_permissions=False):
	"""The filters a reader's list of a log runs with, or None when they may
	read none of it."""
	user = frappe.session.user
	if ignore_permissions or audit._trusted(user):
		return filters, or_filters
	if not roles.administers(user):
		return None
	filters = _listed(filters) + [["user", "not in", list(audit.SYSTEM)]]
	if doctype == "Access Log":
		return filters + [["export_from", "in", audit.kinds(audit.DOWNLOADS)]], or_filters
	if or_filters:
		return filters + [["reference_doctype", "in", audit.kinds()]], or_filters
	return filters, [["reference_doctype", "is", "not set"], ["reference_doctype", "in", audit.kinds()]]


def _list(base, doctype, filters=None, or_filters=None, **kwargs):
	kept = held(doctype, filters, or_filters, kwargs.get("ignore_permissions"))
	if kept is None:
		return []
	return base.get_list(doctype, filters=kept[0], or_filters=kept[1], **kwargs)


def _count(base, doctype, filters=None, or_filters=None, **kwargs):
	kept = held(doctype, filters, or_filters, kwargs.get("ignore_permissions"))
	if kept is None:
		return 0
	return base.get_count(doctype, filters=kept[0], or_filters=kept[1], **kwargs)


class ActivityLog(FrappeActivityLog):
	@staticmethod
	def get_list(doctype, filters=None, or_filters=None, **kwargs):
		return _list(FrappeActivityLog, doctype, filters, or_filters, **kwargs)

	@staticmethod
	def get_count(doctype, filters=None, or_filters=None, **kwargs):
		return _count(FrappeActivityLog, doctype, filters, or_filters, **kwargs)


class AccessLog(FrappeAccessLog):
	@staticmethod
	def get_list(doctype, filters=None, or_filters=None, **kwargs):
		return _list(FrappeAccessLog, doctype, filters, or_filters, **kwargs)

	@staticmethod
	def get_count(doctype, filters=None, or_filters=None, **kwargs):
		return _count(FrappeAccessLog, doctype, filters, or_filters, **kwargs)
