# OneProject

Written by hand. What OneProject does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneProject is where a piece of work bigger than a task is run: a villa's
windows, a website, an office move. A project holds its tasks, its time, what
it costs and what it is billed. It is built on ERPNext's Projects, so a
project's quotation, sales order, timesheets and invoices are the same records
the rest of One reads.

**OneTask and OneProject share one list of tasks.** OneTask answers *what do I
have to do*, for everybody; OneProject answers *how is this project going*, for
the people who run projects. A task in a project is on its people's My Tasks as
well as on the project's board.

## Finding your way

**OneProject** in the dock opens it. The rail has:

- **Projects** — every project you may see.
- **Project Tree** — every project under its parent, with its own figures.
- **Workload** — who has how many hours of open work in a week.
- **Tasks** — every task, in projects and out of them (OneTask's list).
- **Timesheet** — the time people have logged.
- Under **Setup**, **Project Template**, **Project Type**, **Activity Type**,
  **Activity Cost** and **Projects Settings**.

## A project at a glance

The top of a project's page answers first:

- **Done** — how much of the work is finished, and how many tasks of how many.
- **Due** — how long until the expected end date, or how many days late.
- **Cost** — what it has cost so far — time, purchases and materials — against
  the **Estimated Cost**, red once it is over.
- **Billed** — what has been invoiced against what there is to bill (the sales
  order, or the billable time when there is none).
- **Margin** — billed less cost, red below nought.
- **Overdue Tasks** — how many are past their date; press it for the list.
- **Next Milestone** — the next milestone task still to do, and when.

A project with sub-projects answers for **the whole tree** — the villa's cost
is the windows' and the handrails' together — and says how many sub-projects
there are.

## Who sees a project

**A project's Users are its members.** List people under **Users** on a
project and it is theirs: they see it and every task in it, and people who work
in projects but are not listed do not. A **Projects Manager** sees every
project, and whoever made a project sees it.

**A project with nobody listed is open** to everybody who works in projects,
so a small team never has to list anybody.

**A task's own people always see it** — whoever it is assigned to sees it on
My Tasks, member or not, and nothing else of the project.

Somebody who only picks a project on a quotation, an order or an invoice sees
every project in that list; the list is not the project.

## Sub-projects

A piece of a job that is billed on its own is a **sub-project**: the handrails
on a villa whose windows you are already fitting, or a booking module a website
customer asks for halfway through. Set its **Parent Project** — or press **+**
beside **Sub-projects** on the parent's page — and it is a project of its own,
with its own quotation, sales order, time, costs and invoices, that also counts
towards the parent. Sub-projects can have sub-projects of their own, as deep as
the job needs.

- A sub-project takes its parent's **customer** unless you give it another.
- A parent's page shows the **whole tree added up** — estimated cost, what it
  has cost, what has been billed and the margin — above its own figures, and
  **Sub-projects** lists the ones directly under it.
- A parent's **Calendar** has its sub-projects' tasks too, each titled with the
  sub-project it is in.
- **Members** of a project see everything under it.
- A project cannot be put under one of its own sub-projects.

**Group Under New Project** (under **Actions**) puts a new project above this
one. The villa's windows came first and the handrails were added under them;
grouping the windows under a new **Villa** project, with the handrails ticked,
leaves Windows and Handrails side by side under Villa, each with everything it
had.

## A project's board

**Board** on a project shows its tasks in four columns — **Open**, **Working**,
**Pending Review** and **Completed** — each card with its priority, when it is
due and who is on it. Drag a card to move the task along; **Add Task** at the
top of a column adds one there. The first time anybody opens a project's board
it is made, and after that everybody shares it.

**A late task is not a column.** A task past its due date stays where it is and
its date turns red, on the board and in every list.

## A project's calendar

**Calendar** on a project is that project's own calendar: every task in it
still to do, whoever is on it, and every event about the project. Drag a task
to move it. **Add Event** there makes an event about the project, and it shows
on the calendar of everybody who can open the project.

## Task names

A task is named like **TASK-2026-00042** unless its project has a **Task
Prefix**. Give a project the prefix **WEB** and its new tasks are named
**WEB-1**, **WEB-2** and on. Tasks already made keep their names; a prefix is 2
to 10 letters and digits, starting with a letter, and no two projects share
one.

## A project's schedule

**Schedule** on a project shows its tasks on a timeline — this project's and
every sub-project's, the ones not cancelled — with a bar from each task's
start to its due date. A task with only a due date is a day on it; a
**milestone** is marked as one; an arrow runs from a task to each task that
waits on it. It opens on today; **Today** comes back to it, and **Day**,
**Week**, **Month** and the rest at the foot change how much fits.

**Drag a bar to move a task**, or drag its end to make it longer. Double-click
a bar to open the task.

## What a project costs, and billing it

**Time is priced for you.** Every hour on a timesheet — the timer on a task
writes one — is costed and billed at the rate set for that person and
activity under **Setup › Activity Cost**, or the activity's own rate under
**Activity Type** when the person has none. Once the timesheet is submitted the
hours count in the project's **Cost**, and billable ones in what there is to
bill. Time on a project with a customer is billable unless somebody unticks it.

**Invoice Time** (under **Actions**, on a project with a customer) makes an
invoice for every billable hour on the project not yet invoiced — one line for
each activity, so the customer reads *Execution, 7 hours* and *Planning, 2
hours*. It asks which item to bill the time as, remembering the last one, and
opens the invoice unsaved for you to check. Submitting it marks the hours
invoiced, and the project's **Billed** goes up. A sub-project's time is
invoiced from the sub-project.

## Extra work becomes a sub-project

When a customer asks for more in the middle of a job — handrails on a villa
whose windows you are fitting — quote it as its own piece of work. On the
project's page, **+** beside **Quotation** under Connections starts a quotation
for its customer with **Sub-project Of** filled in; or set **Sub-project Of** on
any quotation. When the customer orders it and the **Sales Order** is
submitted, a new project is made for the order under that one, named after
what was ordered, with the order's total as its estimate. It has its own time,
costs and invoices, and they add up into the parent's.

To add an order to a project as it is, without a sub-project, set the order's
**Project** instead.

## Asking the team how it is going

Tick **Collect Progress** on a project (under **More Info**), choose how often —
**Daily**, **Twice Daily** or **Weekly** — and when, and the project asks its
**Users** for an update at that time. Each of them gets a notification that
opens the project, and an email too where the workspace sends mail; **Subject**
and **Message** are what the ask says.

- The project's page says **Your update on this project is asked for today**
  and has a **Post Update** button until you answer. Write what was done, what
  comes next and anything in the way.
- **Post Update** is also under **Actions** any day, asked or not.
- Posting again the same day replaces your earlier update.
- Replying to the email works too, whatever day the reply comes.
- Every update is in the project's **Activity**, under who wrote it.
- Nobody is asked on a day off in the project's **Holiday List**, and a project
  with nobody under **Users** asks nobody.

Where the workspace sends mail, everybody on the project also gets the
day's updates by email the next morning.

## Who has room this week

**Workload** in the rail shows each person with open tasks in a week — this
week unless you pick another, and every project unless you pick one:

- **Capacity (Hours)** — their working days that week, less holidays and
  approved leave, times the working day set in HR Settings (**Standard Working
  Hours**, 8 when it is not set).
- **Planned (Hours)** — the hours still to do on their tasks that fall in the
  week: a task's **Expected Time** less the time already logged on it, spread
  over the days from its start to its due date. Late work counts in full this
  week. A task given to two people counts half to each.
- **Free (Hours)** and **Load (%)** — red once they are over.
- **Tasks** (press it for the list) and **Late**, how many of them are past
  their date.
- **Not Estimated** — how many of their tasks that week have no Expected Time.
  Hours are only as good as the estimates, so a light week with five
  unestimated tasks is not a light week.

Give tasks an **Expected Time** and a date and the figures follow; nothing else
has to be kept up. You only see the tasks you may see.

## What the customer sees

A customer can follow their projects on the website. On the customer's
**Contact**, **Invite as User** gives that person a login; they sign in at the
workspace's address and land on their own pages — **Projects**, and their
quotations, orders and invoices.

**Projects** lists the customer's open projects. Opening one shows:

- how far along it is (the whole project, sub-projects included) and how many
  tasks are done;
- the **Expected End**, and how many days are left or how late it is;
- its **milestones**, its **sub-projects**, and the tasks with their dates and
  whether each is to do, in progress, in review or done;
- the order it answers to and its invoices, paid or not.

They do not see who in the team does what, the hours, the costs or the team's
updates, and they cannot change anything. A customer sees only their own
projects; to hide a project from them, leave its **Customer** empty.

## Starting from a template

A job you do again and again — a website, a fit-out, an office move — starts
from a **template**: the tasks it always has, when each begins and how long it
takes, which waits on which, the milestones and the checklists.

- **Save as Template** (under **Actions** on a project) makes one from a
  project that went well. Each task keeps when it began and ended as days after
  the project started, so a task that began on day 5 and took three days does
  the same next time. Cancelled tasks are left out.
- **New Project** on a template's page — or picking it as **From Template**
  on a new project — starts a project from it. Its tasks are made as it is
  saved, dated from the project's **Expected Start Date** (today if it has
  none), each with its sub-tasks, dependencies, checklist and whether it is a
  milestone, and named with the project's **Task Prefix** if it has one.
