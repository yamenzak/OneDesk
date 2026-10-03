# OneTask

OneTask is where all your work is kept. Every piece of work is a **task**: a
personal to-do, a project step, a sub-task or a milestone.

A deal's next step, a leave application waiting for you and a meeting aren't
tasks. They belong to the deal, the application and the calendar. Everything
else you have to do is here.

## Finding your way

**OneTask** in the dock opens **My Tasks**. The left column has:

- **Add Task** at the top, to create a task.
- **My Tasks**: everything assigned to you that's still open, by due date.
  The red number is how many are overdue, the other how many there are.
- **Inbox**: your own open tasks with no project. Quick notes to yourself
  go here.
- **All Tasks** at the bottom: every task you can see, as a list.
- **Setup** (Task Type), for those with access.

The page updates on its own. A task assigned to you, or completed elsewhere,
appears without reloading.

Projects, with their boards, calendars and budgets, are in **OneProject** and
use the same tasks. A project task assigned to you shows on My Tasks like any
other, and its project name opens the project.

## My Tasks

Tasks are grouped into **Overdue**, **Today**, **Tomorrow**, **Next 7 Days**,
**Later** and **No Due Date**. Within a day, the most pressing come first,
with Urgent and High marked.

- A project task shows its project.
- A task with no project that's about a record, such as one Intake made for
  a supplier, shows that record and opens it.
- An overdue task shows how long ago it was due.

**To complete a task**, tick it. It stays on the list, struck through, until
you reload, so you can untick it if it was a mistake. Completing a task
removes it from everyone's list.

**To add a task**, type it at the top and press Enter. Add a **Due** date if
it has one. It's assigned to you, has no project, and appears in its group
right away.

A task is due on its **Expected End Date**, or its **Expected Start Date** if
it has no end date.

## Adding a task

**Add Task** asks for the subject, the project if there is one, and the
**Expected End Date** (the due date). Everything else is on the task's page.

A task you create with no project and no one assigned is **assigned to you**,
so it shows on your calendar and in your lists.

**To-dos are tasks.** Anything that creates a to-do without a record, such as
the To Do form or a reminder to yourself, creates a task assigned to that
person instead.

## A task's page

**Details** has the task and its project, followed by **Timeline**, open,
with the start and due dates, expected time, progress and weight. Then come
**Is Template**, the issue it came from, and its color. The description and
checklist are under **Details**.

## On the calendar

Your tasks show on **OneCalendar** under **My Tasks**, on their due date.
**Drag a task to another day** to move it. The due date changes, and the
start date moves by the same number of days, so the task keeps its length.

A project's calendar is in OneProject.

## Timing a task

**Start Timer** on a task's page, or ▷ next to it on My Tasks, starts timing
it. **Stop Timer** stops it and shows how much time was added to your
timesheet.

- Only one timer runs at a time. Starting another stops the first.
- My Tasks shows when the running timer started.
- A timer stopped within a minute adds nothing.

The time goes on **your timesheet for the week**, created if you don't have
one, with the task, its project and your last activity type. Change the
activity there if needed, and submit the timesheet at the end of the week as
usual. The task's **Actual Time** counts it once submitted.

Only people who can create timesheets see the timer.

## Sub-tasks and checklists

**Sub-tasks** at the top of a task's page lists the tasks under it. **+**
adds one. A sub-task is a full task, with its own people, dates and board
card, in the same project as its parent.

**Checklist** is for steps toward finishing a task that don't need to be
assigned to anyone. Tick **Done** as you go. The task's **Progress** updates,
and so does the project's if it tracks progress.

## Repeating tasks

**Repeat**, in the task's **⋯** menu, sets a task to repeat daily, weekly,
monthly and so on. Each time, a new task is created:

- due on the day it repeats
- open, with its checklist unticked
- assigned to the same people

Stop repeating from the same menu.

## Who is on a task

**Assign** on a task's page assigns it to someone. They can see it, it shows
on their calendar on its due date, and they're notified. A task can be
assigned to several people.

