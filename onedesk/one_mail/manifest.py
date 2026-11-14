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
	pitch=_lt("{one_mail} is the company's email. The workspace and each person in it get an address, and the mailboxes you already use can be connected. Each message can be linked to the customer, supplier or employee it is about."),
	brings=(
		_lt("An address for the workspace and every person"),
		_lt("Shared mailboxes, assigned and marked done"),
		_lt("Rules and out of office"),
		_lt("Mail kept on its record"),
	),
	media=("inbox.webp", "open-a-message.gif", "message.webp", "mailboxes.webp"),
	credits=("mail",),
	mark="onemail",
	rail=30,
	sidebar="OneMail",
	roles=Roles(user=("OneMail User",), manager=("Mail Manager",)),
	agent=_lt("receptionist"),
	agent_roles=("OneMail Receptionist",),
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
		Settle("access.settle"),
	),
	centres=("ai",),
)
