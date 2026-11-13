from onedesk.one.registry.hooks import heirs, hook, makers, settles
from onedesk.one.stamp import stamped

app_name = "onedesk"
app_title = "One"
app_publisher = "One"
app_description = "Every One product, as modules on the Frappe desk"
app_email = "hello@4dl.app"
app_license = "agpl-3.0"

required_apps = ["erpnext", "hrms"]

app_logo_url = "/assets/onedesk/images/one.svg"

after_sync = settles(install=True)

after_app_install = ["onedesk.account_center.private.installed_now"]

before_app_uninstall = ["onedesk.account_center.private.refuse_uninstall"]

after_migrate = settles(install=False)
extend_bootinfo = [
	"onedesk.one.boot.boot_session",
	"onedesk.one_project.retention.boot",
	"onedesk.one_admin.site.offer",
	"onedesk.one.announcements.boot",
	"onedesk.one_sheet.live.boot",
	"onedesk.one_studio.extensions.boot",
	"onedesk.one.apps.boot",
	"onedesk.one.rail.boot",
]

scheduler_events = {
	"cron": {
		"*/2 * * * *": ["onedesk.one_admin.runner.tick", "onedesk.one_admin.spares.keep", "onedesk.one_admin.sessions.tick", "onedesk.one_display.tell.long_waits", "onedesk.one_display.tell.past_limits"],
		"* * * * *": [
			"onedesk.one_mail.inbound.sweep",
			"onedesk.one_mail.sync.sync_all",
			"onedesk.one_ai.reading.matters.due",
			"onedesk.one_admin.oneos.tick",
			"onedesk.one_cloud.oneos.tick",
		],
		"*/15 * * * *": [
			"onedesk.one_admin.releases.tick",
			"onedesk.one_ai.reading.pipeline.again",
			"onedesk.one_ai.index.catch_up",
			"onedesk.one.announcements.ended",
		],
		"*/5 * * * *": [
			"onedesk.one_admin.servers.watch",
			"onedesk.one_admin.health.watch",
			"onedesk.one.backup.due",
			"onedesk.one_mail.team.due",
			"onedesk.one_hr.tell.interviews_soon",
			"onedesk.one_hr.tell.not_checked_in",
			"onedesk.one_calendar.tell.soon",
			"onedesk.one_crm.tell.due",
			"onedesk.one_crm.tell.answers_late",
			"onedesk.one_mail.tell.not_sent",
			"onedesk.one_display.tell.offline",
			"onedesk.one.news.fetching.due",
			"onedesk.one_admin.google_news.tick",
		],
		"15 9 * * *": ["onedesk.one_demo.living.day"],
		"20 1 * * *": ["onedesk.one_admin.backups.nightly"],
		"10 * * * *": ["onedesk.one_admin.releases.check", "onedesk.one_admin.health.watch_backups"],
		"40 1 * * *": ["onedesk.one.backup.nightly"],
		"45 6 * * *": ["onedesk.one_calendar.tell.today_events"],
		"40 6 * * *": ["onedesk.one_task.tell.today"],
		"30 6 * * *": [
			"onedesk.one_crm.tell.running_out",
			"onedesk.one_book.tell.overdue",
			"onedesk.one_inventory.tell.deliveries_late",
			"onedesk.one_factory.tell.back_late",
			"onedesk.one_factory.tell.late",
			"onedesk.one_quality.tell.overdue",
			"onedesk.one_crm.tell.contracts_ending",
			"onedesk.one_project.tell.milestones_late",
		],
		"25 6 * * 1": ["onedesk.one_book.tell.bills_due"],
		"35 6 * * *": [
			"onedesk.one_hr.tell.birthdays",
			"onedesk.one_hr.tell.anniversaries",
			"onedesk.one_hr.tell.feedback_due",
			"onedesk.one_hr.tell.documents_expiring",
			"onedesk.one_hr.tell.endings",
			"onedesk.one_hr.tell.leave_expiring",
		],
	},
	"daily": [
		"onedesk.one_ai.vectors.tidy",
		"onedesk.one_sheet.versions.tidy",
		"onedesk.one_doc.versions.tidy",
		"onedesk.account_center.devices.forget",
		"onedesk.one_admin.tell.trials_ending",
		"onedesk.one_admin.tell.servers_filling",
		"onedesk.one_admin.health.prune",
		"onedesk.one_admin.errors.today",
		"onedesk.one.tell.automations_failing",
		"onedesk.one_inventory.tell.orders_late",
		"onedesk.one_inventory.tell.expiring",
		"onedesk.one_inventory.tell.services",
		"onedesk.one.privacy.remind",
		"onedesk.one_project.retention.due",
		"onedesk.one_project.billing.bills_due",
		"onedesk.one_ai.reading.steps.daily",
		"onedesk.one_hr.holidays.daily",
		"onedesk.one_hr.periods.daily",
		"onedesk.one_mail.faces.again",
		"onedesk.one_mail.rules.cover",
		"onedesk.one_cloud.api.purge_old",
		"onedesk.one_cloud.store.daily",
		"onedesk.one_cloud.file_requests.remind_due",
		"onedesk.one.account.nightly",
		"onedesk.one_admin.domains.nightly",
		"onedesk.one_admin.lifecycle.nightly",
		"onedesk.one_admin.closing.due",
		"onedesk.one.webhooks.failing",
		"onedesk.one_studio.extensions.failing",
		"onedesk.one_admin.ledger.nightly",
		"onedesk.one_admin.topup.monthly",
		"onedesk.one_admin.storage.nightly",
		"onedesk.one_admin.sales.abandoned",
		"onedesk.one_admin.signup.abandon",
		"onedesk.one_admin.signup.remind",
		"onedesk.one_admin.books.catch_up",
		"onedesk.one_hr.healing.nightly",
		"onedesk.one_hr.hiring.purge",
		"onedesk.one_hr.leaving.nightly",
		"onedesk.one_hr.shift_setup.nightly",
		"onedesk.one_project.updates.sum_up",
	],
	"hourly": [
		"onedesk.one_hr.closing.hourly",
		"onedesk.one_project.updates.ask",
		"onedesk.one_mail.room.again",
		"onedesk.one_inventory.tell.stock_values",
		"onedesk.one_inventory.tell.reorder_failed",
		"onedesk.one.tell.repeats_failed",
		"onedesk.one_admin.tell.builds_slow",
		"onedesk.one.errors.pushed",
		"onedesk.one.copies.said",
		"onedesk.one_ai.brief.due",
	],
	"weekly": ["onedesk.one_ai.reading.digest.weekly", "onedesk.one_hr.tell.holidays_weekly"],
	"monthly": [
		"onedesk.one_hr.tell.holidays_monthly",
		"onedesk.one_project.tell.retainer_months",
	],
}

override_email_send = "onedesk.one_mail.outbound.send"

