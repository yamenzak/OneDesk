# Costs and Budget

**Money** on the project's page shows the money for the project and its
sub-projects together. Click a row to see the documents behind it.

- **Forecast**, by the project's kind:
  - **Fixed Price**: the **Contract** (what the customer ordered), the
    **Budget**, the **Forecast Cost**, the **Forecast Margin** and the
    **Margin So Far** (invoiced less spent).
  - **Time and Materials**, under **So Far**: what's **Earned** (invoiced, and
    time and costs not invoiced yet), the **Cost**, the **Margin So Far**
    (earned less cost), and the **Budget** if it has one. With an order,
    what was **Ordered** and the **Forecast Margin** against it.
  - **Retainer**, under **So Far**: the **Monthly Fee**, what's **Invoiced**,
    the **Cost** and the **Margin So Far**.
  - **Internal**: the **Budget**, what's **Spent**, the **Forecast Cost** and
    what's **Left**.
- **Customer**: what they've been **Quoted**, what they've **Ordered**, what's
  been **Delivered** and **Invoiced**, what's **Not Invoiced Yet** on Time and
  Materials, and what they've **Paid**, each with a bar against what they
  ordered.
- **Cost**: what's been **Ordered** from suppliers, **Received** and
  **Billed**, what they've been **Paid**, and the team's own **Time**,
  **Stock Used**, **Expense Claims** and **Journal Entries** (such as payroll
  or depreciation charged to the project). **Into the Store** is what was
  billed for the project but went onto a store's shelf; it isn't spent until
  it's issued (see Materials).

A row still at nothing isn't shown. Amounts are before tax, except payments,
and in the company's currency. Everyone who reads the project sees its
totals, as the project's form shows what's billed. A row opens its
documents only for someone who may read them.
**Paid** is what's been paid on the project's invoices or bills, however it
was paid, with advances on its orders not yet set against a bill. The page
updates as documents are submitted.

The forecast cost is, for each cost type, what's been spent and what
suppliers still have to bill on their orders, or its budget while that's
more; then the same for the rest of the budget. So an order that takes a
cost type past its budget shows the day it's placed, even while another cost
type is under. With no budget there's no forecast.

Set the **Budget** to what you expect the whole project to cost: the pencil
on **Budget** under **Money**. The same dialog takes the
**Time Budget**, what the team's own hours may cost, and the **Planned
Hours** when the tasks don't plan any; the **+** on **Logged** and **Time
Cost** under **Time** opens it too. A cost type can't hold the time, as
timesheets are booked to no account, so the time has its own budget.
Each can be changed whenever the plan changes.

**Time is priced for you.** Every hour on a timesheet (the timer on a task
writes one) is costed and billed at the rate set for that person and activity
under **Setup › Activity Cost**, or at the activity's own rate under
**Activity Type** if the person has none. Once the timesheet is submitted,
the hours count in the project's **Cost**, and billable ones in what there is
to bill. Time on a project with a customer is billable unless someone unticks
it.

**Bills from suppliers count too.** When OneAI reads a supplier's bill
that names an open project, the bill it drafts is for that project, and so is
each line, so the project's **Cost** includes it once it's submitted. A bill
naming two projects, or none, is left for you to set.

**Invoice Time** (in **Actions**, on a project with a customer) creates an
invoice for every billable hour on the project not yet invoiced, with one line
per activity, so the customer reads *Execution, 7 hours* and *Planning, 2
hours*. It asks which item to bill the time as, remembering the last one, and
opens the invoice unsaved for you to check. Submitting it marks the hours as
invoiced, and the project's **Billed** goes up. A sub-project's time is
invoiced from the sub-project.

## Materials

Things you keep in stock (an item with **Maintain Stock** ticked) are the
project's cost when they leave the store for it, not when they're bought,
even when the order was placed for the project. Everything else, such as a
curtain wall bought in or a subcontract, is the project's cost when it's
billed, as always.

1. **Buy into the store.** Order for the project if you like; the goods are
   received into a warehouse and wait there. They show under **Cost** as
   **Into the Store**, not as spent.
2. **Issue Stock** on **Money**: what goes to the project, from which
   warehouse, how many, and in what unit. A profile kept in metres can be
   issued by the bar. The project pays for it at what the store holds it at.
3. **Return to Store** on **Money**: what comes back. A 6 m bar issued, 2 m
   cut and 4 m returned, and the project pays for 2 m. It comes back at what
   the project was charged for it.

What's left in the store after a job is there for the next one, which pays
for it when it's issued. An offcut nobody returns was used up, and the
project paid for it.

## Budget by Cost Type

Split the budget by **cost type** under **Cost Types** on **Money**: one
for each kind of cost you track, such as labour, materials, subcontracts or
equipment (each is an expense account in OneBook). Each shows its
**Budget**, what's **Committed** on supplier orders not yet billed, what's
been **Spent**, and what's **Left**, over the project and its sub-projects.
**Time** is the team's own hours against the **Time Budget**: timesheets
are booked to no account, so the time has a line of its own, and the
project's **Budget** is the cost types and the Time Budget added up.
**Other** is the rest of the budget and cost, *not in a cost type*: a
sub-project's budget without cost types, and cost booked to accounts none
of them use.

**How a cost lands in a cost type**: by the account it's booked to, with
the project on it. A supplier's bill (**Record Bill** on **Suppliers**, or
an order's bill) books to each item's expense account; an expense claim to
its claim type's account; **Issue Stock** to the item's expense account, or
else the company's cost of goods, never to Stock Adjustment. Click a cost
type to see what was booked to it, each opening its document, and
**Change Budget** there; click **Time** to open **Timesheet**.

**Add Cost Type** asks for the cost type, its budget, and what happens
**Over Budget**: **Warn** shows a warning on an order or expense that takes
it over, and **Stop** refuses it. Click a cost type to change its budget or
remove it. One only a sub-project budgets for adds this project's own. Once
a project has cost types, its **Budget** is their total.

On a Fixed Price project's **Overview**, **Budget** adds up each cost type
over the project and its sub-projects. A cost type counts only what's spent
and ordered on the projects that budget for it, as the warning does.
**Other** is everything else: budget not split into cost types, and cost
outside them, such as the team's time. The arrow on the heading opens
**Money**.

Cost types are set by whoever looks after the books (Accounts Manager).
Everyone who can see the project sees them.
