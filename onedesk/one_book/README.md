# OneBook

Written by hand. What OneBook does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneBook is where the money is kept: the invoices you send, the bills you get,
the payments either way, the bank, and the reports an accountant and a tax
office ask for. Every invoice, payment and journal entry is the same record
the rest of One reads — a project's billed amount, a customer's balance, an
employee's expense claim.

## Finding your way

**OneBook** in the dock opens it. Every row is called by the name of what it
opens, which is also the name **Ctrl+K** finds it by. The rail has:

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
- **Banking** — **Bank Transaction** (each line of a bank statement, to
  match), **Bank Statement Import** (bringing a statement file in) and
  **Bank Account** (each of the company's bank accounts: the bank, the IBAN
  and account number, and the account in the chart it posts to). Tick **Is
  Default Account** on the one you use most: an invoice prints it as the
  account to pay into, and the Bank Reconciliation Tool and a new statement
  import open on it.
- **Financial Reports** — **Profit and Loss**, **Balance Sheet**, **Cash
  Flow**, **General Ledger**, **Trial Balance**, **Gross Profit**, the **Tax
  Return** and the country's own return where there is one, such as the
  **UAE VAT 201** in the UAE.
- **Reports** and **Setup** open those parts of Home: every accounting report
  by what it is about, and the chart of accounts, cost centers, taxes,
  payment terms, modes of payment, fiscal years and settings, with the
  **Books Check** first.

Everything here is for whoever People gives OneBook. An **Accounts User**
matches the bank and imports a statement; an **Accounts Manager** also
enters the opening invoices, adds banks and suppliers, and keeps the purchase
tax templates.

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
  charts: **Cash Flow** (what came into
  and went out of the bank and cash accounts each month), **Profit and Loss**
  (each month's profit or loss) and **Top Expenses** (the five largest expense
  accounts and the rest); then, for **Accounts Receivable** and **Accounts
  Payable** each, the **Ageing** of what is owed by how late it is, who owes
  or is owed the most, and the year's invoices by status. Click a chart to
  open what it was drawn from.
- **Today** — overdue sales invoices, purchase invoices due this week or
  already late, unreconciled bank transactions by bank account, and drafts
  left more than a day, each row opening its document.
- **Everything** — every accounting screen, each by its own name and with a
  line on what it is for, with a search.
- **Reports** and **Setup** — their part of Everything, by topic.

Setup has every accounting setting, a country's own only when the company is
there. Among them: the **Email Digest**, a mail each day, week
or month of how the business is doing; **Plaid Settings**, for a bank Plaid
reaches; and the **Code Lists** an electronic invoice names its units and
taxes by.

## Getting ready

**Setup › Books Check** lists what would stop the first invoice, payment or
bill, and says **Ready**, **To Do** or **Suggested** beside each, with a
**Fix** button where there is one:

- **A bank account is set up.** **Fix** asks for the bank's name and the
  account's, and makes the account in the chart, the company's bank account,
  and connects every bank mode of payment — Wire Transfer, Cheque, Credit Card
  — to it. A bank account added any other way is connected the same way.
- **Invoices carry tax** and **Bills carry tax.** **Fix** asks which tax
  template is added to a new invoice or bill when nobody picks one, in a
  form and on every invoice or bill One, OneAI or an import makes.
- **A late customer is reminded.** **Fix** turns the payment reminder on.
- **Opening balances are finished.** Opening invoices and opening stock are
  posted against Temporary Opening; once every opening balance is in,
  an accountant moves what it holds to capital with a Journal Entry. Until
  then the Balance Sheet carries it, and the check says how much.
- **Every year that has ended is closed.** **Fix** closes the year (below).
- In the UAE: **the VAT return knows the VAT accounts**, **invoices carry
  the company's TRN** and **the company's emirate is known**. **Fix** fills
  the first from the chart and asks for the other two.
- **A supplier's bill cannot be entered twice.** **Fix** turns on the check
  that refuses the same supplier invoice number a second time.
- **Today is in a fiscal year** and **the company's default accounts are
  set** — both are made with the company, and the check catches a workspace
  where they were not.

## Opening balances