doc_events = {
	# A screen is woken to ask again when what it shows changes (one_display/live.py).
	"Display Screen": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Display Channel": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Widget Collection": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Slide Playlist": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Music Playlist": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Voice Ad": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Display Source": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Display Board": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Display Settings": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Queue": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Queue Ticket": {"on_update": "onedesk.one_display.live.changed", "on_trash": "onedesk.one_display.live.changed"},
	"Repost Item Valuation": {"on_change": "onedesk.one_project.money.restocked"},
	"Work Order": {"before_validate": "onedesk.one_factory.making.steps"},
	"BOM": {"onload": "onedesk.one_factory.costs.onload"},
	"Quality Action": {"before_validate": "onedesk.one_quality.company.fill"},
	# An agent's draft or question lands in its conversation in OneChat (one_chat/cards.py).
	"Reading Action": {"after_insert": "onedesk.one_chat.cards.posted"},
	"Non Conformance": {
		"before_validate": "onedesk.one_quality.company.fill",
		"validate": "onedesk.one_quality.resolve.guard",
		"after_insert": "onedesk.one_quality.tell.raised",
		"on_update": "onedesk.one_quality.tell.resolved",
	},
	"Stock Entry": {
		"before_validate": "onedesk.one_project.money.issued",
		"on_submit": ["onedesk.one_factory.tell.work_done", "onedesk.one_inventory.tell.moved"],
	},
	"Version": {"onload": "onedesk.one.audit.onload"},
	"Delivery Trip": {"onload": "onedesk.one_inventory.trips.onload"},
	"Offering": {"on_update": ["onedesk.one_admin.books.synced", "onedesk.one_admin.offerings.warn"]},
	"One Admin Settings": {"on_update": "onedesk.one_admin.offerings.warn"},
	"User": {
		"validate": "onedesk.one.people.seated",
		"before_save": "onedesk.one_mail.addresses.for_person",
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": ["onedesk.one_mail.faces.dress_later", "onedesk.one_hr.everybody.user", "onedesk.account_center.sync.from_user"],
	},
	"System Settings": {"on_update": "onedesk.one_calendar.feed.switched"},
	"Custom Field": {"validate": "onedesk.one.layer.custom_field"},
	"Property Setter": {"validate": "onedesk.one.layer.property_setter"},
	"Client Script": {"validate": "onedesk.one.layer.script"},
	"Server Script": {"validate": "onedesk.one.layer.script"},
	"Notification Type": {"validate": "onedesk.one.notify.validate", "on_update": "onedesk.one.notify.changed"},
	"Print Format": {"validate": "onedesk.one_studio.printing.validate_format"},
	"Report": {
		"validate": "onedesk.one_studio.reports.report_kept",
		"after_insert": "onedesk.one_studio.reports.placed",
		"on_trash": "onedesk.one_studio.reports.removed",
	},
	"Dashboard": {"on_trash": "onedesk.one_studio.reports.removed"},
	"Dashboard Chart": {"validate": "onedesk.one_studio.reports.chart_kept"},
	"Number Card": {"validate": "onedesk.one_studio.reports.chart_kept"},
	"Auto Email Report": {"validate": "onedesk.one_studio.reports.mail_kept"},
	"Letter Head": {"validate": "onedesk.one_studio.printing.validate_letter_head"},
	"Global Defaults": {"on_update": "onedesk.one.company.changed"},
	"Employee Advance": {"after_insert": "onedesk.one_hr.tell.advance_asked"},
	"Company": {
		"validate": "onedesk.one_book.closing.kept_to_today",
		"after_insert": ["onedesk.one_mail.faces.dress_later", "onedesk.one.company.changed"],
		"after_delete": "onedesk.one.company.changed",
		"on_update": [
			"onedesk.one_studio.letter_heads.redraw",
			"onedesk.one_mail.faces.dress_later",
			"onedesk.one_hr.papers.company_saved",
			"onedesk.one_hr.accounts.ready",
			"onedesk.one_studio.print_blocks.offered",
		],
	},
	"Address": {"on_update": "onedesk.one_studio.letter_heads.redraw"},
	"Print Format Snippet": {"validate": "onedesk.one_studio.printing.validate_snippet"},
	"Email Template": {
		"validate": "onedesk.one_mail.mail_templates.validate",
		"on_trash": "onedesk.one_mail.mail_templates.on_trash",
	},
	"Address Template": {"validate": "onedesk.one.lists.validate_address_template"},
	"Customer Group": {"before_insert": "onedesk.one.lists.place"},
	"Territory": {"before_insert": "onedesk.one.lists.place"},
	"Item Group": {"before_insert": "onedesk.one.lists.place"},
	"Supplier Group": {"before_insert": "onedesk.one.lists.place"},
	"Department": {"before_insert": "onedesk.one.lists.place"},
	"Workflow": {"validate": "onedesk.one_studio.approvals.validate"},
	"Workflow Action": {"after_insert": "onedesk.one_studio.approvals.waiting"},
	"Automation Flow": {"validate": "onedesk.one_studio.automations.validate"},
	"Webhook": {"validate": "onedesk.one.webhooks.validate"},
	"Assignment Rule": {"validate": "onedesk.one_crm.access.assignment_rule"},
	"Note": {
		"before_validate": "onedesk.one.announcements.before_validate",
		"validate": "onedesk.one.announcements.validate",
		"on_update": "onedesk.one.announcements.on_update",
		"on_trash": "onedesk.one.announcements.on_trash",
	},
	"Document Naming Rule": {"validate": "onedesk.one_studio.numbering.validate_rule"},
	"Notification Log": {
		"before_insert": "onedesk.one_task.tell.given",
		"after_insert": "onedesk.one.push.pushed",
	},
	"Notification Settings": {"before_insert": "onedesk.one.notify.new_person"},
	"Payroll Settings": {"on_update": "onedesk.one.notify.switched"},
	"Notification": {"on_update": "onedesk.one.notify.switched"},
	"Material Request": {
		"before_validate": "onedesk.one_inventory.requests.titled",
		"on_submit": "onedesk.one_inventory.tell.raised",
		"validate": "onedesk.one_project.chain.agree",
	},
	"Contact": {
		"validate": "onedesk.one_portal.gate.contact",
		"on_update": [
			"onedesk.one_portal.portal.invited",
			"onedesk.one_mail.faces.dress_later",
		],
		"after_insert": "onedesk.one_mail.faces.dress_later",
	},
	"Customer": {
		"after_insert": ["onedesk.one_mail.faces.dress_later", "onedesk.one_ai.reading.planning.carried"],
		"on_update": "onedesk.one_mail.faces.dress_later",
		"on_trash": "onedesk.one_crm.capture.forget",
	},
	"Supplier": {"after_insert": "onedesk.one_mail.faces.dress_later", "on_update": "onedesk.one_mail.faces.dress_later"},
	"Bank": {"after_insert": "onedesk.one_mail.faces.dress_later", "on_update": "onedesk.one_mail.faces.dress_later"},
	"Manufacturer": {
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": "onedesk.one_mail.faces.dress_later",
	},
	"Bank Account": {"on_update": "onedesk.one_book.ready.wired"},
	"Sales Invoice": {
		"on_recurring": "onedesk.one_book.repeat.repeated",
		"before_print": "onedesk.one_book.paper.titled",
		"on_submit": "onedesk.one_project.claims.numbered",
		"before_insert": ["onedesk.one_project.chain.customers_one", "onedesk.one_project.terms.carried"],
		"after_insert": "onedesk.one_project.progress.drafted",
		"validate": [
			"onedesk.one_book.vat.emirate",
			"onedesk.one_project.chain.agree",
			"onedesk.one_project.progress.retained",
			"onedesk.one_project.retainer.billed_by_month",
			"onedesk.one_book.paper.lines",
			"onedesk.one_book.paper.pay_into",
		],
	},
	"Payment Entry": {
		"on_submit": [
			"onedesk.one_ai.reading.steps.paid",
			"onedesk.one_book.tell.paid_online",
			"onedesk.one_hr.tell.claims_paid",
		],
		"on_cancel": "onedesk.one_ai.reading.steps.paid",
		"validate": ["onedesk.one_project.chain.paid_for", "onedesk.one_book.paid.titled"],
	},
	"Journal Entry": {
		"on_submit": "onedesk.one_ai.reading.steps.paid",
		"on_cancel": "onedesk.one_ai.reading.steps.paid",
		"validate": "onedesk.one_book.journal.titled",
	},
	"Purchase Invoice": {
		"on_recurring": "onedesk.one_book.repeat.repeated",
		"before_insert": "onedesk.one_project.terms.carried",
		"after_insert": "onedesk.one_project.progress.drafted",
		"validate": [
			"onedesk.one_book.vat.reclaimed",
			"onedesk.one_inventory.assets.located",
			"onedesk.one_project.chain.agree",
			"onedesk.one_project.progress.retained",
		],
		"on_submit": "onedesk.one_inventory.assets.registered",
	},
	"Item": {
		"validate": "onedesk.one_inventory.assets.fixed_item",
		"before_insert": "onedesk.one_inventory.barcodes.coded",
		"before_validate": "onedesk.one_inventory.measure.follows_unit",
	},
	"Stock Settings": {
		"validate": "onedesk.one_inventory.measure.size_unit_is_a_length",
	},
	"Brand": {
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": "onedesk.one_mail.faces.dress_later",
	},
	"News Source": {
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": "onedesk.one_mail.faces.dress_later",
	},
	"Asset Movement": {"on_submit": "onedesk.one_inventory.tell.handed_over"},
	"Asset Maintenance": {"before_validate": "onedesk.one_inventory.maintenance.due"},
	"Asset Maintenance Log": {
		"before_validate": ["onedesk.one_inventory.maintenance.on_time", "onedesk.one_inventory.maintenance.named"]
	},
	"Purchase Receipt": {
		"validate": ["onedesk.one_inventory.assets.located", "onedesk.one_project.chain.agree"],
		"on_submit": "onedesk.one_inventory.assets.registered",
	},
	"Event": {
		"validate": "onedesk.one_calendar.events.validate",
		"on_update": "onedesk.one_calendar.tell.saved",
		"on_trash": "onedesk.one_calendar.tell.removed",
	},
	"Appointment": {
		"validate": "onedesk.one_calendar.events.booking",
		"on_update": "onedesk.one_calendar.events.booked",
	},
	"*": {
		"before_validate": "onedesk.one_inventory.measure.sized",
		"before_insert": "onedesk.one_ai.reading.fill.before_insert",
		"before_save": "onedesk.one_ai.reading.fill.before_save",
		"on_submit": [
			"onedesk.one.quiet.milestone",
			"onedesk.one_ai.reading.mark.looked_at",
			"onedesk.one_ai.reading.steps.record_changed",
			"onedesk.one.linked.save",
			"onedesk.one_project.money.moved",
			"onedesk.one_studio.approvals.answered",
			"onedesk.one_ai.brief.touched",
			"onedesk.one_sheet.table.changed",
		],
		"after_insert": [
			"onedesk.one.quiet.milestone",
			"onedesk.one_ai.reading.identity.flag",
			"onedesk.one_ai.reading.planning.backlink",
		],
		"onload": ["onedesk.one_ai.touch.onload", "onedesk.one_ai.reading.mark.onload", "onedesk.one.head.onload"],
		"on_update": [
			"onedesk.one_ai.reading.identity.remember",
			"onedesk.one_ai.reading.mark.looked_at",
			"onedesk.one_ai.reading.steps.record_changed",
			"onedesk.one.linked.save",
			"onedesk.one_studio.approvals.answered",
			"onedesk.one_ai.index.changed",
			"onedesk.one_ai.brief.touched",
			"onedesk.one_sheet.table.changed",
			"onedesk.one_display.live.record_saved",
		],
		"on_update_after_submit": ["onedesk.one.linked.save", "onedesk.one_studio.approvals.answered", "onedesk.one_ai.index.changed", "onedesk.one_display.live.record_saved"],
		"on_cancel": [
			"onedesk.one_studio.approvals.answered",
			"onedesk.one_ai.reading.mark.looked_at",
			"onedesk.one_ai.reading.steps.record_changed",
			"onedesk.one_project.money.moved",
			"onedesk.one_ai.brief.touched",
			"onedesk.one_sheet.table.changed",
		],
		"before_rename": "onedesk.one_ai.reading.mark.before_rename",
		"after_rename": ["onedesk.one_ai.reading.identity.renamed", "onedesk.one_ai.reading.mark.after_rename"],
		"on_trash": [
			"onedesk.one.recycle.titled",
			"onedesk.one_ai.reading.lessons.deleted",
			"onedesk.one_ai.touch.forget",
			"onedesk.one_ai.reading.identity.forget",
			"onedesk.one_ai.reading.filing.forget",
			"onedesk.one_ai.index.removed",
			"onedesk.one_display.live.record_saved",
			"onedesk.one_portal.share.forget",
		],
	},
	"Budget": {
		"validate": "onedesk.one_project.budget.kept_to_projects",
		"on_submit": "onedesk.one_project.budget.synced",
		"on_cancel": "onedesk.one_project.budget.synced",
	},
	"Period Closing Voucher": {"on_submit": "onedesk.one_book.closing.year_closed"},
	"Employee": {
		"validate": ["onedesk.one_hr.leaving.notice_ends_on", "onedesk.one_hr.everybody.employee"],
		"after_insert": "onedesk.one_mail.faces.dress_later",
		"on_update": ["onedesk.one_hr.leaving.on_employee_update", "onedesk.one_mail.faces.dress_later", "onedesk.account_center.sync.from_employee"],
	},
	"Overtime Slip": {
		"before_validate": "onedesk.one_hr.overtime.before_validate",
		"validate": "onedesk.one_hr.overtime.no_double_pay",
	},
	"Timesheet": {
		"before_insert": "onedesk.one_project.hours.billable",
		"validate": "onedesk.one_project.hours.on_its_project",
		"before_validate": "onedesk.one_hr.timesheet.before_validate",
		"on_submit": ["onedesk.one_project.tell.hours_used", "onedesk.one_project.tell.time_over"],
	},
	"Salary Component": {"before_validate": "onedesk.one_hr.accounts.component"},
	"Leave Application": {
		"before_validate": "onedesk.one_hr.decision.kept",
		"before_submit": "onedesk.one_hr.leave.before_submit",
		"on_submit": "onedesk.one_mail.rules.covered",
		"on_update_after_submit": "onedesk.one_mail.rules.covered",
		"on_cancel": "onedesk.one_mail.rules.covered",
	},
	"Expense Claim": {
		"before_validate": "onedesk.one_hr.expense.before_validate",
		"before_submit": "onedesk.one_hr.expense.before_submit",
	},
	"Employee Benefit Application": {"before_validate": "onedesk.one_hr.benefit.application"},
	"Employee Benefit Claim": {"before_validate": "onedesk.one_hr.benefit.claim"},
	"Appointment Letter": {"before_validate": "onedesk.one_hr.letter.before_validate"},
	"Appraisal": {
		"before_validate": "onedesk.one_hr.growth.appraisal_period",
		"after_insert": ["onedesk.one_hr.growth.cycle_under_way", "onedesk.one_hr.tell.appraisal_started"],
	},
	"Job Requisition": {"after_insert": "onedesk.one_hr.tell.requisition", "on_update": "onedesk.one_hr.tell.requisition"},
	"Employee Referral": {"after_insert": "onedesk.one_hr.tell.referral"},
	"Employee Promotion": {"before_validate": "onedesk.one_hr.growth.promotion"},
	"Job Applicant": {"after_insert": ["onedesk.one_hr.hiring.arrived", "onedesk.one_ai.reading.planning.applicant_arrived"], "on_update": "onedesk.one_hr.tell.referral_answered"},
	"Interview": {
		"after_insert": "onedesk.one_hr.hiring.scheduled",
		"on_update": "onedesk.one_hr.hiring.interviewers",
		"onload": "onedesk.one_hr.hiring.interview_onload",
	},
	"Email Account": {
		"validate": ["onedesk.one_ai.reading.switches.mailbox_switched", "onedesk.one_mail.holders.signed"]
	},
	"Employee Grievance": {
		"after_insert": "onedesk.one_hr.ai_grievance.raised",
		"validate": "onedesk.one_hr.ai_grievance.unmarked",
		"on_update": "onedesk.one_hr.tell.grievance_answered",
	},
	"File": {
		"before_insert": ["onedesk.one_sheet.api.copied", "onedesk.one_doc.api.copied", "onedesk.one_deck.api.copied"],
		"validate": ["onedesk.one_ai.reading.switches.file_switched", "onedesk.one_project.media.kept_shown"],
		"after_insert": [
			"onedesk.one_sheet.api.placed",
			"onedesk.one_doc.api.placed",
			"onedesk.one_deck.api.placed",
			"onedesk.one_ai.reading.pipeline.file_added",
			"onedesk.one_project.media.changed",
		],
		"on_update": [
			"onedesk.one_cloud.live.changed",
			"onedesk.one_ai.reading.lessons.moved",
			"onedesk.one_project.media.changed",
		],
		"on_trash": [
			"onedesk.one_hr.hiring.keep_sound",
			"onedesk.one_cloud.links.forget_file",
			"onedesk.one_cloud.history.forget",
			"onedesk.one_cloud.live.changed",
			"onedesk.one_project.media.changed",
			"onedesk.one_sheet.api.file_gone",
			"onedesk.one_doc.api.file_gone",
			"onedesk.one_deck.api.file_gone",
		]
	},
	"Employee Onboarding": {
		"before_validate": "onedesk.one_hr.lifecycle.onboarding",
		"on_submit": "onedesk.one_hr.lifecycle.typed",
	},
	"Employee Separation": {
		"before_submit": "onedesk.one_inventory.custody.leaving",
		"on_submit": "onedesk.one_hr.lifecycle.typed",
	},
	"Comment": {"after_insert": "onedesk.one_task.tell.commented"},
	"Task": {
		"before_insert": [
			"onedesk.one_hr.lifecycle.task",
			"onedesk.one_project.templates.task_made",
		],
		"after_insert": "onedesk.one_task.capture.task_made",
		"before_validate": [
			"onedesk.one_task.task.before_validate",
			"onedesk.one_project.templates.days_kept",
			"onedesk.one_project.templates.held_in_phase",
		],
		"validate": "onedesk.one_project.milestones.kept",
		"on_recurring": "onedesk.one_task.task.recurring",
		"on_update": [
			"onedesk.one_project.plan.reschedule",
			"onedesk.one_task.tell.done",
			"onedesk.one_task.tell.changed",
			"onedesk.one_project.milestones.reached",
			"onedesk.one_project.overview.task_changed",
			"onedesk.one_project.tell.over_plan",
			"onedesk.one_project.templates.task_measured",
		],
		"after_delete": "onedesk.one_project.overview.task_changed",
	},
	"Project Template": {"validate": "onedesk.one_project.templates.measured"},
	"Request for Quotation": {"validate": "onedesk.one_project.chain.agree"},
	"Supplier Quotation": {"validate": "onedesk.one_project.chain.agree"},
	"Purchase Order": {
		"validate": [
			"onedesk.one_project.chain.agree",
			"onedesk.one_inventory.order.within_requests",
			"onedesk.one_project.retention.taxed",
		],
		"before_update_after_submit": "onedesk.one_project.retention.taxed",
		"on_update_after_submit": "onedesk.one_project.progress.release",
	},
	"Delivery Note": {
		"before_insert": "onedesk.one_project.chain.customers_one",
		"validate": "onedesk.one_project.chain.agree",
	},
	"DocShare": {"after_insert": "onedesk.one_project.members.shared"},
	"Dunning": {"validate": "onedesk.one_book.paper.pay_into"},
	"Projects Settings": {"on_update": "onedesk.one_project.retention.ready"},
	"Project": {
		"before_validate": [
			"onedesk.one_project.members.nobody",
			"onedesk.one_project.members.invite",
			"onedesk.one_project.members.unlist",
			"onedesk.one_project.kinds.fill",
			"onedesk.one_project.hours.fill",
			"onedesk.one_project.terms.started",
			"onedesk.one_project.status.held",
		],
		"validate": [
			"onedesk.one_project.naming.validate",
			"onedesk.one_project.tree.validate",
			"onedesk.one_project.kinds.held",
			"onedesk.one_project.kinds.settled",
			"onedesk.one_project.budget.summed",
			"onedesk.one_project.contacts.held",
			"onedesk.one_project.members.enabled",
		],
		"on_update": [
			"onedesk.one_project.naming.on_update",
			"onedesk.one_project.contacts.link_all",
			"onedesk.one_project.members.forget",
			"onedesk.one_project.tree.forget",
			"onedesk.one_project.tell.changed",
			"onedesk.one_project.retention.handed_over",
			"onedesk.one_project.overview.project_changed",
			"onedesk.one_project.templates.used",
		],
		"on_trash": [
			"onedesk.one_project.members.forget",
			"onedesk.one_project.tree.forget",
			"onedesk.one_project.templates.used",
		],
	},
	"Kanban Board": {"before_insert": "onedesk.one_project.board.shape"},
	"Training Result": {"before_validate": "onedesk.one_hr.lifecycle.result"},
	"Salary Slip": {"validate": "onedesk.one_hr.lates.counted"},
	"Attendance": {
		"on_submit": ["onedesk.one_project.site_time.attended", "onedesk.one_hr.tell.marked_absent"],
		"on_cancel": "onedesk.one_project.site_time.cancelled",
	},
	"Attendance Request": {
		"before_validate": "onedesk.one_hr.request.before_validate",
		"before_submit": "onedesk.one_hr.request.before_submit",
		"after_insert": "onedesk.one_hr.tell.attendance_asked",
	},
	"Opportunity": {
		"before_validate": "onedesk.one_crm.stages.before_validate",
		"validate": "onedesk.one_crm.deal.validate",
		"on_update": "onedesk.one_crm.tell.given",
	},
	"Lead": {
		"before_insert": "onedesk.one_crm.capture.before_insert",
		"on_trash": "onedesk.one_crm.capture.forget",
		"on_update": [
			"onedesk.one_mail.faces.dress_later",
			"onedesk.one_crm.tell.given",
		],
		"after_insert": ["onedesk.one_mail.faces.dress_later", "onedesk.one_crm.tell.arrived"],
	},
	"ToDo": {
		"before_insert": "onedesk.one_task.capture.todo_made",
		"after_insert": [
			"onedesk.one_crm.capture.assigned",
			"onedesk.one_project.members.assigned",
		],
		"on_update": "onedesk.one_task.capture.todo_changed",
	},
	"Communication": {
		"before_insert": ["onedesk.one_mail.holders.sending", "onedesk.one_mail.outbound.file_sent"],
		"on_update": ["onedesk.one_mail.outbound.thread_sent", "onedesk.one_ai.reading.steps.replied"],
		"after_insert": [
			"onedesk.one_mail.threads.adopt",
			"onedesk.one_mail.live.inserted",
			"onedesk.one_mail.team.arrived",
			"onedesk.one_crm.capture.replied",
			"onedesk.one_crm.tell.they_replied",
			"onedesk.one_project.updates.answered",
			"onedesk.one_mail.signatures.inline_logo",
		],
	},
	"Call Log": {"after_insert": "onedesk.one_crm.capture.replied"},
	"Sales Stage": {
		"on_update": "onedesk.one_crm.board.sync",
		"after_rename": "onedesk.one_crm.board.sync",
		"after_delete": "onedesk.one_crm.board.sync",
	},
	"Quotation": {
		"before_insert": ["onedesk.one_project.chain.customers_one", "onedesk.one_project.terms.carried"],
		"on_submit": "onedesk.one_crm.stages.follow",
		"on_cancel": "onedesk.one_crm.stages.follow",
		"on_update_after_submit": "onedesk.one_crm.stages.follow",
	},
	"Sales Order": {
		"before_insert": [
			"onedesk.one_project.chain.customers_one",
			"onedesk.one_project.terms.carried",
			"onedesk.one_project.retention.ordered",
		],
		"validate": [
			"onedesk.one_project.chain.agree",
			"onedesk.one_book.paper.pay_into",
			"onedesk.one_project.retention.taxed",
		],
		"on_submit": [
			"onedesk.one_crm.stages.follow",
			"onedesk.one_project.billing.ordered",
		],
		"on_cancel": "onedesk.one_crm.stages.follow",
		"before_update_after_submit": "onedesk.one_project.retention.taxed",
		"on_update_after_submit": "onedesk.one_project.progress.release",
	},
	"Shift Request": {
		"before_validate": "onedesk.one_hr.shift.before_validate",
		"before_submit": "onedesk.one_hr.shift.before_submit",
	},
}

