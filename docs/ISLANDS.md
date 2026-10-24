# Islands: frappe-ui screens inside desk

Every bespoke screen, in every app, is an island built from one kit. Desk keeps
everything desk does. Each has one entry in `frontend/src/islands/`. Beside
them is the portal (`frontend/portal`), which is a
frappe-ui app of its own built from the same rules.

## How we stay in desk: islands

Frappe already has the way, in our bench's frappe: **desk islands**
(`frappe/ui/README.md`, decisions in `frappe/ui/island/decisions/`).

- An island is a Vue screen built with frappe-ui. A desk page mounts it with
  `frappe.ui.mount_island(name, el, props)`.
- It runs in a shadow root, so frappe-ui's styles and desk's never touch.
- It follows desk's light or dark theme.
- **Desk keeps the page head**: the breadcrumb, the status, the buttons and
  the ··· menu. The sidebar, the routes, the forms behind Edit Details,
  permissions and realtime stay frappe's.
- An app builds all its islands in one Vite build. An entry's name is the
  island's name: the build writes it into `assets.json`, which is frappe's
  registry of islands.
- `@framework/ui` (frappe's own Vue parts, taken from CRM) is there too: Link,
  FormLayout, Grid, ListView, Filter, ActivityTimeline and FileUpload.

## The rules

- **The order of parts, point 9 of the passover, for a bespoke screen:**
  1. a frappe-ui component;
  2. then `@framework/ui`;
  3. then frappe's calls (`frappe.call`, realtime, `__`, formats), handed
     to the island by the desk page;
  4. ours only when none of these has it.
- **The shell rules stay for every other page.** jQuery pages, settings and
  forms keep `onedesk.shell` and its guards. Islands get guards of their own:
  - every island is declared and built;
  - no CSS of our own beyond layout;
  - plain words checked in `.vue` too.
- **Desk does what desk does.** The head, the menu, Edit Details and the
  realtime room are the desk page's. The island draws the body and asks the
  page to act (Invoice Time, Bill Progress) through props.

## How it is built

- **`frontend/`** holds Vue 3, frappe-ui (pinned, 1.0.0 as Books) and
  `@framework/ui`, linked from frappe.
  - `build-islands.mjs` builds every island in one Vite build, so they share
    one Vue and one frappe-ui. Its `ISLANDS` names each one.
  - The root `package.json` has a `build` script, so `bench build`, and so
    Frappe Cloud, builds the islands with the rest of the app.
- **`frontend/src/kit/`** is what every screen is made from:
  - `desk.js` is the one bridge to desk: `__`, `call` (desk's `xcall`, so
    CSRF and errors are desk's), `money`, `date`, `hours`, `go`, `can`,
    `follow` (a record's realtime room, as a form follows it), `listen`,
    `newDoc` and `onedesk()` for our desk-side dialogs;
  - `mount.js` (`screen`) mounts a screen through frappe's contract, with
    `__` in every template;
  - `Page`, `Figures` (NumberCard), `Section`, `Rows` (`frappe-ui/list`),
    `Facts` and `Loading`;
  - `Pill` (a value from a short list, changed in place, as monday's status
    column), `People` (an avatar stack that assigns) and `Drawer` (a record
    opened beside the page, as Asana opens a task).
  - A part is added here only when frappe-ui and `@framework/ui` have none.
- **`onedesk.island_page`** (`public/js/island_page.js`) is the desk page
  around an island, as frappe draws its own Frappe UI pages:
  - it gives the island the route below the page and the query;
  - it sets the head from what the island reports: `onTitle`, `onStatus`
    and `onActions` (frappe's `{ label, onClick | href }`, with `primary` for
    the main button and `button` for one beside it; the rest go in the ···
    menu).
- **A new screen** takes:
  1. a component in `frontend/src/<screen>/`;
  2. an entry in `frontend/src/islands/` (`export const mount =
     screen(Component)`);
  3. a line in `ISLANDS`, named `onedesk.<screen>`;
  4. a desk Page whose script calls `onedesk.island_page`.
- **Guards** (`tests/guards/test_islands.py`):
  - every island is built and mounted by a desk page;
  - `bench build` builds them, with frappe-ui pinned;
  - a `.vue` file has no style, colour or import of its own;
  - only `kit/desk.js` reaches into desk;
  - every word goes through `__`, which frappe's extractor reads in `.vue`.
- **frappe-ui 1.0's tokens, not Tailwind's**: surfaces are `surface-base`
  (the page) and `surface-elevation-1` (a panel over it), and corners are
  `rounded-1` to `rounded-7`. `bg-surface-white`, `rounded`, `rounded-md`
  and `rounded-lg` don't exist there and draw nothing.
- **frappe-ui's resources call through `frappeRequest`.** The kit sets it as
  frappe-ui's resource fetcher when an island mounts, as a Frappe UI app does
  at start. A part that doesn't pass its own fetcher would otherwise call a
  path under the page.
- **Load the heavy parts when first shown.** An island loads within frappe's
  budget (2 MB). frappe-ui's editor, which `@framework/ui`'s timeline
  brings, loads through `defineAsyncComponent`. `@framework/ui` is imported
  by its part (`@framework/ui/ActivityTimeline`), never whole: the whole
  needs a newer frappe-ui than the one we pin.
- **Desk's dialogs stay desk's.** A field an island edits outside a row (a
  budget, a cost type, Bill Progress) opens the desk dialog the form uses,
  through `onedesk()`, so its controls, links and checks are frappe's.

## What each screen follows

A screen of our own is drawn after the app people already use for the same
job, not invented. `tests/guards/test_islands.py` reads this table: every
island screen and every portal page has a row, and every row names a file
that exists.

| Screen | Modelled on |
|---|---|
| `portal/src/App.vue` | frappe-ui's own shells, as Helpdesk and Gameplan use them |
| `src/sheet/WorkbookPage.vue` | Frappe Suite's Sheets, taken whole (src/sheet/VENDORED.md): Google Sheets' grid, formula bar, tabs, notes and version history |
| `src/writer/DocumentPage.vue` | Frappe Suite's Writer, taken whole (src/writer/VENDORED.md): Google Docs' page, toolbar, outline, comments in the margin and page setup |
| `portal/src/pages/Address.vue` | Shopify's customer account addresses: one form, Save |
| `portal/src/pages/Apps.vue` | GitHub's Authorized OAuth Apps: a line an app, Revoke |
| `portal/src/pages/Home.vue` | Shopify's customer account and Stripe's customer portal: a tile a kind they have, with what is left to pay on bills; then what asks something of them, each with its button, beside what came last |
| `portal/src/pages/Link.vue` | Stripe's hosted invoice page and DocuSign's signing page: one thing, from one sender, to one person |
| `portal/src/pages/List.vue` | Shopify's order list in a customer account and Stripe's invoices: the states as tabs with their counts over a table in a card, each row its number and date, what it is for, its state, the date it looks ahead to and its total |
| `portal/src/pages/Menu.vue` | Gameplan's More tab on frappe-ui's MobileShell |
| `portal/src/pages/Password.vue` | GitHub's Change password: three fields and Update |
| `portal/src/pages/Profile.vue` | Shopify's customer account profile: one form, Save |
| `portal/src/pages/Project.vue` | Basecamp's client view of a project: its photos beside how far along it is and when it ends, then its milestones as a line of dates, its sub-projects and tasks, and beside them its order and invoices, the time a member is shown and its files |
| `portal/src/pages/Record.vue` | Shopify's order page in a customer account, with Stripe's invoice summary: where it is on its way across the top, its items and totals in one card, and beside them what it comes to (what is left to pay, and Pay), its details and the records before and after it |
| `portal/src/pages/Rfq.vue` | Ariba's supplier quote: the buyer's message, each row priced in place in one card, with a discount and the tax the workspace charges on it, and the totals; notes; and beside them what the quote comes to and Send Quote (`send_quote`) |
| `portal/src/pages/YourData.vue` | Google Account's Data & privacy: download, or delete |
| `src/check/CheckList.vue` | Shopify's setup guide and Stripe's account checklist: how much is ready, then what is still to do, what is suggested and what is ready, each with what it means and its Fix |
| `src/floor/ShopFloor.vue` | Odoo's Shop Floor: a tab per workstation, the orders as a table, and each step a card with its clock, who is on it and one button for what comes next |
| `src/home/BooksHome.vue` | Frappe Books' Dashboard: the figures that matter, then cash flow, profit and the largest expenses, then where the receivables and payables stand; laid out as OneInventory's Home |
| `src/home/CrmHome.vue` | Frappe CRM's Dashboard: the figures that matter, then the sales trend, the forecast and the funnel, where the pipeline stands and where sales come from; laid out as OneBook's Home |
| `src/home/HrHome.vue` | HRMS's own phone app's Home (check in, your requests, your team's requests, the leave you have left) for everybody, and laid out as OneCRM's and OneBook's Homes for HR; like them a place an extension may add to |
| `src/home/InventoryHome.vue` | Shopify's admin Home: the figures that matter with their trend, then what needs somebody, then where everything is |
| `src/cloud/OneCloud.vue` | Windows Explorer and Finder: folders as a tree, Details and Tiles, the chosen file beside them, and Explorer's keys, menus, cut, copy and paste, rename in place and dragging |
| `src/intake/IntakeInbox.vue` | Gmail's and Outlook's inbox with the reading pane: one line per document, unread in bold, two boxes, the one open beside the list with what waits for a decision |
| `src/mail/OneMail.vue` | Gmail and Outlook: the mailboxes and their folders down the side, the conversations, the one open beside them read as a thread, and Gmail's keys |
| `src/item/ItemPage.vue` | Shopify's product page and Odoo's product form: what kind of thing it is, what it is called, the one thing worth saying, what it is and how much of it there is, then a view each for its stock, buying, selling and making |
| `src/legal/Agreements.vue` | Stripe's legal centre and GitHub's site policy: the documents down the side with where each stands, the one open in the middle, and who agreed to it and when beside it |
| `src/lots/LotsPage.vue` | Odoo's Lots and Serial Numbers and Katana's batch tracking: a table of lots with one status each, filtered by state above it |
| `src/plant/PlantFloor.vue` | Odoo's work centres overview: a card per workstation with its status to change in place, what runs on it with its clock, and what waits |
| `src/project/ProjectPage.vue` | Asana's project and monday's boards: a head with its health, then views that each open in place, as a form's tabs do, across the top under the head |
| `src/quotes/QuotesPage.vue` | Odoo Purchase: Asked is its list of RFQs, Quotes its vendors' quotations, and Compare its Compare Product Lines, one request's quotes side by side with the cheapest marked |
| `src/sent_out/SentOutPage.vue` | Katana's outsourced purchase orders and Odoo's subcontracting: one table of what is out, and the orders not ready to send above it |
| `src/stock/StockOnHand.vue` | Shopify's Inventory and Katana's Stock screen: a picture and a name, one status, and on hand split into what is committed and what is available, with what is coming in |
| `src/supplier/SupplierItems.vue` | Odoo's vendor price list and Zoho Inventory's items on a vendor: the item with their own code for it, the last price paid in their money, how much was bought in a year, what is on order and the lead time, then what they quoted for and were never ordered from |
| `src/task/MyTasks.vue` | Asana's My Tasks and Todoist's Upcoming: Overdue, the next seven days and Later, each task ticked off in place, a timer on it |
| `src/task/TaskPage.vue` | Linear's issue and Asana's task: where it stands, what it is called, the one thing worth saying, when it runs and how far along it is, then its details, time, files and activity |
| `src/task/Timers.vue` | Toggl's and Harvest's timer: the one running with its clock, pause and stop, then the ones paused to resume |
| `src/template/TemplatePage.vue` | TeamGantt's and Smartsheet's project templates |
| `src/to_order/ToOrderPage.vue` | Odoo's Replenishment screen: one line per item and warehouse, why it is there, how many and from whom, ticked and ordered in one go, a draft purchase order per supplier |
| `src/upkeep/UpkeepPage.vue` | UpKeep's and Fiix's work order lists: a table per tab, one status per row |
| `src/workload/WorkloadList.vue` | Asana's Workload and Float's capacity view: the team's week in one line with a bar, then a row a person, their load as a bar that turns red past what they have, the hours planned of the hours free, and their tasks, late and not estimated, each opening the tasks it counts |
