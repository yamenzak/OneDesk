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
3. **The four failing demo checks** (the plant floor's was fixed in OneFactory), then the areas.
   - `the_stock_in_the_books_is_what_the_warehouses_hold`: the books hold
     108 AED more stock than the warehouses (402,997.13 against
     402,889.13). Back-dated reposts used to fail on R2 (fixed, aa48d968);
     what is left is to find.
   - `home_says_what_needs_somebody_and_where_everything_is`: a block is
     empty (`rows: []`).
   - `stock_on_hand_says_what_the_stores_hold`: returns nothing.
   - `hand_offs_from_the_other_side`: a figure says 100.0.
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

## OneFactory: the split, step by step

Decided 5 November 2026. A new app, folder `one_factory`, frappe module
OneFactory, rail and dock row onefactory. Ticked as each lands.

What moves out of `one_inventory` (and its places):
- [x] `making.py` (Work Order steps, hooks.py doc_events), `floor.py` and
  page `floor` with `frontend/src/inventory/floor` (Shop Floor, kept as an
  island, `tiers`), `plant.py`, `sent_out.py`.
- [x] `custom/`: bom, bom_item, bom_operation, bom_secondary_item, job_card,
  work_order, work_order_additional_item, every subcontracting_* file.
- [x] `print_format/`: one_bill_of_materials, one_bom_creator, one_job_card,
  one_production_plan, one_work_order, one_subcontracting_order,
  one_subcontracting_receipt, one_subcontracting_inward_order (their JSON's
  module too).
- [x] `number_card/`: none after all (Made and Sent Out This Month are the stock story's).
- [ ] From shared files, the making parts: `ai.py` (on_the_floor,
  plant_floor_now, sent_out_now, the making tools and suggestions, REACH
  and NOT_FOR_AI entries), `notifications.py` (work orders, back from
  supplier late, …), `abilities.py` (Manufacturing roles), `heads.py`
  (BOM, Work Order, Job Card, Workstation, Subcontracting Order), `home.py`
  (the making section, EVERYTHING rows), `tour.py`, `setup.py`
  (Manufacturing Settings), `boards.py` (the Manufacturing dashboard),
  `checks.py` (the making checks), `access.py`, `legal.py` if any.
- [x] Sidebar: the Manufacturing group leaves `oneinventory` for a new
  `onefactory` sidebar; the dock (`dock/onedesk/onedesk.json`) gains a row;
  `add_to_apps_screen` if each app has one.
- [ ] Registry: `ready.MODULES["OneFactory"]` (folder, screens, names,
  help), `modules.txt`, the apps list people are given (one/people.py and
  one_demo/people.py), its mark in `scripts/icons.py` (and a flat twin),
  `one_ai/groups.py`, `tiers.SCREENS`, ISLANDS.md, the guards' lists.
- [ ] Docs: `docs/manufacturing.md` becomes OneFactory's pages (what it
  is, work orders and the floor, bills of materials, subcontracting,
  notifications, asking OneAI, who can do what, settings), AGENTS.md and
  SCRATCHPAD.md of its own, a first version 1.0.0; OneInventory's pages and
  a version say manufacturing moved.
- [ ] Translations, close.py, the gates, the demo checks for both apps.

Done and committed on 5 November 2026 (OneFactory 1.0.0, OneInventory 1.5.0);
what OneFactory still lacks is in its own SCRATCHPAD. Old notes:
done: files moved with git mv, their JSON's module, imports; the rail
(`one_factory/sidebar/onefactory`, Overview, Shop Floor, Plant Floor, Work
Order, Job Card, Production Plan, BOM, Subcontracting Order) and the dock
row; the mark (brand/onefactory.svg, icons.py); modules.txt; people.APPS
and APP_SAID; demo people (Tariq Manager, Karim and Yousef User);
abilities.py; ready.MODULES (ready False); ai.py (tools, suggestions,
page, hooks); notifications.py and tell.py (Back From Supplier Late, Work
Order Done, hooks); heads.py (HEADS, MEASURES, hooks).
next: home.py (making rows, the work count), tour.py, setup.py, boards.py,
checks.py, access.py, legal.py, AGENTS, SCRATCHPAD, docs and 1.0.0,
tiers/ISLANDS/guards for the floor's new path, then close and the gates.
