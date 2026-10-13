# OneInventory, the plan

OneInventory is the third module finished against the standard
(`docs/STANDARD.md`), after OneProject and OneTask. This file is the plan,
written before any of it is built. It has what ERPNext offers, what One
offers on it today, where manufacturing goes, the screens to walk and what
each needs under the seventeen points.

## Who works in it

The demo's people, and what each opens OneInventory for.

| Person | Job | OneInventory | Opens it for |
|---|---|---|---|
| Karim | Procurement Officer | Manager | Ordering, receiving, prices, suppliers, counts |
| Tariq | Workshop Supervisor | User | Making windows and doors, materials on the floor |
| Yousef | Installer | User | Taking goods to site, his tools |
| Rania | Site Engineer | User | Asking for materials for a project |
| Samir | Projects Manager | User | What a project has ordered, received and used |
| Huda | Accountant | User | Stock against the books, assets, landed costs |
| A supplier | Portal user | | Answering requests for prices, their orders |

Each screen is walked as the people in its row of the screen list below,
on a desktop and a phone.

## What ERPNext offers

ERPNext keeps what a company holds in five modules. One's OneInventory is
all of them but Quality Management.

### Stock

- **Valuation**. FIFO, Moving Average, LIFO, and Standard Cost (new on
  develop, kept on Item Standard Cost). Set per item or in Stock Settings.
- **Records**. Item (with variants, alternatives, lead times, prices and
  units), Warehouse (a tree, with types), Batch, Serial No, Serial and Batch
  Bundle, Putaway Rule, Inventory Dimension, Item Price, Price List.
- **Documents**. Purchase Receipt and Delivery Note, Stock Entry (thirteen
  purposes, from Material Issue to Disassemble), Stock Reconciliation
  (Opening Stock or a count), Material Request (six types), Pick List,
  Packing Slip, Landed Cost Voucher, Stock Reservation Entry, Shipment,
  Delivery Trip, Quality Inspection, Repost Item Valuation and Stock Closing
  Entry.
- **Stock Settings**. Defaults, what stock may do (negative stock, over
  delivery), serial numbers and batches, reservation, quality inspection,
  reordering by itself, and freezing stock before a date.
- **Every day**. Reordering, reposting stock values, and serial and batch
  upkeep.
- **Reports**. About 55, from Stock Balance and the Stock Ledger to ageing,
  projected stock, and checks that the stock and the books agree.
- **Not on any of ERPNext's sidebars**. Stock Closing Entry, Stock
  Reservation Entry, Putaway Rule and Shipment.

### Buying

- **Supplier**, with a hold that warns or stops, and portal users.
- **Request for Quotation** to several suppliers, answered on the portal.
  **Supplier Quotation**, which expires by itself. **Purchase Order**, with
  its share received and its share billed. **Blanket Order**, a price agreed
  for a year.
- **Supplier Scorecard**, scoring suppliers by delivery and quality.
- **Buying Settings**. Naming, price list, whether an order or a receipt
  comes before a bill, and subcontracting.
- **Reports**. Procurement Tracker, Supplier Quotation Comparison, Purchase
  Order Analysis, and more.

### Subcontracting

ERPNext's subcontracting is sending your materials out to be made into
something and taken back. A purchase order for the finished item makes a
**Subcontracting Order**. A stock entry sends the materials, and a
**Subcontracting Receipt** takes the finished goods in and can make the
purchase receipt by itself. For a glazing workshop that is sending
aluminium profiles out to be powder coated.

This is not OneProject's subcontract, a package of work billed by share of
the order. Both keep their names in the README, so nobody takes one for the
other.

### Manufacturing

- **Making**. BOM (a bill of materials, with operations and costs), BOM
  Creator, Work Order, Job Card, Routing, Operation, Workstation, Plant
  Floor, Downtime Entry.
- **Planning**. Production Plan, Master Production Schedule, Sales
  Forecast.
- **Manufacturing Settings**. How materials are taken (by the BOM or by
  what was moved to the floor), overproduction, capacity planning, and
  time on job cards.
- **Pages**. Shop Floor, BOM Comparison Tool, Production Plan Visualizer.
- **Projects**. A BOM, a work order, a production plan, a job card and the
  stock entry that makes the goods each name a project. What the stock entry
  moves counts in the project's cost.
