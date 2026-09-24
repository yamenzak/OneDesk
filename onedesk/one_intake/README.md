# Intake

Written by hand. Stages 1 to 4 of eleven are built: every file and message
is read into text and found by what is written in it, every record's
identifiers are kept in one registry, and where OneAI is switched on, each
document is understood (what it is, who it is from and about, its dates,
money and what it asks) and filed where it belongs, through one door that
writes down everything it does so it can be undone. The plan for
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

You are told once per document when something waits. Nothing is ever
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

Not built yet: placing a document in its matter and comparing it with what
came before (stage 5), the records and drafts each kind of document makes
(stages 6 and 7), versions of the same file, keeping periods, Kanban cards and
the report view carrying the mark, and a list of everything that waits across
documents other than the Intake Action list the notification opens.
`docs/INTAKE.md` §17 lists the stages.
