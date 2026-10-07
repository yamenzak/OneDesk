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

- **Home** — *my day*: what is due and what has no next step, and four
  figures on the pipeline.
- **Lead** — somebody who got in touch, or somebody you want to reach.
- **Deal** — a sale you are working on, with what it is worth and how far it
  has got.
- **Pipeline** — every open deal on a board, one column per stage.
- **Customer** — somebody who has bought, or is about to.
- **Prospect** — a business you want to sell to. Its people are contacts, in
  One's **Address Book** with every other app's.
- **Sales**, **Campaigns**, **Setup** — one group each, opened with the arrow.
  Quotations, sales orders, appointments, contracts and the four sales reports
  are under Sales. A sales order is what a won deal becomes: OneInventory
  delivers it and OneBook invoices it.

**Contract** under Sales lists what customers sign, ERPNext's own Contract:
whether each is signed (**Unsigned**, **Active**, or **Inactive** once it has
ended), when it ends, and the project it is for. Open one to record who signed
it and when, then submit it. A project's contract is drawn up from the
project's page with **Draw Up Contract**.

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

### How leads come in

A lead can be made three ways:

- **At the desk**, from the Lead list or **New Lead** on Home.
- **From the website.** The **Get in Touch** form at `/get-in-touch` asks for a
  name, business, email, mobile and a message, and makes a lead with its
  source set to Website and the message kept on it. Change the form under
  **Setup › Get in Touch Form**; link to it from your own website.
- **From an inbox.** OneIntake reads the workspace's mail, and an enquiry
  from somebody new comes with a lead ready to make. Mail from somebody who
  is already a lead is linked to their lead instead.

A lead from the website or an inbox belongs to nobody at first. It waits on
Home under **Unclaimed Leads** until somebody presses **Take This Lead**, or an
**Assignment Rule** shares it out: set one up under **Setup › Lead Assignment**
(round robin or by load) and the person it picks becomes the Lead Owner. A
Sales Manager keeps these rules. A rule of theirs is on a lead or a deal, and
says which ones it takes by comparing the record's fields with plain values,
`utm_source == "Website"`, never by code.

**Somebody who is already a lead is not made twice.** At the desk, a second
lead with the same email is refused with a link to the first. From the website
it is made but marked **Possible Duplicate Of** the first, and a lead whose
phone number or business name matches another lead or a customer is marked the
same way. The page says so at the top and offers **Merge Into …**, which moves
its comments, mail, calls and deals across and deletes it, or **Not a
Duplicate**. Phone numbers match however they were typed: +971 50 123 4567
and 050-1234567 are one number.

**The first reply is timed.** A lead's page shows **Waiting For a Reply** and
for how long until the first mail is sent or call is made to them, and then
**First Reply** and how long it took.

### The next step

Every lead and deal has a **Next Step** — what you will do, such as "Call Rana
about the quote" — and **Next Step Due**, when. At that time the owner (Lead
Owner or Deal Owner) gets a notification. A deal nobody owns belongs to
whoever made it, or to its lead's owner.

When it is done, press **Next Step Done** on the lead or deal. It writes
"Done: …" on the timeline, then asks what comes next; leave it empty if nothing
does. **Set Next Step** does the same when there is none yet. Every change to
a lead or deal, the next step included, is kept in its history.

The Lead and Deal lists are sorted by Next Step Due, so the ones with no next
step come first and the rest in the order they are due. A step whose time has
passed is shown in red. The pipeline board shows each deal's next step on its
card.
Your own next steps are also on **OneCalendar**, at the time they are due,
under Deal Next Steps and Lead Next Steps.

### A lead's and a deal's page

The band under the name answers what the page is usually opened for, before
anything is clicked:

- on a deal — **Deal Value** and its probability, the **stage** and how long it
  has been there beside how long deals usually stay there (amber once it is
  longer, and more than a day), the **Next Step** (red once overdue), the
  **Last Call** or **Last Email**, when it **Closes** (red once past), its
  latest **Quotation**, and where it came from;
- on a lead — when it **Came In**, **Waiting For a Reply** or how long the
  **First Reply** took, the Next Step, the last contact, the **Deals** made
  from it, and where it came from.

A lead or deal nobody owns yet offers **Take This Lead** (or Deal), which
makes it yours.

A lead or deal that is closed — converted, won or lost — shows no next step
and no waiting.

