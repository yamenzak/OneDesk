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
- **Tasks** — every task, in projects and out of them (OneTask's list).
- **Timesheet** — the time people have logged.
- Under **Setup**, **Project Template**, **Project Type**, **Activity Type**,
  **Activity Cost** and **Projects Settings**.

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

## When a task is late, what depends on it moves

A task can depend on others (**Dependencies** on its page). When a task's due
date moves later, the tasks in the same project that depend on it and have not
started move later by as much.

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
  rescheduling looks dependants up by and never writes.
- `public/js/project.js` — the Board and Calendar buttons, the tree's figures
  in the band, and Group Under New Project.

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
4. **The overview.** A project's page answers first: done so far, due against
   expected, cost against budget, billed against billable, overdue tasks and
   the next milestone. Figures, not charts.
5. **The plan.** frappe's Gantt over a project's tasks, milestones on it, and
   dependencies that move across projects in one tree, not only within one.
6. **Templates.** ERPNext's Project Template starts a project with its tasks and
   their dependencies.
7. **Cost and billing.** Time priced by Activity Cost; hours invoiced from
   timesheets (OneBook); a quotation accepted as a sub-project of the project
   it is for.
8. **Status updates.** ERPNext's Project Update asks the team for a note on a
   schedule, and the answers are kept on the project.
9. **The customer's view.** ERPNext's portal shows a customer their own
   projects.
10. **Workload.** Who has how many hours of open work this week, from expected
    time on the tasks assigned to them.
11. **The old OneProject.** It left OneApp in `56216d9a`; read it from there,
    take what it had that this does not.
