# OneCRM

Written by hand. What OneCRM does and how to use it, screen by screen. Everything
above **Under the hood** is written for the people who use OneCRM, and OneAI
reads it to answer "how do I…" questions. Under the hood is for the people who
build it.

OneCRM is where a company keeps the people and businesses it sells to: who got
in touch, what they might buy, what was said, and what happens next. Every
lead, opportunity, customer and quotation is the same record the rest of One
reads.

## Finding your way

The rail on the left has the whole of OneCRM in it:

- **Home** — how selling is going, what needs you today, and everything in
  OneCRM with what it is for.
- **Lead** — somebody who got in touch, or somebody you want to reach.
- **Opportunity** — a sale you are working on, with what it is worth and how far it
  has got.
- **Pipeline** — every open opportunity on a board, one column per stage.
- **Customer** — somebody who has bought, or is about to.
- **Prospect** — a business you want to sell to. Its people are contacts, in
  One's **Address Book** with every other app's.
- **Selling**, **Campaign** and **Support** — one group each, opened with the
  arrow. Quotations, sales orders, appointments and contracts are under
  Selling. Support is what comes after the sale: issues, warranty claims,
  maintenance schedules and the visits that keep them.
- **Reports** and **Setup** — open their part of Home: every sales report,
  and every setting and list OneCRM keeps, each with what it is for.

A **Sales Order** is what a won opportunity becomes: OneInventory delivers it
and OneBook invoices it. At its top it says its project and total, the day
what is still to go out was promised (in red once that day has passed), and
how much has been delivered and billed.

**Contract** under Selling lists what customers sign: whether each is signed
(**Unsigned**, **Active**, or **Inactive** once it has ended), when it ends,
and the project it is for. Open one to record who signed it and when, then
submit it. A project's contracts are drawn up from the
project's page with **Draw Up Contract**.

**One workspace is one company.** You are never asked which company a lead or
an opportunity belongs to.

**OneAI is the round button in the corner.** Open it on any page and it offers
what makes sense there. No OneAI button is ever put on a page itself.

## From a lead to a sale

A **Lead** is where a sale usually starts. From a lead, **Create** makes an
opportunity, a quotation, a customer or a prospect, and whatever was written on the
lead goes with it.

An **Opportunity** is a sale in progress. Its **Sales Stage** says how far it has got,
and a quotation made from it is linked back to it. **Opportunity Amount** is what it is
worth; an opportunity priced by its items takes their total when no value is typed.

Every screen says Opportunity, so Ctrl+K finds it by the word on the rail.

### Converting a lead

Open the lead and use **Create**:

- **Opportunity** — they want something you can price. The opportunity
  takes the lead's details, comments and mail, and the lead's status
  becomes Opportunity.
- **Quotation** — straight to a price, without an opportunity.
- **Customer** — they have bought, or are about to. The lead's status
  becomes **Converted**, and it shows no next step from then on.
- **Prospect** — the business behind the lead, when you want to sell to the
  business rather than one person (see Customers and prospects below).

An opportunity's own **Create › Customer** turns whoever it is with into a
customer, and **Create › Quotation** prices it.

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
**Assignment Rule** shares it out: set one up under **Setup › Assignment Rule**
(round robin or by load) and the person it picks becomes the Lead Owner. A
Sales Manager keeps these rules. A rule of theirs is on a lead or an opportunity, and
says which ones it takes by comparing the record's fields with plain values,
`utm_source == "Website"`, never by code.

**Somebody who is already a lead is not made twice.** At the desk, a second
lead with the same email is refused with a link to the first. From the website
it is made but marked **Possible Duplicate Of** the first, and a lead whose
phone number or business name matches another lead or a customer is marked the
same way. The page says so at the top and offers **Merge Into …**, which moves
its comments, mail, calls and opportunities across and deletes it, or **Not a
Duplicate**. Phone numbers match however they were typed: +971 50 123 4567
and 050-1234567 are one number.

**The first reply is timed.** A lead's page shows **Waiting For a Reply** and
for how long until the first mail is sent or call is made to them, and then
**First Reply** and how long it took.

### The next step

Every lead and opportunity has a **Next Step** — what you will do, such as "Call Rana
about the quote" — and **Next Step Due**, when. At that time the owner (Lead
Owner or Opportunity Owner) gets the **Next Step Due** notification, which each
person sets under You › Notifications. An opportunity nobody owns belongs to
whoever made it, or to its lead's owner.

**Being told.** Besides Next Step Due:

- **Given to You**: somebody else makes you the owner of a lead or an
  opportunity. A lead an Assignment Rule gives you is told as an assignment.