- **Completing a task** removes it from everyone's list.
- **Closing your assignment** on a task with no project completes the task.
  On a project task, it only removes the task from your list. The task stays
  open until it's completed.

## Notifications

- **Task Given**: someone assigns you a task. Shows who, the task, its due
  date and project. Also sent by email if you turned that on.
- **Task Done**: someone completes a task you assigned to them, or one you
  created.
- **Today's Tasks**: each morning, what's due today and what's overdue, if
  anything.

Each can be turned off or changed under **Settings › Notifications**.

## Asking OneAI

On My Tasks, OneAI offers **What should I do first?** and **Add a task…**. It
reads your tasks as you see them. A suggested task comes on a card, with a
due date, project, checklist and, if you asked, a colleague to assign it to.
Nothing is added until you approve the card, and the colleague is notified
then.

On a task's page, **Break this into steps** suggests checklist steps, added
after any existing ones when you approve.

## Who sees a task

- **Your own tasks**, ones you created or are assigned to, are yours to see
  and change. No one else sees them unless you assign or share them.
- **A project task** is also seen by anyone who can see the project. That's
  its members, or everyone who works in projects if it has no members (see
  OneProject).
- **A template task**, marked **Is Template** and used by project templates,
  is seen by everyone who works in projects. It isn't assigned to anyone and
  doesn't show on My Tasks or the calendar.
- **Share** on a task's page lets someone see a task without assigning it to
  them.

You can work on a task someone else assigned to you, but you can't delete it.

## Under the hood

For the people who build OneTask. OneAI does not read past this heading.

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
- `capture.py` — a to-do about nothing becomes a task; a task of nobody's is
  its maker's; the last assignment ticked off on a task in no project
  completes it. ERPNext already closes the assignments when a task completes.
- `calendar.py` — **My Tasks** and **Assigned to Me** on OneCalendar (the
  second leaves out assignments on tasks, which are already on the first),
  `due` for any list of tasks (OneProject's calendar reads it), and `move`: a
  task dragged shifts both its dates by the same days (`shifted` is pure).
- `custom/task.json` — the due date is asked for when a task is added, the
  Checklist (Task Step) is added, and Overdue is taken off the statuses
  (one_project/board.py says why). The page's order puts Timeline, open,
  ahead of Is Template, Issue and Color; Company is hidden; the list shows
  Subject, Status, Project, Priority and the due date (`task_list.js` drops
  frappe's ID column).
- `task.py` — a sub-task's parent becomes a group and lends its project; the
  checklist is the progress; sub-tasks are a connection on the task's page.
- `public/js/task_list.js` — a due date read as a day, red once passed.
- `timer.py` — the timer, as a row on the person's draft timesheet for the
  week; a row with a start and no end is the running one, the same rule as the
  Timesheet form's own timer, so either stops what the other started.
  `public/js/task.js` and `task_timer.js` are its buttons and what they say.
- `task.py` also has `recurring`, which gives a repeat (frappe's Auto Repeat, switched on for Task in custom/task.json) its
  dates, its status and its people.
- `tell.py` and `notifications.py` — Task Given, Task Done and Today's
  Tasks. Task Given is frappe's own assignment line said in ours: a
  Notification Log `before_insert` turns frappe's "assigned a new task Task"
  into it, since `assign_to.add` writes that line with no switch to stop it.
- `ai.py` — the page sentence, `my_tasks`, `plan_task` (a Create card; the
  colleagues it names ride on the hidden `one_for` and are given the task by
  `capture.task_made`), `plan_steps` (an Edit card on the checklist), and the
  suggestions. `legal.py` is its line in the AI Addendum.
- `mine.py` and `page/my_tasks` — OneTask's page: the column, the two views
  (`?section=inbox`), their counts, and `frappe.realtime` on Task and ToDo.
  The server only reads, as the reader, and groups (`when` is pure); adding
  and ticking are `frappe.db.insert` and `frappe.db.set_value` from the page,
  so every rule a task has on its own page holds here.

### The plan

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
   OneProject's now (one_project/README.md, which also lists what OneTask keeps
   doing for projects).