- **Project Template** under **Setup** lists them. A template's tasks are
  ordinary tasks marked **Is Template**; open one from the template to change
  its **Begin On (Days)** or **Duration (Days)**.

A template's tasks are nobody's work: they are not on anybody's My Tasks,
calendar or board, and everybody who works in projects can see them. A
Projects Manager makes and changes templates; anybody who works in projects
can use one.

## When a task is late, what depends on it moves

A task can depend on others (**Dependencies** on its page), in its own project
or in another under the same parent. When a task's due date moves later, the
tasks that depend on it and are still **Open** move later by as much — the
handrails wait for the frames, even though each is a sub-project of its own.

## Under the hood

For the people who build OneProject. OneAI does not read past this heading.

### What it is made of

ERPNext's **Project** is the project and its money: the customer, the one
Sales Order it answers to, `estimated_costing`, and the totals ERPNext keeps
from timesheets, purchases and invoices (`total_costing_amount`,
`total_billed_amount`, `gross_margin`). ERPNext's **Task** is the work, and is
OneTask's as much as ours. ERPNext has no project inside a project; stage 3 adds
one field for it.

- `board.py` — ERPNext's own per-project Kanban, shaped as it is made, and
  their nightly Overdue job stopped: a late task is a date, not a column. Their
  Project Summary report counted Overdue tasks, and now counts none.