Each answer that comes from another record opens it.

**Log a Call** in the sidebar writes a call down: outgoing or incoming,
answered, no answer or busy, how long, and what was said. It goes on the
timeline beside the mail and the comments, and counts as the last contact.

**Everything said is on one timeline**, under Activities: comments, calls, mail
sent and received, stage changes and every edit. Write a note in the comment
box there. ERPNext's separate Notes are comments now, and a deal made from a
lead brings the lead's comments and mail with it (CRM Settings).

### Home

Home is your day, counting only your own leads and deals that are still open:

- **Deals Due** and **Leads Due** — a next step due today or already overdue.
- **Unplanned Deals** and **Unplanned Leads** — nothing planned next.
- **Unclaimed Leads** — new leads nobody has taken yet, everybody's to see.
- **New Lead** and **Pipeline**, the two places most days start.

Each count opens the list it counts.

### Reports and figures

Under Home's **My Day** is **The Pipeline**: four figures, each opening the
report behind it.

- **Pipeline Value** — what the open deals are worth, leaving out the ones on
  hold.
- **Weighted Pipeline** — the same, each deal counted at its probability.
- **Won This Month** — what was won since the first of the month.
- **Win Rate (90 Days)** — of the deals won or lost in the last 90 days, the
  share that was won.

Four reports, in the **Sales** group:

- **Deal Forecast** — the open deals, except those on hold, by the month they
  are expected to close, with their value, their weighted value, and what was
  actually won in each month. Deals whose closing date has passed are one row,
  **Overdue**, and deals with no closing date another, so nothing is left out.
- **Won and Lost** — deals won and lost, their value, and the win rate, grouped
  by **Month**, **Deal Owner**, **Source** or **Lost Reason**. A deal lost for two
  reasons counts under both.
- **Lead Sources** — for each source, how many leads came in, how many were
  replied to and how fast, how many became deals, and how many were won. Leads
  with no source are counted as **Not Recorded**.
- **How Long Deals Take** — how long deals stay in each stage and take to be
  won; see Sales stages below.

**A deal is won or lost on the day it reached a Won or Lost stage**, not the
last day anybody edited it. Everything above counts from that day.

**One list of reasons a deal is lost.** A new workspace has seven — Price,
Went With a Competitor, No Budget, No Decision, Timing, Not a Fit and Other —
on deals and on quotations alike. A deal lost because its quotation was lost
takes the quotation's reasons, so Won and Lost reads them from one place.

### Sales stages

A new workspace has seven: **New**, **Qualified**, **Proposal**,
**Negotiation**, **On Hold**, **Won** and **Lost**. Each has a **Position**,
which is the order they are listed in; a **Probability (%)**, which a deal
takes when it moves there; and an **Outcome** — Open, On Hold, Won or Lost.
Change them, add your own or remove them under **Setup › Sales Stage**.

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

**On Hold is for a deal that is neither moving nor lost** — the money is not
signed off, the building is not ready. It stays open and keeps its next step,
so give it one that says when to look again. It is left out of the Pipeline
Value, the Weighted Pipeline, the Deal Forecast, and OneAI's deals that have
gone quiet. Move it back to any stage when it starts again.

Every move is recorded with the date, so how long a deal has sat in a stage is
known, and so is how long deals usually sit there: the middle of the stays
that ended in the last year, once there are three. **How Long Deals Take**, in
the Sales group, has it for every stage — how many deals passed through, the
usual and the longest stay, how many are in it now and how many of those have
been there longer than usual — and a last row, **To Win**, from a deal coming
in to its being won. Filter it by dates and by deal owner.

A deal with an event in the calendar today is left as it is. ERPNext would
reopen it every morning, won and lost ones included; One does not.

### The pipeline

**Pipeline** in the rail opens the board: one column per stage in position
order, and a card per deal with its value and its next step. Drag a card to
another column to move the deal; its probability follows, and a card dropped
on Won converts the deal.

Under each column's name is what the deals in it are worth, and what they are
worth weighted by their probability — 50,000 at 50% counts as 25,000. Both are
in the company's currency and follow the board's filters.

**On Hold** has its own column, with an orange dot, and counts no weighted
value: its deals are not expected to close while they wait.

The Pipeline is the one board of deals. erpnext ships another, of deals by
status, and One takes it out after every install and update, since most of
its columns are set by quotations and orders rather than moved.

