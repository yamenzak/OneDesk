app_name = "onedesk"
app_title = "One"
app_publisher = "One"
app_description = "Every One product, as modules on the Frappe desk"
app_email = "hello@4dl.app"
app_license = "agpl-3.0"
app_logo_url = "/assets/onedesk/images/one.svg"

# The site wears One from its first boot and carries nobody else's navbar rows or
# checklists; after that all of it is the tenant's, in Website and Navbar Settings.
after_install = [
	"onedesk.one.roles.ensure",
	"onedesk.one.company.hide",
	"onedesk.one_hr.names.hide",
	"onedesk.one_hr.money.hide",
	"onedesk.one_hr.policy.seed",
	"onedesk.one_hr.leave.templates",
	"onedesk.one_hr.leave.encashable",
	"onedesk.one_hr.accounts.ready",
	"onedesk.one_hr.accounts.year",
	# The OneAI user hiring comments are written by, and the hiring switches.
	"onedesk.one_hr.hiring.ensure",
	"onedesk.one.brand.apply",
	"onedesk.one.declutter.apply",
	"onedesk.one.companions.apply",
	# Which kind of site this is, and the role that follows from it.
	"onedesk.one_admin.site.apply",
	# After that, because what it does depends on which kind this is.
	"onedesk.one_ai.instructions.trim",
	"onedesk.one_ai.instructions.ready",
	"onedesk.one_admin.actions.voice",
	"onedesk.one_crm.stages.settle",
	"onedesk.one_crm.board.sync",
	"onedesk.one_crm.next.settle",
	"onedesk.one_crm.record.settle",
	"onedesk.one_crm.capture.defaults",
	"onedesk.one_crm.access.settle",
	"onedesk.one_task.access.settle",
	"onedesk.one_task.board.settle",
]

# Their dock files do not carry the mount, so a newer erpnext or hrms clears it,
# and nobody is ever asked which company; see one/company.py.
after_migrate = [
	"onedesk.one.roles.ensure",
	"onedesk.one.companions.apply",
	"onedesk.one.company.hide",
	"onedesk.one_hr.names.hide",
	"onedesk.one_hr.money.hide",
	"onedesk.one_hr.policy.seed",
	"onedesk.one_hr.leave.templates",
	"onedesk.one_hr.leave.encashable",
	"onedesk.one_hr.accounts.ready",
	"onedesk.one_hr.accounts.year",
	"onedesk.one_hr.hiring.ensure",
	"onedesk.one_admin.site.apply",
	"onedesk.one_ai.instructions.trim",
	"onedesk.one_ai.instructions.ready",
	"onedesk.one_admin.actions.voice",
	"onedesk.one_crm.stages.settle",
	"onedesk.one_crm.board.sync",
	"onedesk.one_crm.next.settle",
	"onedesk.one_crm.record.settle",
	"onedesk.one_crm.access.settle",
	"onedesk.one_task.access.settle",
	"onedesk.one_task.board.settle",
]
extend_bootinfo = "onedesk.one.boot.boot_session"

# A pattern is not visible from inside one request. See one_hr/healing.py.
scheduler_events = {
	# A site takes minutes to build, so a request makes a job and this walks it.
	# Inert on a tenant site: `runner.tick` asks whether this site administers
	# workspaces before it asks whether there is anything to do.
	"cron": {"*/2 * * * *": ["onedesk.one_admin.runner.tick"]},
	"daily": [
		"onedesk.one.account.nightly",
		"onedesk.one_admin.domains.nightly",
		# One rung a workspace, one workspace at a time. See one_admin/ladder.py.
		"onedesk.one_admin.lifecycle.nightly",
		# Providers ship models weekly and re-price them without an announcement.
		"onedesk.one_admin.catalogue.nightly",
		# Holds whose call never came back, which nothing else would let go.
		"onedesk.one_admin.ledger.nightly",
		# The credit every plan promises. Keyed by month, so nightly is harmless.
		"onedesk.one_admin.topup.monthly",
		"onedesk.one_admin.storage.nightly",
		"onedesk.one_hr.healing.nightly",
		# The sound of old interview recordings; their transcripts stay.
		"onedesk.one_hr.hiring.purge",
		"onedesk.one_hr.leaving.nightly",
		"onedesk.one_hr.setup.nightly",
	],
	"hourly": ["onedesk.one_hr.closing.hourly"],
}

