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

**OneBook** in the dock opens it. Every row is called what ERPNext calls what
it opens, the name **Ctrl+K** finds it by, or what ERPNext's own Invoicing
sidebar calls it. The rail has:

- **Home** — how the money is doing, what needs doing, and everything else
  (below).
- **Sales Invoice** — what you have billed customers. **Purchase Invoice** —
  what suppliers have billed you.
- **Payment Entry** — money received and money paid. **Journal Entry** —
  anything that is not an invoice or a payment: corrections, accruals,
  opening balances.
- **Bank Reconciliation Tool** — matching your bank statement to the books.
- **Ready to Submit** — bills read from mail and scans, waiting for you.
- **Customer** and **Supplier**.
- **Receivables** — **Credit Note** (money given back), **Accounts
  Receivable** (who owes you, and how late) and **Process Statement Of
  Accounts** (customer statements by mail).
- **Payables** — **Debit Note** and **Accounts Payable** (whom you owe).
- **Banking** — **Bank Transaction**, **Bank Statement Import** and **Bank
  Account**.
- **Financial Reports** — **Profit and Loss**, **Balance Sheet**, **Cash
  Flow**, **General Ledger**, **Trial Balance**, **Gross Profit**, the **VAT
  Return** and, in the UAE, the **UAE VAT 201**.
- **Reports** and **Setup** open those parts of Home: every accounting report
  by what it is about, and the chart of accounts, cost centers, taxes,
  payment terms, modes of payment, fiscal years and settings, with the
  **Books Check** first.

Everything here is for whoever People gives OneBook. An **Accounts User**
matches the bank and imports a statement; an **Accounts Manager** also
enters the opening invoices and keeps the purchase tax templates. ERPNext
gives those four only to its System Manager or to buying, so One gives them
to accounts (`access.py`).

## Home

Six figures say where the money stands, each with its last twelve months
drawn small under it:

- **Cash** — what is in the bank and cash accounts, against last month.
- **Accounts Receivable** — what customers still owe, and **Overdue** — the
  part of it past its due date.
- **Accounts Payable** — what is still to pay suppliers, and **Due This
  Week** — the part due in the next seven days, including any already late.
- **Profit This Month** — income less expenses since the first of the month,
  against last month.

Click a figure to open the report or list it came from. Under them are five
tabs:

- **Overview** — what needs doing as a row of buttons, then the money told in
  charts, as Frappe Books' dashboard tells it: **Cash Flow** (what came into
  and went out of the bank and cash accounts each month), **Profit and Loss**
  (each month's profit or loss) and **Top Expenses** (the five largest expense
  accounts and the rest); then, for **Accounts Receivable** and **Accounts
  Payable** each, the **Ageing** of what is owed in ERPNext's ranges, who owes
  or is owed the most, and the year's invoices by status. Click a chart to
  open what it was drawn from.
- **Today** — overdue sales invoices, purchase invoices due this week or
  already late, unreconciled bank transactions by bank account, and drafts
  left more than a day, each row opening its document.
- **Everything** — every accounting screen, each called what ERPNext calls it
  and with a line on what it is for, with a search.
- **Reports** and **Setup** — their part of Everything, by topic.

## Getting ready

**Setup › Books Check** lists what would stop the first invoice, payment or
bill, and says **Ready**, **To Do** or **Suggested** beside each, with a
**Fix** button where there is one:

- **A bank account is set up.** **Fix** asks for the bank's name and the
  account's, and makes the account in the chart, the company's bank account,
  and connects every bank mode of payment — Wire Transfer, Cheque, Credit Card
  — to it. A bank account added any other way is connected the same way.
- **Invoices carry tax** and **Bills carry tax.** **Fix** asks which VAT
  template is added to a new invoice or bill when nobody picks one, in a
  form and on every invoice or bill One, OneAI or an import makes.
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

