app_name = "onedesk"
app_title = "One"
app_publisher = "One"
app_description = "Every One product, as modules on the Frappe desk"
app_email = "hello@4dl.app"
app_license = "agpl-3.0"
app_logo_url = "/assets/onedesk/images/one.svg"

# Run on install, after the custom fields are synced, since much of it reads them.
after_sync = [
	"onedesk.one.roles.ensure",
	# What after_migrate settles, settled on a new site as well.
	"onedesk.one.notify.install",
	# What One's roles are given on frappe's doctypes. See one/access.py.
	"onedesk.one.access.settle",
	# Calendar Links stored as on, so a System Settings save keeps it on. See one_calendar/feed.py.
	"onedesk.one_calendar.feed.settle",
	"onedesk.one.print_blocks.settle",
	"onedesk.one.mail_templates.settle",
	"onedesk.one.recycle.settle",
	"onedesk.one_calendar.tell.install",
	"onedesk.one.head.install",
	"onedesk.one_intake.search.index",
	# Storage is what a tenant pays for, not file size.
	"onedesk.one_storage.store.unlimit",
	# Portal Settings rows One has no use for. See one/portal.py.
	"onedesk.one.portal.settle",
	"onedesk.one.company.hide",
	"onedesk.one_hr.names.hide",
	"onedesk.one_hr.money.hide",
	"onedesk.one_hr.policy.seed",
	"onedesk.one_hr.leave.encashable",
	"onedesk.one_hr.accounts.ready",
	"onedesk.one_hr.accounts.components",
	"onedesk.one_hr.accounts.year",
	# The OneAI user hiring comments are written by, and the hiring switches.
	"onedesk.one_hr.hiring.ensure",
	"onedesk.one.brand.apply",
	"onedesk.one.declutter.apply",
	"onedesk.one.companions.apply",
	# Which kind of site this is, and the role that follows from it.
	"onedesk.one_admin.site.apply",
	# The price list an admin site starts with. See one_admin/offerings.py.
	"onedesk.one_admin.offerings.install",
	# The Stripe account, the receivable in dollars and an Item per offering.
	"onedesk.one_admin.books.ensure",
	# After that, because what it does depends on which kind this is.
	"onedesk.one_ai.instructions.trim",
	"onedesk.one_ai.instructions.ready",
	"onedesk.one_admin.actions.voice",
	"onedesk.one_crm.stages.settle",
	"onedesk.one_crm.board.sync",
	"onedesk.one_crm.board.one_pipeline",
	"onedesk.one_crm.next.settle",
	"onedesk.one_crm.record.settle",
	"onedesk.one_crm.capture.defaults",
	"onedesk.one_crm.access.settle",
	"onedesk.one_book.access.settle",
	"onedesk.one_inventory.access.settle",
	"onedesk.one_project.access.settle",
	"onedesk.one_hr.access.settle",
	"onedesk.one_task.access.settle",
	"onedesk.one_project.board.settle",
	# Lump Sum and the Retention payment term. See one_project/progress.py.
	"onedesk.one_project.progress.settle",
	# Contract Work, the item a fixed-price contract is billed as. See one_project/kinds.py.
	"onedesk.one_project.kinds.settle",
	"onedesk.one_project.updates.settle",
	"onedesk.one_hr.lifecycle.settle_boardings",
]

# Their dock files do not carry the mount, so a newer erpnext or hrms clears it,
# and nobody is ever asked which company; see one/company.py.
after_migrate = [
	"onedesk.one.roles.ensure",
	"onedesk.one.notify.install",
	# What One's roles are given on frappe's doctypes. See one/access.py.
	"onedesk.one.access.settle",
	# Calendar Links stored as on, so a System Settings save keeps it on. See one_calendar/feed.py.
	"onedesk.one_calendar.feed.settle",
	"onedesk.one.print_blocks.settle",
	"onedesk.one.mail_templates.settle",
	# The Recycle Bin's titles for what was deleted before. See one/recycle.py.
	"onedesk.one.recycle.settle",
	# frappe's own morning event mail stopped; Today's Events replaces it.
	"onedesk.one_calendar.tell.install",
	# What each module's records say above their fields. See one/head.py.
	"onedesk.one.head.install",
	# The index that makes document text searchable. See one_intake/search.py.
	"onedesk.one_intake.search.index",
	"onedesk.one_storage.store.unlimit",
	"onedesk.one.companions.apply",
	"onedesk.one.company.hide",
	"onedesk.one_hr.names.hide",
	"onedesk.one_hr.money.hide",
	"onedesk.one_hr.policy.seed",
	"onedesk.one_hr.leave.encashable",
	"onedesk.one_hr.accounts.ready",
	"onedesk.one_hr.accounts.components",
	"onedesk.one_hr.accounts.year",
	"onedesk.one_hr.hiring.ensure",
	"onedesk.one_admin.site.apply",
	"onedesk.one_ai.instructions.trim",
	"onedesk.one_ai.instructions.ready",
	"onedesk.one_admin.actions.voice",
	"onedesk.one_crm.stages.settle",
	"onedesk.one_crm.board.sync",
	"onedesk.one_crm.board.one_pipeline",
	"onedesk.one_crm.next.settle",
	"onedesk.one_crm.record.settle",
	"onedesk.one_crm.access.settle",
	"onedesk.one_book.access.settle",
	"onedesk.one_inventory.access.settle",
	"onedesk.one_project.access.settle",
	"onedesk.one_hr.access.settle",
	"onedesk.one_task.access.settle",
	"onedesk.one_project.board.settle",
	# Lump Sum and the Retention payment term. See one_project/progress.py.
	"onedesk.one_project.progress.settle",
	# Contract Work, the item a fixed-price contract is billed as. See one_project/kinds.py.
	"onedesk.one_project.kinds.settle",
	"onedesk.one_project.updates.settle",
	"onedesk.one_hr.lifecycle.settle_boardings",
]
extend_bootinfo = [
	"onedesk.one.boot.boot_session",
	# The desk hides retention while a workspace doesn't hold it. See one_project/retention.py.
	"onedesk.one_project.retention.boot",
	# OneAdmin's rail and Home are offered to operators only. See one_admin/site.py.
	"onedesk.one_admin.site.offer",
	# Unseen announcements, which frappe works out for Guest. See one/announcements.py.
	"onedesk.one.announcements.boot",
	# Whether server extensions run here, for the Extensions list. See one_studio/extensions.py.
	"onedesk.one_studio.extensions.boot",
]

# A pattern is not visible from inside one request. See one_hr/healing.py.
scheduler_events = {
	# A site takes minutes to build, so a request makes a job and this walks it.
	# Inert on a tenant site: `runner.tick` asks whether this site administers
	# workspaces before it asks whether there is anything to do.
	"cron": {
		"*/2 * * * *": ["onedesk.one_admin.runner.tick"],
		"* * * * *": [
			# Mail the Worker stored, in case its notice was missed.
			"onedesk.one_mail.inbound.sweep",
			# Connected mailboxes, one job each.
			"onedesk.one_mail.sync.sync_all",
			# Matters quiet long enough are acted on. See one_intake/matters.py.
			"onedesk.one_intake.matters.due",
		],
		# Readings that waited for credits are tried again, and files that were
		# never read are caught up. See one_intake/pipeline.py.
		"*/15 * * * *": ["onedesk.one_intake.pipeline.again"],
		# An interview starting soon, told to its interviewers. See one_hr/tell.py.
		"*/5 * * * *": ["onedesk.one_hr.tell.interviews_soon", "onedesk.one_calendar.tell.soon"],
		# Each person's day, in the morning. See one_calendar/tell.py.
		"45 6 * * *": ["onedesk.one_calendar.tell.today_events"],
		# Each person's tasks due today and late. See one_task/tell.py.
		"40 6 * * *": ["onedesk.one_task.tell.today"],
	},
	"daily": [
		# Privacy requests nobody decided in a week. See one/privacy.py.
		"onedesk.one.privacy.remind",
		# Retention falling due today is told. See one_project/retention.py.
		"onedesk.one_project.retention.due",
		# Task steps that waited for a day. See one_intake/steps.py.
		"onedesk.one_intake.steps.daily",
		# The company field follows the holiday list in force; a list about to end is told.
		"onedesk.one.holidays.daily",
		# Faces not found a month ago are looked for again. See one_mail/faces.py.
		"onedesk.one_mail.faces.again",
		# The Recycle Bin keeps things thirty days. See one_storage/api.py.
		"onedesk.one_storage.api.purge_old",
		"onedesk.one_storage.file_requests.remind_due",
		"onedesk.one.account.nightly",
		"onedesk.one_admin.domains.nightly",
		# One rung a workspace, one workspace at a time. See one_admin/ladder.py.
		"onedesk.one_admin.lifecycle.nightly",
		"onedesk.one_admin.closing.due",
		# Webhooks whose calls gave up yesterday. See one/webhooks.py.
		"onedesk.one.webhooks.failing",
		"onedesk.one_studio.extensions.failing",
		# Providers ship models weekly and re-price them without an announcement.
		"onedesk.one_admin.catalogue.nightly",
		# Holds whose call never came back, which nothing else would let go.
		"onedesk.one_admin.ledger.nightly",
		# The credit every plan promises. Keyed by month, so nightly is harmless.
		"onedesk.one_admin.topup.monthly",
		"onedesk.one_admin.storage.nightly",
		# Deals whose checkout nobody finished and their signups, and paid
		# invoices not yet booked.
		"onedesk.one_admin.sales.abandoned",
		"onedesk.one_admin.signup.abandon",
		# One mail to somebody who filled the signup form and never paid.
		"onedesk.one_admin.signup.remind",
		"onedesk.one_admin.books.catch_up",
		"onedesk.one_hr.healing.nightly",
		# The sound of old interview recordings; their transcripts stay.
		"onedesk.one_hr.hiring.purge",
		"onedesk.one_hr.leaving.nightly",
		"onedesk.one_hr.setup.nightly",
		# Yesterday's project updates, to the project's people. See one_project/updates.py.
		"onedesk.one_project.updates.sum_up",
		# HRMS's reminders, told through the hub. See one_hr/tell.py.
		"onedesk.one_hr.tell.birthdays",
		"onedesk.one_hr.tell.anniversaries",
		"onedesk.one_hr.tell.feedback_due",
	],
	"hourly": [
		"onedesk.one_hr.closing.hourly",
		# A project asks its team for an update. See one_project/updates.py.
		"onedesk.one_project.updates.ask",
		# Attachments that arrived while storage was full, saved once it is not.
		# See one_mail/room.py.
		"onedesk.one_mail.room.again",
	],
	# What OneAI read for each person this week. See one_intake/digest.py.
	"weekly": ["onedesk.one_intake.digest.weekly", "onedesk.one_hr.tell.holidays_weekly"],
	"monthly": [
		"onedesk.one_hr.tell.holidays_monthly",
		# A retainer's last month, to invoice. See one_project/tell.py.
		"onedesk.one_project.tell.retainer_months",
	],
}

