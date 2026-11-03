from frappe.utils.background_jobs import get_queue_list, get_queue
def run():
	print({q: get_queue(q).count for q in get_queue_list()})
