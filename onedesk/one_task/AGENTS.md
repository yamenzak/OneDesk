# OneTask

The one file for agents, OneAI and us: what OneTask is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneTask is where all of a person's work is kept. Every piece of work is a
task: a personal to-do, a project step, a sub-task or a milestone. A deal's
next step, a leave application and a meeting are not tasks; they belong to
the deal, the application and the calendar.

## Connections

- **From OneProject**: A project task assigned to you shows on My Tasks with its project. Who else sees a project task follows who can see the project. **Open Task** in a project's task panel opens the task on its own page.
- **From OneHR**: Each activity on an onboarding or separation checklist becomes a task for whoever does it. A separation also adds a Return task for each asset the person holds. Such a task names the person joining or leaving and opens their onboarding or separation, not the checklist project kept behind it.
- **From OneAI**: Tasks are made from what arrives, such as answering an enquiry or renewing a passport before it runs out. Your Assignment Rules decide who gets one first, and otherwise it goes to whoever's mail it came in. A task about a bill or a delivery for a project is in that project. Their steps tick themselves when the record they wait on changes, such as a bill being paid.
- **To One**: Home shows how many of your tasks are due today or overdue.
- **To OneCalendar**: Your tasks show under My Tasks on their due date, and dragging one moves its dates. Anything else assigned to you, such as a deal or a leave application, shows under Assigned to Me.
- **To OneProject**: A task's progress counts toward its project's progress. Time from the timer is logged on the task's project, as billable when the project bills hours. When a milestone billed on completion is done, the project's manager is told to bill it.
- **To OneHR**: The timer writes your time on your timesheet for the week, and makes the timesheet if you don't have one.

## Under the hood

### What each thing is

frappe and ERPNext have five things that sound like work, and only one of them
is:

- **Task** (ERPNext) — the work. A to-do of one's own is a task with no
  project; a sub-task sets `parent_task` on a task marked `is_group`; a
  milestone is `is_milestone`. ERPNext has no project inside a project, so a
  phase of one is a group task.
- **ToDo** (frappe) — an assignment: *this person, on this record*. **Assign**
  makes one on any record, a task included.
- **Share** — DocShare, which lets one person open one record. Not work.
- **Event** — a time something happens. Not work.
- **Project** (ERPNext) — tasks, timesheets and what they cost, together.

### How it is made

- `access.py` — Desk User may keep tasks (a Custom DocPerm, written once), and
  `allowed` and `query` narrow that to one's own tasks, plus every project
  task for a person whose other roles already read tasks. Hooks can only take
  access away, which is why the grant comes first.

  ERPNext lets a Projects User see every task and everybody else none. In One
  every person keeps their own to-dos as tasks, so every desk user may now
  make one, and sees:

  - **the tasks they made, and the ones assigned to them**, always;
  - **a task in a project they may see**, if a role other than Desk User
    already lets them read tasks — a Projects User, an HR Manager for
    boarding tasks. Which projects that is, is OneProject's rule
    (one_project/members.py): a Projects Manager sees them all, anybody else
    the ones they made, are members of, or that list nobody;
  - **a template task**, for the same people, since a template is the whole
    team's (one_project/templates.py);
  - **a task somebody shared with them**, which is frappe's own rule.

  A task with no project is somebody's own to-do, so nobody else sees it, a
  Projects User included, unless it is assigned or shared to them.

  The grant is a Custom DocPerm for Desk User (`settle`) and the rest is the
  two hooks narrowing it. Who "already reads tasks" is read off the doctype's
  own rules, so a workspace that gives another role Task read changes the
  answer without touching the file.