- **They Replied**: mail in on your lead or opportunity, whichever mailbox
  it reached.
- **Contract Expiring**: an active contract two weeks from its end date, to
  whoever made it and the user it names.
- **New Lead Waiting**: a lead from the website or the inbox that nobody owns,
  to sales, until somebody takes it from Home.
- **Quotation Running Out**: an open quotation three days from its last day,
  to whoever made it and the opportunity's owner; after it the customer can
  no longer accept it.
- **Quotation Accepted** and **Declined**, on the portal or through a link, to
  whoever made the quotation and the opportunity's owner, or the sales
  managers when neither can sign in.

When it is done, press **Next Step Done** on the lead or opportunity. It writes
"Done: …" on the timeline, then asks what comes next; leave it empty if nothing
does. **Set Next Step** does the same when there is none yet. Every change to
a lead or opportunity, the next step included, is kept in its history.

The Lead and Opportunity lists open on the ones still being worked, each
status in its own colour, and are sorted by Next Step Due, so the ones with no next
step come first and the rest in the order they are due. A step whose time has
passed is shown in red. The pipeline board shows each opportunity's next step on its
card.
Your own next steps are also on **OneCalendar**, at the time they are due,
under Opportunity Next Steps and Lead Next Steps.

### A lead's and an opportunity's page

An opportunity's page says first where the sale stands, in a line and a
track: quoted, ordered, billed and paid, as the quotation, the sales order and
the sales invoices made from it say. The line says what the track cannot:
lost and why, on hold, a quotation still with them or run out, or won and
how much of it is still owed — red once some of that is late. Won and lost
opportunities say the day they were won or lost rather than a time in a stage.

The band under the name answers what the page is usually opened for, before
anything is clicked:

- on an opportunity — **Opportunity Amount** and its probability, the **stage** and how long it
  has been there beside how long opportunities usually stay there (amber once it is
  longer, and more than a day), the **Next Step** (red once overdue), the
  **Last Call** or **Last Email**, when it **Closes** (red once past), its
  latest **Quotation**, and where it came from;
- on a lead — when it **Came In**, **Waiting For a Reply** or how long the
  **First Reply** took, the Next Step, the last contact, the **Opportunities** made
  from it, and where it came from.

A lead or opportunity nobody owns yet offers **Take This Lead** (or Opportunity), which
makes it yours.

A lead or opportunity that is closed — converted, won or lost — shows no next step
and no waiting.

Each answer that comes from another record opens it.

**Log a Call** in the sidebar writes a call down: outgoing or incoming,
answered, no answer or busy, how long, and what was said. It goes on the
timeline beside the mail and the comments, and counts as the last contact.

**Everything said is on one timeline**, under Activities: comments, calls, mail
sent and received, stage changes and every edit. Write a note in the comment
box there; notes are comments. An opportunity made from a lead brings the
lead's comments and mail with it (CRM Settings).

### Home

Home opens on six figures, each opening the report behind it:

- **Leads This Month** — how many came in, against last month.
- **Pipeline Value** — what the open opportunities are worth, leaving out the
  ones on hold.
- **Weighted Pipeline** — the same, each opportunity counted at its probability.
- **Won This Month** — what was won since the first of the month, with the
  months before it.
- **Win Rate (90 Days)** — of the opportunities won or lost in the last 90
  days, the share that was won.
- **Average Won Value** — what an opportunity won in the last year was worth.

Under them, **Overview** tells how selling is going, in three parts:

- **Selling** — the **Funnel Conversion**: of the opportunities of the last
  twelve months, how many got a quotation, a sales order, a sales invoice, and
  were paid. Then the **Sales Trend**, leads, opportunities and wins month by
  month, and **Forecasted Revenue**, what was won each month beside what the
  open opportunities should bring in the months they are expected to close,
  each at its probability.
- **Sales Pipeline** — what the open opportunities are worth in each stage,
  On Hold in amber; each owner's pipeline beside what they won; and why
  opportunities were lost.
- **Source** — where leads came from and how many became opportunities, what
  was won from each source, and the pipeline by territory.

Click a part of a chart to open what it counts.

**Today** is your day, counting only your own leads and opportunities that
are still open:

- **Opportunities Due** and **Leads Due** — a next step due today or already
  overdue.
- **Past Expected Closing Date** — open opportunities whose day to close has
  gone.
- **Unclaimed Leads** — new leads nobody has taken yet, everybody's to see.
- **Quotations Expiring** — open quotations whose Valid Till is this week.
- **No Next Step** — nothing planned next.
- **Left as Drafts** — quotations and sales orders you started more than a
  day ago.

