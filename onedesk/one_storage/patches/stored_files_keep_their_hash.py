"""Files stored on R2 since frappe began emptying the content hash of a file at
a URL lost theirs (one_storage/file.py, validate): each is given back the hash
its key is named by, so it is found by its content again."""

import re

import frappe

from onedesk.one_storage import store

HASHED = re.compile(r"^files/(?:private|public)/([0-9a-f]{32})(?:\.|$)")


def execute():
	for name, url in frappe.get_all(
		"File",
		filters={"file_url": ["like", store.FETCH + "%"], "content_hash": ["is", "not set"]},
		fields=["name", "file_url"],
		as_list=True,
	):
		found = HASHED.match(store.key_of(url) or "")
		if found:
			frappe.db.set_value("File", name, "content_hash", found.group(1), update_modified=False)
