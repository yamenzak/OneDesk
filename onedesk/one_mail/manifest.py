"""OneMail's place in One (docs/run/RUN.md, OneRegistry)."""

from onedesk.one.registry.model import App, Region, Roles, Settle, _lt

APP = App(
	id="one_mail",
	name="OneMail",
	kind="app",
	module="One Mail",
	ui="bespoke",
	regions=(
		Region("page", "onemail", "mail, read and written (Communication)"),
	),
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
	},
	hooks={
		"one_record_tabs": ("linking.TABS",),
	},
	settle=(
		Settle("mail_templates.settle"),
	),
	centres=("ai",),
)
