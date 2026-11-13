# OneFactory

The one file for agents, OneAI and us: what OneFactory is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `help/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `updates/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneFactory is where the company makes things: what each product is made
from, the work orders that make it, the steps on the shop floor, and the
work sent to suppliers. It was part of OneInventory until November 2026.

## Connections

- **From OneInventory**: What a work order uses and makes is stock: its
  materials leave a warehouse and what it makes arrives in one. An item's
  page shows its bill of materials and its open work orders under Making.
- **From OneCRM**: A work order can be for a customer's Sales Order, and
  says so at the top.
- **From OneHR**: Whoever works a step logs their time on its job card as an
  employee.
- **From OneProject**: A work order for a project names it, and so do the
  movements it makes.
- **To OneProject**: The materials a project's work orders use count in its
  Stock Used, and its manager is told when one is made.
- **To OneBook**: Workshop time is posted to the company's Default Operating
  Cost Account; a supplier's bill for work sent out is made from the
  purchase receipt its subcontracting receipt creates.

## Under the hood

### What it is made of

ERPNext's Manufacturing and Subcontracting modules: BOM, BOM Creator, Work
Order, Job Card, Routing, Operation, Workstation, Plant Floor, Production
Plan, Downtime Entry, Manufacturing Settings, Subcontracting Order and
Receipt are theirs. The stock they move is OneInventory's.

**Why it left OneInventory.** Making has its own people (the workshop, a
Manufacturing User and Manager), its own screens (the Shop Floor, the Plant
Floor) and its own rail; a business that buys and sells but makes nothing
never needs to see it. `hooks.py` `one_module_heirs` names OneFactory the
heir of ERPNext's Manufacturing and Subcontracting.

- `home.py`, `page/onefactory` and `frontend/src/factory/home` — the Home,
  an island (`tiers`): the figures (the Shop Floor's open and running, late
  work orders, `sent_out.figures` out, and the goods made this month from
  Manufacture entries' `total_incoming_value`, the reader's company's),
  Today (late, due to start, back late from suppliers, drafts) and the
  directory. It tells OneStudio `onefactory_home.shown`.
- `control.py`, `setup.py` and `public/js/one_factory/factory_control.js` —
  the Workshop tab of its settings: the company's Default Operating Cost
  Account and Work In Progress and Finished Goods warehouses, and the two
  setup steps that point at it. They were Inventory Check's until
  November 2026.
- `making.py` — a work order takes its bill's steps however it is saved.
  ERPNext's form fetches them when the bill is chosen, so one saved by Data
  Import, OneAI or a script had none and made no job cards; `steps`
  (before_validate) fills them.
- `floor.py`, `page/floor`, `frontend/src/factory/floor` and
  `public/js/one_factory/floor_actions.js` — the Shop Floor, kept as an island
  (`tiers`). `read` reads through ERPNext's own Shop Floor
  (`manufacturing/page/shop_floor`): its `get_work_orders` for the board and
  its count, and its `get_data` for a work order's or a workstation's job
  cards, with their materials, instructions, quality check and time logs.
  `_step` says what each step's buttons may do now (`may`), as ERPNext's page
  offers them. `figures` counts open work orders by ERPNext's own bucket, and
  running, waiting and closed-today job cards. Every change is ERPNext's
  whitelisted call, made from `floor_actions.js` in frappe's dialogs. The page
  follows Job Card and Work Order through frappe.realtime, and tells
  OneStudio `onefactory_floor.shown`. ERPNext's own page stays at
  /desk/shop-floor.
- `plant.py` — a plant floor as OneAI's `plant_floor_now` reads it (`now`):
  each workstation through ERPNext's `get_workstations`, the steps running on
  it from the Shop Floor's job cards, and the floor's stock from
  `plant_floor.get_stock_summary`. People see it on ERPNext's own Plant Floor
  form (`/desk/plant` leads to the list).
- `sent_out.py` — work sent to suppliers, as OneAI's `sent_out_now` reads
  it: `figures`, `orders` (out now, or done with) and `to_order`
  (subcontracted purchase orders with no subcontracting order yet).
  Subcontracting Order is frappe's own list and form (`/desk/sent-out` leads
  to it).
- `heads.py` — the head cards and measures of Work Order, BOM, Job Card,
  Subcontracting Order and Receipt (hooks `one_record_heads`,
  `one_measures`).
- `costs.py`, `access.py` and `public/js/one_factory/bom.js` — See What
  Making Costs, a Permission Type on Manufacturing Settings
  (`permission_type/`), the managers' to begin with. Without it a BOM's
  Costing tab is hidden (`onload` sets `one_costs_hidden`) and its head has
  no cost per unit. The fields stay readable through the API and reports.
- `tell.py` and `notifications.py` — Work Order Done, on a Manufacture
  entry's submit, to whoever asked (the request's or the customer order's
  maker, else the work order's) and the project's manager once the work
  order is Completed; Back From Supplier Late, the day after subcontracted
  goods were due back.
- `agent.py` — OneAI on the floor: `on_the_floor`, `plant_floor_now`,
  `sent_out_now`, `work_order_facts` (one work order's materials, steps and
  cost so far) and `plan_work_order` (a draft from an item's bill), with
  each page's suggestions and the Shop Floor's sentence (`page`).
- `boards.py` — ERPNext's Manufacturing dashboard, the rail's Overview,
  corrected after every sync and migrate.
- `access.py` — the Subcontracting BOM, the System Manager's alone in
  ERPNext, given to the buyers and the workshop, and the Plant Floor to the
  workshop.
- `custom/` — the BOM, Job Card, Work Order and subcontracting lists say
  what they make and for whom.
- `print_format/` — One Work Order (what to make and for whom, the materials
  and where from, each step), One Job Card (one step, its materials and
  time), One Bill of Materials (the materials and steps, and what it all
  costs), One BOM Creator, One Production Plan, and the work sent out and
  taken in: One Subcontracting Order, Receipt and Inward Order.

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, See What Making Costs, is `access.py`.
- **Setup** needs nothing of its own (`setup.py`); OneInventory's Inventory
  Check still sets the company's workshop account and work order
  warehouses. **Its tour** is `tour.py` over the Shop Floor's figures and
  views.
- **Its foot and settings** are `public/js/one_factory/factory_control.js`.
- **Its screens** are `frontend/src/factory/`.
- **Its checks** are `checks.py`, run with the rest by `one_demo/check.py`.