**Everything**, **Reports** and **Setup** list every screen, report and
setting of OneCRM, each with a line on what it is for, and a search.

### Reports

Four of the reports under **Reports** are OneCRM's own:

- **Opportunity Forecast** — the open opportunities, except those on hold, by the month they
  are expected to close, with their value, their weighted value, and what was
  actually won in each month. Opportunities whose closing date has passed are one row,
  **Overdue**, and opportunities with no closing date another, so nothing is left out.
- **Won and Lost** — opportunities won and lost, their value, and the win rate, grouped
  by **Month**, **Opportunity Owner**, **Source** or **Lost Reason**. An opportunity lost for two
  reasons counts under both.
- **Lead Sources** — for each source, how many leads came in, how many were
  replied to and how fast, how many became opportunities, and how many were won. Leads
  with no source are counted as **Not Recorded**.
- **Time in Sales Stage** — how long opportunities stay in each stage and take to be
  won; see Sales stages below.

**An opportunity is won or lost on the day it reached a Won or Lost stage**, not the
last day anybody edited it. Everything above counts from that day.

**One list of reasons an opportunity is lost.** A new workspace has seven — Price,
Went With a Competitor, No Budget, No Decision, Timing, Not a Fit and Other —
on opportunities and on quotations alike. An opportunity lost because its quotation was lost
takes the quotation's reasons, so Won and Lost reads them from one place.

### Sales stages

A new workspace has seven: **New**, **Qualified**, **Proposal**,
**Negotiation**, **On Hold**, **Won** and **Lost**. Each has a **Position**,
which is the order they are listed in; a **Probability (%)**, which an opportunity
takes when it moves there; and an **Outcome** — Open, On Hold, Won or Lost.
Change them, add your own or remove them under **Setup › Sales Stage**.

**Moving an opportunity to a stage sets its probability** to that stage's. Type a
different probability and it stays until the opportunity moves again. A won opportunity is
always 100% and a lost one 0%.

**Won and Lost are stages as well as statuses**, and the two always agree:

- Move an opportunity to a Won stage and its status becomes Converted.
- Pick a Lost stage and **Declare Lost** opens to ask why; the opportunity moves
  there once you have said.
- Declare it lost from the button, lose its quotation, or receive a sales
  order from its quotation, and the stage moves on its own.
- **Reopen** it, or cancel that sales order, and it goes back to the last
  stage it was in before it was won or lost.

**On Hold is for an opportunity that is neither moving nor lost** — the money is not
signed off, the building is not ready. It stays open and keeps its next step,
so give it one that says when to look again. It is left out of the Pipeline
Value, the Weighted Pipeline, the Opportunity Forecast, and OneAI's opportunities that have
gone quiet. Move it back to any stage when it starts again.

Every move is recorded with the date, so how long an opportunity has sat in a stage is
known, and so is how long opportunities usually sit there: the middle of the stays
that ended in the last year, once there are three. **Time in Sales Stage**, under
Reports, has it for every stage — how many opportunities passed through, the
usual and the longest stay, how many are in it now and how many of those have
been there longer than usual — and a last row, **To Win**, from an opportunity coming
in to its being won. Filter it by dates and by Opportunity Owner.

An event in the calendar never reopens an opportunity or a lead: won, lost
and converted ones stay as they are.

### The pipeline

**Pipeline** in the rail opens the board: one column per stage in position
order, and a card per opportunity with its value and its next step. Drag a card to
another column to move the opportunity; its probability follows, and a card dropped
on Won converts the opportunity.

Under each column's name is what the opportunities in it are worth, and what they are
worth weighted by their probability — 50,000 at 50% counts as 25,000. Both are
in the company's currency and follow the board's filters.

**On Hold** has its own column, with an orange dot, and counts no weighted
value: its opportunities are not expected to close while they wait.

The Pipeline is the one board of opportunities.

**Lost is not a column.** Losing an opportunity asks why, which a drag cannot, so an
opportunity is lost from its own page with **Declare Lost**, and lost opportunities leave the
board.

A stage added, renamed or removed under Setup changes the board's columns.

### Quoting and taking the order

1. On the opportunity, **Create › Quotation**. Add the items with their
   quantity and rate, and set **Valid Till**, the last day the customer may
   accept it.
2. **Submit** it, then **Print** (One Quotation, with room for both sides to
   sign) or send it.