**Lost is not a column.** Losing a deal asks why, which a drag cannot, so a
deal is lost from its own page with **Declare Lost**, and lost deals leave the
board.

A stage added, renamed or removed under Setup changes the board's columns.

### OneAI in OneCRM

Open OneAI on a page and it offers what makes sense there. Anything it would
add or change comes back as a card; nothing happens until somebody approves
it, and they approve it as themselves.

- **On a deal**: *Where does this deal stand?* reads its value, stage, next
  step and its whole history — mail, calls, comments and stage moves — and
  says it in a few lines. *Suggest the next step* puts a next step and a day
  on a card. *Write up a call* asks what was said on the phone and suggests it
  as a call on the deal, and the next step it leads to as a second card.
  *Draft a follow-up* writes a short email from what was said last.
- **On a lead**: *Draft a reply* answers what they asked in the Get in Touch
  form; *Suggest the next step* and *Write up a call* work as on a deal.
- **On the Lead list**: *Add leads from business cards* reads each card
  dropped on it and suggests a lead per person, with the card attached. *Add a
  lead from a signature* does the same from a pasted email signature. Somebody
  whose email is already on a lead is not suggested again — OneAI says which
  lead they are — and a matching phone number or business name is marked as a
  possible duplicate, as the web form would have marked it. *Which leads are
  waiting on us?* lists open leads nobody has spoken to for a week and with
  nothing planned.
- **On the Deal list and Home**: *Which deals have gone quiet?* lists open
  deals nobody has spoken to for two weeks and with nothing planned, or with a
  next step whose day has passed. *Why are we losing deals?* groups the year's
  lost deals by the reasons picked and what was written, with what they were
  worth.

A call OneAI writes up is the same call **Log a Call** makes, so it counts as
the last contact and times the first reply. Anybody in sales may approve one.

## Setup

**Sales Person**, **Sales Stage**, **Lead Assignment**, **Get in Touch Form**
and **CRM Settings** are in the Setup group. Territories, customer groups,
industries, market segments, lead sources and lost reasons are in One's
**Masters**. **Campaigns** has Campaign, Email Campaign, Email Group
and Campaign Efficiency. The workspace's mailboxes are in Settings › Mail.

A Sales Manager runs Email Campaign, Email Group, Lead Source and Lead
Assignment, and a Sales User reads them. ERPNext gives them only to its
System Manager and a Newsletter Manager nobody is given here (`access.py`).

**Forms carry what a small business fills in.** A lead asks for a name, job
title, email and phone numbers, the business, its industry and territory, and
where it came from; a deal for who it is with, its owner, stage, closing date,
value and source. Middle name, gender, salutation, fax, lead type, request
type, revenue, headcount, market segment and the copied address of the
business are hidden, and a record never asks which naming series. **Source**
and **Campaign** sit open at the foot of both forms. A lead or deal linked
from another record shows its name, not its ID.

A deal has no **Close**: a deal that will not happen is lost, with a reason.

**Who may do what.** Everybody in sales sees every lead and deal; a team that
wants each person to see only their own sets User Permissions. A **Sales
User** makes and edits leads, deals and prospects; deleting a lead or a deal,
and merging leads, is a **Sales Manager's**. Both may log and correct calls.
Change any of it under Role Permissions; One does not change it back.

## Connections

- **From OneIntake**: An enquiry from somebody new that reaches a mailbox OneAI reads becomes a new lead. A customer's order that arrives by mail becomes a draft Sales Order.
- **From OneMail**: Mail sent to a lead or a deal, and the replies to it, are on its timeline. The first mail sent to a lead counts as its first reply.
- **From OneBook**: A customer's page shows what they owe, what is overdue, what was billed this year and their last invoice.
- **From OneProject**: Draw Up Contract on a project makes the customer's Contract for it, listed under Sales.
- **To OneProject**: A quotation for a customer with one open Fixed Price project waiting for a price is put on that project. Once the customer orders it, its Sales Order is the project's contract, and an order for extra work becomes a sub-project.
- **To OneInventory**: A Sales Order is delivered with Create › Delivery Note. What open orders promise is taken off each item's Free to Sell.
- **To OneBook**: A Sales Order, or the delivery made from it, is invoiced with Create › Sales Invoice.
- **To OneCalendar**: Your next steps on leads and deals are on your calendar at the time they are due.

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
3. **The next step.** *Done* — `next.py`, `public/js/next_step.js`. Every
   open lead and deal carries what happens next and when. Home is *my day*:
   what is due, and what has no next step at all.
