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
   Reorder (`to-order`), Shop Floor (`floor`). **Supplier Items** is kept, brought into the new UI
   (decided 5 November).
2. **OneFactory.** Manufacturing leaves OneInventory for an app of its
   own (decided 5 November): BOM, BOM Creator, Work Order, Job Card,
   Routing, Operation, Workstation and its types, Plant Floor, Production
   Plan, Downtime Entry, Manufacturing Settings, the Shop Floor, and
   subcontracting. Quality, assets and shipping stay here.
3. **The failing demo checks**: done 5 November (c698f191), 28 of 28.
4. **The areas**, each: the registry for every record type it reaches
   (icons, cards, track, states, links), OneAI actions and notifications
   and permissions for what is missing, setup steps, tours, Help from
   ERPNext's docs in our words, several companies, the walk at 1440 and
   390 in Arabic and dark, then stamps. In order: stock, buying, quality,
   assets, shipping.

Baseline on 5 November, a phone at 4x CPU: Home 4.4s, Item list 6.1s, the
Item page 7.3s and 27 requests, Stock Summary 1.8s, Stock Balance 3.0s.

## The stock area: closed 5 November 2026

Walked at 1440 and 390, Arabic and dark, fixed and stamped; OneAI records a
count (plan_count); a check keeps a second company's stock out; Help says
how stock is valued. Setup steps for the setup page: Inventory Check's
rows. A record type's own tour waits for Help to offer tours. Left for
OneInterface: a record's item table cuts its columns (frappe's grid).
Next area: buying. Supplier Items, decided with Yamen on 5 November: kept
as ours, brought into the new UI (Canvas: section cards, the list rule).

## The buying area: walked 5 November 2026

Walked at 1440 and 390 in Arabic and dark, fixed and stamped. Supplier
Items sits in ERPNext's own Items tab. OneAI, notifications and Help
looked at and current. Left: a material request's title is ERPNext's
English, written into the record. Next: quality, then assets, shipping.

## The pass of November 2026: done (5 November)

Every area walked at 1440 and 390 in Arabic and dark, fixed and stamped:
stock, buying, quality (with OneQuality split out), assets, shipping.
Still open, for later passes: a record's item table cuts its columns
(frappe's grid, for OneInterface); a material request's title is
ERPNext's English, written into the record; the demo's second company
has no stock of its own (the check makes it in a rollback).

## Closing the pass: 6 November 2026

What the 5 November pass left, done: shortcuts.py (/ and O); every
whitelisted method read for permission and POST; ERPNext's statuses,
mappers and base_ figures; the portal (the RFQ print named every
supplier); Intake (a delivery note receives what it lists); deleting
(Portal Link swept); several companies (`ready.MODULES["companies"]`, the
check, a User Permission); 15 mails in English and Arabic; Help pictures on
seven pages; tours for Stock Summary and Reorder; OneAI's seven inv- cases
in `one_ai/evals.py` all pass; a tablet, German, the Standard palette, a
sales user, a cancelled request and a euro order; live updates; reach.

Finished the same evening, as OneCRM's close found: empty dates (a service
with no due date counted as due, in the reminder and on Home); keys with
real presses (/ searches, O asks before drafting, Tab and focus, Escape);
no setup steps of its own (Inventory Check does that); sharing is the
request for quotation's portal link; mail lands on orders, requests and
suppliers; OneCalendar has Goods Expected and Deliveries Due.

Left:
- **A fresh site.** Not walked: this bench keeps only the domain pair and
  Yamen wants no .localhost sites; Inventory Check is what a new workspace
  meets first.
- **The demo's second company**: done, Sahara Glass Saudi (`one_demo/branch.py`), with stock, an order and a sale; the check reads Riyadh's Stock Summary in riyals.
- **Speed**, a phone at 4x CPU on 6 November against 5 November: Home 4.5s
  (4.4), Item list 6.5s (6.1), the Item page 10.5 to 11s with 23 requests
  (7.3s and 27 as its own page, before it became a form), Stock Summary
  2.4s (1.8), Stock Balance 5.2s (3.0), Reorder 2.0s. The Item and Purchase
  Order forms spend it in frappe's form toolbar and in style recalculations
  (OneInterface's scratchpad).
- Every Request for Quotation row says Submitted, where the island said
  Waiting, Answered or Ordered.

## OneFactory: the split, done 5 November 2026

Decided 5 November 2026; every step below landed (OneFactory 1.0.0,
OneInventory 1.5.0), and what OneFactory still lacks is in its own
scratchpad. A new app, folder `one_factory`, frappe module
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
- [x] From shared files, the making parts: `ai.py` (on_the_floor,
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
- [x] Registry: `ready.MODULES["OneFactory"]` (folder, screens, names,
  help), `modules.txt`, the apps list people are given (one/people.py and
  one_demo/people.py), its mark in `scripts/icons.py` (and a flat twin),
  `one_ai/groups.py`, `tiers.SCREENS`, ISLANDS.md, the guards' lists.
- [x] Docs: `docs/manufacturing.md` becomes OneFactory's pages (what it
  is, work orders and the floor, bills of materials, subcontracting,
  notifications, asking OneAI, who can do what, settings), AGENTS.md and
  SCRATCHPAD.md of its own, a first version 1.0.0; OneInventory's pages and
  a version say manufacturing moved.
- [x] Translations, close.py, the gates, the demo checks for both apps.

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