- No scheduled jobs.

### Assets

Asset (with statuses from Draft to Scrapped), Asset Category, Asset
Movement, Asset Maintenance and its log and team, Asset Repair, Asset Value
Adjustment, Asset Capitalization, Asset Shift, Asset Depreciation Schedule
and Location. Their settings are in Accounts Settings. Depreciation and
maintenance due run every day.

### Quality Management

Quality Goal, Procedure, Review, Action, Non Conformance, Feedback and
Meeting. Quality Inspection is in Stock, not here.

## What One offers today

- **The rail**. Items, Stock on Hand, Receipts, Deliveries, Stock Movements,
  Stock Counts, then Buying (To Order, Purchase Orders, Material Requests,
  Suppliers), Assets, Reports, More and Setup.
- **Heads** on Item, Asset, Purchase Order and Stock Entry. An item answers
  On Hand, Free to Sell, On Order, Worth, Reorder and Last Bought.
- **To Order**, what runs low turned into draft purchase orders, one per
  supplier, in the supplier's currency.
- **The Inventory Check**, what would stop the first receipt, count or asset,
  each with a fix.
- **Assets** that register themselves from a receipt, are handed to an
  employee and back, are returned when somebody leaves, and are serviced
  from the calendar.
- **Access** (`access.py`). ERPNext's grants to roles nobody in a small
  business is given, moved to the roles People hands out.
- **Prints**. One Delivery Note, One Purchase Order, One Request for
  Quotation.
- **Notifications**. Eight, from Material Request Raised to Reposting
  Failed.
- **Intake** reads a supplier's delivery note into a draft receipt and a quote
  into a draft supplier quotation.
- **Demo checks**. Eight, among them broken glass sent back and debited, the
  stock in the books, what was ordered received and billed price for price,
  a supplier answering on the portal, and assets depreciating.

## What it lacks, point by point

Found by the audit, before the walk. The walk will find more.

1. **Demo coverage**. No serial numbers or batches, no transfer to a site
   warehouse, no pick list, no landed cost, no quality inspection, no stock
   reservation, no blanket order, no comparison of quotes, no asset bought by
   receipt in the demo itself, no repair and no value adjustment. The work
   orders are made by whoever set the workspace up, not by Tariq.
2. **Rules on the server**. To be found screen by screen. To Order's rule
   that a row on a draft leaves the list is in the report, not the record.
3. **Hand-offs**. The Connections section is there. Manufacturing and
   subcontracting are missing from it, and From OneHR is only the leaver.
4. **Tier declared**. Nothing of OneInventory's is in `tiers.py`. No pages,
   no collections, no screens. Purchase Receipt, Delivery Note, Material
   Request, Stock Reconciliation and Warehouse have no head.
5. **Our look**. Every screen is frappe's form or list with a head. No page
   of its own.
6. **Nothing lost**. Nothing to check until there is a page.
7. **Extensible**. No place for OneStudio on any OneInventory screen.
8. **Built from frappe**. The heads and To Order to be read for rounding and
   dates by hand.
9. **Overrides recorded**. Not recorded yet, among them Stock Settings'
   property setter.
10. **Notifications**. Nothing for an order that is late, goods that arrived
    for whoever asked for them, stock low, equipment handed over, a service
    due or late, or a work order done.
11. **Printed**. No print for a receipt, a material request, a stock entry,
    a pick list, a packing slip, a work order or an equipment handover.
12. **Plain words**. To be read on every screen. "Stock Movements" is ours
    and "Stock Entry" is frappe's, both shown.
13. **Documented, and OneAI knows and does**. The README is a manual for
    what exists. OneAI has no OneInventory group, no `ai.py`, and can neither
    read stock nor do anything here.
14. **Intake**. The goods, quotation and unordered samples have no unit
    tests. Nothing reads a supplier's invoice for goods into a receipt and a
    bill together.
15. **Permissions**. Nobody but the workspace's maker can make a BOM or a
    work order.
16. **Legal**. No `legal.py`. The supplier portal, equipment held by an
    employee and OneAI reading suppliers' mail are to be weighed against the
    agreements.