# Every email this workspace sends: an address on the mail domain through
# admin to Cloudflare, any other account over its own SMTP. See one_mail/outbound.py.
override_email_send = "onedesk.one_mail.outbound.send"

doc_events = {
	# Stock issued to a project is a cost of the job, under a cost type. See
	# one_project/money.py.
	"Stock Entry": {"before_validate": "onedesk.one_project.money.issued"},
	# A change opened in the Audit Log shows only the fields its reader may read.
	# See one/audit.py.
	"Version": {"onload": "onedesk.one.audit.onload"},
	# Our own books sell each offering as an Item. See one_admin/books.py.
	"Offering": {"on_update": ["onedesk.one_admin.books.synced", "onedesk.one_admin.offerings.warn"]},
	"One Admin Settings": {"on_update": "onedesk.one_admin.offerings.warn"},
	"User": {
		# A person turned on takes one of the plan's seats. See one/settings.py.
		"validate": "onedesk.one.settings.seated",
		# Everyone who works here has an address on the mail domain.
		"before_save": "onedesk.one_mail.addresses.for_person",
		# A user without a picture gets their face, or their employee's photo.
		"after_insert": "onedesk.one_mail.faces.dress_later",
		# A manager is not kept to their own employee's records. See one_hr/everybody.py.
		"on_update": ["onedesk.one_mail.faces.dress_later", "onedesk.one_hr.everybody.user"],
	},
	# Calendar Links off deletes every calendar link. See one_calendar/feed.py.
	"System Settings": {"on_update": "onedesk.one_calendar.feed.switched"},
	# What a workspace writes about a form is held: nothing that runs, nothing
	# that weakens a guard. See one/layer.py.
	"Custom Field": {"validate": "onedesk.one.layer.custom_field"},
	"Property Setter": {"validate": "onedesk.one.layer.property_setter"},
	"Client Script": {"validate": "onedesk.one.layer.script"},
	"Server Script": {"validate": "onedesk.one.layer.script"},
	# A type's text names only its own slots. See one/notify.py.
	"Notification Type": {"validate": "onedesk.one.notify.validate", "on_update": "onedesk.one.notify.changed"},
	# What the workspace may write into a print, a mail template, an approval or an automation: one/printing.py and beside it.
	"Print Format": {"validate": "onedesk.one.printing.validate_format"},
	# What a workspace keeps of its own reports and dashboards, and where a
	# saved report shows. See one/reports.py.
	"Report": {
		"validate": "onedesk.one.reports.report_kept",
		"after_insert": "onedesk.one.reports.placed",
		"on_trash": "onedesk.one.reports.removed",
	},
	"Dashboard": {"on_trash": "onedesk.one.reports.removed"},
	"Dashboard Chart": {"validate": "onedesk.one.reports.chart_kept"},
	"Number Card": {"validate": "onedesk.one.reports.chart_kept"},
	"Auto Email Report": {"validate": "onedesk.one.reports.mail_kept"},
	"Letter Head": {"validate": "onedesk.one.printing.validate_letter_head"},
	# A letter head's drawn top says what General says now (one/letter_heads.py).
	# The company without a logo gets its website's. See one_mail/faces.py.
	"Company": {
		# The books lock up to today at the latest. See one_book/closing.py.
		"validate": "onedesk.one_book.closing.kept_to_today",
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": ["onedesk.one.letter_heads.redraw", "onedesk.one_mail.faces.dress_later"],
	},
	"Address": {"on_update": "onedesk.one.letter_heads.redraw"},
	"Print Format Snippet": {"validate": "onedesk.one.printing.validate_snippet"},
	"Email Template": {"validate": "onedesk.one.mail_templates.validate"},
	# An address template the workspace writes names fields of the address. See one/masters.py.
	"Address Template": {"validate": "onedesk.one.masters.validate_address_template"},
	# A new value of a tree goes under its root, and a department is the
	# workspace's company's, however it is made: Masters, OneAI, frappe's form.
	"Customer Group": {"before_insert": "onedesk.one.masters.place"},
	"Territory": {"before_insert": "onedesk.one.masters.place"},
	"Item Group": {"before_insert": "onedesk.one.masters.place"},
	"Supplier Group": {"before_insert": "onedesk.one.masters.place"},
	"Department": {"before_insert": "onedesk.one.masters.place"},
	"Workflow": {"validate": "onedesk.one.approvals.validate"},
	# Whoever a step of an approval waits on is told through the hub. See one/approvals.py.
	"Workflow Action": {"after_insert": "onedesk.one.approvals.waiting"},
	"Automation Flow": {"validate": "onedesk.one.automations.validate"},
	# What a webhook the workspace writes may send, and where. See one/webhooks.py.
	"Webhook": {"validate": "onedesk.one.webhooks.validate"},
	"Assignment Rule": {"validate": "onedesk.one_crm.access.assignment_rule"},
	# Only an administrator announces; everybody is told. See one/announcements.py.
	"Note": {
		"before_validate": "onedesk.one.announcements.before_validate",
		"validate": "onedesk.one.announcements.validate",
		"on_update": "onedesk.one.announcements.on_update",
	},
	"Document Naming Rule": {"validate": "onedesk.one.numbering.validate_rule"},
	# A notification is pushed to the devices its person chose. See one/push.py.
	"Notification Log": {
		# frappe's line for a task given, said in OneTask's. See one_task/tell.py.
		"before_insert": "onedesk.one_task.tell.given",
		"after_insert": "onedesk.one.push.pushed",
	},
	# A new person is mailed only what the administrator said. See one/notify.py.
	"Notification Settings": {"before_insert": "onedesk.one.notify.new_person"},
	# An app's own switch for a mail it sends is that type's Send This.
	"Payroll Settings": {"on_update": "onedesk.one.notify.switched"},
	# A mail one of our Notifications sends: its Enabled and Send This are one.
	"Notification": {"on_update": "onedesk.one.notify.switched"},
	# A request raised by reordering is told to Purchasing. See one_inventory/tell.py.
	"Material Request": {
		"on_submit": "onedesk.one_inventory.tell.raised",
		# A request and its lines name the same project. See one_project/chain.py.
		"validate": "onedesk.one_project.chain.agree",
	},
	# A customer's or supplier's contact invited as a user sees their records on
	# the portal. See one/portal.py.
	"Contact": {
		"on_update": [
			"onedesk.one.portal.invited",
			# A contact without a picture gets their face. See one_mail/faces.py.
			"onedesk.one_mail.faces.dress_later",
		],
		"after_insert": "onedesk.one_mail.faces.dress_later",
	},
	# An organisation without a picture gets its website's logo. See
	# one_mail/faces.py.
	# A customer made from a lead keeps the lead's documents. See one_intake/planning.py.
	"Customer": {
		"after_insert": ["onedesk.one_mail.faces.dress_later", "onedesk.one_intake.planning.carried"],
		"on_update": "onedesk.one_mail.faces.dress_later",
	},
	"Supplier": {"after_insert": "onedesk.one_mail.faces.dress_later", "on_update": "onedesk.one_mail.faces.dress_later"},
	"Bank": {"after_insert": "onedesk.one_mail.faces.dress_later", "on_update": "onedesk.one_mail.faces.dress_later"},
	"Manufacturer": {
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": "onedesk.one_mail.faces.dress_later",
	},
	# A company bank account wires the bank modes of payment. See one_book/ready.py.
	"Bank Account": {"on_update": "onedesk.one_book.ready.wired"},
	# A repeated invoice keeps its days to pay; a repeated bill drops the
	# supplier's number. See one_book/repeat.py.
	"Sales Invoice": {
		"on_recurring": "onedesk.one_book.repeat.repeated",
		# Starts with its order's or its project's terms. See one_project/terms.py.
		"before_insert": "onedesk.one_project.terms.carried",
		"after_insert": "onedesk.one_project.progress.drafted",
		# The emirate a sale is reported under. See one_book/vat.py.
		"validate": [
			"onedesk.one_book.vat.emirate",
			"onedesk.one_project.chain.agree",
			# Retention is the share of the work billed. See one_project/progress.py.
			"onedesk.one_project.progress.retained",
		],
	},
	# A payment lowers an invoice's outstanding with db_set, so the task step
	# waiting for it is checked from the payment. See one_intake/steps.py.
	"Payment Entry": {
		"on_submit": "onedesk.one_intake.steps.paid",
		"on_cancel": "onedesk.one_intake.steps.paid",
		# A payment takes the project its invoices name. See one_project/chain.py.
		"validate": "onedesk.one_project.chain.paid_for",
	},
	"Journal Entry": {"on_submit": "onedesk.one_intake.steps.paid", "on_cancel": "onedesk.one_intake.steps.paid"},
	"Purchase Invoice": {
		"on_recurring": "onedesk.one_book.repeat.repeated",
		# Starts with its order's payment terms. See one_project/terms.py.
		"before_insert": "onedesk.one_project.terms.carried",
		# A bill for a share of the work, for the project's manager to check. See one_project/progress.py.
		"after_insert": "onedesk.one_project.progress.drafted",
		"validate": [
			# A bill's reclaimable VAT is kept at the VAT on it.
			"onedesk.one_book.vat.reclaimed",
			"onedesk.one_inventory.assets.located",
			"onedesk.one_project.chain.agree",
			"onedesk.one_project.progress.retained",
		],
		# A bill that updates stock registers its assets.
		"on_submit": "onedesk.one_inventory.assets.registered",
	},
	# The assets register finishes itself. See one_inventory/assets.py.
	"Item": {"validate": "onedesk.one_inventory.assets.fixed_item"},
	# A schedule with an end date is due too. See one_inventory/maintenance.py.
	"Asset Maintenance": {"validate": "onedesk.one_inventory.maintenance.due"},
	"Purchase Receipt": {
		"validate": ["onedesk.one_inventory.assets.located", "onedesk.one_project.chain.agree"],
		"on_submit": "onedesk.one_inventory.assets.registered",
	},
	# A Public event is on everybody's calendar. See one_calendar/events.py.
	# Who is told of an event: invited, changed, cancelled. See one_calendar/tell.py.
	"Event": {
		"validate": "onedesk.one_calendar.events.validate",
		"on_update": "onedesk.one_calendar.tell.saved",
		"on_trash": "onedesk.one_calendar.tell.removed",
	},
	# hrms counts milestones by letting an insert fail, and the message outlives
	# the savepoint. See one/quiet.py.
	"*": {
		# What a record Intake makes still needs, from the document. See one_intake/fill.py.
		"before_insert": "onedesk.one_intake.fill.before_insert",
		"before_save": "onedesk.one_intake.fill.before_save",
		"on_submit": [
			"onedesk.one.quiet.milestone",
			"onedesk.one_intake.mark.looked_at",
			"onedesk.one_intake.steps.record_changed",
			# Submitting runs no on_update: linked fields changed with it are
			# saved here. See one/linked.py.
			"onedesk.one.linked.save",
			# A project's money changed: its open page redraws. See one_project/money.py.
			"onedesk.one_project.money.moved",
		],
		"after_insert": [
			"onedesk.one.quiet.milestone",
			# A contact, customer or supplier someone already is. See one_intake/identity.py.
			"onedesk.one_intake.identity.flag",
			# Documents that named a new party before it existed. See one_intake/planning.py.
			"onedesk.one_intake.planning.backlink",
		],
		# The fields OneAI wrote that still say it (one_ai/touch.py), and the
		# mark on a record OneAI made that nobody has checked (one_intake/mark.py).
		"onload": ["onedesk.one_ai.touch.onload", "onedesk.one_intake.mark.onload", "onedesk.one.head.onload"],
		# Every identifier a record carries, kept up as it changes and carried
		# through a rename or a merge. See one_intake/identity.py. A person's
		# save, submit or cancel takes the OneAI mark down.
		"on_update": [
			"onedesk.one_intake.identity.remember",
			"onedesk.one_intake.mark.looked_at",
			# A task step that waits for this record's state. See one_intake/steps.py.
			"onedesk.one_intake.steps.record_changed",
			# The linked record's fields edited on this form, in the same save.
			# See one/linked.py.
			"onedesk.one.linked.save",
		],
		"on_update_after_submit": "onedesk.one.linked.save",
		"on_cancel": [
			"onedesk.one_intake.mark.looked_at",
			"onedesk.one_intake.steps.record_changed",
			"onedesk.one_project.money.moved",
		],
		"before_rename": "onedesk.one_intake.mark.before_rename",
		"after_rename": ["onedesk.one_intake.identity.renamed", "onedesk.one_intake.mark.after_rename"],
		# Deleting a record OneAI made is a lesson, read before its mark goes.
		"on_trash": [
			# What the Recycle Bin calls it. See one/recycle.py.
			"onedesk.one.recycle.titled",
			"onedesk.one_intake.lessons.deleted",
			"onedesk.one_ai.touch.forget",
			"onedesk.one_intake.identity.forget",
			"onedesk.one_intake.filing.forget",
		],
	},
	# A project manager's budgets are projects'. See one_project/budget.py.
	# ... and a project's Budget follows its cost types.
	"Budget": {
		"validate": "onedesk.one_project.budget.kept_to_projects",
		"on_submit": "onedesk.one_project.budget.synced",
		"on_cancel": "onedesk.one_project.budget.synced",
	},
	# A closed year is a locked one. See one_book/closing.py.
	"Period Closing Voucher": {"on_submit": "onedesk.one_book.closing.year_closed"},
	"Employee": {
		"validate": ["onedesk.one_hr.leaving.notice_ends_on", "onedesk.one_hr.everybody.employee"],
		# An employee without a photo gets their user's picture, or their face.
		# See one_mail/faces.py.
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": ["onedesk.one_hr.leaving.on_employee_update", "onedesk.one_mail.faces.dress_later"],
	},
	# One day's overtime is claimed once, and the slip says what it pays.
	# See one_hr/overtime.py.
	"Overtime Slip": {
		"before_validate": "onedesk.one_hr.overtime.before_validate",
		"validate": "onedesk.one_hr.overtime.no_double_pay",
	},
	# A block reads as a block. See one_hr/timesheet.py.
	"Timesheet": {
		"before_validate": "onedesk.one_hr.timesheet.before_validate",
		# A retainer's hours for the month, used. See one_project/tell.py.
		"on_submit": "onedesk.one_project.tell.hours_used",
	},
	# The third request doctype, answered like the other two. See one_hr/leave.py.
	# An earning books to the company's Salary account. See one_hr/accounts.py.
	"Salary Component": {"before_validate": "onedesk.one_hr.accounts.component"},
	"Leave Application": {
		"before_validate": "onedesk.one_hr.decision.kept",
		"before_submit": "onedesk.one_hr.leave.before_submit",
	},
	"Expense Claim": {
		"before_validate": "onedesk.one_hr.expense.before_validate",
		"before_submit": "onedesk.one_hr.expense.before_submit",
	},
	"Employee Benefit Application": {"before_validate": "onedesk.one_hr.benefit.application"},
	"Employee Benefit Claim": {"before_validate": "onedesk.one_hr.benefit.claim"},
	"Appointment Letter": {"before_validate": "onedesk.one_hr.letter.before_validate"},
	# A cycle with appraisals on it has started, and the change it makes to
	# somebody can be a list column. See one_hr/growth.py.
	"Appraisal": {
		"before_validate": "onedesk.one_hr.growth.appraisal_period",
		"after_insert": "onedesk.one_hr.growth.cycle_under_way",
	},
	"Employee Promotion": {"before_validate": "onedesk.one_hr.growth.promotion"},
	# Every applicant read, rated and placed by OneAI. See one_hr/hiring.py.
	# An application OneAI made from a mail steps aside for the form's. See
	# one_intake/planning.py.
	"Job Applicant": {"after_insert": ["onedesk.one_hr.hiring.arrived", "onedesk.one_intake.planning.applicant_arrived"]},
	"Interview": {
		"after_insert": "onedesk.one_hr.hiring.scheduled",
		# Whoever holds an interview may open it. See one_hr/hiring.py.
		"on_update": "onedesk.one_hr.hiring.interviewers",
		"onload": "onedesk.one_hr.hiring.interview_onload",
	},
	# A new grievance is read, and a sensitive one is kept to HR Managers and
	# its raiser. See one_hr/ai_grievance.py.
	# A mailbox's OneAI switch holds however it is changed. See one_intake/switches.py.
	"Email Account": {
		"validate": ["onedesk.one_intake.switches.mailbox_switched", "onedesk.one_mail.holders.signed"]
	},
	"Employee Grievance": {
		"after_insert": "onedesk.one_hr.ai_grievance.raised",
		"validate": "onedesk.one_hr.ai_grievance.unmarked",
	},
	# A recording's sound goes by its retention or an HR Manager's hand; a
	# file's OneCloud links and versions go with it.
	"File": {
		# A folder's OneAI switch holds however it is changed. See one_intake/switches.py.
		"validate": ["onedesk.one_intake.switches.file_switched", "onedesk.one_project.media.kept_shown"],
		# Every new file is read, once per content. See one_intake/pipeline.py.
		# A project's Featured Media sets its Cover; see one_project/media.py.
		"after_insert": ["onedesk.one_intake.pipeline.file_added", "onedesk.one_project.media.changed"],
		# An open OneCloud folder redraws; see one_storage/live.py. A file OneAI
		# filed and a person moved back is a lesson; see one_intake/lessons.py.
		"on_update": [
			"onedesk.one_storage.live.changed",
			"onedesk.one_intake.lessons.moved",
			"onedesk.one_project.media.changed",
		],
		"on_trash": [
			"onedesk.one_hr.hiring.keep_sound",
			"onedesk.one_storage.links.forget_file",
			"onedesk.one_storage.history.forget",
			"onedesk.one_storage.live.changed",
			"onedesk.one_project.media.changed",
		]
	},
	# An onboarding is for somebody who is not an employee yet, so the holiday
	# list has to come from the company. See one_hr/lifecycle.py.
	"Employee Onboarding": {
		"before_validate": "onedesk.one_hr.lifecycle.onboarding",
		# The checklist's project is typed a boarding, and left out of OneProject.
		"on_submit": "onedesk.one_hr.lifecycle.typed",
	},
	# Leaving asks for the equipment back. See one_inventory/custody.py.
	"Employee Separation": {
		"before_submit": "onedesk.one_inventory.custody.leaving",
		"on_submit": "onedesk.one_hr.lifecycle.typed",
	},
	# A task of nobody's is its maker's. See one_task/capture.py.
	# A sub-task's parent is a group and its project is the parent's, and a
	# checklist is the progress. See one_task/task.py.
	"Task": {
		"before_insert": [
			"onedesk.one_hr.lifecycle.task",
			# What ERPNext's template copy leaves out. See one_project/templates.py.
			"onedesk.one_project.templates.task_made",
		],
		"after_insert": "onedesk.one_task.capture.task_made",
		"before_validate": [
			"onedesk.one_task.task.before_validate",
			# A template task begins and lasts whole days. See one_project/templates.py.
			"onedesk.one_project.templates.days_kept",
		],
		"on_recurring": "onedesk.one_task.task.recurring",
		"on_update": [
			# A slip moves what waits on it, across sub-projects. See one_project/plan.py.
			"onedesk.one_project.plan.reschedule",
			# A task done is told to whoever gave it, and one ready, sent for
			# review or moved, to its people. See one_task/tell.py.
			"onedesk.one_task.tell.done",
			"onedesk.one_task.tell.changed",
			# A milestone billed on completion, done. See one_project/milestones.py.
			"onedesk.one_project.milestones.reached",
			# The projects above measure their tree again. See one_project/overview.py.
			"onedesk.one_project.overview.task_changed",
			# Its logged hours passing its plan is told. See one_project/tell.py.
			"onedesk.one_project.tell.over_plan",
			# A template task counts again in its templates. See one_project/templates.py.
			"onedesk.one_project.templates.task_measured",
		],
		"after_delete": "onedesk.one_project.overview.task_changed",
	},
	# A template's list says its tasks, days and projects. See one_project/templates.py.
	"Project Template": {"validate": "onedesk.one_project.templates.measured"},
	# A money document and its lines name the same project. See one_project/chain.py.
	"Request for Quotation": {"validate": "onedesk.one_project.chain.agree"},
	"Supplier Quotation": {"validate": "onedesk.one_project.chain.agree"},
	"Purchase Order": {
		"validate": "onedesk.one_project.chain.agree",
		# A new Retention Due moves the retention on its invoices. See one_project/progress.py.
		"on_update_after_submit": "onedesk.one_project.progress.release",
	},
	"Delivery Note": {"validate": "onedesk.one_project.chain.agree"},
	# A project's tasks are named with its prefix. See one_project/naming.py.
	# On a project, sharing is membership. See one_project/members.py.
	"DocShare": {"after_insert": "onedesk.one_project.members.shared"},
	"Project": {
		"before_validate": [
			"onedesk.one_project.members.nobody",
			"onedesk.one_project.members.invite",
			"onedesk.one_project.members.unlist",
			# A project made without a kind gets the one its records say. See one_project/kinds.py.
			"onedesk.one_project.kinds.fill",
			# How it counts its time, and its site. See one_project/hours.py.
			"onedesk.one_project.hours.fill",
			# A project closes with its work. See one_project/status.py.
			"onedesk.one_project.status.held",
		],
		# What its kind needs, after a sub-project takes its parent's customer. See one_project/kinds.py.
		"validate": [
			"onedesk.one_project.naming.validate",
			"onedesk.one_project.tree.validate",
			"onedesk.one_project.kinds.held",
			# Its customer and kind stay once it has orders or invoices. See one_project/kinds.py.
			"onedesk.one_project.kinds.settled",
			# Its Budget is its cost types', and its contacts name somebody. See budget.py, contacts.py.
			"onedesk.one_project.budget.summed",
			"onedesk.one_project.contacts.held",
		],
		"on_update": [
			"onedesk.one_project.naming.on_update",
			"onedesk.one_project.contacts.link_all",
			"onedesk.one_project.members.forget",
			"onedesk.one_project.tree.forget",
			# Who was added, who now runs it, how it is going. See one_project/tell.py.
			"onedesk.one_project.tell.changed",
			# Handed over, the retention released at handover falls due. See one_project/retention.py.
			"onedesk.one_project.retention.handed_over",
			# One progress figure for the tree. See one_project/overview.py.
			"onedesk.one_project.overview.project_changed",
			# How many projects its template has. See one_project/templates.py.
			"onedesk.one_project.templates.used",
		],
		"on_trash": [
			"onedesk.one_project.members.forget",
			"onedesk.one_project.tree.forget",
			"onedesk.one_project.templates.used",
		],
	},
	# A project's board, as ERPNext makes it, shaped. See one_project/board.py.
	"Kanban Board": {"before_insert": "onedesk.one_project.board.shape"},
	"Training Result": {"before_validate": "onedesk.one_hr.lifecycle.result"},
	# The reason is a record and submitting is an approval. See one_hr/request.py.
	# A day at a project's site is a day on the project. See one_project/site_time.py.
	"Attendance": {
		"on_submit": "onedesk.one_project.site_time.attended",
		"on_cancel": "onedesk.one_project.site_time.cancelled",
	},
	"Attendance Request": {
		"before_validate": "onedesk.one_hr.request.before_validate",
		"before_submit": "onedesk.one_hr.request.before_submit",
	},
	# A stage has an outcome, and the status follows it; ERPNext's own verbs
	# move the stage back. See one_crm/stages.py.
	# A deal's value is worked out on the server too. See one_crm/deal.py.
	"Opportunity": {
		"before_validate": "onedesk.one_crm.stages.before_validate",
		"validate": "onedesk.one_crm.deal.validate",
		"on_update": "onedesk.one_crm.next.on_update",
	},
	# The owner is reminded of the next step (one_crm/next.py), and a lead that
	# already exists is found rather than made twice (one_crm/capture.py).
	"Lead": {
		"before_insert": "onedesk.one_crm.capture.before_insert",
		"on_update": [
			"onedesk.one_crm.next.on_update",
			# A lead without a picture gets their face, or their company's logo.
			# See one_mail/faces.py.
			"onedesk.one_mail.faces.dress_later",
		],
		"after_insert": "onedesk.one_mail.faces.dress_later",
	},
	# An Assignment Rule's pick becomes the owner, and a lead's first reply is
	# timed (one_crm/capture.py). A to-do about nothing becomes a task, and the
	# last one ticked off on a task of one's own completes it (one_task/capture.py).
	"ToDo": {
		"before_insert": "onedesk.one_task.capture.todo_made",
		"after_insert": [
			"onedesk.one_crm.capture.assigned",
			# A task given to somebody outside its project lets them in. See one_project/members.py.
			"onedesk.one_project.members.assigned",
		],
		"on_update": "onedesk.one_task.capture.todo_changed",
	},
	"Communication": {
		# Mail sent from here is in Sent and in its thread. See one_mail/outbound.py.
		"before_insert": "onedesk.one_mail.outbound.file_sent",
		# A reply that goes out ticks the step that asked for it; the thread is
		# known by the end of the save. See one_intake/steps.py.
		"on_update": ["onedesk.one_mail.outbound.thread_sent", "onedesk.one_intake.steps.replied"],
		"after_insert": [
			# Replies read before what they answer join its thread. See one_mail/threads.py.
			"onedesk.one_mail.threads.adopt",
			# An open mailbox redraws. See one_mail/live.py.
			"onedesk.one_mail.live.inserted",
			"onedesk.one_crm.capture.replied",
			# An emailed answer to a project's ask. See one_project/updates.py.
			"onedesk.one_project.updates.answered",
		],
	},
	"Call Log": {"after_insert": "onedesk.one_crm.capture.replied"},
	# The board has a column per stage. See one_crm/board.py.
	"Sales Stage": {
		"on_update": "onedesk.one_crm.board.sync",
		"after_rename": "onedesk.one_crm.board.sync",
		"after_delete": "onedesk.one_crm.board.sync",
	},
	"Quotation": {
		# Starts with its project's terms. See one_project/terms.py.
		"before_insert": "onedesk.one_project.terms.carried",
		"on_submit": "onedesk.one_crm.stages.follow",
		"on_cancel": "onedesk.one_crm.stages.follow",
		"on_update_after_submit": "onedesk.one_crm.stages.follow",
	},
	"Sales Order": {
		# Starts with its quotation's or its project's terms, and its project's
		# retention. See one_project/terms.py and retention.py.
		"before_insert": ["onedesk.one_project.terms.carried", "onedesk.one_project.retention.ordered"],
		"validate": "onedesk.one_project.chain.agree",
		"on_submit": [
			"onedesk.one_crm.stages.follow",
			# An order for extra work becomes a sub-project. See one_project/billing.py.
			"onedesk.one_project.billing.ordered",
		],
		"on_cancel": "onedesk.one_crm.stages.follow",
		# A new Retention Due moves the retention on its invoices. See one_project/progress.py.
		"on_update_after_submit": "onedesk.one_project.progress.release",
	},
	# Submitting is the approval, and it says which shift. See one_hr/shift.py.
	"Shift Request": {
		"before_validate": "onedesk.one_hr.shift.before_validate",
		"before_submit": "onedesk.one_hr.shift.before_submit",
	},
}

