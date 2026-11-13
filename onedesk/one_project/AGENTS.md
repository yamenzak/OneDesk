# OneProject

The one file for agents, OneAI and us: what OneProject is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `help/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `updates/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneProject is where work bigger than a task is run: a villa's windows, a
website, an office move. A project holds its tasks, its time, what it costs
and what it's billed. A project's quotation, sales order, timesheets and
invoices are the same records the rest of One uses.

**OneTask and OneProject share the same tasks.** OneTask is what each person
has to do. OneProject is how a project is going, for the people who run it. A
project task assigned to you shows on your My Tasks and on the project's board.

## Connections

- **From OneCRM**: A quotation made from a deal or the Quotation list can be put on the customer's open project. Once the customer orders it, its Sales Order is the project's contract. A Sales Order with no project starts one with its Create › Project: its customer, the order as its contract, and the customer's terms.
- **From OneTask**: A project's tasks are the same tasks people see on My Tasks. The timer on a task logs its time on the project.
- **From OneHR**: A day of attendance at the project's site becomes a timesheet on the project. Expense claims on the project count in its Cost, and Workload leaves out holidays and approved leave.
- **From OneInventory**: Purchase orders, goods received and stock issued for the project count in its Cost. A purchase order for a package of work is a subcontract on the Suppliers view.
- **From OneAI**: A supplier's bill that names an open project is drafted for that project. So is a supplier's timesheet, at the hours and rate it gives. A site log a colleague mails in is their part of the day's update on the project it names. A customer asking for extra work on their project gets a draft quotation for Extra Work on it, which becomes a sub-project once ordered.
- **From OneCloud**: Photos and videos in the project's Featured Media folder show on its page and on the customer's portal.
- **To OneInventory**: New Material Request, Ask for Prices, New Purchase Order and Issue Stock on a project's page start those records on the project. Ask for Prices and Issue Stock ask as OneInventory's Quotes page and Transfer Stock do, with the project filled in; an issue is made and submitted at once, so its cost shows on Money.
- **To OneHR**: New Expense Claim on Money starts an expense claim on the project, which counts in its Cost once approved.
- **To OneBook**: Invoice Time, Invoice Month and Bill Progress make the customer's invoices for the project, due by its payment terms. Bill Progress on a subcontract drafts the supplier's bill. A new Retention Due on an order moves the date in the receivables report too.
- **To OneCRM**: New Quotation and Quote Extra Work start the customer's quotation on the project, and Make Order turns the one open quotation into its Sales Order. Add Contract makes the Sales Order for a contract agreed without a quotation. Draw Up Contract makes a Contract for the project with its customer or one of its suppliers.
- **From One**: the Team view's members are the workspace's people, and adding one shares the project with them. Team › Contacts names the customer's and suppliers' people from One's Address Book, with their email and phone.

## Under the hood

### What it is made of

ERPNext's **Project** is the project and its money: the customer, the one
Sales Order it answers to, `estimated_costing`, and the totals ERPNext keeps
from timesheets, purchases and invoices (`total_costing_amount`,
`total_billed_amount`, `gross_margin`). ERPNext's **Task** is the work, and is
OneTask's as much as ours. ERPNext has no project inside a project; Parent Project
(`one_parent`) adds one field for it.

- `board.py` — ERPNext's own per-project Kanban, shaped as it is made, and
  their nightly Overdue job stopped: a late task is a date, not a column. Their
  Project Summary report counted Overdue tasks, and now counts none.

  ERPNext already makes the board. **View › Kanban Board** on a project
  creates a board named after it, filtered to its tasks, with a column per
  Task status. board.py shapes that board as it is made (`shape`, on the
  Kanban Board's before_insert): Template and Cancelled are archived, the
  columns get colours, and a card shows the priority and the due date beside
  the people on it.

  **Overdue is not a status here.** ERPNext's daily job sets every open task
  past its due date to Overdue, whatever it was — a task somebody was Working
  on moves columns overnight, and moving it back lasts until the next night.
  How late a task is follows from its date, and every list in One already
  shows it from there (My Tasks has an Overdue group; the calendar draws it on
  its day). So the job is stopped, and Overdue is taken off the status list
  (custom/task.json).

  **The Projects list has a board too**: Projects by Health, open projects in
  On Track, At Risk and Off Track, made once by `settle` so the Kanban view
  opens on it rather than on a dialog asking which field to group by.

  The list is public/js/one_project/project_list.js. Each time it is drawn it tells
  OneStudio's extensions the projects it shows (`oneproject_list.projects`,
  one_studio/places.py), with a spot above the rows for what they add. In
  Report view, Health is blank on a completed or cancelled project, as the
  list's pill is.
- **One Project Status** (print_format/one_project_status) is the project's
  print: its name, the customer and its dates from one_studio/print_blocks.py, and
  One's `progress` block (templates/one_print/progress.html). The block reads
  the project as the customer's portal does (portal.py `view`): how much is
  done, the milestones, the next tasks due, the sub-projects, the contract and
  the invoices with what is outstanding. It's the one print still drawn from
  blocks: what it says is gathered from other records (tasks, orders,
  invoices), which a format made of the builder's own pieces can't reach
  from the project.
- **One Timesheet** is drawn from the builder's own pieces
  (`scripts/print_formats.py`): whose hours, for whom and when, each day's
  work with its task, the hours billable, and the customer to approve them.
- **One Project Update** prints what each person said about a project on a
  day.
- **One Sales Invoice** shows the hours a time and materials invoice bills,
  from ERPNext's Time Sheets table on it, as Time Billed, or Time Spent with
  the hours alone on a retainer, whose fee isn't the time's. An invoice that
  bills no time shows nothing.
- `calendar.py` — a project's **Tasks** on its own calendar, read through
  OneTask's `calendar.due`.
- Currency: every order and invoice made here goes through one_book/currency.py
  `bill_in`, so a customer billed in USD is billed in USD. Timesheet amounts
  are turned into the invoice's currency by `billing.in_currency`, as
  ERPNext's own Fetch Timesheet does. A retainer's fee is in the customer's
  currency (`retainer.fee_currency`); the page shows it so (a card's own
  `currency`). Money's **Quoted** counts quotations still standing
  (`money.QUOTED`), and `view.to_quote` names a new quotation's project.
- `media.py` — a project's **Featured Media**: its files marked `one_featured`
  (File), shown in OneCloud as a folder inside the project's own
  (`@featured/<project>`, one_cloud/namespace.py), so nothing is stored for
  the folder. Putting a file in attaches it to the project, marks it and makes
  it public; taking it back to the project's folder clears both. The newest
  photo is `one_cover`, Project's `image_field`, set as the folder changes
  (File after_insert, on_update, on_trash), and `CloudFile.on_trash` hands the
  cover to the next photo before frappe's check that no field still names the
  file. `featured` lists them for the page; `portal.view` for the portal.

  Every project's own folder in OneCloud, under Records, has a **Featured
  Media** folder. What is in it is shown on the project's page, on the
  customer's portal, and wherever else the project is shown off; the newest
  photo in it is the project's **Cover** (`one_cover`, Project's image field,
  so frappe shows it wherever it shows a record's picture).

  **Nothing is stored for the folder.** A record's folder in OneCloud is
  worked out from the files attached to the record each time it is opened
  (one_cloud/namespace.py), and Featured Media is worked out the same way:
  the project's files with `one_featured` set. Putting a file in it attaches
  it to the project with the mark; taking it out to the project's own folder
  clears the mark. A folder called Featured Media anywhere else is just a
  folder.

  **Featured media is public.** It is there to be shown, on a portal and on a
  website, so a file put in it opens for anybody with its link (`is_private =
  0`), which is what frappe's File means by public and what OneCloud's
  `store.fetch` already honours. Only photos and videos go in.
