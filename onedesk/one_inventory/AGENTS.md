# OneInventory

The one file for agents, OneAI and us: what OneInventory is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneInventory is what the company holds: the goods it buys and sells or uses up
(stock), and the equipment it keeps — laptops, vehicles, tools (assets). It is
where things arrive from suppliers, leave for customers and move between
places, where the workshop makes them, and where you order more. It shares
its records with OneBook, so a delivery here is the same record an invoice in
OneBook is made from, and an asset's depreciation lands in OneBook's books by
itself.

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
  Order, Moves This Month — labelled Stock Transactions This Month, since it
  counts papers, not ledger rows), each counted by its method in `story.py`
  (`stock_worth`, `taken_in_this_month` and so on). Any frappe dashboard or
  workspace can show them, and frappe shows each only to somebody who may read
  the record type it names.
- `boards.py` — ERPNext's Stock, Buying, Manufacturing and Asset dashboards
  (the rail's Overview rows) corrected after every sync and migrate: the
  three monthly counts filtered to this month rather than to 2020, no
  growth shown on a count of what exists, sums of money in the company's
  currency, and Asset Value Analytics over every asset, like its card.
- `story.py` and `frontend/src/inventory/home/InventoryStory.vue` — Home's Overview.
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
- `home.py`, `page/inventory` and `frontend/src/inventory/home` — Home. `needs_you`
  reads what needs somebody through `ai.late_orders`, `ai.running_low` and
  `ai.services_due` (OneAI reads the first and last through
  `still_to_arrive(late_only=True)` and `upkeep_now(days=...)`) and
  `batches.dated`, each as the reader may see it, `FEW` rows of each with how many more. `drafts` counts papers left
  as drafts more than a day. `EVERYTHING` is the directory, each entry with
  what it is for, shown only when the reader may open it (a doctype's read
  permission, a report's or page's own roles). The rail's Reports and Setup
  are Page links to it with a route (`/desk/inventory/reports`).
- `lots.py`, `frontend/src/inventory/lots` and `public/js/lots_actions.js`
  — what is kept in lots and by number. Batch and Serial No are frappe's
  own lists and forms (the Lots page went in November 2026; `/desk/lots`
  leads to Batch). `lots` gives Batch with something left, sorted by expiry
  in Python, each with `batches.state` and `batches.left`; `serials` gives
  Serial No, in stock first; `kept_in_lots` the items with has_batch_no or
  has_serial_no; `figures` the counts. The item's Stock view reads `lots`
  and `serials` through `view.py`, drawn by `LotRows` and `SerialRows`.
  Track Batches, on the item, sets the item's own fields (has_batch_no,
  create_new_batch, batch_number_series, has_expiry_date,
  shelf_life_in_days, or has_serial_no, serial_no_series, warranty_period)
  with `frappe.client.set_value`, so ERPNext's Item rules apply; its item
  picker is `can_be_tracked`, items with no stock ledger entry. New Batch
  inserts a Batch with `frappe.client.insert`, and ERPNext numbers it and
  works out its expiry. OneAI's `lots_and_numbers` reads the same.
- `quotes.py`, `public/js/quotes_actions.js` and
  `public/js/one_inventory/request_for_quotation.js` — asking for prices.
  Request for Quotation and Supplier Quotation are frappe's own lists and
  forms (the Quotes page went in November 2026; `/desk/quotes` leads to the
  requests), and ERPNext's own View › Supplier Quotation Comparison is the
  side by side. `figures`, `asked` (Request for Quotation with its
  suppliers' quote_status and each one's quote, `_answers`), `quotes` and
  `compare` are what OneAI's `quotes_now` reads: `compare` sets a request's
  lines against each supplier asked, rate and base_rate from Supplier
  Quotation Item, the cheapest live base_rate marked, and a line ordered
  when the quotes' ordered_qty covers it. Every change is ERPNext's mapper:
  `ask` (a project's Suppliers, Ask for Prices) runs Material Request's
  `make_request_for_quotation`, inserts it and, sent, submits it and runs
  `send_supplier_emails`; `order_cheapest` (the request's Create › Order
  Cheapest, once a quote is submitted) runs
  `supplier_quotation.mapper.make_purchase_order` per supplier with
  `filtered_children` for the lines they are cheapest on, leaving drafts.
- `sent_out.py`, `page/sent_out`, `frontend/src/inventory/sent_out` and
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
- `upkeep.py`, `page/upkeep`, `frontend/src/inventory/upkeep` and
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
- `floor.py`, `page/floor`, `frontend/src/inventory/floor` and
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
- `plant.py`, `page/plant`, `frontend/src/inventory/plant` and
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
- `view.py`, `page/item_view` and `frontend/src/inventory/item` — an item's page. An
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
- `barcodes.py` and `frontend/src/inventory/item/ItemBarcodes.vue` — barcodes, in
  ERPNext's own Item Barcode table. `coded` gives a new item its code as its
  first barcode on every path an item is made by. `save` keeps the order the
  dialog leaves, so the first two are the head's. They are drawn by frappe's
  own Barcode control in the format their type names.
- `stock.py`, `page/stock_on_hand` and `frontend/src/inventory/stock` — Stock on
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
  on the portal (`one_inventory/portal.send_quote`) takes each line's project from the
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

  **To Order** (`page/to_order`, drawn by `frontend/src/inventory/to_order` from
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

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, Fix What the Check Finds, is `abilities.py` with its
  Permission Type on Stock Settings in `permission_type/`. `ready.fixes`
  reads it, for Inventory Check's Fix and the batch switch on Lots. Its roles
  are ERPNext's own; `USER` names Stock User, which People gives rather than
  everybody.
- **Setup** needs nothing of its own (`setup.py`): Inventory Check is it.
  **Its tour** is `tour.py` over Home's figures and views, and **OneAI's
  reach** is `ai.py`'s NOT_FOR_AI: every change OneAI suggests is a `plan_*`
  card of its own.
- **Its foot and settings** are `public/js/one_inventory/inventory_control.js`.
- **Its screens** are `frontend/src/inventory/`, a folder for each island.
- **Its checks** are `checks.py`, run with the rest by `one_demo/check.py`.
