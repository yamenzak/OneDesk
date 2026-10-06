# OneInventory

Written by hand. What OneInventory does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneInventory is what the company holds: the goods it buys and sells or uses up
(stock), and the equipment it keeps — laptops, vehicles, tools (assets). It is
where things arrive from suppliers, leave for customers and move between
places, and where you order more. It is ERPNext's Stock, Buying and Assets, so
a delivery here is the same record an invoice in OneBook is made from, and an
asset's depreciation lands in OneBook's books by itself.

## Finding your way

**OneInventory** in the dock opens it. The rail has:

- **Items** — everything you buy, sell or keep, each with its stock.
- **Stock on Hand** — how much of each item is in each warehouse, and what it
  is worth.
- **Receipts** — goods that arrived from a supplier.
- **Deliveries** — goods that left for a customer.
- **Stock Movements** — anything else that moves stock: from one warehouse to
  another, used up, written off, or found.
- **Stock Counts** — counting what is on the shelf and correcting the books to
  match.
- **Buying** — **To Order** (what is running low, below), **Purchase
  Orders** (what you ordered and are waiting for),
  **Material Requests** (what somebody asked to be bought or moved) and
  **Suppliers**.
- **Assets** — **Assets** (the register), **Asset Movements** (who has what,
  and where), **Maintenance**, **Repairs** and the **Asset Register** report.
- **Reports**, **More** and **Setup** — the stock ledger, projected stock,
  ageing, what is still to arrive, stock against the books, asset balances and
  depreciation; pick lists, landed costs, prices, serial numbers and batches;
  warehouses, price lists, asset categories and locations. Item groups, brands
  and units are in One's **Masters**.

## An item's page

The band under an item's name answers first:

- **On Hand** — how many there are, across every warehouse. Click it for
  the Stock Balance, warehouse by warehouse.
- **Free to Sell** — on hand, less what is promised to customers, with a
  line under it showing how much of what is on hand that is.
- **On Order** — ordered from suppliers and not yet received. Click it for
  the open purchase orders.
- **Worth** — what the stock on hand is valued at in the books.
- **Reorder** — **Low in** a warehouse, in red, when what is there and on
  its way is at or below the reorder level set on the item's **Inventory**
  tab; **Above its level**; or **No level set**.
- **Last Bought** — the price it last came at and from whom; the day is in
  the label.

Beside the numbers, **Out of Stock, Month by Month** is a bar a month for a
year of what left stock (sold, used or sent on), with the year's total over
it. Point at a bar for the month's figure; the title opens the Stock Ledger.
It shows only what your own stock ledger list would.

An item marked **Is Fixed Asset** says how many assets it has become
instead, and how many of them are not yet registered.

## Getting ready

**Setup › Inventory Check** lists what would stop the first receipt, stock
count or asset, with **Ready**, **To Do** or **Suggested** beside each and a
**Fix** where there is one:

- **Somewhere to keep stock** and **stock is valued in the books** — a
  warehouse, and the company's stock accounts. ERPNext makes both.
- **Serial and batch numbers can be used.** Off to begin with, so no item
  can have serial numbers or batches. **Fix** turns them on; an item then
  has **Has Serial No** and **Has Batch No**.
- **Somewhere for an asset to be.** An asset needs a location. **Fix** asks
  what to call the first — Head Office, say.
- **Assets have categories.** **Fix** makes Computers and Software (written
  off over three years), Furniture and Office Equipment (five) and Machinery
  (ten), each kept in the chart's matching Fixed Assets account. Change the
  years under **Setup › Asset Categories**.
- **Depreciation posts itself** — ERPNext's own, checked.

## Buying goods, from order to shelf

1. **Buying › Purchase Orders › + Add.** Pick the supplier, the items, how many
   and at what price, and when you need them. **Submit** sends nothing by
   itself — it records what you ordered; email it from the order's menu.
2. When the goods arrive, **Create › Purchase Receipt** on the order fills in
   what was ordered; change the quantities to what actually came, pick the
   warehouse, and submit. The stock is on the shelf from then.
3. The supplier's bill is **Create › Purchase Invoice** on the receipt, and it
   is OneBook's from there.

Selling works the other way: the customer's order is OneCRM's, **Create ›
Delivery Note** on it sends the goods from a warehouse, and the invoice is
OneBook's.

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
them. A row on a draft order leaves the list, and a
request is marked ordered when its order is submitted.

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

## Who has what

On an asset's page, **Give To…** asks for the employee and hands it over;
once somebody has it, **Hand To…** passes it to somebody else and **Take
Back** returns it to a location. The band says **Who Has It**, and the
person's own page says how much equipment they hold. When somebody leaves,
their separation gets a **Return** task for each thing they hold, and their
final settlement cannot be submitted until everything is back.

## Servicing equipment

