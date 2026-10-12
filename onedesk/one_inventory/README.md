# OneInventory

Written by hand. What OneInventory does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneInventory is what the company holds: the goods it buys and sells or uses up
(stock), and the equipment it keeps — laptops, vehicles, tools (assets). It is
where things arrive from suppliers, leave for customers and move between
places, where the workshop makes them, and where you order more. It is
ERPNext's Stock, Buying, Manufacturing and Assets, so
a delivery here is the same record an invoice in OneBook is made from, and an
asset's depreciation lands in OneBook's books by itself.

## Finding your way

**OneInventory** in the dock opens it on **Home**. Over it, what the stock is
worth, how many items are **Running Low**, how many orders are late and how
many lots are going off.

- **Today** lists what needs somebody, each kind only when there is some:
  **Late Orders** (purchase orders with goods past their date), **Running
  Low** (with **Order**, which opens To Order), **Going Off** (lots near or
  past their date), **Services Due** (late or due this week), **Work Running
  Late** (work orders past their date) and **Left as Drafts** (receipts,
  deliveries, moves and counts started more than a day ago). Each row opens
  what it is about.
- **Everything** lists all of OneInventory, each with a line saying what it
  is for, under Stock, Buying, Making, Equipment, Reports and Setup, and a
  search. **Reports** and **Setup** in the rail open their part of it.

The rail keeps what people use every day:

- **Items**, **Stock on Hand**, **Receipts**, **Deliveries**, **Stock
  Movements**, **Stock Counts** and **Lots**, which holds lots and serial
  numbers together. See Lots and expiry dates.
- **Buying** — **To Order**, **Material Requests**, **Requests for
  Quotation**, **Purchase Orders** and **Suppliers**. See Buying.
- **Making** — **Shop Floor**, **Plant Floor**, **Work Orders**, **Bills of
  Materials** and **Subcontracting Orders**. See Making.
- **Assets** — **Assets**, **Maintenance** and **Repairs**.
- **Reports** — the stock, buying, making and asset reports, each with what
  it shows.
