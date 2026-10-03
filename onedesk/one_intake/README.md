# Intake

Written by hand. Stages 1 to 9 of 11 are built. The plan for the rest is in
`docs/INTAKE.md`. The part above **Under the hood** is the manual. Below it
are the design decisions and what is still to come.

OneIntake reads what arrives and acts on it. Send a supplier invoice, an
employee's passport, a customer order, a scan of the day's post or a tax
office letter to a mailbox, a scanner or a folder. OneAI reads it, files it
with the right record and creates what it asks for. Everything it does is
logged and can be undone.

## What is read

Every document in OneCloud and every message in OneMail is read for its text,
at no cost and with nothing to switch on. This covers:

- PDF, Word, PowerPoint, spreadsheet and CSV files
- E-invoices (XRechnung, ZUGFeRD and Factur-X)
- Bank statements (CAMT and MT940)
- Contact cards and calendar invitations
- Saved messages and zip files

## Finding a document by what it says

Search finds documents by their content, not only by name.

- **Ctrl+K** shows matching documents and messages under **In documents** and
  **In mail**, with the matching line.
- **OneCloud** search matches file contents as well as names, and shows the
  matching words.
- **OneMail** search matches the text of attachments.
- **OneAI chat** finds documents from a description, such as "invoices from
  Stadtwerke this year" or "what did we pay Rheinwerk in September". It
  searches the text in the document's language and yours, plus the document
  type, party and dates. Each answer gives the document type, amount and a
  link. Totals are added up from the invoices.
- **Asking OneAI about a record**, such as "what do we have on Stadtwerke?",
  includes the documents filed with it, what each says and what is still
  open.

You only find documents you have permission to open.

## Letting OneAI read a folder or a mailbox

1. In OneCloud, right-click a folder. In OneMail, open a mailbox's **⋯** menu.
2. Choose **Read with OneAI…**.

New files and mail there are then read by OneAI as well. Scans and photos
are read, recordings are transcribed and a scan of the day's post is split
into separate letters. This uses OneAI credits.

- OneAI only does what the person who switched it on has permission to do.
- Only you can switch it on for your My Files and your own mailbox.
- A folder OneAI reads, and every folder inside it, shows the OneAI mark.

To turn it off, choose **Stop reading with OneAI** in the same menu. What was
already read is kept.

## What OneAI understood

Open a file in OneCloud or a message in OneMail. **Read by OneAI** shows:

- The document type, such as invoice, reminder, order or sick note
- A one-line summary of what it asks
- Number, date, total and payment details
- Who it is from and about, linked to the customer, supplier or person where
  they're known
- Its dates and any requests

Every amount, date, IBAN and number is checked against the document's text.
Anything not found in the document is left out and listed under **Not in
the document**, and the reading is marked **Unsure**.

E-invoices, bank statements, contact cards and invitations are read from
their own data, with no OneAI credits used.

Spam, phishing, advertising, newsletters and automatic notifications are
recognized from a quick look and never read in full, so they cost almost
nothing.

## Where a document goes

In a folder or mailbox OneAI reads, each document is filed once it's
understood.

- **Belongs to a record**, such as a supplier invoice or an employee's
  passport. It's attached to that record and appears in its **Files** tab,
  and in the Files tab of every other record it's about.
- **Belongs to no record yet.** It goes to a folder for its type and year
  inside the folder OneAI reads, for example `Post/Invoice/2026`. Turn on
  **Leave Unmatched Files in Place** in Intake Settings to keep it where it
  arrived.
- **Naming.** It's renamed like
  `2026-09-24 Stadtwerke Köln – Reminder Electricity.pdf`, in the workspace
  language, and tagged with its type, year and OneAI.
- **A scan of the day's post** is split into one file per letter, saved next
  to the scan. Each letter is filed separately and the original scan is kept.
- **A message** is linked to every record it's about and shows on their
  timelines. Attachments are copied to the record under their new name and
  stay on the message too.
- **A message matching a mailbox rule** with an **About** topic, such as
  "soft drinks", goes to that rule's folder.
- **Junk** sent straight to a mailbox leaves the Inbox. Spam and phishing go
  to Junk, advertising and newsletters to a Newsletters folder. Junk from a
  scanner or a forward goes to an Advertising folder and is never deleted.
  Phishing is reported to the person OneAI reads for and to whoever added
  the file.

Files in your own My Files are never moved or renamed, only linked and
tagged. A file someone attached to a record stays on that record.

Medical, pay, personal and legal documents are attached only to the person
they're about. Elsewhere they're only linked, and a link never gives anyone
access they didn't already have.

## Related documents

