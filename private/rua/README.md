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
folds into it and no contract is counted twice.

**Rua never recorded a supplier's bill.** An LPO marked Final is the one the
supplier accepted, so it becomes a Purchase Invoice on its date, which puts
the material cost on the project. Each is listed to be set against the real
bill.

**Retention was used once, and its field never filled.** One invoice held
10%, which shows only in its amounts. The importer reads the share from the
amounts and One holds it as the UAE taxes it: VAT on the work less the
retention now, and the retention in Retention Receivable until an invoice
releases it.

**Retention held on Excel invoices is caught up by hand, any time.** Lately
Rua held retention on invoices made in Excel and typed only the amounts
after it into the old app, so what each client still holds is written
nowhere the import can read. A **Retention Before One** (Rua's sidebar)
says the project, what the client holds before VAT, and when it is due
back. Submitted, it makes the invoice One would have made: the work, all of
it held, nothing billed now, no VAT and no claim number, with the held
amount in Retention Receivable. Release Retention on the project then bills
it back with its VAT like any other. Cancelling it cancels that invoice.

**Payroll has no history.** Pay starts with One's first payroll run, from
the month the import runs in. The roll-call does come over, so that month's
absences already count.

**Files go private.** The old app served employees' passports and Emirates
IDs to anybody with the link. Every file the import brings over is private
except logos and photos. Signatures and the old app's Google key are left
behind.

## What is not built

- A second run that brings over only what changed on the old site since the
  first. It is safe to run again, but it only adds what is missing; it
  doesn't follow a record edited on the old site after it was brought over.
- The costing sheet behind a quotation. Until OneSheet, the sheet stays
  outside One and only its rates come in.
