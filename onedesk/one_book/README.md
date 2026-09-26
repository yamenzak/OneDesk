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
  **General Ledger**, **Trial Balance**, **Gross Profit**, the **VAT Return**
  and, in the UAE, the **UAE VAT 201**.
- **More** — credit and debit notes, bank transactions, importing a bank
  statement, customer statements, repeating invoices and bills, opening
  invoices and closing a period.
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
- **A late customer is reminded.** **Fix** turns the payment reminder on.
- **Every year that has ended is closed.** **Fix** closes the year (below).
- In the UAE: **the VAT return knows the VAT accounts**, **invoices carry
  the company's TRN** and **the company's emirate is known**. **Fix** fills
  the first from the chart and asks for the other two.
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
3. The band under the title says what is **Outstanding**, when it is
   **Due** (in red, with how many days late, once it has passed), what is
   **Paid** (with a line showing how much of the total) and the **Total**.
   Beside them, **Billed to** the customer is a bar a month for a year of
   what they were invoiced, with this invoice's month in blue and the rest in
   grey, so a first invoice and a regular's look different at a glance.
4. When the customer pays, **Record Payment** asks how much, on what day,
   into which bank or cash account, and the bank's reference, and records
   it. The invoice turns **Paid**, or **Partly Paid** if they paid part. A
   payment with a discount, a deduction or in another currency, or one
   covering several invoices, is **Create › Payment**, which opens the whole
   payment form.
5. Money back to a customer is **Create › Return / Credit Note** on the
   invoice.

A bill works the same way from **Bills**: the supplier, what they charged for,
**Submit**, and **Record Payment** when you pay it.

**A customer's page** answers first what they **Owe Us** (red when any of it
is late, and against their credit limit when one is set), what is
**Overdue** and how old the oldest is, what was **Billed This Year** (with
how much more or less than by this day last year), the **Last Invoice**, and
their **Open Orders**. Beside them, **Billed** is their year, a bar a month.
A supplier's page says the same from the other side: **We Owe**,
**Overdue**, **Bought This Year**, the **Last Bill**, **Open Orders** and
**Bought**. Every figure is worked out from the invoices your own list would
show you.

**Reminding a late customer.** Once turned on (the Books Check's **A late
customer is reminded**), a customer is mailed the invoice a week after it
fell due, if it is still unpaid. The wording is **Setup › Notifications ›
Payment Reminder**.

## Repeating invoices and bills

Rent, a retainer, a monthly service: make the first invoice or bill as usual,
then **⋯ › Repeat** on it. Say how often (monthly, quarterly, yearly…), from
when, until when if it ends, and whether each copy is submitted straight away
or left as a draft for somebody to check. Each copy is the same customer,
items and prices, dated the day it is made, and due as many days later as the
first one was. A repeated bill has no supplier invoice number until you type
this month's in.

The band on a repeating invoice says **Repeats Monthly** and when the next
one is made; clicking it opens the schedule, where it can be paused or
stopped. **More › Repeating** lists every schedule.

## VAT

**Reports › VAT Return** is the figure for any VAT return: for the dates you
pick, the tax charged on invoices and the tax paid on bills and expense
claims, each by tax account and rate with the amount it was charged on, and
what is left **To pay** (or **To reclaim**). Credit notes lower what was
charged. Tax added to the cost of what was bought is not counted, since it
cannot be reclaimed.

In the UAE, **Reports › UAE VAT 201** is the return in the FTA's own boxes.
The Books Check makes sure it has what it reads: the VAT accounts, the
company's **TRN** (printed on every tax invoice) and its **emirate** (sales
are reported under it). The VAT on each bill is filled into the bill's
**Recoverable Standard Rated Expenses** as you enter it; type your own figure
there when not all of it can be reclaimed, and it is left alone.

## Closing a period and a year