- **Setup** — the **Inventory Check** first (what is missing before stock
  can be kept right), then warehouses, item groups, brands, units and
  attributes (from One's **Masters**), price lists, workstations, plant
  floors, operations, routings, subcontracted items, asset categories,
  locations, maintenance teams, and the stock, buying and manufacturing
  settings.

Everything else (supplier quotations, quote comparison, blanket orders, job
cards, subcontracting receipts, asset movements, pick lists, packing slips,
delivery trips, landed costs, item prices, quality inspections, supplier
scorecards, production plans, the maintenance log, value adjustments and
asset capitalization) is in **Everything** on Home.

## A new item

**Add Item** on the Items list asks what kind of thing it is first:

- **Stock** — counted in a warehouse.
- **Service** — work or a charge, never stocked.
- **Equipment** — owned and used, like a van or a laptop. It becomes an asset
  when it is bought.
- **Sizes or Colours** — one product in several versions. Pick the sizes and
  colours it comes in, and each combination becomes its own item.

**Details** asks for its name, group, unit and a picture. **Sold by Size**
says whether each line gives its length (**Length**) or its length and width
(**Area**), or neither (**No**). See Selling by size.

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

Glass, sheets, profiles and the like are sold by size. An item whose **Sold
by Size** says **Length** or **Area** gets **Pieces**, **Length (mm)** and **Width (mm)** on
every line it is on: quotations, orders, deliveries, invoices, purchase
orders, receipts, stock movements, bills of materials and the rest. The
quantity is worked out from the size, in the line's unit, and the price,
tax, stock and cost follow from the quantity as on any other line.

- 4 glass panels of 1200 × 800 mm, sold by the square metre, come to
  3.84 m².
- 6 profiles cut at 2400 mm, sold by the metre, come to 14.4 m.
- An item kept by the piece says how big one piece is when it is made, such
  as a sheet of 3.125 m². Two sheets of 1250 × 2500 mm then come to 2 sheets.
- A unit ERPNext can convert to also works, such as square feet.

An item counted in a length or an area, such as metres or square feet, is set
to be sold by it when it is made or its unit changes. A sheet kept by the
piece is set by hand.

The size columns show only once a line's item is sold by size, and the quantity
shows its unit, such as 3.840 m². The size prints under the item's name on
quotes, orders, invoices and the other printed records, such as
"4 × 1200 × 800 mm". A quotation's sizes carry to the order made from it, and
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
  are being made), what it is **Worth** in the books, and when it was **Last
  Bought** and from whom, or **Last Made**. Under On Hand and Worth is a line
  of the last twelve months and how much they moved this month, under On
  Order what was ordered each month, and under Last Bought the prices it was
  last bought at.
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
  has **Move Stock** and **Count Stock**, which start the document with the
  item and that warehouse filled in. Then its batches, and its last moves in
  plain words ("Moved 120 from Stores to Mansour Villa Site", "Used 80 on
  Mansour Villa Windows and Doors"), each with who made it. A move from one
  warehouse to another is one row.
- **Buying**: who it is bought from, each with their picture, the last
  price ordered and the one before it in their own currency (with the
  dirhams under it when it is another), what they agreed for the year and
  their part number, changed on the row. **Add Supplier** puts one on the
  item's list, and each supplier's menu has **Order from Them**, **Ask for a
  Quote** and **Make Default**. Then the quotes still open, the cheapest
  marked, each with **Order This**. What is on order says how much has
  arrived and when it is due (in red once late), with **Receive**. What has
  been asked for says who asked and for which project, with **Make Order**.
  Each makes the next document as its own form's button does. Who makes
  it, each manufacturer with their part number changed on the row, the
  default marked (ERPNext puts it on every order line), with **Add
  Manufacturer** and **Make Default**. The buying prices are changed on the
  row, and one that differs from the last price paid says so and offers
  **Use Last Price**.
- **Selling**: what customers have ordered and not yet had, each with how
  much has gone and whether what is on hand covers it. Stock goes to the
  orders soonest due first, so a row says **Can Go Now** or how many it is
  short. Each order's menu has **Deliver**, and **Invoice** while some of it
  is not billed yet. Then the quotes still open, in the customer's own
  currency with the dirhams under it, and until when (red within a week),
  with **Make Order** for a customer's quote. Then who bought it in the last
  twelve months with returns taken off, each with their picture, what they
  paid in their own currency, their last price and their own code for the
  item, changed on the row. Each customer's menu has **New Quotation**,
  **New Order** and **Set Customer's Code**. The selling prices are changed
  on the row, and one says when it was last sold below it. Each makes the
  next document as its own form's button does.
- **Making**: what it is made from, each material with how many its free
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

The main button is **Order More**, or **Make More** for something made
here, or **Add Variant** for a template. The menu has **Request Material**,
**Move Stock**, **Count Stock** (or **Set Opening Stock** for an item with no
stock yet), **Edit Details**, **Disable Item**, ERPNext's **Stock Balance**,
**Stock Ledger** and **Stock Projected Qty**, and frappe's own Print, Email,
Duplicate, Rename and Delete. Each starts the document in its own form with
the item on its first line.

Every view keeps its own **Details** beside it: Stock has safety stock,
batches, serial numbers and weight, Buying has the buying unit, lead time and
minimum order, Selling the selling unit, discount and commission, and Making
whether it is used in manufacturing. Each is changed where it is shown. The
pencil (or the arrow on a choice) opens the item form's own field there, so
the workspace's scripts and rules hold, and leaving it or pressing Enter
saves. Escape puts it back. A field the form hides is not shown, and one it
locks can't be changed. An item with stock keeps Kept in Lots and Kept by
Number locked, as ERPNext refuses to change them once stock has moved.

**Edit Details** changes everything else about the item, grouped as Details,
Stock, Reordering, Units, Serial Numbers and Batches, Variants, Buying,
Selling, Making, Quality, Equipment and Accounts, with any field the
workspace has added under More. Its name is changed by clicking it.

OneAI reads an item as its page shows it, says what is running low, and
suggests a change to an item (its name, group, lead time, whether it is
disabled, or a warehouse's reorder level) as a card you approve.

## Stock on hand and warehouses

**Stock on Hand** says what the stores hold now. At the top are what it is all
**Worth**, how many **Items** are held, how many are **Low** (at or below
their reorder level) and how many are **Short** (more promised to customers
than there is). **Show Low Items** on the Low figure narrows the list to them.

Under the figures is a tab for **All Warehouses** and one for each warehouse,
with how many items it holds. Each line is an item, with what is **On Hand**,
**Free to Sell** (on hand, less what is promised), **On Order** and what it is
**Worth**. **Low in** a warehouse and how many are **short** show beside its
name. Search finds an item by its name or code, and **Low or Short Only**
leaves the rest out. An item opens on its own page. The page changes as stock
moves.

The main button is **Move Stock**. The menu has **Count Stock**, **Add
Warehouse**, and ERPNext's **Stock Balance** and **Stock Projected Qty**
reports, each for the warehouse that is open.

**Setup › Warehouses** shows every warehouse in its tree, opened all the way
down. A warehouse's form says how many items it holds, what they are worth,
how many are low (which opens Stock on Hand for it) and when stock last moved
in or out. A group warehouse counts everything under it.

OneAI reads the stores as Stock on Hand shows them, for every warehouse or
one, and says what is short or running low.

## Getting ready

**Setup › Inventory Check** lists what would stop the first receipt, stock
count or asset, with **Ready**, **To Do** or **Suggested** beside each and a
**Fix** where there is one:

- **Somewhere to keep stock** and **stock is valued in the books** — a
  warehouse, and the company's stock accounts. ERPNext makes both.
- **Stock has a warehouse to go to.** Without one, every receipt and count
  asks for a warehouse on each line. **Fix** makes the Stores the company's
  default.
- **Stock cannot go below zero.** If it could, what it is worth would go
  wrong with it. **Fix** stops it.
- **Running low asks for more.** An item at its reorder level gets a
  material request each night. **Fix** turns this on. **To Order** lists
  what is low either way.
- **Rejected goods are not billed.** ERPNext's own setting bills what was
  rejected on arrival too. **Fix** bills only what was accepted.
- **Stock can be held for an order.** Off to begin with, so stock promised
  to one order can go out on another first. **Fix** turns it on.
- **Every warehouse posts to a stock account** and **Stock values are up to
  date** — stock and the books agree. See When stock and the books disagree.
- **Suppliers can be scored.** Nothing to score them by to begin with.
  **Fix** adds Delivered On Time and Accepted on Arrival, each out of 100.
- **Workshop time is costed.** Making goods that take time at a workstation
  fails until the company names an account for that time. **Fix** uses the
  account ERPNext keeps for costs included in stock value.
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
- **Depreciation posts itself** — ERPNext's own, checked.

## Buying

**Buying** in the rail goes the way buying does. It holds **To Order**, **Material
Requests**, **Requests for Quotation**, **Supplier Quotations**, **Quote
Comparison**, **Purchase Orders**, **Blanket Orders** and **Suppliers**.
Suppliers are kept in OneBook, and the link here opens the same supplier.

1. **Ask for it.** Somebody who needs goods makes a **Material Request**,
   saying what, how many, for which warehouse and project, and when it is
   wanted.
   Its page says the **Project**, who **Asked By**, when it is **Wanted
   By** (in red once late), how many **Quotes** came in, and how much is
   **Ordered** and **Received**.
2. **Ask for prices.** **Create › Request for Quotation** on the request
   names the suppliers to ask. Submit it and **Send Email** mails each one a
   link. A supplier with a portal login prices it there, and their quote
   arrives as a draft with whoever asked told. A quote by mail is
   **Create › Supplier Quotation** on the request. A quote holds until its
   **Valid Till**, and expires by itself after.
3. **Compare.** A request for quotation says how many suppliers
   **Answered** and who is **Cheapest**, line by line. **Quote Comparison**
   sets every quote side by side, in the company's money too. A quote says
   on how many of its lines it is the cheapest.
4. **Order.** **Create › Purchase Order** on the quote you take. Lines can
   go to different suppliers, each from whoever is cheapest on it.
   An order's page says its **Total** in the supplier's money (with the
   company's beside it), when it is **Wanted By**, the blanket order it is
   **Agreed On**, and how much is **Received** and **Billed**. **Submit**
   sends nothing by itself. Print it or mail it from its menu.
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

## Making

**Making** in the rail is the workshop: **Shop Floor**, **Plant Floor**, **Work Orders**, **Job Cards**,
**Bills of Materials**, **Subcontracting Orders** and **Subcontracting
Receipts**. Workstations, plant floors, operations and Manufacturing Settings are under
Setup, and production plans under More.

1. **Say how it is made.** A **Bill of Materials** names what one of a
   product takes, and with **With Operations** the steps (cutting,
   assembling, glazing) and the workstation each is done at, with its
   minutes. Its page says what it **Makes**, its **Cost Each** in materials
   and time, its **Steps**, and how many **Work Orders** use it.
2. **Make it.** A **Work Order** makes so many of a product, for stock,
   for a project or for a customer's order. Somebody who needs goods made
   asks with a **Material Request** of type Manufacture, and **Create ›
   Work Order** on it keeps who asked. Its page says the **Project**, who it
   is **For**, how many are **Made** of how many, whether the **Materials**
   are on the floor, and when it is **Wanted By** (in red once late).
   **Print** gives the floor its sheet: what to make, the materials and
   where they come from, and each step.
3. **Send the materials.** **Start** moves the materials from the stores to
   Work In Progress.
4. **Work each step.** Submitting the work order makes a **Job Card** for
   each step. Whoever works it logs their time and how many they did, in
   order. A job card done in part keeps the rest as still to do. Its page
   says the **Work Order**, **Where**, how many are **Done**, the **Time**
   and **By** whom.
5. **Finish.** **Finish** on the work order puts what was made into
   Finished Goods, valued at its materials and its workshop time. Whoever
   asked for it and the project's manager are told (**Work Order Done**)
   once all of it is made.

### Shop Floor

**Shop Floor** under Making is the page for the people in the workshop.
Over it, how many work orders are **Open**, how many steps someone is on
now (**Running Now**), how many are **Waiting to Start**, and how many were
**Closed Today**.

- **Open** lists the work orders still on the floor, each with its project,
  the step it is at and where, how many are made and how many of its steps
  are done, the late ones with a red dot. **Done** lists the finished ones.
  Each workstation has a tab of its own with its steps, the oldest first.
- **A work order** shows its steps, each a job card. A step says how many
  are done of how many, who is on it, how long it has run, what of its
  materials is short in the stores, and whether it needs a quality check
  before it closes. **Finish** puts what was made into stock, as on the
  work order.
- **Start** asks when it started and who is on it, the reader first. A
  running step has **Pause**, and a paused one **Resume**.
- **Record Made**, in the step's menu, asks how many were made and lost and
  when the session ended. **Close Step** closes the step, its quality
  check first when it needs one. **Carry On Later** records the session and
  leaves the step paused for the next. A step whose sessions are all
  recorded has **Close Step** as its button.
- **Move Materials** makes the stock entry that moves what the step still
  needs to it. **Check Quality** takes the readings of the step's quality
  check and records them. A rejected check keeps the step open. **Read
  Instructions** shows the operation's own instructions.
- A step that makes a part of its own (**Receive Into Stock**) puts it into
  stock once closed.

Everything on it is ERPNext's own job card, done through ERPNext's own
calls, so the job card's form, its time logs and its reports say the same.
It changes as soon as somebody else starts or closes a step.

### Plant Floor

**Plant Floor** under Making shows a floor's workstations as cards. Over it,
how many **Workstations** there are, how many are **Making**, how many are
**Stopped** by a problem or for maintenance, and how many **Steps Running**.

- Each card says the workstation's type, its status in ERPNext's colours,
  each step running on it and who is on it, and how many steps wait to
  start there. A card opens the workstation's steps on the Shop Floor.
- **Change Status** sets the workstation's status (Production, Off, Idle,
  Problem, Maintenance or Setup). Every open Plant Floor changes with it.
- **Type** and **Status** narrow the cards. A workspace with more than one
  floor has a tab for each.
- **Stock Here** lists what the floor's warehouse holds, and how much of it
  is kept for work orders. **Add Stock** and **Move Stock** make the stock
  entry as a draft to check and submit.
- A floor is set up with **New Plant Floor**: its name and its warehouse.
  A workstation joins it with **Plant Floor** on the workstation.

- **What making costs a project.** The materials a project's work order uses
  count in the project's Stock Used on OneProject, as ERPNext counts them.
- **Sending work out.** A product a supplier makes from your materials,
  powder coating say, is a **Subcontracted Item** (Setup) naming the
  supplier's service. A purchase order for the service with **Is
  Subcontracted** becomes a **Subcontracting Order** with **Create**. Its
  page says how much of the materials went out (**Materials Sent**) and how
  much came back (**Received**). **Material to Supplier** sends them, and
  a **Subcontracting Receipt** takes the goods back into the stores. The
  supplier's bill is made from the purchase receipt it creates. This is not
  OneProject's subcontract, which is a package of work on a project.

## Receiving

**Receipts** lists every delivery with its supplier, where it stands, its date,
its total and how much of it is billed. A supplier's delivery note read from
mail is already there as a draft, marked as made by OneAI.

A receipt says above its fields which **Order** it came on, what it is
**Worth** in the company's money (with the supplier's own currency beside it
when that is another; a service on it, such as coating sent out, at what it
cost), the **Landed Costs** added to it, how much was
**Rejected**, and how much is **Billed**. Under the exchange rate it says what
one of the supplier's currency is in the company's.

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

**Deliveries** lists every delivery with its customer, where it stands, its
date, its total and how much of it is billed.

A delivery says above its fields which **Project** and **Order** it is for,
its **Total** in the customer's money (with the company's beside it when that
is another), the **Trip** taking it out with its date and driver, how much is
**Billed**, and how much came back as **Returned**.

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