When the books start part way through a business's life, what customers
owed and what was owed to suppliers on that day goes in once, from **Home ›
Setup › Opening Invoice Creation Tool** (an Accounts Manager's):

1. Pick the **Invoice Type**: Sales for what customers owe, Purchase for what
   you owe suppliers.
2. Add a row per invoice still open: the party, the **Outstanding Amount**,
   and its **Posting Date** and **Due Date**. **Create Missing Party** makes a
   customer or supplier that is not there yet.
3. **Create Invoices** makes them as opening invoices, which count in
   Accounts Receivable and Accounts Payable like any other.

The bank's and every other account's opening balance is a **Journal Entry**
(below). When all of it is in, the Books Check's **Opening balances are
finished** says what is left in Temporary Opening to move to capital.

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
   unpaid, so a retention held for a year doesn't hide a late payment; in
   red once it has passed) and the **Grand Total**.
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

A purchase invoice works the same way from **Purchase Invoice**: the
supplier, what they charged for, **Submit**, and **Record Payment** when you
pay it. Money a supplier gives back is **Create › Return / Debit Note** on
their bill. **Credit Note** and **Debit Note** in the rail list these returns.

### A customer's and a supplier's page

**A customer's page** answers first their **Total Unpaid** (red when any of it
is late, and against their credit limit when one is set), what is
**Overdue** and how old the oldest is, their **Annual Billing** (with
how much more or less than by this day last year), the **Last Sales Invoice**, and
their **Open Orders**. Beside them, **Billed** is their year, a bar a month.
A supplier's page says the same from the other side: **Total Unpaid**,
**Overdue**, **Annual Billing**, the **Last Purchase Invoice**, **Open Orders** and
**Bought**. Every figure is worked out from the invoices your own list would
show you.

### Late payers and being told

**Reminding a late customer.** Once turned on (the Books Check's **A late
customer is reminded**), a customer is mailed the invoice a week after it
fell due, if it is still unpaid. It is the Payment Reminder rule, in its own
words, which cannot be changed while it is on.

**Being told.** The morning after an invoice goes past its due date unpaid,
whoever made it and the customer's account manager are told (**Invoice
Overdue**). On Monday morning accounts hear what supplier bills fall due that
week (**Bills Due This Week**). A customer paying through a payment link is
told to the same people as an overdue invoice (**Paid Online**), since no
person entered it; a deposit paid on an order the same way. A repeating
invoice or bill that was switched off, because the next could not be made,
is told to whoever set it up and accounts (**Repeat Failed**). **Credit Limit
Crossed** reaches the role Accounts Settings names as credit controller, with
who was stopped.

**Chasing by hand.** On an overdue invoice, **Create › Dunning** makes a
payment reminder listing every invoice of theirs that is late, how late, and
what is owed, with a fee or interest if its **Dunning Type** charges one. It
prints as **Payment Reminder**, with your bank to pay into. **Create › Payment
Request** sends a link to pay online. **Process Statement Of Accounts**
mails each customer their statement on a schedule, monthly or as often as you
set.

## Bills from mail and scans

A supplier's bill that arrives by mail, or is scanned in, is read by OneAI
and made into a draft purchase invoice, matched to its purchase order when
there is one. **Ready to Submit** in the rail lists the drafts whose facts
checked out and that you may submit; **Submit All** submits them as you.
Drafts that failed a check, such as a total that does not match or a bank
account that is not on file for the supplier, are listed in red under
**Needs Review** with the reason. Open one, correct it, and submit it as any
bill.

## Payments without an invoice

**Record Payment** on an invoice is the quick way. For anything else —
money on account, a payment across several invoices, a refund, moving money
between two of the company's accounts — use **Payment Entry › + Add Payment
Entry**:

1. Pick the **Payment Type**: **Receive**, **Pay** or **Internal Transfer**.
2. Pick the party (customer, supplier or employee), the **Mode of Payment**
   and the **Paid Amount**, and the bank's reference in **Cheque/Reference
   No**.
3. **Get Outstanding Invoices** lists what the party still owes or is owed,
   to settle with it.
4. **Submit.**

A payment says who it was to or from in its title, and, once it went through
a bank account, a track to **Reconciled** once it is matched to the bank
statement.

## Matching the bank

Each line of a bank statement is a **Bank Transaction**. To bring a
statement in:

1. **Banking › Bank Statement Import › + Add.** The company's default bank
   account is filled in.