clear_cache = ["onedesk.one.outside.forget"]

standard_queries = {
	"DocType": "onedesk.one.outside.doctype_query",
	"Report": "onedesk.one.outside.report_query",
}

override_whitelisted_methods = {
	"onedesk.one_storage.store.fetch": "onedesk.one_cloud.store.fetch",
	"onedesk.one_storage.dav.serve": "onedesk.one_cloud.dav.serve",
	"onedesk.one_slide.api.download": "onedesk.one_deck.api.download",
	"onedesk.one_slide.api.media": "onedesk.one_deck.api.media",
	"onedesk.one_slide.api.shown": "onedesk.one_deck.api.shown",
	"onedesk.one_slide.fonts.face": "onedesk.one_deck.fonts.face",
	"onedesk.one_account.invite.accept": "onedesk.account_center.invite.accept",
	"frappe.utils.global_search.search": "onedesk.one.outside.search",
	"frappe.desk.page.setup_wizard.setup_wizard.setup_complete": "onedesk.one.setup_wizard.setup_complete",
	"erpnext.stock.doctype.material_request.material_request.update_status": "onedesk.one_inventory.tell.update_status",
	"erpnext.projects.doctype.project.project.get_project_tasks": "onedesk.one_project.milestones.project_tasks",
	"frappe.desk.form.load.getdoc": "onedesk.one_mail.linking.getdoc",
	"frappe.desk.form.load.get_docinfo": "onedesk.one_mail.linking.get_docinfo",
	"frappe.desk.form.load.get_communications": "onedesk.one_mail.linking.get_communications",
	"erpnext.selling.doctype.customer.customer.send_emails": "onedesk.one_book.tell.credit_limit",
	"frappe.core.doctype.user.user.update_password": "onedesk.account_center.signin.update_password",
	"frappe.www.login.send_login_link": "onedesk.one_admin.accounts.send_login_link",
	"frappe.utils.print_format_generator.render_builder_preview": "onedesk.one_studio.printing.render_builder_preview",
	"frappe.utils.print_format_generator.download_builder_preview_pdf": "onedesk.one_studio.printing.download_builder_preview_pdf",
	"frappe.utils.print_format_generator.render_jinja_template": "onedesk.one_studio.printing.render_jinja_template",
	"frappe.email.doctype.email_template.email_template.get_email_template": "onedesk.one_mail.mail_templates.get_email_template",
	"frappe.desk.search.search_link": "onedesk.one.apps.search_link",
}