Give an item a reorder level on its **Inventory** tab: the warehouse, the
level, and how many to order each time. Once a day, anything at or below its
level gets a **Material Request** by itself.

**Buying › To Order** lists what needs ordering: every request not yet
ordered, and every item that is low and not yet requested — how many, for
which warehouse, from whom (the item's default supplier, or whoever it was
last bought from) and what it last cost. Tick the rows and press **Order**:
one draft purchase order is made for each supplier, and rows with no
supplier go to the one you pick. A supplier billed in another currency gets
their order in it. Read the drafts, correct prices and quantities, and submit
them. A request line held by draft orders leaves the list, and no order,
however it is made, can order more of a request line than is left on it.
A request is marked ordered when its order is submitted.

## Buying equipment

A laptop, a desk, a van: make it an item once, with **Is Fixed Asset** ticked
and its **Asset Category** (Computers, Furniture…). Then buy it like anything
else — a purchase order and a receipt. Each one received becomes an asset on
the register by itself: kept at your location, in use from the day it was
bought, and depreciating as its category says from the end of that month.

An asset's page says what it is **Worth Now**, what it **Cost**, how much of
its life is **Written Off** (with a line showing how far through), the
**Next Depreciation** and **Where** it is. Once registered, **Worth Over Its
Life** beside them is a line from what it cost to what it will be worth at
the end, one point per depreciation its schedule books.
The Inventory Check's **Every asset is registered** turns **To Do** if one
could not register itself, and each says why on its page.