17. **Clean code**. The coverage guard reaches all six whitelisted methods.
    The rest to be read file by file.

## Manufacturing, the decision

**OneInventory takes it on**, as **Making** in the rail. The recommendation,
for your word:

- The demo already makes three BOMs and eight work orders, for windows,
  sliding doors and balustrades, from the same stock OneInventory keeps.
  Making turns stock into stock, so it belongs where the stock is.
- A work order names its project, and what it uses counts in the project's
  cost. The glazing workshop makes for projects, so OneProject sees it on
  its Money tab without a second module.
- A small business does not need a module for making. It needs BOMs, work
  orders and the materials moved, as the workshop supervisor's work.
- **In the rail**, under Making: BOMs, Work Orders, Job Cards, and
  Subcontracting (orders sent out and received). Production Plan, Routing,
  Workstations, Operations, the Shop Floor and Manufacturing Settings go
  under More and Setup. Nothing frappe offers is taken away.
- **Roles**. OneInventory's Manager is given Manufacturing Manager's work and
  its User Manufacturing User's, in `access.py`, as Stock and Buying are
  now. Tariq makes the demo's work orders.
- **Quality Management** stays out, for now. Quality Inspection stays in
  OneInventory, where receipts and work orders ask for it. A quality system
  (goals, procedures, non conformance) is written down as open, to be taken
  on as its own place if a customer needs it.

## The screens

Split the way the people use it, as the standard says. Each ends with a
table of all seventeen points, plus Everything follows frappe and What
ERPNext already does.

### 0. The baseline

Run the gates before touching anything and write down the counts. At the
end of OneProject's gaps they were 1900 fast tests and 122 of 122 demo
checks. Then the clean-up the audit found. Record the overrides not
recorded, and add unit tests for Intake's goods, quotation and unordered
plans.

### 1. Items and an item's page

Karim, Huda, Samir. The rail, the Items list and every view of it, an item,
its variants, prices, units, alternatives and reorder levels, and New Item.

- **Decide the tier**. An item is the hub of the module, as a project is of
  OneProject. The recommendation is a page of its own, with Overview (the
  band and the month by month bar), Stock (by warehouse, with batches and
  serial numbers), Buying (suppliers, last prices, open orders), Selling
  (open orders, what is promised), Making (its BOM, and where it is used)
  and Activity. It keeps frappe's sidebar, menu, saving and every field.
- Glazing units in the demo. Glass bought by the sheet and used by the
  square metre, profiles bought by the bar and used by the metre, so the
  conversion is seen.
- Variants for glass thickness, and an item alternative.

### 1b. Items rethought

New Item by kind, Made From and Add from a List, the Items list as a
catalogue, Attributes on Masters, and selling by size on every table that
lines up items. Not yet: sizes in inches, a minimum charge per piece, a
perimeter, volume, and offcuts kept as stock.

### 2. Stock on Hand and warehouses

Karim, Huda, Tariq. Stock on Hand, the warehouse tree, a warehouse's head,
Stock Settings, valuation, the stock ledger and stock against the books.

- A site warehouse per running project, so a transfer to site is seen.
- A head on Warehouse with what it holds, its worth and what is low.
- Stock Settings walked as the Inventory Check walks it, freezing before a
  date and stock reservation included.

### 3. Receiving

Karim, Huda. Receipts, quality inspection on arrival, landed costs, putaway,
serial numbers and batches, and the bill.

- A receipt's head, and One Purchase Receipt printed as a goods received
  note.
- Euros from Euro Hardware Trading with freight and duty on a landed
  cost, so `base_` amounts are checked.
- A quality inspection that rejects glass, joining the broken glass check.
- Goods Received told to whoever asked for them.

### 4. Delivering

Karim, Yousef, Omar from the other side. Deliveries, pick lists, packing
slips, delivery trips, shipments and stock reserved for an order.

- A delivery's head, and One Pick List and One Packing Slip printed.
- Stock reserved for the villa's sales order, and Free to Sell taking it
  off.
- A delivery trip taking windows to site, with Yousef as the driver.

### 5. Moving and counting

Tariq, Yousef, Huda. Stock Movements, transfers to a site, material issued
to a project, Stock Counts, opening stock, reposting and stock closing.