3. To let the customer answer online, press **Portal** on the quotation and
   **Send Link** to one of their contacts. They open it without an account
   and accept or decline it once. Accepting asks the date they need it by
   and their own reference.
4. An acceptance makes a draft **Sales Order** from the quotation and tells
   whoever made the quotation and the opportunity's owner (**Quotation
   Accepted**). Check the order and **Submit** it. A quotation the customer
   agreed to some other way becomes an order with **Create › Sales Order**.
5. A declined quotation is marked lost with their reason (**Quotation
   Declined**). To mark one lost yourself, **Set as Lost** asks why.

The opportunity's track then moves on to ordered, billed and paid on its
own. OneInventory delivers the order (**Create › Delivery Note**) and
OneBook invoices it (**Create › Sales Invoice**). A quotation still open
three days before its Valid Till is told as **Quotation Running Out**.

### OneAI in OneCRM

Open OneAI on a page and it offers what makes sense there. Anything it would
add or change comes back as a card; nothing happens until somebody approves
it, and they approve it as themselves.

- **On an opportunity**: *Where does this opportunity stand?* reads its value, stage, next
  step and its whole history — mail, calls, comments and stage moves — and
  says it in a few lines. *Suggest the next step* puts a next step and a day
  on a card. *Write up a call* asks what was said on the phone and suggests it
  as a call on the opportunity, and the next step it leads to as a second card.
  *Draft a follow-up* writes a short email from what was said last.
- **On a lead**: *Draft a reply* answers what they asked in the Get in Touch
  form; *Suggest the next step* and *Write up a call* work as on an opportunity.
- **On the Lead list**: *Add leads from business cards* reads each card
  dropped on it and suggests a lead per person, with the card attached. *Add a
  lead from a signature* does the same from a pasted email signature. Somebody
  whose email is already on a lead is not suggested again — OneAI says which
  lead they are — and a matching phone number or business name is marked as a
  possible duplicate, as the web form would have marked it. *Which leads are
  waiting on us?* lists open leads nobody has spoken to for a week and with
  nothing planned.
- **On Home**: *Add leads from business cards*, as on the Lead list, and
  the two below.
- **On the Opportunity list and Home**: *Which opportunities have gone quiet?* lists open
  opportunities nobody has spoken to for two weeks and with nothing planned, or with a
  next step whose day has passed. *Why are we losing opportunities?* groups the year's
  lost opportunities by the reasons picked and what was written, with what they were
  worth.

A call OneAI writes up is the same call **Log a Call** makes, so it counts as
the last contact and times the first reply. Anybody in sales may approve one.

## Customers and prospects

A **Customer** is a business or person who buys from you. Their page says
what they owe and how much of it is late, what they were billed this year,
their last invoice, their open orders, and their open opportunities with
what they are worth. **Print** gives their Statement of Account. Customers
are kept here and used by OneBook, OneInventory and OneProject alike.

A **Prospect** is a business you want to sell to before it has bought
anything. Its page gathers its leads and opportunities in one place. Its
people are contacts in One's **Address Book**.

To let a customer's contact sign in and see their own quotations, orders and
invoices, open the contact and choose **Portal › Invite to Portal**. A Sales
Manager or the workspace administrator may invite.

## Appointments and campaigns

An **Appointment**, under Selling, is a meeting booked with a lead or a
customer: who, when (**Scheduled Time**) and their details. It goes on the
calendar of whoever booked it. When customers may book one themselves is set
under **Setup › Appointment Booking Settings**.

Under **Campaign** in the rail:

- **Campaign** — a name for a push, such as a trade show or an advert. Pick
  it in **Campaign** at the foot of a lead or an opportunity, and **Campaign
  Efficiency** under Reports says what each one brought in. Its **Campaign
  Schedules** list the mails to send, each an Email Template and a number of
  days after the start.
- **Email Campaign** — sends a campaign's mails to one lead, contact or
  **Email Group**, from its **Start Date**.
- **Email Group** — a mailing list of addresses.

## Support: issues, warranty claims and maintenance

**Support** in the rail is the service desk. An **Issue** is a
customer's complaint or question until it is resolved, timed against the
service level agreement. A **Warranty Claim** is something sold that broke;
**Make Maintenance Visit** on it sends somebody. A **Maintenance Schedule**
promises a customer visits over a year, and each **Maintenance Visit**
records the work done; a visit prints as a **Service Report** the customer
signs, and a schedule as a **Maintenance Plan**. Issue's own reports are
under Reports' Support.

## Setup

