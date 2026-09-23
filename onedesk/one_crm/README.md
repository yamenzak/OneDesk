# OneCRM

Written by hand. What OneCRM does and how to use it, screen by screen. Everything
above **Under the hood** is written for the people who use OneCRM, and OneAI
reads it to answer "how do I…" questions. Under the hood is for the people who
build it.

OneCRM is where a company keeps the people and businesses it sells to: who got
in touch, what they might buy, what was said, and what happens next. It is
built on ERPNext's CRM, so every lead, deal, customer and quotation is
the same record the rest of One reads.

## Finding your way

The rail on the left has the whole of OneCRM in it:

- **Home** — the start page.
- **Lead** — somebody who got in touch, or somebody you want to reach.
- **Deal** — a sale you are working on, with what it is worth and how far it
  has got.
- **Pipeline** — every open deal on a board, one column per stage.
- **Customer** — somebody who has bought, or is about to.
- **Contact** and **Prospect** — the people, and the businesses they work for.
- **Sales**, **Campaigns**, **Setup** — one group each, opened with the arrow.
  Quotations, appointments and contracts are under Sales.

**One workspace is one company.** You are never asked which company a lead or
a deal belongs to.

**OneAI is the round button in the corner.** Open it on any page and it offers
what makes sense there. No OneAI button is ever put on a page itself.

## From a lead to a sale

A **Lead** is where a sale usually starts. From a lead, **Create** makes a
deal, a quotation, a customer or a prospect, and whatever was written on the
lead goes with it.

A **Deal** is a sale in progress. Its **Sales Stage** says how far it has got,
and a quotation made from it is linked back to it. **Deal Value** is what it is
worth; a deal priced by its items takes their total when no value is typed.

A deal is ERPNext's Opportunity under a shorter name. To call it something
else, change the rows named `one-deal-…` under **Translation**.

### Sales stages

A new workspace has six: **New**, **Qualified**, **Proposal**, **Negotiation**,
**Won** and **Lost**. Each has a **Position**, which is the order they are
listed in; a **Probability (%)**, which a deal takes when it moves there; and
an **Outcome** — Open, Won or Lost. Change them, add your own or remove them
under **Setup › Sales Stage**.

**Moving a deal to a stage sets its probability** to that stage's. Type a
different probability and it stays until the deal moves again. A won deal is
always 100% and a lost one 0%.

**Won and Lost are stages as well as statuses**, and the two always agree:

- Move a deal to a Won stage and its status becomes Converted.
- Pick a Lost stage and **Declare Lost** opens to ask why; the deal moves
  there once you have said.
- Declare it lost from the button, lose its quotation, or receive a sales
  order from its quotation, and the stage moves on its own.
- **Reopen** it, or cancel that sales order, and it goes back to the last
  stage it was in before it was won or lost.

Every move is recorded with the date, so how long a deal has sat in a stage is
known.

A deal with an event in the calendar today is left as it is. ERPNext would
reopen it every morning, won and lost ones included; One does not.

### The pipeline

**Pipeline** in the rail opens the board: one column per stage in position
order, and a card per deal with its value, probability and expected closing
date. Drag a card to another column to move the deal; its probability follows,
and a card dropped on Won converts the deal.

Under each column's name is what the deals in it are worth, and what they are
worth weighted by their probability — 50,000 at 50% counts as 25,000. Both are
in the company's currency and follow the board's filters.

**Lost is not a column.** Losing a deal asks why, which a drag cannot, so a
deal is lost from its own page with **Declare Lost**, and lost deals leave the
board.

A stage added, renamed or removed under Setup changes the board's columns.

## Setup

**Territory**, **Customer Group**, **Sales Person**, **Sales Stage**, **Lead
Source** and **CRM Settings** are in the Setup group.

## Under the hood

For the people who build OneCRM. OneAI does not read past this heading.

### What ERPNext gives, and what it leaves

