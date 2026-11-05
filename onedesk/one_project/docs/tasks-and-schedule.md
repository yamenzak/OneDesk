# Tasks and Schedule

A project's **Tasks** tab lists its tasks, each with its status, priority,
start and end dates, progress and who it's assigned to. Change a task's
status or priority right in its row. **Search** finds a task, the sort orders
them, and **Add Task** adds one. Click a task to open it. **Board**,
**Calendar** and **Schedule** at the top of the project show its tasks in
columns, on its calendar or on a timeline (see below).

Late due dates are red. Whatever someone else changes shows up without
reloading. Planned hours and a milestone's bill share are never below 0,
however they're written. **Planned** leaves out cancelled tasks.

## A Project's Board

**Board** shows a project's tasks in four columns: **Open**, **Working**,
**Pending Review** and **Completed**. Each card shows its priority, due date
and who is on it. Drag a card to move the task along. **Add Task** at the top
of a column adds one there. The board is created the first time anyone opens
it, and everyone shares it.

**Overdue isn't a column.** An overdue task stays where it is and its date
turns red, on the board and in every list.

## A Project's Calendar

**Calendar** is the project's own calendar: every open task in it, whoever is
on it, and every event about the project. Drag a task to move it. **Add
Event** creates an event about the project, which shows on the calendar of
everyone who can open the project.

## Task Names

A task is named like **TASK-2026-00042** unless its project has a **Task
Prefix**. With the prefix **WEB**, its new tasks are named **WEB-1**,
**WEB-2** and so on. Existing tasks keep their names. A prefix is 2 to 10
letters and digits, starting with a letter, and no two projects share one.

## A Project's Schedule

**Schedule** shows a project's tasks on a timeline: this project's and every
sub-project's, except cancelled ones. Each task is a bar from its start to its
due date. A task with only a due date is one day, a **milestone** is marked
as one, and an arrow runs from a task to each task that depends on it. It
opens on today. **Today** goes back to it, and **Day**, **Week**, **Month**
and the rest at the bottom change the scale.

**Drag a bar to move a task**, or drag its end to make it longer.
Double-click a bar to open the task.

## Milestones

A milestone is a task marked **Milestone**, on the project or on any
sub-project. **Add Milestone** under **Milestones** on the Overview asks for
its name, which project it's on, and its due date. To make an existing task
a milestone, open it and turn on **Milestone**.

**Milestones** on the Overview shows the last two done and the ones to come.
Each says when it's due and how far off it is, and turns red once it's late.
One on a sub-project says which.

On a project with sub-projects, **Milestones** is a row per part of the job
on one dated line: **Main** first, then each sub-project with what's under
it, and a line for today across them all. Done ones are filled, a late one is
red, and each row's next one is named with its date. Point at the others to
see theirs. Each row counts how many are done. Click a sub-project's name to
open it. On a phone each part
is a line with its next milestone.

**Bill on Completion** is optional. Give a milestone a share of the contract
and the project is billed by its milestones: **Work and Billing** shows
**Billable on Milestones**, the shares of the milestones done, and **Not
Invoiced Yet** is measured against that instead of the work done. When such
a milestone is done, the project's manager is told, and **Bill Progress**
starts from that share. A project whose milestones have no share is billed
by the work done, as before. A share is between 0 and 100%, and a project's
milestones together bill at most all of its contract, however they're added.

Anyone who can add tasks can add a milestone. Its share is on the task, so
whoever can change the task can change it. A cancelled project takes no new
tasks or sub-projects until it's opened again.

## When a Task Is Late

A task can depend on others (**Dependencies** on its page), in its own
project or in another under the same parent. When a task's due date moves
later, the tasks that depend on it and are still **Open** move later by the
same amount. The handrails wait for the frames, even though each is its own
sub-project.
