# An Item's Page

An item opens on a page of its own. Above its name is its brand, with the
brand's logo (taken from the brand's website when it has none), and what kind
of thing it is (a stock item, a service, equipment or a template for
variants), and **Made Here** when it has a bill of materials. Beside its name
is its picture, which you change by clicking it. Under its name is the one
thing worth saying, if anything: **Disabled**, **Low in** a warehouse, or how
many more are promised to customers than there are, and how many are being
made. Then its code, group, unit and how its stock is valued, each changed
where it is shown.

On the right are its first two barcodes. A new item is given its code as its
first barcode. **Manage Barcodes** adds, changes and removes them, and the
order you drag them into decides which two show.

The figures under that depend on what it is:

- **A stock item**: **On Hand** across every warehouse, **Free to Sell**
  (on hand, less what is promised to customers), **On Order** (and how many
  are being made), what it is worth in the books (**Stock Value**), and the
  price it was **Last Received** or **Last Ordered** at, or when it was
  **Last Manufactured**. Under On Hand and Stock Value is a line of the last
  twelve months and how much they moved this month, under On Order what was
  ordered each month, and under the last price the prices it was last bought
  at.
- **A service**: its **Selling Price** and what it **Sold in 12 Months**.
- **Equipment**: how many **Assets** it has become, and how many are not yet
  registered.

Then its views, each only where the item has it:

- **Overview**: what **Needs You** first, only when something does (past its
  end of life, more promised than there is, running low, an order late in or
  out, a request not yet ordered), then what was used and sent out, month by
  month for a year, its description and its details. A template lists its variants, and equipment
  its assets and who has each.
- **Stock**: each warehouse by its own name, with what it holds, what is
  promised, what is free to use and what it is worth, and a bar against its
  reorder level. The level and how much is ordered at a time are changed on
  the row, and **Set Reorder Level** gives a warehouse one. Each row's menu
  has **Transfer Stock**, which asks where to and how many, and **Count
  Stock**, which starts the count with the item and that warehouse filled in. Then its batches, and its last moves in
  plain words ("Moved 120 from Stores to Branch Store", "Used 80 on
  Head Office Move"), each with who made it. A move from one
  warehouse to another is one row.
- **Buying**: who it is bought from, each with their picture, the last
  price ordered and the one before it in their own currency (with the
  company's currency under it when it is another), what they agreed for the year and
  their part number, changed on the row. **Add Supplier** puts one on the
  item's list, and each supplier's menu has **Order from Them**, **Request
  for Quotation** and **Make Default**. Then the quotes still open, the cheapest
  marked, each with **Order This**. What is on order says how much has
  arrived and when it is due (in red once late), with **Receive**. What has
  been asked for says who asked and for which project, with **Make Order**.
  Each makes the next document as its own form's button does. Who makes
  it, each manufacturer with their part number changed on the row, the
  default marked (it goes on every order line), with **Add
  Manufacturer** and **Make Default**. The buying prices are changed on the
  row, and one that differs from the last price paid says so and offers
  **Use Last Price**.
- **Selling**: what customers have ordered and not yet had, each with how
  much has gone and whether what is on hand covers it. Stock goes to the
  orders soonest due first, so a row says **Can Go Now** or how many it is
  short. Each order's menu has **Deliver**, and **Invoice** while some of it
  is not billed yet. Then the quotes still open, in the customer's own
  currency with the company's currency under it, and until when (red within a week),
  with **Make Order** for a customer's quote. Then who bought it in the last
  twelve months with returns taken off, each with their picture, what they
  paid in their own currency, their last price and their own code for the
  item, changed on the row. Each customer's menu has **New Quotation**,
  **New Order** and **Set Customer's Code**. The selling prices are changed
  on the row, and one says when it was last sold below it. Each makes the
  next document as its own form's button does.
- **Manufacturing**: what it is made from, each material with how many its free
  stock would make, and "Enough for 182, Structural Silicone runs out
  first" over them. Then the steps that make it, each at its workstation
  with its minutes and cost, and what one costs in materials and in steps.
  Each work order still open says its project, how far each step has got
  and, once late, in red. Its menu has **Finish**, which records what has
  been made as the work order's own Finish does, and **Open on Shop Floor**,
  the Shop Floor at that work order. Then what
  was made in the last twelve months, and its bills of materials. A
  material bought rather than made shows only what it goes into and what
  the open work orders still need of it.
- **Files** and **Activity**, as on every record.

The main button is **Order More**, or **Make More** for something made here,
or **Add Variant** for a template. The menu has **Request Material**,
**Transfer Stock**, **Count Stock** (or **Set Opening Stock** for an item with
no stock yet), **Edit Details**, **Disable Item**, the **Stock Balance**,
**Stock Ledger** and **Stock Projected Qty** reports, and the usual Print,
Email, Duplicate, Rename and Delete. Each starts the document in its own form
with the item on its first line.

Every view keeps its own **Details** beside it: Stock has safety stock,
batches, serial numbers and weight, Buying has the buying unit, lead time and
minimum order, Selling the selling unit, discount and commission, and
Manufacturing whether it is used in manufacturing. Each is changed where it is
shown. The pencil (or the arrow on a choice) opens the item form's own field
there, so the workspace's scripts and rules hold, and leaving it or pressing
Enter saves. Escape puts it back. A field the form hides is not shown, and one
it locks can't be changed. An item with stock keeps Kept in Lots and Kept by
Number locked, since they cannot change once stock has moved.

**Edit Details** changes everything else about the item, grouped as Details,
Stock, Reordering, Units, Serial Nos and Batches, Variants, Buying,
Selling, Manufacturing, Quality, Asset and Accounts, with any field the
workspace has added under More. Its name is changed by clicking it.

OneAI reads an item as its page shows it, says what is running low, and
suggests a change to an item (its name, group, lead time, whether it is
disabled, or a warehouse's reorder level) as a card you approve.