ERPNext's CRM is Lead → Prospect → Opportunity → Quotation → Sales Order, with
`opportunity_from` and `quotation_to` as dynamic links to Lead, Prospect or
Customer, and the `make_*` mappers in `crm/doctype/*/mapper.py`. Status is
derived by `controllers/status_updater.py` on every save. Measured on this
checkout, the gaps a small business feels first:

- **A stage means nothing.** `Sales Stage` is a name and nothing else — no
  order, no probability, no won or lost. `probability` defaults to 100 on a
  deal at Prospecting, and status and stage run side by side unconnected.
- **No board.** The desk's Kanban takes Select fields only, and `sales_stage`
  is a Link.
- **No history.** Lead and Opportunity do not track changes, so nobody can
  say how long a deal sat in a stage, and the dashboards' "won date" is
  `modified`.
- **No next step.** A ToDo has a date and no time, nothing asks what happens
  next on an open deal, and nothing lists what is overdue.
- **Calls cannot be written down.** Every Call Log field is read-only and no
  telephony provider ships.
- **Three owners.** `lead_owner`/`opportunity_owner`, `_assign`, and Sales
  Person, which reaches a User only through Employee.
- **Two value fields.** The typed `opportunity_amount` and the items' `total`
  are never reconciled.
- **Wrong numbers.** "Open Opportunity" and "Won Opportunity" number cards
  have no status filter; Campaign and Lead Owner Efficiency miss anything that
  went through a Prospect; every chart filters on a Company.
- **A daily job that reopens the closed.** `crm.utils.open_leads_opportunities
  _based_on_todays_event` sets status Open on any lead or opportunity with an
  Event today, converted and lost ones included. And nothing ever sets
  Replied, so `auto_close_opportunity` closes nothing.
- **Clutter.** Series on every form, Fax, Middle Name, `request_type`, a
  `customer` field that depends on a field that no longer exists, Supplier
  Quotation and RFQ buttons on a sales record, the source hidden in a
  collapsed Analytics section behind a Selling Settings switch.

### The plan

Stages in order. Each is a commit or a few, each leaves the site working, and
none edits erpnext.

1. **A stage means something.** *Done* — `stages.py`. Sales Stage gets an
   order, a probability and an outcome (open, won, lost). A deal's probability
   follows its stage unless somebody types one; a won stage converts it and a
   lost one asks why.
   Stage changes are recorded with frappe's Milestone Tracker, so "days in this
   stage" is a fact. The daily reopening job is stopped. A small business gets
   six stages it recognises instead of eight from a sales textbook.
2. **The board.** *Done* — `board.py`, `deal.py`. Deals by stage, dragged
   from one to the next, each column showing its count, its value and its
   weighted value. Opportunity is called Deal, by Translation rows.
3. **The next step.** Every open lead and deal carries what happens next
   and when. Home is *my day*: overdue, today, coming up, and the deals with no
   next step at all.
4. **The record answers first.** A lead and a deal open on what people
   open them for — value, stage and how long it has been there, the last
   contact, the next step, where it came from — with notes, calls written down
   by hand, mail and comments on one timeline.
5. **Capture.** A web form that makes a lead, mail to an inbox that makes a
   lead, duplicates caught on email, phone and business name, leads shared out
   by an Assignment Rule, and the first reply on a lead measured.
6. **Measured.** A forecast by expected month weighted by stage, won and lost
   with one list of reasons, which sources turn into sales, and the number
   cards counting what they say they count.
7. **Screen by screen.** Every group in the rail opened with data in it and
   fixed: fields nobody fills, Company off every filter, names not IDs, and who
   may see and change what.
8. **OneAI in OneCRM.** A business card or an email signature becomes a lead
   card; a deal summarised with a suggested next step; a follow-up drafted from
   the timeline; call notes turned into a note and a next step; why deals are
   lost; which deals have gone quiet.
9. **The README is the manual.** Everything above Under the hood describes
   what is built.
