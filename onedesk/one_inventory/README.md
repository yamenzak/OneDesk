# OneInventory

Written by hand. What OneInventory does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneInventory is what the company holds: the goods it buys and sells or uses up
(stock), and the equipment it keeps — laptops, vehicles, tools (assets). It is
where things arrive from suppliers, leave for customers and move between
places, where the workshop makes them, and where you order more. It shares
its records with OneBook, so a delivery here is the same record an invoice in
OneBook is made from, and an asset's depreciation lands in OneBook's books by
itself.

## Finding your way

**OneInventory** in the dock opens it on **Home**. Over it, six figures,
each against last month and drawn over its months: **Stock Value**,
**Received This Month**, **Delivered This Month**, **Manufactured This
Month**, **To Receive** (still on order) and **Stock Ledger Entries This
Month** (how many moves). Each opens its list. **New Item**, **New Purchase
Receipt**, **New Stock Entry** and **New Material Request** start one.

- **Overview** opens first. A button for each kind of thing that needs
  somebody (3 Late Orders, 1 Item Running Low) leads to Today. Then the story
  of the stock, in six parts:
  - **Where Stock Is**: its worth by warehouse, by item group, and the most
    valuable items.
  - **How Stock Moves**: its worth month by month, what came in and went out
    each month by kind, where goods came from and went (supplier to
    warehouse to customer, project or the workshop), the busy days, and the
    papers by kind.
  - **How Old Stock Is**: its worth by age, as the **Stock Ageing** report
    counts it.
  - **Buying**: how far the material requests got, what was bought from
    each supplier, and how each supplier keeps to its dates.
  - **Making**: the work orders by status, what was made each month, and
    the hours at each workstation.
  - **Equipment**: its worth by kind, bought against now, the assets by
    status, and the services by month.

  A slice or a bar opens what it stands for: a warehouse's stock, an item
  group's items, a supplier's orders, the work orders or assets in a status.
- **Today** lists what needs somebody, each kind only when there is some:
  **Late Orders** (purchase orders with goods past their date), **Running
  Low** (with **Order**, which opens Reorder), **Expiring Soon** (lots near
  or past their date), **Maintenance Due** (late or due this week), **Work
  Running Late** (work orders past their date) and **Left as Drafts** (receipts,
  deliveries, moves and counts started more than a day ago). Each row opens
  what it is about.
- **Everything** lists all of OneInventory, each with a line saying what it
  is for, under Stock, Buying, Manufacturing, Quality, Assets, Reports and
  Setup, and a
  search. **Reports** and **Setup** in the rail open their part of it.

The rail keeps what people use every day:

- **Item**, **Stock Summary**, **Purchase Receipt**, **Delivery Note**,
  **Stock Entry** (moves), **Stock Reconciliation** (counts) and **Batch and
  Serial No**, which holds lots and serial numbers together. See Batches and
  expiry dates.
- **Buying** — **Reorder**, **Material Request**, **Request for Quotation**,
  **Purchase Order** and **Supplier**. See Buying.
- **Manufacturing** — **Shop Floor**, **Plant Floor**, **Work Order**, **BOM**
  (bills of materials) and **Subcontracting Order**. See Manufacturing.
- **Assets** — **Asset** and **Asset Maintenance**.
- **Reports** — the stock, buying, making and asset reports, each with what
  it shows.
