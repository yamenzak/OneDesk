# Deliverables

A study and a plan, written 2026-10-09. Nothing here is built yet.

## What a deliverable is

A step is something you do. A deliverable is something you hand over, to
somebody who accepts it or sends it back.

- On the villa, **Shop drawings** delivers a drawing set and the structural
  calculations to the consultant. The consultant returns Rev A with comments
  and approves Rev B. The glass can't be ordered before that.
- On a website, **Design** delivers the home page and the inner pages, and
  the customer signs them off.
- At handover, the fit-out delivers the O&M manual, the warranties and the
  test certificates.

So a deliverable has things a checklist step doesn't:

- who receives it, and who decides on it;
- a state that moves: being worked on, sent, approved, returned;
- revisions, each with its own files;
- a history of who sent what, when, and what came back;
- a register across the project, the list a project manager and a
  consultant go through together.

## What we already have

| What | Where | What it gives deliverables |
|---|---|---|
| The checklist | `Task Step` on Task (`one_steps`), ours | steps, ticked. A step can tick itself from a record (`done_when`, `one_intake/steps.py`) |
| Template tasks | ERPNext's Task with `is_template`, linked from Project Template | a template's tasks are real tasks, copied when a project is made. Ours copies their steps too (`one_project/templates.py` `task_made`) |
| The library | `one_project/library/*.json` | twelve presets, each task with its day, days and hours |
| Task Type | ERPNext | a name, a weight and a description. Nothing hangs off it yet |
| Contract and Contract Template | ERPNext | **the same shape we need**. A Contract Template lists requirements (`Contract Template Fulfilment Terms`). They are copied into the contract's `Contract Fulfilment Checklist` (requirement, fulfilled, notes), which sets Unfulfilled, Partially Fulfilled, Fulfilled or Lapsed |
| Pending Review | ERPNext's task status, our notification | a whole task waiting on a review, not one thing it hands over |
| Files on a record | OneCloud | a task's files, in its folder inside the project's |
| Versions | OneCloud (`Cloud File Version`) | each file's past |
| File requests | OneCloud | somebody outside uploads named files without an account, with a due date and reminders. A file can fill a record's field |
| Links outside | OneCloud | a file or folder shared by link, with a code for invited people |
| The portal | ours, over ERPNext's project page | a customer sees their project, its tasks, and its files where the Project User row lets them |
| Approvals | frappe's Workflow, in Settings | a workspace's own states and who may move them, on any record type |
| Web Form | frappe | a form on the website for one record type, for people outside the desk |

Nothing in frappe, ERPNext or HRMS is called a deliverable.

## The ways it could be built

### Web Forms

A Web Form is a door, not a place to keep anything. It lets somebody outside
the desk fill in one record type on the website. It would only help if a
supplier or customer had to send us a deliverable. OneCloud's file requests
already do that, in our look, with reminders and without an account. A
customer deciding on a deliverable belongs on our portal's project page,
like everything else they see there. Web Forms draw frappe's website look,
which our portal replaced.

**Not this.** Keep it in mind only if a workspace wants a public form of its
own, which OneStudio already allows.

### A few custom fields on Task

A **Deliverable** field and an **Approved** box on Task. A task often hands
over several things, each with its own state, so this breaks on the first
real case.

**Not this.**

### A table on Task, like the checklist

A child table, `Task Deliverable`, with the deliverable, its state, the
revision and a file. This is the checklist's pattern and ERPNext's contract
pattern. It is the least to build, and template tasks would copy it as they
copy steps.

A row of a table has no history, comments, assignment, sharing or
permissions of its own. It can't be listed across projects as a register,
sent to a customer on its own, or approved by somebody who may not change
the task. Every decision on a drawing would be a save of the whole task.

**Good for a first week. Wrong for what deliverables are for.**

### A record of its own, linked to the task

A `Deliverable` record type, linked to its task and project. It gets what
any record gets from frappe: a timeline with comments, a version history,
assignment, sharing, its own permissions, Files, the List, Report and Kanban
views, Data Import, Workflow if a workspace wants one, and realtime.

It costs more surface, a tier, a place on the task's page, notifications,
and every point of the passover. That cost is what makes it work like the
rest of One.

**This one.**

## The plan

### The records

**Deliverable** (OneTask's module, as a task's part).

- **Deliverable**: its name, such as *Shop drawings, ground floor*.
- **Task**, and **Project** from the task.
- **Type**: Document, Drawing, Sample, Certificate, Approval, Other. A
  Select, so a workspace can add its own through Customize.
- **Description**.
- **Due**, the task's due date unless set.
- **For**: who decides on it. The customer (a contact on the project), a
  consultant (a project contact), or somebody in the team.
- **Required**: whether the task waits for it.
- **Status**: Not Started, In Progress, Sent, Approved, Approved with
  Comments, Returned, Cancelled.
- **Revision**: 0 for the first, then 1, 2 and so on. Drawn as Rev A, B, C
  unless the workspace numbers them.
- **Sent On**, **Decided On**, **Decided By**, and a **Comment** with the
  decision.
- **Shared**: whether the customer sees it on the portal.
- **Is Template**, as a template task has.

Its files are in its own folder inside the task's, so OneCloud's versions
keep each revision's files.

**Deliverable Template**, a named pack, the way ERPNext's Contract Template
holds requirements. *Façade submittals* holds shop drawings, structural
calculations, samples and test certificates. *Website launch* holds the
sitemap, the designs, the staging site and the launch checklist. Each row
has the deliverable, its type, whether it is required, and who decides
(customer, consultant or team).

### How they reach a task