doc_events = {
	# A Public event is on everybody's calendar. See one_calendar/events.py.
	"Event": {"validate": "onedesk.one_calendar.events.validate"},
	# hrms counts milestones by letting an insert fail, and the message outlives
	# the savepoint. See one/quiet.py.
	"*": {
		"on_submit": "onedesk.one.quiet.milestone",
		"after_insert": "onedesk.one.quiet.milestone",
		# The fields OneAI wrote that still say it. See one_ai/touch.py.
		"onload": "onedesk.one_ai.touch.onload",
		"on_trash": "onedesk.one_ai.touch.forget",
	},
	"Employee": {
		"validate": "onedesk.one_hr.leaving.notice_ends_on",
		"on_update": "onedesk.one_hr.leaving.on_employee_update",
	},
	# One day's overtime is claimed once, and the slip says what it pays.
	# See one_hr/overtime.py.
	"Overtime Slip": {
		"before_validate": "onedesk.one_hr.overtime.before_validate",
		"validate": "onedesk.one_hr.overtime.no_double_pay",
	},
	# A block reads as a block. See one_hr/timesheet.py.
	"Timesheet": {"before_validate": "onedesk.one_hr.timesheet.before_validate"},
	# The third request doctype, answered like the other two. See one_hr/leave.py.
	"Leave Application": {"before_submit": "onedesk.one_hr.leave.before_submit"},
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
	"Job Applicant": {"after_insert": "onedesk.one_hr.hiring.arrived"},
	"Interview": {
		"after_insert": "onedesk.one_hr.hiring.scheduled",
		"onload": "onedesk.one_hr.hiring.interview_onload",
	},
	# A new grievance is read, and a sensitive one is kept to HR Managers and
	# its raiser. See one_hr/ai_grievance.py.
	"Employee Grievance": {
		"after_insert": "onedesk.one_hr.ai_grievance.raised",
		"validate": "onedesk.one_hr.ai_grievance.unmarked",
	},
	# A recording's sound goes by its retention or an HR Manager's hand.
	"File": {"on_trash": "onedesk.one_hr.hiring.keep_sound"},
	# An onboarding is for somebody who is not an employee yet, so the holiday
	# list has to come from the company. See one_hr/lifecycle.py.
	"Employee Onboarding": {"before_validate": "onedesk.one_hr.lifecycle.onboarding"},
	# A task of nobody's is its maker's. See one_task/capture.py.
	# A sub-task's parent is a group and its project is the parent's, and a
	# checklist is the progress. See one_task/task.py.
	"Task": {
		"before_insert": "onedesk.one_hr.lifecycle.task",
		"after_insert": "onedesk.one_task.capture.task_made",
		"before_validate": "onedesk.one_task.task.before_validate",
		"on_recurring": "onedesk.one_task.task.recurring",
	},
	# A project's tasks are named with its prefix. See one_task/naming.py.
	"Project": {
		"validate": "onedesk.one_task.naming.validate",
		"on_update": "onedesk.one_task.naming.on_update",
	},
	# A project's board, as ERPNext makes it, shaped. See one_task/board.py.
	"Kanban Board": {"before_insert": "onedesk.one_task.board.shape"},
	"Training Result": {"before_validate": "onedesk.one_hr.lifecycle.result"},
	# The reason is a record and submitting is an approval. See one_hr/request.py.
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
		"on_update": "onedesk.one_crm.next.on_update",
	},
	# An Assignment Rule's pick becomes the owner, and a lead's first reply is
	# timed (one_crm/capture.py). A to-do about nothing becomes a task, and the
	# last one ticked off on a task of one's own completes it (one_task/capture.py).
	"ToDo": {
		"before_insert": "onedesk.one_task.capture.todo_made",
		"after_insert": "onedesk.one_crm.capture.assigned",
		"on_update": "onedesk.one_task.capture.todo_changed",
	},
	"Communication": {"after_insert": "onedesk.one_crm.capture.replied"},
	"Call Log": {"after_insert": "onedesk.one_crm.capture.replied"},
	# The board has a column per stage. See one_crm/board.py.
	"Sales Stage": {
		"on_update": "onedesk.one_crm.board.sync",
		"after_rename": "onedesk.one_crm.board.sync",
		"after_delete": "onedesk.one_crm.board.sync",
	},
	"Quotation": {
		"on_submit": "onedesk.one_crm.stages.follow",
		"on_cancel": "onedesk.one_crm.stages.follow",
		"on_update_after_submit": "onedesk.one_crm.stages.follow",
	},
	"Sales Order": {
		"on_submit": "onedesk.one_crm.stages.follow",
		"on_cancel": "onedesk.one_crm.stages.follow",
	},
	# Submitting is the approval, and it says which shift. See one_hr/shift.py.
	"Shift Request": {
		"before_validate": "onedesk.one_hr.shift.before_validate",
		"before_submit": "onedesk.one_hr.shift.before_submit",
	},
}

