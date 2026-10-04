# The project

The project is OneProject's main record type. This is its design: what a
project has to answer for every kind of business that runs one, and how One
builds it on ERPNext. It's built in the stages at the end, one commit each.

## Who runs projects in One

| Business | A project is | What they open it for |
|---|---|---|
| Contractor (fit-out, MEP, joinery, glazing) | A job for a client, with subcontractors and suppliers under it | What the client owes, what we owe the subcontractors, what's left to spend, the margin at the end |
| Agency, consultancy | A retainer or a fixed-price engagement | Hours against the budget, what's billed, what's left |
| IT services, software | A delivery with milestones | Milestones, time, what's invoiced |
| Events, production | A one-off with many suppliers | Every supplier's quote, order and bill against the budget |
| Internal (office move, rollout) | Work with a budget and no customer | Spent and committed against the budget |

They share two questions: **is it on time** (the task side, which the page
already answers) and **is it making money** (the money side, which it
doesn't). This design is about the second.

## What's wrong today

- **Quotation and Request for Quotation can't name a project**, and a
  Material Request only names one on each line. A job's first documents are
  outside it.
- **Nothing carries the project from one document to the next.** Someone
  types it on each document, so most go without it.
- **Costing adds up four things**: time, supplier invoices, materials and
  invoices to the customer. It ignores what's been ordered from suppliers
  and not yet billed, so a project looks fine until the subcontractors'
  invoices arrive.
- **The margin is on what's been billed**, so it answers after the money's
  gone. A contractor watches the forecast: the contract against everything
  spent, committed and still budgeted.
- **There are no subcontracts.** A subcontractor bills a share of their
  order each month, minus retention and minus any advance. ERPNext's
  "Subcontracting" is something else, a factory making items from materials
  you send.

## The design

### 1. The project is on every document, and carried

Every document about the job names its project, from the first quote to the
last payment:

- Customer side: Quotation → Sales Order → Delivery Note → Sales Invoice →
  Payment.
- Supplier side: Material Request → Request for Quotation → Supplier
  Quotation → Purchase Order → Purchase Receipt → Purchase Invoice → Payment.
- Also: timesheets, expense claims, stock used, journal lines.

The project is filled in once and carried forward. A document made from
another takes its project. A line with no project takes the document's,
and a document with no project takes its lines' when they all name the same
one. **+** under the project's Connections starts any of them already on the
project.

### 2. Costing has two sides

**Customer**: what they've been quoted, what they've ordered (the
contract), what's been delivered, what's been invoiced, and what they've
paid.

**Cost**: what's committed to suppliers (their orders), what's been
received, what they've billed, and what's been paid, plus the team's time,
stock used and expense claims.

Each figure opens the documents behind it. The project's sub-projects are
included, as the head's figures are.

**Forecast margin** is the contract (the orders, or what's billable if
there are none) minus the forecast cost. The forecast cost is what's been
spent, plus orders not yet billed, plus the budget still unspent. The head
shows it next to the margin so far.

### 3. Subcontracts

A **subcontract** is a Purchase Order on the project, one per supplier per
package of work. The project's **Suppliers** section lists them: supplier,
order value, billed so far, retention held, paid, and left to bill.

- **Bill Progress** on a subcontract asks how far the work has got, as a
  share of the order. It drafts the supplier's invoice for the part not yet
  billed.
- **Retention** is a share set on the order (often 5 to 10%). Each invoice
  splits its payment in two: the main part due as usual, and the retention
  due on release. The retention is held until it's released, at handover or
  after the defects period, by setting that date.
- **Advances** are payments against the order before any invoice. ERPNext
  sets them off against the invoices, and the section shows what's still to
  recover.
- **Extra work** gets an order of its own, so the original stays readable.

### 4. The customer side is the same

The contract is the Sales Order. **Bill Progress** on it drafts the customer
invoice for the part not yet billed, with the customer's retention held the
same way. The customer's own extra work is a sub-project (already built).

### 5. Budget by cost type

A project's budget is split by cost type (labour, materials, subcontract,
equipment, or whatever accounts the workspace uses), as ERPNext's Budget
against a project. ERPNext then warns, or stops, a Purchase Order that would
take a cost type over budget. Costing shows each cost type: budget,
committed, spent, left.

### 6. Told, asked, written down

- **Notifications**: a cost type goes over budget; a progress bill is
  drafted for the person who approves it.
- **OneAI** reads the money as it reads the rest of the project: "Where is
  the money going?", "What's left to pay the subcontractors?"
- **The README** says all of it in plain words, and the AI Addendum says
  what OneAI reads.

## Stages

1. **The project on every document**: Project on Quotation, Request for
   Quotation and Material Request, carried along both chains, lines and
   document kept in agreement.
2. **Costing in two sides**: the customer and cost figures, each opening its
   documents, and the forecast margin on Costing and in the head.
3. **Subcontracts**: the Suppliers section, Bill Progress, retention through
   the payment schedule, advances.
4. **The customer contract**: Bill Progress on the Sales Order, the
   customer's retention.
5. **Budget by cost type**: ERPNext's Budget against the project, on
   Costing.
6. **Notifications, OneAI, README, legal and translations** for all of it.