2. Save, then attach the bank's file under **Import File** (**Download
   Template** gives a spreadsheet to fill when the bank's file will not do).
3. Check the preview and press **Start Import**.

A statement OneIntake reads from mail arrives as Bank Transactions the same
way.

To match them, open **Bank Reconciliation Tool**. It starts on the default
bank account; pick the dates and type the **Closing Balance as per Bank
Statement**, then press **Get Unreconciled Entries**. Each line has
**Actions**:

- **Match Against Voucher** — the payment or journal entry already in the
  books for it.
- **Create Voucher** — a new Payment Entry or Journal Entry for it, such as
  a bank charge.
- **Update Bank Transaction** — correct the line's reference or party.

The figures at the top compare the statement's closing balance with the
books' and show the **Difference**, which is nought once everything is
matched. **Auto Reconcile** matches the lines whose payment it can find by
their reference and amount, and leaves the rest to you.

A **Bank Transaction Rule** (Home › Setup) matches a bank line by its
description, such as DEWA's direct debit to Utility Expenses, so it is not
asked about each month. A bank account's page says what the books hold in it
and how many lines are still to match.

## Journal entries

A journal entry is for anything that is not an invoice or a payment:
correcting a posting, an accrual, depreciation by hand, an opening balance.

1. **Journal Entry › + Add Journal Entry.** Pick the **Entry Type** (Journal
   Entry for most, Opening Entry for opening balances).
2. Add a line per account under **Accounting Entries**, each with a
   **Debit** or a **Credit**. A line on a receivable or payable account also
   names its party. The debits and credits must be equal.
3. Write what it is for in **User Remark**, and **Submit**.

A journal entry nobody gave a title is named by what it is for — the
payroll's period, the asset it depreciates, or its remark — rather than by
its first account.

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

## Tax

**Financial Reports › Tax Return** is the figure for any tax return: for the dates you
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

Once a tax return is filed, the period it covers should not change. **Lock
Books** on the Tax Return asks for a date, and nothing dated on or before it
can then be entered, changed or cancelled — by anybody. The title of the Tax
Return says **Locked to** that date. To correct something in a locked
period, open **Lock Books** again and **Unlock**, correct it, and lock again.

At the end of a year, its profit is moved into **Retained Earnings**. The
Books Check's **Every year that has ended is closed** turns **To Do** once a
year has ended with entries in it; **Fix** closes it and locks the books to
its last day. The reports go on showing the year as it was.

## Customers and suppliers in another currency

A customer or supplier whose account is in another currency is billed in
that currency: their invoices, bills and the orders and invoices other apps
make for them take it, at the day's exchange rate. **Record Payment** does
not take a payment in another currency; use **Create › Payment** on the
invoice. Rates are kept under **Home › Setup › Currency Exchange**.

## Printing invoices and statements

**Print** on a sales invoice offers **One Sales Invoice** and its
**Classic**, **Bordered** and **with Images** looks, **One Simplified Tax
Invoice**, **One Detailed Tax Invoice** and **One Sales Voucher** (what was
posted to which account). Each line shows its tax rate
and tax, and the invoice names the company's bank account to pay into (the
one ticked **Is Default Account**). For a VAT-registered company in the UAE
it is headed **Tax Invoice**, or **Tax Credit Note** for a return, with the
company's TRN. A bill, a payment (**One Payment Receipt**), a journal entry
and a payment reminder print the same way.

**Print** on a customer gives their **Statement of Account**: this fiscal
year's invoices and payments, the balance after each, how old what is open
is, and where to pay. A supplier prints as a **Supplier Statement**.

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

## OneAI in OneBook

Open OneAI on a page and it offers what makes sense there. It reads the books
as you may see them and never posts, pays or changes anything in them.

- **On Home**: *How is the money doing?* says what is in the bank, what
  customers owe and how much is late, what is owed and falls due this week,
  and how profit went. *Who owes us the most, and how late?* and *What do we
  have to pay this week?* list the invoices behind them.
- **On a Sales Invoice**: *Where does this invoice stand?* says what is still
  owed, what is late, and the payments and credit notes that settled the rest.
  *Draft a payment reminder* writes a short, polite email for you to send.
  On the list, *Which invoices are overdue?*