ignore_links_on_delete = ["Reading Action", "Reading Lesson", "Reading", "Reading Party", "Portal Link"]

has_permission = {
	"Mail Draft": "onedesk.one_mail.drafts.has_permission",
	"Mail Conversation": "onedesk.one_mail.team.has_permission",
	"Dashboard": "onedesk.one_hr.access.dashboard_allowed",
	"Interview": "onedesk.one_hr.access.interview_allowed",
	"Clock Device": "onedesk.one_hr.passkey.has_permission",
	"Deleted Document": "onedesk.one.recycle.has_permission",
	"Version": "onedesk.one.audit.has_permission",
	"Activity Log": "onedesk.one.audit.has_permission",
	"Access Log": "onedesk.one.audit.has_permission",
	"Webhook": "onedesk.one.webhooks.has_permission",
	"Assignment Rule": "onedesk.one_crm.access.has_permission",
	"Webhook Request Log": "onedesk.one.webhooks.has_permission",
	"Personal Data Deletion Request": "onedesk.one.privacy.has_permission",
	"Personal Data Download Request": "onedesk.one.privacy.has_permission",
	"Reading Action": "onedesk.one_ai.reading.act.has_permission",
	"Chat Channel": "onedesk.one_chat.channels.has_permission",
	"Chat Message": "onedesk.one_chat.channels.message_permission",
	"Communication": "onedesk.one_mail.access.allowed",
	"Mail Rule": "onedesk.one_mail.rules.rule_allowed",
	"Employee Grievance": "onedesk.one_hr.ai_grievance.allowed",
	"Salary Slip": "onedesk.one_hr.everybody.pay_allowed",
	"Salary Structure Assignment": "onedesk.one_hr.everybody.pay_allowed",
	"Additional Salary": "onedesk.one_hr.everybody.pay_allowed",
	"Employee Incentive": "onedesk.one_hr.everybody.pay_allowed",
	"Retention Bonus": "onedesk.one_hr.everybody.pay_allowed",
	"Overtime Slip": "onedesk.one_hr.everybody.pay_allowed",
	"Arrear": "onedesk.one_hr.everybody.pay_allowed",
	"Payroll Correction": "onedesk.one_hr.everybody.pay_allowed",
	"Gratuity": "onedesk.one_hr.everybody.pay_allowed",
	"Full and Final Statement": "onedesk.one_hr.everybody.pay_allowed",
	"Employee": "onedesk.one_hr.everybody.employee_allowed",
	"Leave Application": "onedesk.one_hr.everybody.personal_allowed",
	"Leave Allocation": "onedesk.one_hr.everybody.personal_allowed",
	"Leave Encashment": "onedesk.one_hr.everybody.personal_allowed",
	"Attendance": "onedesk.one_hr.everybody.personal_allowed",
	"Attendance Request": "onedesk.one_hr.everybody.personal_allowed",
	"Shift Request": "onedesk.one_hr.everybody.personal_allowed",
	"Employee Checkin": "onedesk.one_hr.everybody.personal_allowed",
	"Expense Claim": "onedesk.one_hr.everybody.personal_allowed",
	"Employee Advance": "onedesk.one_hr.everybody.personal_allowed",
	"Travel Request": "onedesk.one_hr.everybody.personal_allowed",
	"Task": "onedesk.one_task.access.allowed",
	"Project": "onedesk.one_project.members.allowed",
	"Credit Ledger Entry": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Credit Reservation": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Account Request": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Offering": "onedesk.one_admin.site.refuse_on_a_tenant",
	"One Admin Settings": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Workspace Server": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Workspace Session": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Workspace Error": "onedesk.one_admin.site.refuse_on_a_tenant",
	"OneOS Session": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Provisioning Job": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Stripe Webhook Event": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Private App": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant Domain": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Tenant Event": "onedesk.one_admin.site.refuse_on_a_tenant",
	"Health Check": "onedesk.one_admin.site.refuse_on_a_tenant",
}

