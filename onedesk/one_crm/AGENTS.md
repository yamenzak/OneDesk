# OneCRM

The one file for agents, OneAI and us: what OneCRM is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneCRM is where a company keeps the people and businesses it sells to: who got
in touch, what they might buy, what was said, and what happens next. Every
lead, opportunity, customer and quotation is the same record the rest of One
reads.

## Connections

- **From OneAI**: An enquiry from somebody new that reaches a mailbox OneAI reads becomes a new lead. A customer's order that arrives by mail becomes a draft Sales Order.
- **From OneMail**: Mail sent to a lead or an opportunity, and the replies to it, are on its timeline. The first mail sent to a lead counts as its first reply.
- **From OneBook**: A customer's page shows what they owe, what is overdue, what was billed this fiscal year and their last invoice. An opportunity says how much of what was won is billed and paid, and what is still owed.
- **From OneProject**: New Quotation and Quote Extra Work on a project start the customer's quotation on it, and Make Order orders the one open quotation. Add Contract makes the Sales Order for a contract agreed without one. Draw Up Contract on a project makes a Contract for it with its customer or one of its suppliers, listed under Sales. The contract says its project, when it was signed and when it ends at the top, and prints as One Contract, with both sides to sign. An opportunity says the project its quote went to, or the customer's one open project.
- **To OneProject**: A quotation for a customer with one open project is put on that project, however it is made. Once the customer orders it, its Sales Order is the project's contract, and an order for extra work becomes a sub-project.
- **To OneInventory**: A Sales Order is delivered with Create › Delivery Note. What open orders promise is taken off each item's Free to Sell, and the order says at the top how much has gone out.
- **To OneBook**: A Sales Order, or the delivery made from it, is invoiced with Create › Sales Invoice. A customer's page counts their open opportunities and what they are worth, opening them.
- **To OneCalendar**: Your next steps on leads and opportunities are on your calendar at the time they are due. An Appointment booked with a lead or a customer is a meeting on your own calendar.

## Under the hood

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
3. **The next step.** *Done* — `next.py`, `public/js/one_crm/next_step.js`. Every
   open lead and opportunity carries what happens next and when. Home is *my day*:
   what is due, and what has no next step at all.
4. **The record answers first.** *Done* — `record.py`, and the band and
   Take This Lead as a Record Head (`heads.py`); `public/js/one_crm/crm_record.js`
   keeps Log a Call and the duplicate. A lead and an opportunity open on what people
   open them for — value, stage and how long it has been there, the last
   contact, the next step, where it came from — with notes, calls written down
   by hand, mail and comments on one timeline.
5. **Capture.** *Done* — `capture.py`, `web_form/get_in_touch`. A web form that
   makes a lead, mail to an inbox that makes a lead, duplicates caught on email,
   phone and business name, leads shared out by an Assignment Rule, and the
   first reply on a lead measured.
6. **Measured.** *Done* — `measure.py`, `report/`, `story.py`. A
   forecast by expected month weighted by stage, won and lost with one list of
   reasons, which sources turn into sales, and number cards counting what they
   say they count. ERPNext's CRM dashboard counts "last month" as the
   calendar month before and won by when a deal was made, so its cards
   contradicted Home; the rail's Overview is `Sales Overview`
   (`one_crm_dashboard/`), ERPNext's charts without cards, and the figures
   are Home's alone.
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
`public/js/one_crm/contract_list.js` extends ERPNext's list settings: a draft shows
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
(`one_studio/print_blocks.py` `REPLACES`). A sales order names the account to pay
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
(one_crm/portal.py `accept_quote`, `decline_quote`). Accepting makes the order with
erpnext's own `make_sales_order`, which refuses a quotation run out unless
Selling Settings allows it, with the date they need it by and their reference,
and keeps it a draft: an order is the team's to confirm. Declining is erpnext's
own Set as Lost, with their reason as its detail. Whoever made the quotation is
told either way (`tell.quotation_accepted`, `tell.quotation_declined`), and the
quotation's timeline says who answered.

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, Merge Duplicate Leads, is `abilities.py` with its
  Permission Type on CRM Settings in `permission_type/`. `capture.merges`
  reads it; before it, merging needed delete on Lead, which only a Sales
  Manager has. Its roles are ERPNext's own; `USER` names Sales User.
- **Setup** needs nothing (`setup.py`), **its tour** is `tour.py` over Home's
  figures and views, and **OneAI's reach** is `ai.py`'s NOT_FOR_AI: the next
  step it suggests is a card of its own (plan_next_step).
- **Its foot and settings** are `public/js/one_crm/crm_control.js`; the
  record pages' own scripts (`crm_record.js`, `lead.js`, `lead_list.js`,
  `next_step.js`) are beside them in `public/js/one_crm/`.
- **Its screens** are `frontend/src/crm/`, and **its checks** `checks.py`.
