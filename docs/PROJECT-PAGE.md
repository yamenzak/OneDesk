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

A Fixed Price project made without a contract value, or started from a
quotation, gets it on its page. While the quotation is open the first card is
**Quoted** with **Make Order** (ERPNext's quotation mapper,
`make_sales_order`, so the order is made as it is from the quotation). With
neither, the card offers **Add Contract** (kinds.py `add_contract`), the same
Sales Order the dialog makes. Both orders are in the customer's currency.
With one open quotation, Make Order is the page's main button; with several,
the card says how many and opens them as a list. New Quotation stays in ···
until the project is ordered. The Overview lists the project's quotations
(view.py `_quotes`), and Work and Billing waits for an order.

## The page

`/desk/project/<name>` opens the page instead of the form. The form stays,
under **···** › **Edit Details**, for every field the page doesn't show.

It is laid out as monday and Asana lay out a project: a head that says what
the project is and how it's going, then views of the same work.

- **Desk's head**: Projects / name, **···**, and the kind's main action.
- **The project's head**: its Featured Media across the page (Hero.vue),
  the cover first and then each in turn, cross-fading: a photo for six
  seconds, slowly drawing in; a video muted to its end; a single video on a
  loop. A bar per item shows where it is, the pointer over it pauses it, and
  a click opens the rest in frappe-ui's Dialog. The kind, the name (click
  to rename), the status and health as pills that change in place and the
  kind's facts sit over it, the team in its corner, and the views right
  under it (on a phone the facts go under the photo). The kind's facts are
  the contract on a Fixed Price project, the start and hours a month on a
  Retainer, days left on an Internal one. With no photos the same sits on a plain panel,
  with **Add Cover**, which opens frappe's upload dialog with media.py's `add`
  as its method. Someone whose system asks for less motion gets the
  photos still.
- **Views**, in one bar under the head, kept in `?view=`:
  - **Overview**: laid out for the kind, each thing once. The brief when
    written, the kind's figures, then Fixed Price: Work and Billing,
    Budget, Milestones (Subcontracts and Retention beside). Time and
    Materials: Hours by Week, Not Invoiced Yet by person (By Activity
    beside). Retainer: Months, Hours by Week (By Person and By Activity
    beside). Internal: Tasks by status, Milestones, Due Soon (Who's On It
    beside). Updates is the latest one and a line to post the next; Needs
    You, About and sub-projects are on every kind.
  - **Tasks**: monday's table. One group per project in the tree (or by
    status, owner or due date), each with its colour, count and an **Add
    Task** row. Owner, status, due date and priority change in the row. A
    switch lays the same tasks out as a **Board** (columns by status; a card
    is dragged to change it) or a **Timeline** (the dated tasks as bars over
    the weeks, today marked), as monday's views of one board.
  - **Time**: the tree's timesheet entries with where each stands (Draft, To
    Invoice, Invoiced, Not Billable), figures for this month, all time, to
    invoice and invoiced, **Log Time** and **Invoice Time**.
  - **Invoices**: the customer's invoices on the tree, with Invoiced, Paid,
    Outstanding and Overdue, and **New Invoice**.
  - **Team**: members, manager, assignees and whoever logged time, with open
    and late tasks and hours; **Add Member** and removing a member.
  - **Files**: what is attached to the project and its tasks, with
    **Upload**.
  - **Activity**: frappe's timeline of the project, with a comment box.
- **A task opens beside the page**, as Asana's does: its fields, its
  description and its own activity, without leaving the project.
- **Money**: the forecast as figures (Contract, Budget, Forecast Cost,
  Forecast Margin, Margin So Far; or Budget, Spent, Forecast Cost and Left
  for a project with no customer), the customer's side and the cost side as
  rows with a bar against what was ordered, and Cost Types as a table with
  **Add Cost Type**. The budget is changed from its figure until there are
  cost types.
- **Suppliers**: a card per subcontract, with how much is billed, what's
  left, paid, retention and advance, **Open Order** and **Bill Progress**;
  **New Purchase Order** above them. Shown on a Fixed Price project, and on
  any other once it has an order.
- **A Retainer's Overview** lists its months: hours used of the allowance,
  any over, and the invoice or **Invoice Month**. Invoice Month is a draft
  invoice with the fee, the hours over, and the month's time on it, so the
  time is marked invoiced when it's submitted.
- The form's Costing tab keeps only the Budget and ERPNext's own fields; the
  HTML sections that drew the money there are gone.

## Built from frappe

- A desk Page whose body is a frappe-ui island (docs/ISLANDS.md): Badge,
  Button, Tabs, Dropdown, DatePicker, TextInput, Avatar and Progress from
  frappe-ui; `frappe-ui/list` for the table; NumberCard and BarChart from
  `frappe-ui/charts`; ActivityTimeline from `@framework/ui`.
- Data from `one_project/view.py`: `said` for the head, Overview, Money and
  Suppliers (with money.py's figures), `work` for the tasks, `files` and
  `updates`; budget.py's `lines` for the cost types; hours.py, billing.py's
  `invoices` and team.py for Time, Invoices and Team.
- Changes are frappe's: `set_value`, `insert` and `assign_to` for tasks and
  the project; the form behind Edit Details for the rest. The page follows
  the project through `doc_subscribe` and `doc_update`, the tasks through
  `list_update`, money through `one_project_money` and the cover through
  `one_project_media`.
- Permissions are the record's: whoever may read the project sees the page;
  whoever may write it or its tasks may change them in place; each action
  shows only to whoever may do it.

## Stages

1. **Kinds**: `one_kind`, the patch that sets it, and the New Project dialog.
2. **The page**: head, title, cards and Overview for each kind; the list
   opens it; Edit Details opens the form. Done, as the workspace.
3. **Money and Suppliers** on the page; the form's Costing tab goes. Done.
4. **Tasks, Schedule, Time, Invoices, Team, Files, Activity** tabs. Done.
5. **Retainer**: the monthly allowance and Invoice Month. Done.
6. **Per kind**: the head and Overview laid out for each kind, the cover and
   Featured Media in the head. Done.
7. **Featured Media turning**: across the head of the page, and beside the
   project on the customer's portal (one_gallery.js). Done.
6. **Phone layout, OneAI** (`where`, suggestions by kind), **README,
   notifications, translations**. Done.
