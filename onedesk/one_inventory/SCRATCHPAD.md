# OneInventory scratchpad

What is known to be wrong and what is planned, kept short.

## The pass of November 2026, where it stands

Run by the passthrough skill (two kinds of app; OneInventory is on ERPNext).
The scope, decided with Yamen on 5 November 2026:

1. **Islands.** Moved to frappe's own screens, done: Lots (Batch, Serial No
   lists), Quotes (Request for Quotation; Order Cheapest on its Create
   menu; ERPNext's comparison report), Sent Out (Subcontracting Order),
   Upkeep (Asset Maintenance Log; Mark Done its primary action), Plant
   (ERPNext's Plant Floor form). Kept as ours, with their reason in
   `tiers`: Item (a cornerstone page), Stock Summary (`stock-on-hand`),
   Reorder (`to-order`), Shop Floor (`floor`). Still to decide with Yamen:
   **Supplier Items** (`supplier_items`, on a supplier), in the buying area.
2. **OneFactory.** Manufacturing leaves OneInventory for an app of its
   own (decided 5 November): BOM, BOM Creator, Work Order, Job Card,
   Routing, Operation, Workstation and its types, Plant Floor, Production
   Plan, Downtime Entry, Manufacturing Settings, the Shop Floor, and
   subcontracting. Quality, assets and shipping stay here.
3. **The five failing demo checks**, then the areas.
   - `the_stock_in_the_books_is_what_the_warehouses_hold`: the books hold
     108 AED more stock than the warehouses (402,997.13 against
     402,889.13). Back-dated reposts used to fail on R2 (fixed, aa48d968);
     what is left is to find.
   - `home_says_what_needs_somebody_and_where_everything_is`: a block is
     empty (`rows: []`).
   - `stock_on_hand_says_what_the_stores_hold`: returns nothing.
   - `hand_offs_from_the_other_side`: a figure says 100.0.
   - `the_plant_floor_shows_each_workstation`: the workstations' statuses
     are not what the demo set (moves to OneFactory with the floor).
4. **The areas**, each: the registry for every record type it reaches
   (icons, cards, track, states, links), OneAI actions and notifications
   and permissions for what is missing, setup steps, tours, Help from
   ERPNext's docs in our words, several companies, the walk at 1440 and
   390 in Arabic and dark, then stamps. In order: stock, buying, quality,
   assets, shipping.

Baseline on 5 November, a phone at 4x CPU: Home 4.4s, Item list 6.1s, the
Item page 7.3s and 27 requests, Stock Summary 1.8s, Stock Balance 3.0s.

## Found on the walk, for the areas

- Serial No rows say Active twice (the pill and the line under the name).
- A batch row shows its quantity with no unit, and no expiry date.
- Arabic cuts an item name at its start ("…therproof").
- Every Request for Quotation row says Submitted, where the island said
  Waiting, Answered or Ordered.
- On a phone a request's head shows only Cancel: check Create and View.
- A service shows frappe's "Submit this document to confirm" over Mark
  Done (head.js drops that intro only for some verbs).
- A query report's Check filters overlap their labels (Stock Balance).
- Stock Balance is a prepared report: it opens empty until Generate.
