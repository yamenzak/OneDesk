"""OneMail's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Settle, Roles, _lt

APP = App(
	id="one_mail",
	name="OneMail",
	kind="app",
	module="One Mail",
	line=_lt("The company's email, each message kept on the customer, supplier or job it's about."),
	mark="onemail",
	rail=30,
	sidebar="OneMail",
	roles=Roles(user=("OneMail User",), manager=("Mail Manager",)),
	screens="mail",
	names=("one_mail", "onemail"),
	help=(
		("overview", "info"),
		("your-addresses", "at-sign"),
		("reading-and-writing", "mail"),
		("working-as-a-team", "users"),
		("connecting-a-mailbox", "plug"),
		("rules-and-out-of-office", "workflow"),
		("mail-on-records", "link"),
		("attachments-and-pictures", "paperclip"),
		("asking-oneai", "sparkles"),
		("who-can-do-what", "shield"),
		("settings", "settings"),
	),
	ready={
		"ready": True,
		"checked": {
			"copy": {"on": "2026-11-07", "commit": "ef82a0f5117c", "by": "Claude, for Yamen"},
			"demo": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
			"notifications": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
			"interface": {"on": "2026-11-07", "commit": "0e158460772b", "by": "Claude, for Yamen"},
			"legal": {"on": "2026-11-07", "commit": "52a0c1d96fdb", "by": "Claude, for Yamen"},
		},
	},
	hooks={
		"one_record_tabs": ("linking.TABS",),
	},
	settle=(
		Settle("mail_templates.settle"),
	),
)
