# Intake

Written by hand. Stages 1 to 9 of eleven are built: every file and message
is read into text and found by what is written in it, every record's
identifiers are kept in one registry, and where OneAI is switched on, each
document is understood (what it is, who it is from and about, its dates,
money and what it asks), placed with the documents it follows, filed
where it belongs, and turned into the people, tasks and requests it is about,
through one door that writes down everything it does so it
can be undone. The plan for
the rest is `docs/INTAKE.md`. The part above **Under the hood** is the
manual; below it are the decisions and what is still to come.

Intake is OneAI handling what arrives. A supplier's invoice, an employee's
passport, a customer's order, a scan of the day's post or a letter from the
tax office goes to a mailbox, a scanner or a folder, and One reads it, files
it where it belongs and does what it asks.

## What is read

Every document in OneCloud and every message in OneMail is read for its words:
PDFs, Word and PowerPoint files, spreadsheets and CSV files, e-invoices
(XRechnung, ZUGFeRD and Factur-X), bank statements (CAMT and MT940), contact
cards and calendar invitations, messages saved as files, and zip files. That
costs nothing and needs no switch.

## Finding a document by what it says

Search finds a document by what is written in it, not only by its name:

- **Ctrl+K** shows documents and messages whose words match, under
  **In documents** and **In mail**, with the line they were found by;
- **OneCloud's** search box finds files by their contents as well as their
  names, and shows the matching words beside each;
- **OneMail's** search finds a message by what its attachments say.

- **OneAI's chat** finds documents too: "the letter about the heating bill",
  "invoices from Stadtwerke this year", "what did we pay Rheinwerk in
  September". It searches the words (in the document's language as well as
  yours), the kind, the party and the dates, answers with what each document
  is, its amount and a link, and adds amounts up from the invoices rather
  than quoting a passage;
- **asking OneAI about a record** ("what do we have on Stadtwerke?") now
  includes its documents: every letter and invoice filed with it, what each
  said and what it still asks.

You only ever find what you may open yourself.

## Letting OneAI read a folder or a mailbox

Right-click a folder in OneCloud and choose **Read with OneAI…**, or open a
mailbox's **⋯** menu in OneMail and choose the same. New files and mail there
are then read by OneAI too, which means scans and photos of documents are
read as well, and recordings are written down. A scan of the day's post is
cut into its letters. This is read with OneAI credits.

OneAI does there only what you may do yourself, because you switched it on.
Your My Files and your own mailbox can only be switched on by you. A folder
OneAI reads shows the OneAI mark, and so does every folder inside it.

**Stop reading with OneAI** in the same menu turns it off. Nothing already
read is forgotten.

## What OneAI understood

Open a file in OneCloud, or a message in OneMail, and **Read by OneAI** shows
beside it what it is (an invoice, a reminder, an order, a sick note), a
line saying what it asks, its number, date, total and where to pay, who it is
from and about (linked to the customer, supplier or person it is, where One
knows them), its dates and what it asks somebody to do.

Every amount, date, IBAN and number OneAI reads is checked against the
document's own words. Anything it said that the document does not say is
left out and listed under **Not in the document**, and the reading is marked
**Unsure**. An e-invoice, a bank statement, a contact card and an invitation
are understood from their own data, with no OneAI credits used at all.

Junk is only looked at, never read in full: spam, phishing, advertising,
newsletters and automatic notifications are named as such and cost almost
nothing.

## Where a document goes

Where OneAI reads a folder or a mailbox, each document is filed once it is
understood:

- **it belongs to a record** (a supplier's invoice, an employee's passport):
  it is attached to that record, so it is in the record's **Files** tab, and
  it shows in the Files tab of every other record it is about too;
- **it belongs to no record yet**: it goes to a folder for its kind and year
  inside the folder OneAI reads, for example `Post/Invoice/2026`. Intake
  Settings' **Leave Unmatched Files in Place** keeps it where it arrived;
- **it is named** `2026-09-24 Stadtwerke Köln – Reminder Electricity.pdf`, in
  the workspace's language, and tagged with its kind, its year and OneAI;
