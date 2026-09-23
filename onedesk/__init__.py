__version__ = "0.0.1"


def check_app_permission() -> bool:
	"""Whether One is on the reader's apps screen. Not for a website user — a
	customer or supplier signing in — whom frappe would otherwise send to the
	first app that does not refuse them, which was the desk they cannot open."""
	import frappe
	from frappe.utils.user import is_website_user

	return frappe.session.user == "Administrator" or not is_website_user()