**Setup** in the rail opens Home's Setup: **CRM Settings**, **Selling
Settings**, **Get in Touch Form**, **Sales Stage**, **Sales Person**,
**Assignment Rule**, the lists a lead and an opportunity are sorted by —
**Lead Source**, **Opportunity Lost Reason**, **Territory**, **Customer Group**,
**Industry Type**, **Market Segment** — and the prices and terms a quotation
carries, among them a **Promotional Scheme** and the **Party Specific Items**
a customer is offered. **Support** has Support Settings, the **Service Level
Agreement**, Issue Type and Issue Priority; **Telephony** the call types and
who answers which line when. The lists are kept in One's **Masters**.
**Campaign** in the rail has Campaign, Email Campaign and Email Group;
Campaign Efficiency is under Reports.
The workspace's mailboxes are in Settings › Mail.

A Sales Manager runs Email Campaign, Email Group, Lead Source and Assignment
Rule, and a Sales User reads them.

### Forms, and who may do what

**Forms carry what a small business fills in.** A lead asks for a name, job
title, email and phone numbers, the business, its industry and territory, and
where it came from; an opportunity for who it is with, its owner, stage, closing date,
value and source. Middle name, gender, salutation, fax, lead type, request
type, revenue, headcount, market segment and the copied address of the
business are hidden, and a record never asks which naming series. **Source**
and **Campaign** sit open at the foot of both forms. A lead or opportunity linked
from another record shows its name, not its ID.

An opportunity has no **Close**: an opportunity that will not happen is lost, with a reason.

**Who may do what.** Everybody in sales sees every lead and opportunity; a team that
wants each person to see only their own sets User Permissions. A **Sales
User** makes and edits leads, opportunities and prospects; deleting a lead or an opportunity,
and merging leads, is a **Sales Manager's**. Both may log and correct calls.
Change any of it under Role Permissions; One does not change it back.

## Connections

- **From OneIntake**: An enquiry from somebody new that reaches a mailbox OneAI reads becomes a new lead. A customer's order that arrives by mail becomes a draft Sales Order.
- **From OneMail**: Mail sent to a lead or an opportunity, and the replies to it, are on its timeline. The first mail sent to a lead counts as its first reply.
- **From OneBook**: A customer's page shows what they owe, what is overdue, what was billed this year and their last invoice. An opportunity says how much of what was won is billed and paid, and what is still owed.
- **From OneProject**: New Quotation and Quote Extra Work on a project start the customer's quotation on it, and Make Order orders the one open quotation. Add Contract makes the Sales Order for a contract agreed without one. Draw Up Contract on a project makes a Contract for it with its customer or one of its suppliers, listed under Sales. The contract says its project, when it was signed and when it ends at the top, and prints as One Contract, with both sides to sign. An opportunity says the project its quote went to, or the customer's one open project.
- **To OneProject**: A quotation for a customer with one open project is put on that project, however it is made. Once the customer orders it, its Sales Order is the project's contract, and an order for extra work becomes a sub-project.
- **To OneInventory**: A Sales Order is delivered with Create › Delivery Note. What open orders promise is taken off each item's Free to Sell, and the order says at the top how much has gone out.
- **To OneBook**: A Sales Order, or the delivery made from it, is invoiced with Create › Sales Invoice. A customer's page counts their open opportunities and what they are worth, opening them.
- **To OneCalendar**: Your next steps on leads and opportunities are on your calendar at the time they are due. An Appointment booked with a lead or a customer is a meeting on your own calendar.

## Under the hood

For the people who build OneCRM. OneAI does not read past this heading.

### What ERPNext gives, and what it leaves

ERPNext's CRM is Lead → Prospect → Opportunity → Quotation → Sales Order, with
`opportunity_from` and `quotation_to` as dynamic links to Lead, Prospect or
Customer, and the `make_*` mappers in `crm/doctype/*/mapper.py`. Status is
derived by `controllers/status_updater.py` on every save. Measured on this
checkout, the gaps a small business feels first:

- **A stage means nothing.** `Sales Stage` is a name and nothing else — no
  order, no probability, no won or lost. `probability` defaults to 100 on an
  opportunity at Prospecting, and status and stage run side by side unconnected.
- **No board.** The desk's Kanban takes Select fields only, and `sales_stage`
  is a Link.
- **No history.** Lead and Opportunity do not track changes, so nobody can
  say how long an opportunity sat in a stage, and the dashboards' "won date" is
  `modified`.