# A form's timeline lists only the mail its reader may open: a link to a
# record never grants read. See one_mail/linking.py.
override_whitelisted_methods = {
	"frappe.desk.form.load.getdoc": "onedesk.one_mail.linking.getdoc",
	"frappe.desk.form.load.get_docinfo": "onedesk.one_mail.linking.get_docinfo",
	"frappe.desk.form.load.get_communications": "onedesk.one_mail.linking.get_communications",
	# The credit limit dialog tells the credit controllers in One. See one_book/tell.py.
	"erpnext.selling.doctype.customer.customer.send_emails": "onedesk.one_book.tell.credit_limit",
	# A changed password tells the person, always by mail. See one/signin.py.
	"frappe.core.doctype.user.user.update_password": "onedesk.one.signin.update_password",
	# On the admin site the mailed sign-in link is for One accounts only, and
	# in our words. Anywhere else it is frappe's. See one_admin/accounts.py.
	"frappe.www.login.send_login_link": "onedesk.one_admin.accounts.send_login_link",
	# The builder previews a format before it is saved; a workspace's is checked as
	# its save would be. See one/printing.py.
	"frappe.utils.print_format_generator.render_builder_preview": "onedesk.one.printing.render_builder_preview",
	"frappe.utils.print_format_generator.download_builder_preview_pdf": "onedesk.one.printing.download_builder_preview_pdf",
	"frappe.utils.print_format_generator.render_jinja_template": "onedesk.one.printing.render_jinja_template",
	# A template picked in OneMail's composer, which has no form behind it, is filled
	# in from the record read here. See one/mail_templates.py.
	"frappe.email.doctype.email_template.email_template.get_email_template": "onedesk.one.mail_templates.get_email_template",
	# A person in a link reads as their name to whoever may pick them, not
	# only to whoever may read their User. See one/link_titles.py.
	"frappe.desk.search.get_link_title": "onedesk.one.link_titles.get_link_title",
}