Equipment you already had is **Assets › + Add** with **Existing Asset**.
The list says who has each piece.

## Who has what

On an asset's page, **Give To…** asks for the employee and hands it over.
Once somebody has it, **Hand To…** passes it to somebody else and **Take
Back** returns it to a location. The person is told it is in their care.
Each handover prints as an **Equipment Handover** for them to sign: what
they were given, who gave it, and that they will look after it and give it
back when asked.

The band says **Who Has It**, and the person's own page says how much
equipment they hold, to whoever runs HR as well. When somebody leaves, HR
submits their separation, and it gets a **Return** task for each thing they
hold, given to the stores.

## Servicing equipment

Tick **Maintenance Required** on an asset that needs looking after, then
**Assets › Maintenance › + Add**: the asset, the maintenance team, and a row
per job — what it is, how often (monthly, quarterly, yearly…), from when,
until when if it stops, and who does it. Each due date is on that person's
calendar as **My Maintenance**, and on everybody's as **Maintenance Due**
when they turn it on, each named after the asset it is for; clicking one
opens it to record it done, and the next one is worked out from that day.
**More › Maintenance Log** lists every service with its asset. The asset's page says its **Next Service**,
in red once it is late.

The first schedule needs a maintenance team. The Inventory Check makes one.

Whoever does a service is told a week before it is due. Once it is late,
they and the team's manager are told. A schedule brought in from a
spreadsheet or by OneAI has its dates worked out the same as one typed in.

