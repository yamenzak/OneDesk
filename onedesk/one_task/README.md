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

**OneTask** in the dock opens it. The rail has:

- **Inbox** — your own tasks that are in no project, still to do. A quick note
  to yourself lands here.
- **Tasks** — every task you may see, in projects and out of them.
- **Projects** — for the people who work in projects.
- Under **Setup**, **Task Type**.

## Adding a task

**Add Task** on the Inbox asks for the subject, the project if it belongs to
one, and the **Expected End Date**, which is when it is due. That is all a
to-do needs; everything else is on the task's own page.

A task you make with no project and nobody on it is **assigned to you**, so it
is on your calendar and in every list of your work.

**A to-do is a task.** Anything that makes a to-do with nothing it is about —
the To Do form, a reminder to yourself — makes a task, assigned to whoever the
to-do was for.

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
- `calendar.py` — **My Tasks** and **Assigned to Me** on OneCalendar. The
  second leaves out assignments on tasks, which are already on the first.
- `custom/task.json` — the due date is asked for when a task is added.

### The plan

1. **Capture and inbox.** *Done.* Every desk user keeps tasks, a to-do about
   nothing is a task, and the inbox is the tasks in no project.
2. **My Tasks.** What is assigned to me, by due date, ticked off where it is
   listed.
3. **The project board.** A board per project by status, with sub-tasks and a
   checklist.
4. **The calendar.** Moving a task's due date by dragging it, and a
   project's own calendar.
5. **Time.** A timer on a task that writes a Timesheet row.
6. **The old OneTask.** Read OneApp's, take what it had that this does not —
   states, rank, labels, the checklist, and its fix for ERPNext never
   rescheduling dependent tasks — and delete it.