Tick **Maintenance Required** on an asset that needs looking after, then
**Assets › Maintenance › + Add**: the asset, the maintenance team, and a row
per job — what it is, how often (monthly, quarterly, yearly…), from when,
until when if it stops, and who does it. Each due date is on that person's
calendar as **My Maintenance**, and on everybody's as **Maintenance Due**
when they turn it on; clicking one opens it to record it done, and the next
one is worked out from that day. The asset's page says its **Next Service**,
in red once it is late.

The first schedule needs a maintenance team; the Inventory Check makes one.

## Counting stock

**Stock Counts › + Add**, choose the warehouse, and **Fetch Items from
Warehouse** lists everything the books say is there. Type what you actually
counted over the quantities and submit: the difference is written off or found,
and the books match the shelf. The first count of a new warehouse is how you
enter opening stock — set **Purpose** to **Opening Stock**.

## Who may do what

A **Stock User** reads the equipment register and does its upkeep:
maintenance, its log and teams, repairs and quality inspections. A **Stock
Manager** runs all of it, value adjustments and capitalization included.
Whoever manages items, stock or buying keeps the item prices; whoever uses
stock or buying reads them. ERPNext gives these to accounts, quality and
manufacturing roles nobody in a small business is given, so One gives them
to the roles People hands out (`access.py`).

## What is kept where

OneCRM keeps customers, quotations and the sales order a won deal becomes;
OneBook keeps invoices, bills, payments and suppliers; OneInventory keeps
items, stock, what arrives and what is delivered, what is ordered from
suppliers, and the company's equipment. See OneBook's README for the whole
split.

## Connections

- **From OneCRM**: A customer's Sales Order is delivered here with Create › Delivery Note. What open orders promise is taken off an item's Free to Sell.
- **From OneProject**: Material requests, requests for prices, purchase orders and stock issues started on a project's page are put on that project.
- **From OneBook**: Suppliers are kept in OneBook, and a supplier billed in another currency gets their order in it. Asset categories use the Fixed Assets accounts in the chart.
- **From OneIntake**: A supplier's delivery note read from mail becomes a draft Purchase Receipt against its order. A supplier's quote becomes a draft Supplier Quotation.
- **To OneBook**: A receipt or a purchase order becomes the supplier's bill with Create › Purchase Invoice. A delivery is invoiced the same way, and each asset's depreciation is posted to the books by itself.
- **To OneProject**: What is ordered, received and issued for a project counts in its Cost. A purchase order for a package of work is a subcontract on the project's Suppliers view.
- **To OneHR**: An employee's page shows how much equipment they hold. When they leave, their separation gets a Return task for each piece.
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

- `item.py` and `heads.py` — the item's band, a Record Head (one/head.py). ERPNext has every
  figure in a different place — the Bins behind the Stock Levels panel at the
  foot of the form, the reorder table on the Inventory tab, a Last Purchase
  Rate with no supplier or date — and `said` reads them into one answer.
  Low is ERPNext's own test, projected quantity at or below the level
  (`summary`, pure), so the band and the reorder list agree.

  An item answers how many there are, how many are free to sell, how many
  are on order, what they are worth, whether it is time to order more, and
  what it last cost (`item.py`). An item marked Is Fixed Asset says how many
  assets it has become instead.

  ERPNext has all of it, in four places: the Bins behind the Stock Levels
  panel at the foot of the form, the reorder table on the Inventory tab, the
  item's *Last Purchase Rate* (with no supplier or date beside it), and the
  Stock Balance report. `said` reads them into one answer for the band
  (`heads.py`).
- `order.py` and `report/to_order` — what to order. ERPNext's daily
  `reorder_item` raises a Material Request for everything low, and stops:
  nothing lists the requests, groups them by supplier or makes the orders.
  To Order lists open purchase requests not fully ordered plus items low with
  no request, and **Order** makes one draft Purchase Order per supplier
  (`grouped`, pure), each line keeping `material_request` and
  `material_request_item` so ERPNext's own status update marks the request
  ordered on submit. How many is ERPNext's rule (`quantity`, pure). Rows on a
  draft order are left off so nothing is ordered twice.

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
  order is submitted; until then a row on a draft order is off the list.
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
  that runs until the warranty ends is never due and gets no log; `due`
  (Asset Maintenance validate) works it out again (`next_due`, pure). Three
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
    reminder. `due` (Asset Maintenance validate) works the date out again
    for those, from ERPNext's own periodicities (`next_due`, pure), and
    leaves it empty only when the next one falls after the end.
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
    rail offers Serial Numbers and Batches. Whether a business tracks them is
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
- `sidebar/oneinventory` — the rail. Items, Receipts, Deliveries, Stock
  Movements, Stock Counts, Purchase Orders, Material Requests and the asset
  doctypes are owned here (`is_default_module`); Supplier is OneBook's and
  Sales Order OneCRM's.

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
