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

### The plan

1. **The place.** OneBook's rail, in the dock, and what belongs to it rather
   than to OneCRM or OneInventory.
2. **Ready to use.** A check of what will fail the first time somebody
   invoices, is paid or pays — no bank account behind the bank modes of
   payment, no default tax, no fiscal year ahead — with the fix beside each,
   and the fixes that need no decision made automatically.
3. **Home.** The page that answers first: cash in the bank, what customers owe
   and how much of it is late, what is owed to suppliers and due this week,
   and this month's profit.
4. **Getting paid and paying.** An invoice's and a bill's page says what is
   outstanding and when it is due; one step records the payment; an overdue
   customer is reminded.
5. **Repeating invoices and bills.** Rent, retainers and subscriptions made on
   a schedule.
6. **VAT.** The settings the UAE return needs filled in from the chart, and a
   return any country can read: tax charged against tax paid, by rate.
7. **Closing.** Locking the books up to a date, and the year-end close.