- `naming.py` — a project's Task Prefix, as a frappe Document Naming Rule for
  Task with the condition "project is this one". ERPNext's Task class is not
  overridden, and frappe's series for a prefix never reuses a name.

  **Task Prefix** on a project is a short key. Setting it writes a frappe
  Document Naming Rule for Task with the condition "project is this one",
  which is the framework's own way to name a doctype differently by a field —
  nothing of ERPNext's Task is overridden, and a task in a project with no
  prefix keeps ERPNext's series.

  The number comes from frappe's series for the prefix, which is global to the
  site: a prefix changed and changed back carries on counting rather than
  reusing a name. Tasks already made keep the names they have. A new project's
  rule is written as it is saved, so the tasks a Project Template makes for it
  carry the prefix too.
- `members.py` — who sees a project: Projects Managers all, anybody else
  holding Projects User the ones they made, are listed on, or that list
  nobody (`visible`, kept for the request). A project's tasks follow it
  through one_task/access.py. Being listed is also ERPNext's own share.
  ERPNext's invitation mail is never sent (`invite`); tell.py says it in ours.
  Somebody who can't open a project joins it (`join`) when given one of its
  tasks (`assigned`, ToDo after_insert; New Task asks `joins` first), when
  it's shared with them (`shared`, DocShare after_insert, the sidebar's
  Members on the page and the form, `public/js/one_project/project_actions.js`), and
  when a comment mentions them and the writer agrees (`unseen`, `let_in`,
  through the composer's `vet`). ERPNext shares the project with a new member
  as whoever saves it, so when OneAI or Intake gives the task without the
  right to share, the joining is saved as Administrator.

  ERPNext lets every Projects User read every project. A workspace running a
  villa for one customer and a website for another does not want the window
  fitter reading the website's budget, so a project's **Users** decide:

  - a **Projects Manager** sees every project, and so do the books (an
    **Accounts User** or **Accounts Manager**), who invoice every project's
    time and progress;
  - anybody else who works in projects sees a project they made, one they run
    (**Project Manager**), one they are listed on, and one with **nobody
    listed** — a project nobody has closed is open to everybody who works in
    projects, which is also what every project was before this;
  - members of a project see what is under it (sub-projects; `under`).

  The same rule decides a project's tasks (one_task/access.py): a task in a
  project is seen by whoever may see the project, and by its own people
  always.

  **Being listed is ERPNext's own share.** Their Project already shares itself
  with each person on Users and takes the share back when they are removed, so
  a member opens the project through frappe's share as well as through this
  rule.

  **A member can be taken off.** ERPNext takes back a removed member's share
  in a way only a System Manager may, so the save failed for everybody in a
  workspace; `unlist` takes it back first.

  **A member is told in ours.** ERPNext mails an invitation to each new member
  while the project saves: English mail outside the hub, which also failed the
  save where the workspace has no outgoing mail. `invite` marks it sent, and
  tell.py tells the member as Added to Project instead.

  Only somebody holding Projects User is narrowed here. Twenty other roles
  have Select on Project so a sales order or an invoice can name one; they
  pick from a list and never open the project, and narrowing their list would
  break their forms, not protect the project.
- `tell.py` — Added to Project, Made Project Manager, Project Health,
  Project Completed, Project Stopped and Project End Moved, through the hub.
  `time_over` (Timesheet on_submit) tells a project's manager once its hours
  pass its plan (Hours Over Plan) or its time's cost passes its Time Budget
  (Over Budget, cost type Time), counted over the project and those under it.

  **Added to a project.** ERPNext mails each new member its own "Project
  Collaboration Invitation", in English, outside the hub. `members.invite`
  marks that mail sent, and `added` tells them in ours: on the bell, and by
  email or push as they chose, in their language.

  **Made its manager.** Nobody was told. `added` tells the new manager too.

  **Completed.** A project is completed by somebody or, in ERPNext, by its
  last task. `completed` tells its manager, with what's still owed on it, so a
  job done isn't taken for a job paid.

  **At risk.** Health is somebody's judgement that a project is in trouble
  before any figure says so. `health` tells its manager and members when an
  open project is marked At Risk or Off Track. Whoever marked it already
  knows. A closed project's health is shown nowhere, so it isn't told.

  **On hold, cancelled or later.** `stopped` tells the project's people when
  it is put On hold or cancelled, and `moved` when an open project's end date
  moves, with the date it had.

  **A retainer's month.** On the first of the month, `retainer_months` tells
  whoever runs each open retainer that last month isn't invoiced, with its
  hours against the allowance. And when a submitted timesheet takes this
  month's hours past the allowance, `hours_used` tells them then, while there
  is still time to say so to the customer.
- `updates.py` also keeps each answer's health (`one_health` on Project
  User), says how often the team is asked (`asking`), and tells the page an
  update was posted (`one_project_update`). OneAI's `draft_update` is a card
  whose approval puts the draft in the line (`one_project_draft`); nothing is
  posted from it.
- `milestones.py` — the Overview's milestones over the tree: the last two
  done and the ones to come (`pick`), where each is (`where`), and billing on
  them when one has a **Bill on Completion** share (`one_bill_share` on Task,
  `billable`). `reached` tells the manager of the project with the order.
  `kept`, on Task validate, holds a share between 0 and 100% and a project's
  milestones to 100% together, and refuses new work on a cancelled project
  (tree.py `validate` refuses a sub-project under one), however it's made.

  - The Overview shows the last two done and the ones to come, soonest first,
    with those without a date last (`pick`). One on a sub-project says which
    (`where`), and each says how far off or how late it is.
  - On a whole job, they are a row per part of it on one dated line: Main,
    then each sub-project directly under the page with what is under it
    (`lanes`).
  - **Bill on Completion** (`one_bill_share`) is a milestone's share of the
    contract, and it's optional. A project bills by milestones only when one
    of its milestones has a share: Work and Billing then counts the shares of
    the milestones done instead of the work done, and Bill Progress starts
    from that share (`billable`). When such a milestone is done, the manager
    of the project with the order is told to bill it (`reached`).
- `status.py` — the status, ERPNext's four. ERPNext sets it again on every
  save from the tasks (`update_percent_complete`), so `change` closes the
  open tasks and sub-projects first when asked (`ask`), keeps a task's own
  status when it's already closed, and puts progress back on the tasks when
  a project completed without any is opened again. `due` is what's still
  owed on a completed project.

  ERPNext works the status out again on every save
  (`update_percent_complete`): a project whose tasks are all done is
  Completed, and one with any task open is Open, unless it's On hold or
  Cancelled. So marking a project Completed while a task is open doesn't hold;
  the save sets it back to Open. `change` closes the open work first, on the
  page's say-so: the project's open tasks, and its open sub-projects with
  theirs, as ERPNext's own `set_project_status` closes a project's tasks.
  Unlike it, a task already done or cancelled keeps its status.

  Completing a project with no tasks of its own makes ERPNext keep its
  progress by hand at 100%, for good. Opening it again puts the progress back
  on its tasks.

  `due` is what's still owed on a completed project: the contract not yet
  invoiced, invoices not yet paid, and retention still held. Needs You shows
  it, and `tell.completed` tells the manager.

  `held` (Project before_validate, ahead of ERPNext's own status from
  progress) makes the status hold however it is set (the page, a bulk edit, an
  import):

  - A project closes with its work. Closed from its page, with its open tasks
    and sub-projects closed too, it closes them there. Set to closed any other
    way while work is open, it is refused.
  - Reopened after being completed with no tasks, its progress goes back to
    its tasks: ERPNext turned it to by hand only because there were none.