- `calendar.py` — a project's **Tasks** on its own calendar, read through
  OneTask's `calendar.due`.
- `naming.py` — a project's Task Prefix, as a frappe Document Naming Rule for
  Task with the condition "project is this one". ERPNext's Task class is not
  overridden, and frappe's series for a prefix never reuses a name.
- `members.py` — who sees a project: Projects Managers all, anybody else
  holding Projects User the ones they made, are listed on, or that list
  nobody (`visible`, kept for the request). A project's tasks follow it
  through one_task/access.py. Being listed is also ERPNext's own share, and a
  site with no outgoing mail marks the invitation sent rather than failing the
  save (`invite`).
- `tree.py` — sub-projects: Parent Project (`one_parent`), the only field
  added, since ERPNext keeps money per project and has no project inside one.
  A loop is refused, a sub-project takes its parent's customer, a tree's
  figures are ERPNext's own added up each time (`totals`), and
  `group_under` puts a new project above one. `path` is where a task is, for My
  Tasks and a parent's calendar. Sub-projects are a connection on the page
  (`dashboard`), and `report/project_tree` is frappe's tree report over them.
- `plan.py` — each dependency row names its project, the field ERPNext's own
  rescheduling looks dependants up by and never writes; and a slip moves the
  dependants in the rest of the tree, which theirs never looks at
  (`reschedule`, `moved_after` is pure). The schedule is frappe's Gantt over
  Task, filtered to the tree (`public/js/project.js`); `public/js/task_list.js`
  draws a task with only a due date and lights the view mode the chart is in,
  and `public/css/desk.css` lets it scroll.