4. **The record answers first.** *Done* — `record.py`, and the band and
   Take This Lead as a Record Head (`heads.py`); `public/js/crm_record.js`
   keeps Log a Call and the duplicate. A lead and a deal open on what people
   open them for — value, stage and how long it has been there, the last
   contact, the next step, where it came from — with notes, calls written down
   by hand, mail and comments on one timeline.
5. **Capture.** *Done* — `capture.py`, `web_form/get_in_touch`. A web form that
   makes a lead, mail to an inbox that makes a lead, duplicates caught on email,
   phone and business name, leads shared out by an Assignment Rule, and the
   first reply on a lead measured.
6. **Measured.** *Done* — `measure.py`, `report/`, `number_card/`. A
   forecast by expected month weighted by stage, won and lost with one list of
   reasons, which sources turn into sales, and number cards counting what they
   say they count. ERPNext's two wrong cards stay wrong on its own CRM
   dashboard, which OneCRM does not link to; Home has its own four.
7. **Screen by screen.** *Done* — `custom/*.json`, `crm_record.js`, `access.py`.
   Every group in the rail opened with data in it and fixed: fields nobody
   fills, Company off every filter, names not IDs, and who may see and change
   what.
8. **OneAI in OneCRM.** *Done* — `ai.py`. Four reads (`deal_facts`,
   `lead_facts`, `gone_quiet`, `why_we_lose`) and three cards (`add_lead`,
   `plan_next_step`, `write_up_call`), with the panel's suggestions per page.
   A business card is matched to its file by `one_ai/files.uploaded`, which
   OneHR's CVs use too. A written-up call is `record.call`, the dialog's own
   Call Log, and `access.py` lets sales make one, because a card is applied
   with the approver's own permissions.
9. **The README is the manual.** *Done* — read against the running site
   after stage 11: every button, band, rail group and report above Under the
   hood is what is there.

### What the old OneCRM had that this does not

OneApp's OneCRM, the single-page app this replaces, was read after stage 8
and deleted. It is at OneApp `65dacfd9` for anybody who needs a line of it.
Four ideas in it are worth having here, and each is a stage:

10. **On hold.** *Done* — `stages.HOLD`, `measure.alive`, the patch
    `add_on_hold` for a workspace seeded before it. A seventh stage whose
    outcome is On Hold, for the deal that is neither moving nor lost — the money
    is not signed off, the building is not ready. Without it such a deal sits in
    Negotiation and the pipeline and the forecast count it. It stays open, keeps
    its column on the board, and is left out of the pipeline's value, the
    weighted value and the forecast.
11. **How long deals take.** *Done* — `measure.stays`, `usual`, `stuck`, the
    report `how_long_deals_take`, and `usual`/`long` in `record.overview`.
    From the Milestones stage 1 already writes: the
    usual days a deal spends in each stage, and from New to Won. The old app
    kept a stage log of its own for this; Milestone is that log. On a deal's
    page the stage reads "for 12 days" beside the usual 5, so a stuck deal
    shows as one.
12. **Next steps on a calendar.** *Done in OneCalendar* — `one_crm/calendar.py`,
    two layers. *Moved to OneCalendar.* A next step is one
    thing in a person's week beside their tasks, meetings and leave, and that
    week is OneCalendar's; a Deal calendar and a Lead calendar now would be two
    more places to look, replaced when it comes. It needs only to read
    `one_next_on` off Lead and Opportunity. What it was to be: the Deal and Lead
    lists opening as a calendar on the next step's day, the reader's own by
    default, as the old app's Follow-ups screen did.
13. **A promise to answer.** A lead answered within a working day, counted in
    working hours with the holiday list, and Home listing the leads that are
    late. The old app built this itself, seven hundred lines, because it
    refused a stored Python condition; ERPNext's own Service Level Agreement
    does it on any doctype, Lead included, and an agreement with no condition
    needs none. What that one lacks is the old app's restart when the lead
    writes back — a first answer is measured, a later one is not.
    *Moved to OneMail*, because the hard part is noticing a reply. Found
    while starting it: ERPNext's agreement never sees a mail reply to a lead.
    frappe stamps `first_responded_on` only on a doctype that also has
    `first_response_time`, which the agreement does not add to Lead, and
    ERPNext's own reply branch waits for that stamp. So `capture.replied`,
    which already notices the first mail and the first call, is what writes
    it — replacing `one_first_reply_at` — and the agreement needs a holiday
    list, which a new site has only after its setup wizard.