- **Setup** — the **Inventory Check** first (what is missing before stock
  can be kept right), then warehouses with their putaway rules, stock
  dimensions and stock closings, item groups, brands, units and attributes
  (from One's **Masters**) with variant settings, supplier groups and
  scorecard variables, price lists, workstations, plant floors, operations,
  routings, Replace in Bills of Materials, subcontracted items, asset
  categories, locations, maintenance teams, shift factors, delivery
  settings, and the stock, buying and manufacturing settings.

**Batch and Serial No**, **Request for Quotation**, **Subcontracting Order**
and **Asset Maintenance** each gather several kinds of record. At the top of
each is the same view switch a list has. **List View** and **Report View**
open those records as a list or a report, and the reports that go with them
are there too. On those lists the switch leads back to the page.

Everything else (blanket orders, job cards, asset movements, pick lists,
packing slips, delivery trips, landed costs, item prices, item alternatives,
lead times, standard costs, quality inspections, supplier scorecards,
production plans and their timeline, production schedules, sales forecasts,
the bill of materials builder, downtime, value adjustments, asset
capitalization and shift allocations) is in **Everything** on Home. When
something about stock, buying, making or assets is not on the rail, look
there first.

## A new item

**Add Item** on the Items list asks what kind of thing it is first:

- **Kept in Stock** — counted in a warehouse.
- **Service** — work or a charge, never stocked.
- **Equipment** — owned and used, like a van or a laptop. It becomes an asset
  when it is bought.
- **Sizes or Colours** — one product in several versions. Pick the sizes and
  colours it comes in, and each combination becomes its own item.

The Items list has a tab for each kind: **All**, **Kept in Stock**, **Made
Here**, **Services**, **Equipment** and **Sizes or Colours**.

**Details** asks for its name, group, unit and a picture. **Sold by Size**
says whether each line gives its length (**Length**) or its length and width
(**Area**), so the quantity follows; a size that only prints, on something
counted by the piece (**Piece**), like a curtain-wall panel; or none (**No**).
See Selling by size.

**Buying, Selling and Stock** has a switch for each side. **Sold to
Customers** opens its selling price. **Bought from Suppliers** opens its
buying price and usual supplier. **Made in Our Workshop** adds a step for what
it is made from. **Order More When Low** opens the level to reorder at and how
many to order. **Kept In** and **On Hand Now** put its first stock in a
warehouse.

**Made From** lists the parts that go into one, with their quantities. It
becomes the item's bill of materials. **Add from a List** reads a parts list,
uploaded as a spreadsheet or CSV file or pasted in, with a code, name,
quantity and unit on each row. It matches each part to an item by its code, a
supplier's part number or its name, shows which are new, and adds the new ones
as stock items when you press **Add Parts**.

## Selling by size

Glass, sheets, profiles, concrete and the like are sold by size. An item
whose **Sold by Size** says **Length**, **Area** or **Volume** gets
**Pieces**, **Length**, **Width** and **Height** on every line it is on, as
many of them as it needs: quotations, orders, deliveries, invoices, purchase
orders, receipts, stock movements, bills of materials and the rest. The
quantity is worked out from the size, in the line's unit, and the price,
tax, stock and cost follow from the quantity as on any other line.

- 4 glass panels of 1200 × 800 mm, sold by the square metre, come to
  3.84 m².
- 6 profiles cut at 2400 mm, sold by the metre, come to 14.4 m.
- 2 slabs of 100 × 50 × 20 cm of concrete, sold by the cubic metre, come to
  0.2 m³, or 200 litres if the line is in litres.
- An item kept by the piece says how big one piece is when it is made, such
  as a sheet of 3.125 m². Two sheets of 1250 × 2500 mm then come to 2 sheets.
- Any unit with a conversion set up also works, such as square feet.

Sizes are typed in the line's **Size Unit**: any length, such as
millimetres, centimetres or inches. A line takes it from its item's Size
Unit, and an item without one from the workspace's, in Stock Settings,
which is millimetres until somebody changes it. Change a line's unit and its
quantity follows. A line keeps the unit it was saved with, so changing the
workspace's later doesn't change what an old order meant.

An item counted in a length, an area or a volume, such as metres, square
feet or litres, is set to be sold by it when it is made or its unit
changes. A sheet kept by the piece is set by hand.

The size columns show only once a line's item is sold by size, and the quantity
shows its unit, such as 3.840 m². The size prints under the item's name on
quotes, orders, invoices and the other printed records, such as
"4 × 1200 × 800 mm", in the line's own unit. A quotation's sizes carry to the order made from it, and
on from there.

A unit that must be whole, such as Nos, stays whole. Selling 3 m² from a sheet
kept by the piece is refused, because that is not a whole sheet.

## An item's page

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

## Stock on hand and warehouses

**Stock Summary** in the rail says what the stores hold now. At the top are
what it is all worth (**Stock Value**), how many **Items** are held, how many
are **Low** (at or below their reorder level) and how many are **Short**
(more promised to customers than there is); the Low and Short figures narrow
the list to theirs.

Above the list are the warehouse picker (**All Warehouses** or one), a search
by name or code, and **All**, **Low**, **Short** and **Out of Stock** with how
many of each. Each line is an item: its picture, its name with its code and
group under it, one status (In Stock, Low, Short or Out of Stock, the worst
that is true), then **Actual Qty** (on hand), **Reserved Qty** (promised to
customers), **Available Qty** (on hand, less what is promised), **Ordered
Qty** (on order) and its **Stock Value**. A quantity carries its unit, and
nothing is a dash. On a phone a line keeps the picture, the name, the status
and Available Qty. An item opens on its own page. The page changes as stock
moves.

The main button is **Transfer Stock**, which asks only where from (the
warehouse that is open), where to, which items and how many, and the
project and a note when there are, then makes and submits the Material
Transfer. **Open Full Form** in it opens the whole Stock Entry form instead.
The menu has **Count Stock**, **Add Warehouse**, and the **Stock Balance**
and **Stock Projected Qty** reports, each for the warehouse that is open.

**Setup › Warehouses** shows every warehouse in its tree, opened all the way
down. A warehouse's form says how many **Items** it holds, their **Stock
Value**, how many are **Below Reorder Level** (which opens Stock Summary for
it) and when stock last moved in or out (**Last Stock Entry**). A group
warehouse counts everything under it.

OneAI reads the stores as Stock Summary shows them, for every warehouse or
one, and says what is short or running low.

## Getting ready

**Setup › Inventory Check** lists what would stop the first receipt, stock
count or asset, with **Ready**, **To Do** or **Suggested** beside each and a
**Fix** where there is one:

- **Somewhere to keep stock** and **stock is valued in the books** — a
  warehouse, and the company's stock accounts. A new company has both.
- **Stock has a warehouse to go to.** Without one, every receipt and count
  asks for a warehouse on each line. **Fix** makes the Stores the company's
  default.
- **Stock cannot go below zero.** If it could, what it is worth would go
  wrong with it. **Fix** stops it.
- **Running low asks for more.** An item at its reorder level gets a
  material request each night. **Fix** turns this on. **Reorder** lists
  what is low either way.
- **Rejected goods are not billed.** To begin with, what was rejected on
  arrival is billed too. **Fix** bills only what was accepted.
- **Stock can be held for an order.** Off to begin with, so stock promised
  to one order can go out on another first. **Fix** turns it on.
- **Every warehouse posts to a stock account** and **Stock values are up to
  date** — stock and the books agree. See When stock and the books disagree.
- **Suppliers can be scored.** Nothing to score them by to begin with.
  **Fix** adds Delivered On Time and Accepted on Arrival, each out of 100.
- **Workshop time is costed.** Making goods that take time at a workstation
  fails until the company names an account for that time. **Fix** uses the
  company's account for costs included in stock value.
- **Work orders know their warehouses.** Without them, each new work order
  asks where its materials go and where what it makes is kept. **Fix** sets
  the company's Work In Progress and Finished Goods.
- **Serial and batch numbers can be used.** Off to begin with, so no item
  can have serial numbers or batches. **Fix** turns them on. An item then
  has **Has Serial No** and **Has Batch No**.
- **Somewhere for an asset to be.** An asset needs a location. **Fix** asks
  what to call the first — Head Office, say.
- **Assets have categories.** **Fix** makes Computers and Software (written
  off over three years), Furniture and Office Equipment (five) and Machinery
  (ten), each kept in the chart's matching Fixed Assets account. Change the
  years under **Setup › Asset Categories**.
- **Depreciation posts itself.** Without it, depreciation is worked out but
  never posted unless somebody does it. **Fix** turns it on, so each
  asset's depreciation is posted to the books when it falls due.

## Buying

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
   currency for one in another money, with the cheapest live rate marked **Cheapest** and a
   line ordered already said as ordered. Under each supplier, **Add
   Supplier Quotation** types in the quote of a supplier who answered by
   mail, **Check Supplier Quotation** opens one still a draft, and
   **Order** drafts an order from a quote while a line it prices is left to
   order. **Order the Cheapest** drafts one order to each supplier for the
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

## Manufacturing

**Manufacturing** in the rail is the workshop: **Shop Floor**, **Plant
Floor**, **Work Order**, **BOM** and **Subcontracting Order**. Job cards,
subcontracting receipts and production plans are under Everything on Home,
and workstations, plant floors, operations and Manufacturing Settings under
Setup.

1. **Say how it is made.** A **BOM** (bill of materials) names what one of
   a product takes, and with **With Operations** the steps (cutting,
   assembling, glazing) and the workstation each is done at, with its
   minutes. Its page says its **Cost per Unit** in materials and time, its
   **Operations**, and how many **Work Order** use it.
2. **Make it.** A **Work Order** makes so many of a product, for stock,
   for a project or for a customer's order. Somebody who needs goods made
   asks with a **Material Request** of type Manufacture, and **Create ›
   Work Order** on it keeps who asked. Its page says the **Project**, the
   **Sales Order or Material Request** it is for, and under **Progress**
   how far it has got: Planned, Material Transferred, Operations (how many
   steps are done) and Manufactured (how many of how many).
   **Print** gives the floor its sheet: what to make, the materials and
   where they come from, and each step.
3. **Send the materials.** **Start** moves the materials from the stores to
   Work In Progress.
4. **Work each step.** Submitting the work order makes a **Job Card** for
   each step. Whoever works it logs their time and how many they did, in
   order. A job card done in part keeps the rest as still to do. Its page
   says the **Work Order**, the **Workstation**, the **Total Completed
   Qty**, the **Total Time in Mins** and the **Employee** who did it.
5. **Finish.** **Finish** on the work order puts what was made into
   Finished Goods, valued at its materials and its workshop time. Whoever
   asked for it and the project's manager are told (**Work Order Done**)
   once all of it is made.

### Shop Floor

**Shop Floor** under Manufacturing is the page for the people in the
workshop. Over it, how many **Open Work Orders** there are, how many steps
someone is on now (**Running Now**), how many are **Waiting to Start**, and
how many were **Closed Today**. **New Work Order** starts one.

- **Open** is a table of the work orders still on the floor: the item with
  its number and project, its status, the step it is at and where, how
  many are made with a bar, how many of its steps are done, and when it is
  wanted, red once that is past. **Completed** lists the finished ones.
  Each workstation has a tab of its own with its steps, the oldest first.
- **A work order** shows its steps as cards, each a job card: the operation
  and its workstation, its status, who is on it and the clock while it
  runs, how many are done of how many with a bar, what of its materials is
  short in the stores, and whether it needs a quality check before it
  closes, with one button for what comes next and the rest in its menu.
  **Finish** puts what was made into stock, as on the work order.
- **Start** asks when it started and who is on it, the reader first. A
  running step has **Pause**, and a paused one **Resume**.
- **Record Made**, in the step's menu, asks how many were made and lost and
  when the session ended. **Close Operation** closes the step, its quality
  check first when it needs one. **Carry On Later** records the session and
  leaves the step paused for the next. A step whose sessions are all
  recorded has **Close Operation** as its button.
- **Transfer Material** makes the stock entry that moves what the step
  still needs to it. **Check Quality** takes the readings of the step's
  quality check and records them. A rejected check keeps the step open.
  **Read Instructions** shows the operation's own instructions. **Open Job
  Card** opens the step's job card.
- A step that makes a part of its own (**Receive Into Stock**) puts it into
  stock once closed.

Everything on it is the job card itself, so the job card's form, its time
logs and its reports say the same. It changes as soon as somebody else
starts or closes a step.

### Plant Floor

**Plant Floor** under Manufacturing shows a floor's workstations as cards.
Over it, how many **Workstations** there are, how many are in
**Production**, how many are **Stopped** by a problem or for maintenance,
and how many **Operations Running**.

- Each card says the workstation's type, its status with its colour, each
  step running on it with who is on it and its clock, and how many steps
  wait to start there. Its name and **Operations** open the workstation's
  steps on the Shop Floor, and the gear (**Open Workstation**) opens the
  workstation.
- The status is a menu on the card (**Change Status**): Production, Off,
  Idle, Problem, Maintenance or Setup. Every open Plant Floor changes with
  it.
- **All Types** and **Any Status** narrow the cards. A workspace with more
  than one floor has a tab for each.
- **Stock Here** is a table of what the floor's warehouse holds, how much of
  it is kept for work orders, and how much is on its way, each with its
  unit. **Add Stock** and **Move Stock** make the stock entry as a draft to
  check and submit.
- A floor is set up with **New Plant Floor**: its name and its warehouse.
  **Edit Plant Floor** changes it. A workstation joins it with **Plant
  Floor** on the workstation.

### What making costs a project

The materials a project's work order uses count in the project's Stock Used
on OneProject.

### Sending work out to a supplier

A product a supplier makes from your materials, powder coating say, is a
**Subcontracting BOM** (Setup) naming the supplier's service.
**Subcontracting Order** in the rail keeps that work on one page.

- The figures say how many orders are **Open**, how many still have
  **Material to Transfer**, how many are **Late** back, and what our
  materials **With Suppliers** are worth at cost.
- **Open** is a table: what the supplier makes with its number and
  project, the supplier, where it stands, what went to them (**Supplied**),
  how much is **Received** with a bar, and when it is **Due**, red once
  late. **Received** is the same table of those done with, with when each
  went.
- **New Subcontracting Order** starts the purchase order for the
  supplier's service, marked **Is Subcontracted**. A purchase order with no
  subcontracting order yet is listed under **Not Ready to Send**, with
  **Make Subcontracting Order**.
- In an order's menu, **Transfer Material** opens the transfer of your
  materials to the supplier and **Subcontracting Receipt** the receipt of
  what they made into the stores, both as drafts to check and submit.
  **Open Purchase Order** opens the order it came from.

The supplier's bill is made from the purchase receipt the subcontracting
receipt creates. A subcontracting order's page says the **Project**, its
**Total**, and under **Progress**: Ordered, Material Transferred and
Received. OneAI answers **What is out with suppliers?** there. This is not
OneProject's subcontract, which is a package of work on a project.

## Receiving

Goods arriving from a supplier are taken in on a **Purchase Receipt**. Open
the purchase order and press **Create › Purchase Receipt**, or start one with
**New Purchase Receipt** on Home. Check the quantities against what came,
and submit it to put the goods into stock.

**Purchase Receipt** in the rail lists every delivery with its supplier,
where it stands, its date, its total and how much of it is billed. A
supplier's delivery note read from mail is already there as a draft, marked
as made by OneAI.

A receipt says above its fields its **Project**, the **Purchase Order** it
came on, what it is worth in the company's money (**Stock Value**, with the
supplier's own currency beside it when that is another; a service on it,
such as coating sent out, at what it cost), the **Landed Cost Voucher**
added to it, how much was rejected (**Rejected Qty**), and under
**Progress**: Ordered, Received and Billed. Under the exchange rate it says
what one of the supplier's currency is in the company's.

