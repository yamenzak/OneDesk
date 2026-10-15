# The passover

Every screen of One, one at a time, checked against the points below. You
decide when a screen is done and when the next one starts. This file is the
points and how a screen is walked; what each walk found and fixed, where each
area stands and what is up next are in `docs/PASSOVER-LOG.md`.

## The points

Seventeen points in five groups. Each has guards in the registry
(`tests/guards/`) that catch what a reading can miss. A new bad practice found
on any screen gets a guard first, then the fix.

### Works

1. **Demo coverage**: the screen's records exist in the demo company
   (`one_demo`), and the integration suite running on it covers every
   behaviour the screen has: each kind, each branch, each preset, each
   combination that matters (a project's kind against its sub-projects' kinds
   against how each bills). A feature without a demo record and a test on it
   is not finished.
2. **Rules on the server**: every rule lives in the record's own hooks
   (`validate`, `on_update`, `on_submit` and the rest, `doc_events` in
   `hooks.py`). Buttons and endpoints offer and orchestrate, never decide. So
   the list's bulk edit, the report view's inline edit and Data Import give the
   same result as the screen, and the demo suite checks they do.
3. **Hand-offs**: where the screen's data comes from and where it goes in
   the other modules: a deal's customer on the project, its billing in OneBook,
   its items in OneInventory, its people in OneHR and One, its tasks in
   OneTask. The module's README has a **Connections** section saying so, and
   the demo company runs each hand-off end to end.

### Stays desk

4. **Tier declared**: how the doctype is shown is recorded in the tier
   registry (`onedesk/one/tiers.py`), for the record and for every collection:
   - the record: **desk** (frappe's form as it is), **head** (the form with a
     Record Head), or **page** (a page of its own, for the few records people
     work inside all day: Project, Deal, Lead, Employee, Applicant);
   - each collection view frappe has, as frappe's own or ours: List, Report,
     Kanban, Calendar, Gantt, Tree, Image, Dashboard, Map and Inbox.
   A record moves up a tier only when the tier it has gets in the way of real
   work, and the registry says why.
5. **Our look**: the product has its own look, as OneMail and OneCloud do,
   rather than a standard desk. It still uses frappe-ui and espresso parts.
   Nothing looks boxed in: sections sit on the page, and Save goes in the page
   head. Every colour, border and corner is a frappe-ui token (`--ink-*`,
   `--surface-*`, `--outline-*`, `--radius-*`), a border is 1px, and nothing of
   ours casts a shadow (`tests/guards/test_tokens.py`).
6. **Nothing lost**: a page of its own keeps everything frappe's form gives,
   through the record frame: the menu (Print, PDF, Email, Copy Link, Duplicate,
   Delete, Customize, the form itself), the sidebar (Assign, Share, Like, Tags,
   Followers, attachments, who's viewing, created and modified by), the record
   kept live (`doc_subscribe`, `doc_update`), a change made against the
   `modified` it was loaded with, and a warning before leaving unsaved work.
   And every field of the record that can be typed in on its form is edited
   on the page: in its own place there, or in the page's Edit dialog, grouped,
   with any field a workspace adds under More. Its form stays in the menu as
   a fallback, never as the only way to a field
   (`test_a_page_edits_every_field_of_its_record`).
7. **Extensible**: what a workspace adds still reaches the screen. A Client
   Script runs on frappe's form; a page of its own declares its places, where
   OneStudio's extensions go. Server Scripts and our hooks run whatever the
   screen is.
8. **Built from frappe, in this order**: every part of the screen is taken
   from the first of these that has it, and only written by us when none does:
   1. a **frappe-ui component** (`node_modules/frappe-ui/src/components/`);
   2. the **desk's own parts**: its controls, `FieldGroup`, `FilterGroup`,
      list and form views, dialogs, and espresso's `frappe.ui.button`,
      `badge` and `alert`, looking the way frappe-ui draws them;
   3. frappe's **primitives and utilities**: `frappe.call`/`xcall`,
      `frappe.realtime`, `frappe.utils`, `__()`, the model and the router.
   Every value shown goes through `frappe.format` with its field, so the
   workspace's date, number and currency settings and the field's own
   precision and options apply. Nothing is formatted by hand.
9. **Overrides recorded**: whatever of frappe's, erpnext's or hrms's we
   change is recorded in `scripts/overrides.py` beside what it shadows, so
   `scripts/upstream.py` flags it when they change it. The order of choice is
   native first: Custom Fields and Property Setters, then hooks, then a Record
   Head or a form script, and a page of its own last.

### Speaks

10. **Notifications**: what the screen's events send, to whom, and whether
    the message reads well. Every notification and mail is one file in
    `onedesk/notifications/`, by module, on one layout; the workspace changes
    its own copy in Settings › Notifications.
11. **Printed**: a record that leaves the company (a quotation, an order, an
    invoice, a payslip, a report) has a designed print format we ship, built
    from our print blocks in the house look.
12. **Plain words**: every heading, note, button, column, badge, empty state
    and confirmation on the screen reads like a good SaaS product, as
    `docs/WORDING.md` says under On a Screen. A thing is called what ERPNext
    calls it, the name Ctrl+K finds: a rail row, heading, crumb, field label,
    column and status say the doctype's, report's, field's or status's own
    name (Purchase Receipt, not Receipts). A note is optional and one short
    sentence. Frappe's own words, never our coinages ("carry", "came with",
    "take back"). No colon or
    semicolon joining two clauses, and no narrating how OneAI works. The
    screen's README section is written the same way.