## Mending equipment and its value

When something breaks, **Assets › Repairs › + Add**: the asset, when it
failed, and what is wrong. It shows **Out of Order** until the repair is
**Completed**. The garage's bill is entered as a supplier bill first, booked
to repairs, and the repair takes its cost from it. Its band says how long
the asset was **Out of Use** and what it **Cost**. The asset's band counts
its **Repairs**.

When something is worth less than its books say, after damage for
instance, **More › Asset Value Adjustments** sets its new value. The
difference is posted to the account you choose, and its band says what it
**Was Worth**, is **Now Worth** and the **Change**.

## Moving stock

**Stock Movements** lists every movement with its type, where it came from,
where it went, its project and what it moved. **Move Stock** on Stock on Hand
starts a transfer from the warehouse you are looking at.

A movement says above its fields which **Project** it is for, its **Type**,
**From** and **To** which warehouse, what it is **Worth**, and for goods made,
what making them **Used**. A transfer sent through Goods In Transit says how
much has **Arrived**.

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

**Stock Counts › + Add**, choose the warehouse, and **Fetch Items from
Warehouse** lists everything the books say is there. Type what you actually
counted over the quantities and submit. A new count starts as a count, so the
difference is written off or found in the stock adjustment account and the
books match the shelf. ERPNext keeps only the lines whose quantity changed.
The first count of a new warehouse is how you enter opening stock. Set
**Purpose** to **Opening Stock**, and its value goes to Temporary Opening.

