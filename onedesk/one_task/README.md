# OneTask

Written by hand. What OneTask does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneTask is where all work is kept, and all of it is a **task**: a to-do of your
own, a step in a project, a part of a bigger task, a milestone. There is no
second list somewhere else. A deal's next step, a leave application waiting on
you and a meeting are not tasks — they are the deal's, the application's and
the calendar's — but everything you have to *do* is here.

## Finding your way

**OneTask** in the dock opens it, on **My Tasks**. The rail has:

- **My Tasks** — everything assigned to you and still to do, by when it is
  due.
- **Inbox** — your own tasks that are in no project, still to do. A quick note
  to yourself lands here.
- **Tasks** — every task you may see, in projects and out of them.
- Under **Setup**, **Task Type**.

Projects — their boards, calendars and money — are **OneProject**'s, over the
same tasks.

## My Tasks

Your work, in groups: **Overdue**, **Today**, **Tomorrow**, **Next 7 Days**,
**Later** and **No Due Date**. Within a day the most pressing comes first, and
Urgent and High say so. A task in a project names the project.

**Tick a task to complete it.** It stays on the list, struck through, until you
next open the page, so a tick made by mistake is undone by ticking it again.
Completing a task takes it off everybody's list, not only yours.

**Type a task at the top and press Enter** to add it, with a **Due** date if it
has one. It is yours, in no project, and lands in its group straight away.

A task is due on its **Expected End Date**, or on its **Expected Start Date**
when it has no end.

## Adding a task

**Add Task** on the Inbox asks for the subject, the project if it belongs to
one, and the **Expected End Date**, which is when it is due. That is all a
to-do needs; everything else is on the task's own page.

A task you make with no project and nobody on it is **assigned to you**, so it
is on your calendar and in every list of your work.

**A to-do is a task.** Anything that makes a to-do with nothing it is about —
the To Do form, a reminder to yourself — makes a task, assigned to whoever the
to-do was for.

## On the calendar

Your tasks are on **OneCalendar** under **My Tasks**, on the day each is due.
**Drag one to another day** to move it: its due date goes there, and its start
date moves by as many days, so the task keeps its length.

A project's own calendar is OneProject's.

## Timing a task

**Start Timer** on a task's page, or the ▷ beside it on My Tasks, starts timing
it; **Stop Timer** stops it and says how long went on your timesheet. Only one
timer runs at a time — starting another stops the first — and a task being
timed says since when on My Tasks.

The time goes on **your timesheet for the week**, made for you if you have
none, with the task and its project filled in and the activity you used last.
Change the activity there if it was something else, and submit the timesheet
at the end of the week as usual; the task's **Actual Time** counts it from
then. A timer stopped within a minute of starting adds nothing.

Timing is for people who keep a timesheet; somebody who cannot make one does
not see the timer.

## Sub-tasks and checklists

**Sub-tasks** at the top of a task's page lists the tasks under it, and **+**
adds one. A sub-task is a whole task — its own people, date and board card —
in the same project as the task it is under.

**Checklist** on a task's page is for the steps on the way to finishing it,
which nobody else has to be given. Tick **Done** as you go; the task's
**Progress** follows, and so does the project's when it counts progress.

## Repeating tasks

**Repeat** in a task's menu (the **⋯** at the top) makes it repeat — daily,
weekly, monthly and so on — and a new task is made each time. Each one is due
on the day it repeats, is still to do with its checklist unticked, and is
given to the same people as the task it repeats. Stop it from the same place.

## Who is on a task

**Assign** on a task's page gives it to somebody. They see it, it is on their
calendar on the day it is due, and they are told. A task can be assigned to
more than one person.

- **Completing a task** takes it off everybody's list.
- **Ticking off your assignment** on a task in no project completes the task,
  since you were the one doing it. On a task in a project it only takes it off
  your list; the task is done when it is completed.

## Who sees a task

- **Your own tasks** — ones you made, or that are assigned to you — are yours
  to see and change, and nobody else's unless you assign or share them.
- **A task in a project** is also seen by the people who work in projects.
- **Share** on a task's page lets somebody see one task without giving it to
  them.

A task you were given by somebody else is yours to do, not yours to delete.

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
  (one_project/board.py says why).
- `task.py` — a sub-task's parent becomes a group and lends its project; the
  checklist is the progress; sub-tasks are a connection on the task's page.
- `public/js/task_list.js` — a due date read as a day, red once passed.
- `timer.py` — the timer, as a row on the person's draft timesheet for the
  week; a row with a start and no end is the running one, the same rule as the
  Timesheet form's own timer, so either stops what the other started.
  `public/js/task.js` and `task_timer.js` are its buttons and what they say.
- `task.py` also has `recurring`, which gives a repeat (frappe's Auto Repeat, switched on for Task in custom/task.json) its
  dates, its status and its people.
- `mine.py` and `page/my_tasks` — My Tasks. The server only reads, as the
  reader, and groups (`when` is pure); adding and ticking are `frappe.db.insert`
  and `frappe.db.set_value` from the page, so every rule a task has on its own
  page holds here.

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