- `agent.py` — OneAI's `project_facts` (a project as its page reads it, with its
  late tasks, what waits on them, milestones and updates) and
  `projects_needing_attention`, and the page's suggestions.

  `project_facts` hands over the page's own answers (`overview.overview`): how
  far it has got, its dates, cost against the budget, what is billed, what is
  late and the next milestone, for the project and everything under it, and
  the Money view: both sides of the money, the subcontracts, the cost types
  and the forecast (`_money`). Beside them, what the page has further down:
  the late tasks with who is on each and what waits on them, the milestones to
  come, its people, and the team's last updates. `projects_needing_attention`
  reads the Projects list as the reader sees it and keeps the open ones in
  trouble.

  Both read as the person asking: a project they may not open is not read, and
  neither are its tasks. Tasks are only suggested (one_task/agent.py
  `plan_task`), as cards the reader approves.

  `draft_project` checks what it is given (a kind, a customer that exists, a
  template or preset, a contract's item) and proposes a Setup card with the
  values **Add Project** would send. Approving it runs `kinds.make` as
  whoever approved it (`approved`, through one_studio/ai_setup.py), so the project
  has the customer's terms and its contract's sales order.
- `chain.py` — every money document and its lines name the same project.
  Quotation, Request for Quotation and Material Request get a `project` field
  (custom/), named as on every other document so ERPNext's mapping carries
  it. Extra work is `one_extra_work` on Quotation and Sales Order
  (billing.py); `patches/extra_work.py` turned the old Sub-project Of into it.

  ERPNext lets most money documents name a project, on the document and on
  each line, and carries it when one is made from another: an order's delivery
  and invoice, a purchase order's receipt and bill, an invoice's payment.
  Three couldn't name one at all (Quotation, Request for Quotation and
  Material Request, which now can: custom/), and nothing kept a document's
  lines and the document itself in agreement, so a project's figures missed
  whatever somebody forgot to type.

  `agree` does that as each is validated: a line with no project takes the
  document's, and a document with no project takes its lines' when they all
  name the same one. Since the field is called `project` on every one of them,
  ERPNext's own mapping then carries it from document to document: a quotation
  to its order, a material request to its purchase order, a request for
  quotation to the supplier's quotation and on.

  A payment made from an invoice or an order takes its project from it, as
  ERPNext does. One made on its own and matched to invoices later, or paying
  several at once, takes the project they all name (`paid_for`). A new
  quotation, order, delivery or invoice for a customer with one open project
  names it on insert (`customers_one`), and the form fills it as the customer
  is picked (`customer_project`, public/js/one_project/customer_project.js).
- `heads.py` — `project.of`: the project a document is for, by name, opening
  its page, in the head of every document a project hands on. A contract's is
  its reference, and a deal's is the project its quote went to, else the
  customer's one open project.
- `budget.py` — cost types: ERPNext's own Budget against the project, one per
  expense account, checked on orders and expenses alone and together
  (`applicable_on_cumulative_expense`). Changing one revises it as ERPNext's
  Revise Budget does (cancel, copy, submit). Committed is the open order
  lines on that account (`money.unbilled`); spent is the ledger. `sync` makes
  the project's Budget their total. Budget permissions are ERPNext's.

  A **cost type** is an expense account (labour, materials, subcontract,
  equipment, or whatever accounts the workspace uses), and its budget is one
  ERPNext **Budget** against the project for that account, submitted. ERPNext
  then checks every purchase order and every expense booked on the project
  against it, and warns or stops as the budget says (`Over Budget`).

  - ERPNext checks orders and spending each on their own, and together when
    `applicable_on_cumulative_expense` is set, which a cost type always is: an
    order is over budget when it, the open orders and what's spent come to
    more than the budget.
  - **Cost Types** on the page's Money view lists each one over the project
    and those under it, as the Overview does: its budget, what's committed on
    supplier orders not yet billed, what's been spent (the general ledger),
    and what's left, with Other for what they leave out (`lines`). A row the
    project budgets for itself is changed there; any other adds the project's
    own.
  - **Add Cost Type** and changing one (`set_budget`) are ERPNext's own: a new
    Budget, or the old one revised as ERPNext's Revise Budget does it,
    cancelled and copied with the new amount. Removing one cancels it.
  - The project's **Budget** is then the cost types added up (`sync`), so the
    forecast and the head read the same number.
  - **Over Budget** tells the project's manager and whoever set the budget,
    once for each budget, when its orders and spending pass it (`over`).
  - Making a budget is for whoever ERPNext lets make one (Accounts Manager);
    everybody who sees the project sees the cost types.
- `kinds.py` — a project's kind (`one_kind`, and `one_monthly_fee` and
  `one_monthly_hours` for a Retainer). `make` is New Project: the project,
  and for Fixed Price its customer's Sales Order, submitted, as its
  `sales_order`. `fill` gives a project made elsewhere the kind its records
  say (`guess`, pure); `patches/kinds.py` did it for the projects before.
  `settle` makes the **Contract Work** item, in Lump Sum.
  `public/js/one_project/project_new.js` is frappe's quick entry for Project
  (`ProjectQuickEntryForm`): the kinds as cards, then the kind's fields. Its
  fieldnames are its own, since a quick entry takes a field's label and
  whether it's hidden from the doctype when the names match.

  - **Fixed Price**: an agreed price, billed as the work gets done. Its
    contract is the customer's Sales Order, made with the project (`make`), so
    Bill Progress works from the first day (progress.py).
  - **Time and Materials**: billed by the hour at agreed rates, plus what's
    bought for it (billing.py's Invoice Time).
  - **Retainer**: a monthly fee for a set number of hours (`one_monthly_fee`,
    `one_monthly_hours`).
  - **Internal**: no customer; a budget and the work.

  A project made without a kind, by ERPNext, HR or an import, is given the
  kind its records say (`guess`, `fill`), as `patches/kinds.py` did for the
  projects made before kinds existed.
- `progress.py` — Bill Progress on a purchase or sales order (a subcontract is
  a purchase order; ERPNext's own "Subcontracting" is something else, a factory
  making items from materials sent to it): ERPNext's own
  "Create > Invoice" mapper with each line's quantity cut to the share done
  less what's billed (`to_bill`), since ERPNext keeps an invoice at the
  order's rate. `settle` makes the **Lump Sum** unit (can be split) and the
  **Retention** and **Retention at Handover** payment terms. Retention is the
  order's `one_retention`, `one_retention_due` and `one_retention_handover`
  (custom/purchase_order.json and sales_order.json, all editable after
  submit). Each invoice holds its own `one_retention`, which ERPNext's mapper
  copies from the order and which may be changed before submit; an invoice
  made before had its order's (patches/retention_by_invoice.py). The
  payment schedule holds it under those terms after the invoice's own
  (`_hold`, dated from the order or else the project, `source`), set again
  after ERPNext's own split so it's the share of the work billed, not of
  what's left after advances (`retained`, `split`, `spread`). Set to 0, the
  terms go. A new Retention Due moves it on the order's invoices (`release`).
  `public/js/one_project/progress.js` is the dialog; `money._suppliers` is the Suppliers
  table.

  A **subcontract** is a Purchase Order on the project, one per supplier per
  package of work. The customer's contract is their Sales Order. Both are
  billed the same way, a share at a time:

  - **Bill Progress** (`bill_progress`) asks how far the work has got, as a
    share of the order, or line by line (`lines`) where work is measured
    against a bill of quantities, and drafts the invoice for what that comes
    to less what's been billed already. The invoice's Work Done is then the
    share of the whole by amount (`overall`). It's ERPNext's own "Create >
    Invoice" from the order with each line's quantity cut to that share, so
    the order's billed amount, its status and the project's figures are
    ERPNext's. ERPNext keeps an invoice at the order's rate, so a share is a
    part of the quantity: a package of work is ordered as 1 **Lump Sum**
    (`settle`), a unit that can be split. A line in a unit that can't is
    refused in plain words.
  - **Retention** is a share of each invoice held back (often 5 to 10%), set
    on the order with the date it's due (`one_retention`,
    `one_retention_due`). The invoice's payment schedule splits in two: the
    rest, due as usual, and **Retention**, a Payment Term of that name due on
    that date, the share of the work billed before tax, whatever advance is
    set off (`retained`). Part of it may be released at handover first
    (retention.py). Changing the date on the order moves it on every invoice
    made from it (`release`).
  - **Advances** paid against the order are set off by ERPNext on each invoice
    (`allocate_advances_automatically`).
  - The invoice says the share it's for (**Work Done**, `one_progress`), and
    saving it tells the project's manager to check it (`drafted`).