permission_query_conditions = {
	"Dashboard": "onedesk.one_hr.access.dashboard_query",
	"Interview": "onedesk.one_hr.access.interview_query",
	"Clock Device": "onedesk.one_hr.passkey.query",
	"Deleted Document": "onedesk.one.recycle.query",
	"Version": "onedesk.one.audit.version_query",
	"Webhook": "onedesk.one.webhooks.query",
	"Assignment Rule": "onedesk.one_crm.access.query",
	"Webhook Request Log": "onedesk.one.webhooks.log_query",
	"Personal Data Deletion Request": "onedesk.one.privacy.query",
	"Personal Data Download Request": "onedesk.one.privacy.query",
	"Reading Action": "onedesk.one_ai.reading.act.query",
	"Chat Channel": "onedesk.one_chat.channels.query",
	"Chat Message": "onedesk.one_chat.channels.message_query",
	"Mail Rule": "onedesk.one_mail.rules.rule_query",
	"Employee Grievance": "onedesk.one_hr.ai_grievance.query",
	"Salary Slip": "onedesk.one_hr.everybody.pay_query",
	"Salary Structure Assignment": "onedesk.one_hr.everybody.pay_query",
	"Additional Salary": "onedesk.one_hr.everybody.pay_query",
	"Employee Incentive": "onedesk.one_hr.everybody.pay_query",
	"Retention Bonus": "onedesk.one_hr.everybody.pay_query",
	"Overtime Slip": "onedesk.one_hr.everybody.pay_query",
	"Arrear": "onedesk.one_hr.everybody.pay_query",
	"Payroll Correction": "onedesk.one_hr.everybody.pay_query",
	"Gratuity": "onedesk.one_hr.everybody.pay_query",
	"Full and Final Statement": "onedesk.one_hr.everybody.pay_query",
	"Employee": "onedesk.one_hr.everybody.employee_query",
	"Leave Application": "onedesk.one_hr.everybody.personal_query",
	"Leave Allocation": "onedesk.one_hr.everybody.personal_query",
	"Leave Encashment": "onedesk.one_hr.everybody.personal_query",
	"Attendance": "onedesk.one_hr.everybody.personal_query",
	"Attendance Request": "onedesk.one_hr.everybody.personal_query",
	"Shift Request": "onedesk.one_hr.everybody.personal_query",
	"Employee Checkin": "onedesk.one_hr.everybody.personal_query",
	"Expense Claim": "onedesk.one_hr.everybody.personal_query",
	"Employee Advance": "onedesk.one_hr.everybody.personal_query",
	"Travel Request": "onedesk.one_hr.everybody.personal_query",
	"Task": "onedesk.one_task.access.query",
	"Project": "onedesk.one_project.members.query",
	"Credit Ledger Entry": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Credit Reservation": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Account Request": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Offering": "onedesk.one_admin.site.nothing_on_a_tenant",
	"One Admin Settings": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Workspace Server": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Workspace Session": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Workspace Error": "onedesk.one_admin.site.nothing_on_a_tenant",
	"OneOS Session": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Provisioning Job": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Stripe Webhook Event": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Private App": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant Domain": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Tenant Event": "onedesk.one_admin.site.nothing_on_a_tenant",
	"Health Check": "onedesk.one_admin.site.nothing_on_a_tenant",
}

