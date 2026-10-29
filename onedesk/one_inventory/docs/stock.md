# Stock and Warehouses

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
none at all is a dash, so the figures that matter stand out. On a phone a line keeps the picture, the name, the status
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

## Moving Stock

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

## Counting Stock

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

## When Stock and Books Disagree

A back-dated entry, such as a count dated last week, makes the stock values
after it be worked out again. **Stock values are up to date** in the
Inventory Check says when a recalculation stopped with an error, and **Fix**
tries it again. **Every warehouse posts to a stock account** says when a
warehouse's stock is posted to an account that is not a stock account, so
stock and the books can never agree. Both are told to the stock and accounts
managers as **Reposting Failed** and **Stock Account Wrong**.