# What Intake wrote down about a record is its history, not a reason to keep
# the record: deleting a supplier OneAI made, or undoing it, is not blocked by
# the Intake Action that made it. See one_intake/act.py.
ignore_links_on_delete = ["Intake Action", "Intake Lesson", "Reading", "Reading Party"]

has_permission = {
	# The Recycle Bin: one's own deletions, and an administrator's readable kinds.
	# See one/recycle.py.
	"Deleted Document": "onedesk.one.recycle.has_permission",
	# The Audit Log: an administrator's, of what they may read. See one/audit.py.
	"Version": "onedesk.one.audit.has_permission",
	"Activity Log": "onedesk.one.audit.has_permission",
	"Access Log": "onedesk.one.audit.has_permission",
	# Webhooks, on the kinds the administrator may read. See one/webhooks.py.
	"Webhook": "onedesk.one.webhooks.has_permission",
	"Assignment Rule": "onedesk.one_crm.access.has_permission",
	"Webhook Request Log": "onedesk.one.webhooks.has_permission",
	# Deleting somebody's account is decided by an administrator, never by
	# editing the request. See one/privacy.py.
	"Personal Data Deletion Request": "onedesk.one.privacy.has_permission",
	"Personal Data Download Request": "onedesk.one.privacy_copy.has_permission",
	# What OneAI did is seen by whom it acted for. See one_intake/act.py.
	"Intake Action": "onedesk.one_intake.act.has_permission",
	# A message opens for its mailbox's holders only.
	# See one_mail/access.py.
	"Communication": "onedesk.one_mail.access.allowed",
	# A mailbox's rules are its holders'. See one_mail/rules.py.
	"Mail Rule": "onedesk.one_mail.rules.rule_allowed",
	"Employee Grievance": "onedesk.one_hr.ai_grievance.allowed",
	# Everybody keeps tasks; a task with no project is its own people's.
	# See one_task/access.py.
	"Task": "onedesk.one_task.access.allowed",
	# A project is its members'. See one_project/members.py.
	"Project": "onedesk.one_project.members.allowed",
	# The operator console answers only on the admin site, whatever roles a
	# tenant gives itself. See one_admin/site.py.
	"AI Model": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Credit Ledger Entry": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Credit Reservation": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Account Request": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Offering": "onedesk.one_admin.site.refuse_on_a_tenant",
	"One Admin Settings": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Provisioning Job": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Stripe Webhook Event": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant Domain": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant Event": "onedesk.one_admin.site.refuse_on_a_tenant",
}