A count says above its fields what it was for, **Where** it was counted, how
many **Items** it changed, and the **Difference** it made in the books.

OneAI says what a count found and what it did to the books.

## Lots and expiry dates

**Lots** in the rail keeps lots and serial numbers in one place. The figures
say how many lots are in stock, how many go off within a month, how many have
gone off and how many numbered pieces are in stock. Three tabs follow.

- **Lots** lists each lot with something left, the one going off first. Each
  says what is left in each warehouse and when it goes off, amber within a
  month and red once past. **Going Off Only** narrows it to those.
- **Serial Numbers** lists each numbered piece with where it is, or the
  customer it went to, and when its warranty ends.
- **Items** lists the items kept in lots or by number, and how each is
  numbered.

**Track Lots** sets an item up to be kept in lots or by number in one step:
whether new lots are numbered for you and how, whether lots go off and how
many days one keeps, or how serial numbers run and how long the warranty is.
It offers only items that have never moved, since ERPNext fixes how an item
is kept once it has. **New Lot** makes a lot by hand, with when it was made
and when it goes off. Left empty, the date is worked out from how long the
item keeps. Each receipt asks which lot or numbers came in.

When lots are switched off for the workspace, the page says so and
**Turn On** switches them on, as the Inventory Check does.

An item's Stock view shows the same lots and numbers, with **New Lot**, and
**Keep it in lots or by number** for an item that has not moved yet. Its
Overview says **Expiring Soon** for a lot that runs out of date within a
month and **Expired, Still in Stock** for one past its date, so it is used,
sold or taken out of stock first. Whoever keeps the stores is told once when
a lot with some left will expire within a month. **Batch Expiry** and
**Stock by Batch** are under Reports.