### Knows

13. **Documented, and OneAI knows and does**:
    - The screen has its section in its module's `README.md`, above
      `## Under the hood`, written for the people using it: what it is for,
      how to fill it in, and who sees and changes what.
    - OneAI answers "how do I…" from that section (`how_to`), knows which
      screen the reader is on and what records that means, and offers the
      screen's own suggestions if any are worth offering.
    - Whatever is AI on the screen is drawn one way: something OneAI does or
      did is `onedesk.oneai.tag` ("Read by OneAI"), and something that asks it
      is `onedesk.oneai.button`, opening the panel on the same question. A
      violet badge or a plain button standing in for one is a finding.
14. **Intake**: which mails and files should create or change this screen's
    records, and whether Intake does. The demo company has a real sample of
    each (`tests/samples`), and the suite has Intake handle them.

### Rules

15. **Permissions and roles**: who sees the screen, who may change what, and
    whether the server holds that line.
16. **Legal**:
    - Whatever the screen does that the agreements must say is declared in its
      module's `legal.py`, beside the code:
      - a `clause()` for the Privacy Policy, the Terms, the Data Processing
        Addendum or the AI Addendum;
      - a `subprocessor()` for any company it sends data to.
    - OneLegal assembles them into the documents people agree to
      (`one_legal/README.md`).
    - A changed clause fails `tests/guards/test_legal.py` until it is either a new
      revision (material, so everybody agrees again) or a recorded hash (a
      typo).
17. **Clean code**: the module keeps one layout, its logic, endpoints,
    notifications, legal and AI each in their place; a comment is only there
    when the code can't say why, in a line; the README carries the rest.

## Everything follows frappe

This applies to every screen, on top of the points. How a screen looks can
be ours; how it behaves is frappe's.

- **Fields** are frappe's own controls (`frappe.ui.FieldGroup`, or the desk
  form itself), never inputs drawn by hand. They carry frappe's Link search,
  date picker, validation and translation.
- **A record being edited** acts like a desk form:
  - It knows it is dirty by comparing against what was loaded, and it is clean
    again when a change is undone.
  - It warns before the page is left with unsaved changes.
  - It saves against the `modified` it loaded, so a change made elsewhere in
    the meantime is refused, not silently overwritten.
  - It listens on the record's realtime room (`doc_subscribe`, `doc_update`)
    and says when somebody else has changed it.
- **What a screen shows** changes live through `frappe.realtime` when the data
  under it changes, the way the desk's lists do.
- Where frappe already ships the behaviour, the screen uses it rather than a
  copy of it.
- **What a part looks like comes from frappe-ui.** The desk's espresso parts
  (`frappe.ui.button`, `alert`, `badge` and so on) are frappe-ui's design,
  ported to plain HTML, and the port is sometimes behind or simpler. Before
  using one, open the same component in frappe-ui
  (`node_modules/frappe-ui/src/components/<Name>/`: the `.vue`, its `.md` and
  its stories). Where the two differ, in layout, variant, size or colour,
  follow frappe-ui. For example, frappe-ui draws an alert with one action as
  one row, and espresso put the button on a line of its own. The desk part
  stays; only its look is brought in line. Behaviour is still frappe's.

## The panel

Your word: "it should be open on all collection views. On smaller devices it
becomes changeable from the breadcrumbs, like Projects ▾", and "make sure
it's universal over the app". Every module has this without asking
(`public/js/crumb_switch.js`, guarded by `tests/guards/test_record_page.py`).