- `retention.py` — the **Hold Retention** switch (`on`, Projects Settings'
  `one_retention`, in the boot for the desk), what's still held on an
  invoice part by part (`still_held`, `held_on`), the Overview's two sides
  (`sides`), Needs You's asks (`asks`), handover falling due when a project
  is completed (`handed_over`), and the daily Retention Due (`due`). A
  customer order on a project starts with the project's retention
  (`ordered`, Sales Order before_insert, and `public/js/one_project/progress.js` on the
  form); the project's own is `one_retention`, `one_retention_due` and
  `one_retention_handover` (custom/project.json). Release Retention and Pay
  Retention are `release`: ERPNext's `get_payment_entry` for the party, its
  lines replaced by one per retention term still held (`picked`), so
  ERPNext's own `update_payment_schedule` marks the terms paid. What's held
  is each term's own outstanding, so a released term no longer counts, and
  no more than the invoice owes (`held_on`, `_base`).

  - **Hold Retention** in Projects Settings turns it on (`on`). Off, the
    retention fields leave the orders, the project dialogs and the Overview. A
    workspace already holding retention had it turned on by the update
    (patches/retention_switch.py).
  - An order may release part of its retention at **Handover** (`HANDOVER`,
    `one_retention_handover`), due when the order's delivery date comes, or as
    soon as its project is marked Completed (`handed_over`), and the rest at
    **Retention Due** (`RETENTION`).
  - What's still held on an invoice is read part by part (`still_held`):
    retention is paid last, its handover part before the rest.
  - The Overview sets what the customer holds beside what's held from
    suppliers (`sides`). A customer's retention due within a month, or past
    due, is in Needs You (`asks`), and a project's manager is told on the day
    any of it falls due, either side (`due`).
- `intake.py` — which open project a document names, for the bills OneAI
  drafts (one_ai/reading/money.py).

  A supplier's bill for the villa's glass says "Villa Al Barsha" somewhere: in
  its reference, a line, the delivery address. Booked with no project, it was
  missing from the project's **Cost** until somebody set it by hand. Intake
  now asks `named` which open project the document names, and the bill it
  drafts, and each of its lines, carry it.

  A name only counts whole, ignoring case, and only one project may be named:
  a bill naming two is left for a person, as one naming none is. A name inside
  a longer one that is also named ("Villa" and "Villa Windows") is the longer.
- `tree.py` — sub-projects: Parent Project (`one_parent`), the only field
  added, since ERPNext keeps money per project and has no project inside one.
  A loop is refused, a sub-project takes its parent's customer, a tree's
  figures are ERPNext's own added up each time (`totals`), and
  `group_under` puts a new project above one. `path` is where a task is, for My
  Tasks and a parent's calendar. Sub-projects are a connection on the page
  (`dashboard`). The Projects list's Tree view is frappe's treeview over
  `nodes` (`public/js/one_project/project_tree.js`, `under` is pure), and its Gantt view
  is frappe's over the project's dates, with `milestones` added as rows of
  their own that can't be dragged (`public/js/one_project/project_calendar.js`).

  ERPNext keeps a project's money per project — its one Sales Order, its
  timesheets, its costs, what it has billed and its margin — and has no
  project inside a project. So a separately billable piece of a job is a
  project of its own, and the one field tree.py adds is **Parent Project**
  (`one_parent`). The handrails on a villa are a project under the villa:
  their own quotation and order, their own time and invoices, and ERPNext's
  totals for them as for any project. Nothing of ERPNext's is copied or
  changed.

  - **A project cannot sit under itself**, however far down (`validate`).
  - **A sub-project takes its parent's customer** when it has none.
  - **A parent adds up its tree** (`totals`): its own figures and the whole
    tree's, worked out each time rather than stored, so moving a project in
    the tree is right straight away.
  - **Group Under New Project** (`group_under`) puts a new project above one —
    the villa above the windows — and moves it and whichever of its
    sub-projects are ticked underneath, so they become siblings.
  - **Members of a project see what is under it** (members.under).
  - **A page can read a parent on its own** (`narrow`, `scope`): its Main, the
    work on the project itself without what is under it.
  - **Where a task is** reads as a path, Villa › Handrails (`path`), on My
    Tasks and on a project's calendar.
- `rates.py` — Rates: Activity Type is the rail's row, and an Activity Cost,
  a person's own rates for one, is its connection and leads back to it.

  ERPNext keeps rates in two places: an **Activity Type** has a default
  costing and billing rate, and an **Activity Cost** overrides them for one
  employee. They answer one question, so the rail has one row, Rates, the
  Activity Type list, and each activity lists its people's own rates under it,
  with + to add one for somebody (`dashboard`). A timesheet prices an hour
  from the person's rate if there is one, else the activity's (ERPNext's own
  rule).
- `plan.py` — a slip moves the dependants in the rest of the tree, which
  ERPNext's own pass never looks at (`reschedule`, `moved_after` is pure). The
  schedule is frappe's Gantt over Task, filtered to the tree
  (`public/js/one_project/project.js`); `public/js/one_task/task_list.js` draws a task with only a
  due date and lights the view mode the chart is in, and `public/css/desk.css`
  lets it scroll.

  **A slip crosses sub-projects** (`reschedule`). ERPNext moves only
  dependants in the same project as the task that slipped. "Install the
  handrails" in Handrails waits on "Fit the frames" in Windows, both under one
  villa, and should move when the frames do. So after ERPNext's own pass
  plan.py moves the dependants in the rest of the same tree, the way theirs
  moves the others: a task not yet done (Open, Working or Overdue) that would
  start before the new end starts the day after it, keeping its length, and a
  date past its project's end warns rather than refuses. It saves the
  dependant whether or not the person who moved the date may edit it: the date
  moved because of theirs, and a plan that holds only where the mover is a
  member is not a plan.

  **The plan is frappe's Gantt** over the tree's tasks (public/js/one_project/project.js,
  Schedule): bars, milestones, the dependency arrows, and dragging a bar moves
  the task. A task with a due date and no start is drawn as a day on its due
  date (public/js/one_task/task_list.js).