1. **Sales Invoice › + Add Sales Invoice.** Pick the customer, add a line per item
   or service with its quantity and rate, and the tax if you charge one. The
   due date follows the customer's payment terms.
2. **Save** keeps a draft you can still change. **Submit** issues it: it is in
   the books from then on and can no longer be edited, only cancelled or
   credited.
3. A sentence over the page says where it stands ("25 days late. Acme
   Holdings still owes $1,300.00.", "Paid in full."), and under it a track
   from **Ordered** and **Delivered** (when an order or delivery note came
   first) to **Billed** and **Paid**, the last with how much is paid so far
   or how late it is. Beside the track are the **Project** it is for, the
   **Outstanding Amount**, the **Payment Due Date** (the first part still
   unpaid, as ERPNext's status reads it, so a retention held for a year
   doesn't hide a late payment; in red once it has passed) and the **Grand
   Total**.
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

A purchase invoice works the same way from **Purchase Invoice**: the supplier, what they charged for,
**Submit**, and **Record Payment** when you pay it.

**A customer's page** answers first their **Total Unpaid** (red when any of it
is late, and against their credit limit when one is set), what is
**Overdue** and how old the oldest is, their **Annual Billing** (with
how much more or less than by this day last year), the **Last Sales Invoice**, and
their **Open Orders**. Beside them, **Billed** is their year, a bar a month.
A supplier's page says the same from the other side: **Total Unpaid**,
**Overdue**, **Annual Billing**, the **Last Purchase Invoice**, **Open Orders** and
**Bought**. Every figure is worked out from the invoices your own list would
show you.

**Reminding a late customer.** Once turned on (the Books Check's **A late
customer is reminded**), a customer is mailed the invoice a week after it
fell due, if it is still unpaid. The wording is **Automation › Workspace Notifications ›
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
stopped. **Home › Everything › Auto Repeat** lists every schedule.

## VAT

**Financial Reports › VAT Return** is the figure for any VAT return: for the dates you
pick, the tax charged on invoices and the tax paid on bills and expense
claims, each by tax account and rate with the amount it was charged on, and
what is left **To pay** (or **To reclaim**). Credit notes lower what was
charged. Tax added to the cost of what was bought is not counted, since it
cannot be reclaimed.

In the UAE, **Financial Reports › UAE VAT 201** is the return in the FTA's own boxes.
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

## Connections

- **From OneCRM**: A Sales Order is invoiced here with Create › Sales Invoice. Customers are kept in OneCRM.
- **From OneProject**: Invoice Time, Invoice Month and Bill Progress on a project make the customer's invoices. Bill Progress on a subcontract drafts the supplier's bill for the project's manager to check.
- **From OneInventory**: A receipt or a purchase order becomes the supplier's bill with Create › Purchase Invoice, and a delivery becomes the customer's invoice the same way. Each asset's depreciation is posted to the books by itself.
- **From OneHR**: Approved expense claims and payroll runs are posted to the books. The VAT on expense claims counts in the VAT Return.
- **From OneIntake**: A supplier's bill read from mail or a file becomes a draft bill, matched to its purchase order. A customer's payment advice becomes a draft payment, and a bank statement's lines are ready to match.
- **To OneProject**: Invoices, bills and payments that name a project count in its Billed, Paid and Cost figures. A payment takes the project its invoices name.
- **To OneCRM**: A customer's page shows what they owe, what is overdue, what was billed this year and their last invoice.
- **To OneInventory**: Suppliers are kept in OneBook. A supplier billed in another currency gets the purchase orders made from To Order in that currency. A supplier's **Items** tab is OneInventory's: what is bought from them, item by item.

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
- `page/books`, `home.py` and `story.py` — Home, the `onedesk.books` island
  (frontend/src/home/BooksHome.vue, BooksStory.vue), laid out as
  OneInventory's Home and drawn from Frappe Books' dashboard. ERPNext's
  accounting number cards total every invoice ever submitted and count a
  credit note as a negative invoice; none says what is unpaid, late or due.
  `story.py` works each figure and chart out for the one company: cash and
  profit from the ledger (leaving out the Period Closing Voucher's entries,
  which move profit rather than make it), what is owed from
  `outstanding_amount` on submitted invoices, by due date (`home.outstanding`
  and `ageing`, both pure). `home.py` has Today and the directory, each row
  named as ERPNext names what it opens; its single-figure functions stay for
  the demo's checks and OneAI. The `OneBook` workspace and its six number
  cards were Home until the page replaced them (`patches/home_is_a_page`).
- `custom/` — **Outstanding Amount** is a column of both invoice lists, as
  Frappe Books' lists show what is still due beside the total; **Paid
  Amount** a column of the payments, in place of the two accounts; and
  **Posting Date** a column of the journal entries.
- `paid.py` `titled` and `journal.py` — what a payment and a journal entry
  are called. ERPNext titles a payment by the party's ID (an employee's
  reads HR-EMP-00013) and a journal entry by its first account (forty read
  Accumulated Depreciation - SGA). A payment takes the party's name; a
  journal entry nobody titled takes the asset it depreciates, the payroll's
  period, its remark or what it references. Two patches retitle the old
  ones.
