# Billing the Customer

What the customer agreed to, the invoices for the work as it gets done, and
the retention they hold back.

## What's Agreed With the Customer

A project for a customer holds two things agreed with them:

- **Payment Terms**: when an invoice is due, such as **Net 30**.
- **Terms and Conditions**: the wording printed at the foot of its
  quotations, orders and invoices.

**Add Project** fills both in. The payment terms are the customer's own when
they have some, else the template's, else the company's. The terms and
conditions are the template's, else the company's. Change either in the
dialog, or later on the project's **Details**. A project made another way (a Sales Order's
**Create › Project**, the form, Data Import) starts with the same, and a
Fixed Price one with its template's retention. An internal project has neither. A sub-project
with none of its own is billed on the nearest project above it that has some,
and its **Payment Terms** say which.

Every quotation, order and invoice made for the project starts with them:
**New Quotation**, the contract, **Bill Progress**, **Invoice Time** and
**Invoice Month**. An order made from a quotation keeps the quotation's, and
an invoice made from an order keeps the order's. Pick others on a document and
that document keeps yours. **Bill Progress** dates the invoice by the order's
payment terms, and any retention falls due after. A supplier's bill is due as
its purchase order says, not as the customer agreed.

**Add Contract** asks for the payment terms and the terms and conditions too.
Ones changed there become the project's.

### Contracts

The contract value is the customer's sales order. What gets signed is a
**Contract**, and a project can have as many as it needs: the main
contract, an addendum for extra work, a renewal, or a supplier's subcontract
agreement.

**Draw Up Contract** (under **Contracts** on the Overview)
asks who it is with: the project's customer, or one of its suppliers (those
ordered from for the project, and those on its contacts). It names the
project and runs over its dates. Its wording comes from a **Contract
Template**, or for the customer from the project's terms and conditions. A
supplier's contract needs a template. It opens in the Contract form, where you
record who signed it and when, then submit it.

**Contracts** on the Overview lists each one with who it is with, whether it
is signed and when it ends. A supplier's contract also shows on its card on
the **Suppliers** tab. While the project is open, Needs You says **Get
the contract signed** for each one not signed, and **Renew the contract** from
a month before a signed one ends, unless a later one with the same party runs
on past it.

**Draw Up Contract** shows to whoever may create contracts, such as a Sales
Manager. Everyone who reads the project sees the list. A contract's wording
opens only for those who may read contracts, since an employee's contract is
a Contract too.

## Billing the Work Done

The customer's contract is their **sales order** on the project, and a
project can have more than one: a variation ordered later is a second order
on the same project, and extra work is ordered on its own sub-project.
**Contract** adds up the orders on the project and those under it. With more
than one, the project's head says how many, **Orders** on the Overview (under
**Work and Billing**, with **Quotations** after it) lists each with where it is, what it's for, what's left to bill and how much of it
is billed (or its status when it's on hold or closed), and **Bill Progress**
asks which order to bill, each with where it is and what's left on it. The
heading's arrow opens the orders. **Bill Progress** (also under **Create** on a
submitted order) works as it does for a supplier: say how far the work has got and it drafts the invoice for that
share, less what's been invoiced already. On an order of several lines, such
as a bill of quantities, tick **By Line** to give each line its own share
done: 50% of the lights and 30% of the cabling bills 20 of 40 lights and 180
of 600 m. Each line shows what's ordered and what's billed so far, and the
invoice's **Work Done** is the share of the whole by value.