# The One marks, as sprite symbols every Icon field can name. Generated by
# `scripts/icons.py`, with each one's ids rewritten so two marks in one sprite
# do not share a gradient.
# The marks, the reasons a day pauses, and the reasons a day still counts.
# A workspace adds its own to any of them.
# The second gate on the operator console. The role decides what is listed; this
# decides what is answered, and it reads site_config.json rather than a table —
# so a tenant administrator granting themselves One Operator on their own
# workspace gets a rail entry and nothing behind it. See one_admin/site.py.
has_permission = {
	"Employee Grievance": "onedesk.one_hr.ai_grievance.allowed",
	# Everybody keeps tasks; a task with no project is its own people's.
	# See one_task/access.py.
	"Task": "onedesk.one_task.access.allowed",
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
	"Employee Grievance": "onedesk.one_hr.ai_grievance.query",
	"Task": "onedesk.one_task.access.query",
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

fixtures = [
	"Custom Icon",
	"Clock Reason",
	"Attendance Reason",
	"Identification Document Type",
	# The two leave mails hrms promises and ships nothing to send.
	"Email Template",
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
]


# A record answers before it offers links; see `onedesk/one_hr/employee.py`.
doctype_js = {
	# A workspace is read-only and carries verbs instead; see one_admin/operator.py.
	# A workspace reads its own account and manages its addresses; the account
	# itself lives on the administrator. See one/account.py.
	"Workspace Account": "public/js/workspace_account.js",
	"Tenant": "public/js/tenant.js",
	# A job says where in its walk it stopped; see one_admin/steps.py SAID.
	"Provisioning Job": "public/js/job.js",
	# A paid signup that never became a workspace can be built from its screen.
	"Account Request": "public/js/account_request.js",
	# A custom domain is Frappe Cloud's answer written down, and can be re-asked.
	"Tenant Domain": "public/js/tenant_domain.js",
	# A price list says how many workspaces already bought what is being edited.
	"Offering": "public/js/offering.js",
	# The gateway is the one credential here with nothing that later proves it.
	"One Admin Settings": "public/js/admin_settings.js",
	# What is charged on top, and what one call actually comes to.
	"AI Model": "public/js/ai_model.js",
	# The model list comes from the account, filtered to what the action needs.
	"AI Action Setting": "public/js/ai_action_setting.js",
	# Read-only with two verbs: nothing happened yet, and it is yours to decide.
	"AI Proposal": "public/js/ai_proposal.js",
	"Employee": "public/js/employee.js",
	"Employee Attendance Tool": "public/js/attendance_tool.js",
	"Attendance": "public/js/attendance.js",
	"Clock Network": "public/js/learned.js",
	"Clock Place": "public/js/learned.js",
	"Shift Type": "public/js/shift_type.js",
	"Attendance Request": "public/js/attendance_request.js",
	"Shift Request": "public/js/shift_request.js",
	"Overtime Slip": "public/js/overtime_slip.js",
	"Timesheet": "public/js/timesheet.js",
	"Leave Application": "public/js/leave_application.js",
	"Leave Control Panel": "public/js/leave_control_panel.js",
	"Leave Encashment": "public/js/leave_encashment.js",
	"Salary Slip": "public/js/salary_slip.js",
	"Payroll Entry": "public/js/payroll_entry.js",
	"Expense Claim": "public/js/expense_claim.js",
	"Vehicle Log": "public/js/vehicle_log.js",
	"Appraisal": "public/js/appraisal.js",
	"Employee Promotion": "public/js/employee_promotion.js",
	# The interview recorder; see one_hr/hiring.py.
	"Interview": "public/js/hiring.js",
	"Employee Tax Exemption Declaration": "public/js/exemption.js",
	"Employee Tax Exemption Proof Submission": "public/js/exemption.js",
	"Opportunity": "public/js/opportunity.js",
	# Next Step Done, which asks what comes next. See public/js/next_step.js.
	"Lead": "public/js/lead.js",
	# The project's board is a button of its own. See one_task/board.py.
	"Project": "public/js/project.js",
	# A timer on the task. See one_task/timer.py.
	"Task": "public/js/task.js",
}

# Loaded after the doctype's own list script, so ours has the last word.
doctype_list_js = {
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
}

override_doctype_dashboards = {
	"Attendance": ["onedesk.one_hr.attendance.dashboard"],
	# A task's sub-tasks, as a connection. See one_task/task.py.
	"Task": ["onedesk.one_task.task.dashboard"],
}

# Every shift location counts, not the first. See one_hr/checkin.py.
override_doctype_class = {"Employee Checkin": "onedesk.one_hr.checkin.OneEmployeeCheckin"}

add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"logo": app_logo_url,
		"route": "/desk/one",
		# Ahead of erpnext (1) and hrms (2). Not 0: the boot reads this with `or`,
		# so a falsy one falls through to the default and lands One mid-row.
		"sequence_id": 0.5,
	}
]