A lot's page says what is left and in which warehouses, when it was made and
when it expires, the receipt it came from, and how many times some was taken
out, opening ERPNext's trace of it. Its stock levels, Move and Split are
ERPNext's own.

OneAI answers **Which lots go off soon?** and **Where is each numbered
piece?** on the page, from `lots_and_numbers`.

## When stock and the books disagree

A back-dated entry, such as a count dated last week, makes ERPNext
recalculate the stock values after it. **Stock values are up to date** in the
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
stock or buying reads them. ERPNext gives these to accounts, quality and
manufacturing roles nobody in a small business is given, so One gives them
to the roles People hands out (`access.py`).

Using OneInventory includes making: its users make bills of materials, work
orders and job cards, and its managers also run Manufacturing Settings and
which supplier makes what for the company.

Whoever works in HR reads the equipment register and its handovers, to see
what a person holds and ask for it back when they leave. They change none
of it.

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
- **From OneBook**: Suppliers are kept in OneBook, and Buying › Suppliers opens the same supplier there. A supplier billed in another currency gets their order in it. Asset categories use the Fixed Assets accounts in the chart.
- **From OneIntake**: A supplier's delivery note read from mail becomes a draft Purchase Receipt against its order. A supplier's quote becomes a draft Supplier Quotation, and so does one priced on the portal. A supplier's bill for an order, such as the coater's, becomes a draft bill against the order, due when the bill says.
- **To OneBook**: A receipt or a purchase order becomes the supplier's bill with Create › Purchase Invoice. A delivery is invoiced the same way, and each asset's depreciation is posted to the books by itself. A count's difference is posted to the stock adjustment account, and stock that does not agree with the books is told to the accountant. A repair takes its cost from the garage's bill, and an asset's value adjustment posts a journal entry.
- **To OneProject**: What is ordered, received and issued for a project counts in its Cost. A purchase order for a package of work is a subcontract on the project's Suppliers view. Stock sent to a site and used there for a project counts the same way, and so do the materials a project's work orders use. Its manager is told when one is made.
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
  `one_measured_by` (Sold by Size: No, Length or Area), set by `follows_unit`
  before_validate from ERPNext's UOM Conversion Factor category when the item
  is made or its unit changes, and on every table in `LINES` the custom fields
  one_measured_by (fetched from the item), one_pieces, one_length, one_width
  and one_size. `sized` runs before_validate on every record (`doc_events`
  "*"), so the quantity holds under bulk edit, Data Import and ERPNext's
  mappers. `factor` converts a metre or square metre to the line's unit by
  the item's own conversion first, then ERPNext's UOM Conversion Factor. The
  form script sets the quantity as the size is typed, shows the size columns
  only where a line is measured, and the unit's symbol beside the quantity.
  The shipped print formats merge one_size under the item's name.
