# The standard

OneProject is the first module finished against every point of the passover,
and it was closed on 2026-10-09. Your word was "OneProject will be the
standard". This file says what finished means, taken from OneProject, so
every module after it is finished the same way and checked against the same
things.

`docs/PASSOVER.md` has the seventeen points and the rules on top of them.
This file says what meeting each one looks like in a real module, where
OneProject keeps it, what checks it, and what went wrong on the way. A module
is finished when it meets all of it, and the gates at the end pass.

## How a module is finished

1. **The baseline.** Run the gates before touching anything, and write down
   the counts. They are what "nothing broke" is measured against.
2. **Screen by screen.** Split the module into its screens the way its people
   use it. For OneProject that was six:
   - the list and every view of it, and New Project;
   - a project's head and Overview;
   - Tasks, Time and Money;
   - Invoices, Suppliers, Team, Files and Activity;
   - Workload, Timesheet and Templates;
   - across modules, from the other side of each hand-off.
3. **Every point, every screen.** Look at the screen in the browser as the
   people who use it (OneProject used Samir, who runs projects, and Huda, who
   keeps the books), on a desktop and a phone, and read the code behind it.
   Write the findings under the points in `docs/PASSOVER.md`. Each screen ends
   with a table of all seventeen points, plus Everything follows frappe and
   What ERPNext already does, saying what was looked at, even where nothing
   was found. A point left out of the table is a point not checked.
4. **Fix, then look again.** Fix every finding, see it in the browser, run the
   gates, commit and push, and show a screenshot.
5. **Revisit.** OneProject's first three screens were walked before the rule
   that every point is written down. They were walked again against the
   points they had skipped, and that found as much as the first walk. A
   module is not finished until every screen has every point in its table.
6. **Close it.** Mark each screen done in `docs/PASSOVER.md`, then the module
   closed, with what stays open written down.

## What finished looks like

### Works

**1 Demo coverage.** The demo company holds a real case of every kind the
module has. OneProject has a fixed price villa with sub-projects and a
subcontract, a curtain wall tower counted by attendance on site, a time and
materials showroom billed in euros, two retainers, an internal project, a
completed one and a cancelled one. Each record is made by the person whose
work it is, on the day it happened (`one_demo/history.py` moves it back).

- Every whitelisted method and every OneAI tool is reached by a demo check
  (`tests/guards/test_coverage.py`). OneProject's checks run as the people
  who would do the work, with `bench … one_demo.check.run --kwargs "{'only':
  'oneproject_'}"`.
- Each screen's walk adds a check that says what the walk found, such as
  `oneproject_its_tasks_time_and_money_keep_their_rules`.
- **Watch for** demo data that lies. On OneProject every open task was
  overdue, every invoice was due the day the demo was built, retention was
  paid in full, the workshop's time sat on the handover tasks, and a Berlin
  customer lived in Business Bay. The product was right each time and the
  demo made it look wrong. Fix the builder, then repair the site the same
  way, so a rebuilt demo and this one agree.

**2 Rules on the server.** Every rule is on the record's own hooks in
`hooks.py`, so the page, a bulk edit, a report cell and Data Import all meet
it. OneProject keeps these there:

- a project isn't closed with open work, and an internal one bills nobody
  (`status.py`, `kinds.py`);
- a budget is its cost types, and a cost centre's budget is the books' own
  (`budget.py`);
- milestones bill between 0 and 100% of the contract, and together at most
  all of it (`milestones.py`);
- a cancelled project takes no new work, and somebody who can't sign in
  joins no project (`members.py`);
- time on a project billed by the hour is billable, a timesheet row's task is
  on its project, and a retainer's hours are billed only with their month
  (`hours.py`, `retainer.py`);
- a new quotation, order or invoice takes the customer's one open project
  (`chain.py`);
- hours, budgets and bill shares are never below 0 (`non_negative` on the
  fields).

Checked by `tests/guards/test_rules.py` and by the demo, each rule changed
every way. **Watch for** a rule that lives in an endpoint behind a button.
The button offers and orchestrates. The record decides.

**3 Hand-offs.** The README's **Connections** says where the module's data
comes from and where it goes, one line per module. Each hand-off runs end to
end on the demo (`one_demo/check.py` HANDOFFS, `tests/guards/test_handoffs.py`).
The document a project hands on says the project at the top, by name,
opening its page (`one_project/heads.py`). The last screen of the walk is from the
other side of each hand-off, as the person who works there.

### Stays desk

**4 Tier declared.** `onedesk/one/tiers.py` says how each record is shown and
why, and every collection view frappe has, as frappe's own or ours.
OneProject has two pages of their own (Project and Project Template), heads
on the documents it hands on, Project's List, Report, Kanban, Calendar,
Gantt, Tree, Image and Dashboard declared, and Task's List, Gantt and Kanban.
No view frappe offers is taken away.

