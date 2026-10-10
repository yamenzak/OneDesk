# OneIntake

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
- **Requests** become one task per matter, with a step for each request.
  The workspace's Assignment Rules give it to somebody first, such as a rule
  sending every task about a supplier to whoever keeps the books. When no
  rule takes it, it goes to the person OneAI reads for. A task about a bill
  or a delivery for a project is in that project, when its due date is
  inside the project's dates.
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
  - A bill that names one open project, by its name, is for that project, and
    so is each line, so the project's cost includes it.
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

**OneIntake** is at the foot of the rail, above your picture, with a count
when something is waiting for you. On a phone it is at the top of the panel. It has two boxes that work like a
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
workspace requires more, through a field made required with OneAI
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

## Connections

- **From OneMail**: Every message, sent or received, can be found by its text. In a mailbox set to **Read with OneAI**, each new message and its attachments appear in Intake.
- **From OneCloud**: Every new file can be found by its text. In a folder set to **Read with OneAI**, each new file appears in Intake.
- **To OneCRM**: An enquiry creates a Lead, and an order creates the Customer and a draft Sales Order. The sender gets a Contact, and a contract becomes a Contract with a Cancel By date.
- **To OneInventory**: An invoice from a new sender with a tax ID creates the Supplier. A delivery note becomes a draft Purchase Receipt against its order, and a quote becomes a Supplier Quotation.
- **To OneBook**: Bills, credit notes and paid receipts become draft Purchase Invoices, listed in Ready to Submit. A payment advice becomes a draft Payment Entry, and a bank statement becomes Bank Transactions.
- **To OneHR**: A CV creates a Job Applicant. An employee's passport, permit or certificate is added to their Employee record, a sick note becomes a Leave Application, and a receipt they paid becomes their Expense Claim.
- **To OneProject**: A bill that names an open project is drafted for that project. Each line is booked to the item it names: the supplier's code for it, its exact name, or the one item whose whole name the line says.
- **To OneTask**: Each matter becomes one task with a step for each request. A reply or a payment completes its step.
- **To OneCalendar**: An appointment becomes an event on that person's calendar. Due dates, contract cancellation dates and expiring employee documents are listed in Deadlines.
- **To OneCloud**: A document is attached to the record it belongs to, or filed in a folder for its type and year. It is renamed and tagged with its type and its year.

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

  A file dropped in OneCloud, a file attached on a form and a message with
  its attachments are each read in the background, once per content. What
  needs no model (a text PDF, an e-invoice, a Word file, a bank statement) is
  read for every file, so a workspace can search inside its documents whether
  or not it uses OneAI. What needs a model (a scan, a photo, a recording) is
  read only where somebody switched OneAI on, and is charged as OneAI credits.
- A reading that needs a model waits for credits rather than failing
  (`Waiting for Credits`). One that failed for a passing reason is tried
  again every quarter hour, five times. The same job catches up files and
  mail that were there before Intake was, forty at a time, as history.
- `search.py` keeps a FULLTEXT index on the Reading's title and text, and
  answers the awesome bar through Frappe's `awesomebar_search` hook. Every hit
  is checked against the File's or the Communication's own permission.
  Document text stays out of Frappe's global search, which checks only
  doctypes and would show one person's payslip to anybody who may read files.

  The index is asked from three places: the awesome bar (Ctrl+K), OneCloud's
  search box and OneMail's. Each hit is checked against the reader's own right
  to open the file or the message it came from. Frappe's global search is left
  alone on purpose: it checks only whether a person may read a *doctype*,
  never which record. Document text put there would show one employee's
  payslip to anybody who may read any document.
- Mail signatures' pictures are not read: a picture under 20 KB, or one drawn
  inline in the message.