- `home.py`, `page/inventory` and `frontend/src/home` — Home. `needs_you`
  reads what needs somebody through the readers OneAI uses
  (`ai.late_orders`, `ai.running_low`, `ai.services_due`) and
  `batches.dated`, so Home and OneAI count the same, each as the reader may
  see it, `FEW` rows of each with how many more. `drafts` counts papers left
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
  they are shown (`FieldEdit`, docs/STANDARD.md point 6).
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
  (`one/print_blocks.py`). `rate_note.js` writes the rate under every money
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
  each have a head, and a purchase order's says its total and when it is
  wanted. Who is cheapest is read line by line in the company's money
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
  come, `plan_receipt` drafts a receipt through ERPNext's own mapping,
  `delivery_facts` a delivery, its slips and its trip, `still_to_deliver`
  what is ordered and not yet sent, and how much of it is held,
  `plan_delivery` drafts a delivery through ERPNext's own mapping,
  `movement_facts` a stock movement, `count_facts` a count, `plan_transfer`
  drafts a transfer to a site, `quote_comparison` sets the quotes for a
  request side by side in the company's money, `late_orders` says which
  orders are late, `plan_quote_request` drafts a request for quotation from a
  material request through ERPNext's own mapping,
  `running_low` lists what is at or below its reorder level as ERPNext's
  reordering reads it, `work_in_hand` the open work orders and their steps,
  `work_order_facts` one work order's materials, steps and cost so far,
  `plan_work_order` drafts a work order from an item's bill,
  `asset_facts` reads a piece of equipment as its page does, with its
  repairs, `equipment_held` what a person holds, `services_due` the services
  late or due within a month, `plan_handover` drafts a handover, and
  `plan_item_change` suggests a change as a card.
- `item.py` and `heads.py` — the item's figures and the head its form keeps
  at `?edit=1`. ERPNext has every figure in a different place, the Bins
  behind the Stock Levels panel at the foot of the form, the reorder table on
  the Inventory tab, and a Last Purchase Rate with no supplier or date.
  `said` reads them into one answer. Low is ERPNext's own test, projected
  quantity at or below the level (`summary`, pure), so the page, the band and
  the reorder list agree.
- `order.py` and `report/to_order` — what to order. ERPNext's daily
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

  **To Order** (`report/to_order`) is that list: every open purchase request
  not yet fully ordered, and every item low with no request yet — how many,
  for which warehouse, from whom, at what it last cost. **Order** makes one
  draft purchase order per supplier from the rows ticked, each row still
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
  (`one/reports.py` `settle`).

### The plan

1. **The place.** OneInventory's rail, in the dock after OneBook, with buying
   and assets in it, and the sales order on OneCRM's rail. *Done.*
2. **Ready to use.** A check of what will fail the first time somebody
   receives, delivers or registers an asset — serial and batch numbers
   switched off, no account for opening stock, no location for an asset — with
   the fix beside each. *Done.*
3. **An item answers first.** On hand across warehouses, what is free to sell,
   what is on order, what it is worth, whether it is below its reorder level,
   and what it last cost and from whom. *Done.*
4. **What to order.** Items at or below their reorder level with how many to
   order and from whom, made into purchase orders a supplier at a time. *Done.*
5. **Assets: a register that finishes itself.** The assets a receipt makes are
   drafts nobody completes and so never depreciate; they are completed from
   their purchase and category, and an asset's page says what it is worth. *Done.*
6. **Assets: who has what.** Give an asset to an employee and take it back in
   one step; an employee's page lists what they hold, and leaving asks for it
   back. *Done.*
7. **Assets: maintenance.** What is due for a service, on the calendar and in
   the owner's tasks. *Done.*

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
- **Suppliers**: ERPNext lets only a Purchase Master Manager add one. Buying
  adds its suppliers, and its manager removes them (`RAISED`).