- **Something broken or wrong on arrival.** Put what came under Received, what
  you keep under Accepted, and the rest under Rejected with the warehouse it
  waits in. Only what was accepted goes on the shelf. An item marked
  **Inspection Required before Purchase** needs a quality inspection on its
  line before the receipt can be submitted. An inspection marked Rejected
  stops the whole receipt, so a delivery that is partly bad passes its
  inspection and has the bad part rejected on the receipt.
- **Freight and duty.** **Create › Landed Cost Voucher** on the receipt, add
  each charge, and submit. What each item cost goes up by its share, and the
  receipt says so. The accountant may add them too.
- **The bill.** **Create › Purchase Invoice** charges for what was accepted,
  once **Rejected goods are not billed** is Ready in the Inventory Check.
- **Paper.** A receipt prints as a **Goods Received Note**, with what was
  received, accepted and rejected on each line, signed by whoever delivered and
  whoever received.

Whoever asked for the goods on a material request is told when they arrive.
OneAI says what came in on a receipt, what is still to arrive and what is
late, and drafts a receipt for what arrived on an order as a card you approve.

## Delivering

The customer's order is OneCRM's and the invoice is OneBook's. What happens
between them is here.

Goods leave for a customer on a **Delivery Note**. On the submitted sales
order, press **Create › Delivery Note**, check what is going, and submit it
to take the goods out of stock.

**Delivery Note** in the rail lists every delivery with its customer, where
it stands, its date, its total and how much of it is billed.

A delivery says above its fields its **Project**, the **Sales Order** it is
for, its **Grand Total** in the customer's money (with the company's beside
it when that is another), the **Delivery Trip** taking it out with its date
and driver, and under **Progress**: Ordered, Delivered and Billed. Its line
says when some of it came back.

- **Hold stock for an order.** On a submitted sales order, **Stock
  Reservation › Reserve** sets stock aside for its lines, once **Stock can be
  held for an order** is Ready in the Inventory Check. No other order can
  deliver it. An item's page says how much of what is promised is held, and
  Free to Sell counts it once.
- **Pick it.** **Create › Pick List** on the order says what to take from
  which warehouse. It prints as a **Pick List**, signed by whoever picked and
  whoever checked. **Create › Delivery Note** on the pick list makes the
  delivery from what was picked. An order with stock held for it is
  delivered straight from the order instead.
- **Pack it.** **Create › Packing Slip** on a draft delivery says what went
  in which cases and what they weigh. It prints as a **Packing Slip** with the
  customer's address, signed by whoever packed and whoever received.
- **Take it to site.** **Create › Delivery Trip** on the submitted delivery
  names the driver, the vehicle and when it leaves, with a stop at the
  customer's address. **Notify Customers via Email** tells each customer on
  the trip it is coming. The route buttons appear once a Google Maps key is
  set in Google Settings.
- **Paper.** A delivery prints as a **Delivery Note**.

OneAI says what went out on a delivery, what is still to deliver for a
customer or project and how much of it is held, and drafts a delivery for what
an order still needs as a card you approve.

## Ordering what runs low

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

## Buying equipment

A laptop, a desk, a van: make it an item once, with **Is Fixed Asset** ticked
and its **Asset Category** (Computers, Furniture…). Then buy it like anything
else — a purchase order and a receipt. Each one received becomes an asset on
the register by itself: kept at your location, in use from the day it was
bought, and depreciating as its category says from the end of that month.

An asset's page says what it is worth now (**Value After Depreciation**),
what it cost (**Net Purchase Amount**), its **Depreciation**, how many
months of its life are written off (**Depreciations Booked**, with a line
showing how far through) and the **Next Depreciation**. Once registered, a
chart beside them, also **Value After Depreciation**, is a line from what it
cost to what it will be worth at the end, one point per depreciation its
schedule books.
The Inventory Check's **Every asset is registered** turns **To Do** if one
could not register itself, and each says why on its page.

Equipment you already had is **Asset** in the rail, then **Add Asset**,
with **Is Existing Asset** ticked. The list says who has each piece.

## Who has what

On an asset's page, **Give To…** asks for the employee and hands it over.
Once somebody has it, **Hand To…** passes it to somebody else and **Take
Back** returns it to a location. The person is told it is in their care.
Each handover prints as an **Equipment Handover** for them to sign: what
they were given, who gave it, and that they will look after it and give it
back when asked.

The asset says who has it, and the person's own page says how much
equipment they hold, to whoever runs HR as well. When somebody leaves, HR
submits their separation, and it gets a **Return** task for each thing they
hold, given to the stores.

## Servicing equipment

**Asset Maintenance** in the rail keeps servicing and mending on one page.
The figures say how many services are **Due This Week**, how many are
**Overdue**, what is **Out of Order**, and the **Repair Cost** over the
last twelve months. Each tab is a table, one status to a row.

- **Planned** lists each service not done yet, the soonest first, with the
  asset, the job, Overdue, Due Soon or Planned, who does it, how often and
  when, red once late. **Mark Done** asks the **Completion Date** and the
  **Actions Performed**, records them in the maintenance log and works out
  the next date from that day.
- **Asset Repair** lists what broke, what is wrong and how many days it has
  been out of use, then the repairs finished, with what each cost.
- **Asset Maintenance** lists each asset's servicing plan: its team, and
  each job with how often and when it is next due.
- **Completed** lists what was done, services with who did them and repairs
  with what they cost, the latest first.

**New Asset Repair** reports a breakdown and **New Asset Maintenance** plans
servicing. OneAI answers **Which services are due?** and **What is out of
order?** there.

Tick **Maintenance Required** on an asset that needs looking after, then
**New Asset Maintenance**: the asset, the maintenance team, and a row
per job — what it is, how often (monthly, quarterly, yearly…), from when,
until when if it stops, and who does it. Each due date is on that person's
calendar as **My Maintenance**, and on everybody's as **Maintenance Due**
when they turn it on, each named after the asset it is for; clicking one
opens it to record it done, and the next one is worked out from that day.
**Asset Maintenance Log**, under Everything on Home, lists every service
with its asset. The asset's page says its next service (**Next Due Date**),
in red once it is late.

The first schedule needs a maintenance team. The Inventory Check makes one.

Whoever does a service is told a week before it is due. Once it is late,
they and the team's manager are told. A schedule brought in from a
spreadsheet or by OneAI has its dates worked out the same as one typed in.

## Mending equipment and its value

When something breaks, **New Asset Repair** on Asset Maintenance: the
asset, when it failed, and what is wrong. The asset shows **Out of Order**
until the repair is **Completed**. The garage's bill is entered as a
supplier bill first, booked to repairs, and the repair takes its cost from
it. The repair says how long the asset was out of use (**Downtime**) and
what it cost (**Repair Cost**). The asset counts its repairs (**Asset
Repair**).

When something is worth less than its books say, after damage for
instance, an **Asset Value Adjustment** (under Everything on Home) sets its
new value. The difference is posted to the account you choose, and it says
the **Current Asset Value**, the **New Asset Value** and the **Difference
Amount**.

## Moving stock

**Stock Entry** in the rail lists every movement with its type, where it came
from, where it went, its project and what it moved. **New Stock Entry** on
Home starts one: pick its type (Material Transfer to move between warehouses,
Material Issue to use stock up, Material Receipt to add it), fill in the
warehouses and the lines, and submit. **Transfer Stock** on Stock Summary
moves stock from the warehouse you are looking at in one step.

A movement says above its fields which **Project** it is for, its **Stock
Entry Type**, which warehouses it went from and to (**Default Source
Warehouse** and **Default Target Warehouse**), what it is worth (**Total
Value**), and for goods made, what making them used (**Total Outgoing
Value**). A transfer sent through Goods In Transit says how much has
arrived (**% Transferred**).

- **To a site.** A site is a warehouse of its own, with its address on it.
  A transfer to it prints as a **Transfer Note** with the site's address,
  every line from and to, and spaces for whoever sent and whoever received
  it. Put the project on it, and what it moved counts on the project.