The customer's **Retention** is set three ways. The project holds the usual
one (**Retention**, **Retention Due** and **Released at Handover**, from its
template or the New Project dialog, changed on the project's **Details**). Each new
customer order on the project starts with it, and the order may change it,
say to 0 on extra work. Each invoice starts with its order's, and may change
it or set it to 0 before it's submitted. **Customer** under **Money** shows the **Retention Held** still to be
paid. **Retention** on the Overview sets what the customer holds (**From the
Customer**) beside what's held from suppliers (**To Suppliers**), across the
project and those under it, each with the rate when the orders agree and when
the first of it is due. A month before the customer's retention is due,
Needs You says to ask for it, and a supplier's past due says to pay it. The
project's manager is told on the day any of it falls due (**Retention Due**).
How it's held follows the order's **Tax on Retention**, and either way the
accounts are the standard ones. An invoice made from no order follows Projects
Settings.

- **With Invoice**: the invoice is for the whole amount, taxed whole, and
  the retention is a later part of its payment schedule. It stays in Debtors
  and Creditors until paid, and Accounts Receivable by payment terms shows it
  not yet due. **Release Retention** (and **Pay Retention** for a supplier)
  is a Payment Entry with each line naming its retention term, so those
  terms are marked paid and Debtors or Creditors goes down by what was
  held.
- **When Released**: the invoice holds the retention as **Retention** lines
  below nothing, one for the part released at handover and one for the rest,
  each with its **Retention Due**, so its tax is on the work less the
  retention. Tax on retention is due in the UAE when it's invoiced, paid, or a
  year after the work is certified complete, whichever comes first, and in
  the UK when it's invoiced or paid. What's held is booked to **Retention
  Receivable** (**Retention Payable** on a supplier's bill), made beside
  Debtors (Creditors) the first time, and isn't owed until it's invoiced.
  **Release Retention** is an invoice for it, one Retention line naming each
  invoice it releases (**Releases Retention Of**), taxed as that invoice was;
  submitted, it moves the retention into Debtors with its tax. An invoice
  takes a line below nothing only when **Allow Negative Rates for Items** is on in
  Selling and Buying Settings, so an order or the workspace choosing When
  Released turns it on. What a project has
  billed leaves the Retention lines out, so it reads the same either way.
  An order's Tax on Retention may change after it's submitted, until its
  first invoice, so Release Retention never meets one
  order's retention held both ways. Orders from before it was the order's
  say what their invoices already did.
  A credit note against such an invoice gives back the retention on the
  work it takes back, in Retention lines of its own that name no item
  (otherwise each would be held to the quantity of the line it returns,
  which is 1, however many credit notes share it), so what's held comes down with it.
  In the UAE the tax on retention falls due a year after the work is
  certified complete even if nobody has invoiced it, so a project keeps
  **Completed On**, the day it's marked Completed unless somebody changes
  it, and a month before that year is out Needs You says to invoice the
  retention.

Every invoice on a project is a **claim**. When it's submitted it gets the
next **Claim No** within its project; an amendment keeps the number of the
invoice it replaces. Its print adds where the contract stands as of it: the
**Contract** (the project's orders), **Billed Before**, **This Claim**,
**Billed to Date**, **Received to Date** and **Left to Bill**. Invoices
from before claim numbers got theirs in the order they were posted.

### Before the Customer Orders

A Fixed Price project can start before anything is agreed. **New Quotation**
(under **Quotations** on the Overview) starts a quotation for the project's customer, as often as you
need until one is ordered. While the customer's quotation is open,
**Customer** under **Money** shows what they've been **Quoted**,
**Forecast Margin** is worked out against it, and **Make Order** at the top
of the project turns the quotation into the sales order. A quotation with
alternative items opens instead, so you can pick which ones were ordered.
**Quotations** on the Overview lists the project's quotations not ordered
yet, drafts too, with where each stands. An ordered one is its order. **Work and Billing** shows once something is
ordered.

A project can have more than one quotation, a revised price or a choice of
two. With several open, **Quoted** shows the newest and says how many there
are, and clicking it lists them so you can order the right one. Mark a
quotation **Lost** once it's replaced, or cancel and amend it for a new
revision. A lost, expired or cancelled quotation no longer counts.

A quotation made outside the project, from a deal in {one_crm} or the
Quotation list, offers the customer's open projects to pick from. If the
customer has one open Fixed Price project with nothing ordered yet, it's
picked for you.

With no quotation and no order, **Add Contract** under **Contract** makes the
sales order from a **Contract Value**, the item to **Bill As** and any
**Retention**, as **Add Project** does. To change a contract once it's made,
change its sales order.

### Customers Billed in Another Currency

A customer whose account is in another currency, such as USD, is billed in
it. The contract value and a retainer's monthly fee are agreed in that
currency, and the contract, **Invoice Time** and **Invoice Month** make their
orders and invoices in it. Hours are turned into it at the day's exchange
rate. The project's own figures are all in your company's currency.

**Make Order** and **Add Contract** show to whoever may create sales orders;
**Add Contract** also needs the right to change the project.

## A Retainer's Months

A Retainer's **Overview** lists its months, newest first, from the one it
starts in: the hours used of the month's allowance, any over, and the
month's invoice. A month that has ended without one has **Invoice Month**.

**Invoice Month** (also the project's main button) asks for the month and the
item to invoice it as. It shows the hours used of the allowance, and any on
timesheets not submitted yet, which the invoice won't include. When the
month went over, a tick to bill the hours over adds a line for them at what the
month's hours were billed at on average; untick it to leave them. It opens a
draft invoice with the month's fee, any hours over, and the month's time on
it. Submitting it marks that time invoiced, so it's never billed again, and
the month shows its invoice. A month is invoiced once.

A retainer's hours are billed with its months, so **Invoice Time** isn't
offered on one. Its **Timesheet** shows this month's hours against the allowance
instead of amounts, and its **Invoices** has **Invoice Month** instead of
**New Invoice**.

## Invoices

The customer's invoices for the project and those under it, newest first.
Each says what it's for (**Work done 40%**, **9 h of time and costs**, a
retainer's month, **Credit note**, or its first item) and which sub-project
it's on, its date, when the part owed now is due (in red once it's past), its
status, total, and what's **Outstanding**, the figure the invoice itself
says. What of it is retention still held is said under it,
with the date it's due on hover. The customer and their logo show when there's more than
one customer. The figures and amounts are in the company's currency, said
once above them, as on **Suppliers**. An invoice in the customer's own
currency keeps its symbol.

The figures above are what's been **Invoiced**, **Paid** (with anything paid
in advance on the order), **Outstanding** (with what of it is held), and
**Overdue**. They count with tax, as the customer
pays, and only the project's part of an invoice that's partly another's.
Overdue says how many invoices are late.

**Release Retention** above the figures releases the retention, for the
parts due by today (or all of it when none is due yet). Where the order's tax on
retention is charged with the invoice, it opens a payment, not saved
yet, each part matched to its invoice's retention, so those parts show as
paid: check the amount, the account and the bank reference, and submit it.
Where it's charged when released, it opens an invoice for the retention, with
its tax, to check and submit; the customer then pays it as any other.
When the project's orders are taxed different ways, it opens the invoice
first, and pressed again after that, the payment.
**···** on an invoice offers Release Retention for that invoice alone.

**···** on an invoice offers **Record Payment** (how much, when, into which
account) and **Send**, which opens the invoice with its email ready and the
invoice attached. **New Invoice** starts one for the customer on the
project; **Invoice Time** and **Bill Progress** are at the top of the project.
Shown on a project with a customer, to whoever may read invoices; Record
Payment to whoever may make payments.
