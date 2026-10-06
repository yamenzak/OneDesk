"""How each doctype is shown: its records and its collections
(docs/PASSOVER.md, point 4).

Frappe shows every doctype the same way: its form for a record, and for the
collection each view the doctype qualifies for. Most stay that way. Where we
do more it is declared here, and `tests/guards/test_tiers.py` fails on
anything done and not declared.

- **A record** is shown in one of three tiers. **desk** is frappe's form as it
  is, and every doctype not named below. **head** is frappe's form with a
  Record Head above its fields (`one/head.py`). **page** is a page of its own,
  for the few records people work inside all day, keeping all the form gives
  (point 6).
- **A collection** keeps every view frappe offers it. Ours may set a view up
  (a list's indicators and filters, a calendar's fields, a tree's parent),
  never take one away.
- **A screen** of ours that stands for a collection or a tool is a desk page,
  named here with what it is.
"""

#: Every collection view frappe has. Ours set one up; none is taken away.
VIEWS = ("List", "Report", "Dashboard", "Kanban", "Calendar", "Gantt", "Tree", "Image", "Map", "Inbox")

#: Records with a page of their own, and why the form was not enough.
PAGES = {
	"Project": "a job is run from it all day: its money with both sides, tasks, time, suppliers, people and files, across its sub-projects",
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
	"Salary Slip",
	"Sales Invoice",
	"Shift Request",
	"Shift Type",
	"Supplier",
	"Tenant",
	"Tenant Domain",
	"Vehicle Log",
	"Workspace Account",
)

#: Collection views we set up, by doctype: which view and what it adds. A list
#: script, a calendar's fields or a tree's parent (doctype_list_js,
#: doctype_calendar_js, doctype_tree_js in hooks.py) is declared here.
COLLECTIONS = {
	"Project": {
		"List": "each project's standing in one pill, and the views and dashboard of OneProject",
		"Calendar": "each project a bar from its start to its end",
		"Gantt": "the same bars, filled as far as each is done, with milestones under them",
		"Tree": "each project under its parent",
		"Kanban": "Projects by Health",
		"Image": "each project's cover",
	},
	"Task": {"List": "a task's due date as a day, red once it has passed"},
	"Lead": {"List": "an overdue next step in red"},
	"Opportunity": {
		"List": "an overdue next step in red",
		"Kanban": "the pipeline, each stage with what it is worth",
	},
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
	"my-tasks": "the reader's own tasks, grouped (Task)",
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