- One Stock Entry printed as a transfer note that travels with the goods.
- A stock count with a difference, and its effect in the books.
- Reposting Failed and Stock Account Wrong walked as Huda.

### 6. Buying

Karim, Rania, a supplier on the portal, Huda. To Order, Material Requests,
Requests for Quotation, Supplier Quotations and their comparison, Purchase
Orders, Blanket Orders, the Supplier Scorecard and Buying Settings.

- A request from Rania on the villa, priced by two suppliers, compared and
  ordered.
- A blanket order with the aluminium supplier for the year.
- Order Late told to Karim when goods are past their date.
- To Order's rules moved onto the records where they decide.
- OneBook keeps suppliers. The walk checks that the supplier form reached
  from here is the same one.

### 7. Making

Tariq, Samir, Huda. BOMs, Work Orders, Job Cards, Production Plan and
subcontracting.

- The roles, the rail group and the README section from the decision above.
- Tariq's work orders on the villa and the tower, with materials taken from
  Stores and windows made into Finished Goods.
- Powder coating sent out on a Subcontracting Order and received back.
- One Work Order printed as a sheet for the floor. Work Order Done told to
  whoever asked for it, and to the project's manager.
- The materials used counted in the project's cost, checked on the demo.

### 8. Equipment

Karim, Yousef, Mariam from the other side, Huda. Assets, movements,
handing over, maintenance, repairs, value adjustments, capitalization and
the asset reports.

- An asset bought by receipt in the demo, a repair, a value adjustment.
- Equipment Handed Over told to the person, and an equipment handover
  printed for signing.
- Service Due and Service Late told to whoever does it.
- The asset's head and register walked again against all seventeen points.

### 9. Reports and Setup

Huda, Karim. The Reports group, More, Setup, the Inventory Check and the
three settings pages.

- Every report's heading matches its rail label, as on OneProject.
- The reports the audit found missing from the rail weighed one by one.

### 10. Across modules

From the other side of each hand-off, as the person who works there.
OneCRM's sales order delivered, OneBook's bill from a receipt and its stock
value, OneProject's Money and Suppliers tabs, OneHR's leaver returning
equipment, OneCalendar's maintenance, OneIntake's delivery note and quote,
and OneAI.

### 11. The closing pass

Every screen's table complete, the gates green on a fresh rebuild, the
module marked closed in `docs/PASSOVER-LOG.md` and what stays open written down.

## Across every screen

These run through the walk rather than belonging to one screen.

- **OneAI** (point 13). A `one_inventory/ai.py` and an `inventory` group.
  OneAI reads an item's stock, what is low, an order's state, where an asset
  is and who holds it, as the reader sees them. It drafts a material
  request, orders from To Order, moves stock, counts a warehouse, hands
  over an asset and records a service, each as a card the reader approves,
  running the screen's own code.
- **Intake** (point 14). Samples for a supplier's invoice for goods, a
  delivery note with a short delivery, a price list from a supplier, and a
  coater's delivery note for subcontracted goods.
- **Legal** (point 16). A `one_inventory/legal.py` with what the module does
  that the agreements must say, weighed screen by screen.
- **Places** (point 7). One for each page and each list of OneInventory's.
- **Realtime**. Every screen hears when its stock, order or asset changes.
- **What ERPNext already does**. On every document, the supplier's currency
  and `base_` amounts, units and their conversion, precision of quantities
  and rates, valuation, drafts, cancelled and amended documents, its
  statuses (received and billed shares, To Receive and Bill, Completed,
  Closed), its mappers (request to order to receipt to bill, order to
  delivery, work order to stock entry), taxes on buying, price lists,
  payment terms, posting dates in the past and the reposting they cause,
  and who may read which warehouse.

## Decisions for you

1. **Manufacturing** goes into OneInventory as Making, with the roles. The
   recommendation is yes.
2. **An item gets a page of its own**, as a project has. The recommendation
   is yes. The rest stay frappe's forms with a head.
3. **Quality Management** stays out, written down as open. The
   recommendation is to leave it out.

Once you have given your word, the walk begins with step 0, one screen at a
time, each shown before the next.