- **a scan of the day's post** is cut into one file per letter, next to the
  scan, and each letter is filed on its own. The scan is kept as it came;
- **a message** is linked to every record it is about, so it is on their
  timelines. A mail attachment is copied onto the record, under its new
  name, and the mail keeps it too;
- **junk** that came straight to a mailbox leaves the Inbox: spam and phishing
  to Junk, advertising and newsletters to a Newsletters folder. Junk that
  came through a scanner or a forward is set aside in an Advertising folder,
  never deleted. Phishing is said to whoever OneAI reads for, and to whoever
  put the file there.

A file in your own My Files is never moved or renamed, only linked and
tagged, and a file a person attached to a record stays on that record.
A medical, pay, personal or legal document is attached only to the person it
is about; anywhere else it is only linked, and a link never lets anybody open
what they could not open before.

## One matter, many documents

A reminder, a corrected invoice, "did you get our invoice?", the scan of a
letter that also came by mail: most of what arrives is about something that
arrived before. The panel says so: **About Stadtwerke Köln RE-2026-0042**,
with what it changes there (**Nudge**, **Update**, **Answer**, **Closing**,
**Nothing New**), or **A copy of …**. A later document is filed with the
records its matter's first document went to, so a reminder that names only
an invoice number lands on the supplier the invoice did. A copy is only
linked there, never filed a second time.

OneAI waits a few minutes after the last message of a matter before it acts,
so a burst of three mails is handled once (Intake Settings' **Quiet
Minutes**). Search finds a message at once all the same. Phishing, and money
or deadlines due within a day, do not wait.

## Who it is from, and what it asks

Where OneAI reads, a document makes what it is about:

- **an invoice from somebody new** with a VAT id, tax number, IBAN or register
  number makes the **Supplier**, and is filed with it. A name alone makes
  nobody, and a company a document only mentions is never made;
- **an order** makes the **Customer**, through ERPNext's own conversion when
  the sender is already a lead; **a first inquiry** makes a **Lead**; **a CV**
  makes a **Job Applicant**, with an opening only if the mail named one;
- **the person who wrote** gets a **Contact**, linked to their company.
  Frappe's own habit of making a bare contact for every address on every
  message is turned off for a mailbox OneAI reads; one it made before is
  completed, never duplicated;
- **an employee's own documents** go on their Employee: a passport or permit
  as a row in their identity documents, with a task for HR before it runs out
  (ninety days for a residence permit, sixty for a passport, thirty for a
  driving licence); a certificate as an education row; a sick note as a leave
  application for their approver; a receipt they paid as their expense claim.
  A resignation, and making an employee from a signed offer, are only
  proposed;
- **what it asks** becomes **one task** per matter, with a step per ask,
  assigned to whoever OneAI reads for (unless an Assignment Rule shares tasks
  out). A reply ticks its step when it goes out in the same thread, an
  appointment's step ticks the day after, and when every step is done the
  task is. A reminder raises the task's priority and moves its date; "paid,
  thanks" closes it. A task a person closed stays closed, and they are told
  the matter moved;
- **an appointment** is an event on that person's calendar;
- **our own mail** is read too: what it promises ("the offer by Friday")
  becomes a task for whoever wrote it.

A sensitive document's task says only "A document arrived for …", and its
event has no description.

**Somebody we knew before.** When a supplier, customer, lead, contact,
employee or applicant is made, the documents that named its email, VAT id,
IBAN or document number before it existed are linked to it.

**An application by mail, then by the form.** Maria mails her CV and OneAI
makes her application. When she then applies through the form, OneAI's is
folded into the form's, which keeps its own values; one HR had worked on is
only flagged.

## Money and goods

A company keeps books, so what arrives becomes a **draft** that a person
posts:

- **an invoice from a known supplier** is a draft bill with its lines. A line
  is booked to the item it is (the supplier's own code for it, or an item of
  that name), else in its own words to the account this supplier's bills
  went to last time. An invoice naming one of our purchase orders is billed
  from the order, so it is matched to it. A bill somebody already booked
  gets the document and nothing new;