awesomebar_search = ["onedesk.one.outside.awesomebar", "onedesk.one_ai.reading.search.awesomebar"]

fixtures = [
	"Custom Icon",
	"Clock Reason",
	"Attendance Reason",
	"Identification Document Type",
	{"dt": "Milestone Tracker", "filters": [["name", "=", "Opportunity-sales_stage"]]},
	{"dt": "Opportunity Lost Reason", "filters": [["name", "in", ["Price", "Went With a Competitor", "No Budget", "No Decision", "Timing", "Not a Fit", "Other", "Declined by the Customer"]]]},
	{"dt": "Quotation Lost Reason", "filters": [["name", "in", ["Price", "Went With a Competitor", "No Budget", "No Decision", "Timing", "Not a Fit", "Other", "Declined by the Customer"]]]},
	{"dt": "UTM Source", "filters": [["name", "=", "Website"]]},
	{"dt": "Custom HTML Block", "filters": [["name", "in", ["OneAdmin Needs You"]]]},
]


doctype_js = {
	"Mail Conversation": "public/js/one_mail/mail_conversation.js",
	"Asset Maintenance Log": "public/js/one_inventory/asset_maintenance_log.js",
	"Request for Quotation": "public/js/one_inventory/request_for_quotation.js",
	"Shift Location": "public/js/one_hr/shift_location.js",
	"Appointment": "public/js/one_crm/appointment.js",
	"Bank Reconciliation Tool": "public/js/one_book/bank.js",
	"Bank Statement Import": "public/js/one_book/bank.js",
	"Delivery Trip": "public/js/one_inventory/delivery_trip.js",
	"Webhook": "public/js/one_studio/webhook.js",
	"Note": "public/js/one/note.js",
	"Deleted Document": "public/js/one/deleted_document.js",
	"Personal Data Deletion Request": "public/js/trust_center/privacy_request.js",
	"Contact": "public/js/one_portal/contact.js",
	"Personal Data Download Request": "public/js/trust_center/privacy_copy.js",
	"Workspace Account": "public/js/account_center/workspace_account.js",
	"Tenant": "public/js/one_admin/tenant.js",
	"Workspace Server": "public/js/one_admin/workspace_server.js",
	"Account Request": "public/js/one_admin/account_request.js",
	"Credit Ledger Entry": "public/js/one_admin/credit_ledger_entry.js",
	"Offering": "public/js/one_admin/offering.js",
	"One Admin Settings": "public/js/one_admin/admin_settings.js",
	"Item": ["public/js/one_inventory/item_form.js", "public/js/one_inventory/item.js"],
	"Employee": "public/js/one_hr/employee.js",
	"Employee Attendance Tool": "public/js/one_hr/attendance_tool.js",
	"Attendance": "public/js/one_hr/attendance.js",
	"Clock Network": "public/js/one_hr/learned.js",
	"Clock Place": "public/js/one_hr/learned.js",
	"Attendance Request": "public/js/one_hr/attendance_request.js",
	"Shift Request": "public/js/one_hr/shift_request.js",
	"Overtime Slip": "public/js/one_hr/overtime_slip.js",
	"Timesheet": "public/js/one_hr/timesheet.js",
	"Leave Control Panel": "public/js/one_hr/leave_control_panel.js",
	"Interview": "public/js/one_hr/hiring.js",
	"Opportunity": "public/js/one_crm/opportunity.js",
	"Lead": "public/js/one_crm/lead.js",
	"Project": ["public/js/one_project/project_actions.js", "public/js/one_project/project.js"],
	"Activity Type": "public/js/one_project/activity_type.js",
	"Project Template": "public/js/one_project/project_template.js",
	"Purchase Order": "public/js/one_project/progress.js",
	"Quotation": "public/js/one_project/quotation.js",
	"Sales Order": ["public/js/one_project/progress.js", "public/js/one_project/customer_project.js"],
	"Delivery Note": "public/js/one_project/customer_project.js",
	"Sales Invoice": "public/js/one_project/customer_project.js",
	"Task": "public/js/one_task/task.js",
	"Stock Reconciliation": "public/js/one_inventory/stock_count.js",
}

doctype_tree_js = {
	"Account": "public/js/one_book/account_tree.js",
	"Project": "public/js/one_project/project_tree.js",
	"Task": "public/js/one_task/task_tree.js",
	"Warehouse": "public/js/one_inventory/warehouse_tree.js",
}
doctype_calendar_js = {"Project": "public/js/one_project/project_calendar.js", "Task": "public/js/one_task/task_calendar.js"}
doctype_kanban_js = {"Project": "public/js/one_project/project_kanban.js", "Task": "public/js/one_task/task_kanban.js"}

doctype_list_js = {
	"Sales Stage": "public/js/one_crm/sales_stage_list.js",
	"Address Template": "public/js/one/address_template_list.js",
	"Contact": "public/js/one_portal/contact_list.js",
	"Deleted Document": "public/js/one/deleted_document_list.js",
	"Event": "public/js/one_calendar/event_list.js",
	"Note": "public/js/one/note_list.js",
	"Project Template": "public/js/one_project/project_template_list.js",
	"Timesheet": "public/js/one_hr/timesheet_list.js",
	"Version": "public/js/one/audit_list.js",
	"Activity Log": "public/js/one/audit_list.js",
	"Access Log": "public/js/one/audit_list.js",
	"Personal Data Deletion Request": "public/js/trust_center/privacy_request_list.js",
	"Personal Data Download Request": "public/js/trust_center/privacy_copy_list.js",
	"Credit Ledger Entry": "public/js/one_admin/credit_ledger_entry_list.js",
	"AI Proposal": "public/js/one_ai/ai_proposal_list.js",
	"Attendance": "public/js/one_hr/attendance_list.js",
	"Employee Checkin": "public/js/one_hr/checkin_list.js",
	"Opportunity": "public/js/one_crm/opportunity_list.js",
	"Lead": "public/js/one_crm/lead_list.js",
	"Prospect": "public/js/one_crm/prospect_list.js",
	"Task": "public/js/one_task/task_list.js",
	"Project": "public/js/one_project/project_list.js",
	"Item": "public/js/one_inventory/item_list.js",
	"Contract": "public/js/one_crm/contract_list.js",
	"Purchase Receipt": "public/js/one_inventory/purchase_receipt_list.js",
	"Delivery Note": "public/js/one_inventory/delivery_note_list.js",
	"Stock Entry": "public/js/one_inventory/stock_entry_list.js",
	"Material Request": "public/js/one_inventory/material_request_list.js",
	"Purchase Order": "public/js/one_inventory/purchase_order_list.js",
	"Sales Order": "public/js/one_crm/sales_order_list.js",
	"Issue": "public/js/one_crm/issue_list.js",
	"Maintenance Visit": "public/js/one_crm/maintenance_visit_list.js",
	"Supplier": "public/js/one_inventory/supplier_list.js",
	"Work Order": "public/js/one_factory/work_order_list.js",
	"Batch": "public/js/one_inventory/batch_list.js",
	"Request for Quotation": "public/js/one_inventory/request_for_quotation_list.js",
	"BOM": ["public/js/one_factory/bom_list.js", "public/js/one_factory/bom.js"],
	"Asset": "public/js/one_inventory/asset_list.js",
}