- **On a Purchase Invoice**: *What do we have to pay this week?* on the list,
  and *Where does this invoice stand?* on one.
- **On a Customer**: *What do they owe, and how late?*
- **On Bank Transaction**: *Which bank lines are still to match?*

## Connections

- **From OneCRM**: A Sales Order is invoiced here with Create › Sales Invoice. Customers are kept in OneCRM.
- **From OneProject**: Invoice Time, Invoice Month and Bill Progress on a project make the customer's invoices. Bill Progress on a subcontract drafts the supplier's bill for the project's manager to check.
- **From OneInventory**: A receipt or a purchase order becomes the supplier's bill with Create › Purchase Invoice, and a delivery becomes the customer's invoice the same way. Each asset's depreciation is posted to the books by itself.
- **From OneHR**: Approved expense claims and payroll runs are posted to the books. The tax on expense claims counts in the Tax Return.
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
- `one/print_blocks.py`, a UAE invoice — a VAT-registered company's sales
  invoice prints as a **Tax Invoice** and a return as a **Tax Credit Note**,
  each with the company's **TRN** under its number, as the FTA asks (its
  Executive Regulation, Article 59). ERPNext heads every return "Credit Note"
  by itself; that automatic heading gives way, and one somebody chose is
  kept. A tax line says its rate once ("VAT 5%", not "VAT 5% @ 5.0").
- `print_format/one_sales_invoice` — the first format made only of the
  builder's own pieces: fields, ERPNext's tables, linked fields and static
  text, each shown or hidden by a condition, so a workspace changes any of it
  in the builder rather than in a template. The title reads Tax Invoice, Tax
  Credit Note, Invoice or Credit Note by the company's TRN and the return
  flag; the standing is a pill per status. What the builder could not reach
  became fields on the record, filled on save by `paper.py`: each line's
  **Tax Rate**, **Tax Amount** and **Amount incl. Tax**, from ERPNext's own Item
  Wise Tax Detail (Article 59 asks for the tax per supply), and **Pay Into**,
  the company's default bank account, which the Pay To block reads through.
  The dirham prints as AED, not its symbol, which reads differently on every
  printer (`paper.settle`). A retainer's invoice shows its hours without what
  they would come to: the amounts show only when the time is what the
  invoice bills. `patches/invoices_say_their_vat` fills the old invoices.
  Retention is said under the totals, from fields OneProject fills
  (`progress._said`): taxed when released, **Work Billed** and **Less
  Retention** above the Subtotal, the Retention lines left out of the table;
  taxed with the invoice, **Retention Held** and, until anything is paid,
  **Due Now** below the Total.
- One's version of each Sales Invoice format ERPNext ships, made the same
  way, and ERPNext's own turned off so the print menu offers each once
  (`one/print_blocks.py` `REPLACES`): **One Sales Invoice** for Modern, the
  UAE's Tax Invoice and the Return; **Classic**, the details in a shaded
  panel and the lines in a rounded table with their item codes;
  **Bordered**, the heading facts in ruled boxes and from whom and to whom
  side by side; **with Images**, each line led by its item's picture; **One
  Simplified Tax Invoice**, what the FTA asks of a simplified one (Article
  60: the seller, its TRN, the date, what, and the total with its tax);
  **One Detailed Tax Invoice**, with each tax and the amounts in the
  company's currency; and **One Sales Voucher** for ERPNext's auditing
  voucher, what was posted where, from the invoice's own lines and taxes,
  with room to sign. A purchase invoice prints the same way as **One
  Purchase Invoice** (the supplier's own number and date, due date) with
  ERPNext's three other looks, and **One Purchase Voucher** for ERPNext's
  Purchase Auditing Voucher: the supplier's account credited, each line's
  expense account and each tax's account debited.
- Payments, journals and reminders print the same way: **One Payment
  Receipt** (a receipt, or a payment when it's paid out, the amount large
  and what it settles), **One Payment Voucher** for ERPNext's Bank and
  Cash Payment Voucher (the accounts paid from and to, deductions, room to
  sign), **One Journal Voucher**, a journal entry's default, for ERPNext's
  Journal Auditing Voucher (each account debited and credited with its
  party and cost center), **One Journal Credit Note** for ERPNext's Credit
  Note, and **One Payment Reminder** for its Dunning Letter (the letter,
  each invoice overdue and by how long, fee and interest, and the bank to
  pay into, which a reminder now names as an invoice does). A payment order
prints as an instruction to the bank (the account to pay from, each payment
with the account it goes into, two to sign) and a bank guarantee as what it
is for, the bank behind it and what it cost. A payment request prints as
the request it is: how much, for what, and the bank and link to pay by.
Every other record OneBook submits prints from One's pieces too, rather
than frappe's Standard: a bank transaction (in or out, and what it was
matched to), a budget and how it's spread, a cost allocation, an exchange
rate revaluation, invoice discounting, a period closing, a share transfer
with both sides to sign, and the background runs (deferred accounting,
payment reconciliation, ledger reposts, a transactions deletion), each
saying what it did. A customer prints as a **Statement of Account** and a
supplier as a **Supplier Statement**: this fiscal year from the ledger, the
balance after each document, how old what's open is, and, to a customer who
owes, where to pay. A payment order has no total
of its own, and frappe's builder can't add one up. ERPNext's six
  POS Invoice formats have no version: One has no till, so it makes no POS
  invoices to print. ERPNext's nine report formats (Accounts Receivable,
  General Ledger, Trial Balance and the rest) stay its own: they print a
  report rather than a record, which frappe's builder doesn't lay out.
