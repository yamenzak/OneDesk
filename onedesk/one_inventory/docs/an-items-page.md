# An Item's Page

An item opens on its form, with its picture, name and code at the top and,
for a stock item, four figures beside them: **On Hand** across every
warehouse, **Free to Sell** (on hand, less what is promised to customers),
**On Order** and what it is worth in the books (**Stock Value**).

Beside its name is **Order More**, or **Make More** for something made here,
or **Add Variant** for a template. **Create** has **Request Material**,
**Transfer Stock** and **Count Stock**, each starting the document with the
item on its first line.

Its tabs are the item's own: **Details**, **Accounting**, **UOM**,
**Inventory**, **Purchasing**, **Sales** and **Manufacturing**, each with the
fields that belong there. Four of them start with what the item has there now:

- **Inventory**: each warehouse by its own name, with what it holds, what is
  free to use, what is on order and what it is worth, and a bar against its
  reorder level. The level and how much is ordered at a time are changed on
  the row, and each row's menu has **Transfer Stock** and **Count Stock**.
  Then its batches, and its last moves in plain words ("Moved 120 from
  Stores to Branch Store", "Used 80 on Head Office Move"), each with who
  made it.
- **Purchasing**: who it is bought from, each with the last price ordered
  and the one before it in their own currency, what they agreed for the
  year and their part number. **Add Supplier** puts one on the item's list,
  and each supplier's menu has **Order from Them**, **Request for
  Quotation** and **Make Default**. Then the quotes still open, the cheapest
  marked, each with **Order This**; what is on order, with **Receive**;
  what has been asked for, with **Make Order**; who makes it; and the
  buying prices, changed on the row.
- **Sales**: what customers have ordered and not yet had, each saying **Can
  Go Now** or how many it is short, with **Deliver** and **Invoice**. Then
  the quotes still open, who bought it in the last twelve months with their
  last price and their own code for it, and the selling prices, changed on
  the row.
- **Manufacturing**: what it is made from, with how many its free stock
  would make ("Enough for 182, Structural Silicone runs out first"), the
  steps that make it with their minutes and cost, the work orders still
  open with **Finish** and **Open on Shop Floor**, and what was made in the
  last twelve months.

Each changes as soon as the stock, an order or a price does, without
reloading. A template's variants are made from **Create › Multiple
Variants**, and barcodes are kept in the item's **Barcodes** table.

OneAI reads an item as its page shows it, says what is running low, and
suggests a change to an item (its name, group, lead time, whether it is
disabled, or a warehouse's reorder level) as a card you approve.
