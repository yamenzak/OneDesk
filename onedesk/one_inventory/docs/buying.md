# Buying

**Buying** in the rail goes the way buying does. It holds **Reorder**,
**Material Request**, **Request for Quotation**, **Purchase Order** and
**Supplier**. Supplier Quotations, the Supplier Quotation Comparison report
and Blanket Orders are under Everything on Home. Suppliers are kept in
OneBook, and the link here opens the same supplier. A supplier's **Items**
tab says what is bought from them, item by item: their own code for it,
whether they are its default supplier, the last price paid in their money
and what it was before, or what they agreed on a blanket order, how much was
bought in a year and in how many orders, what is on order and the lead time;
then what they quoted for and were never ordered from. Each opens the item's
Buying tab, which says the same from the item's side, and **New Purchase
Order** starts one with them.

1. **Ask for it.** Somebody who needs goods makes a **Material Request**,
   saying what, how many, for which warehouse and project, and when it is
   wanted.
   Its page says the **Project**, who it was **Requested By**, and under
   **Progress** how far it has got: Requested, Quoted (how many suppliers
   answered), Ordered and Received.
   The list leads with the title, which
   already names the items and whether they are bought or made, so it has
   no number or Purpose column; a request's lines take the request's
   Required By and leave it out of the table.
2. **Ask for prices.** **Request for Quotation** in the rail opens the
   page for asking suppliers. **Ask for Prices** on it picks the material
   request and the suppliers, and with **Email Suppliers Now** ticked mails
   each one a link; untick it to leave the request a draft to finish on its
   form. **Create › Request for Quotation** on the material request does the
   same from there. Submit it and **Send Email** mails each one a link. A
   supplier with a portal login prices it there, and their quote arrives as
   a draft with whoever asked told. A quote by mail is **Create › Supplier
   Quotation** on the request. A quote holds until its **Valid Till**, and
   expires by itself after.
3. **Compare.** The page has three tabs. **Request for Quotation** is a
   table of requests: what each asks for, where it stands (Draft, Waiting,
   Answered or Ordered), each supplier asked with a tick once they
   answered, and when it was asked and is wanted. A row's menu has
   **Compare**, **Add Supplier Quotation from** a supplier who has not
   answered, and **Open Request for Quotation**. **Supplier Quotations** is
   a table of suppliers' quotes: who, where it stands, the request it
   answers and the orders made from it, until when it holds, and its total
   in its own money, with **All**, **To Decide**, **Draft** and **Expiring**
   above it. **Comparison** sets one request's quotes side by side: each
   supplier's rate on each line, in their own money and in the company's
   currency for one in another money, with the cheapest live rate marked **Cheapest** (a quote past its
   Valid Till never is) and a
   line ordered already said as ordered. Under each supplier, **Add
   Supplier Quotation** types in the quote of a supplier who answered by
   mail, **Check Supplier Quotation** opens one still a draft, and
   **Order** drafts an order from a quote while a line it prices is left to
   order. **Order the Cheapest**, the main button on a comparison, drafts one order to each supplier for the
   lines they are cheapest on. The figures say how many suppliers are still
   to answer (**Waiting for Prices**), how many quotes wait for a decision
   or are still drafts, and how many run out within a week (**Expiring**).
   OneAI answers **Who has not answered?** and **Who is cheapest?** there.
   A request for quotation's own page says how many suppliers have
   **Quoted** and who is **Cheapest**, line by line. The **Supplier
   Quotation Comparison** report sets every quote side by side, in the
   company's money too. A quote says on how many of its lines it is the
   cheapest (**Lowest On**).
4. **Order.** **Create › Purchase Order** on the quote you take. Lines can
   go to different suppliers, each from whoever is cheapest on it.
   An order's page says the **Project**, its **Grand Total** while it is a
   draft, the **Blanket Order** it is agreed on, and under **Progress** how
   far it has got: Ordered, Received (in red once late) and Billed.
   **Supplier's Quote No** keeps the number on the supplier's own
   quotation as they wrote it (Q-12548 Rev 2), changeable after submit, and
   the order's print says it beside Required By.
   **Submit** sends nothing by itself. Print it or
   mail it from its menu. The list gives the supplier room for its name and
   the status room for "To Receive and Bill", without the number, and a
   line's own Required By stays out of the items table.
5. **Receive and pay.** See Receiving. The supplier's bill is
   **Create › Purchase Invoice**, and it is OneBook's from there.

- **Late orders.** Once a day, an order whose goods are past the date they
  were wanted and not all here is told to whoever made it (**Order Late**),
  once. Services are never late, and a closed order is done with. Close an
  order with **Status › Close** when nothing more is coming.
- **A price for the year.** A **Blanket Order** agrees a price and a
  quantity with a supplier from one date to another. An order line that
  names it is held to its price, and the blanket order says how much of it
  is **Ordered** so far. It prints as a **Blanket Order** for the supplier
  to sign.
- **Scoring suppliers.** A **Supplier Scorecard** scores a supplier each
  month on what was delivered on time and what was accepted on arrival, and
  can warn or stop a new order to a supplier who scores poorly. Its criteria
  come from the Inventory Check.
- **Buying Settings** (Setup) hold the buying price list, whether an order
  or a receipt must come before a bill, and how much over a request may be
  ordered.

## Ordering What Runs Low

Give an item a reorder level on its page's **Stock** view (**Set Reorder
Level**): the warehouse, the level, and how many to order each time. Once a
day, anything at or below its level gets a **Material Request** by itself.

**Buying › Reorder** lists what needs ordering: every request not yet
ordered, and every item that is low and not yet requested — why it is
there, how many, for which warehouse, from whom (the item's default
supplier, or whoever it was last bought from), what it last cost a unit and
what the line would cost. The figures above say how many lines
(**Items**), how many **Requested** and **Running Low**, and what it all
comes to before tax (**Cost**). Tick the
lines and press **Order**, or **Order All** with none ticked: one draft
purchase order is made for each supplier, and lines with no supplier go to
the one you pick (**Who Supplies the Rest?**). **New Material Request**
asks for something by hand. A supplier billed in another currency gets
their order in it. Read the drafts, correct prices and quantities, and submit
them. A request line held by draft orders leaves the list, and no order,
however it is made, can order more of a request line than is left on it.
A request is marked ordered when its order is submitted.

Purchasing is told of both: a request reordering raised (**Material Request
Raised**) and one a person asked for (**Material Request Asked**). A customer's
order not all delivered by its date is told the next morning to whoever made
it and the stock managers (**Delivery Late**).

A request to move, issue or make something reaches whoever keeps the stores,
or makes it (**Stock Asked**). Whoever asked hears when it is all moved or
issued (**Material Request Done**) and when somebody stops it
(**Material Request Stopped**). When reordering could not raise a request,
the stock and buying managers are told within the hour (**Reordering
Failed**). Subcontracted goods a day late back are told to whoever ordered
them (**Back From Supplier Late**).
