"""Who chose an offering: the workspaces on a plan and the signups that
picked it. An add-on's workspaces carry it in a table, which frappe's
connections cannot count, so the form has a button for them (offering.js)."""


def get_data():
	return {
		"fieldname": "offering",
		"transactions": [{"label": "Sold", "items": ["Tenant", "Account Request"]}],
	}
