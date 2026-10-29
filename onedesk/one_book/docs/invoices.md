# Invoices and Bills

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

### A Customer's Page

**A customer's page** answers first their **Annual Billing** and **Total
Unpaid**, then what is **Overdue** and how old the oldest is, the **Last Sales
Invoice**, and their **Open Orders**. Beside them, **Billed** is their year, a
bar a month. A supplier's page says the same from the other side: **Annual
Billing**, **Total Unpaid**, **Overdue**, the **Last Purchase Invoice**, **Open
Orders** and **Bought**. Every figure is worked out from the invoices your own list would
show you.

### Late Payers and Being Told

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

## Bills From Mail and Scans

A supplier's bill that arrives by mail, or is scanned in, is read by OneAI
and made into a draft purchase invoice, matched to its purchase order when
there is one. **Ready to Submit** in the rail lists the drafts whose facts
checked out and that you may submit; tick them and **Submit** submits them
as you. It lists every draft OneAI read, so an order, a quotation or a
receipt it read is there beside the bills. Drafts that failed a check, such as a total that does not match or a
bank account that is not on file for the supplier, are marked **Needs
Review** with the reason. Open one, correct it, and submit it as any
bill.

## Repeating Invoices and Bills

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