- `billing.py` — money on ERPNext's own records. Pricing is theirs
  (Activity Cost, then Activity Type, in `TimesheetDetail.update_cost`).
  **Invoice Time** (`invoice_time`, opened through
  `frappe.model.open_mapped_doc`) is their Sales Invoice with its Time Sheets
  filled from their own list of billable unbilled hours
  (`get_projectwise_timesheet_data`), lines by activity and hourly rate
  (`lines`, pure); submitting it is theirs too. ERPNext rounds each Time
  Sheets row and each line to the cent apart, so the rows under a line are
  set to add up to the amount ERPNext makes of the line, the last row taking
  the cent left over, and **Time Billed** is the time lines to the cent, in
  the customer's currency as much as in ours. **Extra Work** (`one_extra_work`, the same
  field on Quotation and Sales Order so their mapping carries it) makes the
  submitted order a sub-project of its project through their own
  `make_project` (`ordered`, named by `title`, pure), and moves the order and
  its lines onto it. **Quote Extra Work** (`public/js/one_project/project.js`) starts
  such a quotation, and `public/js/one_project/quotation.js` gives it the project's
  customer.

  **Time is priced by ERPNext.** A timesheet row takes its costing and billing
  rate from the person's **Activity Cost** for its activity, or the **Activity
  Type**'s own rates when they have none (`TimesheetDetail.update_cost`), and
  a submitted timesheet adds its cost and billable amount to the project. The
  timer (one_task/timer.py) writes those rows; nothing in billing.py prices
  anything.

  **Invoice Time** (`invoice_time`) is ERPNext's Sales Invoice with its Time
  Sheets table filled: every billable hour on the project not yet invoiced, as
  lines by activity — Design 12 h, Site visits 4 h — at what the hours come
  to. It opens as a draft for somebody to read before it is submitted, and
  submitting it is what marks the hours billed and adds to the project's
  Billed, which is ERPNext's (TimesheetBillingService). On a project with
  sub-projects it takes the whole tree's billable time for the same customer,
  each line of the invoice's Time Sheets naming its project, so the villa's
  page invoices the windows' hours too (`_rows`). A retainer's hours are
  billed with its month, never here.

  **What was bought for it** (`costs`). A Time and Materials job bills the
  materials and outside work bought for it as well as its hours: supplier
  bills' lines on the project, stock issued to it, and approved expense claims
  for it, each at what it cost the company plus the project's **Markup on
  Costs** (`one_markup`). Invoice Time adds them as lines under the time, one
  per cost, and each line names the cost it bills (`one_rebills`), so a cost
  is never billed twice and is billable again if its invoice is cancelled.
  Only a Time and Materials project's costs are billed this way; a fixed price
  covers its own.

  **A quotation for extra work becomes a sub-project** (`ordered`). A
  quotation names its project like any other (chain.py), and **Extra Work**
  says it is more than the job was ordered for. Both are carried to its Sales
  Order (the same fields on both, so ERPNext's mapping carries them), and when
  the order is submitted a project is made for it under that one, ERPNext's
  own "Create > Project" from an order with the order's total as its estimate.
  The order and its lines then name the sub-project, so the handrails a
  customer asked for halfway through the windows have their own order, time,
  costs and invoices, and add up into the villa's.
- `updates.py` — ERPNext's Project Update, asked and answered. Their asking
  mailed only (and raised where no mail goes), asked hourly all day and twice
  daily in two hours running, and read email replies back every hour, adding
  them again each time, and only on the day asked. Their three askers and the
  collector are stopped (`settle`); `ask` (hourly, `due` pure) makes the
  Project Update, notifies members in One and mails where mail goes; `post` is
  Post Update; `answered` takes an email reply once as it arrives; `logged` is
  a site log OneAI read, written as its sender's answer for the day;
  `timeline`
  (additional_timeline_content) shows the answers in the project's activity.
  Their morning summary still runs, where mail goes (`sum_up`). Hourly is off
  the Frequency choices.

  ERPNext has the parts: **Collect Progress** on a project, how often and
  when, the subject and message of the ask; a **Project Update** for each ask;
  the answers as rows on it; and a summary of yesterday's answers mailed to
  the team (`send_project_status_email_to_users`). The asking and the
  collecting did not work, and updates.py replaces those two:

  - **It only asked by email, and only where there was mail.** With no
    outgoing account the ask raised, rolled back its Project Update, and
    nothing was asked. `ask` makes the Project Update, tells each member in
    One (a notification that opens the project), and mails them as well where
    mail can go.
  - **It asked too often.** Hourly asked every hour of the day, its window
    tested with `or`; Twice Daily asked in two hours running. `due` asks once
    a day, twice at the two times, or once on the day of the week. Hourly is
    taken off the choices: a status note every hour is not a status note.
  - **An answer could only be an email reply**, and was read back every hour
    and added again each time, and only on the day it was asked. `post` is
    **Post Update** on the project's page, which answers today's ask or, with
    none, makes one; `answered` takes an email reply once, when it arrives,
    whatever the day.
  - **The answers were kept out of sight** on the Project Update. `timeline`
    puts each one in the project's activity, under who wrote it.
  - **The summary of yesterday's answers was only mailed**, and only where
    mail could go. `sum_up` tells the project's people in One instead, and
    each chooses whether it is mailed too.
  - **An answer kept no health.** `_answer` keeps the project's health on the
    answer (`one_health` on its row), so the page shows how it was going when
    each was written, and tells the page's readers it was posted
    (`one_project_update`).
  - **Nothing on the page said whether the team is asked.** `asking` says how
    often, for the Updates heading.
- `custom/project.json` also carries **Health** (`one_health`) and **Project
  Manager** (`one_manager`, who always sees the project — members.visible),
  both from the old OneProject: ERPNext's Project has neither a judgement of
  how it is going nor one person who runs it.
- Boarding projects — HRMS builds an onboarding or an exit out of a Project —
  are typed **Employee Boarding** by one_hr/lifecycle.py, and the Projects
  rail entry, the Tree view and the Timeline leave that type out.
- `report/project_progress` and `report/stock_by_project` — ERPNext's
  Project Summary and Project wise Stock Tracking, asked through theirs
  without the HR checklists. Theirs read every Project, and an employee's
  onboarding or exit checklist is one (one_hr/lifecycle.py), so their rows,
  charts and totals took them in; Stock Tracking also read past the reader's
  permissions. Ours drop the columns that say the project's name again and
  the company, give completion as a whole share, and keep only the projects
  stock moved on. Theirs are disabled (one/declutter.py,
  patches/reports_without_checklists.py).
- `report/workload` — Workload: planned hours from ERPNext's Expected Time
  and Actual Time on the reader's visible tasks (`in_week`, `load` pure),
  capacity from the holiday list (the employee's, else the company's), HR
  Settings' Standard Working Hours and approved Leave Applications. Its rows
  are drawn by an island (`frontend/src/workload`), modelled on Asana's
  Workload: the team's week in a line with a bar, then a person a row with
  their load as a bar, red past what they have, and their tasks, late and
  not estimated, each opening the tasks it counts. frappe's filters stay;
  its grid, cards and footer stay out of sight as the report's own, so
  exports and OneAI read the same rows.

  **Planned** is the hours still to do on each person's open tasks in the
  week: a task's Expected Time less the time already logged on it (ERPNext's
  Actual Time), spread evenly over the days from its start to its due date and
  counted for the days that fall in the week, and shared equally when a task
  is given to more than one person. Work already late counts in full this
  week, since that is when it has to be done now. A task with only a due date
  is a day on it.

  **Capacity** is the person's working days in the week — not a holiday on
  their holiday list, not a day of approved leave — times HR Settings'
  **Standard Working Hours**, 8 when it is not set. Somebody with no employee
  record works the company's working days, or Monday to Friday where there is
  no holiday list.

  Hours are only as good as the Expected Time on tasks, so **Not Estimated**
  says how many of a person's tasks in the week have none: a light load with
  five unestimated tasks is not a light load.

  Only tasks the reader may see are counted. A project filter counts the tasks
  of that project and everything under it.
