"""The portal's home, and frappe's list of a kind of record, as One's
(one/portal.py). Frappe's own context, which lists through the kind's
`get_list_context`."""

from frappe.www import portal

no_cache = 1


def get_context(context, **dict_params):
	return portal.get_context(context, **dict_params)