- **No next step.** A ToDo has a date and no time, nothing asks what happens
  next on an open opportunity, and nothing lists what is overdue.
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
   order, a probability and an outcome (open, won, lost). An opportunity's probability
   follows its stage unless somebody types one; a won stage converts it and a
   lost one asks why.
   Stage changes are recorded with frappe's Milestone Tracker, so "days in this
   stage" is a fact. The daily reopening job is stopped. A small business gets
   six stages it recognises instead of eight from a sales textbook.
2. **The board.** *Done* — `board.py`, `deal.py`. Opportunities by stage, dragged
   from one to the next, each column showing its count, its value and its
   weighted value. Opportunity was called Deal by Translation rows until
   OneCRM was held to ERPNext's names (`patches/opportunity_again`).
3. **The next step.** *Done* — `next.py`, `public/js/next_step.js`. Every
   open lead and opportunity carries what happens next and when. Home is *my day*:
   what is due, and what has no next step at all.
4. **The record answers first.** *Done* — `record.py`, and the band and
   Take This Lead as a Record Head (`heads.py`); `public/js/crm_record.js`
   keeps Log a Call and the duplicate. A lead and an opportunity open on what people
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
8. **OneAI in OneCRM.** *Done* — `ai.py`. Three reads (`crm_facts`,
   for a deal or a lead, `gone_quiet`, `why_we_lose`) and three cards (`add_lead`,
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
    outcome is On Hold, for the opportunity that is neither moving nor lost — the money
    is not signed off, the building is not ready. Without it such an opportunity sits in
    Negotiation and the pipeline and the forecast count it. It stays open, keeps
    its column on the board, and is left out of the pipeline's value, the
    weighted value and the forecast.
11. **How long opportunities take.** *Done* — `measure.stays`, `usual`, `stuck`, the
    report `time_in_sales_stage`, and `usual`/`long` in `record.overview`.
    From the Milestones stage 1 already writes: the
    usual days an opportunity spends in each stage, and from New to Won. The old app
    kept a stage log of its own for this; Milestone is that log. On an opportunity's
    page the stage reads "for 12 days" beside the usual 5, so a stuck opportunity
    shows as one.
12. **Next steps on a calendar.** *Done in OneCalendar* — `one_crm/calendar.py`,
    two layers. *Moved to OneCalendar.* A next step is one
    thing in a person's week beside their tasks, meetings and leave, and that
    week is OneCalendar's; a Opportunity calendar and a Lead calendar now would be two
    more places to look, replaced when it comes. It needs only to read
    `one_next_on` off Lead and Opportunity. What it was to be: the Opportunity and Lead
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

After Frappe CRM was read (commit c3e54ac), two more:

14. **ERPNext's names.** *Done* — `patches/opportunity_again`. The Translation
    rows that called an Opportunity a Deal are gone, and with them the word
    on every screen.
15. **Home tells the story.** *Done* — `page/onecrm`, `home.py`, `story.py`,
    `chain.py`. The workspace and its four number cards gave way to a page
    like OneBook's, with Frappe CRM's dashboard and a funnel that follows a
    sale to its payment.

Left behind, with the reason: its own stage, stage-log and call doctypes
(Sales Stage with three fields, Milestone and Call Log do the same); a chart
on every screen (the reports and Home's four figures answer the questions);
renaming Opportunity per workspace (a Translation row does it, and One
keeps ERPNext's name); an Organisations
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

- A **Sales User** could delete an opportunity but not a lead. An opportunity carries its
  stage history, its calls and its reasons for being lost, so deleting one is
  a Sales Manager's, as deleting a lead already was.
- A **Sales User** could only read a Prospect, so the person who makes a lead
  into a business could not write the business down. They may now create and
  edit one.
- Only a **System Manager** could make a Call Log. Sales people log calls by
  hand from a lead's or opportunity's page, and OneAI suggests one from what they
  said about a call, which they approve as themselves. They may now read,
  make and correct one.
- Only a **System Manager** could open what the Campaign group and Setup
  link to: Email Campaign, Email Group, Lead Source and Assignment Rule. A
  Sales Manager now runs them and a Sales User reads them (`GIVEN`).
- ERPNext gives its service desk to a **Support Team** and a **Maintenance
  User** People never hands out, and its telephony and Party Specific
  Items to the System Manager. Sales now works issues, warranty
  claims, maintenance schedules and visits, and the Sales Manager keeps
  their settings and lists (`SUPPORT`, `SUPPORT_LISTS`, `GIVEN`). Issue's
  four reports are opened to both through frappe's Custom Role
  (`roles.open_report`).
- A **Sales Manager** keeps the Assignment Rules that share out leads and
  opportunities, and only those: a rule of theirs is on a lead or an opportunity, and decides
  by comparing the record's own fields with plain values, `utm_source ==
  "Website"`, never by code (`assignment_rule`).

Everybody in sales still sees every lead and opportunity: a small team shares its
pipeline, and one that does not can say so with User Permissions.

frappe's `update_permission_property` copies a doctype's standard permissions
into Custom DocPerm before changing one, which is what the Role Permissions
Manager does. Written once: a doctype that already has Custom DocPerm rows has
been decided by the workspace, and is left alone.

### ai.py

The rules are OneAI's: a read runs as the person asking, and anything that
would write is a card somebody approves. What `ai.py` adds is what sales
knows — that an opportunity is an Opportunity, what an opportunity's history is made of, when
an opportunity has gone quiet, and when a person is already a lead.

**The model reads the history; the record keeps it.** `crm_facts`, for a
deal or a lead, hands over the page's own answers (`record.overview`) and the
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

Dragging an opportunity saves it, so a move runs `stages.before_validate` like any
other: the probability follows and Won converts. A Lost stage is an archived
column, so nothing can be dropped on it: losing an opportunity asks why, and a drop
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

`defaults` sets, on install: an opportunity made from a lead carries the lead's
comments and mail; ERPNext's own refusal of a second lead with the same email
is off, and capture's own rules decide instead; the Source (UTM) section is
shown.

### chain.py

ERPNext links each paper of a sale to the one before it and nothing back: a
Quotation names its opportunity, a Sales Order Item its quotation
(`prevdoc_docname`), a Sales Invoice Item its order. So nothing on an
opportunity knows what it became. `follow` walks the chain forward for many
opportunities at once, each paper as the reader may see it, and `reached`
says how far one got: a submitted quotation, order and invoice, and Paid once
every invoice is. Home's funnel counts it; Frappe CRM's own deal stops at its
quotations, because it has no orders or invoices of its own to follow.

### print_format/

Quotations and sales orders print from frappe's print format builder's own
pieces, written by `scripts/print_formats.py` from the same parts as the
Tax Invoice: One Quotation (prepared for, valid until, both sides to sign)
and One Sales Order (bill to, ship to when it's elsewhere, what's been paid
ahead, the bank to pay into), each with Classic, Bordered and with Images
versions in place of ERPNext's, and One Proforma Invoice, the order as the
invoice it will become. ERPNext's own Proforma Invoice record prints its
order through the format Selling Settings names, so One's is put there
(`print_blocks.py` `_proforma`): it says the proforma's number and date and,
for a proforma by amount, leaves out the quantities and rates, as ERPNext's
does. ERPNext's own are turned off
(`one/print_blocks.py` `REPLACES`). A sales order names the account to pay
into as an invoice does (**Pay Into**, `one_book/paper.py`). A contract (its
terms in full, what it requires and by when, both sides to sign), a
maintenance plan (what's maintained, how often, each visit and who did it)
and a service report (each item seen to and the work done, the customer's
feedback) print the same way, and so does an installation note (each item
with its serial numbers and the delivery it came on, the customer to accept
it); its lines keep the item's name (`one_item_name`) for it. A call type prints as
its name, so nothing OneCRM submits falls back to frappe's Standard.

### deal.py

ERPNext works out `base_opportunity_amount` only in the form's script, so an
opportunity made by import, the API or OneAI is worth nothing in the company's
currency, and every total that reads it. And an opportunity priced by its items keeps
Opportunity Amount empty beside a filled Total.

An opportunity has one owner, Opportunity Owner, and an opportunity nobody owns is on nobody's Home:
it takes its lead's owner, or whoever made it.

### heads.py

An opportunity answers what it is worth and how likely, how long it has been in its
stage against how long opportunities usually stay there, what comes next and when,
when they were last in touch, when it should close, its quotation and where
it came from. A lead answers when it came in, whether and how fast it was
answered, what comes next, when they were last in touch and the opportunities made
from it.

A time since ("yesterday") is sent as the moment itself (`when`), and the
desk says it with frappe's own `prettyDate` when it draws the band, so it
reads as every other time on the desk does.

### home.py

What needs the reader today, and the directory behind Everything, Reports and
Setup: OneBook's `home.py` laid over sales. A due step is asked to be set as
well as due, since frappe compares an empty date as the first day there is
and would count every lead with no step as overdue. Each row of the
directory is called what ERPNext calls what it opens, a filtered list as
ERPNext's own sidebar calls it.

### measure.py

**When an opportunity was won or lost** is the Milestone that recorded it reaching a
stage whose outcome is Won or Lost (`stages.py`). ERPNext's dashboards use
`modified`, which is the last time anybody touched the opportunity: an opportunity won in
March and corrected in May was "won in May". Every report and card here reads
`closed()` instead.

**How long an opportunity stays in a stage** is read off the same Milestones: each one
is an opportunity arriving in a stage, and it left when the next one was written
(`stays`). What is usual for a stage is the middle of the finished stays in it
over the last year — the median, so one opportunity forgotten for a year does not make
every other opportunity look quick.

The figures on Home are worked out in `story.py` from `measure.py`, through
the reader's own permissions.

### next.py

Two fields on the record rather than a ToDo: a ToDo on a record marks the
record assigned to whoever holds it, and closing it unassigns them, so the
step and the owner would be one thing. On the record, a missing next step is
a filter, a column and a count on Home, and the step shows on the board card.

`done` writes the step that was done on the timeline before setting the next
one, so the history of an opportunity is what was done, not only what was planned.

### record.py

An opportunity is opened to find out what it is worth, how far it has got and for how
long, what happens next, when anybody last spoke to them, and when it should
close. A lead is opened for how long it has waited, where it came from, what
happens next and what it has turned into.

A call written down by hand is a Call Log, erpnext's own record of a call, so
it is on the timeline beside the mail and the comments, and a later telephony
integration writes the same record.

### report/opportunity_forecast/opportunity_forecast.py

An opportunity counts in the month it is expected to close, at its value and at its
value weighted by probability. An opportunity whose expected date has passed is not
dropped into a month that is over: it is its own row, Overdue, because that
is the answer somebody opened the forecast to find. So is an opportunity with no date
at all. Won is by the day the opportunity was won (`measure.closed`), not the day it
was expected.

### legal.py

What the agreements say because of OneCRM: the Privacy Policy that it keeps
leads from the form and the inbox and compares them by email, phone and
business; the Data Processing Addendum that the form's visitors and the email
campaigns' recipients are the organisation's to answer for; the AI Addendum
what OneAI reads of a sale.

### stages.py

ERPNext's `Sales Stage` is a name and nothing else, so an opportunity's stage
and its status are two answers to one question that nothing keeps in step.
In `stages.py` a stage has a position, a probability and an outcome, and the
outcome is what ties the two together: a stage whose outcome is Won is a
converted opportunity, one whose outcome is Lost is a lost one, and the stage
follows when ERPNext's own verbs — Declare Lost, a quotation lost, a sales
order — change the status instead.

A stage whose outcome is **On Hold** is for the opportunity that is neither moving
nor lost: the money is not signed off, the building is not ready. It is still
open, so its status is left alone, but it is not in the pipeline: the value,
the weighted value and the forecast leave it out (`measure.alive`).

Stage changes are recorded by frappe's Milestone Tracker, a fixture, so the
day an opportunity reached its stage is a row rather than a guess.

### story.py

Frappe CRM's dashboard over ERPNext's records: its figures, sales trend,
forecasted revenue, funnel, stages, lost reasons, sources and territories,
for the last twelve months. Won and lost are read from `measure.closed`, so a
month is the month it was won, not the last time anybody edited it. The
funnel is ours: Frappe CRM's runs Lead, Deal, Won from its status log, which a
sale that goes on to be ordered, billed and paid outgrows, so ours counts the
papers `chain.py` follows.

### tell.py

A next step's reminder was frappe's own Reminder, a bell entry nobody could
switch off or reword. It is One's Next Step Due now, sent by `due` every five
minutes to the owner of each open lead and opportunity whose step has come due
since the last look, once (`patches/next_step_is_ours` removed the Reminders
waiting).

Mail that comes in on a lead or an opportunity is told to its owner, whichever
mailbox it reached (**They Replied**, `they_replied`). A contract two weeks
from its end is told to whoever made it and the user it names (**Contract
Expiring**); ERPNext only marks it Inactive on the day. erpnext's own mails
from here are listed as types: Appointment Confirmation, and a proforma
invoice sent from its order (**Proforma Invoice by Mail**).

## Answered on the portal

A customer accepts or declines an open quotation on the portal
(one/portal.py `accept_quote`, `decline_quote`). Accepting makes the order with
erpnext's own `make_sales_order`, which refuses a quotation run out unless
Selling Settings allows it, with the date they need it by and their reference,
and keeps it a draft: an order is the team's to confirm. Declining is erpnext's
own Set as Lost, with their reason as its detail. Whoever made the quotation is
told either way (`tell.quotation_accepted`, `tell.quotation_declined`), and the
quotation's timeline says who answered.