Most of what arrives is about something that arrived before, such as a
reminder, a corrected invoice or a letter that also came by mail. The panel
shows this as **About Stadtwerke Köln RE-2026-0042**, with what changes:
**Nudge**, **Update**, **Answer**, **Closing** or **Nothing New**. A duplicate
shows **A copy of …**.

- A later document is filed with the same records as the first one. A
  reminder that only gives an invoice number goes to that invoice's supplier.
- A copy is only linked, never filed again.
- OneAI waits a few minutes after the last message on a matter before acting,
  so three quick emails are handled once. Set this with **Quiet Minutes** in
  Intake Settings. Search finds new messages right away.
- Phishing, and money or deadlines due within a day, are handled without
  waiting.

## Records and tasks from documents

In a folder or mailbox OneAI reads, documents create the records they're
about.

- **An invoice from a new sender** with a VAT ID, tax number, IBAN or
  register number creates the **Supplier** and is filed with it. A name alone
  creates nothing, and a company only mentioned in a document is never
  created.
- **An order** creates the **Customer**, using ERPNext's own conversion if
  the sender is already a lead.
- **A first inquiry** creates a **Lead**.
- **A CV** creates a **Job Applicant**, linked to an opening only if the
  email named one.
- **The sender** gets a **Contact**, linked to their company. Frappe's
  automatic contact for every email address is turned off for mailboxes
  OneAI reads. Contacts it already made are completed, not duplicated.
- **An employee's own documents** go on their Employee record:
  - A passport or permit is added to their identity documents, with a task
    for HR before it expires (90 days ahead for a residence permit, 60 for a
    passport, 30 for a driving licence).
  - A certificate is added as an education row.
  - A sick note becomes a leave application for their approver.
  - A receipt they paid becomes their expense claim.
  - A resignation, or creating an employee from a signed offer, is only
    proposed.
- **Requests** become one task per matter, with a step for each request,
  assigned to the person OneAI reads for unless an Assignment Rule assigns
  it.
  - A reply sent in the same thread completes its step. An appointment's
    step completes the day after. The task completes when every step is
    done.
  - A reminder raises the task's priority and moves its due date. A "paid,
    thanks" closes it.
  - A task someone closed stays closed, and they're notified that the matter
    changed.
- **An appointment** becomes an event on that person's calendar.
- **Outgoing mail** is read too. A promise such as "the offer by Friday"
  becomes a task for whoever wrote it.

A task from a sensitive document only says "A document arrived for …", and
its event has no description.

**Earlier documents.** When a supplier, customer, lead, contact, employee or
applicant is created, earlier documents with its email, VAT ID, IBAN or
document number are linked to it.

**Applying by email, then by form.** If someone emails a CV and then applies
through the form, OneAI's application is merged into the form's, which keeps
its own values. If HR already worked on OneAI's application, it's flagged
instead.

## Money and goods

For a company that keeps books, documents become **drafts** for a person to
submit.

- **Supplier invoice**: a draft Purchase Invoice with its lines.
  - A new supplier is created first from the name and tax ID on the invoice.
  - Each line is matched to an item by the supplier's item code or the item
    name. Otherwise it's booked, in its own words, to the account this
    supplier's last bill used.
  - An invoice that names one of your purchase orders is billed from that
    order, so it's matched to it.
  - If the bill is already booked, the document is attached and nothing new
    is created.
- **Receipt the company paid**: a draft bill marked as not to be paid. One a
  colleague forwards becomes their expense claim.
- **Credit note**: a return against the bill it credits, or a proposal if
  that bill isn't found.
- **Supplier delivery note**: a draft Purchase Receipt against the order.
- **Supplier quote**: a Supplier Quotation.
- **Customer order**: a draft Sales Order, or a proposal if a line matches no
  item.
- **Customer payment advice**: a draft Payment Entry against the invoice it
  names.
- **Bank statement**: Bank Transactions on your account, ready for
  reconciliation. A bank line is not a posting.
- **Contract**: an ERPNext Contract with the party.
- **Reminder for an invoice you don't have**: a task to ask for the invoice,
  with a warning, since this is a common start of fraud.

Paying and dates:

- The pay step of the matter's task completes when the bill is submitted and
  fully paid by a payment or journal entry. It reopens if the payment is
  cancelled.
- An invoice paid by direct debit, or already paid, asks no one to pay.
- A draft dated in a period OneBook has closed is dated on the first open
  day, with a note.
- A bill in a currency with no exchange rate is only proposed, with
  ERPNext's reason. OneAI never makes up a rate.

### Ready to Submit

**Ready to Submit** in OneBook lists the drafts OneAI made that you have
permission to submit, where:

- the facts checked out and the party is known
- the total matches the document
- for a bill from an order, quantities and prices match the order

**Submit All** submits them as you. Drafts that fail a check, including a bill
with an IBAN that isn't on file for the supplier, are listed in red under
**Needs Review** with the reason, and stay there until someone opens them.