- `portal.py` — ERPNext's portal, reachable. A member
  of the project sees its time (`time`, each activity's hours by day) unless
  their row hides timesheets, and its public files when it lets them, as
  ERPNext's own page did. Its list
  (/project) reads the Customer's Portal Users, which Invite as User never
  filled (`invited`, Contact on_update, fills it); a customer signing in was
  sent to One's desk (`onedesk.check_app_permission` now refuses website
  users on the apps screen); and its project page (/projects) checked role
  permissions a customer never has, so refused everybody — and showed the
  team's assignees and a New Task button. The portal app's project page
  (frontend/portal, `page`) takes its place, and /projects?project=… leads to
  it: `view` checks ERPNext's own website permission (`may_see`) and shows
  progress over the tree, the end, milestones, sub-projects, tasks, the order
  and the invoices; `page` says each value as frappe formats it.

  ERPNext's portal lists a customer's projects at /project and shows one at
  /projects?project=…, to anybody listed under **Portal Users** on the
  Customer. Two things stopped any customer getting there:

  - **Invite as User** on a customer's Contact makes the login and never lists
    it under the Customer's Portal Users, which is the only thing their portal
    reads (`get_customers_suppliers`), so the customer was refused their own
    projects. `invited` lists it (Contact on_update).
  - A website user signing in was sent to One's desk, which they cannot open,
    because One's entry on the apps screen did not refuse them
    (onedesk.check_app_permission).

  And one thing that stopped a customer seeing a project once there: ERPNext's
  project page (templates/pages/projects.py) checks the reader's role
  permissions, which a customer has none of, so it refused every customer. It
  also showed who in the team each task is assigned to, and a New Task button
  that let a customer add tasks to the team's project. The portal app's
  project page takes its place, and the old address leads to it: what a
  customer asks of a project — how far
  along it is, when it ends, the milestones, the sub-projects, the work and
  its state, and their order and invoices (`view`). Nothing of the team's: no
  names, no hours, no updates.
- `templates.py` — ERPNext's Project Template, which already makes a
  project's tasks from template tasks as the project is saved. Added: **Save
  as Template** (`save_as`, with `start_of` and `days` pure), what their copy
  leaves out — milestone, expected time, checklist (`task_made`). A Projects
  Manager may keep templates (access.py `_templates`; ERPNext allowed only a
  System Manager). A template task is not assigned to its maker
  (one_task/capture.py), everybody in projects sees it (one_task/access.py),
  the Tasks rail entries leave templates out, and a new project's prefix rule
  is written before ERPNext makes its tasks (naming.py).

  ERPNext's **Project Template** is a list of template tasks — Tasks ticked
  **Is Template**, each with **Begin On (Days)** after the project starts and
  a **Duration (Days)** — and a project given one gets a task for each, dated
  from its own start, with the template's sub-tasks and dependencies between
  them (`Project.copy_from_template`). That part is theirs and stays theirs.
  What templates.py adds is what stopped anybody using it:

  - **Save as Template** (`save_as`). Building a template meant making each
    template task by hand on the Task form and then listing it on the
    template. Now a project that went well is the template: its tasks, their
    dates as days after the project's start, their lengths, sub-tasks,
    dependencies, milestones, checklists and expected time. Cancelled tasks
    are left out, and so are dependencies on tasks in other projects, since a
    template is one project.
  - **Add from Template** (`add`). ERPNext copies a template only into a new
    project with no tasks yet. A running project may take one too: its tasks
    are made by ERPNext's own copy (`create_task_from_template`,
    `dependency_mapping`), dated from the day chosen, beside the tasks it has.
  - **What ERPNext's copy leaves behind** (`task_made`). Their copy carries
    the subject, dates, priority, type and a few more, and not whether a task
    is a milestone, its expected time or its checklist; the new task takes
    them from the template task it was made from.
  - **Who may keep templates** (access.py `_templates`). ERPNext lets only a
    System Manager open one. A Projects Manager may keep them, and a Projects
    User read them.
  - **Days kept whole** (`days_kept`, Task before_validate). A template task
    never begins before the project or lasts fewer than no days, however it
    is saved.
  - **A task fits in its phase** (`held_in_phase`, Task before_validate).
    ERPNext's copy moves each task off a holiday on its own, so on some start
    days a task ends after the phase it is then put in, and ERPNext refused
    it. The phase stretches to hold it instead.
  - **A template task is nobody's work.** It is not assigned to its maker
    (one_task/capture.py) and everybody who works in projects sees it
    (one_task/access.py), since a template is for the whole team.

  A new project's Task Prefix names the tasks a template makes, because the
  naming rule is written when the project is, not after (naming.py).
- `template_view.py` — a template's tasks, drawn in its form (the
  onedesk.template_part island in frontend/src/template, mounted by
  public/js/one_project/project_template.js in the one_tasks_part field; the Tasks table
  shows only on a new template). The form's head has its Tasks, Duration and
  Projects (heads.py, template.*). `read` gives its tasks
  in the template's order with their depth and what each waits on, leaving
  out the tasks ERPNext lists on a group as what it waits on, which are only
  its own tasks. `change`, `add`, `nest`, `wait` and `remove` each save the
  task as its form would and then the template, so ERPNext's own check on it
  (every task a task waits on is in the template) runs, and the save tells
  whoever has the page open. A task put under another makes that one a group
  (ERPNext asks it of a parent), and a group left with no tasks stops being
  one. A task added under another goes after the last of its tasks, so the
  template's order reads as its tree.
- `library.py` — the presets in library/, one JSON file each: a title, what
  it is for, its place in the list (`order`) and its tasks, each with the day
  it begins on, the days it lasts and its own tasks. A phase is a milestone
  when it says so. `rows` turns a preset into the template tasks it makes
  (pure): a group begins with its first task and ends with its last, and a
  task waits on the one before it in its group when that one has ended by
  then, unless it says what it comes after. `copy` makes the workspace's own
  template the first time a preset is used, in the workspace's language
  (one/babel.py `project_template` puts every title and task in the
  translations), and returns that one after. New Project (kinds.py `make`)
  and Add from Template (templates.py `add`) take a preset as `library`.
  `drafted` makes a template OneAI drafted, once a person approves its card
  (agent.py `draft_template`, a Setup card applied by one_studio/ai_setup.py), the same
  way as a preset and as whoever approved it.
- `overview.py` — what the band answers, over the tree the reader may see:
  tasks done of all, days to the expected end (`days_left`), the money
  (money.py), overdue tasks, the next milestone, and the hours logged a week
  for twelve weeks.

  All of it is ERPNext's own: `expected_end_date`, the project's tasks, and
  the money on its documents as money.py adds it up. A project with
  sub-projects answers for the whole tree (tree.py), since the villa's
  question is about the villa, handrails included.

  How far it has got (`share`): a completed project is done, whatever its
  tasks say, since one completed with no tasks of its own has none to count.
  Otherwise it is ERPNext's own % Complete, the tree's for a project with
  sub-projects (roll_up), so the page and the lists say the same; its own
  tasks' when the page shows its Main.
- `money.py` — the page's Money view, two sides and a forecast, over the whole tree:
  each figure is the submitted lines naming a project in it, before tax, as
  ERPNext adds up a project's Billed and Purchases, with the list behind it
  (`WHERE` finds the project on the lines). Time, stock used and expense
  claims are ERPNext's totals on the project; Margin So Far counts expense
  claims, which ERPNext's own gross margin leaves out. `forecast` and
  `unbilled` are pure. `moved` (every submit and cancel) tells the open
  pages of the project and those above it to redraw. `_suppliers` is the
  Suppliers view, one card per order. ERPNext's stored totals are hidden from
  the form, not removed; the form's Costing tab keeps the Budget and the
  fields ERPNext needs (patches/costing_on_the_page.py took the rest).

  **Customer**: what they've been quoted, what they've ordered, what's been
  delivered and invoiced, and what they've paid. **Cost**: what's been ordered
  from suppliers, received and billed, what they've been paid, and the team's
  time, stock used and expense claims. Each figure opens the documents behind
  it, and the project's sub-projects are included, as the head's are.

  Every figure is ERPNext's own record added up, before tax, as ERPNext adds
  up a project's Billed and Purchases: a document's lines that name the
  project, on submitted documents. Payments are what was paid, tax included.
  Time, stock used and expense claims are the totals ERPNext keeps on the
  project. Stock used is summed again when ERPNext revalues stock after a
  back-dated entry (`restocked`).

  **The forecast** answers before the money's gone. The contract is what the
  customer ordered, or the billable time when nothing was ordered. The
  forecast cost is, for each cost type, what's been spent and what suppliers
  still have to bill on their orders, or its budget while that's more; then
  the same for the rest of the budget. A cost type over its budget shows, even
  while another is under. With no budget there's no forecast (`forecast`).
