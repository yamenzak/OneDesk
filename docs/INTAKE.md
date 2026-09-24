# Intake — every document that arrives, read, filed and acted on

A family in Germany, a clinic, an office: all of them receive a stream of
paper and mail they have to keep up with. A tax assessment, a reminder with a
deadline, an invoice to pay, a sick note, a contract that renews unless it is
cancelled by the 30th. What they want is for it to be read, put in the right
place, attached to the right person or company, and turned into the one thing
somebody has to do, without anybody sorting it by hand.

With OneMail and OneCloud built, every way a document reaches a workspace
already ends in One:

- **paper**: a scanner sending to a WebDAV folder, a phone's scan app, an upload;
- **mail**: the workspace's address on the mail domain, a person's address, a
  connected mailbox, or mail forwarded to any of them;
- **people outside**: a file request, a shared folder with upload;
- **records**: a file attached on a form.

So this is not an app. It is **one pipeline that OneAI runs over what
arrives**, switched on in three places:

- ( ) *Read and file new files with OneAI*, in OneCloud's settings, for the
  folders chosen;
- ( ) *Read and file new mail with OneAI*, in OneMail's settings, for the
  mailboxes and folders chosen;
- ( ) *Create tasks from what OneAI reads*, in OneTask's settings.

This document is the argument and the plan. Nothing in it is built.

---

## 1. What it does, in order

The user's list was eight agents. Seven of them survive as stages. What
changes is that **the document is read once**. Eight agents each reading the
same forty-page PDF is eight times the cost and eight slightly different
understandings of one letter. So one careful reading produces a structured
record of the document, and every later stage works from that record. It goes
back to the document only for what the record does not hold.

Each stage is deterministic first and uses a model only for what is left, the
rule linking.py already follows. A number the site issued, an email address
we know, an IBAN on file and an XRechnung's own XML are facts, not guesses.
Paying a model to rediscover them is slower, dearer and sometimes wrong.

### 0. Gate: whether to read it at all

- The folder or mailbox is switched on, and the file is not in somebody's My
  Files unless they switched on that folder themselves.
- It has not been read before. The same invoice arriving by mail and by scan
  is recognised by content hash, and then by its number and amount.
- It is a kind we can read, and not larger than the workspace's limit.
- Mail that is obviously automatic (List-Id, bulk, bounces) and mail already
  in Junk is skipped. Rules and bounces already run before this (rules.py).

### 1. Read: turn anything into text

| What arrives | How it is read | Model? |
|---|---|---|
| PDF with a text layer | pypdf / pdfminer (both on the bench) | no |
| PDF that is a scan | a vision model reading the pages (Gemini reads PDFs, capability.py) | yes |
| ZUGFeRD / Factur-X PDF | the embedded CII XML, read as data | no |
| XRechnung (UBL or CII XML) | read as data: seller, VAT id, IBAN, lines, due date | no |
| Image (jpg, png, heic) | a vision model | yes |
| Word, OpenDocument, PowerPoint | they are zip files of XML, read with zipfile | no |
| Excel, CSV | openpyxl / xlrd (on the bench) | no |
| Email | its own text and HTML; each attachment is read as its own document | no |
| .eml / .msg attached to an email | parsed as mail; .msg needs extract_msg added | no |
| vCard, iCalendar | vobject (on the bench) | no |
| Audio (a voicemail) | the transcription action HIRE 4 already uses | yes |
| zip | opened, and each file read as its own document | no |

The text is kept in a new doctype, **Document Text**: the File or
Communication it belongs to, the text, its language, the pages, how it was
read, and a hash. That is what search, the later stages and OneAI's chat all
read. Nobody pays to read the same scan twice.

### 2. Understand: one structured reading

One call, with the text or the pages, answers a fixed schema:

- **what it is**: invoice, receipt, reminder (Mahnung), tax assessment, contract,
  offer, order confirmation, delivery note, payslip, sick note (AU), medical
  report, appointment letter, letter from an authority, CV, statement, spam, other;
- **title**, a one-line **summary** and the **language**;
- **dates**: issued, service period, due, and every deadline with what it is
  for ("objection within one month", "cancel by 30.11.");
- **money**: amounts, currency, VAT, the IBAN to pay and the payment reference;
- **references**: invoice, order, customer and contract numbers and case
  numbers (Aktenzeichen, Steuernummer);
- **parties**: each with a role (sender, recipient, patient, employee named) and
  every identifier it carries (name, address, email, phone, website, VAT id,
  tax number, IBAN, register number);
- **what is asked**: pay, sign, reply, attend, send something, nothing.