# Every list, report and link search goes through this one. The hook above is
# only called when there is a document, so on its own it guarded the form and
# left get_list wide open — measured, not assumed.
permission_query_conditions = {
	"Deleted Document": "onedesk.one.recycle.query",
	"Version": "onedesk.one.audit.version_query",
	"Activity Log": "onedesk.one.audit.activity_query",
	"Access Log": "onedesk.one.audit.access_query",
	"Webhook": "onedesk.one.webhooks.query",
	"Assignment Rule": "onedesk.one_crm.access.query",
	"Webhook Request Log": "onedesk.one.webhooks.log_query",
	"Personal Data Deletion Request": "onedesk.one.privacy.query",
	"Personal Data Download Request": "onedesk.one.privacy_copy.query",
	"Intake Action": "onedesk.one_intake.act.query",
	"Mail Rule": "onedesk.one_mail.rules.rule_query",
	"Employee Grievance": "onedesk.one_hr.ai_grievance.query",
	"Task": "onedesk.one_task.access.query",
	"Project": "onedesk.one_project.members.query",
	"AI Model": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Credit Ledger Entry": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Credit Reservation": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Account Request": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Offering": "onedesk.one_admin.site.nothing_on_a_tenant",
	"One Admin Settings": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Provisioning Job": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Stripe Webhook Event": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant Domain": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant Event": "onedesk.one_admin.site.nothing_on_a_tenant",
}

# Ctrl+K finds documents by what is written in them. See one_intake/search.py.
awesomebar_search = ["onedesk.one_intake.search.awesomebar"]

fixtures = [
	"Custom Icon",
	"Clock Reason",
	"Attendance Reason",
	"Identification Document Type",
	# What a model may be asked to do, and the instruction it is asked with.
	# A fixture so a new one arrives with a migrate and an edit survives the next.
	"AI Action",
	# An Opportunity is called a Deal, in every language One ships. Translation
	# rows rather than a catalogue, so a workspace can change the word back.
	{"dt": "Translation", "filters": [["name", "like", "one-deal-%"]]},
	# The tracker that dates every move of an opportunity's stage.
	{"dt": "Milestone Tracker", "filters": [["name", "=", "Opportunity-sales_stage"]]},
	# One list of reasons a deal is lost, on a deal and on its quotation alike.
	{"dt": "Opportunity Lost Reason", "filters": [["name", "in", ["Price", "Went With a Competitor", "No Budget", "No Decision", "Timing", "Not a Fit", "Other"]]]},
	{"dt": "Quotation Lost Reason", "filters": [["name", "in", ["Price", "Went With a Competitor", "No Budget", "No Decision", "Timing", "Not a Fit", "Other"]]]},
	# Where a lead from the web form says it came from.
	{"dt": "UTM Source", "filters": [["name", "=", "Website"]]},
	# One's Home, the part for administrators: what in the workspace needs them
	# (one/home.py, attention). A block has no module to be standard in.
	# OneAdmin's Home, the operator's list of what needs them (one_admin/home.py).
	{"dt": "Custom HTML Block", "filters": [["name", "in", ["One Needs You", "OneAdmin Needs You"]]]},
]


# A record answers before it offers links; see `onedesk/one_hr/employee.py`.
doctype_js = {
	# What a workspace's webhook may not do is not offered. See one/webhooks.py.
	"Webhook": "public/js/webhook.js",
	# An announcement, as the administrator writes it. See one/announcements.py.
	"Note": "public/js/note.js",
	# Put back through One's restore, which a workspace may use. See one/recycle.py.
	"Deleted Document": "public/js/deleted_document.js",
	# Approve and Delete, or Hold, by a workspace administrator. See one/privacy.py.
	"Personal Data Deletion Request": "public/js/privacy_request.js",
	# Invite to Portal, and taking it back. See one/portal_invite.py.
	"Contact": "public/js/contact.js",
	# Review a copy of somebody's data, kind by kind, then send it. See one/privacy_copy.py.
	"Personal Data Download Request": "public/js/privacy_copy.js",
	# A workspace is read-only and carries verbs instead; see one_admin/operator.py.
	# A workspace reads its own account and manages its addresses; the account
	# itself lives on the administrator. See one/account.py.
	"Workspace Account": "public/js/workspace_account.js",
	"Tenant": "public/js/tenant.js",
	# A paid signup that never became a workspace can be built from its screen.
	"Account Request": "public/js/account_request.js",
	"Credit Ledger Entry": "public/js/credit_ledger_entry.js",
	# A price list says how many workspaces already bought what is being edited.
	"Offering": "public/js/offering.js",
	# The gateway is the one credential here with nothing that later proves it.
	"One Admin Settings": "public/js/admin_settings.js",
	# What is charged on top, and what one call actually comes to.
	"AI Model": "public/js/ai_model.js",
	# The model list comes from the account, filtered to what the action needs.
	"AI Action Setting": "public/js/ai_action_setting.js",
	"Employee": "public/js/employee.js",
	"Employee Attendance Tool": "public/js/attendance_tool.js",
	"Attendance": "public/js/attendance.js",
	"Clock Network": "public/js/learned.js",
	"Clock Place": "public/js/learned.js",
	"Attendance Request": "public/js/attendance_request.js",
	"Shift Request": "public/js/shift_request.js",
	"Overtime Slip": "public/js/overtime_slip.js",
	"Timesheet": "public/js/timesheet.js",
	"Leave Control Panel": "public/js/leave_control_panel.js",
	# The interview recorder; see one_hr/hiring.py.
	"Interview": "public/js/hiring.js",
	"Opportunity": "public/js/opportunity.js",
	# Next Step Done, which asks what comes next. See public/js/next_step.js.
	"Lead": "public/js/lead.js",
	# The project's board is a button of its own. See one_project/board.py.
	# What the form and the project's page both do is project_actions.js.
	"Project": ["public/js/project_actions.js", "public/js/project.js"],
	# An activity's rates for a person are its connection (one_project/rates.py).
	"Activity Type": "public/js/activity_type.js",
	"Project Template": "public/js/project_template.js",
	# Bill Progress on a subcontract and on the customer's contract. See one_project/progress.py.
	"Purchase Order": "public/js/progress.js",
	"Quotation": "public/js/quotation.js",
	# A customer's one open project is named on a new order, delivery or
	# invoice. See one_project/chain.py.
	"Sales Order": ["public/js/progress.js", "public/js/customer_project.js"],
	"Delivery Note": "public/js/customer_project.js",
	"Sales Invoice": "public/js/customer_project.js",
	# A timer on the task. See one_task/timer.py.
	"Task": "public/js/task.js",
}