- `hours.py` — `settle` stores **Count Time By** on a new site, since a
  Single shows its default only before it's first saved. The Time view: `entries` reads the tree's Timesheet Detail
  as the reader reads timesheets, with where each stands (`state`, pure);
  `log` writes into the reader's draft timesheet for the week through
  one_task/timer.py, after the day's last entry (`after`, pure); `whose`
  finds who a timesheet is for when it has no user of its own.

  **How time is counted** (`one_time`) is asked when a project is made, beside
  its kind, which says how the customer pays. The two are separate questions:
  a fixed-price villa counts its crews' days on site, and a fixed-price
  software build counts timesheets.

  - **Timesheets**: people log hours on the project, by hand or with a task's
    timer.
  - **Attendance on Site**: the project names its site (an HRMS Shift
    Location), and each day somebody's attendance has them there is a day on
    the project (site_time.py).
  - **Not Tracked**: hours aren't counted. The page has no Time view unless
    somebody logged some anyway.

  A project made without one (by ERPNext, HR or an import) is given the
  workspace's default, **Count Time By** in Projects Settings (`fill`).
  Whether an hour is billable follows the kind (`bills_hours`): Time and
  Materials and Retainer hours are, and a Fixed Price or Internal project's
  are cost only. `billable` (Timesheet before_insert) ticks it however the
  timesheet is made, except from desk's form, where timesheet.js ticks it as
  the project is picked (`billed_hourly`) so an untick stays. `on_its_project`
  (Timesheet validate) keeps a row's task on the row's project or one under
  it. A draft counts its hours but no cost or amount (`sums`), as `count` does.

  Every hour is ERPNext's Timesheet Detail on the project or a project under
  it, read as the reader reads timesheets, so somebody who may see only their
  own sees only their own. Each entry says where it stands: a draft not yet
  submitted, not billable, still to invoice, or invoiced on a Sales Invoice.

  **Log Time** (`log`) writes an entry into the reader's draft timesheet for
  the week, the one the task timer (one_task/timer.py) writes into, so time
  logged by hand and timed by the clock end up in the same place and are
  submitted together.
- `team.py` — the Team view: members, manager, assignees and whoever logged
  time, with open and late tasks and hours; `add` and `remove` change the
  project's Members as the form does, and `show` a member's ERPNext **Hide
  Timesheets** and **View Attachments**, what they see on the portal.

  The team is ERPNext's **Members** on the project (Project User), and with
  them everyone the work names: the manager, whoever a task on the project or
  a project under it is assigned to, and whoever logged time on it. Each says
  how much is on them (open tasks, and how many are late) and how much they
  have put in (hours this month and in all), read as the reader reads tasks
  and timesheets.

  Adding or removing a member is a change to the project, made by whoever may
  change it, and saved as the form saves it, so ERPNext's own rules on members
  (the welcome mail, who sees the project in the portal) run as they do there.
- `billing.py` `invoices` — the Invoices view: Sales Invoices naming the
  tree on the invoice or a line, read as the reader reads them.
- `retainer.py` — a Retainer's months: `months` (hours used of the
  allowance, over, the month's invoice), `waiting`, `asked` (what Invoice
  Month would bill) and `invoice_month`, a draft Sales Invoice with the fee,
  the hours over at the month's average rate (`over`, `rate`, pure) and the
  month's billable time on its Time Sheets table. The month is
  `one_retainer_month` on Sales Invoice. Invoice Time refuses a retainer.

  A month is a calendar month from the one the project starts in. Each says
  how many hours were used of the allowance (`one_monthly_hours`), how many
  over, and whether it's been invoiced: a Sales Invoice for the project with
  its **Retainer Month** (`one_retainer_month`) set to the month.

  **Invoice Month** (`invoice_month`) is a draft Sales Invoice, opened unsaved
  as Invoice Time's is: one line for the month's fee, and, when the month went
  over, one for the hours over at what the month's billable hours were billed
  at on average. The month's billable time is put on the invoice's Time Sheets
  table, so submitting it marks that time invoiced (ERPNext's
  TimesheetBillingService) and Invoice Time never bills it again.
- `heads.py` — the band and the hours chart as the project's Record Head
  (one/head.py), each a measure or a chart over `overview`.
- `view.py` — the project's page (`page/project_view`): `said` gives it, in
  one call read as the reader, the head, the kind's four cards (`cards`) and
  its Overview, from overview.py, money.py, budget.py, billing.py and
  tree.py. `needs` is Needs You; `contract` is the project's Sales Order or
  the first one against it; `quotation` is its open quotation (not extra
  work) while nothing is ordered, which the first Fixed Price card shows as
  **Quoted** (`_first`). kinds.py's `add_contract` makes the contract after
  the project, as `_contract` does for the New Project dialog, in the
  customer's party account currency. `work` gives the Tasks, Board and Timeline views
  the tasks of the project and its sub-projects, the people they're assigned
  to, and the statuses and priorities to pick from; `files` and `updates`
  give the Files view and the Overview's updates. The page's body is the
  `onedesk.project` island, `frontend/src/project/ProjectPage.vue` and the
  views beside it, built from the kit in `frontend/src/kit`
  (docs/ISLANDS.md). A task is changed as desk changes it
  (`frappe.client.set_value`, `insert`, `assign_to`), and the views follow
  the Task list through desk's `list_update`. Desk keeps its head through
  `onedesk.island_page`, and the island reports the name, the status and the
  actions. `public/js/one_project/project_new.js` hands `/desk/project/<name>` to the
  page; the form is the same address with `?edit=1`, and a new project's form
  stays. The page follows the record through the kit (`follow`, desk's
  `doc_subscribe` and `doc_update`) and its money through `one_project_money`.
  OneStudio's extensions are told the project on the head
  (`oneproject.project`) and what each of Overview, Tasks, Time, Money,
  Invoices, Suppliers, Team, Files and Activity shows (`project/place.js`). The page is a shadow root desk's styles
  don't reach, so their notes and buttons are drawn by the kit's `PlaceSpot`
  as frappe-ui's Alert and Button.

  The page is `page/project_view` (public/js/project_page.js), opened at the
  project's own address. `said` gives it the head (the kind, status, health,
  the main action), the title line, the kind's four cards and its Overview.
  Everything is read from the modules that work it out already: overview.py
  (tasks, dates, hours), money.py (both sides), budget.py (cost types),
  billing.py (time not invoiced) and tree.py (sub-projects). It reads as the
  person asking and checks they may read the project.
- `public/js/one_project/project_actions.js` — Board, Schedule, Group Under New Project,
  Save as Template, Invoice Time and Post Update, for the page and the form
  alike. `public/js/one_project/project.js` is the form: those as its buttons, and
  Calendar; `public/js/one_project/project_template.js` is a template's New Project.

### What OneTask has to keep doing for projects

OneTask is everybody's; these are the promises it makes to OneProject, and each
change here that touches tasks keeps them:

- a task's people see it wherever it is, and a task in no project is its own
  people's alone (`one_task/access.py`);
- a sub-task is in its parent's project (`one_task/task.py`);
- the timer writes time against whichever project a task is in;
- My Tasks names the project a task is in — and, once there are sub-projects,
  the path to it.

### access.py

ERPNext lets only a **System Manager** open **Projects Settings**, which the
Projects list's menu opens: whether a timesheet may overlap another and
whether a sales invoice brings in its project's timesheets. A Projects
Manager keeps them. Their labels and notes are One's words
(`custom/projects_settings.json`). erpnext's Projects module has no sidebar
in One, so a kind of it no rail lists, such as Projects Settings, Activity
Type or Project Type, opens beside OneProject's rail (`one_module_heirs`,
one/outside.py) rather than the reader's first.