- `heads.py`, a payment and a journal entry — a sentence of what moved,
  and for one through a bank account a track to **Reconciled**, read from
  its clearance date, the field the Bank Reconciliation Tool sets.
- `paid.py` and `heads.py` — the band and **Record Payment**, a Record Head
  (one/head.py).
  ERPNext's **Create › Payment** opens a thirty-field Payment Entry for the
  case four fields answer; `settle` takes those four and submits ERPNext's own
  entry, made by its `get_payment_entry`, allocating the amount across the
  invoice's payment-term rows first to last (`allocate`, pure). A bank payment
  needs a reference to submit, so the invoice's number stands in when none is
  typed. `notification/payment_reminder` is a standard Notification, Days
  After the due date by seven, shipped disabled.

  ERPNext's **Create › Payment** opens a Payment Entry form of some thirty
  fields, filled from the invoice, for somebody to read, save and submit; the
  common case — the customer paid all or part of this invoice into our bank —
  needs four of them. **Record Payment** on a submitted invoice or bill asks
  for those four (how much, on what day, into or out of which account, and the
  bank's reference) and submits ERPNext's own Payment Entry, made by its own
  `get_payment_entry`. Anything else — a discount, a deduction, another
  currency, one payment across several invoices — is still **Create ›
  Payment**.

  An invoice left unpaid is also a reminder: **Payment Reminder**
  (`notification/payment_reminder`) mails the customer the invoice a week
  after it fell due. It is shipped off, since it writes to customers; the
  Books Check turns it on.
- `repeat.py` and `custom/` — repeating. Frappe's Auto Repeat, switched on
  for both invoices by a property setter (`allow_auto_repeat`), rather than
  ERPNext's Subscription, which needs a plan per item to say what the invoice
  already says. `repeated` runs after ERPNext's `on_recurring`: the copy keeps
  the original's days to pay (`terms`, pure) where Auto Repeat would make it
  due the day it is made, its payment schedule is made again rather than
  copied with last time's dates, and a bill drops the supplier's number,
  which a duplicate-number check would otherwise refuse.

  Frappe's **Auto Repeat** copies a document on a schedule, and ERPNext's
  invoices were written for it — each has an `auto_repeat` field and an
  `on_recurring` method — but neither is switched on for it
  (`allow_auto_repeat`), so **⋯ › Repeat** is not offered. OneBook switches it
  on (`custom/sales_invoice.json`, `custom/purchase_invoice.json`) rather than
  using ERPNext's **Subscription**, which needs a plan per item and a price
  per plan to say what the invoice already says.

  The copy is not right as Auto Repeat makes it, and `repeated` (both
  invoices' `on_recurring`, run after ERPNext's own) corrects it:

  - **The due date.** Auto Repeat dates every required date field the day it
    runs, and ERPNext's `on_recurring` empties the due date, so a copy with
    no payment terms falls due the day it is made and is late the next. The
    copy keeps the original's days to pay instead.
  - **The payment schedule.** Its rows are copied with last time's dates; the
    copy's is made again from its own due date or payment terms.
  - **The supplier's bill number.** It is copied, and is the supplier's
    number for last month's bill; with duplicate bill numbers refused (the
    Books Check suggests it) the copy cannot even be saved. The copy has none
    until this month's bill comes, and is dated the day it is made.
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

  **The UAE's own return** is ERPNext's UAE VAT 201
  (`regional/report/uae_vat_201`), and on a new company three of its inputs
  are empty and nothing says so:

  - **UAE VAT Settings** names the company's VAT accounts. Without them the
    reverse-charge boxes are nought and a reverse-charge bill will not
    submit. `uae_accounts` fills them from the chart: the Tax accounts called
    VAT.
  - **The VAT on a bill** (box 9) is not read from the bill. It is the sum of
    a field on each, *Recoverable Standard Rated Expenses*, that somebody is
    meant to type; a bill left at nought does not count, so the company
    reclaims none of the VAT it paid and pays it twice. `reclaimed` (Purchase
    Invoice validate) keeps it at the VAT charged on the bill until somebody
    types their own figure, which is then left alone.
  - **The emirate and the TRN.** Box 1 is by emirate, read from the company's
    address; a UAE tax invoice must carry the company's TRN. A new company
    has neither. The Books Check asks for both, and `emirate` (Sales Invoice
    validate) copies the emirate onto an invoice made anywhere but its page.

  **A return any country can read** is `report/vat_return`: tax charged on
  invoices against tax paid on bills and expense claims, by tax account and
  rate, and what is left to pay or reclaim. It reads the tax rows of
  submitted documents, so a credit note lowers what was charged and a debit
  note what was paid. A bill's tax counts only when it was added to the
  bill's total: tax added to the cost of what was bought (Valuation) cannot
  be reclaimed. Journal entries to a tax account are not in it; they are in
  the General Ledger.