A workspace can let OneAI submit e-invoices from known suppliers that are
billed from an order and ready (**Submit Matching E-Invoices** in Intake
Settings, off by default).

### Spending

**Spending** in OneBook's reports totals what was bought, from the receipts
and invoices themselves, by category, shop, person or month, one currency at
a time. Categories are learned per shop, so lines from a known shop soon
need no model.

A **Household** (Intake Settings) keeps no books. No drafts are made, and
Spending shows where the money went.

## Deadlines

Letters usually give a period, such as "within one month of receipt", rather
than a date. OneAI copies the period as written and One calculates the date
by the legal rules, never the model.

- A German authority's letter sent by post counts as received four days
  after posting (§ 122 AO).
- A month ends on the same day of the later month, or its last day (§ 188
  BGB).
- A deadline on a weekend or a public holiday in the workspace's Holiday List
  moves to the next working day (§ 193 BGB).

Each calculated date shows the start date and the rule used, so anyone can
check it.

**Contracts** with a notice period get a **Cancel By** date on the ERPNext
Contract, and a task a month before to decide whether to cancel.

### The Deadlines report

**Deadlines** in OneCalendar lists every due date: from documents read for
you, contract cancellation dates and expiring employee documents. Each
shows to whoever can read its record, with the days left in red within a
week. Workspace administrators see deadlines for everyone. The calendar has
the same three as layers.

A deadline disappears once there's nothing left to do: its matter is
closed, OneAI's task is done or the invoice is paid. A copy of a document
has no deadlines of its own, and a sick note's "valid until" isn't a
deadline.

## Explain and Pay

**Explain** in the panel asks OneAI what the document means, in your
language, what you need to do and by when. It also drafts a reply in the
letter's language, ready to copy. This is the only Intake call a person
starts. The result is saved, so explaining the same document in the same
language again costs nothing unless you choose **Explain Again**.

For a contract with a cancellation date, **Write Cancellation** drafts a
letter that must arrive by that date.

**Pay** appears on a bill paid by transfer. It shows the payee, IBAN, amount
and reference, each copied with a click, and a GiroCode that any European
banking app can scan. Nothing is paid from One. If the supplier's bank
accounts are on file and the bill's IBAN isn't one of them, there's no code,
only a red warning to confirm the IBAN on a number you already know.

## Duplicates and unordered deliveries

- A draft bill with the same number as another bill from that supplier, or
  the same total on the same day, shows in red in Ready to Submit with the
  other bill named.
- A delivery note from a known supplier that matches none of your orders
  becomes a task to check it before anyone signs for it or pays.

## Tax year download and summaries

**Documents for the Tax Year** on the Spending report downloads the year's
invoices, receipts, payslips, bank statements, tax office letters, contracts
and certificates as a zip. There's a folder per type and an index that opens
in a spreadsheet. You get documents read for you. Administrators get the
whole workspace's.

**Weekly summary.** Each week, everyone OneAI read for gets one notification,
also emailed if they get notifications by email. It shows how many documents
arrived, how many OneAI handled, what's waiting and what's due in the next
seven days.

**Monthly summary.** **Intake Settings** shows the month in one line, for
example "OneAI handled 24 of 38 documents this month. 14 needed review." A
document needed review when OneAI was unsure, proposed something or wasn't
allowed to act.

## Kept by law

Businesses must keep their records for a set number of years:

| Country | Records | Years |
|---|---|---|
| Germany | Invoices, receipts, bank statements (§ 147 AO) | 8 |
| Germany | Business letters, orders, delivery notes, contracts, payroll | 6 |
| United Arab Emirates | Books and their records | 5 |

Each reading has a **Keep Until** date: the end of the year it's dated in,
plus those years. A file that is the only copy of such a document can go to
the Recycle Bin but can't be permanently deleted before that date, by
anyone. Emptying the bin leaves it there.

Households, and countries not listed yet, have no retention periods.

## Filling in party details

Documents fill in details on their parties, such as a VAT ID, website or
phone number.

- An empty field on the supplier, customer or lead is filled in and shows the
  OneAI badge.
- A field that already has a different value keeps it, and the new value is
  proposed next to it.
- A phone number the sender's contact doesn't have is added.
- A supplier who bills the same thing every month has it booked like last time.

A known supplier asking to be paid to an IBAN that isn't on file is a common
sign of invoice fraud. You're notified at once, the draft shows in red in
Ready to Submit, and the supplier's IBAN is never changed from a document.

## The Intake inbox

**Intake** is in the side rail below Notifications and the clock, with a count
when something is waiting for you. It has two boxes that work like a
mailbox, one line per document, bold until you open it.