# Loaded after the doctype's own list script, so ours has the last word.
# The Projects list as a tree and on a timeline: frappe's Tree and Gantt views.
# See one_project/tree.py.
doctype_tree_js = {"Project": "public/js/project_tree.js"}
doctype_calendar_js = {"Project": "public/js/project_calendar.js"}
doctype_kanban_js = {"Project": "public/js/project_kanban.js"}

doctype_list_js = {
	"Deleted Document": "public/js/deleted_document_list.js",
	# From the Library, beside Add. See one_project/library.py.
	"Project Template": "public/js/project_template_list.js",
	# Its columns say who, which project and how long; the ID is on hover.
	"Timesheet": "public/js/timesheet_list.js",
	# The Audit Log's three lists, as One's sidebar names them. See one/audit.py.
	"Version": "public/js/audit_list.js",
	"Activity Log": "public/js/audit_list.js",
	"Access Log": "public/js/audit_list.js",
	"Personal Data Deletion Request": "public/js/privacy_request_list.js",
	"Personal Data Download Request": "public/js/privacy_copy_list.js",
	# Nothing on the catalogue is typed; its only verb is to sync it now.
	"AI Model": "public/js/ai_model_list.js",
	# Which way each row moved money, which is all a ledger list is for.
	"Credit Ledger Entry": "public/js/credit_ledger_entry_list.js",
	# A queue: the one thing a row says is whether anybody still has to answer it.
	"AI Proposal": "public/js/ai_proposal_list.js",
	"Attendance": "public/js/attendance_list.js",
	"Employee Checkin": "public/js/checkin_list.js",
	"Opportunity": "public/js/opportunity_list.js",
	"Lead": "public/js/lead_list.js",
	# A due date is a day, red once passed. See public/js/task_list.js.
	"Task": "public/js/task_list.js",
	# A project's status is its status, and its manager a name.
	"Project": "public/js/project_list.js",
	# Whether a contract is signed, and the project it is for by name.
	"Contract": "public/js/contract_list.js",
}

override_doctype_dashboards = {
	"Attendance": ["onedesk.one_hr.attendance.dashboard"],
	# A task's sub-tasks, as a connection. See one_task/task.py.
	"Task": ["onedesk.one_task.task.dashboard"],
	# A project's sub-projects, the same way. See one_project/tree.py.
	"Project": ["onedesk.one_project.tree.dashboard"],
	# An activity's rates for each person, under the activity. See one_project/rates.py.
	"Activity Type": ["onedesk.one_project.rates.dashboard"],
}

# Every shift location counts, not the first. See one_hr/checkin.py.
override_doctype_class = {
	"Employee Checkin": "onedesk.one_hr.checkin.OneEmployeeCheckin",
	# Time logged for somebody without an account. See one_hr/timesheet.py.
	"Timesheet": "onedesk.one_hr.timesheet.OneTimesheet",
	# A stored file's content is read back from R2. See one_storage/file.py.
	"File": "onedesk.one_storage.file.CloudFile",
	# A rule a workspace builds is held to what it may do. See one/rules.py.
	"Notification": "onedesk.one.rules.Rule",
	# HRMS's approvals and a moved interview, told through the hub. See one_hr/tell.py.
	"Leave Application": "onedesk.one_hr.tell.LeaveApplication",
	"Expense Claim": "onedesk.one_hr.tell.ExpenseClaim",
	"Shift Request": "onedesk.one_hr.tell.ShiftRequest",
	"Interview": "onedesk.one_hr.tell.Interview",
}

# Every new file's content goes to R2 through admin's signed URLs, and is
# dropped from there when the last File naming it goes. See one_storage/store.py.
write_file = "onedesk.one_storage.store.write"
delete_file_data_content = "onedesk.one_storage.store.delete"

add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"logo": app_logo_url,
		"route": "/desk/one",
		# A customer signing in goes to the portal, not a desk they cannot open.
		"has_permission": "onedesk.check_app_permission",
		# Ahead of erpnext (1) and hrms (2). Not 0: the boot reads this with `or`,
		# so a falsy one falls through to the default and lands One mid-row.
		"sequence_id": 0.5,
	}
]

# An account signing in on the admin site lands on /account, not frappe's
# /portal. See one_admin/accounts.py.
get_website_user_home_page = "onedesk.one_admin.accounts.home_page"

# `setup_wizard_url` is ignored while erpnext or hrms are installed.
# Reaches the login page: base.html renders these and login.html extends it.
web_include_js = ["/assets/onedesk/js/login.js"]

setup_wizard_requires = "assets/onedesk/js/setup_wizard.js"
setup_wizard_stages = "onedesk.one.setup_wizard.get_setup_stages"

app_include_css = [
	"/assets/onedesk/css/theme.css",
	"/assets/onedesk/css/desk.css",
	# The shell every page of ours is built in. See docs/SHELL.md.
	"/assets/onedesk/css/shell.css",
	"/assets/onedesk/css/oneai.css",
	"/assets/onedesk/css/legal.css",
	"/assets/onedesk/css/intake.css",
	# Not found, no access and errors, on the desk and off it.
	"/assets/onedesk/css/lost.css",
]
# /start and /welcome, which are not desk screens and load none of the above.
web_include_css = ["/assets/onedesk/css/portal.css", "/assets/onedesk/css/lost.css"]
# Screens drawn with frappe-ui inside desk pages are named by their entry in
# frontend/build-islands.mjs, and mounted by onedesk.island_page. docs/ISLANDS.md.

app_include_js = [
	"/assets/onedesk/js/theme.js",
	# "One" of a product's name at a light weight, wherever it is drawn.
	"/assets/onedesk/js/brand.js",
	"/assets/onedesk/js/check.js",
	"/assets/onedesk/js/size.js",
	"/assets/onedesk/js/desk.js",
	# A record on a page of its own keeps its form's menu and sidebar. See record.js.
	"/assets/onedesk/js/record.js",
	# What of frappe's own desk a workspace is not offered; see one/outside.py.
	"/assets/onedesk/js/outside.js",
	"/assets/onedesk/js/shell.js",
	"/assets/onedesk/js/passkey.js",
	"/assets/onedesk/js/clock.js",
	"/assets/onedesk/js/overtime.js",
	"/assets/onedesk/js/next_step.js",
	"/assets/onedesk/js/task_timer.js",
	# New Task, OneTask's own dialog. See task_new.js.
	"/assets/onedesk/js/task_new.js",
	"/assets/onedesk/js/record_calendar.js",
	# The calendar link, drawn once for Settings and OneCalendar's Subscribe.
	"/assets/onedesk/js/calendar_link.js",
	# A record's tabs after its fields, declared under one_record_tabs.
	"/assets/onedesk/js/record_tabs.js",
	"/assets/onedesk/js/record_files.js",
	"/assets/onedesk/js/extension_errors.js",
	"/assets/onedesk/js/record_mail.js",
	"/assets/onedesk/js/record_activity.js",
	"/assets/onedesk/js/mail_compose.js",
	"/assets/onedesk/js/onecloud_picker.js",
	"/assets/onedesk/js/band.js",
	# New Project, by kind: frappe's quick entry for Project. See one_project/kinds.py.
	"/assets/onedesk/js/island_page.js",
	"/assets/onedesk/js/project_new.js",
	# Where the panel is not out, the breadcrumb is the menu of the module's places. See public/js/panel_menu.js.
	"/assets/onedesk/js/panel_menu.js",
	# A project's name in its breadcrumb lists the other projects. See public/js/project_places.js.
	"/assets/onedesk/js/project_places.js",
	# Frappe's Settings dialog for a doctype, for a workspace administrator.
	"/assets/onedesk/js/doctype_settings.js",
	# Extensions on One's own pages: OneMail, OneCalendar, a record's head. See one_studio/places.py.
	"/assets/onedesk/js/places.js",
	# Every record's head, from its Record Head. See one/head.py.
	"/assets/onedesk/js/head.js",
	"/assets/onedesk/js/crm_record.js",
	"/assets/onedesk/js/reports.js",
	# A chart's colours follow its labels. See public/js/chart_colors.js.
	"/assets/onedesk/js/chart_colors.js",
	"/assets/onedesk/js/oneai.js",
	"/assets/onedesk/js/intake.js",
	"/assets/onedesk/js/legal.js",
]

# Modules with no place of their own, and where their navigation went.
code_only_modules = {"One AI": ["One"], "One Legal": ["One"]}

