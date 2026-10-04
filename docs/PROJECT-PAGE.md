# The project page

ERPNext's Project form is a long form with tabs of fields. A project is
something people work in every day, so OneProject gets a page of its own, as
OneMail and OneCloud have: its own look, drawn with frappe-ui's parts, over
the same Project record and everything built in docs/PROJECT.md.

## A project has a kind

What a project needs to show depends on how it's paid for. The kind is chosen
when the project is made, and decides what the page asks for and shows.

| Kind | For | The page leads with | Main action |
|---|---|---|---|
| **Fixed Price** | Contractors, fit-out, delivery for an agreed sum | Contract, cost, forecast margin, done | Bill Progress |
| **Time and Materials** | Agencies, consultancies, IT services | Hours this month, not invoiced yet, invoiced, budget used | Invoice Time |
| **Retainer** | A monthly fee for a set number of hours | Hours used of this month's, next renewal, invoiced | Invoice Month |
| **Internal** | Office moves, rollouts, anything without a customer | Budget used, done, due | Post Update |

The kind is a field on Project (`one_kind`). A project made before kinds
existed is Fixed Price if it has a sales order, Time and Materials if it has
billable time, and Internal otherwise.

## Making a project

**New Project** opens a dialog: pick the kind, then fill in only what that
kind needs.

- Fixed Price: name, customer, contract value, retention, dates, manager,
  template.
- Time and Materials: name, customer, budget, dates, manager, template.
- Retainer: name, customer, monthly fee, hours a month, start, manager.
- Internal: name, budget, dates, manager, template.

The dialog is frappe's own (fields are frappe controls). It makes the Project
and, for Fixed Price, the customer's Sales Order for the contract value, so
Bill Progress works from day one.

## The page

`/desk/project/<name>` opens the page instead of the form. The form stays,
under **···** › **Edit Details**, for every field the page doesn't show.

- **Head**: Projects / name, the kind, status and health as badges, Board
  and Schedule, **···**, and the kind's main action.
- **Title**: the name, then customer, dates and manager in one line, and the
  team's avatars.
- **Four cards**, the kind's figures (table above), each with a bar where
  there is something to fill.
- **Tabs**, by kind:
  - Fixed Price: Overview, Tasks, Schedule, Money, Suppliers, Team, Files,
    Activity.
  - Time and Materials and Retainer: Overview, Tasks, Time, Invoices, Team,
    Files, Activity.
  - Internal: Overview, Tasks, Schedule, Money, Team, Files, Activity.
- **Overview**:
  - Fixed Price: milestones as a line, **Needs you** (over budget, bills to
    check, late tasks, retention coming due), the latest update, then About,
    sub-projects and subcontracts on the right.
  - Time and Materials: hours by week, hours by activity, Needs you (time
    not invoiced, late tasks), then About and who logged time.
- **Money** is today's Costing tab, laid out on the page: Customer, Cost,
  Cost Types, Forecast. **Suppliers** is the subcontracts as cards, each with
  Bill Progress.
- **Tasks**, **Schedule**, **Files** and **Activity** are the parts that
  exist (the board, the Gantt, OneCloud, frappe's timeline), shown in the tab.

## Built from frappe

- A desk Page, as OneMail and OneCloud are, in plain JS with frappe-ui's
  look: Badge, Button, Tabs, Progress and ListView as frappe-ui draws them.
- Data from one call per tab (`one_project/page.py`), over the modules that
  exist: overview, money, budget, progress, tree.
- Changes are frappe's: fields in dialogs of frappe controls, saved against
  `modified`; the page follows the record through `doc_subscribe` and
  `doc_update`, and money through `one_project_money`.
- Permissions are the record's: whoever may read the project sees the page;
  each action shows only to whoever may do it.

## Stages

1. **Kinds**: `one_kind`, the patch that sets it, and the New Project dialog.
2. **The page**: head, title, cards and Overview for each kind; the list
   opens it; Edit Details opens the form.
3. **Money and Suppliers** on the page; the form's Costing tab goes.
4. **Tasks, Schedule, Time, Invoices, Team, Files, Activity** tabs.
5. **Retainer**: the monthly allowance and Invoice Month.
6. **Phone layout, OneAI** (`where`, suggestions by kind), **README,
   notifications, translations**.