- `closing.py` — the lock and the year-end close. The lock is ERPNext's
  `Company.accounts_frozen_till_date`, enforced in `check_freezing_date`, on a
  Company tab nothing leads to; **Lock Books** sets it and leaves the role
  that may post anyway empty, so locked means locked. The close is ERPNext's
  Period Closing Voucher with the one answer it asks for — the chart's
  Retained Earnings — made and submitted by the Books Check's fix, which
  then locks the books to the year's end. ERPNext posts the voucher in the
  background, so it needs a worker.

  **The lock** is ERPNext's own — nothing is posted, edited or cancelled on
  or before `Company.accounts_frozen_till_date`
  (`accounts/services/gl_validator.py` `check_freezing_date`) — but it sits
  on a tab of the Company form beside a role that may post anyway, and
  nothing leads there. **Lock Books** on the VAT Return sets it to the end of
  the period just filed, since a period that has been filed is not to
  change; the Books Check says where it stands. Locking leaves the role
  empty, so locked means locked for everybody, the Administrator too; to
  correct a locked period, unlock it, correct, and lock again.

  **The year-end close** is ERPNext's Period Closing Voucher, which moves the
  year's profit to an equity account and asks which. OneBook answers: the
  chart's Retained Earnings. The Books Check notices a year that has ended
  with entries in it and no closing, and **Close the Year** makes and submits
  the voucher, then locks the books to the year's last day. ERPNext posts it
  in the background.
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

  ERPNext builds a company's chart and most of its defaults when the company
  is made, and leaves a handful of things that nothing complains about until
  the first document that needs them. Each is a row of the **Books Check**
  (`report/books_check`) with what it means and, where one exists, the fix
  beside it. The ones that need no decision are made without asking:

  - **The bank.** The Standard chart has a *group* called Bank Accounts and
    no bank ledger, so the company's default bank account is empty and every
    bank mode of payment — Wire Transfer, Cheque, Credit Card, Bank Draft —
    has no account behind it: a payment by transfer does not know where the
    money went. **Add Bank Account** makes the bank, its ledger under that
    group and the company's Bank Account in one step, and a company bank
    account saved from anywhere fills the company default and every bank
    mode of payment that has none (`wired`).
  - **Tax.** Five UAE templates ship and none is the default, so an invoice
    carries no VAT unless somebody picks it. Which is the default is the
    business's decision, so the fix asks. ERPNext's default template only
    reaches an invoice made in its form. One made on the server (Invoice
    Time, Bill Progress, OneAI, Intake, an import) takes its taxes from a
    Tax Rule, so the fix also makes a Tax Rule for that template with the
    lowest priority, and the row asks again while none names it (`charge`).
    A business that zero-rates exports adds its own rules above it.
  - **The same bill twice.** ERPNext does not stop a supplier's invoice
    number being entered twice unless told to.
  - **The year.** A date outside every fiscal year stops every document on
    it. ERPNext makes next year's three days before this one ends, when the
    scheduler runs; the check catches a site where it did not.
  - **Reminding a late customer.** The Payment Reminder (`paid.py`) is
    shipped off, since it writes to customers; the fix turns it on.
  - **The UAE's VAT** (`vat.py`): the VAT accounts the return reads, the TRN
    a tax invoice must carry, and the emirate sales are reported under.
  - **A year that has ended is closed** (`closing.py`): its profit moved to
    Retained Earnings and the books locked to its last day.
  - **The defaults ERPNext throws on** — receivable, payable, income, cost
    center, round-off, exchange gain or loss — named when any is empty.