**5 Our look.** The project page has its own look, built from frappe-ui. It
is checked at 1440 wide and on a phone. **Watch for** text cut off in a
column, a figure only a bar says, a large empty state where every other one
is a line, and a list that only fits on a desktop.

**6 Nothing lost.** A page of its own keeps everything frappe's form gives.
Its sidebar is frappe's own, its menu is frappe's under the page's, it saves
against the `modified` it loaded, and it hears changes made elsewhere
(`tests/guards/test_frame.py`). Every field on the form can be changed on
the page, in place or in Edit Details (`test_a_page_edits_every_field_of_its_record`).

**Changing a field where it is shown.** A field on a page is changed where it
is shown, not in a dialog, and it is the record's own form field (set by the
user on 2026-10-12, first on the item page).
- The page holds the record's real desk form, out of sight
  (`onedesk.record.form`, the kit's `useForm`), as frappe's own Data Import
  dialog holds one. Its client scripts, queries, `depends_on` and
  `set_df_property` all run.
- Each field shows its value as the form formats it, with a pencil (a
  chevron for a Link or Select). The pencil floats that form's own control
  over the place (`onedesk.record.lend`, the kit's `FieldEdit`). It floats
  rather than moves because a page's island has its own styles, which
  desk's don't reach.
- A change saves the form as desk saves it, against the `modified` it
  loaded. Enter or leaving the field saves, Escape reloads it unchanged.
  Long text gets Save and Cancel. A Check is frappe-ui's Switch, which sets
  the form's value and saves.
- A field the form hides is not shown, and one it locks has no pencil. A
  script that locks or hides a field after the refresh is heard too.
- A field of a table row is changed the same way, as the form's grid makes
  its control (`onedesk.record.lend_row`, `FieldEdit` with `table` and
  `row`). A new row is added as the grid adds one, and its fields go in
  together with Save and Cancel (an item's reorder levels).
- Each label sits on the left and its value on the right (`Facts`).
- Something on or off is a Switch, never a checkbox, on a page as in a
  filter (set by the user on 2026-10-12). A checkbox is only a step ticked
  off a checklist or a task done (`test_a_setting_is_a_switch`).

OneProject and OneTask follow this when they are next passed.

**The head and the breadcrumb.** Set by the user on 2026-10-13, for every
page.
- Every crumb with somewhere to go is a switcher with a search box, as a
  link field searches (`public/js/crumb_switch.js`). The place's crumb lists
  the app's places. A record's crumb lists records of its kind, its own
  suggestions first (a project's open projects), and finds any by typing.
  **All …** stays at the foot. A page never draws a menu of its own on a
  crumb; it gives the trail a `menu` and the switcher draws it.
- On a phone the head is two bars, each its own height with a line under it
  (`public/js/phone_head.js`). The first is the panel's button, the place and
  the record, and search. The second has what is shown at its start (the
  record's status, the view switch, a scope such as a project's All Work)
  and the page's buttons at its end. A name is never cut to make room for a
  button.
- A page that gathers several kinds of record keeps frappe's view switch,
  leading to their List and Report views (`public/js/page_views.js`).

**7 Extensible.** Every view of a page is a place where OneStudio's
extensions go, told what the view shows (`one_studio/places.py`, mapped to
its source in `tests/guards/test_frame.py`). OneProject has one for the page
and one for each tab (Overview, Tasks, Time, Money, Invoices, Suppliers,
Team, Files, Activity), and one each for the Projects list, a template and
Workload. A place's notes and buttons are drawn as frappe-ui's Alert and
Button (`PlaceSpot`).

**8 Built from frappe.** Every part comes from frappe-ui first, then the
desk's own parts, then frappe's primitives. Every value goes through
`frappe.format`. **Watch for** a number rounded by hand, a date written by
hand, or an amount without its currency.

**9 Overrides recorded.** Whatever of frappe's, ERPNext's or HRMS's the module
changes is a row in `scripts/overrides.py`, and `python3 scripts/overrides.py
--check` passes. OneProject has 45 rows.

### Speaks

**10 Notifications.** Every event someone should hear about is one file in
`onedesk/notifications/<module>/`, rendered by the hub, in the reader's
language. OneProject has sixteen, from Added to Project to Bill Due, each
listed under **Being told** in the README with who gets it. **Watch for**
amounts in the site's currency instead of the company's, a notice sent to
whoever did it, and a notice told during an install, a migrate or an import.

**11 Printed.** Every record that leaves the company has a print format we
ship, built from the print blocks (`one/print_blocks.py`,
`templates/one_print/`) and checked by `tests/guards/test_print.py`. For
OneProject that is One Project Status, One Timesheet, OneCRM's One Contract,
and the hours a time and materials invoice bills on One Sales Invoice. A print
format's `modified` moves with every change to it, or a migrate leaves the
site's copy as it was.

**12 Plain words.** Every label is frappe's word where frappe has one
(Assigned To, Parent Task, Depends On), and the rest follows
`docs/WORDING.md` (`tests/guards/test_wording.py`). Every string is in Arabic
and German before it is committed (`tests/guards/test_translations.py`).

### Knows

**13 Documented, and OneAI knows and does.** The README is the manual. Each
screen has its section above `## Under the hood`, written for the people who
use it, and the file map under the hood says what each file does. OneAI
reads a project as its reader sees it on the page, and does what the page
does as a card the reader approves: a project, its status, a milestone,
time, a budget, a member, a contact, a reminder, a template
(`one_project/ai.py`, the `projects` group in `one_ai/groups.py`). Approving
a card runs the page's own code (`one/ai_setup.py`). Nothing is changed
until it is approved.

**14 Intake.** Every mail or file that should make or change the module's
records has a sample in `tests/samples/intake/<module>/`, and the demo has
Intake read it. OneProject's is a scaffolding bill that names the villa.

### Rules

**15 Permissions.** Each screen is walked as each person who uses it, and
the server holds the line, not the screen. On OneProject a project is its
members', the books read every project, totals show to every reader and
documents open only for those who may read them (`members.py`,
`money._figure`).

**16 Legal.** Whatever the module does that the agreements must say is a
clause in its `legal.py`. OneProject has six, and each changes the AI
Addendum or the Privacy Policy by a new revision when it says something new
(`tests/guards/test_legal.py`). Everybody on the demo agrees again.

**17 Clean code.** One layout per module, a file per concern, and lint clean
(`ruff check onedesk/one_project onedesk/one_demo`). A helper said once
(`money.currency` for the company's currency). A comment only where the code
can't say why.

### On top of the points

**Everything follows frappe.** Fields are frappe's controls, a record being
edited acts as a desk form, and every screen updates through
`frappe.realtime` when what's under it changes. OneProject's tabs each
follow the records they show.

**What ERPNext already does.** Every screen checks currency (the party's on
documents, `base_` amounts in figures), the company, drafts and cancelled
and amended documents, ERPNext's own statuses, its mappers, payment terms,
precision, dates, record access and units. On OneProject this found euros
read as dirhams, a draft timesheet counted as cost, cancelled tasks counted
as planned hours, a retention date read as a due date, and a subcontract
booked to the wrong cost type. **Watch for** ERPNext's own checks on save
that a fix written straight to the database skips, such as a task's dates
inside its parent's.

## The gates

Each must pass before a push.

```
python3 -m pytest -q tests                  # fast tests and every guard
sh check.sh                                 # the demo suite, every check
python3 scripts/overrides.py --check
python3 scripts/docs.py --check
ruff check onedesk/<module> onedesk/one_demo
```

When OneProject closed these were 1891 fast tests and 103 of 103 demo checks.
When OneTask closed they were 1894 and 108 of 108.

## What stays open on OneProject

Intake into a project, the cents on a time and materials invoice and the
cost of a day on site were open here and are done (PASSOVER, "OneProject's
gaps").

- **Manufacturing.** No module offers bills of materials or work orders.
  Whether OneInventory takes them on is a product decision.

## OneTask, closed against it

OneTask was the second module closed against the standard, on 2026-10-09,
in five steps: a task's page, My Tasks and the Inbox, All Tasks and its
views, across modules, and the closing pass. It added these to watch for:

- **A rule on the hooks that the guard doesn't know.** A task's progress was
  its checklist on `before_validate`, but nothing changed it every way until
  it was registered in `tests/guards/test_rules.py`.
- **OneAI that reads but doesn't do.** The page completes a task and moves
  its due date. OneAI does the same as a card (`plan_change`).
- **A kind the demo only makes in a check.** A repeating task was made and
  taken away in a check, so no screen showed one. The demo keeps one.
- **frappe's own bugs in the record frame.** A record's page carries
  frappe's sidebar, bugs included, such as "Repeats Weekly" without its
  words. Fix them for the form too, and record the override.

What stays open on OneTask is under its step 5 in `docs/PASSOVER.md`.

## The next module

Each finished module is walked again against these points, one screen at a
time, in the order `docs/PASSOVER.md` keeps under Up next. A module is closed
the way OneProject was, with a row in its table saying "closed" and its open
items written down.