ERPNext keeps **Budget** to the books, so a project manager could not set a
project's budget by cost type. A Projects Manager now keeps the budgets of
projects, and only those (budget.py `kept_to_projects`): a budget against a
cost centre stays the books'.

The books read every **Project**, since they invoice its time and progress
(members.py sees to which ones).

A role that reads it already, by ERPNext's rules or the workspace's, keeps
what it has (one/roles.py `give`). Tasks and project templates are
one_task/access.py and `_templates` here.

### agreement.py

A project's contracts are ERPNext's **Contract**, with `document_type`
Project and `document_name` the project, so ERPNext's own form, statuses
(Unsigned, Active, Inactive) and daily status update all hold. `draw_up`
fills the party (the customer, or a supplier from `suppliers`: those with a
submitted purchase order on the project or those under it, and those on its
contacts), the dates and `contract_terms`: a Contract Template's wording
rendered as ERPNext's form renders it (`get_contract_template`), else, with
the customer, the project's Terms and Conditions. `contracts` lists those not
cancelled on the project and those under it with no permission check, since
whether they are signed is the project's business, and gives a route only to
whoever may read contracts. `main` is the customer's for About: the latest
signed, else the latest. `asks` adds the Needs You rows, and `_renewed` keeps
a contract quiet once a later signed one with the same party runs past it. No
grant is added. Contract stays with ERPNext's roles, because employment
contracts are Contracts too.

### activity.py

The Activity view puts the project's history beside frappe's own timeline of the project,
which keeps its comments, its emails and the changes to its fields (Project
tracks its changes, `custom/project.json`). Each row here is one of frappe's
ActivityTimeline rows (`type`, `key`, `timestamp`, `author`, `data`), with a
`kind`: `money` for documents, `work` for the rest.

A document shows when it was made, submitted and cancelled, read from the
Version frappe keeps of it, or from the document itself where its type keeps
none. Tasks added in one day are one row, as are a person's hours in a day and
the files somebody added in a day.

### buying.py

The orders for goods leave out subcontracts, which have their own card
(money.subcontract). An order for goods says how much is received and billed,
and when it's billed ahead of delivery. The Suppliers view lists them beside
the subcontracts, the project's and those under it, each opening its document
(`papers`).

Each is ERPNext's own document, naming the project on its lines (chain.py).

### contacts.py

Each person outside the company on a project is a row of its **Contacts** (Project Contact): a **Role**, the
**Supplier** or, for anyone who isn't one, the **Company**, a frappe
**Contact** with their email and phone, and a **Note**. The Team view lists
them under **Contacts**, and Suppliers lists the suppliers among them
(`contacts`). Adding one is changing the project (`save`, `remove`); the
Contact is linked to the project too, as frappe links a contact to any record,
so the project is among the contact's own links.

### terms.py

A project's `one_payment_terms` (Payment Terms Template) and `one_terms`
(Terms and Conditions), also on Project Template with `one_retention` and
`one_retention_handover`. `defaults` gives a new project the customer's own
payment terms (ERPNext's `get_payment_terms_template`: customer, then group,
then company) before the template's, then the company's. The wording is the
template's, else the company's `default_selling_terms`. `started` gives them
to a new project however it is made, before validate; the New Project dialog
sets `flags.one_terms_given`, so what it was answered stands, a blank
included. A sub-project starts with none of its own, so it bills on the job
it is part of (`of`).

`of` is what a project is billed on: its own, else the nearest project
above it with some, with the one they come from. `carried`, Invoice Time,
Invoice Month and the New Project contract all read it.

`give` puts both on a document not saved yet: the template, which ERPNext
turns into the payment schedule, a due date from it (ERPNext's
`set_missing_values` dates an invoice by the party's terms, not the ones on
it), and the wording rendered as ERPNext's form renders it.

`carried` runs before_insert on Quotation, Sales Order, Sales Invoice and
Purchase Invoice. A document made from a single order or quotation starts
with that one's terms, as ERPNext's Fetch Payment Terms from Order does. A
selling document for a project otherwise starts with the project's. A
purchase invoice made outside an order keeps ERPNext's. Payment terms someone
picked, other than the party's own default, are kept, and so is wording other
than the company default.

Bill Progress gives the invoice the order's terms before ERPNext's
`set_missing_values` (ERPNext's mapper leaves `payment_terms_template` off),
then splits the schedule for retention (progress.py `_retain`). Moving an
order's Retention Due moves the date on its submitted invoices, their
payment schedules and their Payment Ledger Entry and GL Entry rows
(progress.py `_due`), which the receivables and payables reports age by.

library.py makes the payment terms and wording a preset names
(`library_terms.json`) the first time it is copied in.

### site_time.py

HRMS's attendance says who worked and for how long, for payroll; it has no
project. ERPNext's project costing reads only timesheets. So a day on site is
written as the timesheet ERPNext expects, made from the attendance, and HR
keeps attendance as it is:

- **Attendance submitted** (`attended`): when the day was at the site of an
  open project counted by attendance (`project_at`), a Timesheet for that
  person is made and submitted. It has one row on the project, the
  attendance's working hours (or HR Settings' standard day, half of it for a
  Half Day), at Projects Settings' **Activity for Days on Site**, billable
  when the project bills hours (`hours.bills_hours`). Its cost is the person's
  Activity Cost, as any timesheet's.
- **Where they were**: one of their check-ins that day inside the site (its
  own circle, or any clock place drawn on it). With no position on any
  check-in, a shift assignment that day naming the site.
- **Attendance cancelled** (`cancelled`): its timesheet is cancelled too,
  unless it's already invoiced, which ERPNext refuses.
- A timesheet made here names its attendance (`one_attendance`), so neither is
  made twice.

A day that can't be written (a timesheet already covering those hours, say)
doesn't stop the attendance. It's logged in the Error Log for HR to see.

### Materials, `materials.py`

ERPNext adds every supplier bill line marked with a project to its
`total_purchase_cost`, and every stock issue marked with it to its
`total_consumed_material_cost`, so bars bought for a project into a store
and then issued to it were the project's twice. `OneProject` (over HRMS's
`EmployeeProject`, which already replaces ERPNext's class) takes off
`into_store`: bill lines whose goods have a live Stock Ledger Entry, on the
bill itself or on its receipt, so an item only later switched to stock
keeps its history. **Money** shows them as **Into the Store** and leaves
them out of spent, `billing.costs` doesn't rebill them, and open orders for
stock items are left out of what's committed (`money._not_stocked`).

A return is a Material Receipt of the type `Return to Store`, made by
`give_back` at the rate the project was last charged for the item, booked
by `money.issued` to the cost of goods account the issue was, with the
project, so the budget by account goes down with it; `returned` takes it
off `total_consumed_material_cost`. `stock_counted_once` sums the purchase
cost again for projects that had stock in it. A return after the issue was
rebilled to a Time and Materials customer isn't credited to them.


### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, See Every Project, is `access.py` with its
  Permission Type in `permission_type/`, a OneProject Manager's.
  `members.manages` reads it, and `access.settle` gives OneProject Manager
  once to whoever already holds Projects Manager (`_every`).
- **Setup** needs nothing (`setup.py`), **its tour** is `tour.py` over the
  project page's marks, and **OneAI's reach** is `agent.py`'s REACH and
  NOT_FOR_AI.
- **Its foot and settings** are `public/js/one_project/project_control.js`.
- **The project page** keeps OneProject's rail on a wide screen, as the task
  page keeps OneTask's; `window/frame.css` lets the page's column shrink so
  the record panel beside it stays inside the window.
