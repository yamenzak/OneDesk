# Rua

Rua Company's private app on One. Rua is an aluminium, glass and cladding
contractor in Abu Dhabi. Before One it ran its own Frappe app, without
ERPNext: projects, claims, payments, LPOs, a roll-call and employee papers,
each in a record type of its own, none of them in a set of books.

This app does two things and nothing else:

- **It sets Rua's workspace up** the way Rua works (`rua/setup.py`): its
  years from 2023, VAT at 5% on every invoice and bill, the UAE VAT return's
  accounts and Rua's emirate, retention taxed when it is released, its
  supplier kinds, its products, its quotation headings, and its pay: basic
  and allowance, a day off unpaid taking a thirtieth.
- **It brings the old app over, once** (`rua/importer/`), with its whole
  history in the books, and checks the books against the old app's own
  totals.

Everything Rua does from then on is One's own: OneProject's contracts and
progress claims, OneBook's books and VAT return, OneHR's attendance, leave,
papers and payroll. What each old record becomes is `docs/IMPORT.md`.

## Running it

Installing the app sets the workspace up. When the site's config says where
the old app is, the import follows in the background:

    bench --site <site> set-config rua_source '{"url": "...", "key": "...", "secret": "..."}'

The sub-projects Rua later merged into their main project's contract are
named in `rua/importer/projects.py` (`MERGED`), as Rua said them, so they
fold into the main project and add nothing to its contract. Another found
later can be added without a release:

    bench --site <site> set-config rua_merged '["<old sub-project name>"]' --parse

The key only ever reads: the importer sends nothing but GET. A copy of the
old app on disk (`rua_source_dir`, written by `rua.source.Source.dump`) is
read instead when it's set, which is how the import is tried on a copy
before it runs on Rua's own site.

The import is safe to run again. Every old record and what it became is a
**Rua Import Record**, and a step skips what it has made already. **Rua
Import** says how far it got, what failed if it did, the checks, and the
list for Rua's accountant.

## The decisions that cost something

**The books have the whole history.** Every final claim is a submitted
Sales Invoice on its date, every receipt a Payment Entry into the bank it
went to. The alternative, opening balances, would have been quicker and
would have left the project pages, the claim statement and the VAT return
with nothing behind them.

**A receipt nobody linked is matched, and the match is listed.** Two in
three of the old receipts name no invoice. Each is matched within its
project family (Rua billed the parent and received on the child, or the
other way round): first an open invoice of the same amount, nearest in
date; then oldest invoice first. What no invoice takes is an advance on the
project's contract. Each match and each advance is on Rua Import for the
accountant to confirm. Rua says what is left are advances it took and has
not invoiced yet; on a project marked Completed, that means its last
invoice is still to be made.

**Some payments were entered twice, and some work ordered twice.** When a
job was split into sub-projects, its payments were typed in again on the
sub-projects, under the same bank references: 7.8M of the old app's 39M
received is copies, on four jobs. Each copy is left out and listed. And a
sub-project called "Original Contract" or "Original Scope" was the main
project's own work, with the main project's value the total of its parts;
One shows a main project's own work as its Main view, so that sub-project
folds into it and no contract is counted twice. Where a main project's
value is more than its parts, Rua says the main is right, and the
difference is ordered as its own work; where it is less, the parts stand.
A sub-project Rua later merged into the main contract (`MERGED`) folds
too, its value already in the main's.

**An LPO line's total is what the supplier billed.** The old app kept a
measured quantity as a whole one (3,369 for 3,369.66 m²), so one line's
total isn't its quantity times its price. The line keeps both, and a Line
Difference line on the same order carries the rest.

**Rua never recorded a supplier's bill.** An LPO marked Final is the one the
supplier accepted, so it becomes a Purchase Invoice on its date, which puts
the material cost on the project. Each is listed to be set against the real
bill.

**Retention was used once, and its field never filled.** One invoice held
10%, which shows only in its amounts. The importer reads the share from the
amounts and One holds it as the UAE taxes it: VAT on the work less the
retention now, and the retention in Retention Receivable until an invoice
releases it.

**Retention held on Excel invoices is asked on the project.** Lately Rua
held retention on invoices made in Excel and typed only the amounts after
it into the old app, so nothing the import reads says what a client still
holds. Each project that billed or was paid gets a **Retention Check**, and
its Overview asks once: **Retention Held** or **No Retention Held**.
Answered, the project says nothing; the Retention Check list in Rua's
sidebar is what is left to ask.

Retention Held asks how much, when it is due back, and what the old app has,
because Rua typed it both ways. Where it has **what was billed after the
retention**, the held work goes on top: the invoice One would have made, the
work all held, nothing billed now, no VAT, the retention in Retention
Receivable until Release Retention bills it with its VAT. Where it has **the
full amount, retention included**, the retention comes off the invoice it was
in: a credit note for it and its VAT, and the same held invoice, so the work
is billed once and its VAT moves to the release. Nearly every old invoice is
paid in full once the receipts are matched, so that leaves the client paid
ahead by the retention and its VAT. The dialog shows the project's work
billed, VAT, what the client owes and the retention held, now and after, as
it is typed, so whoever answers sees which reading matches what the client
actually paid.

**Payroll has no history.** Pay starts with One's first payroll run, from
the month the import runs in. The roll-call does come over, so that month's
absences already count.

**Files go private.** The old app served employees' passports and Emirates
IDs to anybody with the link. Every file the import brings over is private
except logos and photos. Signatures and the old app's Google key are left
behind.

## The costing templates

Rua's estimators price a job in a costing sheet, one line per opening.
`setup.costing` makes one workbook template for a quotation's items per
family of systems (`setup.COSTINGS`): **Costing (Alumil, Gutmann,
Technal)** and **Costing (Gulf Extrusion)**. A template is the sheet's
header, its formulas on 100 lines and its totals, and nothing a job types:
no items, sizes, glass prices or kilos. It is laid out under the company's
brand (`one_sheet/style.branded`): the logo and name on top, the
quotation's number, customer, date, validity, currency and status beside
them, the header on the company's colour, what the formulas work out in
grey and the rate and overall price marked, money in dirhams. Gulf Extrusion's sizes are in
centimetres and its aluminium is priced from its weight, powder coated or
mill finish; Alumil's sizes are in millimetres.

Each has an Items sheet whose first line holds one formula a column, each
filling its column down from the costing (`setup.costing_items`), a line
for each costing line with an item. The product comes from the description
(`setup.kind_formula`, on `setup.KINDS`, which the importer reads the same
way), the mark is the item name, then the description, quantity, width and
height in millimetres, and the rate is the line's overall price (P) over its
quantity (C).

Pasting the C-28 costing (65 lines) into the Alumil template's Costing
sheet made a quotation of 65 lines totalling 6,903,715, the sheet's own
TOTAL; the Gulf Extrusion template gives the 140,000 of the NAD community
centre sheet it was taken from.

## What is not built

- A second run that brings over only what changed on the old site since the
  first. It is safe to run again, but it only adds what is missing; it
  doesn't follow a record edited on the old site after it was brought over.
- The costing sheet behind a quotation. Until OneSheet, the sheet stays
  outside One and only its rates come in.