- `billing.py` — money on ERPNext's own records. Pricing is theirs
  (Activity Cost, then Activity Type, in `TimesheetDetail.update_cost`).
  **Invoice Time** (`invoice_time`, opened through
  `frappe.model.open_mapped_doc`) is their Sales Invoice with its Time Sheets
  filled from their own list of billable unbilled hours
  (`get_projectwise_timesheet_data`), lines by activity (`lines`, pure);
  submitting it is theirs too. **Sub-project Of** (`one_project`, the same
  field on Quotation and Sales Order so their mapping carries it) makes the
  submitted order a sub-project through their own `make_project` (`ordered`,
  named by `title`, pure), and adds up its sales once their after_insert has
  linked the order. `public/js/quotation.js` gives such a quotation the
  project's customer, and `tree.dashboard` lists quotations on the project.
- `updates.py` — ERPNext's Project Update, asked and answered. Their asking
  mailed only (and raised where no mail goes), asked hourly all day and twice
  daily in two hours running, and read email replies back every hour, adding
  them again each time, and only on the day asked. Their three askers and the
  collector are stopped (`settle`); `ask` (hourly, `due` pure) makes the
  Project Update, notifies members in One and mails where mail goes; `post` is
  Post Update; `answered` takes an email reply once as it arrives; `timeline`
  (additional_timeline_content) shows the answers in the project's activity.
  Their morning summary still runs, where mail goes (`sum_up`). Hourly is off
  the Frequency choices.
- `report/workload` — Workload: planned hours from ERPNext's Expected Time
  and Actual Time on the reader's visible tasks (`in_week`, `load` pure),
  capacity from the holiday list (the employee's, else the company's), HR
  Settings' Standard Working Hours and approved Leave Applications. Figures,
  not a chart.