- **a credit note** is a return against the bill it credits, or a proposal
  when that bill is not found; **a receipt the company paid** is a draft bill
  that asks nobody to pay; **a supplier's delivery note** is a draft receipt
  against the order; **a supplier's quote** a Supplier Quotation;
- **an order from a customer** is a draft Sales Order, or a proposal when a
  line matches no item; **a customer's payment advice** a draft payment
  against our invoice it names;
- **a bank statement's lines** are Bank Transactions on our account, ready
  for reconciliation (a bank line is not a posting);
- **a contract** is ERPNext's Contract with the party;
- **a reminder for an invoice nobody here has** is a task to ask for it,
  with a warning, since that is also how fraud begins.

The pay step of the matter's task ticks itself when the bill is submitted and
paid in full, by a payment or a journal entry, and opens again if the payment
is cancelled. An invoice paid by direct debit, or already paid, asks nobody
to pay. A draft dated inside books locked by OneBook is dated on the first
open day, and says so. A bill in a currency the workspace has no exchange
rate for is proposed with ERPNext's reason; OneAI never makes up a rate.

**Ready to Submit** (in OneBook) lists every draft OneAI made that you may
post: those whose facts checked out, whose party is known, whose total is
the document's and, billed from an order, whose quantities and prices are
the order's. **Submit All** posts them as you. A draft asking to be paid to an
IBAN we do not have for the supplier, or failing any other check, is listed
apart in red with why, and stays out until somebody opens it. A workspace may
let OneAI submit an e-invoice from a known supplier that is billed from an
order and ready (Intake Settings, off by default).

