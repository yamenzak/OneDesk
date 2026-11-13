"""OneCRM's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Roles, Settle, _lt

APP = App(
	id="one_crm",
	name="OneCRM",
	kind="app",
	module="One CRM",
	ui="native",
	regions=(
		Region("page", "onecrm", "OneCRM's home: how selling is going, what needs the reader today, and everything in it (Lead, Opportunity, Quotation, Sales Order)"),
	),
	line=_lt("Follow every lead from first call to signed quote, and keep each customer's story in one place."),
	mark="onecrm",
	owns=("CRM", "Selling", "Support", "Maintenance", "Telephony", "Communication"),
	rail=80,
	sidebar="OneCRM",
	roles=Roles(user=("Sales User", "Support Team"), manager=("Sales Manager",)),
	screens="crm",
	names=("one_crm", "onecrm"),
	help=(
		("overview", "info"),
		("leads", "user-plus"),
		("next-step", "calendar-check"),
		("a-record-page", "layout-dashboard"),
		("home", "house"),
		("stages-and-pipeline", "kanban"),
		("quoting", "file-text"),
		("customers", "building-2"),
		("appointments-and-campaigns", "megaphone"),
		("support", "life-buoy"),
		("reports", "chart-bar"),
		("setup", "list-checks"),
		("notifications", "bell"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
	},
	companies=(
		"Customer Credit Limit",
		"Installation Note",
		"Issue",
		"Lead",
		"Maintenance Schedule",
		"Maintenance Visit",
		"Opportunity",
		"Party Account",
		"Proforma Invoice",
		"Prospect",
		"Quotation",
		"Sales Order",
		"Subcontracting Inward Order",
		"Warranty Claim",
	),
	interface={
		"Customer": {
			"cards": (
				{"key": "party.overdue"},
				{"key": "party.last_bill"},
				{"key": "Open Orders"},
				{"key": "party.billed", "title": _lt("Billed in 12 Months")},
			),
			"states": {"field": "customer_type", "order": ("Company", "Individual", "Partnership")},
		},
		"Lead": {
			"tabs": {"activities_tab": "calendar-check"},
			"cards": ({"key": "crm.next_step"}, {"key": "crm.reply"}, {"key": "crm.contact"}, {"key": "crm.deals"}),
			"states": {"order": ("Lead", "Open", "Replied", "Interested", "Opportunity", "Quotation", "Converted"), "hide": ("Do Not Contact", "Lost Quotation")},
		},
		"Opportunity": {
			"tabs": {"activities_tab": "calendar-check"},
			"cards": ({"key": "crm.value"}, {"key": "crm.stage"}, {"key": "crm.next_step"}, {"key": "crm.closes"}),
			"states": {"order": ("Open", "Replied", "Quotation", "Converted", "Lost"), "hide": ("Closed",)},
		},
		"Quotation": {
			"cards": ({"key": "order.total"}, {"key": "crm.valid"}, {"key": "crm.deal_of"}, {"key": "project.of"}),
			"states": {"order": ("Draft", "Open", "Replied", "Partially Ordered", "Ordered", "Expired", "Lost"), "hide": ("Cancelled",)},
		},
		"Sales Order": {
			"tabs": {"payment_schedule_section": "calendar-clock"},
			"cards": ({"key": "order.total"}, {"key": "crm.deliver_by"}, {"key": "per_delivered"}, {"key": "per_billed"}),
			"states": {"order": ("Draft", "To Deliver and Bill", "To Bill", "To Deliver", "Completed"), "hide": ("Cancelled", "Closed")},
		},
		"Contract": {
			"cards": ({"key": "signed_on"}, {"key": "end_date"}, {"key": "project.of"}),
			"states": {"order": ("Unsigned", "Active", "Inactive")},
		},
		"Appointment": {
			"fields": {"customer_name": "user"},
			"cards": ({"key": "scheduled_time"}, {"key": "crm.met_with"}),
			"states": {"order": ("Open", "Unverified", "Closed")},
		},
		"Email Campaign": {
			"fields": {"email_campaign_for": "users"},
			"cards": ({"key": "start_date"}, {"key": "end_date"}, {"key": "recipient"}),
			"states": {"order": ("Scheduled", "In Progress", "Completed", "Unsubscribed")},
		},
		"Email Group": {
			"states": {
				"kinds": (
					{"label": _lt("With Subscribers"), "filters": (("total_subscribers", ">", 0),)},
					{"label": _lt("Empty"), "filters": (("total_subscribers", "=", 0),)},
				),
			},
		},
		"Issue": {
			"fields": {"subject": "message-circle-warning"},
			"states": {"order": ("Open", "Replied", "On Hold", "Resolved", "Closed")},
		},
		"Maintenance Schedule": {
			"cards": ({"key": "crm.next_visit"}, {"key": "crm.visits_made"}),
			"states": {"field": "status"},
		},
		"Prospect": {
			"tabs": {"activities_tab": "calendar-check"},
			"states": {"field": "industry"},
		},
		"Warranty Claim": {
			"cards": ({"key": "warranty_amc_status"}, {"key": "warranty_expiry_date"}, {"key": "resolution_date"}),
			"states": {"order": ("Open", "Work In Progress", "Closed", "Cancelled")},
		},
	},
	hooks={
		"one_ai_workspace": ("agent.workspace",),
	},
	settle=(
		Settle("stages.settle"),
		Settle("board.sync"),
		Settle("board.one_pipeline"),
		Settle("next.settle"),
		Settle("record.settle"),
		Settle("capture.defaults", install_only=True),
		Settle("access.settle"),
	),
	makes=(
		"Appointment",
		"Call Log",
		"Contract",
		"Customer",
		"Email Campaign",
		"Lead",
		"Maintenance Schedule",
		"Opportunity",
		"Opportunity Lost Reason",
		"Quotation",
		"Sales Order",
		"Sales Stage",
		"Warranty Claim",
	),
)