Once a VAT return is filed, the period it covers should not change. **Lock
Books** on the VAT Return asks for a date, and nothing dated on or before it
can then be entered, changed or cancelled — by anybody. The title of the VAT
Return says **Locked to** that date. To correct something in a locked
period, open **Lock Books** again and **Unlock**, correct it, and lock again.

At the end of a year, its profit is moved into **Retained Earnings**. The
Books Check's **Every year that has ended is closed** turns **To Do** once a
year has ended with entries in it; **Fix** closes it and locks the books to
its last day. The reports go on showing the year as it was.

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
- `paid.py` and `heads.py` — the band and **Record Payment**, a Record Head
  (one/head.py).
  ERPNext's **Create › Payment** opens a thirty-field Payment Entry for the
  case four fields answer; `settle` takes those four and submits ERPNext's own
  entry, made by its `get_payment_entry`, allocating the amount across the
  invoice's payment-term rows first to last (`allocate`, pure). A bank payment
  needs a reference to submit, so the invoice's number stands in when none is
  typed. `notification/payment_reminder` is a standard Notification, Days
  After the due date by seven, shipped disabled.
- `repeat.py` and `custom/` — repeating. Frappe's Auto Repeat, switched on
  for both invoices by a property setter (`allow_auto_repeat`), rather than
  ERPNext's Subscription, which needs a plan per item to say what the invoice
  already says. `repeated` runs after ERPNext's `on_recurring`: the copy keeps
  the original's days to pay (`terms`, pure) where Auto Repeat would make it
  due the day it is made, its payment schedule is made again rather than
  copied with last time's dates, and a bill drops the supplier's number,
  which a duplicate-number check would otherwise refuse.
- `vat.py` and `report/vat_return` — VAT. ERPNext's UAE VAT 201 reads three
  things a new company does not have — UAE VAT Settings, the TRN, an address
  with an emirate — and says nothing; the Books Check asks. Its box 9 (VAT on
  expenses) sums a field on each bill that somebody is meant to type, so an
  untouched bill reclaims nothing and the VAT is paid twice: `reclaimed`
  (Purchase Invoice validate) keeps it at the bill's VAT until somebody types
  their own figure (`recoverable`, pure). `emirate` (Sales Invoice validate)
  copies the address's emirate onto an invoice not made on its page, since
  Frappe only fetches it there. The VAT Return reads tax rows of submitted
  invoices, bills and expense claims, grouped by account and rate (`lines`,
  pure); it is not a UAE form, and needs nothing set up.
- `closing.py` — the lock and the year-end close. The lock is ERPNext's
  `Company.accounts_frozen_till_date`, enforced in `check_freezing_date`, on a
  Company tab nothing leads to; **Lock Books** sets it and leaves the role
  that may post anyway empty, so locked means locked. The close is ERPNext's
  Period Closing Voucher with the one answer it asks for — the chart's
  Retained Earnings — made and submitted by the Books Check's fix, which
  then locks the books to the year's end. ERPNext posts the voucher in the
  background, so it needs a worker.
- `ready.py` and `report/books_check` — the Books Check. ERPNext's Standard
  chart makes *Bank Accounts* a group, so `Company.default_bank_account` is
  left empty, and `set_mode_of_payment_account` gives only Cash an account;
  every payment by transfer then stops on "Please set default Cash or Bank
  account". `add_bank` makes the bank, its ledger under the group and the Bank
  Account; `wired` (Bank Account `on_update`) fills the company default and
  every bank mode of payment with none, whoever made the account. The checks
  are rows with a key, and the fix for a key is `fix` — Accounts Manager or
  Workspace Administrator only. The page is `public/js/check.js`, which the
  Inventory Check draws too.

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
   customer is reminded. *Done.*
5. **Repeating invoices and bills.** Rent, retainers and subscriptions made on
   a schedule. *Done.*
6. **VAT.** The settings the UAE return needs filled in from the chart, and a
   return any country can read: tax charged against tax paid, by rate.
   *Done.*
7. **Closing.** Locking the books up to a date, and the year-end close.
   *Done.*