The model is small and cheap for mail and the vision model only for scans.
Both are ordinary OneAI actions, so a workspace can point them at another
model, and admin meters them against credits like every other call.

### 3. Who it is about: parties

Each party in the reading is matched to a record by its identifiers, strongest
first (see §3 for the list). A match on an IBAN or a VAT id is certain. A
match on a name alone is not, and becomes a question rather than a link.

A party nobody knows becomes a **proposal**: *new supplier "Stadtwerke
Köln", with this address, this IBAN and this website.* It is an `AI Proposal`
card as OneAI already makes them, so nothing is created on a model's say-so.

What is found is written the way mail is already linked: `Communication Link`
rows for a message, and a new **File Link** for a file, each saying how it
was made (`one_linked_by`: address, text, identifier, model, manual).

### 4. Junk

Mail only, and only after the rules and bounces. The reading's own verdict
("spam", with a reason) moves the message to Junk on the server, the way a
rule does, and Undo takes it back. Being wrong here costs a message somebody
does not see, so only a confident verdict moves anything. An unsure one is
flagged in the list.

### 5. What it relates to: documents

First deterministically, as linking.py already does: every reference number
that matches a naming series this site issues and exists. Then the model,
**with tools and a shortlist** rather than an open question. "Which of these
open Purchase Orders from this supplier does this delivery note answer?" is a
good question for a model. "What does this relate to?" is not. The tools are
OneAI's existing read tools (find_records, search_everywhere,
what_links_here), which cannot reach past the person the workspace runs this
for.

### 6. What has to happen: tasks, events, drafts

From *what is asked* and the deadlines:

- **a task**, only when something has to be done by somebody. It carries the
  deadline, links to the document and its records, and goes to whoever the
  routing says: the holder of the mailbox it arrived in, the owner of the
  linked record, the customer's account manager, or a default per kind. Tasks
  go into OneTask and their dates into OneCalendar, which is how both fill
  themselves;
- **an event** for an appointment a letter gives ("your appointment on 12.10.
  at 9:30");
- **a draft** where ERPNext already has the document for it, always a draft
  and never submitted:
  - a Purchase Invoice from a supplier's invoice;
  - an Expense Claim from a receipt (the OneHR receipts action already does
    this);
  - a Leave Application from a sick note;
  - a Job Applicant from a CV (HIRE already screens on arrival);
  - an Opportunity from a request for a quote;
  - a payment match from a reminder, against an unpaid invoice (OneBook's
    reconciliation).

### 7. Say it where people look: comments

A comment on each linked record, in two lines: what arrived and what it asks.
*"Reminder from Stadtwerke: €84.20 due by 15.10., second notice. Invoice
ACC-PINV-2026-00031."* Written by OneAI and marked as such, so it can be told
from a colleague's.

### 8. Put it away: name, folder, tags

A scan called `scan_0042.pdf` becomes `2026-09-24 Stadtwerke Köln – Mahnung
Strom.pdf`. It moves to the folder its kind and party say (a folder pattern
per workspace, for example `Company/Suppliers/{party}/{year}`), and is tagged
with its kind, its year and its parties. The retention a kind needs is noted
too: ten years for invoices under German law, so nothing is deleted early.
A file somebody already put in a folder of their own is not moved unless
they asked for that.

### 9. Learn about them: enrichment

Every document teaches something about the parties in it: a new contact
person, a phone number, a website, a VAT id, an IBAN, a new address, a logo.
An empty field is filled straight away (for example a supplier with no
website gets the one on its letterhead). A field that already holds something
different becomes a proposal, because a changed IBAN on a "supplier's" letter
is exactly what invoice fraud looks like. That one is said in red.

---

## 2. People decide, and can take it back

Every stage writes what it did and why, with a confidence. What happens then
depends on a workspace setting with three levels, one per kind of change:

- **do it**: links, tags, the file's name and folder, filling empty fields,
  comments;
- **propose it**: new parties, changed fields, tasks, drafts;
- **leave it**: anything below the confidence floor, shown only on the
  document.

Each document gets an **Intake** panel beside its preview in OneCloud and
beside the message in OneMail. It shows what was read, who it is about, what
it was linked to, what was done, what is proposed, and one Undo for
everything the pipeline did to it. A queue of documents with open proposals
is one list, "Needs a look", so nothing is decided silently and nothing waits
unseen.

**A reading must not publish what it read.** The rule mail already follows:
a link never grants read. A comment on a customer that quotes a medical
report, or a task whose title is a salary, would tell people something they
could not open. So what a stage writes on a record is **only what everybody
who may read that record may know**. Otherwise it says "a document arrived,
open it", and the details stay on the document. Sensitive kinds (medical,
payslip, HR, legal) never make comments at all, only tasks assigned to
people who can open the document.