# Kinds of record a module's code makes without a name or a model to ask; Numbering keeps them
# nameable by it. Intake is not here: it asks OneAI for what is missing (one_intake/fill.py).
one_makes_records = {
	"Account": ["one", "one_admin", "one_book"],
	"Activity Type": ["one_project"],
	"Address": ["one", "one_book"],
	"Appraisal": ["one_hr"],
	"Asset": ["one_inventory"],
	"Asset Category": ["one_inventory"],
	"Asset Maintenance Log": ["one_inventory"],
	"Asset Maintenance Team": ["one_inventory"],
	"Asset Movement": ["one_inventory"],
	"Attendance Request": ["one_hr"],
	"Bank": ["one_book"],
	"Bank Account": ["one_book"],
	"Budget": ["one_project"],
	"Call Log": ["one_crm"],
	"Contact": ["one_admin", "one_calendar"],
	"Contract": ["one_project"],
	"Customer": ["one_admin", "one_book", "one_crm"],
	"Employee": ["one_hr"],
	"Employee Checkin": ["one_hr"],
	"Employee Performance Feedback": ["one_hr"],
	"Employee Promotion": ["one_hr"],
	"Employee Tax Exemption Declaration": ["one_hr"],
	"Employee Tax Exemption Proof Submission": ["one_hr"],
	"Exit Interview": ["one_hr"],
	"Expense Claim": ["one_hr"],
	"Fiscal Year": ["one_book"],
	"Holiday List": ["one", "one_hr"],
	"Holiday List Assignment": ["one"],
	"Interview": ["one_hr"],
	"Interview Feedback": ["one_hr"],
	"Item": ["one", "one_admin", "one_inventory", "one_project"],
	"Item Group": ["one_admin"],
	"Job Applicant": ["one_hr"],
	"Job Opening": ["one_hr"],
	"Journal Entry": ["one_admin"],
	"Lead": ["one_admin", "one_crm"],
	"Leave Application": ["one_hr"],
	"Leave Encashment": ["one_hr"],
	"Leave Period": ["one"],
	"Location": ["one_inventory"],
	"Mode of Payment": ["one_admin"],
	"Opportunity": ["one_admin", "one_crm"],
	"Opportunity Lost Reason": ["one_admin", "one_crm"],
	"Overtime Slip": ["one_hr"],
	"Payment Term": ["one_project"],
	"Payment Terms Template": ["one_project"],
	"Payroll Entry": ["one_hr"],
	"Payroll Period": ["one"],
	"Period Closing Voucher": ["one_book"],
	"Project": ["one_project"],
	"Project Template": ["one_project"],
	"Project Type": ["one_hr"],
	"Project Update": ["one_project"],
	"Purchase Invoice": ["one"],
	"Purchase Order": ["one_inventory"],
	"Salary Slip": ["one_hr"],
	"Sales Invoice": ["one_admin", "one_project"],
	"Sales Order": ["one_project"],
	"Sales Stage": ["one_admin", "one_crm"],
	"Shift Request": ["one_hr"],
	"Shift Type": ["one", "one_hr"],
	"Supplier": ["one", "one_book"],
	"Supplier Quotation": ["one"],
	"Task": ["one_project", "one_task"],
	"Terms and Conditions": ["one_project"],
	"Timesheet": ["one_project", "one_task"],
	"UAE VAT Settings": ["one_book"],
	"UOM": ["one_project"],
	"Vehicle Log": ["one_hr"],
	"Warehouse": ["one_inventory"],
}

# What OneAI can do in each module, owned by the module, from its ai.py.
# See one_ai/tools.py and one_ai/suggest.py.
one_ai_reads = [
	# How records are numbered, for the workspace's administrators. See one/numbering.py.
	"onedesk.one.ai.workspace_numbering",
	"onedesk.one.ai.workspace_printing",
	# The mail templates, what each is for and which setting sends it. See one/mail_templates.py.
	"onedesk.one.ai.workspace_mail_templates",
	# The approvals, their states and steps, and what an approval may use. See one/approvals.py.
	"onedesk.one.ai.workspace_approvals",
	# The automations, what starts each and what it does. See one/automations.py.
	"onedesk.one.ai.workspace_automations",
	"onedesk.one.ai.print_layout",
	# How the person signs in, and where they are signed in. See one/signin.py.
	"onedesk.one.ai.my_sign_in",
	"onedesk.one.ai.my_memories",
	# How everybody signs in, for the workspace's administrators.
	"onedesk.one.ai.workspace_sign_in",
	"onedesk.one.ai.workspace_people",
	# Levels, profiles, groups and who is held to which records. See one/access.py.
	"onedesk.one.ai.workspace_access",
	# Saved reports, dashboards and reports by mail. See one/reports.py.
	"onedesk.one.ai.workspace_reports",
	# What was deleted, as the reader may see it. See one/recycle.py.
	"onedesk.one.ai.recycle_bin",
	# Who changed, signed in and exported what. See one/audit.py.
	"onedesk.one.ai.audit_log",
	# The workspace's webhooks and how their calls went. See one/webhooks.py.
	"onedesk.one.ai.webhooks",
	# Announcements and who has read them. See one/announcements.py.
	"onedesk.one.ai.announcements",
	# What deleting somebody's account would do. See one/privacy.py.
	"onedesk.one.ai.privacy_request",
	# The plan and the credits, for the workspace's administrators.
	"onedesk.one.ai.workspace_plan",
	# The addresses the workspace opens at, for its administrators.
	"onedesk.one.ai.workspace_domains",
	# OneAI's actions, their models and what they cost, for the administrators.
	"onedesk.one.ai.workspace_oneai",
	# OneIntake's settings and its month, for the administrators.
	"onedesk.one.ai.workspace_intake",
	# The holiday list in force, when it ends and what follows it.
	"onedesk.one.ai.workspace_holidays",
	# What waits for the reader today, as Home counts it.
	"onedesk.one.ai.my_day",
	# A conversation the reader holds, and what in a folder waits for an answer.
	"onedesk.one_mail.ai.open_conversation",
	"onedesk.one_mail.ai.waiting_for_answer",
	# The reader's calendar, and when colleagues are busy. See one_calendar/ai.py.
	"onedesk.one_calendar.ai.my_calendar",
	# The reader's tasks, as My Tasks shows them. See one_task/ai.py.
	"onedesk.one_task.ai.my_tasks",
	# What needs the operator, as OneAdmin's Home lists it. See one_admin/ai.py.
	"onedesk.one_admin.ai.console_today",
	"onedesk.one_admin.ai.workspace_facts",
	"onedesk.one_admin.ai.job_facts",
	"onedesk.one_admin.ai.signup_facts",
	"onedesk.one_admin.ai.credit_facts",
	"onedesk.one_admin.ai.model_facts",
	"onedesk.one_admin.ai.ai_usage",
	"onedesk.one_admin.ai.settings_check",
	"onedesk.one_admin.ai.domain_facts",
	"onedesk.one_admin.ai.price_list",
	"onedesk.one_admin.ai.price_check",
	"onedesk.one_admin.ai.plan_quote",
	"onedesk.one_calendar.ai.busy_times",
	# A file's text, who can see it, and what takes the space. See one_storage/ai.py.
	"onedesk.one_storage.ai.open_file",
	"onedesk.one_storage.ai.who_can_see",
	"onedesk.one_storage.ai.largest_files",
	# Documents by what they say, and what they are. See one_intake/ai.py.
	"onedesk.one_intake.ai.find_documents",
	"onedesk.one_hr.ai.my_leave",
	"onedesk.one_hr.ai.appraisal_facts",
	"onedesk.one_hr.ai.why_people_leave",
	"onedesk.one_hr.ai.interview_facts",
	"onedesk.one_hr.ai_payroll.payroll_changes",
	"onedesk.one_hr.ai_letters.letter_facts",
	"onedesk.one_hr.ai_policy.hr_policy",
	"onedesk.one_hr.ai_growth.goal_facts",
	"onedesk.one_hr.ai_growth.training_options",
	# A project as its page shows it, and which projects need attention. See one_project/ai.py.
	"onedesk.one_project.ai.project_facts",
	"onedesk.one_project.ai.projects_needing_attention",
	"onedesk.one_project.ai.project_templates",
	"onedesk.one_crm.ai.deal_facts",
	"onedesk.one_crm.ai.lead_facts",
	"onedesk.one_crm.ai.gone_quiet",
	"onedesk.one_crm.ai.why_we_lose",
	"onedesk.one_legal.ai.agreement",
	"onedesk.one.ai.notification_type",
	"onedesk.one.ai.my_notifications",
	"onedesk.one.ai.my_mailboxes",
	"onedesk.one_studio.ai.extensions_here",
	"onedesk.one_studio.ai.extension_mistakes",
	"onedesk.one_studio.ai.extension_code",
	"onedesk.one_studio.ai.extension_places",
	"onedesk.one_studio.ai.record_types_here",
	"onedesk.one_studio.ai.forms_here",
	"onedesk.one_studio.ai.form_relations",
]

#: A sentence each about who is asking, added to what the model is told.
one_ai_reader = ["onedesk.one_hr.ai.reader"]