- `portal.py` and `www/projects.py` — ERPNext's portal, reachable. Its list
  (/project) reads the Customer's Portal Users, which Invite as User never
  filled (`invited`, Contact on_update, fills it); a customer signing in was
  sent to One's desk (`onedesk.check_app_permission` now refuses website
  users on the apps screen); and its project page (/projects) checked role
  permissions a customer never has, so refused everybody — and showed the
  team's assignees and a New Task button. `www/projects.py` replaces that page
  (frappe renders the last app's page for a route): `view` checks ERPNext's own
  website permission (`may_see`) and shows progress over the tree, the end,
  milestones, sub-projects, tasks, the order and the invoices; `when` is pure.
- `templates.py` — ERPNext's Project Template, which already makes a
  project's tasks from template tasks as the project is saved. Added: **Save
  as Template** (`save_as`, with `start_of` and `days` pure), what their copy
  leaves out — milestone, expected time, checklist (`task_made`) — and a
  Projects Manager may keep templates (`settle`; ERPNext allowed only a System
  Manager). A template task is not assigned to its maker
  (one_task/capture.py), everybody in projects sees it (one_task/access.py),
  the Tasks rail entries leave templates out, and a new project's prefix rule
  is written before ERPNext makes its tasks (naming.py).
- `overview.py` — what the band answers, over the tree the reader may see:
  tasks done of all, days to the expected end (`days_left`), ERPNext's cost,
  billing and margin added up (tree.totals), overdue tasks and the next
  milestone.
- `public/js/project.js` — the Board, Calendar and Schedule buttons, the
  overview in the band, Group Under New Project, Save as Template, Invoice
  Time and Post Update;
  `public/js/project_template.js` is a template's New Project.

### What OneTask has to keep doing for projects

OneTask is everybody's; these are the promises it makes to OneProject, and each
stage below that touches tasks keeps them:

- a task's people see it wherever it is, and a task in no project is its own
  people's alone (`one_task/access.py`);
- a sub-task is in its parent's project (`one_task/task.py`);
- the timer writes time against whichever project a task is in;
- My Tasks names the project a task is in — and, once there are sub-projects,
  the path to it.

### The plan

1. **The split.** *Done.* The project half of OneTask — the board, a project's
   calendar, task prefixes, the plan and the project settings — moves here,
   and OneProject gets its own place in the dock.
2. **Members.** *Done.* A project's Users decide who sees it and its tasks,
   instead of every Projects User seeing every project; a project listing
   nobody stays open. A task's own people still see it. Members of a project
   will see what is under it once there is something under it (`under`).
3. **Sub-projects.** *Done.* A Parent Project on Project, to any depth, so a separately
   billable piece — the handrails on a villa, a change request on a website —
   is a project of its own with its own quotation, sales order, time and
   invoices. A project cannot sit under itself. A parent shows its own figures
   and the whole tree's, worked out rather than stored, and its sub-projects as
   an indented list. **Group Under New Project** makes a parent above a project
   and moves it and any of its sub-projects under it. A sub-project takes its
   parent's customer unless told otherwise. The calendar includes the
   sub-projects' tasks, titled by sub-project; the board stays one project's,
   since ERPNext's board is a filter fixed when it is made.
4. **The overview.** *Done.* A project's page answers first: done so far, due against
   expected, cost against budget, billed against billable, overdue tasks and
   the next milestone. Figures, not charts.
5. **The plan.** *Done.* frappe's Gantt over a project's tasks and its
   sub-projects', milestones on it, and dependencies that move across projects
   in one tree, not only within one. Three things of frappe's needed fixing for
   it to show anything: a task with no start date, a chart that never scrolled,
   and the view mode pills.
6. **Templates.** *Done.* ERPNext's Project Template starts a project with its
   tasks, sub-tasks and dependencies; a project that went well is saved as
   one; milestones, expected time and checklists come across; the project's
   prefix names them; templates are the team's, not their maker's. A template
   of a whole tree of sub-projects is not built: ERPNext's template is one
   project.
7. **Cost and billing.** *Done.* Time priced by Activity Cost, which ERPNext
   already did; a project's billable hours invoiced in one step, by activity;
   a quotation for extra work ordered as a sub-project of the project it is
   for. A rate per customer or per project is not built: ERPNext prices time
   by person and activity only.
8. **Status updates.** *Done.* ERPNext's Project Update asks the team for a
   note on a schedule — in One, and by mail where there is mail — the note is
   written on the project's page or by replying, and the answers are in the
   project's activity. Asking the customer is stage 9's.
9. **The customer's view.** *Done.* ERPNext's portal shows a customer their
   own projects: a customer invited from their contact can sign in, reach the
   list and open a project, which shows its progress, end, milestones,
   sub-projects, tasks, order and invoices, and nothing of the team's. A
   customer adding tasks or commenting is not built.
10. **Workload.** *Done.* Who has how many hours of open work in a week, from
    the expected time left on the tasks assigned to them, against their working
    days less holidays and leave, with what is late and what is not estimated.
    Moving work between people is done on the tasks, not here.
11. **The old OneProject.** It left OneApp in `56216d9a`; read it from there,
    take what it had that this does not.