---

## 3. Identity: the doctypes that say who someone is

The pipeline is only as good as its ability to say *this is the same
Stadtwerke as last month*. Frappe, ERPNext and HRMS already hold identity in
these places:

| Kind | Doctypes | The identifiers they carry |
|---|---|---|
| a person | **Contact** (Contact Email, Contact Phone), User, Employee, Job Applicant, Lead (a person) | email, phone, name, address |
| an organisation | **Customer**, **Supplier**, Prospect, Lead (a company), Bank, Sales Partner, Competitor, Manufacturer, Shareholder, Company (ourselves) | website and domain, VAT id (`tax_id`), IBAN, address, email domain |
| money | **Bank Account** (a Dynamic Link to its party) | IBAN, the strongest identifier there is |
| a place | **Address** (Dynamic Links to its parties) | street, postcode, city |
| the glue | **Dynamic Link** (Contact or Address to any party), Party Type | — |
| ours | **Face** (a picture per address or domain) | email, domain |

**Contact is the hub, and the parties are its links**, as the user said. A
Contact belongs to a Customer, a Supplier, an Employee or a Lead through its
Dynamic Links. That is how Frappe already links an email to a customer
(Communication's contact links), and why mail filing works today.

What is missing is a way to go **from an identifier to a record**. Today
that is a query per field per doctype. The plan adds one small doctype,
**Identifier**: a kind (email, domain, phone, VAT id, tax number, IBAN,
register number, website), the value written one canonical way (lowercase
email, E.164 phone, IBAN without spaces, VAT id without spaces), the record it
belongs to, where it was learned and when. It is filled from the records
themselves on save and by enrichment. It is read by the pipeline, by mail
filing and by OneAI's chat ("who is DE812345678?").

**Merging is Frappe's own.** Renaming one Contact or Supplier into another
with merge rewrites every Link and Dynamic Link that names it, and the
Identifier, File Link and Communication Link rows are those. So a merge
brings all the findings with it, as the user expected, with nothing to write.

---

## 4. Finding things again

Search is the reason to keep the text:

- **words**: MariaDB's FULLTEXT index on Document Text, which the bench's
  MariaDB 10.11 has. Every OneCloud and OneMail search gains the contents of
  documents, not only their names;
- **meaning**: an embedding per chunk, from the catalogue's embedding models,
  so "the letter about the heating bill" finds a document that says
  *Nebenkostenabrechnung*. MariaDB 10.11 has no vector type, so the vectors
  rerank the FULLTEXT and filter candidates in Python. That is fast enough per
  workspace and needs one small dependency (numpy) or none. A workspace large
  enough to outgrow it is a later problem with a known answer (MariaDB 11.7's
  VECTOR);
- **facts**: the structured reading is searchable as fields. *Invoices from
  Stadtwerke over €50 this year*, *everything due next week* and *all sick
  notes for Ahmad* are ordinary list filters;
- **OneAI's chat**: a new read tool, `find_documents`, answers "where is my
  car insurance contract?" with the document and the lines that say so. It
  only returns what the asker may open.

---

## 5. More it can do, once documents are understood

In rough order of value:

1. **Deadlines, all in one place (Fristen).** Every deadline read from every
   document in one list and on the calendar: payment, objection, cancellation,
   reply by. For a German household this alone is worth the product.
2. **Contracts and subscriptions.** A contract or recurring bill becomes a
   record with its term, notice period and the date by which it must be
   cancelled not to renew. OneAI reminds a month before.
3. **Explain this letter.** Any document explained in the reader's language,
   in plain words, with what to do and by when. That is German bureaucracy for
   anybody who does not read German, and a reply drafted in German for them to
   send.
4. **E-invoices, deterministically.** XRechnung and ZUGFeRD are mandatory for
   B2B in Germany from 2025. Reading their XML gives a Purchase Invoice draft
   with every line, no model and no guessing.
5. **Pay from the document.** The IBAN, amount and reference read from an
   invoice (or its GiroCode QR) are offered as a payment. A changed IBAN for
   a known supplier stops it and says why.
6. **Tax year bundle.** Everything a tax adviser needs for a year (receipts,
   invoices, statements, certificates) gathered by kind into one folder or one
   export. For a household, the year's Steuererklärung documents; for a
   business, a DATEV-shaped export later.
7. **Expiring documents.** A passport, a residence permit, a driving licence, a
   certificate, a warranty: when it expires and a reminder before. For
   employees this feeds HRMS's own identification documents.
8. **Duplicates and missing pieces.** The same invoice twice, a reminder for
   an invoice that was never received, a delivery note with no order.
9. **A weekly digest.** What arrived, what was done, what waits for a person,
   and what is due next week.
10. **Retention.** Each kind's legal keeping period, and a document never
    deleted before it (the Recycle Bin respects it).

Two things it should refuse to do: send anything outside the workspace on its
own (a reply is always a draft), and submit or pay anything on its own.

---

## 6. Cost, privacy and control

- **Credits** are OneAI's: each reading is metered by admin like every other
  call, and the settings show a month's estimate and a hard cap. Deterministic
  steps cost nothing, so a workspace that mostly receives e-invoices and
  digital PDFs pays for very little.
- **Where it runs**: the workspace's jurisdiction decides which models may
  read (EU workspaces use EU-served models), as the catalogue already does for
  chat. Medical and HR kinds can be restricted to a model the workspace
  chooses, or kept out of the pipeline entirely.
- **Consent**: turning a folder or mailbox on is a person's choice, stated
  plainly: *documents here will be read by OneAI*. A person's My Files and
  own mailbox are theirs to turn on, not an administrator's.
- **Everything is visible and reversible**: every change says what made it,
  and a document's Undo takes back everything the pipeline did to it.

---

## 7. Where it lives

A new module, **one_intake** (a service, not a space: it has no rail entry of
its own and shows up inside OneCloud, OneMail and OneTask):

- `read.py`: stage 1, one reader per kind, and Document Text;
- `understand.py`: stage 2, the structured reading as an OneAI action;
- `identity.py`: the Identifier registry and party matching (§3);
- `relate.py`, `act.py`, `file.py`, `enrich.py`: stages 5 to 9;
- `pipeline.py`: the order, a background job per document on the long queue,
  retries, and the record of what each stage did;
- `search.py`: FULLTEXT, embeddings and the `find_documents` tool.

It hooks into what exists rather than beside it. OneCloud's upload and DAV
put, the File on_update hook and OneMail's `Arrival.process` hand it
documents. `linking.py` is its deterministic linker. `faces.py` is part of
enrichment. `AI Proposal` is its card. OneTask and OneCalendar receive what
it creates.

---

## 8. The stages

Each ends with something a person can use, and with a check on real
documents: a folder of German letters, invoices, receipts and scans kept as a
test set, with the expected reading for each.

1. **Read.** Document Text and every deterministic reader in the table,
   including XRechnung and ZUGFeRD. The vision model for scans. Search in
   OneCloud and OneMail looks inside documents. *Checkpoint: every test file
   has text, and the e-invoices are read field by field with no model.*
2. **Identity.** The Identifier registry, filled from existing records and
   kept up on save, and party matching. *Checkpoint: each party in the test
   set is found, or proposed once.*
3. **Understand.** The structured reading as an OneAI action, the three
   switches, the gate, and the Intake panel showing what was read. *Nothing
   is done yet; checkpoint: the readings are right on the test set.*
4. **Link and file.** Parties and documents linked (File Link), name, folder
   and tags, junk for mail, the Undo, and the "Needs a look" queue.
5. **Act.** Tasks with routing, calendar events, comments that follow the
   "must not publish" rule, and the ERPNext drafts (Purchase Invoice, Expense
   Claim, Leave Application, Job Applicant, Opportunity).
6. **Enrich.** Empty fields filled, changes proposed, the IBAN-change warning.
7. **Search by meaning.** Embeddings, reranking and OneAI's `find_documents`.
8. **Deadlines and contracts.** The Fristen list, contract records with
   notice periods, and reminders.
9. **The rest of §5**, one at a time: explain this letter, pay from the
   document, the tax year bundle, expiring documents, duplicates, the
   digest, retention.

---

## 9. Decisions for the user

1. **Its name.** "Intake" here. It is a feature inside OneCloud and OneMail,
   so it may not want a product name at all.
2. **How bold by default.** The three levels in §2 are proposed as the
   default. A household may want "do it" for almost everything, a clinic
   almost nothing.
3. **Who it is for first.** The German household, the clinic and the office
   want different kinds read well first: letters from authorities and
   contracts; medical reports and sick notes; invoices and orders. That
   decides the test set and the order of stage 5's drafts.
4. **What a workspace may spend.** A default monthly cap for the pipeline,
   apart from chat.