# `setup_wizard_url` is ignored while erpnext or hrms are installed.
# Reaches the login page: base.html renders these and login.html extends it.
web_include_js = ["/assets/onedesk/js/login.js"]

setup_wizard_requires = "assets/onedesk/js/setup_wizard.js"
setup_wizard_stages = "onedesk.one.setup_wizard.get_setup_stages"

app_include_css = [
	"/assets/onedesk/css/theme.css",
	"/assets/onedesk/css/desk.css",
	"/assets/onedesk/css/oneai.css",
]
# /start and /welcome, which are not desk screens and load none of the above.
web_include_css = ["/assets/onedesk/css/portal.css"]
app_include_js = [
	"/assets/onedesk/js/theme.js",
	"/assets/onedesk/js/desk.js",
	"/assets/onedesk/js/passkey.js",
	"/assets/onedesk/js/clock.js",
	"/assets/onedesk/js/overtime.js",
	"/assets/onedesk/js/decision.js",
	"/assets/onedesk/js/next_step.js",
	"/assets/onedesk/js/task_timer.js",
	"/assets/onedesk/js/record_calendar.js",
	"/assets/onedesk/js/band.js",
	"/assets/onedesk/js/crm_record.js",
	"/assets/onedesk/js/reports.js",
	"/assets/onedesk/js/oneai.js",
]

# OneAI is not a place. Its screens live in One — what a workspace
# administers — and in One Admin, what the operator does; a module sidebar of
# its own was five doctype lists nobody navigates to. Its doctypes and reports
# stay where they are; only the dock entry goes, and One inherits the rest.
# A mapping, as frappe's and erpnext's are: module to where its navigation went.
code_only_modules = {"One AI": ["One"]}

# What OneAI can do in each module, owned by the module. Reads run as the
# person asking; suggests write a card. Suggestions are what the panel offers
# when it opens on a page. See one_ai/tools.py and one_ai/suggest.py.
one_ai_reads = [
	"onedesk.one_hr.ai.my_leave",
	"onedesk.one_hr.ai.appraisal_facts",
	"onedesk.one_hr.ai.why_people_leave",
	"onedesk.one_hr.ai.interview_facts",
	"onedesk.one_hr.ai_payroll.payroll_changes",
	"onedesk.one_hr.ai_letters.letter_facts",
	"onedesk.one_hr.ai_policy.hr_policy",
	"onedesk.one_hr.ai_growth.goal_facts",
	"onedesk.one_hr.ai_growth.training_options",
	"onedesk.one_crm.ai.deal_facts",
	"onedesk.one_crm.ai.lead_facts",
	"onedesk.one_crm.ai.gone_quiet",
	"onedesk.one_crm.ai.why_we_lose",
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
	"onedesk.one_crm.ai.plan_next_step",
	"onedesk.one_crm.ai.write_up_call",
]
one_ai_suggestions = ["onedesk.one_hr.ai.SUGGESTIONS", "onedesk.one_crm.ai.SUGGESTIONS"]

# What each module puts on the calendar, as layers. Each reads its own records
# as the person looking; nothing is copied. See one_calendar/layers.py.
one_calendar_layers = [
	"onedesk.one_calendar.events.LAYERS",
	"onedesk.one_task.calendar.LAYERS",
	"onedesk.one_crm.calendar.LAYERS",
	"onedesk.one_hr.calendar.LAYERS",
]