- On a desktop the module's panel is open on every collection view (a list
  and its Report, Kanban, Tree and other views, a report, a page that lists).
  It is frappe's own sidebar, and a page leaves `hide_sidebar` unset.
- A record's page closes it (`hide_sidebar: !frappe.is_mobile()`), as a
  project's and a template's do.
- The breadcrumb switches, at any width (your word on 2026-10-13: "standardize
  the breadcrumbs dropdowns for switching doctype and document ... make it
  searchable like a link field"). Each crumb opens a search box over its
  choices (`public/js/crumb_switch.js`):
  - the place's name lists the module's places, read from the panel itself,
    in its order and under its sections, the place you are on marked;
  - a record's name lists the records of its kind and finds any as a link
    field does, a project's open projects first, **All Projects** pinned at
    the foot;
  - a crumb a page gives choices of its own (a project's **All Work**)
    filters those.
- On a phone the head is two bars (your word: "on mobile we need to introduce
  our double top navbar so we don't keep struggling with trimmed content",
  then "why not two navbars, why did you cram them up", then "top bar is for
  the doctype stuff, bottom bar is for the current doc, so the breadcrumb
  should split", then "move actions to the top bar"). Each is its own height
  with a line under it. The first is the panel's button, the place, the
  page's buttons and search. The second is the record's: its name, its status
  with its word and a scope such as a project's **All Work**. A list's second
  bar has its view switch (`public/js/phone_head.js`, `crumb_switch.js`).
- No module puts places of its own in the page head.
- Every view of a list marks the list's row in the panel.

## A record's page

Your word: "use frappe desk's sidebar, it's nicer and neater and cleaner on
the right side", and "move the vertical tabs to become horizontal tabs …
don't make them fixed". Every record shown on a page of its own
(`one/tiers.py` PAGES) is laid out as a frappe form is.

- Its details are frappe's own form sidebar on the page's right: the image,
  the name, print and like, Assign, Attachments, Tags, Share, and who last
  changed and made it. "Currently Viewing" is frappe's avatars in the page
  head. The desk page names its record (`onedesk.island_page`'s `record`),
  and `onedesk.record.sidebar` lends frappe's sidebar the part of a form it
  reads. A page draws none of this itself.
- Its Attachments are one **Files** row with the count, as on a form
  (`record_files.js`), never a list of files. It opens the page's own Files
  view (`island_page`'s `files`, a project's Files tab), or OneCloud on the
  record's folder where the page has none (a template).
- Its views are one row of tabs across the top under its head, as a form's
  tabs are (`frontend/src/kit/ViewTabs.vue`). When they do not fit, the row
  scrolls sideways, as a form's tabs do (your word: "switch it to
  scrolling"). A fade at the edge shows where more continue, and the chosen
  tab is scrolled into view, after a reload too. The row moves with the page,
  on a desktop and on a phone; it is never fixed to the top.
- On a phone frappe's sidebar is hidden, as on a form, and the tabs are the
  same row, swiped sideways.
- A place's crumb keeps its name and chevron whole at any width; the
  record's name after it is the one that shortens.
- Its Activity reads as a form's Activity does (your word: "comment box on
  top and a New Email button which simply opens the email dialog"), drawn
  with frappe/ui's timeline. At the top is frappe's own comment composer,
  as frappe ships it with no frame of ours (`frontend/src/kit/ActivityComposer.vue`), with
  @-mentions. Its toolbar's buttons are frappe-ui's smallest: frappe/ui
  asks for `button-size="sm"`, a prop no frappe-ui has (1.0.0 calls it
  `size`), upstream too, so it is left as frappe draws it. Under it are the page's filters and **New Email**, which opens
  frappe's own Email dialog on the record (`onedesk.record.email` in
  `record.js`, with the arguments the form timeline's compose_mail gives
  it). The list runs newest first, as a form's does, and **Show earlier
  activity** is at its foot. Each email has **Reply** and **Reply All**,
  which open the same dialog as on a form. A task's panel has the same.
- Every island sits inside frappe-ui's provider, as a Frappe UI app does, so
  its messages ("Email sent") and dialogs show. Times on an island are read
  in the site's timezone. They were not before, so a comment made a minute
  ago read "in 4 hours" wherever the browser's clock differed.

## What ERPNext already does

ERPNext handles more than a screen shows, and anything we build on top has to
keep it working. On every doctype the pass checks:

- **Currency.** A customer or supplier can be billed in their own currency,
  set by their receivable or payable account. A document we make for them
  takes that currency (`get_party_account_currency`), or ERPNext refuses it.
  Figures that add documents up use the `base_` amounts, in the company's
  currency, never the document's own. A rate we keep on our side (a monthly
  fee, a contract value) says which currency it is in.
- **The company.** No Company field or filter is shown, but every document
  still has one, from the user's default, and its accounts are that
  company's.
- **Draft, submitted, cancelled, amended.** Only submitted documents count.
  An amended document replaces the one it amends, and a revised quotation
  replaces the earlier one, so neither is counted twice.
- **Statuses ERPNext moves itself**, such as Expired, Overdue, Lost, Ordered,
  Partially Ordered and Completed. We read them, never work them out again.
- **One document made from another** goes through ERPNext's own mapper
  (`make_sales_order`, `make_sales_invoice` and the rest). It keeps the links
  between lines that ordered, billed and delivered amounts are counted from.
- **Taxes, price lists and discounts** come from the party and the item. A
  figure says whether it is before or after tax (we use net).
- **Precision and rounding** come from the field's precision through
  `flt(value, precision)`, never from rounding by hand.
- **Dates** show in the user's date format and time zone, and money periods
  follow the fiscal year.
- **Record access.** A User Permission (only this customer, only this
  project) narrows every list, figure and link the screen shows.
- **Units, stock and payment terms.** Quantities use the item's unit and
  conversion factor; a stock item moves stock; an invoice's due dates come
  from its payment terms.
- **Figures that add things up** (a Home, a card, a chart, a total). Set by
  the user on 2026-10-13, so it is never asked for again:
  - Each is the reader's company's, their default as
    `erpnext.get_default_company` reads it, in that company's currency. Two
    companies in two currencies are never added up. It reads amounts already
    in the company's currency (`base_` amounts, `stock_value`,
    `total_asset_cost`, a stock entry line's `amount`), never a document's
    own.
  - A quantity is added up only within one item, and shows its unit. Across
    items a figure is worth, in the company's currency, never pieces and
    metres in one bar.
  - It prints the way the reader and the workspace set it: money through
    `format_currency`, numbers through `format_number` (the kit's `money`,
    `count`, `hours`, `quantity`), months and days in the reader's language,
    and a week from System Settings' first day of the week (the kit's
    `weekdays`). Every frappe-ui chart and number card gets one of those
    formatters (`tests/guards/test_formats.py`).

## A record answers first

On top of the points, every record screen is checked against the record
shell (`docs/SHELL.md`), which is how One looks now and what the pass enforces:

- **Its head answers what somebody opened it for**, above the fields and on
  every tab: where it stands (the pill), one sentence when there is news, a
  band of metric cards (a value, a meter for a part of a whole, a change
  against the period before), a chart only where the trend is the question,
  and its verbs, each asking in frappe's own dialog, with at most one
  primary. A record with nothing worth saying there gets no head; one that
  has something gets a Record Head in its module's `heads.py`.
- **No form script draws a head.** A pill, a headline, a band or a progress
  bar set from a script is refused by `tests/test_head.py`, headed doctype or
  not. A script keeps only what is not a head: a dialog that answers inside
  itself, a sidebar action, a field's options.
- **A sentence that reads a field the form changes redraws as it changes**
  (`redraw_on`), so a new record says what it will do before it is saved.
- **Another record's fields are edited in place**, as a Linked Section,
  rather than by opening the other record.
- **Mail, Files and Activity are the record's own tabs** (`one_record_tabs`),
  not links out.
- **A workspace administrator shapes it from the form's menu** (Customize),
  and OneAI proposes a change through the same door. Nothing a workspace
  does is code.
- **Lists stay frappe's list.** No stat strip above one; numbers belong on a
  record's head or a dashboard.

## How one screen goes

1. Screenshot it and read the code behind it, and read its module in
   `docs/ATLAS.md`: what still waits, has no demo record, prints on
   ERPNext's format, lists only a number or reads in English.
2. Write the findings under the points in `docs/PASSOVER-LOG.md`, then "A
   record answers first" for a record screen, then anything else about using
   it (UX).
3. Fix them, look again in the browser, and run the gates: the fast tests,
   the guards, and the demo suite for the screen's module.
4. Commit, push, and show you a screenshot.
5. Wait for your word before the next screen. A module is not done while its
   modules have anything waiting in the atlas.