override_doctype_dashboards = {
	"Employee": ["onedesk.one_hr.employee.dashboard"],
	"Attendance": ["onedesk.one_hr.attendance.dashboard"],
	"Task": ["onedesk.one_task.task.dashboard"],
	"Project": ["onedesk.one_project.tree.dashboard"],
	"Activity Type": ["onedesk.one_project.rates.dashboard"],
	"Non Conformance": ["onedesk.one_quality.connections.dashboard"],
}

override_doctype_class = {
	"Activity Log": "onedesk.one.audit_logs.ActivityLog",
	"Access Log": "onedesk.one.audit_logs.AccessLog",
	"Reminder": "onedesk.one.tell.Reminder",
	"Employee Checkin": "onedesk.one_hr.checkin.OneEmployeeCheckin",
	"Timesheet": "onedesk.one_hr.timesheet.OneTimesheet",
	"File": "onedesk.one_cloud.file.CloudFile",
	"Notification": "onedesk.one.rules.Rule",
	"Leave Application": "onedesk.one_hr.tell.LeaveApplication",
	"Expense Claim": "onedesk.one_hr.tell.ExpenseClaim",
	"Shift Request": "onedesk.one_hr.tell.ShiftRequest",
	"Interview": "onedesk.one_hr.tell.Interview",
	"Notification Log": "onedesk.one.notify.NotificationLog",
	"Project": "onedesk.one_project.materials.OneProject",
}

write_file = "onedesk.one_cloud.store.write"
delete_file_data_content = "onedesk.one_cloud.store.delete"

add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"logo": app_logo_url,
		"route": "/desk/one",
		"has_permission": "onedesk.check_app_permission",
		"sequence_id": 0.5,
	}
]

get_website_user_home_page = "onedesk.one_admin.accounts.home_page"

web_include_js = stamped(["/assets/onedesk/js/one_hr/login.js"])

setup_wizard_requires = "/assets/onedesk/js/setup_wizard.js"
setup_wizard_stages = "onedesk.one.setup_wizard.get_setup_stages"
# The first person on the admin site becomes its operator (one_admin/site.py).
setup_wizard_success = "onedesk.one_admin.site.first_operators"

app_include_css = stamped([
	"/assets/onedesk/css/theme.css",
	"/assets/onedesk/css/one_interface/tokens.css",
	"/assets/onedesk/css/one_interface/palettes.css",
	"/assets/onedesk/css/desk.css",
	"/assets/onedesk/css/one_interface/centre.css",
	"/assets/onedesk/css/account_center/account_center.css",
	"/assets/onedesk/css/center_section.css",
	"/assets/onedesk/css/shell.css",
	"/assets/onedesk/css/one_interface/chrome.css",
	"/assets/onedesk/css/one_interface/frame.css",
	"/assets/onedesk/css/one_interface/json_view.css",
	"/assets/onedesk/css/one_portal/button.css",
	"/assets/onedesk/css/one_interface/views.css",
	"/assets/onedesk/css/one_interface/scrollbar.css",
	"/assets/onedesk/css/one_interface/canvas.css",
	"/assets/onedesk/css/one_interface/dialogs.css",
	"/assets/onedesk/css/one_interface/phone.css",
	"/assets/onedesk/css/one_interface/launcher.css",
	"/assets/onedesk/css/one_ai/oneai.css",
	"/assets/onedesk/css/trust_center/legal.css",
	"/assets/onedesk/css/one_ai/intake.css",
	"/assets/onedesk/css/one/news_add.css",
	"/assets/onedesk/css/one/shortcut_center.css",
	"/assets/onedesk/css/lost.css",
])

web_include_css = stamped(["/assets/onedesk/css/one_portal/portal.css", "/assets/onedesk/css/lost.css"])
update_website_context = ["onedesk.one_portal.portal.light_or_dark"]

page_js = {"print": "public/js/one_doc/print_documents.js"}

app_include_js = stamped([
	"/assets/onedesk/js/theme.js",
	"/assets/onedesk/js/brand.js",
	"/assets/onedesk/js/one_interface/centre.js",
	"/assets/onedesk/js/one/shortcuts.js",
	"/assets/onedesk/js/one/shortcut_center.js",
	"/assets/onedesk/js/one_interface/tour.js",
	"/assets/onedesk/js/one/help_center.js",
	"/assets/onedesk/js/trust_center/trust_center.js",
	"/assets/onedesk/js/check.js",
	"/assets/onedesk/js/size.js",
	"/assets/onedesk/js/desk.js",
	"/assets/onedesk/js/one_sheet/workbooks.js",
	"/assets/onedesk/js/apps.js",
	"/assets/onedesk/js/record.js",
	"/assets/onedesk/js/list_names.js",
	"/assets/onedesk/js/one_inventory/measure.js",
	"/assets/onedesk/js/outside.js",
	"/assets/onedesk/js/shell.js",
	"/assets/onedesk/js/center_section.js",
	"/assets/onedesk/js/account_center/account_center.js",
	"/assets/onedesk/js/one/access_center.js",
	"/assets/onedesk/js/one_ai/ai_center.js",
	"/assets/onedesk/js/one/notification_center.js",
	"/assets/onedesk/js/one/setup_center.js",
	"/assets/onedesk/js/one/one_control.js",
	"/assets/onedesk/js/one_hr/hr_control.js",
	"/assets/onedesk/js/one_calendar/calendar_control.js",
	"/assets/onedesk/js/one_admin/admin_control.js",
	"/assets/onedesk/js/one_studio/studio_control.js",
	"/assets/onedesk/js/one_interface/frame.js",
	"/assets/onedesk/js/one_interface/chrome.js",
	"/assets/onedesk/js/one_interface/phone.js",
	"/assets/onedesk/js/one_interface/folders.js",
	"/assets/onedesk/js/one_interface/arrange.js",
	"/assets/onedesk/js/one_interface/launcher.js",
	"/assets/onedesk/js/one_interface/nav_tree.js",
	"/assets/onedesk/js/one_interface/page.js",
	"/assets/onedesk/js/one_interface/list.js",
	"/assets/onedesk/js/one_interface/views.js",
	"/assets/onedesk/js/one_interface/board.js",
	"/assets/onedesk/js/one_interface/report.js",
	"/assets/onedesk/js/one_interface/tree.js",
	"/assets/onedesk/js/one_interface/form.js",
	"/assets/onedesk/js/one_interface/json_view.js",
	"/assets/onedesk/js/one_interface/look.js",
	"/assets/onedesk/js/one_interface/star.js",
	"/assets/onedesk/js/one_interface/select.js",
	"/assets/onedesk/js/one_interface/dialogs.js",
	"/assets/onedesk/js/one_interface/stamps.js",
	"/assets/onedesk/js/one_interface/keys.js",
	"/assets/onedesk/js/one/news_add.js",
	"/assets/onedesk/js/one_portal/portal.js",
	"/assets/onedesk/js/one_task/task_control.js",
	"/assets/onedesk/js/one_project/project_control.js",
	"/assets/onedesk/js/one_inventory/inventory_control.js",
	"/assets/onedesk/js/one_factory/factory_control.js",
	"/assets/onedesk/js/one_quality/quality_control.js",
	"/assets/onedesk/js/one_chat/chat_control.js",
	"/assets/onedesk/js/one_book/book_control.js",
	"/assets/onedesk/js/one_crm/crm_control.js",
	"/assets/onedesk/js/one_display/display_control.js",
	"/assets/onedesk/js/one_interface/print.js",
	"/assets/onedesk/js/one_interface/workspace.js",
	"/assets/onedesk/js/one_hr/passkey.js",
	"/assets/onedesk/js/one_hr/clock.js",
	"/assets/onedesk/js/one_hr/overtime.js",
	"/assets/onedesk/js/one_crm/next_step.js",
	"/assets/onedesk/js/one_task/task_timer.js",
	"/assets/onedesk/js/one_task/task_new.js",
	"/assets/onedesk/js/record_calendar.js",
	"/assets/onedesk/js/one_calendar/calendar_link.js",
	"/assets/onedesk/js/record_tabs.js",
	"/assets/onedesk/js/one_cloud/record_files.js",
	"/assets/onedesk/js/one_sheet/table_workbook.js",
	"/assets/onedesk/js/one_doc/text_writer.js",
	"/assets/onedesk/js/one_studio/extension_errors.js",
	"/assets/onedesk/js/one_mail/record_mail.js",
	"/assets/onedesk/js/one_cloud/record_activity.js",
	"/assets/onedesk/js/one_inventory/supplier_items.js",
	"/assets/onedesk/js/one_mail/mail_compose.js",
	"/assets/onedesk/js/one_cloud/onecloud_picker.js",
	"/assets/onedesk/js/one_cloud/cloud_control.js",
	"/assets/onedesk/js/band.js",
	"/assets/onedesk/js/one_inventory/rate_note.js",
	"/assets/onedesk/js/island_page.js",
	"/assets/onedesk/js/one_project/project_new.js",
	"/assets/onedesk/js/one_inventory/item_new.js",
	"/assets/onedesk/js/panel_menu.js",
	"/assets/onedesk/js/crumb_switch.js",
	"/assets/onedesk/js/one_project/project_places.js",
	"/assets/onedesk/js/phone_head.js",
	"/assets/onedesk/js/doctype_settings.js",
	"/assets/onedesk/js/one_mail/mail_templates.js",
	"/assets/onedesk/js/one_studio/places.js",
	"/assets/onedesk/js/head.js",
	"/assets/onedesk/js/one_crm/crm_record.js",
	"/assets/onedesk/js/reports.js",
	"/assets/onedesk/js/chart_colors.js",
	"/assets/onedesk/js/one_ai/oneai.js",
	"/assets/onedesk/js/one_ai/intake.js",
	"/assets/onedesk/js/trust_center/legal.js",
	"/assets/onedesk/js/one/lists.js",
])