- `identifiers.py` writes each kind of identifier one way (an IBAN compact and
  checked, a phone number in E.164, a VAT id without spaces) and refuses one
  that is not valid. `identity.py` keeps the **Identifier** table: every
  record's identifiers on every save, a Bank Account's IBAN as its party's and
  an Address's email as its parties'. Rows are Dynamic Links, so Frappe's
  rename and merge carry them; there is no unique index because a merge would
  trip it half way, and `renamed` folds the doubles after. `match` says which
  records a document's identifiers point at and how surely (a contact stands
  for the parties it is linked to, not a project it is a contact on, which is
  its customer's), `ours` recognises
  the workspace itself and its people, and `fold` is the merge OneCRM's lead
  merge uses too.

  Frappe, ERPNext and HRMS hold identity in a dozen places: a Contact's emails
  and phones, a Supplier's tax id and website, an Employee's passport, a Bank
  Account's IBAN, an Address's email. Going from an identifier to its record
  was a query per field per doctype. The Identifier table is that in one
  place, kept up on every save, so "who is DE123456789?" is one lookup.
  Frappe's rename and merge carry its rows along through
  `rename_dynamic_links`.

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

  Deterministic first: an e-invoice, a bank statement, a contact card and an
  invitation already say all of it as data, and are understood with no model.
  The first look tells junk from something to read; the reading puts it into
  the fixed shape. What was there before the switch is read for its words
  only.

  A model reading a letter can invent: an amount it expected, a date one day
  off, an IBAN with two digits swapped. So every amount, date, IBAN and number
  it returns has to be found in the document's own text (`facts.py`), allowing
  for how it was written there ("1.234,56 €" is 1234.56). One that is not
  found is dropped and the reading is marked unsure.
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

  `apply` is the only code in Intake that writes, and goes in order:

  1. **the key.** An action already written under this key, done, proposed,
     dismissed or undone, is not done again. A copy, a retry and a re-run
     find the key and stop there; so does something a person dismissed or
     undid;
  2. **on whose behalf.** The person who switched the folder or mailbox on
     must be allowed to do this themselves (docs/INTAKE.md §4.3). If not, it
     is written down as refused and nothing happens;
  3. **the level.** Done, or proposed for a person to look at: an overwrite,
     the end of somebody's employment, and anything below the confidence
     floor or from a reading whose facts did not check out (§4.1). Nothing is
     submitted, so posting stays a draft whatever the level;
  4. **the flow.** A record whose making has a door of its own
     (`make_employee`, OneCRM's `capture`) is made through it, named by
     `flow`;
  5. **the write**, as the OneAI user, with what was there before kept for
     Undo;
  6. **the mark** on a record OneAI made (`mark.py`), and the `Intake Action`
     row.

  `undo` takes an action back, and says why when it cannot: a record a person
  has since checked, submitted or built on stays.
- `mark.py` keeps the mark as an `AI Touch` row whose field is `*`. It is
  taken down by `looked_at` on every save, submit and cancel that is not
  OneAI's own (`frappe.flags.one_intake_writing`), an import or a migration;
  a cached list of the doctypes holding any mark keeps that to one cache
  read for everything else. A merge by a person clears it, a fold by OneAI
  keeps it only where the kept record had one. The list asks once per page
  which rows carry it (`unchecked`), and the boot says which doctypes to ask.

  The field badge of `one_ai/touch.py` compares what OneAI wrote with what a
  field says now; a record has nothing to compare, so its mark is a flag
  (docs/INTAKE.md §4.2). The flag is taken down by a person doing something to
  the record: saving it, submitting it, cancelling it, pressing Looks right,
  or merging another record into it. Opening it does not, nor does ERPNext
  touching it with `db_set`, nor another OneAI action, which writes with
  `frappe.flags.one_intake_writing` set. The cached set of the doctypes that
  carry any mark at all is a handful.
- `filing.py` plans where a document goes (`plan` is pure and tested case by
  case) and hands each action to the door. `cut` is the flow that makes one
  letter's file out of a batch scan's pages; its File carries `one_reading`,
  so the panel finds the letter's reading rather than the batch's. File Link
  is a file belonging to a record other than the one it is attached to;
  `namespace.attachments` lists those the reader may open in the record's
  Files tab. Tags are written the way Frappe writes them, since its own
  `DocTags` asks the OneAI user for a write permission it does not hold.

  A document that belongs to a record is attached to it, so it is in the
  record's Files tab, and File-Linked to the other records it belongs to. One
  that belongs to no record goes to `{kind}/{year}` below the folder that was
  switched on. It is named `2026-09-24 Stadtwerke Köln – Reminder Strom.pdf`
  in the workspace's language and tagged with its kind, its year and OneAI. A
  file somebody put in their own My Files is linked and tagged, never moved or
  renamed. A message is linked to every record it is about, and junk that
  came straight to a mailbox is moved out of the Inbox; junk that came
  through a trusted channel (a scan, a forward) is set aside, never thrown
  away.

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

  Most of what arrives is not new business. It is the reminder for last
  month's invoice, "sorry, forgot the attachment", the corrected invoice,
  "paid, thanks", or the scan of a letter that also came by mail. So a matter
  needs no doctype of its own (docs/INTAKE.md §5.3).

  A document is placed strongest first, stopping at the first that is sure:

  1. **its mail**: an attachment belongs where the message carrying it does,
     and the other way round;
  2. **the thread**: an answer is about what it answers, unless it names a
     different document of its own;
  3. **a reference**: an invoice, order or case number an earlier document of
     the same party carried;
  4. **the party and kind**, when that party has exactly one open matter of
     that kind;
  5. **OneAI**, given that party's open matters as a shortlist, only where a
     model may be asked at all.

  Before any of that, a **copy** (the same kind, number, amount and date from
  the same party) is recognised and does nothing new. The subject line is
  never a key.

  **What it changes** is decided without a model where the facts say it (a
  reminder nudges, a different amount updates, an automatic reply is nothing
  new, a payment advice closes), and by the same one question to the model
  otherwise.

  **Quiet time.** Reading and understanding start at once, so search finds a
  message in seconds. Acting (filing, and what later stages make) waits until
  the matter has been quiet for Intake Settings' Quiet Minutes, then runs once
  over the burst. Phishing, and money or deadlines due within a day, do not
  wait.
- `lessons.py` writes an **Intake Lesson** on Dismiss, on Undo, on deleting a
  marked record (read in `on_trash` before the mark goes) and on moving a
  filed file back (File `on_update`). `rule_says` makes the door propose once
  three alike exist. Intake's own rows are in `ignore_links_on_delete`: what
  it wrote down about a record is its history, not a reason to keep it.

  Undoing something OneAI did, dismissing what it proposed, deleting a record
  it made and moving a file it filed back are each kept with the party and the
  kind of document that led to it. Two things follow:

  - the next document from that party is read with its lessons, so the model
    is told "last time, people took back the supplier OneAI made";
  - **three** lessons alike (the same party, the same kind of document, the
    same thing done to the same doctype) and OneAI stops doing it by itself:
    the door proposes it instead, saying why. Deleting the lessons in the
    Intake Lesson list lets it act again.

- `plans.py` is stage 6: pure planners, each a function from a reading and
  what `planning.context` found (the sender, the employee, the matter's
  task) to the actions to take, tested row by row. Two passes, because the
  supplier an invoice needs must exist before the invoice is filed with it:
  `parties`, then the reading's parties are matched again (`rematch`), then
  filing, then `second`. Keys are per matter for tasks and requests, per
  document for the rest.

  None of the planners touches the database or asks a model, so each row of
  docs/INTAKE.md §3.1 is an ordinary unit test: this reading, in this
  context, makes these actions.

  **Parties** first: the counterpart a document needs and does not have yet
  (a supplier for an invoice, a customer for an order, a lead for an inquiry,
  an applicant for a CV). The door makes them, the reading's parties are
  matched again, and filing runs with the new records in place. Then
  **everything else**: the sender's Contact, a person's documents on their
  Employee, a sick note's leave, an employee's receipt, one task per matter,
  an appointment's event and what our own mail promised.

  **A document never creates a party just for being mentioned.** Only the
  counterpart, and only when the kind of document says what it must be. A
  name alone makes nothing: a supplier needs a VAT id, a tax number, an IBAN,
  a register number or its own email domain.
- `planning.py` holds the context and the flows planners name: `make_task`
  (assigned, and told OneTask not to give it to its maker, OneAI),
  `make_event` (shared with the person), `customer_from_lead` and
  `employee_from_offer` (ERPNext's and HRMS's own conversions). HRMS checks
  who is signed in for leave and expense claims, so those are written as the
  person OneAI acts for (`Action.as_person`); the mark still says OneAI made
  them. `backlink` links earlier documents to a new party; `applicant_arrived`
  folds a provisional application into the form's.

  `run` is called once a matter is quiet (`matters.act_now`). It finds out
  who the sender is, which employee a document is about and whether the
  matter already has a task, asks the pure planners what to do, and hands
  each action to the door. Parties come first; the reading's parties are then
  matched again, so the supplier just made is the record the invoice is filed
  with and the Contact is linked to.

  The flows are the functions a planner names in `Action.flow`: a task that
  is assigned to somebody, an event that shows on their calendar, a customer
  made from a lead through ERPNext's own conversion, and an employee made
  from an accepted job offer through HRMS's.

  Also here: somebody we knew before they had a record. When a Supplier,
  Customer, Lead, Contact, Employee or Job Applicant is made, the readings
  that named one of its identifiers and matched nobody are matched to it, and
  their documents linked (docs/INTAKE.md §7).
- `steps.py` ticks task steps by what their `done_when` says: a record's
  state, a reply in the thread, a day passing. A state that changes back
  opens the step again.

  A step's `done_when` is a record reaching a state (`{"doctype", "name",
  "field", "in" | "equals"}`), a reply going out in the mail thread the ask
  came in (`{"reply_in": thread}`), or a day passing (`{"after": date}`). It
  is checked when that record changes, when a message is sent and once a
  day, with no model. A state that changes back (a payment cancelled) opens
  the step again because ERPNext's state changed, not a person's mind. When
  every step is done, a task OneAI made is done.

  The hook on record changes runs for every save, so it first asks a cached
  set of the doctypes any open step watches.
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

  A company keeps books, so every purchase document becomes a draft matched
  to what came before it: an invoice to its Purchase Order, a supplier's
  delivery note to a Purchase Receipt against the order, a credit note to a
  return against the invoice it credits (docs/INTAKE.md §3.2). An order from
  a customer becomes a draft Sales Order, a payment advice a draft Payment
  Entry against our invoice, a supplier's quote a Supplier Quotation, a
  contract ERPNext's Contract. A bank statement's lines become Bank
  Transactions, which are not postings. Nothing is ever submitted in
  `money.py`: posting stays a person's act, in Ready to submit (`drafts.py`).
  The OneAI mark still says who made each draft. Like `plans.py`, the money
  planners take a reading and what planning found out and answer actions;
  they touch nothing.

  A household does not keep books (Intake Settings' Make Drafts in the Books
  is off): nothing in `money.py` runs, and Spending reads the same readings.

  In `drafts.py`, a draft is ready when its document's facts all passed the
  check, its party is known, its total is the document's total, and, for an
  invoice billed from an order, what it bills is what was ordered and
  received: ERPNext's three-way match, read there rather than redone. A
  supplier whose IBAN on the document is not one we have for them is red, and
  so is anything that fails another check. Red drafts are listed apart and
  stay out of Submit all until somebody opens them. Submitting is the
  person's own act, under their own permission. An e-invoice from a known
  supplier, billed from an order and ready, may be submitted by OneAI itself
  when a workspace switches that on (Intake Settings); it is off by default.

- `plans.enrich` is stage 8: a matched party's empty fields from the reading,
  through the door, which proposes wherever the record already says
  something else. An update that changes nothing is not written down.
  `planning._hold_iban` marks the drafted bill wrong when the document asks to
  be paid to an IBAN we do not have for the supplier, so it waits.

- `ai.find_documents` is stage 9, a read tool for OneAI's chat: the
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

  A letter rarely gives a date. It says "within one month of receipt", and
  the day that means depends on when it counts as received and on how a month
  is counted:

  - **received**: a German authority's posted letter counts as received on
    the fourth day after it was posted (§ 122 AO and § 41 VwVfG, since 2025),
    not the day it was scanned; anything else from the day it arrived;
  - **a month or a week** ends on the day of the later month or week with the
    same number as the day it started from, or the month's last day when
    there is none (§ 188 BGB): 31 January plus one month is 28 February;
  - **a weekend or a public holiday** moves the end to the next working day
    (§ 193 BGB), by the workspace's own Holiday List.

  The day it was counted from and the rule used are kept beside the date, so
  a person can check the arithmetic. The model never counts; it only copies
  the period as written.

  The three kinds of date `calendar.py` shows, each to whoever may read the
  record it sits on:

  - **a reading's deadline**: a bill's due date, an authority's "within one
    month", a document's expiry. It is shown to the person it was read for,
    with the day it was counted from and the rule, so the arithmetic can be
    checked. A matter that is closed has none.
  - **a contract's last day to cancel**, from its notice period, for whoever
    may read the contract.
  - **an employee's document expiring**, a passport or a permit, for whoever
    may read the employee.

  Nothing is copied: each is read from its record as the person looking. The
  Deadlines report (`report/deadlines/`) has the same three kinds in one list
  a person can work down: what was read for them, contracts' last days to
  cancel, and employees' documents expiring, each for whoever may read its
  record. A reading's date says the day it was counted from and the rule, so
  the arithmetic can be checked. An administrator of the workspace sees what
  was read for anybody.

- `inbox.py` is the two boxes, the rail's count and who has seen what;
  `audit.py` the auditor, whose pure parts (what is worth a call, what it
  never decides, how its answer is read) are tested. Applying a proposal,
  by a person or the auditor, now goes through the flow it was planned with
  (`Intake Action.flow`), so a bill from an order is made by ERPNext's
  mapper whoever applies it; before, Apply inserted the values bare.

  **Intake** at the top of every app's panel, under Notification and Check In, opens two boxes that
  work like a mailbox, one line per document:

  - **Done**: documents OneAI acted on and nothing waits for. Open one to
    read what it made and changed, field by field, and undo any of it.
  - **Waiting**: documents with something a person has to decide — a
    proposal the auditor was unsure of or could not apply, or something done
    that the auditor thinks is wrong. Apply, dismiss, undo or keep.

  What a person has opened is remembered per person with Frappe's own
  `track_seen`, so a document is unread for you until you open it, whoever
  else has, and is unread again when OneAI does something new with it. The
  rail shows how many wait for you. You see the documents read for you. An
  administrator of the workspace may also look at everybody's, except what is
  medical, about pay or personal.

  Full automation means a person is asked only when a person is needed. The
  reader that understood a document and planned what to do is not the one to
  judge its own work, so the auditor is a separate call, its own AI action
  `intake_audit`, whose model a workspace chooses on its own.

  - **A proposal it finds right** is applied for the person it was read for,
    under their permission, and carries the OneAI mark like anything else
    OneAI made. **One it finds wrong** is dismissed. **One it is unsure of**
    waits.
  - **Something done that it finds wrong** stays done and goes to the
    person's Waiting box with the auditor's reason, to undo or to keep.
    Undoing on the auditor's word alone would let one model's mistake erase
    another's work.
  - It never decides what ends somebody's employment, and never retries what
    was refused for want of permission: those wait for a person whatever it
    says.

  A document with nothing done but filing (moved, renamed, tagged, linked)
  and nothing waiting is not audited: there is little to get wrong and a call
  to pay for. A workspace can turn the auditor off in Intake Settings.

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

### bundle.py

A tax adviser asks for the same things every spring: the invoices and
receipts, the payslips, the bank statements, the tax office's letters and the
contracts, for one year. They have all been read already, so the download is a
zip of them by kind, with a list of every document, its date, whom it is from
and its amount, that opens in any spreadsheet.

A reader gets what was read for them; an administrator of the workspace gets
the workspace's. Only a file the reader may open goes in, as everywhere else.
A DATEV-shaped export for a business is not built.

### digest.py

**The weekly digest** goes to each person OneAI read for this week, as one
notification that is also mailed when they get mail for notifications: how
many documents arrived, how many OneAI dealt with itself, what still waits for
them, and what falls due in the next seven days. A week with nothing read for
somebody sends them nothing.

**The monthly number** is what a workspace pays OneAI for, said plainly in
Intake Settings: "OneAI handled 1,140 of 1,240 documents this month; 100
needed a person". A document needed a person when OneAI was unsure of what it
read, or proposed something, or was not allowed to do it. A batch scan counts
as the letters cut from it.

### explain.py

**Explain** in the Intake panel asks OneAI, once, what a document means in
plain words in the reader's own language, what they have to do and by when,
and for a letter, a reply in the letter's own language. For a contract with a
last day to cancel, **Write the cancellation** asks for the cancellation
letter instead, to reach them by that day.

It is the one Intake call a person starts, so it is kept: the same document
explained again in the same language costs nothing, and **Again** asks anew.
Whoever may open the file or the message may ask; nobody else learns it
exists.

### fill.py

A planner fills the fields it knows a kind by: a task's subject and dates, a
bill's supplier and lines. What else the kind requires is the workspace's to
decide, and it changes: a required field added on the Customize page, a kind
Numbering names by one of its fields, or one whose name a person types. None
of that is in the planner, so without `fill.py` the save fails and the action
is refused.

So while Intake writes a new record (`filling`, from `act._write`), two hooks
on every kind ask the model, once each, for what is still `missing`
(`one_ai/kind.py`), from the document and nothing else:

- `before_insert`, before frappe names the record: its name, when the kind is
  named by a field or typed by whoever makes it;
- `before_save`, after the kind's own validate has filled what it fills:
  every required field still empty.

A value the document does not give is left empty, and frappe then refuses the
record as it always would, with its own words, so the action waits for a
person. Only the record Intake is making is touched, never one its flow makes
on the way, and never outside Intake's write.

### keep.py

A business must keep its books' papers for years, and which papers and how
many years is the law of its country:

- **Germany** (§ 147 AO, § 257 HGB, since 2025): invoices, receipts, bank
  statements and other vouchers eight years; business letters, orders,
  delivery notes and contracts six; the payroll account six (§ 41 EStG);
- **the United Arab Emirates** (Federal Decree-Law 50 of 2022, and the VAT
  law): the books and their papers five years.

The time runs from the end of the year the document is dated in. A file whose
only copy holds a reading cannot be deleted for good before its Keep Until
day, but it may go to the Recycle Bin, where it stays. A household keeps no books and has no keeping
periods, and neither has a country not listed here.

### pay.py

A bill that asks to be paid by transfer shows, in the Intake panel, whom to
pay, the IBAN, the amount and the reference, each ready to copy, and a
GiroCode: the EPC QR code every European banking app scans into a filled-in
transfer. Nothing is paid from here; the bank does that, as the person.

**A changed IBAN stops it.** When the payee is a supplier we already hold bank
accounts for and the document's IBAN is none of them, there is no code, and
the panel says so in red: that is how invoice fraud works, and the one safe
answer is to ask the supplier on a number already known.

### report/spending/spending.py

A household keeps no books, and a company's books answer "what did we spend on
fuel this quarter" only through a report somebody builds. The readings already
hold every line with its amount and category, so the Spending report adds them
up: by category, by shop, by person or by month, one currency at a time, with
the document behind every row one click away. A reader sees what was read on
their own behalf; an administrator of the workspace sees all of it.

### switches.py

Three switches: a OneCloud folder (and every folder inside it), a OneMail
mailbox, and Intake Settings' "Read Files Attached to Records". Each is turned
on by a person and remembers who, because OneAI may only do there what that
person may do (docs/INTAKE.md §4.3). A person's My Files and own mailbox are
theirs to turn on, not an administrator's.

OneIntake Settings lists every mailbox and every folder OneAI reads
(`overview`). An administrator may stop any of them from there; turning one on
is still for whoever holds it, since OneAI then acts as that person.
