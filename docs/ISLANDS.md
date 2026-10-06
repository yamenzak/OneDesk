# OneProject and OneBook in frappe-ui, inside desk

The project page built in jQuery over espresso's parts still did not look or
feel like frappe-ui. Frappe Books (github.com/frappe/frappe-books) shows what a
screen built from frappe-ui itself looks like. This is the plan to build
OneProject's and OneBook's own screens the same way without leaving desk.

## What Frappe Books is

- A Vue app with frappe-ui 1.0.0, served as its own page at `/books` on a
  Frappe site (Frappe v17, no ERPNext). It has its own doctypes, all named
  `Books …`, and its own ledger. It is not a desk app.
- Every visible part is a frappe-ui component, laid out with frappe-ui's
  Tailwind tokens and nothing of its own:
  - figures: `NumberCard` borderless, with `LineChart`, `BarChart` and
    `DonutChart` from `frappe-ui/charts`;
  - lists, child tables and reports: `List`, `ListRows`, `ListRow` and
    `ListCell` from `frappe-ui/list`;
  - the head: `PageHeader`, `Breadcrumbs` and `Badge`, `Dropdown` menus
    grouped as Create and View, and one solid button;
  - fields: `TextInput`, `Combobox`, `Select`, `DatePicker` and the other
    inputs; tabs are `TabButtons`; side panels and sheets are `BottomSheet`
    and `Dialog`.
- We take its patterns, not its app.

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
- An app builds all its islands in one Vite build and declares them in
  `hooks.py` as `ui_islands`.
- `@framework/ui` (frappe's own Vue parts, taken from CRM) is there too: Link,
  FormLayout, Grid, ListView, Filter, ActivityTimeline and FileUpload.

**Decided.** Every bespoke screen, in every app, is an island built from one
kit. Desk keeps everything desk does. The project page was the first,
replacing the jQuery page of stage 2.

## What changes in how we build

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
- **The build:**
  - `frontend/build-islands.mjs` builds every island in one go;
  - a root `package.json` with a `build` script, as Books has, lets `bench
    build` and Frappe Cloud build it;
  - `hooks.py` names each island.

## OneProject and OneBook together

They share most of what an island needs, so they are built together, in
stages:

1. **Foundation.**
   - `frontend/`, the build, and the desk bridge: words, money and dates,
     navigation, realtime and CSRF.
   - The shared parts: figures, sections, rows, Needs You, empty states.
   - The guards and the README.
2. **The project page.** The spike made whole: Overview for each kind, then
   Money and Suppliers (stage 3 of docs/PROJECT-PAGE.md), drawn from the same
   parts.
3. **OneBook Home**, as Books' dashboard:
   - paid and unpaid sales and purchases as figures that open the list;
   - Cashflow as a line chart;
   - Profit and Loss by month as bars;
   - Top Expenses as a donut;
   - a period picker in the head.
   - OneBook's own owed, owing and overdue stay.
4. **A document's actions, as Books does them**, on invoices, bills and
   orders:
   - Create and View menus grouped in the head;
   - after submit, the main button becomes the next step (Receive Payment,
     Make Payment);
   - the payment opens in a side panel and the invoice shows what is left;
   - a Linked Entries panel;
   - a hover preview of a linked record.
5. **Reports in Books' look**: Profit and Loss, Balance Sheet and General
   Ledger.
   - Rows as a tree that folds, from `frappe-ui/list`.
   - A date range with presets.
   - Export, and print with chosen columns.
   - ERPNext's own report data underneath.
6. **The rest of the project tabs**, the Retainer month, and the phone
   layout. Books' phone patterns are the reference: bottom sheets and pinned
   footers.

## From Books' features, worth adopting in OneBook

In the order they'd pay off:

- **Next step after submit**, **payment in a side panel**, and **Create and
  View menus** (stage 4).
- **Get Started that ticks itself**, as records are made: first customer,
  first invoice, opening balances and so on.
- **Payment history and balance on the printed invoice**, and sharing the
  PDF from a phone.
- **Import with column mapping**: paste or upload any CSV, map its columns,
  edit cells, then re-import only the failed rows. It runs over frappe's own
  Data Import.
- **Feature switches** that hide whole areas a business doesn't use: POS,
  batches, serial numbers, price lists.
- **Tax counted when paid** (cash-basis VAT). Books moves an invoice's tax
  to the tax account as it's paid. ERPNext doesn't do this, so it needs a
  design of its own before it's promised.
- **Already ours, Books lacks**: due dates and payment terms, ageing,
  statements, repeating invoices, the VAT return, closing the books, bank
  reconciliation and the cash-flow statement. They stay.
- **Not taken**: Books' own ledger and doctypes. OneBook stays on ERPNext.

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
  3. a line in `ISLANDS` and in `hooks.py` `ui_islands`;
  4. a desk Page whose script calls `onedesk.island_page`.
- **Guards** (`tests/guards/test_islands.py`):
  - every island is declared, built and mounted by a desk page;
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
- **Built so far**: the project page (`onedesk.project`), with its Money and
  Suppliers views. Next, in order: OneBook Home, then a document's actions,
  then reports. One screen at a time, as the passover goes.
- **Desk's dialogs stay desk's.** A field an island edits outside a row (a
  budget, a cost type, Bill Progress) opens the desk dialog the form uses,
  through `onedesk()`, so its controls, links and checks are frappe's.