Left behind, with the reason: its own stage, stage-log and call doctypes
(Sales Stage with three fields, Milestone and Call Log do the same); a chart
on every screen (the reports and Home's four figures answer the questions);
renaming Deal per workspace (a Translation row does it); an Organisations
screen (a Prospect is one, and not every party is a business).

### The Contract list

ERPNext's own list read **Draft** for an unsigned contract, since a draft is
never asked its status, and showed each contract's whole wording.
`public/js/contract_list.js` extends ERPNext's list settings: a draft shows
its status, a cancelled one says so, and the project a contract is for reads
by its name. `custom/contract.json` shows the end date in place of the
wording, the fulfilment status and the time it was signed. No grant is
added: contracts stay with ERPNext's roles.

### access.py

- A **Sales User** could delete a deal but not a lead. A deal carries its
  stage history, its calls and its reasons for being lost, so deleting one is
  a Sales Manager's, as deleting a lead already was.
- A **Sales User** could only read a Prospect, so the person who makes a lead
  into a business could not write the business down. They may now create and
  edit one.
- Only a **System Manager** could make a Call Log. Sales people log calls by
  hand from a lead's or deal's page, and OneAI suggests one from what they
  said about a call, which they approve as themselves. They may now read,
  make and correct one.
- Only a **System Manager** could open what the Campaigns and Setup groups
  link to: Email Campaign, Email Group, Lead Source and Lead Assignment. A
  Sales Manager now runs them and a Sales User reads them (`GIVEN`).
- A **Sales Manager** keeps the Assignment Rules that share out leads and
  deals, and only those: a rule of theirs is on a lead or a deal, and decides
  by comparing the record's own fields with plain values, `utm_source ==
  "Website"`, never by code (`assignment_rule`).

Everybody in sales still sees every lead and deal: a small team shares its
pipeline, and one that does not can say so with User Permissions.

frappe's `update_permission_property` copies a doctype's standard permissions
into Custom DocPerm before changing one, which is what the Role Permissions
Manager does. Written once: a doctype that already has Custom DocPerm rows has
been decided by the workspace, and is left alone.

### ai.py

The rules are OneAI's: a read runs as the person asking, and anything that
would write is a card somebody approves. What `ai.py` adds is what sales
knows — that a deal is an Opportunity, what a deal's history is made of, when
a deal has gone quiet, and when a person is already a lead.

**The model reads the history; the record keeps it.** `deal_facts` and
`lead_facts` hand over the page's own answers (`record.overview`) and the
timeline — mail, calls, comments and stage moves, oldest first — so a summary,
a next step or a follow-up is written from what was said rather than from the
fields. Nothing the model writes becomes history until somebody approves it.

**A call written up is a Call Log**, the same record the Log a Call dialog
makes, so it counts as the last time anybody spoke to them and times the first
reply. A next step is its own card: one card per suggestion, and a person may
want the call and not the step.

**A business card becomes a lead only if the person is not one already.**
`add_lead` runs capture's own match: the same email is refused and said, a
matching phone or business name is written on the card as a possible
duplicate, as the web form would have flagged it.

### board.py

The desk's Kanban reads and writes its column field on the server whatever the
field's type; only its New Board dialog insists on a Select. So the board is
made in `board.py` rather than from that dialog. A stage added, renamed or
removed changes the board, which is why the columns are derived rather than a
fixture.

Dragging a deal saves it, so a move runs `stages.before_validate` like any
other: the probability follows and Won converts. A Lost stage is an archived
column, so nothing can be dropped on it: losing a deal asks why, and a drop
cannot, so the server refused it and the board left the card where it fell.

### capture.py

The inbox's Email Account appends to Lead. Whichever way a lead comes in:

- **Mail** from an address that is already a lead is added to that lead.
  frappe's mail receiver makes a new lead when no thread matches, and if the
  insert raises DuplicateEntryError it looks the sender up instead; raising
  exactly that is how the mail finds its lead.
- **The web form** cannot tell a visitor "you already exist", so the lead is
  made and marked as a possible duplicate, with Merge and Not a Duplicate on
  its page.
- **The desk** is told, as ERPNext's own email check told it; ERPNext's check
  is switched off at install because it refused the web form and the inbox as
  well.

A phone number or a business name already on a lead or a customer is never a
refusal, only a flag: two people share a switchboard, and "Ali" is a name.

A lead from the web form or the inbox belongs to nobody until somebody takes it
or an Assignment Rule shares it out. It is on Home as Unclaimed until then.

`defaults` sets, on install: a deal made from a lead carries the lead's
comments and mail; ERPNext's own refusal of a second lead with the same email
is off, and capture's own rules decide instead; the Source (UTM) section is
shown.

### deal.py

ERPNext works out `base_opportunity_amount` only in the form's script, so a
deal made by import, the API or OneAI is worth nothing in the company's
currency, and every total that reads it. And a deal priced by its items keeps
Opportunity Amount empty beside a filled Total.

A deal has one owner, Deal Owner, and a deal nobody owns is on nobody's Home:
it takes its lead's owner, or whoever made it.

### heads.py

A deal answers what it is worth and how likely, how long it has been in its
stage against how long deals usually stay there, what comes next and when,
when they were last in touch, when it should close, its quotation and where
it came from. A lead answers when it came in, whether and how fast it was
answered, what comes next, when they were last in touch and the deals made
from it.

A time since ("yesterday") is sent as the moment itself (`when`), and the
desk says it with frappe's own `prettyDate` when it draws the band, so it
reads as every other time on the desk does.

### measure.py

**When a deal was won or lost** is the Milestone that recorded it reaching a
stage whose outcome is Won or Lost (`stages.py`). ERPNext's dashboards use
`modified`, which is the last time anybody touched the deal: a deal won in
March and corrected in May was "won in May". Every report and card here reads
`closed()` instead.

**How long a deal stays in a stage** is read off the same Milestones: each one
is a deal arriving in a stage, and it left when the next one was written
(`stays`). What is usual for a stage is the middle of the finished stays in it
over the last year — the median, so one deal forgotten for a year does not make
every other deal look quick.

The four figures on Home are Custom number cards, so each is worked out in
`measure.py` through the reader's own permissions and opens the report behind
it.

### next.py

Two fields on the record rather than a ToDo: a ToDo on a record marks the
record assigned to whoever holds it, and closing it unassigns them, so the
step and the owner would be one thing. On the record, a missing next step is
a filter, a column and a count on Home, and the step shows on the board card.

`done` writes the step that was done on the timeline before setting the next
one, so the history of a deal is what was done, not only what was planned.

### record.py

A deal is opened to find out what it is worth, how far it has got and for how
long, what happens next, when anybody last spoke to them, and when it should
close. A lead is opened for how long it has waited, where it came from, what
happens next and what it has turned into.

A call written down by hand is a Call Log, erpnext's own record of a call, so
it is on the timeline beside the mail and the comments, and a later telephony
integration writes the same record.

### report/deal_forecast/deal_forecast.py

A deal counts in the month it is expected to close, at its value and at its
value weighted by probability. A deal whose expected date has passed is not
dropped into a month that is over: it is its own row, Overdue, because that
is the answer somebody opened the forecast to find. So is a deal with no date
at all. Won is by the day the deal was won (`measure.closed`), not the day it
was expected.

### stages.py

ERPNext's `Sales Stage` is a name and nothing else, so an opportunity's stage
and its status are two answers to one question that nothing keeps in step.
In `stages.py` a stage has a position, a probability and an outcome, and the
outcome is what ties the two together: a stage whose outcome is Won is a
converted opportunity, one whose outcome is Lost is a lost one, and the stage
follows when ERPNext's own verbs — Declare Lost, a quotation lost, a sales
order — change the status instead.

A stage whose outcome is **On Hold** is for the deal that is neither moving
nor lost: the money is not signed off, the building is not ready. It is still
open, so its status is left alone, but it is not in the pipeline: the value,
the weighted value and the forecast leave it out (`measure.alive`).

Stage changes are recorded by frappe's Milestone Tracker, a fixture, so the
day an opportunity reached its stage is a row rather than a guess.
