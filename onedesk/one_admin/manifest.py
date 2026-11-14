"""OneAdmin's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Kept, Region, Settle, _lt

APP = App(
	id="one_admin",
	name="OneAdmin",
	kind="app",
	module="One Admin",
	ui="mixed",
	regions=(
		Region("page", "oneadmin", "OneAdmin's overview, a console of its own, read from several records"),
		Region("page", "oneadmin-billing", "Billing's home: what live workspaces pay, what that leaves against the margin floor, and credits (Tenant, Offering, Credit Reservation)"),
		Region("page", "oneadmin-releases", "Releases: each release with its commit, build and rollout, the servers and workspaces on it and each workspace's window, across servers, workspaces and the registry (Workspace Server, Tenant)"),
		Region("page", "oneadmin-sessions", "start, stop, open and delete sessions on our own servers: real actions a list cannot do"),
		Region("page", "oneadmin-status", "each service's state now and over thirty days, with its checks' history, as a status page, which a list of checks cannot show (Health Check)"),
	),
	kept=Kept(_lt("Runs every workspace from the admin site.")),
	mark="oneadmin",
	rail=170,
	sidebar="One Admin",
	screens="admin",
	names=("one_admin", "oneadmin"),
	help=(
		("overview", "info"),
		("workspaces", "building"),
		("settings", "settings"),
	),
	no_roles="OneAdmin runs only on the admin site, where its one role is set, so it ships no roles to a workspace.",
	operators=True,
	interface={
		"Workspace Server": {
			"views": ({"name": "Cards", "label": _lt("Cards View"), "icon": "layout-grid", "island": "onedesk.oneadmin_servers"},),
		},
	},
	settle=(
		Settle("media.after_migrate"),
		Settle("notes.after_migrate"),
		Settle("site.apply"),
		Settle("offerings.install", install_only=True),
		Settle("books.ensure", install_only=True),
	),
	makes=(
		"Account",
		"Contact",
		"Customer",
		"Item",
		"Item Group",
		"Journal Entry",
		"Lead",
		"Mode of Payment",
		"Opportunity",
		"Opportunity Lost Reason",
		"Sales Invoice",
		"Sales Stage",
	),
)

PARTS = (
	App(id="one_credits", name="OneCredit", kind="engine", module="", mark="onecredit"),
)