- **Used on the job.** A **Material Issue** from the site warehouse, for the
  project, takes what was used off the shelf and puts its cost on the
  project. It prints as an **Issue Note**.

OneAI says what a movement did, and drafts a transfer to a site as a card you
approve.

## Counting stock

**Stock Reconciliation** in the rail, then **Add Stock Reconciliation**
(or **Count Stock** on Stock Summary or an item's page). Choose the
warehouse, and **Fetch Items from Warehouse** lists everything the books
say is there. Type what you actually counted over the quantities and
submit. A new count starts as a count, so the
difference is written off or found in the stock adjustment account and the
books match the shelf. Only the lines whose quantity changed are kept.
The first count of a new warehouse is how you enter opening stock. Set
**Purpose** to **Opening Stock**, and its value goes to Temporary Opening.

A count says above its fields what it was for (**Purpose**), the
**Warehouse** it was counted in, how many **Items** it changed, and the
**Difference Amount** it made in the books.

OneAI says what a count found and what it did to the books.

## Batches and expiry dates

**Batch and Serial No** in the rail keeps lots (batches) and serial numbers
in one place. The figures say how many lots are in stock (**Batches in
Stock**), how many go off within a month (**Expiring Soon**), how many have
gone off (**Expired**) and how many numbered pieces are in stock (**Serial
Nos**), the company's own. Three tabs follow.

- **Batches** is a table of each lot with something left, the one going off
  first, with one status (Good, Expiring Soon within a month, Expired, or
  Keeps for a lot that never goes off), when it was made, when it goes off
  and in how many days, what is left in each warehouse, and how much in
  all. **All**, **Expiring Soon** and **Expired** above it narrow it, and
  the Expiring Soon and Expired figures do too.
- **Serial Nos** is a table of each numbered piece with its status, where
  it is or the customer it went to, its lot, and when its warranty ends.
- **Items** lists the items kept in lots or by number, and how each is
  numbered.

### Tracking an item by batch or serial number

**Track Batches** sets an item up to be kept in lots or by number in one
step: **By Batch** or **By Serial No**, whether new lots are numbered for
you and how (**Automatically Create New Batch**, **Batch Number Series**),
whether lots go off and how many days one keeps (**Has Expiry Date**,
**Shelf Life In Days**), or how serial numbers run and how long the warranty
is. It offers only items that have never moved, since how an item is kept
cannot change once it has. **New Batch** makes a lot by hand, with when it
was made and when it goes off. Left empty, the date is worked out from how
long the item keeps. Each receipt asks which lot or numbers came in.

When lots are switched off for the workspace, the page says so and
**Turn On** switches them on, as the Inventory Check does.

An item's Stock view shows the same lots and numbers, with **New Batch**,
and **Track by Batch or Serial No** for an item that has not moved yet. Its
Overview says **Expiring Soon** for a lot that runs out of date within a
month and **Expired, Still in Stock** for one past its date, so it is used,
sold or taken out of stock first. The stock managers are told once when
a lot with some left will expire within a month. **Batch Item Expiry
Status** and **Available Batch Report** are under Reports.

A lot's page says what is left (**Batch Quantity**), its **Manufacturing
Date** and **Expiry Date**, the receipt it came from (**Source Document**),
and how many times some was taken out (**Issued**), which opens its trace.
Its stock levels, Move and Split are on the lot's form as usual.

OneAI answers **Which lots go off soon?** and **Where is each numbered
piece?** on the page.

## Quality

**Quality** under Everything on Home has quality management beside the
inspections. A **Quality Inspection** checks goods on the way in, on the way
out or while they are made.
A **Quality Procedure** says how a piece of work is done, step by step. A
**Quality Goal** says what the business means to achieve against it, and how
often it is checked; each check is a **Quality Review**, objective by
objective, and a failed one asks for a **Quality Action**, with who fixes what
by when. Work that did not follow its procedure is a **Non Conformance**. The
**Quality Meeting** keeps an agenda and minutes that point at reviews and
actions, and **Quality Feedback** asks a customer or a colleague the
questions of a template (Setup's Quality). The **Review** report lists every
action with the review it came from.

## When stock and the books disagree

A back-dated entry, such as a count dated last week, makes the stock values
after it be worked out again. **Stock values are up to date** in the
Inventory Check says when a recalculation stopped with an error, and **Fix**
tries it again. **Every warehouse posts to a stock account** says when a
warehouse's stock is posted to an account that is not a stock account, so
stock and the books can never agree. Both are told to the stock and accounts
managers as **Reposting Failed** and **Stock Account Wrong**.

## Who may do what

A **Stock User** reads the equipment register and does its upkeep:
maintenance, its log and teams, repairs and quality inspections. A **Stock
Manager** runs all of it, value adjustments and capitalization included.
Whoever manages items, stock or buying keeps the item prices; whoever uses
stock or buying reads them. Out of the box these belong to accounts, quality
and manufacturing roles nobody in a small business is given, so One gives
them to the roles People hands out.

Using OneInventory includes making: its users make bills of materials, work
orders and job cards, and its managers also run Manufacturing Settings and
which supplier makes what for the company.

Whoever works in HR reads the equipment register and its handovers, to see
what a person holds and ask for it back when they leave. They change none
of it.

## Asking OneAI about stock

The OneAI panel offers questions that fit the page you are on. Press one, or
type your own.

- **Home**: **Which orders are late?**, **What is running low?** and
  **Which services are due?**
- **An item's page**: **How is this item doing?**, **Should I order
  more?** and **Change this item…**, which suggests a change as a card you
  approve.
- **Stock Summary**: **What is running low?** and **What is short?** A
  warehouse: **What is this warehouse worth?**
- **Receiving and buying**: on a receipt, **What came in on this receipt?**
  and **What is still to arrive?**; on a purchase order, **Receive this
  order**, **Which orders are late?** and **What is still to arrive?**; on a
  material request, **Ask suppliers for prices** and **Compare the
  quotes**; on Request for Quotation, **Who has not answered?** and **Who
  is cheapest?**
- **Delivering**: on a delivery, **What went out on this delivery?** and
  **What is still to deliver?**; on a sales order, **Deliver this order**.
- **Moving and counting**: on a stock entry, **What did this movement do?**
  and **Send stock to a site**; on a count, **What did this count find?**
- **Manufacturing**: on the Shop Floor, **What is running on the floor?**
  and **What is the workshop making?**; on the Plant Floor and a
  workstation, **How are the workstations doing?**; on a work order, **How
  far along is it?**; on a BOM, **Make a work order**; on Subcontracting
  Order, **What is out with suppliers?**
- **Batches**: **Which lots go off soon?** and **Where is each numbered
  piece?**
- **Equipment**: on an asset, **How is this asset doing?**, **Hand this to
  somebody…** and **Which services are due?**; on Asset Maintenance, **Which
  services are due?** and **What is out of order?**

Whatever OneAI would change or make, such as a receipt, a delivery, a
transfer or a work order, comes as a draft card you approve first.

## What is kept where

OneCRM keeps customers, quotations and the sales order a won deal becomes;
OneBook keeps invoices, bills, payments and suppliers; OneInventory keeps
items, stock, what arrives and what is delivered, what is ordered from
suppliers, what the workshop makes, and the company's equipment. See OneBook's README for the whole
split.

## Connections

- **From OneCRM**: A customer's Sales Order is delivered here with Create › Delivery Note. What open orders promise is taken off an item's Free to Sell, and stock held for an order is counted once. The order says at the top how much has gone out, and since when it is late.
- **From OneHR**: A delivery trip's driver is an employee, named on the trip and on the delivery it carries. Whoever works a step logs their time on its job card as an employee.
- **From OneProject**: Material requests, requests for prices, purchase orders and stock issues started on a project's page are put on that project. A work order for a project names it, and so do the movements it makes. A purchase order says its project, and how much is received and billed, at the top. A stock entry says its project, its type and the value it moved.
- **From OneBook**: Suppliers are kept in OneBook, and Buying › Supplier opens the same supplier there. A supplier billed in another currency gets their order in it. Asset categories use the Fixed Assets accounts in the chart.
- **From OneAI**: A supplier's delivery note read from mail becomes a draft Purchase Receipt against its order. A supplier's quote becomes a draft Supplier Quotation, and so does one priced on the portal. A supplier's bill for an order, such as the coater's, becomes a draft bill against the order, due when the bill says.
- **To OneBook**: A receipt or a purchase order becomes the supplier's bill with Create › Purchase Invoice. A delivery is invoiced the same way, and each asset's depreciation is posted to the books by itself. A count's difference is posted to the stock adjustment account, and stock that does not agree with the books is told to the accountant. A repair takes its cost from the garage's bill, and an asset's value adjustment posts a journal entry.
- **To OneProject**: A project's Buying colours each order, request and receipt as urgent as its page here says it is, and Reorder and Request for Quotation name a request's project by its name. What is ordered, received and issued for a project counts in its Cost. A purchase order for a package of work is a subcontract on the project's Suppliers view. Stock sent to a site and used there for a project counts the same way, and so do the materials a project's work orders use. Its manager is told when one is made.
- **To OneHR**: An employee's page shows how much equipment they hold, to HR as well, who may read the register. A person given equipment is told and signs the handover. When they leave, HR submits their separation, and it gets a Return task for each piece, given to the stores.
- **To OneCalendar**: Each maintenance due date is on the calendar of whoever does it, and on everybody's under Maintenance Due.

## Under the hood

For the people who build OneInventory. OneAI does not read past this heading.

### What it is made of

ERPNext's Stock, Buying and Assets modules: Item, Warehouse, Bin, Stock Entry,
Stock Reconciliation, Purchase Receipt, Delivery Note, Material Request,
Purchase Order, Asset and the rest are theirs. What OneInventory adds is the
shape — one place for the three modules a small business uses together, where
ERPNext has three sidebars and a fourth for selling — and the places their
inventory fails on first use or leaves a question unanswered.

**Why assets are here and not an app of their own.** An asset is bought the
way stock is — ERPNext makes it from the Purchase Receipt of an item marked
**Is Fixed Asset** — sits somewhere the way stock does, and is looked after by
the same people. What the accountant needs from it, depreciation, is posted to
the books by itself every day, and the asset reports are OneBook's to read as
well. The product line has no mark for a separate assets app, and an app with
a register and a movement form in it would be a rail with five rows.

- `kinds.py` and `public/js/item_new.js` — New Item. `KINDS` sets the
  ERPNext fields each kind needs (is_stock_item, is_fixed_asset,
  has_variants), and `make` saves the item as ERPNext's form would: its item
  defaults, reorder level, opening stock, attributes and versions, prices on
  the workspace's buying and selling price lists, and its bill of materials
  from Made From (`_recipe`, submitted when the reader may). Made here is
  ERPNext's own default material request type, Manufacture, which production
  planning reads too. The dialog is frappe's Slides in a dialog, each step a
  dialog's form from the start (`onedesk.project.Step`). `stocked` is the
  Items list's on-hand figure, summed as the page sums it.
- `parts.py` — Add from a List. `parse` is pure and reads a heading row when
  there is one; `read` matches each part by code, a supplier's part number
  (Item Supplier) or name; `add` makes the missing parts stock items in Raw
  Material, bought and not sold.
- `measure.py` and `public/js/measure.js` — selling by size. Item's
  `one_measured_by` (Sold by Size: No, Piece, Length, Area or Volume), set by
  `follows_unit` before_validate from ERPNext's UOM Conversion Factor
  category when the item is made or its unit changes, and on every table in
  `LINES` the custom fields one_measured_by (fetched from the item),
  one_pieces, one_length, one_width, one_height, one_size_uom and one_size.
  The size unit is the line's, the item's (`one_size_uom`) or Stock
  Settings' (`one_size_uom`, millimetres by default; `size_unit`), and must
  be a length (`metres`, by ERPNext's conversion to Meter); `sized` writes
  it on the line, so a line keeps what it was typed in. `amount` multiplies
  as many sides as the kind has (`POWER`), each turned into metres. `sized`
  runs before_validate on every record (`doc_events` "*"), so the quantity
  holds under bulk edit, Data Import and ERPNext's mappers. A Piece line
  keeps its quantity and gets only `one_size` (`described`). `factor`
  converts a metre, square metre or cubic metre to the line's unit by the
  item's own conversion first, then ERPNext's UOM Conversion Factor. The
  form script sets the quantity as the size is typed, shows the size
  columns only where a line is measured (Height only where one is a
  volume), offers only lengths as a size unit (`for_boot`'s `lengths`), and
  the unit's symbol beside the quantity. The shipped print formats merge
  one_size under the item's name. `patches/sizes_say_their_unit` wrote
  millimetres on every line that had a size before units.
- `number_card/` — the six figures over Home as frappe Number Cards (Stock
  Worth, Taken In This Month, Sent Out This Month, Made This Month, Still on
  Order, Moves This Month), each counted by its method in `story.py`
  (`stock_worth`, `taken_in_this_month` and so on). Any frappe dashboard or
  workspace can show them, and frappe shows each only to somebody who may read
  the record type it names.
- `story.py` and `frontend/src/home/InventoryStory.vue` — Home's Overview.
  `read` gives the six figures, each its Number Card's own value, with their
  months, and each part of the story,
  read through `frappe.get_list` so permissions and record access hold, and
  a part the reader may not see comes back empty. Moves are the stock
  ledger's papers since the story starts, each named for what it was from the
  paper itself (`_kinds`). Worth by month is today's less what moved since,
  so the last month always equals Stock on Hand. Ages are ERPNext's Stock
  Ageing, in five bands. The page draws it with frappe-ui's charts, colours
  by what a chart shows: a kind of move keeps its hue, statuses keep theirs
  (done green, under way blue, late red), and age and busy days run light to
  dark.
- `home.py`, `page/inventory` and `frontend/src/home` — Home. `needs_you`
  reads what needs somebody through `ai.late_orders`, `ai.running_low` and
  `ai.services_due` (OneAI reads the first and last through
  `still_to_arrive(late_only=True)` and `upkeep_now(days=...)`) and
  `batches.dated`, each as the reader may see it, `FEW` rows of each with how many more. `drafts` counts papers left
  as drafts more than a day. `EVERYTHING` is the directory, each entry with
  what it is for, shown only when the reader may open it (a doctype's read
  permission, a report's or page's own roles). The rail's Reports and Setup
  are Page links to it with a route (`/desk/inventory/reports`).
- `lots.py`, `page/lots`, `frontend/src/lots` and
  `public/js/lots_actions.js` — Lots. `read` gives the figures and one tab:
  `lots` (Batch with something left, sorted by expiry in Python, each with
  `batches.state` and `batches.left`), `serials` (Serial No, in stock
  first) or `kept_in_lots` (items with has_batch_no or has_serial_no). The
  item's Stock view reads the same `lots` and `serials` through `view.py`,
  drawn by the same `LotRows` and `SerialRows`. Track Lots sets the item's
  own fields (has_batch_no, create_new_batch, batch_number_series,
  has_expiry_date, shelf_life_in_days, or has_serial_no, serial_no_series,
  warranty_period) with `frappe.client.set_value`, so ERPNext's Item rules
  apply. Its item picker is `can_be_tracked`, items with no stock ledger
  entry. New Lot inserts a Batch with `frappe.client.insert`, and ERPNext
  numbers it and works out its expiry. Turn On runs the Inventory Check's
  `serials` fix. OneAI's `lots_and_numbers` reads the page.
- `quotes.py`, `page/quotes`, `frontend/src/quotes` and
  `public/js/quotes_actions.js` — Quotes. `read` gives the figures and one
  tab: `asked` (Request for Quotation with its suppliers' quote_status and
  each one's quote, `_answers`), `quotes` (Supplier Quotation with the
  request it answers and the orders made from it) or `compare`. `compare`
  sets a request's lines against each supplier asked, rate and base_rate
  from Supplier Quotation Item, the cheapest live base_rate marked, and a
  line ordered when the quotes' ordered_qty covers it. Every change is
  ERPNext's mapper: `ask` runs Material Request's
  `make_request_for_quotation`, inserts it and, sent, submits it and runs
  `send_supplier_emails`. Add Their Quote calls
  `make_supplier_quotation_from_rfq` with `for_supplier`, as the request's
  form does. Order opens `supplier_quotation.mapper.make_purchase_order`,
  and `order_cheapest` runs it per supplier with `filtered_children` for the
  lines they are cheapest on, leaving drafts. OneAI's `quotes_now` reads the
  page.
- `sent_out.py`, `page/sent_out`, `frontend/src/sent_out` and
  `public/js/sent_out_actions.js` — Sent Out. `read` gives the figures and
  one tab of Subcontracting Orders by ERPNext's own status (`OUT` or
  `DONE`), each with its items (qty, received_qty) and supplied items
  (supplied less returned, consumed). `figures` values the stock in the open
  orders' supplier warehouses from Bin. `to_order` lists subcontracted
  purchase orders with no subcontracting order. Every change is ERPNext's
  call, as the Subcontracting Order's form makes it:
  `purchase_order.mapper.make_subcontracting_order`,
  `subcontracting_controller.make_rm_stock_entry` and
  `subcontracting_order.make_subcontracting_receipt`. OneAI's
  `sent_out_now` reads the page.
- `upkeep.py`, `page/upkeep`, `frontend/src/upkeep` and
  `public/js/upkeep_actions.js` — Upkeep. `read` gives the figures and one
  tab: `due` (Asset Maintenance Log not submitted, Planned or Overdue),
  `repairs` (Asset Repair, open first, with the days since it failed),
  `plans` (Asset Maintenance with its tasks) or `log` (submitted, completed
  logs and submitted repairs). `done` completes and submits a log as its
  form does, and ERPNext's own `update_maintenance_task` moves the task's
  next date. OneAI's `upkeep_now` reads the page.
- `public/js/page_views.js` — the view switch on Lots, Quotes, Sent Out and
  Upkeep. `onedesk.page_views` names, per page, the doctypes it gathers (with
  the tab that shows each) and the script reports that go with them.
  `switcher` draws frappe's own switcher in the page's head (the
  `views` option of `onedesk.island_page`), with List View and Report View
  per doctype. ListViewSelect's `get_view_options` is wrapped so the
  switcher on those doctypes' lists has the page as its first row.
- `floor.py`, `page/floor`, `frontend/src/floor` and
  `public/js/floor_actions.js` — the Shop Floor. `read` reads through
  ERPNext's own Shop Floor (`manufacturing/page/shop_floor`): its
  `get_work_orders` for the board and its count, and its `get_data` for a
  work order's or a workstation's job cards, with their materials,
  instructions, quality check and time logs. `_step` says what each step's
  buttons may do now (`may`), as ERPNext's page offers them. `figures`
  counts open work orders by ERPNext's own bucket, and running, waiting and
  closed-today job cards. Every change is ERPNext's whitelisted call, made
  from `floor_actions.js` in frappe's dialogs: Workstation's
  `update_job_card` (start_timer, pause_job, resume_job), Shop Floor's
  `save_and_continue`, `complete_and_submit`, `submit_job_card`,
  `make_manufacture_stock_entry`, `get_quality_inspection_checklist` and
  `submit_quality_inspection`, and Job Card's `make_stock_entry`. The page
  follows Job Card and Work Order through frappe.realtime. ERPNext's own
  page stays at /desk/shop-floor. OneAI's `on_the_floor` reads what is
  running.
- `plant.py`, `page/plant`, `frontend/src/plant` and
  `public/js/plant_actions.js` — the Plant Floor. `read` reads ERPNext's
  own `workstation.get_workstations` for a floor's cards and its filters,
  the steps running on each workstation (`floor.running_now`), and
  `plant_floor.get_stock_summary` for the floor's warehouse, leaving out
  items with nothing there. Change Status saves the workstation's status,
  which ERPNext tells every open Plant Floor about. Add Stock and Move Stock
  run the Plant Floor's own `make_stock_entry` and open the draft. ERPNext's
  Visual Plant Floor stays at /desk/visual-plant-floor. OneAI's
  `plant_floor_now` reads it. Plant Floor is read by the Manufacturing User
  and kept by the Manufacturing Manager (access.py), as ERPNext gives it to
  the System Manager alone.
- `view.py`, `page/item_view` and `frontend/src/item` — an item's page. An
  item is the hub of the stores, as a project is of a job, so it opens on a
  page of its own (one/tiers.py PAGES) at its own address; `?edit=1` is the
  form. `read` gathers what ERPNext keeps in a dozen places, each as the
  reader may see it: the Bins per warehouse with their reorder levels, the
  stock ledger's last moves (each Stock Entry by its type, a transfer's two
  rows made one by the pure `merged`, each with who made it), suppliers from
  the item's own table and its submitted orders, open purchase and sales
  orders with what is still to come, material requests, prices, its bills of
  materials, what they go into and the work orders making it. `headline` is
  pure. The supplier's last two prices, a blanket order still running, the
  quotes still open and the last price paid come from the submitted
  documents, each in its party's currency with its base amount. What the
  page changes it changes as desk does, and
  `public/js/item_actions.js` has Edit Details (every field, its tables in
  frappe's grid, a row's company the workspace's own) and the documents an
  item starts, each opened in its form with ERPNext's own triggers filling
  the line. The page keeps frappe's sidebar and menu and hears the item and
  its stock change. Each view is a place for OneStudio
  (`oneinventory_item.*`). `_trends` draws the head's lines from the ledger's
  balance per warehouse at each month's end (a stock count sets a balance
  without moving any), the purchase orders per month, and `item.rates` the
  last prices bought at. The fields shown in each view's Details are the
  item form's own, held out of sight by the kit's `useForm` and lent where
  they are shown (`FieldEdit`, docs/READY.md point 6).
- `batches.py` — lots. ERPNext keeps a lot's moves in the Serial and Batch
  Entry rows of each move's bundle, so `left` and `moves` read those, per
  warehouse, and `state` (pure) says Expired or Expiring Soon. A lot's head
  is in `heads.py` (`batch.*`), and `tell.expiring` tells whoever keeps the
  stores once a day. A lot's name is ERPNext's own hash; people read its
  `batch_id`.
- `barcodes.py` and `frontend/src/item/ItemBarcodes.vue` — barcodes, in
  ERPNext's own Item Barcode table. `coded` gives a new item its code as its
  first barcode on every path an item is made by. `save` keeps the order the
  dialog leaves, so the first two are the head's. They are drawn by frappe's
  own Barcode control in the format their type names.
- `stock.py`, `page/stock_on_hand` and `frontend/src/stock` — Stock on
  Hand. ERPNext's Stock Balance answers it over a period and is a prepared
  report, so the rail's first look at the stores was an empty page with a
  Generate button. `on_hand` reads the Bins, which ERPNext keeps current with
  every move, as the reader may see them, and `rows` (pure) adds them up per
  item, low by ERPNext's own test (projected quantity at or below the
  warehouse's reorder level). The page follows the stock ledger and the Bins,
  and is a place for OneStudio (`oneinventory_stock.on_hand`). A warehouse's
  head is in `heads.py`, and a group's figures cover the warehouses under it.
- `public/js/warehouse_tree.js` — the warehouse tree without ERPNext's Company
  filter, opened all the way down once.
- `heads.py` (Purchase Receipt), `print_format/one_purchase_receipt`,
  `public/js/purchase_receipt_list.js` and `public/js/rate_note.js` —
  receiving. The receipt's head reads its lines: their orders, what they were
  valued at once received (landed costs included), and what was rejected. The
  goods received note is laid out in frappe's builder from One's print blocks
  (`one_studio/print_blocks.py`). `rate_note.js` writes the rate under every money
  document's exchange rate, where ERPNext writes "[?]". `access.py` lets the
  accountant add landed costs.
- `heads.py` (Delivery Note), `print_format/one_pick_list`,
  `print_format/one_packing_slip`, `public/js/delivery_note_list.js`,
  `custom/delivery_note.json`, `custom/driver.json`, `trips.py` and
  `public/js/delivery_trip.js` — delivering. The delivery's head reads its
  lines' orders and the trip stop that names it. The two prints are laid out
  in frappe's builder from One's print blocks, the packing slip's party read
  from its delivery. A driver shows by name in a trip, through frappe's
  `show_title_field_in_link`. `trips.py` tells the trip form whether Google
  Settings has a key, and `delivery_trip.js` hides the two route buttons and
  the distance when it has none. Free to Sell is on hand less what orders
  want: ERPNext's `reserved_qty` already counts what is held
  (`reserved_stock`), so it is taken off once (`item.summary`, `stock.rows`).
  OneCRM's `access.py` lets the selling, stores, accounts and projects people
  read Selling Settings, which ERPNext's sales order form reads on opening.
- `heads.py` (Stock Entry, Stock Reconciliation), `print_format/one_stock_entry`,
  `public/js/stock_entry_list.js`, `custom/stock_entry.json` and
  `custom/stock_reconciliation.json` — moving and counting. A movement's head
  reads its lines' warehouses, and what it is worth by what it did. The
  transfer note is laid out in frappe's builder from One's print blocks, its
  party the one warehouse the lines go to, with that warehouse's address.
  ERPNext leaves Total Amount empty for goods made, so the list shows what
  was made there. A new count starts as Stock Reconciliation, where ERPNext
  starts it with no purpose and the form fetches Temporary Opening as the
  difference account. `tell.stock_values`, hourly, tells the stock and
  accounts managers of a failed recalculation (`ready.failed_reposts`) and a
  warehouse posting to an account that is not a stock account
  (`ready.wrong_accounts`, as ERPNext's `get_warehouse_account_map` resolves
  it). ERPNext mails the second only to System Managers, and marks the first
  failed without a hook when no outgoing mail is set. `access.py` lets the
  stock, purchase, accounts, projects and manufacturing users read Stock
  Settings, which every order, receipt, delivery, movement and invoice form
  reads on opening.
- `heads.py`, `tell.py`, `access.py` and `ready.py` on buying. A material
  request, a request for quotation, a supplier quotation and a blanket order
  each have a head. Who is cheapest is read line by line in the company's money
  (`_quoted`, `base_rate`), so a quote in euros compares, and an expired
  quote never counts. `tell.orders_late`, daily, tells whoever made an order
  whose stock or asset lines are past their date and not all received, once
  per order (`tell.late`). ERPNext tells nobody. ERPNext gives Blanket Order
  and the Supplier Scorecard kinds to the System Manager alone, the
  operator's role, and `access.py` gives them to the purchase and sales
  roles. ERPNext ships no scorecard criteria, so a scorecard cannot be made
  until `ready.add_criteria` adds two from its own variables. A quote priced
  on the portal (`one/portal.send_quote`) takes each line's project from the
  request, which ERPNext's own rows leave out and an order from the quote is
  then refused for. A request for quotation's title is its number, where
  ERPNext titles it with the company's name. One Blanket Order prints the
  agreement for the supplier.
- `heads.py` — where a document stands. A purchase order, a material
  request, a receipt, a delivery, a work order and work sent out each open
  on a sentence saying what is next, coloured by how urgent it is (late is
  red), then a track of their stages, Ordered → Received → Billed → Paid on
  an order, each done, the one it is at, late or still to come
  (`*.progress`, drawn by `band.steps`). A BOM and an asset have the
  sentence alone. Modelled on Shopify's order page. The band keeps only what
  the form does not already say: the project, the order it came from, what
  it is worth. A note on a step says one thing, as a sum and a date side by
  side reorder around an Arabic currency sign.
- `making.py`, `heads.py` (Work Order, BOM, Job Card, Subcontracting Order
  and Receipt), `tell.work_done`, `print_format/one_work_order`, `ready.py`
  and the five `custom/` lists — making. The work order form fetches its
  bill's steps when the bill is chosen, so one saved any other way had no
  steps and so no job cards. `making.steps` (before_validate) fills them
  however it is saved. ERPNext reads a job card submitted in part as the rest
  lost unless it is marked still to do, and the demo marks it. Making with
  workstation time fails on a GL entry with no account until the company
  has a Default Operating Cost Account (`ready._workshop`), and a new work
  order asks for its warehouses until the company has defaults
  (`ready._floor`). `tell.work_done`, on a Manufacture entry's submit, tells
  whoever asked (the request's or the customer order's maker, else the work
  order's) and the project's manager once the work order is Completed.
  People's OneInventory levels hold Manufacturing User and Manager
  (`one/settings.py`, patched in by `patches/making_roles.py`), and
  `access.py` gives the Subcontracting BOM, the System Manager's alone in
  ERPNext, to the buyers and the workshop.
- `ai.py` — OneAI on an item, the stores, receiving, delivering, moving, counting, buying and making: `item_facts` reads
  an item as its page does, `stock_on_hand` the stores as Stock on Hand does,
  `receipt_facts` a receipt, `still_to_arrive` what is ordered and not yet
  come (with `late_only`, the late orders only, a line per order),
  `plan_receipt` drafts a receipt through ERPNext's own mapping,
  `still_to_deliver` what is ordered and not yet sent, and how much of it is
  held, `plan_delivery` drafts a delivery through ERPNext's own mapping,
  `plan_transfer` drafts a transfer to a site, `quotes_now` the Quotes page
  (with `request`, one request's quotes side by side in the company's money,
  through `quotes.compare`), `plan_quote_request` drafts a request for
  quotation from a material request through ERPNext's own mapping,
  `running_low` lists what is at or below its reorder level as ERPNext's
  reordering reads it, `work_order_facts` one work order's materials, steps
  and cost so far, `plan_work_order` drafts a work order from an item's bill,
  `asset_facts` reads a piece of equipment as its page does, with its
  repairs, `upkeep_now` the Upkeep page with the services late or due within
  `days` (30 if not said), `plan_handover` drafts a handover, and
  `plan_item_change` suggests a change as a card. A delivery, a stock
  movement, a count, the open work orders and what a person holds are the
  generic tools' (`about_record`, `read_record`, `list_records`), so the
  suggestions on those pages expect them.
- `item.py` and `heads.py` — the item's figures and the head its form keeps
  at `?edit=1`. ERPNext has every figure in a different place, the Bins
  behind the Stock Levels panel at the foot of the form, the reorder table on
  the Inventory tab, and a Last Purchase Rate with no supplier or date.
  `said` reads them into one answer. Low is ERPNext's own test, projected
  quantity at or below the level (`summary`, pure), so the page, the band and
  the reorder list agree.
- `order.py` and `page/to_order` — what to order. ERPNext's daily
  `reorder_item` raises a Material Request for everything low, and stops:
  nothing lists the requests, groups them by supplier or makes the orders.
  To Order lists open purchase requests not fully ordered plus items low with
  no request, and **Order** makes one draft Purchase Order per supplier
  (`grouped`, pure), each line keeping `material_request` and
  `material_request_item` so ERPNext's own status update marks the request
  ordered on submit. How many is ERPNext's rule (`quantity`, pure). What is
  left on a request line is what it asks less what orders took and drafts
  hold (`left`, pure), and the order itself holds to it on validate
  (`within_requests`), as ERPNext does only on submit. So two drafts cannot
  each order the whole line, under To Order, a form, a bulk edit or Data
  Import alike. The project on each line is read from the request.

  ERPNext reorders by itself: once a day (`reorder_item`, with Stock
  Settings' *Raise Material Request When Stock Reaches Re-order Level*, on by
  default) every item at or below its reorder level gets a Material Request.
  And there it stops. A request is not an order; somebody has to find the
  requests, open each, make a purchase order from it, pick the supplier, and
  do it again for the next one. Nothing lists what is short, or who supplies
  it.

  **To Order** (`page/to_order`, drawn by `frontend/src/to_order` from
  `read`) is that list, modelled on Odoo's Replenishment screen: every open
  purchase request in the company not yet fully ordered, and every item low
  in one of its warehouses with no request yet — why, how many, for which
  warehouse, from whom, at what it last cost a stock unit. It was a report,
  a grid of IDs with a checkbox column. **Order** makes one draft purchase
  order per supplier from the lines ticked, each row still
  pointing at its request, so ERPNext marks the request ordered when the
  order is submitted. Until then what a draft holds is off the list.
  Drafts, because what is ordered and at what price is somebody's decision
  to read before it is sent.

  The supplier is the item's default supplier, else the one it was last
  bought from.
- `assets.py` and `heads.py` — the register that finishes itself, and the
  asset's band and its Give To… and Take Back, as a Record Head.
  ERPNext makes assets from a receipt only if the item also has Auto Create
  Assets and a naming series (`fixed_item` sets both when an item becomes a
  fixed asset), refuses a fixed-asset row with no Asset Location (`located`
  fills the one location there is), and makes each a Draft with Calculate
  Depreciation off, which is never depreciated or counted. `registered`
  (receipt on_submit, after ERPNext's) finishes each: finance books from the
  category, available for use from the purchase date, the first depreciation
  at the end of that month rather than the today ERPNext's `get_item_details`
  stamps, then submitted. A failure rolls back to a savepoint, leaves the
  draft, and comments why; the receipt is never blocked by it.

  An asset's head answers what it is worth now, what it cost, how far
  through its life it is, the next depreciation and service, where it is and
  who has it (`assets.py`), and offers the two movements a person makes:
  Give To… and Take Back (`custody.py`).

  ERPNext makes assets from a purchase receipt of an item marked Is Fixed
  Asset, and three things stand between buying a laptop and a laptop on the
  register depreciating:

  - **The item.** Assets are made only when the item also has *Auto Create
    Assets on Purchase* and an asset naming series; both are off. Without
    them the receipt says "create the asset manually" and nobody does.
    `fixed_item` (Item validate) sets both when an item becomes a fixed
    asset.
  - **The location.** The receipt refuses a fixed-asset row with no *Asset
    Location*. With one location — Head Office — there is nothing to decide,
    and `located` (Purchase Receipt validate) fills it.
  - **The draft.** What the receipt makes is a Draft asset with depreciation
    off, and a draft is never depreciated or counted; ERPNext expects
    somebody to open each one, tick Calculate Depreciation, fill the finance
    book from the category, give it an available-for-use date, and submit.
    `registered` (Purchase Receipt on_submit, after ERPNext's) does that for
    each asset the receipt made (`finish`): in use from the day it was
    bought, depreciating as its category says from the end of that month.
    One that will not finish is left a draft with the reason on it, and the
    Inventory Check counts it.
- `custody.py` — who has what. ERPNext changes an asset's custodian only
  through an Asset Movement, a form whose columns matter or not by purpose;
  **Give To…** is an Issue and **Take Back** a Receipt, one step each, so the
  asset's history is still ERPNext's. `held` feeds the employee's band
  (one_hr/employee.py). `leaving` (Employee Separation before_submit) adds a
  Return activity per asset for the Stock Manager role (`returns`, pure);
  HRMS turns activities into tasks on submit, and its Full and Final
  Statement already refuses to submit while an asset is out.
  `tell.handed_over` (Asset Movement on_submit) tells whoever is given
  something, and `print_format/one_equipment_handover` is the sheet they
  sign (print_blocks `_handed_to`, `_handover_signatures`). `access.py`
  lets HR read assets and their movements, so a person's page shows what
  they hold. `tell.services` (daily) tells a service due within a week to
  whoever does it, and a late one to them and the team's manager, each once.
  Repairs, value adjustments, movements, schedules and logs each have a head
  (`heads.py`), and the lists name the asset, the person and the date.

  ERPNext keeps it on the asset (`custodian`) and changes it only through an
  **Asset Movement**: a form with a purpose, a date and time, and a table of
  assets with a source and target location and a from and to employee, where
  which columns matter depends on the purpose. `give` and `take_back` are the
  two movements a person makes, one step each from the asset's page (**Give
  To…**, **Take Back**); the movement is still ERPNext's, so the asset's
  history and its custodian are what ERPNext would have written.

  A person's page counts what they hold (`held`, read by
  `one_hr/employee.overview`). When they leave, `leaving` (Employee
  Separation before_submit) adds a **Return** activity per asset to the
  separation's checklist, which HRMS turns into tasks; HRMS's Full and Final
  Statement already refuses to submit while an asset is unreturned, and this
  is how it gets returned before then.
- `maintenance.py` and `calendar.py` — maintenance due. ERPNext's
  `calculate_next_due_date` blanks the next due date whenever a task has an
  end date (`or next_due_date` is true as soon as there is one), so a task
  that runs until the warranty ends is never due and gets no log, and only
  the form works it out at all, so a schedule saved any other way has none.
  `due` (Asset Maintenance before_validate) works it out for every task that
  has none or whose dates changed (`next_due`, pure). `on_time` (Asset
  Maintenance Log before_validate) puts a log moved past today back to
  Planned, as ERPNext marks one Overdue and never takes it back. Three
  calendar layers read the Asset Maintenance Logs: the reader's own, the
  workspace's, and an asset's own calendar. ERPNext also assigns one to-do per
  schedule and person, dated for its first task only; the Assigned to Me
  layer (one_task/calendar.py) leaves those out so nothing is on the calendar
  twice.

  ERPNext's **Asset Maintenance** is a schedule per asset — tasks, each with
  a periodicity, a start and an optional end, and the person it is assigned
  to — and an **Asset Maintenance Log** per due date, which somebody
  completes. It assigns the person a to-do and marks a log Overdue once its
  day passes. Two things were missing:

  - **A schedule with an end date is never due.** ERPNext's
    `calculate_next_due_date` blanks the next due date whenever an end date
    is set (`or next_due_date` is true as soon as there is one), so a task
    that runs until the warranty ends has no due date, no log and no
    reminder. `due` (Asset Maintenance before_validate) works the date out
    again for those, and for a schedule saved without the form, from
    ERPNext's own periodicities (`next_due`, pure), and leaves it empty only
    when the next one falls after the end.
  - **Due maintenance was on no calendar.** One's calendar has three layers
    for it (`calendar.py`): the reader's own, everybody's, and an asset's
    own, each opening the log to record it done. An asset's page says when
    its next service is (`next_service`, read by `assets.said`).
- `ready.py` and `report/inventory_check` — the Inventory Check, the Books
  Check's twin, drawn by the same page (`public/js/check.js`). What a new
  company is missing is an asset's two prerequisites: a Location (an Asset
  will not save without one) and an Asset Category (an item marked Is Fixed
  Asset needs one, and the company's own fixed-asset account is empty, so the
  category is the only place the ledger is named). `add_categories` makes the
  usual five from the chart's Fixed Asset ledgers (`plan`, pure), straight
  line, monthly. Serial and batch numbers are off by
  `enable_serial_and_batch_no_for_item`, which hides the item's two checkboxes
  and refuses a bundle.

  The **Inventory Check** (`report/inventory_check`) is a row per check with
  what it means and the fix beside it.

  - **Somewhere to keep stock.** A warehouse that is not a group. ERPNext's
    setup makes four; the check catches a site where they were deleted.
  - **Stock is valued in the books.** Perpetual inventory posts every
    receipt and delivery to the ledger, through the company's stock
    accounts; an empty one stops the first receipt.
  - **Serial and batch numbers.** Switched off by default: the item has no
    *Has Serial No* or *Has Batch No*, and a bundle is refused — while the
    rail offers Lots. Whether a business tracks them is
    its decision, so it is a suggestion.
  - **Somewhere for an asset to be.** An asset will not save without a
    location, and a new company has none. The fix asks what to call the
    first.
  - **Asset categories.** An item marked *Is Fixed Asset* needs a category,
    and a category needs the ledger its assets are kept in and how they
    depreciate. A new company has none, and its fixed-asset account is
    empty. The fix makes the usual ones from the chart's Fixed Assets
    ledgers, each depreciating straight-line monthly over its usual life.
  - **Every asset is registered** (`assets.py`): a draft asset is never
    depreciated or counted; the fix finishes the ones that can be.
  - **Equipment that needs servicing has a schedule** (`maintenance.py`): a
    schedule needs a maintenance team, and a new company has none; the fix
    makes one of the person fixing it.
  - **Depreciation posts itself.** ERPNext books it daily when Accounts
    Settings says to; the check catches a site where it does not.
  - **Every warehouse posts to a stock account** (`wrong_accounts`) and
    **Stock values are up to date** (`failed_reposts`, fixed by ERPNext's
    `bulk_restart_reposting`).
  - **Stock can be held for an order.** ERPNext's
    `enable_stock_reservation`, off by default. Without it a sales order's
    Reserve Stock is hidden and stock promised to one order can go out on
    another.
- `sidebar/oneinventory` — the rail. Items, Receipts, Deliveries, Stock
  Movements, Stock Counts, Purchase Orders, Material Requests, Pick Lists,
  Packing Slips, Delivery Trips and the asset doctypes are owned here
  (`is_default_module`); Supplier is OneBook's and Sales Order OneCRM's. A
  row shipped after a workspace arranged its rail goes where it is shipped
  (`one_studio/reports.py` `settle`).

### print_format/

A delivery note prints from the builder's own pieces too
(`scripts/print_formats.py`): where it goes, the vehicle and driver, the
lines without prices, and both sides to sign; Classic, Bordered and with
Images in place of ERPNext's. So do the buying documents: One Purchase
Order (the supplier, where to deliver, required by, any advance), One
Request for Quotation (every supplier it goes to, each line's required by
date, the message to them) and One Purchase Receipt as a Goods Received
Note (received, accepted and rejected, both sides to sign), the first two
with ERPNext's three other looks, the receipt with each line's batch and
serial numbers in place of ERPNext's serial and batch print. That one reads
the numbers the line keeps; a receipt that keeps them only in a serial and
batch bundle prints them empty. A pick list prints what to pick, from where and
for which order, with Picked By and Checked By, in place of ERPNext's. The rest of
the stores' paper is drawn the same way: One Packing Slip (the delivery and
who it goes to, the cases, each item's weight), One Stock Entry (a Transfer
Note, an Issue Note, a Goods Receipt or a Production Note by what it's for,
where the goods go with that store's address), One Blanket Order (the
quantity and rate agreed, how much is ordered so far), One Work Order (what
to make and for whom, the materials and where from, each step) and One
Equipment Handover (each piece from whom or where to whom or where, and the
pledge of whoever takes it). Work sent out and taken in prints too: One
Subcontracting Order (what the supplier makes at what cost, and the materials
we send for it), One Subcontracting Receipt (received, accepted and rejected,
and the materials it used) and One Subcontracting Inward Order (what a
customer sends us to make, how far it has got, and their materials). So
does the rest ERPNext ships no print for: One Material Request (a Purchase,
Transfer, Issue or Production Request by what it's for), One Supplier
Quotation (the supplier's prices as entered, for whoever approves the
buying), One Delivery Trip (the driver's stops in order, who to ask for,
room to tick each one), One Quality Inspection (each reading against what
it should be, and whether it passed), One Job Card (one step of a work order
on the floor, its materials and time) and One Bill of Materials (the
materials and steps, and what it all costs). The rest of what OneInventory
submits prints from One's pieces too rather than frappe's Standard: an
asset's card (what it cost and is worth now, how it's written down, its
insurance), its maintenance and repair records, a value adjustment, shift
depreciation and a capitalization; a stock count (what the books said and
what was found), a landed cost, a stock reservation, the serial and batch
numbers a line moved, a stock closing; a production plan, a BOM draft, a
sales forecast, an item's standard cost, a product bundle, a supplier's
score and a shipment.

### access.py

ERPNext gives a company's assets to accounts, quality and manufacturing, and
its item prices to two master roles nobody in a small business holds. In One
assets and prices are OneInventory's (see What it is made of), so its own
roles have them:

- **Assets**, their categories, maintenance, repairs, value adjustments and
  capitalization: a Stock Manager runs them; a Stock User reads the register
  and does the upkeep (maintenance, its log and teams, repairs).
- **Item Prices**: whoever manages items, stock or buying keeps them; the
  people who use stock and buying read them.
- **Quality Inspections**: a Stock User records one, a Stock Manager runs
  them.
- **Quality management** (goals, procedures, reviews, actions, non
  conformances, meetings and feedback), which ERPNext gives a Quality
  Manager: a Stock User records them, a Stock Manager runs them and keeps
  the feedback templates (`QUALITY`). The Review report is opened to both
  through frappe's Custom Role (`roles.open_report`).
- **UOM Conversion Factors**, the System Manager's alone: read by stock,
  kept by its managers.
- **Suppliers**: ERPNext lets only a Purchase Master Manager add one. Buying
  adds its suppliers, and its manager removes them (`RAISED`).