- `paid.py` `titled` and `journal.py` — what a payment and a journal entry
  are called. ERPNext titles a payment by the party's ID (an employee's
  reads HR-EMP-00013) and a journal entry by its first account (forty read
  Accumulated Depreciation - SGA). A payment takes the party's name; a
  journal entry nobody titled takes the asset it depreciates, the payroll's
  period, its remark or what it references. Two patches retitle the old
  ones.
- `public/js/bank.js` — the Bank Reconciliation Tool and a new Bank
  Statement Import start on the company's default or only bank account;
  ERPNext leaves both empty, and the tool draws nothing until one is
  picked. The tool's intro advertised ERPNext's separate Banking app, which
  One does not install, and is cleared.
- `heads.py`, the bank — a statement line says what came in or went out
  and whether it is matched, and names the payment with its reference that
  is not matched yet, as the tool would suggest; a bank account says what
  the books hold in it, how many lines are unmatched (into the tool) and the
  last statement line's date. A line is titled by what the bank wrote, not
  by the bank account (`custom/bank_transaction.json`).
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
- `vat.py` and `report/tax_return` — tax. ERPNext's UAE VAT 201 reads three
  things a new company does not have — UAE VAT Settings, the TRN, an address
  with an emirate — and says nothing; the Books Check asks. Its box 9 (VAT on
  expenses) sums a field on each bill that somebody is meant to type, so an
  untouched bill reclaims nothing and the VAT is paid twice: `reclaimed`
  (Purchase Invoice validate) keeps it at the bill's VAT until somebody types
  their own figure (`recoverable`, pure). `emirate` (Sales Invoice validate)
  copies the address's emirate onto an invoice not made on its page, since
  Frappe only fetches it there. The Tax Return reads tax rows of submitted
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

  **A return any country can read** is `report/tax_return`: tax charged on
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
  nothing leads there. **Lock Books** on the Tax Return sets it to the end of
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
  - **Tax.** ERPNext ships the country's templates and none is the default, so an invoice
    carries no tax unless somebody picks it. Which is the default is the
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
- **Purchase Taxes and Charges Template**: ERPNext gives them to buying. The tax a bill
  carries is the books' decision, so an Accounts Manager keeps them and an
  Accounts User reads them.
- **Suppliers**: a bill often comes from a new supplier, so an Accounts
  Manager adds one too (`RAISED`).
- **End of Service** (Gratuity): HRMS shows it to HR alone, but the books pay
  it, so accounts read it.

### ai.py

Four reads and no writes: `money_now` is Home's own figures and debts
(`story.read`), `late_invoices` is Today's list (`home._late`, the payment
schedule as ERPNext's Overdue reads it), `invoice_facts` is one invoice with its
schedule, payments and credit notes, and `bank_to_match` is Today's bank lines.
OneAI drafts a payment reminder as text for the reader to send; it is given no
tool that posts, pays or reconciles, because a ledger entry is the one thing a
suggestion card should never be.