#: A sentence each about the workspace itself, added to what the model is told.
one_ai_workspace = ["onedesk.one_hr.ai.workspace", "onedesk.one_crm.ai.workspace"]
one_ai_suggests = [
	"onedesk.one_hr.ai.claim_expense",
	"onedesk.one_hr.ai.book_leave",
	"onedesk.one_hr.ai.add_applicant",
	"onedesk.one_hr.ai.draft_feedback",
	"onedesk.one_hr.ai.draft_interview_feedback",
	"onedesk.one_hr.ai_letters.request_letter",
	"onedesk.one_hr.ai_growth.draft_goal",
	"onedesk.one_crm.ai.add_lead",
	# The reader's update on a project, put under Updates to post. See one_project/ai.py.
	"onedesk.one_project.ai.draft_update",
	# A project template, made when the reader approves. See one_project/library.py.
	"onedesk.one_project.ai.draft_template",
	"onedesk.one_crm.ai.plan_next_step",
	"onedesk.one_crm.ai.write_up_call",
	"onedesk.one.ai.rewrite_notification",
	"onedesk.one.ai.draft_notification",
	"onedesk.one.ai.change_numbering",
	"onedesk.one.ai.change_printing",
	"onedesk.one.ai.design_print_format",
	"onedesk.one.ai.write_mail_template",
	"onedesk.one.ai.suggest_approval",
	"onedesk.one.ai.suggest_automation",
	# Saved reports, dashboards, reports by mail, levels, profiles, groups and
	# what a person sees, each a card. See one/ai_setup.py.
	"onedesk.one.ai_setup.suggest_saved_report",
	"onedesk.one.ai_setup.suggest_dashboard",
	"onedesk.one.ai_setup.suggest_report_mail",
	"onedesk.one.ai_setup.suggest_level",
	"onedesk.one.ai_setup.suggest_profile",
	"onedesk.one.ai_setup.suggest_group",
	"onedesk.one.ai_setup.suggest_hold",
	"onedesk.one.ai.customize",
	"onedesk.one.ai.sign_mailbox",
	# Holidays and days off, as the Holidays settings would save them.
	"onedesk.one.ai.change_holidays",
	# A reply, written as the reader asked, opened in the email window to send.
	"onedesk.one_mail.ai.draft_reply",
	# A rule that sorts a mailbox's new mail into a folder. See one_mail/rules.py.
	"onedesk.one_mail.ai.suggest_mail_rule",
	# An event, with the people on it, made when the reader approves.
	"onedesk.one_calendar.ai.plan_event",
	# A task, and the steps of a task's checklist. See one_task/ai.py.
	"onedesk.one_task.ai.plan_task",
	"onedesk.one_task.ai.plan_steps",
	"onedesk.one_studio.ai.write_extension",
	"onedesk.one_studio.ai.mend_extension",
	"onedesk.one_studio.ai.design_record_type",
]
# One's own steps for frappe's automation engine: Tell People. See one/automation_steps.py.
automation_actions = ["onedesk.one.automation_steps.TellPeople"]

one_ai_suggestions = [
	"onedesk.one_hr.ai.SUGGESTIONS",
	"onedesk.one_crm.ai.SUGGESTIONS",
	"onedesk.one.ai.SUGGESTIONS",
	"onedesk.one_mail.ai.SUGGESTIONS",
	"onedesk.one_storage.ai.SUGGESTIONS",
	"onedesk.one_calendar.ai.SUGGESTIONS",
	"onedesk.one_task.ai.SUGGESTIONS",
	"onedesk.one_project.ai.SUGGESTIONS",
	"onedesk.one_admin.ai.SUGGESTIONS",
	"onedesk.one_studio.ai.SUGGESTIONS",
]

one_ai_page = [
	"onedesk.one.ai.page",
	"onedesk.one_mail.ai.page",
	"onedesk.one_storage.ai.page",
	"onedesk.one_calendar.ai.page",
	"onedesk.one_task.ai.page",
	"onedesk.one_admin.ai.page",
	"onedesk.one_project.ai.page",
]

# Kinds of record whose home is one of a module's pages rather than their own
# list, as {doctype: [crumb, ...]} for the reader: a form's trail leads back
# there. See one/homes.py.
one_homes = ["onedesk.one.masters.homes", "onedesk.one_project.rates.homes"]

# Every notification and mail One sends, one file each, by module, in
# onedesk/notifications/. Another app may add its own. See one/notify.py.
one_notification_types = ["onedesk.notifications.TYPES"]

# What a record's form says above its fields, as rows: each module's heads,
# the measures they place and the verbs they offer. See one/head.py.
one_record_heads = [
	"onedesk.one_inventory.heads.HEADS",
	"onedesk.one_book.heads.HEADS",
	"onedesk.one_crm.heads.HEADS",
	"onedesk.one_project.heads.HEADS",
	"onedesk.one_hr.heads.HEADS",
	"onedesk.one.heads.HEADS",
	"onedesk.one_admin.heads.HEADS",
	"onedesk.one_ai.heads.HEADS",
	"onedesk.one_studio.heads.HEADS",
]
one_measures = [
	"onedesk.one_inventory.heads.MEASURES",
	"onedesk.one_book.heads.MEASURES",
	"onedesk.one_crm.heads.MEASURES",
	"onedesk.one_project.heads.MEASURES",
	"onedesk.one_hr.heads.MEASURES",
	"onedesk.one.heads.MEASURES",
	"onedesk.one_admin.heads.MEASURES",
	"onedesk.one_ai.heads.MEASURES",
	"onedesk.one_studio.heads.MEASURES",
]
one_verbs = [
	"onedesk.one_inventory.heads.VERBS",
	"onedesk.one_book.heads.VERBS",
	"onedesk.one_crm.heads.VERBS",
	"onedesk.one_hr.heads.VERBS",
	"onedesk.one_admin.heads.VERBS",
	"onedesk.one_ai.heads.VERBS",
	"onedesk.one_studio.heads.VERBS",
]
one_charts = [
	"onedesk.one_inventory.heads.CHARTS",
	"onedesk.one_book.heads.CHARTS",
	"onedesk.one_project.heads.CHARTS",
	"onedesk.one_hr.heads.CHARTS",
]
# The tabs after a record's fields, each drawn by its module. See one/tabs.py.
one_record_tabs = [
	"onedesk.one_mail.linking.TABS",
	"onedesk.one_storage.namespace.TABS",
	"onedesk.one.tabs.TABS",
	"onedesk.one_studio.mend.TABS",
]

# What each module puts on the calendar, as layers. Each reads its own records
# as the person looking; nothing is copied. See one_calendar/layers.py.
one_calendar_layers = [
	"onedesk.one_calendar.events.LAYERS",
	"onedesk.one_task.calendar.LAYERS",
	"onedesk.one_project.calendar.LAYERS",
	"onedesk.one_crm.calendar.LAYERS",
	"onedesk.one_hr.calendar.LAYERS",
	"onedesk.one_inventory.calendar.LAYERS",
	"onedesk.one_intake.calendar.LAYERS",
]

# A project's updates in its activity, under who wrote them. See one_project/updates.py.
additional_timeline_content = {
	"Project": ["onedesk.one_project.updates.timeline"],
	# A workspace's log in its Activity. See one_admin/log.py.
	"Tenant": ["onedesk.one_admin.log.timeline"],
}

# A OneCloud link: /s/<token> is www/s.py, for somebody with no account.
website_route_rules = [
	{"from_route": "/s/<token>", "to_route": "s"},
	# A file request: /r/<token> is www/r.py.
	{"from_route": "/r/<token>", "to_route": "r"},
	# The agreements, readable before anybody has an account: /legal/terms is
	# www/legal.py, and /start links to it.
	{"from_route": "/legal/<document>", "to_route": "legal"},
	# A One account's invoices: www/account_invoices.py.
	{"from_route": "/account/invoices", "to_route": "account_invoices"},
	{"from_route": "/account/profile", "to_route": "account_profile"},
	# Your Data, for somebody who is not a user: www/your_data.py.
	{"from_route": "/your-data", "to_route": "your_data"},
]

# frappe's account deletion form: everybody asks under Your Data instead,
# where the request is confirmed and decided as One decides it (one/privacy.py).
website_redirects = [{"source": r"/request-for-account-deletion.*", "target": "/your-data"}]

# OneCloud as a network drive (one_storage/dav.py), and frappe's webhook
# sender kept off internal addresses (one/webhooks.py).
before_request = ["onedesk.one_storage.dav.sign_in", "onedesk.one.webhooks.install"]
before_job = ["onedesk.one.webhooks.install"]
after_request = ["onedesk.one_storage.dav.headers"]

# A workspace's HTML block prints through One's sandbox: onedesk's copy of frappe's
# HTML block macro calls this for a block the workspace saved. See one/print_html.py.
jinja = {
	"methods": [
		"onedesk.one.print_html.one_html_block",
		# What One's print blocks show, in templates/one_print/. See one/print_blocks.py.
		"onedesk.one.print_blocks.one_print_block",
		# The portal's tabs, its home and its pills. See one/portal.py.
		"onedesk.one.portal.one_portal_tabs",
		"onedesk.one.portal.one_portal_tone",
		"onedesk.one.portal.one_portal_home",
		"onedesk.one.portal.one_portal_record",
		"onedesk.one.portal.one_portal_rfq",
		"onedesk.one.portal.one_portal_status",
		"onedesk.one.portal.one_portal_quoted",
		"onedesk.one.portal.one_portal_add",
		"onedesk.one.portal.one_portal_timesheet",
		"onedesk.one.portal.one_portal_title",
		"onedesk.one.portal.one_portal_number",
		"onedesk.one_project.portal.one_portal_progress",
		"onedesk.one.portal.one_portal_here",
		"onedesk.one.portal.one_portal_account",
		"onedesk.one.portal.one_portal_at_home",
		"onedesk.one.portal.one_portal_me",
		"onedesk.one.portal.one_portal_columns",
	]
}


# What frappe's erasure redacts beyond its own list. See one/privacy.py.
user_data_fields = [
	{"doctype": doctype, "strict": True} for doctype in ("Deleted Document", "ToDo", "Notification Log")
] + [
	# An applicant who asks to be forgotten. A customer or supplier with the
	# address stays: their invoices are kept by law.
	{"doctype": "Job Applicant", "filter_by": "email_id", "redact_fields": ["applicant_name", "email_id", "phone_number"]},
]