- **Waiting**: what needs a decision. This includes proposals the auditor was
  unsure of or couldn't apply (with ERPNext's reason), and actions the
  auditor thinks are wrong, to undo or keep.
- **Done**: everything OneAI handled, each document with what it created and
  changed, field by field, and **Undo** next to each.

Read status uses Frappe's `track_seen`, per person. A document is unread
until you open it, and unread again when OneAI does something new with it.

You see documents read for you. Administrators can tick **Everyone's**,
which still excludes medical, pay and personal documents.

### The panel

The panel next to a file or above a message shows first what people look
for: the sender and their tax numbers, document numbers and references,
dates, amounts and requests. It also shows other useful details OneAI found,
such as a booking code, flight, meter reading or license plate, each under
its own label. These are only kept when the value appears in the document,
and never mark the reading as unsure.

Below that it's short: the document type, a one-line summary, the amount and
due date, a link such as "OneAI did 4 things with it" that opens it in
Intake, and **Pay**, **Explain** and **Details** buttons.

## The auditor

The aim is full automation, so a person is asked only when needed. After a
document is acted on, a second agent, the auditor, reviews the document and
everything done or proposed for it, and decides whether the document
supports each one. It's a separate AI action (`intake_audit`), so a
workspace can give it a different model.

- **A proposal it finds right** is applied for the person, with their
  permissions, and shows the OneAI mark.
- **A proposal it finds wrong** is dismissed.
- **A proposal it can't judge** waits for a person.
- **An action it finds wrong** stays done and goes to **Waiting** with the
  reason, so one model's mistake can't erase another's work.

The auditor never decides anything that ends someone's employment. Documents
that were only filed aren't audited, since there's little to get wrong. Turn
the auditor off with **Audit What OneAI Does** in Intake Settings.

A value missing from the document is dropped and doesn't hold up the rest of
the reading, and a zero tax on a receipt without VAT is accepted. What still
waits is mostly something no approval can fix, such as someone without
permission to post to an account, or a currency without an exchange rate.

## Fields your workspace requires

A record OneAI creates is filled with the fields that record type needs,
such as a task's subject and dates or a bill's supplier and lines. If your
workspace requires more, through a field made required on the Customize page
or a field used in the naming (**Numbering**), OneAI reads the document again
for those fields before saving. Anything the document doesn't say is left
empty, and the record waits for you instead of being filled with a guess.

## Undo

The panel next to a document ends with **What OneAI did**: records created,
filing, renaming, moving and tagging. **Undo** reverses all of it. Files go
back to their old folders and names, tags and links are removed, and records
OneAI created are deleted. Anything someone has since checked, changed or
submitted stays, and Undo lists what stayed and why.

Some actions wait for you instead, marked **Needs Review**, with **Apply** and
**Dismiss**:

- Changing a value a record already has, such as a tax number or IBAN
- Ending someone's employment
- Anything below the **Confidence Floor** in Intake Settings, or read from a
  document whose facts didn't all check out

You're notified once per document when something is waiting, and not at all
for a document that changes nothing.

### What OneAI learns

Undoing an action, dismissing a proposal, deleting a record OneAI created or
moving a file it filed is remembered for that party, and the next document
from them is read with that in mind. After the same correction three times,
OneAI asks instead of acting. The **Intake Lesson** list shows what it
learned. Delete a lesson to let it act again.

OneAI never submits, posts or sends anything. Whatever it creates that could
post stays a draft. OneAI only does what the person who switched it on has
permission to do. Anything else is logged as **Not allowed** and not done.

## The OneAI mark on a record

Records OneAI created show the OneAI mark next to their title in every list.
A **{n} not checked** button above the list filters to those. The form shows
**Made by OneAI from …** with the document, **Mark as Checked** and **Undo**.

The mark stays until someone saves a change, submits, cancels, clicks **Mark
as Checked** or merges another record into it. Opening the record doesn't
clear it, and neither does OneAI changing it again. Every record, version and
comment OneAI writes is attributed to OneAI.

## Duplicate records

A new contact, customer or supplier with the same email address, VAT ID, tax
number, IBAN or register number as an existing one shows a notice at the top
of its form, with **Merge Into …** and **Not a Duplicate**. Merging moves
everything on it (mail, files, comments, links) to the existing record, fills
that record's empty fields and deletes the duplicate. The record you keep
never loses a value it had.

## OneIntake Settings

Set what OneIntake may do under **OneIntake** › **Settings** in the
sidebar. Each setting, its default and who can change it
is described in One's documentation under OneIntake Settings, for the
Workspace.

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
  **Intake Action** row: the idempotency, Undo, Needs Review and the audit in
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
  `planning._hold_iban` marks the drafted bill wrong when the document asks to
  be paid to an IBAN we do not have for the supplier, so it waits.

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