- `capture.py` — a to-do about nothing becomes a task; a task of nobody's is
  its maker's; the last assignment ticked off on a task in no project
  completes it. ERPNext already closes the assignments when a task completes.

  frappe has two things called a to-do. A **ToDo** is an assignment —
  somebody was given something to do about a record — and assigning a task, a
  deal or a leave application makes one. A ToDo with nothing it is about is
  the other kind: a note to self, made from the ToDo form or
  `frappe.desk.doctype.todo.todo.new_todo`, and it lives outside everything
  else — no project, no sub-tasks, no board. So One keeps one kind of work,
  the Task:

  - **A to-do with nothing it is about becomes a task** (`todo_made`). The
    task is made from what was typed, and the ToDo is kept as what it always
    was, the assignment on it. Whoever it was for is still who it is for.
  - **A task made with no project and nobody on it is its maker's**
    (`task_made`), so "assigned to me" is the one question that finds all of
    a person's work, on the calendar and in every list. A template task is
    nobody's work (one_project/templates.py) and is not.
  - **Ticking off the last assignment on a task with no project completes
    it** (`todo_changed`). ERPNext already does the other direction:
    completing a task closes its assignments. A task in a project is not
    completed by one person being done with it.
- `calendar.py` — **My Tasks** and **Assigned to Me** on OneCalendar (the
  second leaves out assignments on tasks, which are already on the first),
  `due` for any list of tasks (OneProject's calendar reads it), and `move`: a
  task dragged shifts both its dates by the same days (`shifted` is pure).

  A task is drawn on the day it is due, from its own table, and done where it
  lives. Assignments are drawn too, but only the ones on other records — a
  deal, a leave application — since an assignment on a task is that task,
  already on the calendar once. **Dragging a task moves its dates** (`move`):
  the due date goes to the day it was dropped on, and the start goes with it
  by as many days, so a task keeps its length. A time of day already set
  stays. A task is a day on the calendar, so it is dragged, never stretched.
  A project's own calendar is OneProject's (one_project/calendar.py), and
  reads tasks through `due`.
- `custom/task.json` — the due date is asked for when a task is added, the
  Checklist (Task Step) is added, and Overdue is taken off the statuses
  (one_project/board.py says why). The page's order puts Timeline, open,
  ahead of Is Template, Issue and Color; Company is hidden; the list shows
  Subject, Status, Project, Priority and the due date (`task_list.js` drops
  frappe's ID column), each as wide as it needs, the subject widest.
- `task.py` — a sub-task's parent becomes a group and lends its project; the
  checklist is the progress; sub-tasks are a connection on the task's page.

  **A sub-task is a task** with `parent_task` set, which is ERPNext's own
  tree. ERPNext refuses a parent that is not marked Is Group, a box nobody
  ticks before wanting a sub-task, so the parent is marked when the first one
  is made. A sub-task made from its parent's page is in the parent's project;
  without that it would be nobody's but its maker's, in their inbox.

  **A step is not a task.** It has no owner, no date and nobody assigned — it
  is a line to tick on the way to finishing the task (Task Step). When a task
  has steps, its Progress is the share of them done, which ERPNext's Project
  already reads when a project measures completion by task progress.

  The sub-tasks are on the task's page as a connection (`dashboard`), so its
  + makes one with the parent filled in, which is frappe's own way of doing
  it.
- `public/js/task_list.js` — a due date read as a day, red once passed, and
  a start date read as a day.
- `views.py`, `public/js/task_calendar.js` and `public/js/task_tree.js` —
  All Tasks on frappe's Calendar and Tree, ERPNext's own settings read
  through `events` and `children`, which leave a template's tasks out. A task
  planned by the day is a day on the calendar, since ERPNext keeps a task's
  dates as datetimes at midnight. The tree names a task by its subject and
  says where it stands. Both read as the reader (`get_list`).
- `timer.py` — the timer, as a row on the person's draft timesheet for the
  week; a row with a start and no end is the running one, the same rule as the
  Timesheet form's own timer, so either stops what the other started.
  `public/js/task.js` and `task_timer.js` are its buttons and what they say.
  A pause ends the line and keeps the task in a user default (`PAUSED`), so
  `timers` lists the one running and the ones paused; every change tells the
  person's screens (`one_timers`). The rail's Timers tile is in
  `public/js/desk.js` (`timers`, `timers_open`). It opens the onedesk.timers
  island (`frontend/src/task/Timers.vue`), frappe-ui's Popover anchored to the
  tile, also the `timers` page for a phone. The list in both is
  `TimerList.vue`.

  Time is ERPNext's Timesheet, which payroll, costing and billing already
  read; the timer only saves somebody opening one. **Start** adds a row to the
  person's draft timesheet for the week — made if there is none — with the
  task, its project and a start. **Stop** gives the row its end, and ERPNext
  works out the hours. One timer runs at a time: starting another stops the
  first. The Timesheet form's own timer is public/js/timesheet.js. Every
  stamp is `now_datetime`, the site's clock, for the reason given there. A
  timer stopped within a minute of starting was a slip, and its row is taken
  out rather than left at nought hours to be refused on submit.

  Time is billable on a project whose kind bills hours (Time and Materials, or
  a Retainer) until somebody unticks it, and cost only on any other
  (one_project/hours.py `bills_hours`). The activity is the one the person
  used last, since it is required when the timesheet is submitted and is
  usually the same all week; they change it on the timesheet when it is not.
- `task.py` also has `recurring`, which gives a repeat (frappe's Auto Repeat, switched on for Task in custom/task.json) its
  dates, its status and its people. **A repeating task is frappe's Auto
  Repeat** (Repeat on a task's page). Each repeat is a copy of the task, which
  would keep its old dates, its Completed and its ticked steps; `recurring`
  makes it due on the day it repeats and gives it to the same people.
- `tell.py`, with the types in `notifications/one_task/` — Task Given, Task Done, Task Ready,
  Pending Review, Sent Back, Due Date Changed, Task Reopened, Task Cancelled,
  Comment on Your Task and Today's Tasks. Task Given is frappe's own assignment line said in ours: a
  Notification Log `before_insert` turns frappe's "assigned a new task Task"
  into it, since `assign_to.add` writes that line with no switch to stop it.

  **A task given.** Giving somebody a task is frappe's assignment, and frappe
  writes its own line for it: "Samir assigned a new task Task Write the copy
  to you". It is written from deep inside `assign_to.add`, with no switch to
  turn it off, so rather than send a second one, `given` says frappe's line in
  ours as it is written: the Notification Log becomes a Task Given, with when
  the task is due and its project. frappe's line for an assignment taken away
  is left alone.

  **A task done.** ERPNext closes a task's assignments when it is completed,
  and frappe tells each other assignee their assignment was "removed".
  `given` says that as Task Done instead, and `done` tells whoever gave the
  task, and whoever made it, unless they completed it themselves. Both write
  the bell's title as well, which frappe has already filled with its own
  line before our hook runs.

  **A task changed** (`changed`). These are told to its people:
  - *Task Ready*: the last task it waits on (ERPNext's Depends On) is done,
    told to whoever it's given to, or whoever made it when nobody is. ERPNext
    adds a sub-task to its parent's Depends On, so a parent is ready when its
    sub-tasks are done.
  - *Pending Review*: somebody marks it Pending Review, told to whoever gave
    it and whoever made it. A formal approval is a Workflow (Settings,
    Approvals).
  - *Sent Back*: a review answered no, told to whoever it's given to.
  - *Due Date Changed*: its due date moved, told to whoever it's given to.
  - *Task Reopened*: a completed task opened again, told to whoever held it,
    completed it and made it, since completing it closed their assignments.
  - *Task Cancelled*: told to whoever gave it and made it; ERPNext clears its
    assignments, and frappe's "removed" line is all the assignees get.

  A comment on a task is told to its people as *Comment on Your Task*; one on
  a project goes to the project's manager (one_project, Comment on Project).

  Whoever made the change is never told.

  **The morning.** `today` tells each person what is due that day and what is
  late, from the tasks given to them, as My Tasks groups them (mine.py).
- `heads.py` — a task opens on its form, as every record does. The head
  says when it is due and how late, the checklist, what it still waits on
  (its own sub-tasks left out) and the hours logged, and offers Complete Task.
  The form hides Weight, Color, Issue and the template fields (custom/task.json).
- `view.py` — the task as the reader may see it, for OneAI's `task_facts`:
  what it waits on and what waits on it, its checklist, its sub-tasks, the
  time on it and the one thing worth saying (`headline`, pure).
- `ai.py` — the timers page sentence, `my_tasks`, `plan_task` (a Create card; the
  colleagues it names ride on the hidden `one_for` and are given the task by
  `capture.task_made`), `plan_steps` (an Edit card on the checklist; a
  change to the status, due date or priority is the generic `edit_record`,
  saved as the page saves them, so ERPNext's checks hold),
  `assign_task` (a Setup
  card, `what: assign`; approving runs `assigned` through one_studio/ai_setup.py,
  which checks again that the approver may change the task and that each
  colleague is an enabled workspace user, then calls frappe's
  `assign_to.add` as the approver, as the page's Assign does), `task_facts`
  (a task as its page shows it), and the suggestions. `legal.py` is its line in the AI Addendum. The tasks are read
  as the reader (`mine.tasks`), with the same filters as the boards. A task is only ever suggested; approving the card
  makes it, and gives it to whoever the card names then (capture.py), which
  tells them (tell.py). Steps are suggested the same way, as a change to the
  task's checklist the reader approves.
- `board.py` and `public/js/one_task/task_kanban.js` — **My Tasks** and the **Inbox**
  are two Kanban Boards on Task by status, made once (`settle`) and shaped
  as every task board is (one_project/board.py). The script narrows each to
  its reader (`_assign`, and for the Inbox no project), names it in the
  reader's language, puts an add bar over it and a timer on every task
  card. Everything else is frappe's board. `mine.py` reads the same two for
  OneAI and the reminders, grouped by when each is due (`when` is pure),
  with how many open tasks each waits on (`_waiting`).

  Where a task opens is `place`: its project's page, or for a step of an
  onboarding or a separation (HRMS's checklist project, one_hr/lifecycle.py)
  that onboarding or separation, named by the person. The task's page uses
  the same, in its breadcrumb and its details.

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, See Every Task, is `abilities.py` with its Permission
  Type in `permission_type/`, a OneTask Manager's; `access.py` reads it in
  both `allowed` and `query` (`every`).
- **Setup** needs nothing (`setup.py`), **its tour** is `tour.py` over the
  board's marks, and **OneAI's reach** is `ai.py`'s REACH and NOT_FOR_AI.
- **Its foot and settings** are `public/js/one_task/task_control.js`.
- **My Tasks** sits on OneTask's rail as a board, and Add Task is the
  board's own. The task page keeps the rail too.

## The plan

1. **Capture and inbox.** *Done.* Every desk user keeps tasks, a to-do about
   nothing is a task, and the inbox is the tasks in no project.
2. **My Tasks.** *Done.* What is assigned to me, by due date, ticked off where
   it is listed, and added from the top of the list.
3. **The project board.** *Done.* A board per project by status, sub-tasks as
   a connection, a checklist that is the progress, and projects in OneTask
   rather than a rail entry of their own.
4. **The calendar.** *Done.* A task dragged on the calendar moves, and a
   project has its own calendar of its tasks and the events about it.
5. **Time.** *Done.* A timer on a task and on My Tasks, writing the person's
   timesheet for the week.
6. **The old OneTask.** *Done.* Read and deleted with the old OneProject space.
   Taken: the dependency fix, repeating tasks, a task named after its project,
   and billable time on a customer's project. Not taken, because frappe or
   ERPNext already has it: team-named columns (the statuses), a rank on each
   card (the board keeps its own order), labels (frappe's Tags), an assignee
   column (the list and board show who is on a task), and sprints (not asked
   for, and a project with a date range is most of one).
7. **Projects leave.** *Done.* The board, a project's calendar, task prefixes,
   the plan and the project settings built in stages 3, 4 and 6 are
   OneProject's now (one_project/AGENTS.md, which also lists what OneTask keeps
   doing for projects).