1. **By hand**, on the task's page: **Add Deliverable**, or **Add from
   Template** to bring in a pack.
2. **From a project template.** A template task holds its deliverables as
   template deliverables (`is_template`), the way ERPNext keeps template
   tasks as tasks. When a project is made, they are copied with the task,
   where `templates.task_made` already copies the steps. The template page
   shows them under each task. The library's files gain a `deliverables`
   list per task, with Aluminium & Glazing first.
3. **By task type.** A Task Type can name a pack (`one_deliverable_template`,
   a custom field on ERPNext's Task Type). A task of that type gets the pack
   when it is made.
4. **From OneAI**, as a card. It suggests the deliverables for a task, or
   drafts a pack from a description.

### On the task's page

A **Deliverables** section beside the checklist. Each row shows its name,
type, revision, status as a badge, and who decides. **Send** and **Revise**
are on the row, and the row opens the deliverable's own page. The head says
*2 of 3 approved* when a task has any.

A deliverable's page uses the task page's frame: its head, files by
revision, the history of what was sent and what came back, and frappe's
sidebar. It is declared in `one/tiers.py` like the task's page.

### The register

**Deliverables** in OneProject's rail and on a project's page, as a tab
beside Tasks. It lists every deliverable of the project and its
sub-projects, with what is waiting on whom, what is late, and what was
returned. It is frappe's List, Report and Kanban by status, declared in the
tier registry.

### Rules on the server

On the deliverable's own hooks, so a bulk edit, a report cell and an import
meet them:

- **Approved** or **Returned** needs a decision, and stamps who decided and
  when;
- **Sent** needs at least one file, unless its type is Sample or Approval;
- **Revise** moves a returned deliverable to In Progress and raises the
  revision by one. A revision is never lowered by hand;
- a cancelled task cancels its deliverables, and a deliverable can't be
  added to a template's task unless it is a template deliverable.

And on the task: a task can't be **Completed** while a required deliverable
isn't approved. That is a rule on Task's own validate, beside ERPNext's own
check on what the task depends on.

### People outside

- **The customer, on the portal.** The project's page lists the deliverables
  shared with them. Each opens with its files, and **Approve** and **Return**
  with a comment. Our portal page, in our look, not a Web Form.
- **A consultant by mail.** **Send** mails the files to the person who
  decides, with a transmittal (below). Their reply arrives in OneMail. Intake
  reads it, such as *approved as noted* with a marked-up PDF, and suggests
  the decision as an action, with the marked-up file kept as the
  deliverable's.
- **A supplier who makes it.** **Ask for Files** on a deliverable is
  OneCloud's file request, made for it. What arrives is attached, and the
  deliverable moves to In Progress for us to check and send.

### Printed

A **Transmittal**, the cover sheet sent with deliverables. It names the
project, each deliverable with its revision and type, why it is sent (for
approval, for information, for construction), and to whom. It is a builder
format from the print blocks, shipped like the others, since it leaves the
company.

### Notifications

One file each in `onedesk/notifications/one_task/`:

- **Deliverable Sent**, to whoever decides, when they are in the team;
- **Deliverable Approved** and **Deliverable Returned**, to the task's
  people;
- **Deliverable Due**, the day before, to the task's people, when it is not
  sent.

### OneAI

- `task_facts` reads the task's deliverables, and a new `deliverable_facts`
  reads one with its revisions.
- `plan_deliverables` suggests a task's deliverables as a card.
- `draft_deliverable_template` drafts a pack as a card, as
  `draft_template` drafts a project template.
- The AI Addendum gains a line, at a new revision.

### Permissions

A deliverable is read and changed by whoever may read and change its task
(`one_task/access.py`), through a permission hook on Deliverable, so it
follows the project's members. A portal user sees only the deliverables
marked **Shared** on their own projects, and may only approve or return
them.

### The demo

- The villa's **Shop drawings and structural calculations** has three
  deliverables. The drawing set went at Rev A, came back with the
  consultant's comments, went again at Rev B, and was approved. The
  calculations were approved first time. The samples are still with the
  consultant.
- The villa's handover task has the O&M manual, the warranties and the test
  certificates from the *Handover documents* pack, with the warranties late.
- The showroom website's design deliverables wait on the customer, shared
  on the portal.
- The consultant's *approved as noted* mail is an Intake sample.

## Stages

| Stage | What |
|---|---|
| D1 | Deliverable and its rules, the task page's section, permissions, demo on the villa |
| D2 | A deliverable's page, revisions and files, notifications |
| D3 | Deliverable Template, Add from Template, Task Type's pack |
| D4 | Template tasks carry deliverables, the template page, the library's files |
| D5 | The register in OneProject, and the project page's tab |
| D6 | Sending: the Transmittal print, Send by mail, Ask for Files |
| D7 | The portal: shared deliverables, Approve and Return |
| D8 | Intake reads a decision by mail, and OneAI |
| D9 | Closed against the standard |

Each stage is walked against the seventeen points, as OneTask was.

## Decisions for you

1. **Who decides.** The customer on the portal, a consultant by mail,
   somebody in the team, or any of the three per deliverable. The plan
   assumes any of the three.
2. **Does a task wait for its deliverables?** The plan says a task with a
   required deliverable not yet approved can't be completed.
3. **Templates.** All three ways (packs, template tasks and task types), or
   template tasks first and packs later.
4. **Revisions.** Rev A, B, C, or 0, 1, 2. Construction uses letters,
   software uses numbers. The plan draws letters and lets a workspace
   choose.
5. **The word.** *Deliverable* everywhere, or *Submittal* for construction
   workspaces. The plan uses Deliverable, as the plain word.