company_data_to_be_ignored = [
	"UAE VAT Settings",
	"Tax Rule",
	"Pricing Rule",
	"Promotional Scheme",
	"Bank Transaction Rule",
	"Dunning Type",
	"Putaway Rule",
	"Plant Floor",
	"Asset Maintenance Team",
	"Leave Block List",
	"Email Digest",
	"Vehicle",
]

code_only_modules = {"Trust Center": ["One"]}

one_module_heirs = heirs()

one_makes_records = makers()

one_ai_reads = hook("one_ai_reads")

one_ai_reader = hook("one_ai_reader")

one_ai_workspace = hook("one_ai_workspace")

# What keeps OneAI's answer where it was asked: OneChat posts it into the
# conversation (one_chat/answers.py).
one_ai_chat_kept = hook("one_ai_chat_kept")

# Each app's OneAI actions, the buttons that do one thing in place, which
# AICenter lists and an administrator turns off (one_ai/actions.py).
one_ai_actions = hook("one_ai_actions")
one_ai_suggests = hook("one_ai_suggests")
automation_actions = hook("automation_actions")

one_ai_suggestions = hook("one_ai_suggestions")

one_ai_page = hook("one_ai_page")

one_homes = hook("one_homes")

one_notification_types = ["onedesk.notifications.TYPES"]

one_abilities = hook("one_abilities")

# What another module adds to a presentation as OneDeck loads and saves it
# (one_deck/api.py): OneDisplay's widgets on a screen's backdrop.
one_deck_loaded = hook("one_deck_loaded")
one_deck_saving = hook("one_deck_saving")
# a presentation's `rows` source: a Display Source's rows, for chips on a screen (one_deck/data.py)
one_deck_rows = hook("one_deck_rows")

# What each module shows on the portal, in its own portal.py's KINDS, read by
# OnePortal's engine (one_portal/portal.py `kinds`).
one_portal = hook("one_portal")

one_record_heads = hook("one_record_heads")
one_measures = hook("one_measures")
one_verbs = hook("one_verbs")
one_record_notices = hook("one_record_notices")
one_charts = hook("one_charts")
one_record_tabs = hook("one_record_tabs")

one_calendar_layers = hook("one_calendar_layers")

additional_timeline_content = {
	"Project": ["onedesk.one_project.updates.timeline", "onedesk.one_project.activity.timeline"],
	"Tenant": ["onedesk.one_admin.log.timeline"],
}

# /tv-worker.js, the TV's service worker (one_display/worker.py).
page_renderer = ["onedesk.one_display.worker.Worker"]

website_route_rules = [
	{"from_route": "/portal/<path:app_path>", "to_route": "portal"},
	{"from_route": "/s/<token>", "to_route": "s"},
	{"from_route": "/r/<token>", "to_route": "r"},
	{"from_route": "/legal/<document>", "to_route": "legal"},
	{"from_route": "/account/invoices", "to_route": "account_invoices"},
	{"from_route": "/account/profile", "to_route": "account_profile"},
	{"from_route": "/your-data", "to_route": "your_data"},
	# a radio is the TV page playing a sound zone (www/tv.py)
	{"from_route": "/radio", "to_route": "tv"},
]

has_website_permission = {
	doctype: "onedesk.one_portal.portal.has_website_permission"
	for doctype in (
		"Quotation",
		"Sales Order",
		"Delivery Note",
		"Sales Invoice",
		"Supplier Quotation",
		"Purchase Order",
		"Purchase Invoice",
	)
}
has_website_permission["Subcontracting Order"] = "onedesk.one_factory.portal.has_website_permission"

standard_portal_menu_items = [
	{"title": "Work Sent to You", "route": "/subcontracting-orders", "reference_doctype": "Subcontracting Order", "role": "Supplier"},
]

website_redirects = [
	{"source": r"/request-for-account-deletion.*", "target": "/your-data"},
	{
		"source": r"/(orders|invoices|quotations|shipments|rfq|supplier-quotations|purchase-orders|purchase-invoices|addresses|timesheets)(/.*)?",
		"target": r"/portal/\1\2",
	},
	{"source": "/project", "target": "/portal/projects"},
	{"source": r"/address/(.+)", "target": r"/portal/addresses/\1"},
	{"source": r"/update-profile/.*", "target": "/portal/profile"},
	{"source": r"/hrms(/.*)?", "target": "/desk/onehr"},
]

before_request = ["onedesk.one_cloud.dav.sign_in", "onedesk.one.webhooks.install", "onedesk.one_portal.gate.ending"]
before_job = ["onedesk.one.webhooks.install"]
after_request = ["onedesk.one_cloud.dav.headers"]

jinja = {
	"methods": [
		"onedesk.one_studio.print_html.one_html_block",
		"onedesk.one_studio.print_blocks.one_print_block",
		"onedesk.one.notify.one_mail_brand",
	]
}


user_data_fields = [
	{"doctype": doctype, "strict": True} for doctype in ("Deleted Document", "ToDo", "Notification Log")
] + [
	{"doctype": "Job Applicant", "filter_by": "email_id", "redact_fields": ["applicant_name", "email_id", "phone_number"]},
]

on_login = ["onedesk.one_portal.gate.signing_in"]
on_session_creation = ["onedesk.account_center.signin.arrived", "onedesk.account_center.devices.signed_in"]
