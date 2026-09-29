"""What a signup became and what it was paid with: the workspace it made,
our own lead and deal for it (sales.py), and what Stripe told us about its
checkout. The workspace's jobs and log are on the workspace."""


def get_data():
	return {
		"fieldname": "request",
		"internal_links": {"Tenant": "tenant", "Lead": "lead", "Opportunity": "deal"},
		"transactions": [
			{"label": "Workspace", "items": ["Tenant"]},
			{"label": "Sales", "items": ["Lead", "Opportunity"]},
			{"label": "Payment", "items": ["Stripe Webhook Event"]},
		],
	}