- `currency.py` — billing a party in their own currency. ERPNext refuses a
  document in any currency but the one on the party's receivable or payable
  account, and a document made in code starts in the company's. `bill_in`
  sets the company, the party's currency and its rate, as the form would;
  `rate` reads ERPNext's exchange rate, or the inverse of the one kept the
  other way. OneProject's contract, Invoice Time and Invoice Month and
  OneInventory's reorder all make their documents through it.

  A customer or supplier whose receivable or payable account is in another
  currency can only be billed in that currency: ERPNext refuses any other
  (`validate_party_account_currency`). Its forms pick the currency as the
  party is chosen, but a document made in code starts in the company's.
  `bill_in` sets what the form would: the company, the party's currency and
  its rate to the company's currency. `rate` turns an amount from one
  currency into another at ERPNext's own exchange rate (Currency Exchange,
  then its provider), or the inverse of the rate the other way when only
  that one is kept.

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

### access.py

ERPNext lets only a **System Manager** open three of the tools the rail
links to, or add a bank, and keeps the purchase tax templates from accounts:

- **Bank Reconciliation Tool** and **Bank Statement Import**: matching
  the bank's lines to payments is an accountant's daily work, so an Accounts
  User may do it and import a statement, and an Accounts Manager too.
- **Opening Invoice Creation Tool**: what customers and
  suppliers owed on the day the books start, entered once, by an Accounts
  Manager.
- **Banks**: the list of banks a bank account picks from. ERPNext lets only
  a System Manager add one, so One's own Add Bank stopped for everybody; an
  Accounts Manager adds one here and an Accounts User reads them.
- **Purchase Taxes and Charges Template**: ERPNext gives them to buying. The VAT a bill
  carries is the books' decision, so an Accounts Manager keeps them and an
  Accounts User reads them.
- **Suppliers**: a bill often comes from a new supplier, so an Accounts
  Manager adds one too (`RAISED`).
- **End of Service** (Gratuity): HRMS shows it to HR alone, but the books pay
  it, so accounts read it.