**Spending** (in OneBook's reports) adds up what was bought, from the
receipts and invoices themselves: by category, shop, person or month, one
currency at a time. Each line's category is learned per shop, so a shop's
lines soon need no model. A **household** (Intake Settings) keeps no books:
no drafts are made at all, and Spending is how it sees where the money went.

## Deadlines

A letter rarely gives a date. It says "within one month of receipt", so
OneAI copies the period as written and **the counting is done here, by the
law's rules**, never by the model: a German authority's posted letter counts
as received four days after it was posted (§ 122 AO), a month ends on the
same day of the later month or its last day (§ 188 BGB), and a weekend or a
public holiday on the workspace's Holiday List moves the end to the next
working day (§ 193 BGB). Each counted date keeps the day it was counted from
and the rule, in words, so a person can check it.

**A contract** with a notice period gets its **last day to cancel** (Cancel By
on ERPNext's Contract) and a task, a month before it, to decide whether to
cancel.

**Deadlines** (in OneCalendar) lists every date something must be done by:
what was read for you, contracts' last days to cancel, and employees'
documents expiring, each for whoever may read its record, with the days left
in red inside a week. An administrator of the workspace sees what was read
for anybody. The calendar has the same three as layers. A deadline goes
once nothing is left to do: its matter is closed, the task OneAI made is
done, or the invoice it booked is paid. A copy of a document has none of its
own, and a sick note's "valid until" is not a deadline.

## Explaining it, and paying it

**Explain** in the panel asks OneAI what the document means in plain words in
your language, what you have to do and by when, and writes the reply in the
letter's own language, ready to copy. It is the one Intake call a person
starts, and it is kept: the same document explained again in the same
language costs nothing unless you ask again. A contract with a last day to
cancel also offers **Write the Cancellation**, a letter that must arrive by
that day.

A bill to pay by transfer shows **Pay**: whom, the IBAN, the amount and the
reference, each copied with a click, and a GiroCode any European banking
app scans into a filled-in transfer. Nothing is paid from One. When the payee
is a supplier whose bank accounts we hold and the bill's IBAN is none of
them, there is no code, only a red line saying to ask them on a number you
already know.

## Twice, and never ordered

A draft bill with the same number as another bill from that supplier, or the
same total on the same day, is red in Ready to Submit, naming the other one.
A delivery note from a known supplier that no order of ours matches is a task
to check it before anybody signs for it or pays.

## The tax year, the week and the month

**Documents for the Tax Year** (on Spending) downloads the year's invoices,
receipts, payslips, bank statements, tax office letters, contracts and
certificates as a zip, a folder per kind, with an index a spreadsheet opens.
You get what was read for you; an administrator gets the workspace's.

Each week everybody OneAI read for gets one notification, mailed too when
they take mail for notifications: how many documents arrived, how many OneAI
dealt with itself, what waits for them, and what falls due in the next seven
days. **Intake Settings** says the month in one line: "OneAI handled 24 of 38
documents this month; 14 needed a person". A document needed a person when
OneAI was unsure of it, proposed something or was not allowed to act.

## Kept by law

A business must keep its papers for years: in Germany invoices, receipts and
bank statements eight (§ 147 AO), business letters, orders, delivery notes
and contracts six, payroll six; in the Emirates the books and their papers
five. Each reading carries its **Keep Until**, the end of the year it is
dated in plus those years. A file that is the only copy of such a document
may go to the Recycle Bin but is not deleted for good before that day, by
anyone, and emptying the bin leaves it there. A household keeps no books and
has no keeping periods, and neither has a country not listed yet.

## What a document teaches

Every document teaches its parties something: a VAT id, a website, a phone
number. An empty field on the supplier, customer or lead is filled and gets
the OneAI badge; one that already says something else keeps it, and the new
value is proposed beside it. A phone the writer's contact does not have yet
is added. A known supplier's document asking to be paid to an IBAN we do not
have for them is what invoice fraud looks like: you are told at once, the
draft is red in Ready to Submit, and our IBAN is never changed from a
document. A supplier who bills one thing a month has it booked to what it was
booked to last time.

## Intake, the inbox

**Intake** sits in the rail under the bell and the clock, with a number when
something waits for you. It opens two boxes that work like a mailbox, one line
per document, bold until you open it:

- **Waiting**: what a person has to decide. A proposal the auditor was unsure
  of or could not apply (ERPNext's reason is under it), or something done
  that the auditor thinks is wrong, to undo or keep.
- **Done**: everything OneAI dealt with, each document with what it made and
  changed, field by field, and **Undo** beside each.

Who opened what is Frappe's own `track_seen`, per person: a document is unread
for you until you open it, and unread again when OneAI does something new
with it. You see what was read for you; an administrator can tick
**Everybody's**, which still leaves out what is medical, about pay or
personal.

Beside a file or above a message the panel leads with the facts a person
looks for first, whatever the document is: who it is from and their tax
numbers, its numbers and references, dates, amounts, what it asks, and
anything else OneAI noted as worth having at hand, under its own label: a
booking code, a flight, a meter reading, a plate. Such a fact is kept only
when its value is written in the document, and never makes it unsure.

The panel is otherwise short: what it is, one line
about it, the amount and due date, "OneAI did 4 things with it" opening it in
Intake, and **Pay**, **Explain** and **Details** behind a button each.

## The auditor

The point is full automation, so a person should be asked only when a person
is needed. Once a document has been acted on, a second agent, the auditor, is
shown the document and everything done and proposed because of it, and says
of each whether the document supports it. It is its own AI action
(`intake_audit`), so a workspace can give it a different model from the one
that did the work.

A proposal it finds right is applied for the person, under their permission,
and carries the OneAI mark; one it finds wrong is dismissed; one it cannot
tell waits. Something done that it finds wrong stays done and goes to
Waiting with its reason: undoing on its word alone would let one model's
mistake erase another's work. It never decides what ends somebody's
employment. A document that was only filed is not audited, since there is
little to get wrong and a call to pay for; Intake Settings can turn the
auditor off.

Two things no longer make OneAI wait. A fact the check found missing from the
document is dropped and never used, so it no longer holds up everything else
read from that document; and a zero tax is how a receipt without VAT reads.
What still waits is mostly what no approval fixes: somebody without
permission to post to an account, a currency without an exchange rate.

## What OneAI did, and taking it back

The panel beside a document ends with **What OneAI did**: made this record,
filed it with that supplier, named it, moved it, tagged it. **Undo** takes
all of it back: files go back where they were with their old names, tags come
off, links go, and a record it made is deleted. What a person has since
checked, changed or submitted stays, and Undo says which and why.

Some things wait for you instead, marked **Needs a look**, with **Apply** and
**Dismiss**:

- changing a value a record already has (a different tax number, an IBAN);
- ending somebody's employment;
- anything OneAI is not sure enough of (below Intake Settings' **Confidence
  Floor**), or read from a document whose facts did not all check out.

You are told once per document when something waits, and not at all for a
document that changes nothing.

OneAI learns from being taken back. Undoing what it did, dismissing what it
proposed, deleting a record it made or moving a file it filed somewhere else
is remembered for that party, and the next document from them is read with
it. Three times the same, and OneAI asks instead of doing it. The **Intake
Lesson** list shows what it learned; deleting a lesson lets it act again. Nothing is ever
submitted, posted or sent by OneAI: whatever it makes that could post stays a
draft. OneAI does only what the person who switched it on may do; what they
may not is written down as **Not allowed** and not done.

## The OneAI mark on a record

A record OneAI made carries the OneAI mark beside its title in every list,
and a **N not checked by a person** button above the list shows only those.
Its form says **OneAI made this from …**, with the document, **Looks right**
and **Undo**. The mark stays until a person looks: saving a change,
submitting, cancelling, pressing Looks right or merging another record into
it. Opening it does not, and neither does OneAI changing it again. Every
record, version and comment OneAI writes says OneAI wrote it.

## The same customer twice

A new contact, customer or supplier that has the email address, VAT id, tax
number, IBAN or register number of one already there says so at the top of
its form, with **Merge Into …** and **Not a Duplicate**. Merging moves
everything on it (mail, files, comments, links) to the one it duplicates,
fills that one's empty fields from it, and deletes it. The one you keep never
loses a value it had.

## Under the hood

- `read.py` turns any file into text without a site or a model, and says
  what it could not do itself: a scan needs eyes, a recording needs ears, a
  locked PDF needs a password. The readers are in `readers/`, one per kind.
- `split.py` cuts a batch scan into its documents at blank pages, separator
  sheets and page numbering that starts again. A vision model marks the rest
  when it reads the pages (`vision.py`, the `read_pages` action).
- `pipeline.py` makes one **Reading** per content, keyed by the same hash
  OneCloud stores content under. The same PDF attached to ten records is one
  reading. A part (the letters of a batch scan, the files of a zip) is a
  Reading of its own with `part_of`.
- A reading that needs a model waits for credits rather than failing
  (`Waiting for Credits`). One that failed for a passing reason is tried
  again every quarter hour, five times. The same job catches up files and
  mail that were there before Intake was, forty at a time, as history.
- `search.py` keeps a FULLTEXT index on the Reading's title and text, and
  answers the awesome bar through Frappe's `awesomebar_search` hook. Every hit
  is checked against the File's or the Communication's own permission.
  Document text stays out of Frappe's global search, which checks only
  doctypes and would show one person's payslip to anybody who may read files.
- Mail signatures' pictures are not read: a picture under 20 KB, or one drawn
  inline in the message.
- `identifiers.py` writes each kind of identifier one way (an IBAN compact and
  checked, a phone number in E.164, a VAT id without spaces) and refuses one
  that is not valid. `identity.py` keeps the **Identifier** table: every
  record's identifiers on every save, a Bank Account's IBAN as its party's and
  an Address's email as its parties'. Rows are Dynamic Links, so Frappe's
  rename and merge carry them; there is no unique index because a merge would
  trip it half way, and `renamed` folds the doubles after. `match` says which
  records a document's identifiers point at and how surely, `ours` recognises
  the workspace itself and its people, and `fold` is the merge OneCRM's lead
  merge uses too.

- `understand.py` is stage 3. `known` understands an e-invoice, a statement, a
  card or an invitation from its data. Everything else gets `look` (the
  `intake_look` action on the first 1,500 characters; mail a machine sent in
  bulk is a newsletter with no model asked) and then `ask` (the `intake_read`
  action, one fixed JSON shape). `facts.check` drops whatever the text does
  not bear out, reading amounts and dates the way the document's country
  writes them, and says what it dropped. Parties are matched through the
  registry, and ourselves set aside. A kind is at least as sensitive as it is:
  the model cannot make a sick note ordinary. A model is asked only where
  OneAI is switched on and never about history.
- `panel.py` answers the panel only for somebody who may open the file or the
  message, and links a party only for somebody who may open its record.

- `act.py` is the one door (stage 4). A planner says what should happen as an
  `Action`; `apply` checks its key (the document's content hash and what is
  done, so a copy, a retry or a re-run does nothing, and neither does anything
  a person dismissed or undid), then whether the person OneAI acts for may do
  it themselves, then its level (`level` is pure), then writes as the OneAI
  user inside a savepoint and keeps what was there before. Every action is an
  **Intake Action** row: the idempotency, Undo, Needs a look and the audit in
  one table. A person sees the rows done on their behalf, an administrator
  all of them. `settle` applies a proposal as the person who pressed Apply,
  under their own permission, with no mark, since a person decided.
- `mark.py` keeps the mark as an `AI Touch` row whose field is `*`. It is
  taken down by `looked_at` on every save, submit and cancel that is not
  OneAI's own (`frappe.flags.one_intake_writing`), an import or a migration;
  a cached list of the doctypes holding any mark keeps that to one cache
  read for everything else. A merge by a person clears it, a fold by OneAI
  keeps it only where the kept record had one. The list asks once per page
  which rows carry it (`unchecked`), and the boot says which doctypes to ask.
- `filing.py` plans where a document goes (`plan` is pure and tested case by
  case) and hands each action to the door. `cut` is the flow that makes one
  letter's file out of a batch scan's pages; its File carries `one_reading`,
  so the panel finds the letter's reading rather than the batch's. File Link
  is a file belonging to a record other than the one it is attached to;
  `namespace.attachments` lists those the reader may open in the record's
  Files tab. Tags are written the way Frappe writes them, since its own
  `DocTags` asks the OneAI user for a write permission it does not hold.

- `matters.py` is stage 5. A matter is its first Reading; later ones name it
  in `matter`. Placing goes strongest first (a copy by its facts, the mail an
  attachment came in, the thread, a number the earlier document carried, the
  one open matter of that party and kind, and last the `intake_place` action
  choosing from the party's open matters) and stops at the first that is
  sure. `change_of` says what a document changes from its facts where it can;
  the same action is asked only when it cannot. The pure parts are tested
  case by case. `understand._done` places and sets `act_after`; `due`, every
  minute, acts once a matter's burst is quiet. `key` gives planners a key per
  matter, so "a task to pay this invoice" exists once however many reminders
  follow.
- `lessons.py` writes an **Intake Lesson** on Dismiss, on Undo, on deleting a
  marked record (read in `on_trash` before the mark goes) and on moving a
  filed file back (File `on_update`). `rule_says` makes the door propose once
  three alike exist. Intake's own rows are in `ignore_links_on_delete`: what
  it wrote down about a record is its history, not a reason to keep it.

- `plans.py` is stage 6: pure planners, each a function from a reading and
  what `planning.context` found (the sender, the employee, the matter's
  task) to the actions to take, tested row by row. Two passes, because the
  supplier an invoice needs must exist before the invoice is filed with it:
  `parties`, then the reading's parties are matched again (`rematch`), then
  filing, then `second`. Keys are per matter for tasks and requests, per
  document for the rest.
- `planning.py` holds the context and the flows planners name: `make_task`
  (assigned, and told OneTask not to give it to its maker, OneAI),
  `make_event` (shared with the person), `customer_from_lead` and
  `employee_from_offer` (ERPNext's and HRMS's own conversions). HRMS checks
  who is signed in for leave and expense claims, so those are written as the
  person OneAI acts for (`Action.as_person`); the mark still says OneAI made
  them. `backlink` links earlier documents to a new party; `applicant_arrived`
  folds a provisional application into the form's.
- `steps.py` ticks task steps by what their `done_when` says: a record's
  state, a reply in the thread, a day passing. A state that changes back
  opens the step again.
- The door gained `Add` (a row on a record's table), `propose` (always a
  person's decision), `propose_on_error` (a flow's refusal becomes a proposal
  with its reason) and `over` (a placeholder value that is filled, not
  proposed). A record that still carries the mark is OneAI's own to change.

- `money.py` is stage 7: pure planners for every money and goods row, each
  action written as the person OneAI acts for (ERPNext asks the signed-in
  user about every account a draft touches). `planning._money` gathers what
  they need (the party's record, the order, the bill a credit note credits,
  one already booked, the items, our bank account, the lock, where this
  supplier's bills were booked last time) and the flows go through ERPNext's
  own mappers. `drafts.py` decides what is ready, submits as the person
  pressing Submit All, and holds the optional e-invoice submit. `steps.paid`
  re-checks the bills a payment or journal entry touched, since ERPNext
  changes their outstanding amount with `db_set`.

- `plans.enrich` is stage 8: a matched party's empty fields from the reading,
  through the door, which proposes wherever the record already says
  something else. An update that changes nothing is not written down.
  `planning._warn_iban` is the red warning.

- `search.find_documents` is stage 9, a read tool for OneAI's chat: the
  FULLTEXT index for words, the Reading's own fields for kind, party and
  dates, every hit checked against the file or message it came from.
  `search.about` gives `memory.about_record` a record's documents. Search
  had looked only at readings still in state Read, so everything understood
  since stage 3 had dropped out of it; it looks at both now. Ranking by
  meaning with embeddings waits on an embedding call through the gateway,
  which meters and prices text generation only today; until then the chat
  model supplies the synonyms and translations a vector would have found.

- `deadlines.py` is stage 10 and pure: the period in a sentence, when a
  letter counts as received, and the end by § 188 and § 193. The fact check
  lets a date with no day through when it says a period, and
  `understand.counted` counts it with the workspace's holidays and writes
  the rule in the workspace's language. `money.contract` fills Cancel By
  with `deadlines.before`. `calendar.py` is both the three calendar layers
  and the Deadlines report's rows, so the two cannot disagree.

- `inbox.py` is the two boxes, the rail's count and who has seen what;
  `audit.py` the auditor, whose pure parts (what is worth a call, what it
  never decides, how its answer is read) are tested. Applying a proposal,
  by a person or the auditor, now goes through the flow it was planned with
  (`Intake Action.flow`), so a bill from an order is made by ERPNext's
  mapper whoever applies it; before, Apply inserted the values bare.

- Stage 11 is `explain.py` (the one call a person starts, kept per language
  on the Reading), `pay.py` (the EPC069-12 text is pure; the code is drawn by
  `pyqrcode`, which frappe already ships), `drafts._twice`, `money.unordered`,
  `bundle.py`, `digest.py` (the weekly digest and the monthly number) and
  `keep.py`. The keep guard sits in OneCloud's File override, ahead of
  Frappe's own on_trash, because that is what removes the stored content:
  a hook would run after it.

Not built yet: a DATEV-shaped export for a business; keeping periods for
countries other than Germany and the Emirates, and for mail deleted in
OneMail; the model credits the month used, which the control plane holds;
an Asset from an equipment invoice; an order confirmation's
changed dates proposed on the order; a reminder's fee proposed as a line;
marking a renewed identity document's old row as replaced; parsing a
supplier's address into an Address and its IBAN into a Bank Account; routing
an employee's documents to their own HR officer rather than whoever OneAI
reads for;
versions of the same file (a corrected or signed copy is placed as an update
but not yet stored as a version), keeping periods, Kanban cards and
the report view carrying the mark, and a list of everything that waits across
documents other than the Intake Action list the notification opens.
`docs/INTAKE.md` §17 lists the stages.
