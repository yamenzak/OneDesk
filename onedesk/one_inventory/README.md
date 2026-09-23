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
- **Buying** — **Purchase Orders** (what you ordered and are waiting for),
  **Material Requests** (what somebody asked to be bought or moved) and
  **Suppliers**.
- **Assets** — **Assets** (the register), **Asset Movements** (who has what,
  and where), **Maintenance**, **Repairs** and the **Asset Register** report.
- **Reports**, **More** and **Setup** — the stock ledger, projected stock,
  ageing, what is still to arrive, stock against the books, asset balances and
  depreciation; pick lists, landed costs, prices, serial numbers and batches;
  warehouses, item groups, units, price lists, asset categories and locations.

## An item's page

The band under an item's name answers first:

- **On Hand** — how many there are, across every warehouse. Click it for
  the Stock Balance, warehouse by warehouse.
- **Free to Sell** — on hand, less what is promised to customers.
- **On Order** — ordered from suppliers and not yet received. Click it for
  the open purchase orders.
- **Worth** — what the stock on hand is valued at in the books.
- **Reorder** — **Low in** a warehouse, in red, when what is there and on
  its way is at or below the reorder level set on the item's **Inventory**
  tab; **Above its level**; or **No level set**.
- **Last Bought** — the price it last came at, from whom and when.

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

## Counting stock

**Stock Counts › + Add**, choose the warehouse, and **Fetch Items from
Warehouse** lists everything the books say is there. Type what you actually
counted over the quantities and submit: the difference is written off or found,
and the books match the shelf. The first count of a new warehouse is how you
enter opening stock — set **Purpose** to **Opening Stock**.

## What is kept where

OneCRM keeps customers, quotations and the sales order a won deal becomes;
OneBook keeps invoices, bills, payments and suppliers; OneInventory keeps
items, stock, what arrives and what is delivered, what is ordered from
suppliers, and the company's equipment. See OneBook's README for the whole
split.

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

- `item.py` and `public/js/item.js` — the item's band. ERPNext has every
  figure in a different place — the Bins behind the Stock Levels panel at the
  foot of the form, the reorder table on the Inventory tab, a Last Purchase
  Rate with no supplier or date — and `said` reads them into one answer.
  Low is ERPNext's own test, projected quantity at or below the level
  (`summary`, pure), so the band and the reorder list agree.
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
   order and from whom, made into purchase orders a supplier at a time.
5. **Assets: a register that finishes itself.** The assets a receipt makes are
   drafts nobody completes and so never depreciate; they are completed from
   their purchase and category, and an asset's page says what it is worth.
6. **Assets: who has what.** Give an asset to an employee and take it back in
   one step; an employee's page lists what they hold, and leaving asks for it
   back.
7. **Assets: maintenance.** What is due for a service, on the calendar and in
   the owner's tasks.
