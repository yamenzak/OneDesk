"""How each doctype is shown: its records and its collections
(docs/PASSOVER.md, point 4).

Where we do more than frappe it is declared here, and
`tests/guards/test_tiers.py` fails on anything done and not declared.
"""

#: Every collection view frappe has. Ours set one up; none is taken away.
VIEWS = ("List", "Report", "Dashboard", "Kanban", "Calendar", "Gantt", "Tree", "Image", "Map", "Inbox")

#: Records with a page of their own, and why the form was not enough.
PAGES = {
	"Project": "a job is run from it all day: its money with both sides, tasks, time, suppliers, people and files, across its sub-projects",
	"Project Template": "its tasks are laid out, nested, linked and timed as a project's are, which a form's child table cannot show",
	"Task": "a person's work is done from it all day: what it waits on, its checklist and sub-tasks, its time and its conversation",
	"Item": "the stores run on it: where it is kept and how much, who it is bought from and sold to, what it is made of and goes into",
}

#: Records to become pages next, and why.
NEXT_PAGES = {
	"Opportunity": "a deal is worked from first call to signed order, with its calls, mails, quotes and next steps",
	"Lead": "a lead is worked until it becomes a deal or is let go",
	"Employee": "a person's whole time with the company: contract, leave, pay, assets, reviews",
	"Job Applicant": "a candidate is moved through interviews, feedback and an offer",
}

#: Records with a Record Head: frappe's form with its band, sentence and verbs
#: above the fields (each module's heads.py, `one_record_heads`).
HEADS = (
	"AI Action Setting",
	"AI Model",
	"AI Proposal",
	"Account Request",
	"Appraisal",
	"Asset",
	"Attendance Request",
	"Clock Attempt",
	"Contract",
	"Credit Ledger Entry",
	"Customer",
	"Employee",
	"Employee Promotion",
	"Employee Tax Exemption Declaration",
	"Employee Tax Exemption Proof Submission",
	"Expense Claim",
	"Extension",
	"Item",
	"Lead",
	"Leave Application",
	"Leave Encashment",
	"Offering",
	"One Admin Settings",
	"Opportunity",
	"Overtime Slip",
	"Payroll Entry",
	"Project",
	"Provisioning Job",
	"Purchase Invoice",
	"Purchase Order",
	"Salary Slip",
	"Sales Invoice",
	"Shift Request",
	"Shift Type",
	"Stock Entry",
	"Supplier",
	"Tenant",
	"Tenant Domain",
	"Vehicle Log",
	"Warehouse",
	"Workspace Account",
)

#: Collection views we set up, by doctype: which view and what it adds. A list
#: script, a calendar's fields or a tree's parent (doctype_list_js,
#: doctype_calendar_js, doctype_tree_js in hooks.py) is declared here.
COLLECTIONS = {
	"Project Template": {"List": "From the Library beside Add, copying a preset in and opening it"},
	"Timesheet": {"List": "OneProject's Time: the project, the days and the billable hours as columns, the ID on hover"},
	"Project": {
		"List": "each project's standing in one pill, and the views and dashboard of OneProject",
		"Calendar": "each project a bar from its start to its end",
		"Gantt": "the same bars, filled as far as each is done, with milestones under them",
		"Tree": "each project under its parent",
		"Kanban": "Projects by Health",
		"Image": "each project's cover",
		"Report": "the Project column reads each project's name, without a second name column or the cover's file path",
		"Dashboard": "OneProject's cards and charts, where things stand first, then who and what for, then over time",
	},
	"Task": {
		"List": "a task's due date as a day, red once it has passed",
		"Gantt": "a task with only a due date is a bar on its day, and the pills light the mode it is in",
		"Kanban": "a project's board, a column per status as it is made, with Template and Cancelled put away, and Overdue put away on ERPNext's own board",
		"Report": "the start date read as a day, as the due date is",
		"Calendar": "a template's tasks left out, and a task planned by the day drawn as a day",
		"Tree": "a template's tasks left out, each task its subject and where it stands",
	},
	"Warehouse": {"Tree": "opened all the way down, without ERPNext's Company filter"},
	"Lead": {"List": "an overdue next step in red"},
	"Opportunity": {
		"List": "an overdue next step in red",
		"Kanban": "the pipeline, each stage with what it is worth",
	},
	"Contract": {"List": "whether each contract is signed, when it ends and the project it is for"},
	"Attendance": {"List": "Mark Attendance kept, merged into hrms's own settings"},
	"Employee Checkin": {"List": "whether each log counted"},
	"AI Model": {"List": "the model catalogue from the operator's side"},
	"AI Proposal": {"List": "whether anybody still has to answer each suggestion"},
	"Credit Ledger Entry": {"List": "the credit ledger from the operator's side"},
	"Deleted Document": {"List": "the Recycle Bin, restored through One"},
	"Version": {"List": "the Audit Log's changes, each a sentence"},
	"Activity Log": {"List": "the Audit Log's sign-ins, each a sentence"},
	"Access Log": {"List": "the Audit Log's exports, each a sentence"},
	"Personal Data Deletion Request": {"List": "Account Deletions and where each stands"},
	"Personal Data Download Request": {"List": "Data Copies and where each stands"},
}

#: Desk pages of ours, and what each one is.
SCREENS = {
	"project-view": "the page a Project opens on (PAGES)",
	"project-template-view": "the page a Project Template opens on (PAGES)",
	"task-view": "the page a Task opens on (PAGES)",
	"item-view": "the page an Item opens on (PAGES)",
	"stock-on-hand": "what the stores hold now, item by item, in every warehouse or one (Bin)",
	"my-tasks": "the reader's own tasks, grouped, drawn with frappe-ui (Task)",
	"timers": "the reader's task timers, the rail's Timers popover on a page for a phone (Timesheet)",
	"onemail": "mail, read and written (Communication)",
	"onecalendar": "everybody's calendar (Event, and the dated records shown on it)",
	"onecloud": "the files (File)",
	"intake": "what Intake read and did (Reading, Intake Action)",
	"ready-to-submit": "drafts waiting to be submitted, across doctypes",
	"masters": "the simple lists, one home each",
	"legal": "the agreements a person has agreed to",
	"settings": "the reader's own settings",
	"workspace-settings": "the workspace's settings",
}
