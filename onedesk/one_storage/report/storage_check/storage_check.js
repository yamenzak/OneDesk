// Whether files are going to cloud storage, with the fix beside each
// (one_storage/ready.py).
frappe.query_reports["Storage Check"] = onedesk.check.report({ method: "onedesk.one_storage.ready.fix" });
