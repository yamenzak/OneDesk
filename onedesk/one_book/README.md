# OneBook

Written by hand. What OneBook does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneBook is where the money is kept: the invoices you send, the bills you get,
the payments either way, the bank, and the reports an accountant and a tax
office ask for. It is ERPNext's accounting, so every invoice, payment and
journal entry is the same record the rest of One reads — a project's billed
amount, a customer's balance, an employee's expense claim.

## Finding your way

**OneBook** in the dock opens it. The rail has:

- **Home** — what needs doing and where the money stands (below).
- **Invoices** — what you have billed customers. A **credit note** (money
  given back) is under **More**.
- **Bills** — what suppliers have billed you. A **debit note** is under
  **More**.
- **Payments** — money received and money paid.
- **Bank** — matching your bank statement to what is in the books.
- **Journal Entries** — anything that is not an invoice, bill or payment:
  corrections, accruals, opening balances.
- **Customers** and **Suppliers**.
- **Reports** — **Profit and Loss**, **Balance Sheet**, **Cash Flow**,
  **Receivables** (who owes you, and how late), **Payables** (whom you owe),
  **General Ledger**, **Trial Balance**, **Gross Profit** and the VAT return.
- **More** — credit and debit notes, bank transactions, importing a bank
  statement, customer statements, subscriptions, opening invoices and closing
  a period.
- **Setup** — the chart of accounts, cost centers, bank accounts, taxes,
  payment terms, modes of payment and fiscal years.

## Home

The top row is what needs doing: **Draft Invoices** not yet issued,
**Overdue Invoices**, **Bills to Pay** and **Bank to Match** (bank lines not
yet matched to a payment), each with how many. Under it are **New Invoice**,
**New Bill**, **Match the Bank** and the **Books Check**.

The six figures say where the money stands:

- **Cash** — what is in the bank and cash accounts.
- **Owed to Us** — what customers still owe on invoices, and **Overdue** — the
  part of it past its due date.
- **We Owe** — what is still to pay on bills, and **Due This Week** — the part
  due in the next seven days, including any already late.
- **Profit This Month** — income less expenses since the first of the month.

Click a figure to open the report or list it came from.

## Getting ready

**Setup › Books Check** lists what would stop the first invoice, payment or
bill, and says **Ready**, **To Do** or **Suggested** beside each, with a
**Fix** button where there is one:

- **A bank account is set up.** **Fix** asks for the bank's name and the
  account's, and makes the account in the chart, the company's bank account,
  and connects every bank mode of payment — Wire Transfer, Cheque, Credit Card
  — to it. A bank account added any other way is connected the same way.
- **Invoices carry tax** and **Bills carry tax.** **Fix** asks which VAT
  template is added to a new invoice or bill when nobody picks one.
- **A supplier's bill cannot be entered twice.** **Fix** turns on the check
  that refuses the same supplier invoice number a second time.
- **Today is in a fiscal year** and **the company's default accounts are
  set** — ERPNext makes both, and the check catches a site where it did not.

## An invoice, from start to paid

1. **Invoices › + Add Sales Invoice.** Pick the customer, add a line per item
   or service with its quantity and rate, and the tax if you charge one. The
   due date follows the customer's payment terms.
2. **Save** keeps a draft you can still change. **Submit** issues it: it is in
   the books from then on and can no longer be edited, only cancelled or
   credited.
3. When the customer pays, **Create › Payment** on the invoice makes the
   payment with the amount and the customer filled in; say which bank or cash
   account it went into and submit it. The invoice turns **Paid**, or
   **Partly Paid** if they paid part.
4. Money back to a customer is **Create › Return / Credit Note** on the
   invoice.

A bill works the same way from **Bills**: the supplier, what they charged for,
**Submit**, and **Create › Payment** when you pay it.

## What is kept where

Three apps share the records behind a sale and a purchase, and each answers
one question:

- **OneCRM** — *who might buy, and what did they agree to*: leads, deals,
  quotations and the **sales order** a won deal becomes. Customers are its.
- **OneInventory** — *what we hold*: items, stock and its movements, what
  arrives and what is delivered, what we are ordering from suppliers, and the
  equipment we keep (assets).
- **OneBook** — *the money*: the invoice for what was sold, the bill for what
  was bought, and everything paid. Suppliers are its, since a supplier is
  somebody you pay.

So a sale goes quotation and order (OneCRM), delivery (OneInventory), invoice
and payment (OneBook); a purchase goes order and receipt (OneInventory), bill
and payment (OneBook). Each record opens in its own app's rail, wherever it
was found.

## Under the hood

For the people who build OneBook. OneAI does not read past this heading.

### What it is made of

ERPNext's Accounts module is the ledger and every document that writes to it.
Nothing is re-modelled: Sales Invoice, Purchase Invoice, Payment Entry,
Journal Entry, Bank Account, Bank Transaction and the reports are theirs. What
OneBook adds is the shape — which of ERPNext's hundred-odd accounting screens
a person is shown and in what order — and the places where their accounting
fails a small business on first use or leaves a question unanswered.

- `sidebar/onebook` — the rail. ERPNext's own Accounts sidebar has 121 rows,
  among them share management, budgets, TDS, Plaid, payment orders and the
  repost tools; OneBook's has what a small business works in, and the rest is
  still reachable by search. It replaces the Accounts sidebar the dock's Books
  row used to open. Supplier is owned here (`is_default_module`), Customer by
  OneCRM.
- `workspace/onebook`, `number_card/` and `home.py` — Home. ERPNext's
  accounting number cards total every invoice ever submitted and count a
  credit note as a negative invoice; none says what is unpaid, late or due.
  Each figure is worked out in `home.py`: cash and profit from the ledger
  (profit leaves out the Period Closing Voucher's entries, which move profit
  rather than make it), what is owed from `outstanding_amount` on submitted
  invoices and bills, by due date (`outstanding`, pure).
- `ready.py` and `report/books_check` — the Books Check. ERPNext's Standard
  chart makes *Bank Accounts* a group, so `Company.default_bank_account` is
  left empty, and `set_mode_of_payment_account` gives only Cash an account;
  every payment by transfer then stops on "Please set default Cash or Bank
  account". `add_bank` makes the bank, its ledger under the group and the Bank
  Account; `wired` (Bank Account `on_update`) fills the company default and
  every bank mode of payment with none, whoever made the account. The checks
  are rows with a key, and the fix for a key is `fix` — Accounts Manager or
  Workspace Administrator only.

### The plan

1. **The place.** OneBook's rail, in the dock, and what belongs to it rather
   than to OneCRM or OneInventory. *Done.*
2. **Ready to use.** A check of what will fail the first time somebody
   invoices, is paid or pays — no bank account behind the bank modes of
   payment, no default tax, no fiscal year ahead — with the fix beside each,
   and the fixes that need no decision made automatically. *Done.*
3. **Home.** The page that answers first: cash in the bank, what customers owe
   and how much of it is late, what is owed to suppliers and due this week,
   and this month's profit. *Done.*
4. **Getting paid and paying.** An invoice's and a bill's page says what is
   outstanding and when it is due; one step records the payment; an overdue
   customer is reminded.
5. **Repeating invoices and bills.** Rent, retainers and subscriptions made on
   a schedule.
6. **VAT.** The settings the UAE return needs filled in from the chart, and a
   return any country can read: tax charged against tax paid, by rate.
7. **Closing.** Locking the books up to a date, and the year-end close.
