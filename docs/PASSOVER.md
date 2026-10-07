# The passover

Every screen of One, one at a time, checked against the points below. You
decide when a screen is done and when the next one starts. This file is where
each screen's findings and fixes are written down.

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
   head.
6. **Nothing lost**: a page of its own keeps everything frappe's form gives,
   through the record frame: the menu (Print, PDF, Email, Copy Link, Duplicate,
   Delete, Customize, the form itself), the sidebar (Assign, Share, Like, Tags,
   Followers, attachments, who's viewing, created and modified by), the record
   kept live (`doc_subscribe`, `doc_update`), a change made against the
   `modified` it was loaded with, and a warning before leaving unsaved work.
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
    `docs/WORDING.md` says under On a Screen. A heading is the plain name of
    what is listed. A note is optional and one short sentence. Frappe's own
    words, never our coinages ("carry", "came with", "take back"). No colon or
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
(`public/js/panel_menu.js`, guarded by `tests/guards/test_record_page.py`).

- On a desktop the module's panel is open on every collection view (a list
  and its Report, Kanban, Tree and other views, a report, a page that lists).
  It is frappe's own sidebar, and a page leaves `hide_sidebar` unset.
- A record's page closes it (`hide_sidebar: !frappe.is_mobile()`), as a
  project's and a template's do.
- Wherever the panel is not out, the breadcrumb is the menu of the module's
  places, read from the panel itself, in its order and under its sections,
  the place you are on ticked:
  - on a phone, the place's own name at the top, **Projects ▾**;
  - on a record's page, the place's name before the record's, at any width.
  The record's own name keeps its own menu, as a project's lists the others.
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

1. Screenshot it and read the code behind it.
2. Write the findings under the points, then "A record answers first"
   for a record screen, then anything else about using it (UX).
3. Fix them, look again in the browser, and run the gates: the fast tests,
   the guards, and the demo suite for the screen's module.
4. Commit, push, and show you a screenshot.
5. Wait for your word before the next screen.

## Where we are

| Area | Screen | State |
|---|---|---|
| Settings, You | Profile | done (second pass too) |
| Settings, You | Notifications | done, second pass |
| Settings, You | Mail | done |
| Settings, You | Calendar | done |
| Settings, You | Sign-in | done |
| Settings, You | What OneAI Remembers | done |
| Settings, You | Agreements | done |
| Settings, Workspace | General | done |
| Settings, Workspace | People | done |
| Settings, Workspace | Notifications | done (stages 2 and 5 of NOTIFICATIONS.md) |
| Settings, Workspace | Plan and Credits | done |
| Settings, Workspace | Domains | done |
| Settings, Workspace | OneAI (now OneAI › Actions) | done |
| Settings, Workspace | OneIntake (now OneIntake › Settings) | done |
| Settings, Workspace | Holidays | done |
| Settings, Workspace | Masters, and the Address Book | done |
| Products | One › Home | done |
| Products | OneMail | done |
| Products | OneCloud | done |
| Products | OneCalendar | done |
| Products | OneTask | done |
| Products | OneAdmin › Home | done |
| Products | OneStudio › Extensions | done |
| Products | OneStudio › Forms | done |
| Products | OneStudio › Custom Collections | done, second pass |
| Outside the desk | The portal, and the public Your Data page | done (Portals 1 to 8) |
| Products | OneProject › Projects | done |
| Products | OneProject › Templates | done |
| Products | OneCRM, OneBook, OneInventory, OneHR, OneAI, OneIntake, the rest of OneAdmin, the rest of OneProject | each screen listed here once we reach it |

Foundations done so far:

- **The points** above, and the guard registry (`tests/guards/registry.py`,
  `python3 scripts/guards.py`). Every guard now lives in `tests/guards`. The
  twelve older files that were nothing but guards moved there whole, and the
  guards inside feature tests (notifications, the operator console,
  OneStudio's places, record tabs) moved into the file of their point. The
  registry fails on a guard anywhere else.
- **Tiers** (`onedesk/one/tiers.py`): one page of its own (Project), 37
  records with a Record Head, the collections we set up, and our 11 desk
  pages, each with what it is. Projects had its Calendar view taken away; it
  is back, with Image beside it, and no view frappe offers may be taken away.
- **Formats**: every value is written by frappe. Money on the project page
  follows the workspace's Currency Precision (frappe's own default) instead
  of whole units, so a workspace that wants whole units sets Currency
  Precision to 0. Sizes come from one `onedesk.size` (`public/js/size.js`)
  that writes the number through `format_number`, used by OneMail, OneCloud,
  the plan pages and the portal's file picker. OneAI credits go through
  `format_number`. Only the kit may wrap frappe's formatters.
- **The record frame**: the project page has what its form has. frappe's own
  menu items (Print, Email, Show Links, Duplicate, Rename, Reload, Delete,
  Remind Me, Follow, Copy to Clipboard, New Project, Customize) sit under the
  page's, and beside the views are Assigned To, Tags, Shared With, likes, who
  else has it open, and who made and changed it. Each opens frappe's own
  dialog or calls frappe's own method (`public/js/record.js`, kit
  `useRecord`, and since then frappe's own form sidebar), so the next page (Opportunity, Lead, Employee,
  Job Applicant) takes the same two lines.
- **Places on the page**: OneStudio extensions reach the project page
  (`oneproject.project`), and those written for a Project's head run there
  too. Points 6 and 7 are now guarded (`tests/guards/test_frame.py`).
- **The demo company** (`onedesk/one_demo`, its README): Sahara Glass &
  Aluminium, a year of a Dubai glazing contractor, built on a new site in
  twelve steps by the people whose work each record is. The integration
  suite (`one_demo/check.py`) reads it back as them. Building it on a new
  site found these, now fixed:
  - A new site stopped installing. System Settings refused to save, the
    install hooks ran before One's own fields existed, three of One's
    customizations hid fields ERPNext requires, and the names of the mail
    accounts were sent while the site was still being made. The install now
    runs after the fields are synced and does everything a migrate does
    (`tests/guards/test_install.py`).
  - A new workspace could not run payroll until its first migrate. Much of
    what the install sets up is about the company, and the setup wizard
    makes the company afterwards. One's own wizard stage now runs it all
    again once the company exists.
  - Nobody on a workspace could add a bank, so OneBook's own Add Bank
    stopped for everybody. An accounts manager adds one now.
  - A project page did not open for its team once its customer had an
    account of its own (a customer billed in euros, say). ERPNext asks
    whether the reader may open that ledger account just to learn the
    currency. One reads the currency without asking.
  - Invoice Month refused a retainer whose item is counted in whole units
    (a visit, in Nos) when the hours over came to a part of an hour. Hours
    on such an item now go on one line priced in full, the hours in its
    description. Invoice Time does the same.
  - **Reject approved.** The approver an expense claim or a leave
    application names often holds no HR role, and frappe put the verdict
    back for them, since the field is above their level. The record came
    back unanswered, and the submit read that as a yes, so their Reject
    approved it. One's Approve and Reject now carry the verdict through the
    save (`tests/guards/test_decisions.py`).
  - The books' home added what customers owe in dollars as if it were
    dirhams. It is turned into the company's currency now.
  - Storage Check did not run for a workspace administrator.
  - Monthly Attendance broke when run without a month picked, as from a
    scheduled mail.
- **Rules on the server**: a rule of One's lives on its record's hooks, so a
  bulk edit, a report view cell and a Data Import row meet it as the page
  does. Each is checked on the demo all three ways, as the person who would
  make the change (`one_demo/check.py`), and guarded
  (`tests/guards/test_rules.py`). These were decided in the page's own
  methods, and a bulk edit went round them:
  - A project closed with open work, and a project marked Internal kept its
    customer, monthly fee and markup (`one_project/status.py`, `kinds.py`).
  - A project's Budget could be typed over its cost types, and a budget
    submitted or cancelled in the list left the project's figure as it was
    (`one_project/budget.py`).
  - A project contact could name nobody (`one_project/contacts.py`).
  - The books could be locked past today, and closing a year in ERPNext's
    own form did not lock them (`one_book/closing.py`).
  - Turning somebody on in the User list took a seat the plan does not have
    (`one/settings.py`).
  - A folder or a mailbox could be set to read for somebody else, or by
    somebody who may not change it (`one_intake/switches.py`).
  - A featured photo could be made private, a mailbox could have a signature
    it never added, a OneCloud link could share a file its maker cannot
    open, and a file request could go nowhere.
  - A remembered fact could name a record its owner cannot open, and the
    print designer's own format could be turned on.
  - Moving a collection to another app in its form left its rights and its
    place in the rail behind (`one_studio/record_types.py`).
  - Building the checks found the demo left 69 stock revaluations waiting,
    which stops anybody locking the books. The build now finishes them as
    ERPNext's hourly job would.
  - **Still as ERPNext does it**: closing a project with its open work
    closes the tasks without their own hooks, as ERPNext closes them.
- **Notifications in one place**: every notification and mail One sends is
  one file in `onedesk/notifications/`, under the module that sends it, in one
  layout (its README). The header says who it goes to and how it is switched,
  and the subject and message below read as the mail does. The thirteen
  module lists are gone, with every word kept, so translations and each
  workspace's own copy still match. Guarded (`tests/test_notify.py`), and the
  demo checks every file is on Settings › Notifications. Moving them found
  four mails sent with no type and on no page:
  - The Payment Reminder OneBook mails a customer a week after an invoice is
    due. It is listed now, and its Send This and the rule's Enabled box are
    one.
  - Reports by mail, and frappe's own password reset link and sign-in code.
    They are listed as mailed by frappe.
- **Printed**: every record that leaves the company prints from a format we
  ship. The quotation, the sales order, the invoice, the receipt, the
  delivery note, the purchase order, the request for quotation, the payslip,
  the job offer and the appointment letter are each laid out in frappe's
  print format builder (`print_format/` in each module), so a workspace opens
  one there, changes it or copies it. What the builder can't say is One's
  print blocks, frappe's own field templates, in the builder's Library for
  any format (`one/print_blocks.py`): the title in the company's Brand
  Colour, who it is for, its dates, the totals with what is paid and owed and
  the total in the company's currency, when it is due, where to pay, a
  payslip's pay, what a payment settles, and where each side signs. One's
  format is the default unless the workspace chose another. Guarded
  (`tests/guards/test_print.py`), and the demo prints every one as the owner,
  under the company's letter head and in its colour. Found on the way:
  - The demo company had no Brand Colour, contact details or letter head.
    Its owner now sets them on General and Printing, as a new workspace
    does.
  - A workspace administrator's builder showed every field template as
    "Couldn't render", since only whoever set the workspace up could read
    them. Printing grants them to read now.
  - A new site printed One's formats with every block empty. frappe syncs a
    module's print formats but not its field templates, so One now brings
    its blocks in after every install and migrate. The demo check looks for
    what only a block prints, so it can't pass on the letter head alone.
  - **Still open**: a report that leaves the company. The Statement of
    Accounts prints from ERPNext's own template.
- **Hand-offs**: every product's README says what it takes from the others
  and what it hands them, in a Connections section just before Under the
  hood. OneAI has a README of its own now. The demo holds fourteen hand-offs
  to the records they leave, such as an order invoiced and delivered, a
  project's time and costs on it, and a payroll in the books
  (`every_hand_off_left_its_records`). Guarded
  (`tests/guards/test_handoffs.py`). Found on the way:
  - Payroll never reached the books. A salary component had no account, so
    every run made the slips and never submitted them. An earning now books
    to the company's Salary account until the workspace picks another
    (`one_hr/accounts.py`).
  - The demo's employees had no leave or expense approver. Each now has
    their manager.
- **Intake**: `tests/samples/intake` holds 16 real mails and files, one
  folder per app, each with what a model answered about it and what Intake
  must make. The demo reads the owner's mailbox and the accounts team's Bank
  Statements folder, and the suite has each one arrive as it would and checks
  what Intake made (`every_intake_sample_left_what_it_should`). Guarded
  (`tests/guards/test_intake_samples.py`). Running them found:
  - Nobody in One could add a supplier, since ERPNext keeps that for a role
    One never gives. Buying adds suppliers, and so does an accounts manager.
  - A bill from a new supplier made the supplier and never the bill. The
    record made for whoever sent a document is now matched to it, and
    learns the address it came from.
  - An order from a known lead never made the customer, and a signed
    contract never proposed the employee.
  - Every Intake step through an ERPNext mapper failed (a bill from a
    purchase order, a receipt, a credit note, a payment, a customer from a
    lead, an employee from an offer). They read as the person Intake acts
    for now.
  - A placeholder mailbox HRMS makes (jobs@example.com) made example.com one
    of ours, so a CV from such an address was never read as an applicant.
  - A tax number without its country letters was dropped, and an import
    ERPNext had moved stopped the lead conversion.
  - A model call a sample does not answer now fails the sample, even where
    Intake carries on without it. Four samples were missing one (placing an
    attachment with its mail, and the fields an employee from a contract
    still needs).
- **Clean code**: a comment says why in a line or two and a docstring says
  what a file or function is for. Everything longer moved into the module's
  README, under Under the hood, word for word where it could (about 380
  docstrings and 110 comment blocks). Every notification goes out from its
  module's `tell.py`, and every OneAI hook points at a module's `ai.py`.
  Guarded (`tests/guards/test_source_style.py`, `tests/guards/test_layout.py`), and
  a new guard fails on any import of a name frappe, erpnext or hrms no longer
  has (`tests/guards/test_upstream_imports.py`).
  - Every right a role is given is given in a module's `access.py`. The
    workspace administrator's (Printing, Approvals, Reports and nine more)
    moved into one list in `one/access.py`, and Project Template's into
    `one_project/access.py`. Guarded (`test_roles_are_given_in_access`).

**Upstream checkpoints** (docs/UPSTREAM.md). From 2026-10-07 One runs on
recorded frappe, erpnext and hrms commits (`upstream.json`), and moving to newer
ones is a checkpoint: a note of what One leans on that moved and what upstream
shipped, each item closed as Kept, Corrected, Adopted, Not for us or Later with
a task, and a guard that fails while the bench is off the ledger, an item is
open or the checkpoint is over 14 days old. The first, docs/upstream/2026-10-07.md,
moved frappe 1119 commits, erpnext 557 and hrms 88. What it corrected:

- **The rail and the panel**: frappe rewrote its rail (icon-only, pinned) and
  decides the panel on the server. One's sidebar rules moved to
  `shell_for_route`, the map is built again over One's sidebars
  (`outside.placed`). Check In and Intake are rows in the panel's band, under
  Search and Notification, where frappe moved those from the rail.
  The panel header keeps its app's mark beside the name, as well as on the rail.
- **The breadcrumb**: each page draws its own trail. A record on a page
  ("Projects / Mansour Villa ▾"), a list named as its row, a record's crumb to
  its home, the panel menu in the crumb, and the lit row all moved onto it, and
  the browser checks read the trail.
- **Islands** are named by their build entry (assets.json is frappe's registry).
- **A slip** moves Working and Overdue tasks too, as erpnext's does now.
- **Quotes**: Quoted counts the active version of a revised quote.
- **A supplier's quote** goes through erpnext's hardened mapper.
- **The new Kanban**: frappe opens every new board on it, so a fresh Pipeline
  threw. The Pipeline, Projects by Health and a project's task board are on
  it now, each card showing One's fields by icon, and each stage still says
  what it is worth.
- **erpnext's new boards**: erpnext now ships boards for leads, deals by
  status, tasks, issues and more. Its deals-by-status board is taken out
  after every install and update, so the Pipeline by stage is the one deal
  board. Its task board is erpnext's own and One leaves it as shipped.
- **hrms's timesheet**: One's timesheet class now builds on hrms's, and a
  guard fails when a class One puts on a record type drops another app's.
- **Unclaimed leads stay unclaimed**: an update gave a lead without an owner
  to whoever made it. Only deals get their maker as owner now.
- **Time for somebody without an account**: erpnext now checks overlap by the
  sheet's user, and took the one logging it as that user. The workshop's days,
  logged by one person, are checked by employee again (OneTimesheet).
- **A purchase order To Pay** (an advance first) reads "Awaiting payment" on
  the portal.

Up next, in this order:

1. **The foundations** (this arc): the points above, the guard registry, the
   tier registry, formats from frappe, the record frame and places on the
   project page, the demo company and its suite, rules on the server,
   notifications in one place, shipped print formats, hand-offs, Intake
   samples and the code cleanup (all done).
2. **Project templates**, right after:
   - **The page**: Templates in the OneProject rail; a template opens in the
     Tasks table in template mode ("Day 12 · 5 days"), added, renamed, nested,
     linked and marked as milestones in place.
   - **The library**: presets shipped as files and offered under **From the
     library** in New Project and Add from Template, copied into the workspace
     on use. Aluminium & glazing (five phases, 25 tasks, a milestone ending
     each phase), interior fit-out, small building works, architectural design
     stages, website, mobile app, marketing campaign, ERP rollout, office
     move, event, new client onboarding, year-end audit.
   - **OneAI** drafts a template from a description, as a card to approve.
   - Done so far:
     - **The page.** **Templates** is OneProject's fourth place, beside
       Projects, Workload and Time (it left the Projects list's menu). A
       template opens on a page of its own at its own address, the
       onedesk.template island, declared in the tier registry with its
       record frame and a place for extensions
       (`oneproject_template.template`). Its tasks are in the Tasks table in
       template mode: "Day 30 · 25 days", the milestone flag, Waits On with
       + and ×, Hours, and a row menu with Add Task Under, Put Under, Move to
       the Top and Delete. Every change goes through
       `one_project/template_view.py`, saves the task and then the template,
       so ERPNext's own check on a template runs, and whoever has it open
       hears it. A template task can never begin before the project or last
       fewer than no days, however it is saved (`templates.days_kept`).
     - **The library.** Twelve presets in `one_project/library/`, one file
       each. Aluminium & Glazing is the friend's five phases and 25 tasks,
       each phase a milestone, and the demo now copies its template from
       that file instead of building it in code. From the Library is offered
       in New Project, Add from Template and on the Templates list, and the
       first use copies a preset into the workspace, in its language (every
       title and task is in the translations).
     - **OneAI.** **Draft a template** is offered on the Templates list and
       on a template's page, to whoever may make templates. OneAI reads the
       workspace's templates and the library first (`project_templates`) and
       offers one of those before drafting. A draft is a Setup card listing
       its phases, tasks and days (`draft_template`). Approving makes it as
       a preset is made (`library.drafted`), by whoever approved it. Checked
       on the demo (`oneai_drafts_a_template_as_a_card`), and an eval case
       added. The live eval could not run, because the rebuilt demo site is
       not linked to an admin site for OneAI calls.
     - **Checked** on the demo (`a_template_is_laid_out_and_changed_on_its_page`):
       the project manager reads and changes the template, copies a preset,
       starts a project from the library and adds one to a running project,
       and a projects user is refused a change. And in the browser, as the
       project manager.
3. **Demo coverage** (point 1), done:
   - Every whitelisted method of ours and every tool OneAI is given is a
     feature. A guard counts, per module, those no demo check reaches, and
     the count may only fall (`tests/guards/test_coverage.py`, which takes
     the place of the planned point-1 guard). OneAdmin's are left out, as
     they run on the admin site.
   - At the start, 14 of 511 were reached. Then OneTask, OneCalendar,
     OneBook, OneInventory, OneCRM, OneLegal, OneStudio and OneProject were
     reached in full, each read and used as its people use it, with 371
     left.
   - The demo gained two leads from the Get in Touch form with nobody owning
     them, one maybe a lead we have, and a studio step: Company Van, a record
     type of the company's own, with two vans, and two extensions, one on and
     with an error from somebody's browser.
   - The villa gained its window schedule on the Files tab, a photo from site
     in its Featured Media and a request for the next run of profile. Its two
     updates are Rania's and Tariq's, each on its own day; before, both were
     posted today by Samir and one hid the other.
   - Found on the way: extra work lost its name. A sub-project made from a
     quotation called "Staircase balustrade" was called "Glass Balustrade and
     1 more". It now takes the quotation's title (`one_project/billing.py`).
   - Found on the way: the demo's won deal was never won. Its quotation was
     sent and never ordered, so the win rate read 0. It is now ordered
     through Make Sales Order, which wins the deal.
   - The demo gained a calendar step: the weekly site meeting, a handover walk
     with the customer, a supplier visit, a safety briefing and a pricing
     review. Before it the demo had no events at all.
   - Found on the way: Calendar Links switched itself off. frappe reads a
     Single's field nobody saved as 0, so the first save of System Settings
     stored 0 and deleted every link. It is now stored as on at install and
     after every migrate (`one_calendar/feed.py` `settle`).
   - OneIntake and OneAI are now reached in full. 322 are left: One 168,
     OneHR 62, OneStorage 54, OneMail 38.
   - Intake's samples are kept in the demo. Each mail and file is read once
     when the demo is built and what it left stays, so the suite reads the
     demo back instead of reading every sample again. A new sample is a
     taxi receipt the check doubts: the read claims the tip as well, and the
     claim waits with the reason.
   - Layla works through what OneAI read (`oneintake_layla_works_through_what_oneai_read`):
     the inbox, keep, undo, mark, drafts, merging a supplier entered twice,
     the switches, the side panel and the year's bundle. A conversation with
     OneAI, its cards and its settings is checked the same way.
   - Found on the way: bills OneAI drafted had no VAT. ERPNext adds a tax
     template's rows only when Accounts Settings asks it to, and Intake
     named no template. A bill now names the template whose rate matches
     the tax on the document (`one_intake/money.py` `taxed_by`), and
     OneBook › Check has a row that switches ERPNext's setting on.
   - Found on the way: the One home was empty for everybody but the
     administrator. frappe shows a number card only to someone who can read
     its record type, and One's cards named none. Each now names what it
     counts. Guarded (`cards-shown`).
   - Found on the way: the checks were saving to the demo. Keeping a reading,
     submitting drafts and merging save as they go, so a check run changed
     the demo for the next one. Every check now runs inside a rollback.
   - The demo gained a storage step (the Projects library for the crew, a
     shared link, a second version of a drawing, a file request to a
     supplier) and in HR an interview, shift requests, an attendance
     request, an overtime type and an appraisal.
   - Every feature is now reached: all 511, in every module, each read and
     used by a check as its people use it, 69 checks in all. The coverage
     guard holds every module at none left.
   - Found on the way: OneAI's tool for who is on the workspace failed every
     time, since People's rows changed shape (`one/ai.py`
     `workspace_people`), and its tool for the plan failed on the sizes the
     account keeps (`workspace_plan`).
   - Found on the way: a OneAI card that changes a mailbox's signature could
     not be approved by the administrator it was for. Approving it saved the
     mailbox as them; it now goes through the signature's own step
     (`one_ai/proposals.py`).
   - A card that adds a column to a table (a new field, an approval) is read
     by its check, not approved, since a check may not keep a change to a
     table.
   - Found on the way: a workspace administrator could not make a connected
     mailbox the one the workspace sends from, nor put the workspace's own
     address back. frappe takes the default off the old mailbox by saving it
     as the person, who may not write mailboxes. One now does that step
     itself (`one_mail/holders.py`).
   - Found on the way: Samir could share his own file and not take Rania off
     it again. The removal passed frappe the wrong switch and frappe asked for
     its own Share right (`one_storage/share.py`).
   - Found on the way: somebody named to hold an interview could not open it
     unless they were in HR. hrms opens interviews to its Interviewer role,
     and no app of One's gives it. Everybody named on an interview now gets
     that role when it is saved (`one_hr/hiring.py`).
   - Found on the way: setting the signature of an address that only receives
     said "Only a Workspace Administrator can change the signature", to a
     Workspace Administrator. It now says the address only receives.
   - Found on the way: the demo marked Yousef present on the day he asked off
     sick, and hrms then refuses any answer to that leave, Yes or No. The demo
     no longer marks a day somebody asked off.
   - The checks now clear frappe's cache after each one, since a rolled-back
     change could stay cached and reach the next check.
   - Key screens are opened in a browser as their people
     (`tests/browser/`, run against the demo). Every desk page of ours is on
     the list. Guarded (`screens-opened`).
   - The demo gained a mail step. The workspace's own address was made the
     first time somebody opened OneMail, so a new demo had none, and the
     first mailbox Layla saw was empty. It is now made with the demo, with a
     customer's request for a price, a supplier's delivery date and a
     hotel's maintenance call in it.
   - Found on the way: mail at One's own addresses never showed how much was
     unread. Only a connected server's sync counted a folder, so the
     workspace's Inbox and everybody's own showed no count. A message that
     arrives now counts its folder (`one_mail/inbound.py`).
   - Tests that read the code to claim what it does are becoming checks on the
     demo, module by module. OneProject first: who sees a project, what a
     member added or taken off gets, a slip moving what waits on it in a
     sub-project, and what a template hands on.
   - Found on the way: a project manager could not give a project a task
     prefix. The prefix is a naming rule, and Numbering's check on every
     naming rule asked for an administrator. Who may save a rule is now asked
     where it is saved: Numbering asks for an administrator, the project for
     whoever may change it (`one/numbering.py`).
   - Then the money: no margin to come without a price, the margin so far as
     earned less spent, extra work as the sub-project's own order, a
     progress bill at the order's prices with advances set off, a retainer's
     month billing its time, and who is told when a budget, an allowance, a
     task's plan or the project itself runs out. A budget changed is a
     revision of the old one, and a projects user may not set one.
   - Found on the way: time logged after a submitted timesheet overlapped
     it. A new entry starts after the last one that day, but One only looked
     at the week's draft, so time logged on a day after its timesheet was
     sent started at nine again and ERPNext refused it. It now starts after
     the last entry on any of the person's timesheets (`one_project/hours.py`).
   - Then the rest of OneProject and OneTask: a team asked for its update, a
     retainer's month to invoice, OneAI reading only a project its reader may
     open, the villa's customer on the portal reading the villa and nothing
     of the team's, a day on the tower's site becoming a day on the tower,
     the Cover handed on when its photo goes, who reads which task, a to-do
     about nothing becoming a task, and who hears a task done.
   - Found on the way: only the books could make a task repeat. Repeat on a
     task is frappe's Auto Repeat, which frappe gives only to the accounts
     roles, so a project manager pressing it was refused, and the task panel
     could not say how a task repeats to anybody else. Every desk user may
     now keep repeats of their own (frappe still asks that they may change
     what repeats), the panel reads it through the task, and whoever may
     change the task may stop it (`one_task/access.py`, `one_task/task.py`).
   - Found on the way: a repeat of a task already done was given to nobody.
     Doing a task closes its to-dos and empties its list of people, and the
     repeat copied the empty list. It now goes to whoever did it.
   - Found on the way: a task done could not be opened by its project's
     people. Its list of people was then empty text, which the check on who
     may read a task could not read (`one_task/access.py`).
   - OneCloud's rules on the demo: a private stored file not there at all for
     a stranger, what was shared copied out but not taken, sharing only with
     the team and never a record's own file, a library kept with an owner,
     a server its maker's until an administrator shares it and its password
     never sent, searching finding only what may be opened, a closed request
     refusing more, and an upload ticket used once and only by its asker.
   - Privacy's rules on the demo: only administrators read the requests, a
     wrong password refused, the payer kept, everybody concerned told, what
     a copy may withhold and why, the copy kept on the account and gone with
     it, approving signing the person out, frappe's erasure run for a user
     and its redaction for somebody who is not one, and the public page
     answering the same whatever the address.
   - OneMail's on the demo: a mailbox read only by those who hold it, two
     mails with one subject kept apart and a reply joining the one it
     answers, and a delivery report stopping mail to an address gone for
     good but not to one only late.
   - Found on the way: a person could be given a second address of their
     own. Their address is set once, as their page says, but the
     administrator's way of giving one did not ask whether they had one
     already (`one_mail/addresses.py`).
   - OneStudio's and OneAI's memory on the demo: the other administrators
     told when an extension is turned on, off or deleted, the same fact
     remembered once and a changed one replacing it, a memory tied to a
     record only when it names it, and past chats only the reader's own. And
     access: a level kept to its app's kinds, record access to its own.
   - Then closing the workspace (the payer alone, everybody told, the
     download built whole), OneBook's rules (a bank mode wired when added,
     only invoices and bills paid in one step, a repeated bill without last
     month's number, the books locked only up to today and by the closers,
     a year closed into Retained Earnings and locked), the portal invitation
     (never to somebody in the workspace, only by the party's manager, a
     taken login's link dead) and saved reports (no code, a report by mail as
     whoever set it up, Show In kept to the reader's apps).
   - Found on the way: whoever saved a report could not change or delete it.
     One lets everybody save one, but frappe gives a desk user no right to
     change or delete a report. Now they may, their own only
     (`one/access.py`).
   - Then the bin (each person's own, the administrator's of the kinds they
     read, nothing the system deleted) and OneAI's setup cards (nothing made
     until approved, a level card sent back when nothing would change and
     refused once the level has changed, a report by mail as its approver,
     an administrator's card refused to anybody else).
   - Found on the way: an administrator could not change a plain User level
     the first time. Its role is then given to the app's plain users, by
     saving their User record as the administrator, which frappe refuses
     (`one/access.py`).
   - Found on the way: a deleted meeting, note or to-do was not in the bin.
     The bin left out all of frappe's Desk module, where they live. They are
     in it now (`one/recycle.py`).
   - Found on the way: a record put back from the bin came back under a new
     ID when frappe names its kind at random, so what linked to it no longer
     found it. It now comes back under its own where that is free.
   - Then webhooks (over https to a public address, every record, fields
     alone and none the administrator may not read, a short wait and a few
     tries, the administrators told when calls give up), the audit log (the
     administrator's only, read only, without the system's changes or the
     fields its reader may not read), Intake filling only the record it is
     making, and every sidebar a person is sent being One's own.
   - Then announcements (an administrator's alone, everybody told once,
     waiting on sign-in), a letter asked for about somebody else refused, and
     a row of What to Order off the list once it is on a draft order.
   - Found on the way: What to Order could not order a request made for a
     project. The order line did not carry the request's project, and
     ERPNext refuses an order whose project differs from its request's
     (`one_inventory/order.py`).
   - Then a print format OneAI lays out from sections a model wrote loosely
     (Python's words, a table named before its columns, widths in per cent,
     a sentence after), printing in the font, page number and look asked
     for, and a restyle keeping its layout.
   - Where it stands: 88 checks on the demo, all passing, and 21 screens
     opened in a browser as their people, all as they should be. The tests
     that still read the code read wiring (hooks, fixtures, sidebars), the
     screens' own JavaScript, OneAdmin's side, which runs on the admin site,
     or what a model is told. Each claim about what One does is now made on
     the demo.
4. The finished modules again, against the new points only, one screen at a
   time.

Noticed along the way, for the screen it belongs to:

- **OneAI**: a card says Approve and Refuse, and the same proposal's own
  page says Apply and Refuse.
- **OneIntake**: once, while the demo was built, attaching a file to a
  record was refused with "You do not have permission to access this file".
  It did not happen again.
- **OneHR**: hrms refuses any answer to a leave application over a day
  already marked present, so HR cannot say No to it either. The person sees
  hrms's message about attendance.
- **The demo company** sends no mail. It has no outgoing mailbox, so every
  notification a person chose to have by mail lands in the Error Log as
  "Failed to send notification email".
- **Workspace › Mail**: every workspace carries the Jobs mailbox HRMS makes
  on install (jobs@example.com). It reads and sends nothing, so Intake no
  longer counts it, but it still sits in the list.

- **Sign-in**: says "288 sessions" for the administrator. That counts every
  session ever left open, not the devices a person uses.
- **Access**, found building the demo and settled in ARC 7 as rules on the
  records themselves, so they hold however a person or a role is changed.
  - A manager of any app, or an administrator, is no longer kept to their
    own employee's records (`one_hr/everybody.py`). hrms keeps every
    employee to their own, which stopped a project manager approving the
    crew's time and the books seeing the timesheets they invoice.
  - A project manager sets a project's budget by cost type. A budget against
    a cost centre stays the books' (`one_project/budget.py`).
  - The books read every project, since they invoice its time and progress
    (`one_project/members.py`).
  - A manager may share, so assigning somebody a record they cannot open
    works (`one/roles.py`, `MANAGE`).
  - **Still open**: no app of One's offers manufacturing (bills of materials,
    work orders), so nobody but whoever set the workspace up can make them.
    Whether OneInventory takes them on is a product decision.

## Settings

Every settings screen, from the first commit of the pass:

- The sections are entries in One's own sidebar, so there is no second sidebar
  inside the page.
- No bordered card. Parts of a section are divided by a rule.
- Save is the page's primary action in the head, so Ctrl+S works. "Not Saved"
  shows once something changes. A section with nothing to save puts its one
  action there instead (Mail's Connect a Mailbox), never as a button in the
  page.
- The breadcrumb names the section.
- A section is a column in the middle of the page, the form's width, so a wide
  screen leaves room on both sides rather than all of it on the right. A
  section that is a table (People) gets the width a table needs.

### Profile

1. **Notifications**: nothing is sent when a person changes their own details.
   The employee record keeps the change in its history, where HR sees it.
   Whether HR should also be told about a new address or emergency contact is
   open.
2. **OneAI**:
   - Before, the panel knew nothing on any Settings page. `oneai.where()` only
     recognised records, lists and reports, so it offered nothing and told the
     model nothing.
   - Now a desk page tells the panel the page and the open section, and the
     panel follows the reader between sections.
   - On Profile the model is told that it is the reader's own User record and,
     when they have one, their own Employee record. It is told what they may
     change and that job and bank are HR's.
   - Two suggestions:
     - **What is missing from my profile?** reads both records.
     - **How do I fill this in?** answers from the README.
   - Letting OneAI make a change itself ("I moved, update my address") is not
     offered. `edit_record` would need write permission on Employee, which the
     Employee role does not have.
3. **Intake**: nothing yet. Later, a proof of address that Intake reads could
   offer to update the address here.
4. **Permissions**:
   - "About You" said only HR sees marital status and blood group. The person
     sees them too, so it now says "Only you and HR see these".
   - A person changes their own login, and only the Profile fields.
   - On their employee record they may change how to reach them, the emergency
     contact, marital status and blood group. That record is only ever the one
     whose `user_id` is theirs.
   - Their job and their bank account are shown but never written, and the
     account shows only its last four characters.
   - `tests/test_settings.py` holds this.
5. **Cross-module**: gender, birth date, mobile and photo are on both the login
   and the employee. erpnext copies the employee's values onto the login every
   time the employee is saved. So those four are written to the employee as
   well, or HR's next save would undo the person's change. A department shows
   by its name, without the company's abbreviation.
6. **UI**: a Page of our own (`one/page/settings`), drawn by
   `public/js/settings.js`. It is not frappe's User form with CSS laid over
   it. The fields are frappe's controls in a `FieldGroup`, so they behave as on
   any form.
   - It follows "Everything follows frappe" the way a desk form does, from
     `form.js` and `model.js`:
     - Dirty is a difference from what was loaded, so undoing a change makes it
       clean again.
     - Leaving with changes gets frappe's own warning. Like frappe, it is off
       in developer mode.
     - Switching sections keeps unsaved changes, as frappe keeps an unsaved
       document in `locals`.
     - Save sends each record's `modified`, and frappe's `check_if_latest`
       refuses a stale save with its own message. The page then offers
       Refresh.
     - That warning is frappe-ui's row alert, from `Alert.vue`: the title
       and one action on one line, the action a ghost button in the alert's
       amber. Neither button library has an amber button (espresso: gray and
       red; frappe-ui: gray, blue, green and red). The colour belongs to the
       alert.
     - Both records' realtime rooms are subscribed. Untouched, the page reloads
       when somebody else saves. With changes in it, it says "This form has
       been modified after you have loaded it" and keeps them.
     - Ctrl+S saves. On a page that is `save_action`, not the button, which is
       why it did nothing before.
     - Every field is sent. `FieldGroup.get_values` leaves an empty field out,
       so a field somebody cleared was never cleared.
   - The photo is the avatar, at 80px. Espresso's largest size is 3xl, which
     is 46px, so the page sets the avatar's own size variable instead of
     drawing its own.
   - Clicking the photo opens frappe's upload dialog: My Device, Link, Camera
     and OneCloud.
   - Fields sit side by side, as on a record.
   - A person who is an employee also sees:
     - At Work (read-only)
     - Where You Live
     - In an Emergency
     - About You
     - Where Your Pay Goes (read-only)
7. **Documented**:
   - One had no README, so OneAI could not answer any question about Settings.
   - `one/README.md` now has Finding your way, Settings (how saving works, and
     what happens when somebody else changes the same thing), Settings ›
     Profile, and Asking OneAI.
   - Each Settings screen adds its own section as the pass reaches it.
   - Checked on the site: "how do I change my bank account", "how do I change
     my photo" and "who sees my blood group" each find One › Settings ›
     Profile first.
8. **Legal**: added when OneLegal was founded, after Profile was otherwise
   done.
   - Privacy Policy, `profile-employee`: what the profile holds, what the
     employee record adds, and who sees which.
   - Data Processing Addendum, `profile-special`: a blood group is a special
     category of personal data, and an emergency contact is personal data
     about somebody who is not a user. The organisation decides whether to
     collect them and needs a lawful basis to.

#### Profile, second pass

Against what the pass learned since: the OneAI tag and button, one action in
the page head, product names, and UX. All of it done, on your word.

1. **Notifications**: the question left open is worth a yes. HR relies on an
   emergency contact and an address being right, and learns of a change only
   by opening the record. Recommended: one notice to HR when a person
   changes their addresses or emergency contact, saying what changed.
2. **OneAI**: the panel offers its two suggestions, but nothing on the page
   says OneAI can help. Recommended: a OneAI button under the name, **Check
   My Profile**, asking the existing "What is missing?" question; and one
   under Bio, **Write It With OneAI**, as records have on a prose field.
3. **Intake**: still nothing; a proof of address offering to update the
   address stays a later idea.
4. **Permissions**: hold as the first pass left them.
5. **Cross-module**: nothing new.
6. **UI and UX**:
   - An emergency contact can be half filled: this one has a relation
     (Sister) and no name or phone, and saves without a word. Recommended:
     once any of the three is filled, a name and a phone are asked for.
   - The photo's placeholder shows "S" where the rail shows "SA".
     Recommended: both initials, as frappe's own avatar gives them.
   - "Mobile No" is frappe's label. Recommended: "Mobile".
   - Save is in the head, the page's one action. Nothing to change.
7. **Documented**: the Profile section of `one/README.md` gains whatever of
   the above is done.
8. **Legal**: nothing new.
9. **Built from frappe**: nothing new.

Done:

- **Employee Details Changed** (`one_hr/notifications.py`): HR Managers are
  told, once per save, when a person changes their current or permanent
  address or their emergency contact, with what changed ("current address
  and emergency contact"). Not the person themselves, and not the bench's
  own account.
- **An emergency contact is whole or empty**: once a name, relation or phone
  is filled, a name and a phone are required, on the server.
- **Check My Profile** under the name and **Write It With OneAI** under Bio,
  both OneAI buttons; the second is a new suggestion, Write My Bio, which
  comes back as an edit card to approve.
- **Both initials** in the photo's placeholder, as the rail says them.
- **Mobile**, not "Mobile No".
- `one/README.md`'s Profile section says all of it.

### Mail

Lists the reader's mailboxes (`holders.mailboxes`): the workspace's, their
own address on the mail domain, and any they connected. Each opens in
OneMail; one that sends has a Signature button (frappe's Text Editor in a
Dialog, `holders.set_signature`). Connect a Mailbox goes to OneMail.

Findings, and what was done about each (all of them, on your word; the
list stays a list, since three rows with actions read better than cards).

1. **Notifications**: a mailbox that stops being reachable says nothing to
   anybody. `sync.py` writes `one_error` and stops; the only sign is a red
   badge here and in OneMail. Recommended: one notice to its holders when it
   breaks, through the hub, with a way to reconnect, and none on every
   failed sync after that.
2. **OneAI**: the panel knows the section (`page:settings/mail`) and has no
   suggestion for it. Recommended: "Write my signature", from the profile
   (name, designation, phone, company), into the same dialog to check
   before saving.
3. **Intake**: nothing to add. The badge says which mailbox Intake reads;
   choosing one is Workspace › Intake.
4. **Permissions**: anybody who holds the workspace's mailbox can change the
   signature everybody sends under. By design (`set_signature`), but worth a
   decision: keep it, or keep a shared mailbox's signature to Workspace
   Administrators.
5. **Cross-module**: OneMail owns the mailboxes; this reads them and opens
   them there. Nothing to add.
6. **Bespoke UI and UX**:
   - What you sign with is behind a button. Recommended: the signature's
     first line on the row, or "No signature".
   - A personal address on the mail domain receives only, so it has no
     Signature button and nothing says why. Recommended: "Receives only".
   - A mailbox that is not reachable shows a red badge whose reason is in a
     hover title. Recommended: the reason on the row, and Reconnect.
   - The list does not change when a mailbox breaks or recovers until the
     page is opened again. Recommended: redraw on the sync's realtime event.
7. **Documented**: `one/README.md` has no Mail section, so OneAI cannot
   answer "how do I change my signature". Recommended: write it.
8. **Legal**: `one_mail/legal.py` already declares connected mailboxes
   (`onemail-mailboxes`) and the mail carrier. Nothing to add.
9. **Built from frappe**: the dialog is frappe's, the rows and buttons are
   the settings shell's (espresso buttons and badges). Nothing to change.

Done:

- **Mailbox Not Reachable** (`one_mail/notifications.py`): when a sync first
  fails, everybody who holds the mailbox is told, on the bell and by email,
  with the reason and a link here. Only the first failure sends, so a
  mailbox that stays broken is one notice.
- **Reconnect** on a mailbox that is not connecting: its password again
  (`connect.reconnect`), tried on the servers it already has before it is
  kept, then read at once. A holder may; a workspace mailbox, an
  administrator.
- **Each row says what it signs with** ("Signs with …" or "No signature"),
  **Receives Only** on a personal address on the mail domain, and a mailbox
  that is not connecting says why on the row, in red, beside Reconnect.
- **The page redraws** when a mailbox breaks or comes back (`one_mailbox`,
  published by `sync.py` to its holders).
- **A workspace mailbox is signed by its administrators** (`holders.may_sign`),
  held on the server in `set_signature` and in OneMail's own menu.
- **Connect a Mailbox is the page's primary action**, in the head.
- **OneAI**: Write My Signature (`my_mailboxes` reads the mailboxes and what
  a signature is made of, `sign_mailbox` suggests one as a card, a new
  proposal kind `Signature` that Approve saves), Why Is a Mailbox Not
  Working, and How Does Mail Work Here, which reads the new Settings › Mail
  section of `one/README.md`.

### Calendar

The page is one section: the calendar link as a raw `webcal://` address in a
code box, Copy, Make a New Link and Turn the Link Off. Nothing is changed yet.

1. **Notifications**: nothing is sent, and nothing needs to be. The link is
   the person's own, made by them.
2. **OneAI**: the page has no suggestions and no page sentence, and the panel
   cannot answer "how do I get this on my phone?". Recommended: a OneAI button,
   **How Do I Add It?**, answering from the README for Google, Apple and
   Outlook.
3. **Intake**: nothing here.
4. **Permissions**: hold. The secret is stored encrypted and found by its
   hash, the feed is rate-limited per link, a disabled person's link stops,
   and it carries only what that person can see. Administrators switch
   anybody's link off under OneCalendar › Calendar Links.
5. **Cross-module**: OneCalendar's own **Subscribe** dialog already does this
   better: a button per app with its mark (Google Calendar, Apple Calendar,
   Outlook) that opens the app ready to add it, and Copy Link. The two
   disagree: different words ("New Link" and "Switch Off" there, "Make a New
   Link" and "Turn the Link Off" here), and Copy copies the `https://` link
   there and the `webcal://` one here. Recommended: one drawing of the link,
   used by both.
6. **UI and UX**:
   - A raw address nobody reads fills the page. Recommended: the three app
     buttons, as in Subscribe, with Copy Link for anything else.
   - Nothing says whether the link works. The feed records when an app last
     read it (`last_read`). Recommended: "Read by a calendar app 2 hours ago",
     or "No app has read it yet".
   - Nothing says what the link carries. Recommended: the layers it carries,
     named ("Your events, your tasks, holidays…").
   - No action in the page head, and with no link, **Make My Link** is a dark
     button in the page. Recommended: **Make My Link** in the head when there
     is none, **Copy Link** when there is; New Link and Switch Off stay quiet
     in the page.
   - For both ways with Google, frappe's own Google Calendar sync exists
     once an administrator has set Google up. Recommended: a row saying so,
     shown only when Google Settings is on, opening the person's own Google
     Calendar record.
7. **Documented**: Settings has no Calendar section in `one/README.md`.
   Recommended: one, pointing at OneCalendar's README for the rest.
8. **Legal**: the privacy notice does not say a person can publish their
   own calendar to another app through a private link, readable by whoever
   holds it. Recommended: a clause in OneCalendar's `legal.py` (which does
   not exist yet); a new processing purpose, so a new revision.
9. **Built from frappe**: the code box is ours. The app buttons are
   espresso's, as Subscribe draws them; frappe's `copy_to_clipboard` and
   `confirm` are used as they are.

Your word: all of them but the Google sync row (5), which leans on frappe's
own Google integration.

Done:

- **One drawing of the link** (`public/js/calendar_link.js`), used by
  Settings and by OneCalendar's Subscribe: the three app buttons with their
  marks, what it carries as badges, whether an app has read it, and New Link
  and Switch Off as quiet buttons, both asking first. Copy Link copies the
  `https://` address everywhere.
- **The page head's action** is Make My Link with no link, Copy Link with
  one; Settings leaves the in-page Copy Link out.
- `feed.mine` and `feed.renew` also return `carries` and `last_read`;
  `feed.current` reads the link without making one.
- **OneAI**: How Do I Add It? on the page and as its suggestion, and the
  panel is told what the page is.
- `one/README.md` gains Settings › Calendar.
- **Legal**: `one_calendar/legal.py` says a person may publish their
  calendar through a private link; the privacy notice is revision 3.

Then, on your word: **Calendar Links** under Workspace › General (a switch
on System Settings). Off, every link is deleted at once (`feed.switched`),
the feed refuses any link, Settings says the workspace does not allow them,
OneCalendar has no Subscribe, and OneAI says so. On again, nobody's old link
comes back. Found on the way and fixed:

- Opening your own calendar link while signed in signed you out: the feed's
  `frappe.set_user` rewrote the request's session, sid and all. It now reads
  as the link's owner and gives the request its own session back (`feed._as`).
- General could not be saved: System Settings' Time Zone arrived with no
  options, so it showed blank and saved blank (`settings._zones`).

### Sign-in

Three sections: Change Password (a dialog), the passkey for checking in with
a dark Register This Device, and "475 sessions, this one included" with Sign
Out Everywhere Else. Nothing is changed yet.

1. **Notifications**: changing the password here tells nobody. Frappe mails
   "Security Alert: Your password has been changed" only when a password is
   set on the User form, and straight through `frappe.sendmail`, outside the
   hub. Registering a passkey tells nobody either. Recommended: two kinds
   through the hub, **Password Changed** and **Passkey Added**, mailed to the
   person always (a security notice cannot be switched off), each saying
   when, from which device, and what to do if it was not them.
2. **OneAI**: no suggestions, no page sentence. Recommended: **Is My Account
   Safe?**, reading this page's facts (password age, passkey, how many places
   you are signed in, two-factor) and saying what to do.
3. **Intake**: nothing here.
4. **Permissions**: hold. Each action is the reader's own; Sign Out
   Everywhere Else keeps this session.
5. **Cross-module**: the passkey is OneHR's, for checking in, but when the
   workspace allows Login with Passkey (System Settings) the same passkey
   signs you in, and the page does not say so. Two-factor sign-in, where the
   workspace requires it, is not mentioned either. Recommended: the passkey
   section says what it is used for here (checking in, and signing in when
   allowed), and a line says whether two-factor is on for you.
6. **UI and UX**:
   - "475 sessions" is a number nobody can act on, and most are old. Frappe
     keeps each session's device (user agent), network address and last
     activity. Recommended: a list of where you are signed in, as "Chrome on
     Mac · 2 hours ago", this one marked, each with Sign Out, and Sign Out
     Everywhere Else kept for all of them.
   - Change Password does not offer to sign out elsewhere, which is what a
     person changing a leaked password wants. Recommended: a switch in the
     dialog, on by default.
   - Register This Device is a dark button in the page. Recommended: quiet;
     this page has nothing to save, so its head has no action.
7. **Documented**: no Sign-in section in `one/README.md`. Recommended: one.
8. **Legal**: holds. The privacy notice already covers sign-in records with
   time and network address, and passkeys.
9. **Built from frappe**: the password dialog is frappe's, with its Password
   controls and strength check. Signing out one session is frappe's
   `delete_session`.

Your word: all of them, reading what frappe already keeps rather than
keeping anything new.

Done (`one/signin.py`):

- **Where You Are Signed In** reads `tabSessions`: each session's user agent
  as "Chrome on Mac", its network address and when it was last used, this
  one marked, each with Sign Out (frappe's `delete_session`, so the Activity
  Log records it). The page names a session by a hash, never its id.
- **Recent Sign-ins** are the Activity Log's last six, failed ones in red.
- **Password** says when it last changed (User's
  `last_password_reset_date`); **Two-Factor Sign-in** says whether frappe asks
  this person for a code, and that the workspace decides it.
- **Passkey** says it also signs you in where Login with Passkey is on.
- **Change Password** has Sign Out Everywhere Else, on by default.
- **Password Changed** and **Passkey Added** go through the hub, always
  mailed. Frappe's `update_password` is overridden to tell the person after
  it, so the reset link tells them too.
- **OneAI**: Is My Account Safe? on the page and as its suggestion, read by
  `my_sign_in`.
- `one/README.md` gains Settings › Sign-in.

### What OneAI Remembers

One section: the facts OneAI keeps for this person (`AI Memory`, private to
them), each with Forget, or a large centred "Nothing yet." Nothing is
changed yet.

1. **Notifications**: nothing is sent, and nothing needs to be.
2. **OneAI**: the panel links here ("What OneAI remembers"), but the page
   has no OneAI part, and OneAI keeps a memory quietly: nothing in the
   conversation says it did. Recommended: when OneAI keeps something, one
   quiet line in the conversation, "Remembered", with Undo; and a OneAI
   button here, **What Do You Know About Me?**, that says what it keeps and
   what the workspace told it.
3. **Intake**: nothing here.
4. **Permissions**: hold. A memory is its owner's only (`if_owner`), and
   Forget checks delete permission.
5. **Cross-module**: a memory about a record names the record as plain text.
   Recommended: a link that opens it. And OneAI also uses what the
   workspace's administrators wrote for everybody (`AI Knowledge`), which a
   person cannot see anywhere. Recommended: a second section, read-only,
   **What Your Workspace Told OneAI**, listing those by title.
6. **UI and UX**:
   - A person can only add a memory by asking OneAI. Recommended: **Add a
     Memory** in the page head, a dialog with the fact and an optional
     record, frappe's own controls.
   - A memory cannot be corrected, only forgotten. Recommended: Edit beside
     Forget, the same dialog.
   - Nothing says when each was kept. Recommended: "kept 3 days ago" under
     each.
   - With many, there is no way to clear them. Recommended: **Forget
     Everything**, quiet, asking first.
   - The empty state is large and centred, unlike every other section.
     Recommended: one quiet line, as the other sections say it.
7. **Documented**: no section in `one/README.md`. Recommended: one.
8. **Legal**: holds. The AI Addendum already says what OneAI remembers is
   listed in the person's settings and can be deleted.
9. **Built from frappe**: the list is ours; the dialog would be frappe's
   (Small Text, Link, Dynamic Link).

Your word: all of them.

Done:

- When OneAI keeps or updates a memory, the conversation shows one quiet line,
  "Remembered: …", with Undo (`one_ai/chat.py` `_remembered`, `Panel.vue`).
  Undo forgets it and the line says "Forgotten".
- **What Do You Know About Me?** on the page and as its suggestion, read by
  `my_memories`: what it keeps and what the workspace told it.
- A memory about a record links to it. **From Your Workspace** lists the
  enabled `AI Knowledge` by title, read-only.
- **Add a Memory** in the page head, and Edit beside Forget: one frappe dialog
  (Small Text, Link DocType, Dynamic Link). A record the person cannot read is
  refused. "kept 3 days ago" under each; **Forget Everything** when there is
  more than one, asking first. The empty state is one quiet line.
- The page redraws through `frappe.realtime` (`one_memory`, sent by the
  `AI Memory` controller) when a memory changes in the panel or another tab.
- Your word after seeing it with many: too cluttered. Both lists are now
  frappe's `EmbeddedList` (the table DocType Settings uses): one line each
  with Memory, About and Kept, a row opens the Edit dialog, the bin shows on
  the row under the pointer, and Search appears past five.
- `one/README.md` gains Settings › What OneAI Remembers.

### Agreements

Built during the pass, right after OneLegal, so a person can see what they
agreed to. The Terms already promise that.

1. **Notifications**: nothing is sent. A new revision is asked for at the next
   sign-in. Whether administrators should also be told by mail when their
   organisation's agreements change is open.
2. **OneAI**:
   - A new read tool, `agreement`, returns a document's actual text, so OneAI
     answers from what was agreed, not from what such documents usually say.
     It sits in `one_legal/ai.py` and is registered in `one_ai_reads`.
   - The panel is told the reader is on Agreements.
   - It offers **What have I agreed to?** and **Who else sees my data?**, both
     expecting the tool.
3. **Intake**: nothing here.
4. **Permissions**:
   - Everybody sees their own acceptances, and the organisation's with who
     agreed and when, since they are bound by them.
   - Only administrators get **Everybody's Agreements**, the Legal Acceptance
     list, whose doctype only they may read.
5. **Cross-module**:
   - The section reads the rows OneLegal's gate writes, not a copy.
   - **Agree Now** opens the same dialog as sign-in. Agreeing there redraws
     the section (`legal-agreed`).
6. **UI**:
   - Three parts: Yours, Your Organisation's, Published.
   - Each document has a badge (Agreed, Not agreed yet, Updated since) and
     when, or by whom and when.
   - A changed document links to the exact text that was agreed.
   - It is read-only, so there is no form and no Save.
7. **Documented**: One's README has Settings › Agreements, and a test holds
   that a section OneAI offers anything on has its README section.
8. **Legal**: no new lines. The Terms' "every version anybody agreed to is kept
   and can be read in One" is now true of a screen.

### Notifications

Stage 3 of `docs/NOTIFICATIONS.md`. What was here were frappe's older
per-kind checkboxes (Mentions, Assignments, Document Share), which v17 hides
because they no longer decide anything: frappe mails a person the types in
their `email_notification_types`, and nothing on this screen wrote that.

1. **Notifications**: this screen is each person's half of the hub. Every kind
   reaches the bell; a tick per kind says whether it is also mailed, and it
   writes frappe's own `email_notification_types`, so frappe's mailing honours
   it with nothing of ours in between. Saving sends nothing.
2. **OneAI**:
   - A read tool, `my_notifications`, returns the kinds the reader can receive
     and which they get by email. It reads their own settings only.
   - The panel is told the reader is on their own Notifications.
   - It offers **What will I be told about?** and **Too many emails?**. Both
     advise; the person ticks and saves.
3. **Intake**: six kinds are Intake's (waiting, the weekly digest, a new IBAN,
   phishing and two more), chosen here like any other.
4. **Permissions**:
   - A person's own Notification Settings, and only theirs.
   - A kind declared for some roles (`roles` in a module's
     `notifications.py`) is shown only to people holding one: HR's kinds are
     for HR. A kind not shown is left as it was on save.
   - A kind the workspace does not mail is shown and cannot be ticked, with the
     reason. The project update, whose mail is always sent so people can
     reply, is shown ticked and fixed.
5. **Cross-module**: every module's kinds in one list, grouped by app, with
   frappe's own (mentions, assignments, shares) as Across One. Energy points
   left frappe with gamification, and frappe's Alert never mails, so neither is
   listed. Workspace › Notifications shows the always-mailed kind as Always
   Mailed.
6. **UI**:
   - Notifications and Also by Email first, then a part per app with a tick per
     kind and a sentence on when it is sent, then Other Mail (event reminders,
     mails on a record assigned to you).
   - Turning either switch off hides the ticks it makes meaningless.
   - Found doing it: frappe marks a section empty while a FieldGroup draws it,
     before its values are in, and never looks again, so a section whose
     fields have `depends_on` stayed hidden. `form()` now re-checks sections
     once the values are in and on every change, for every Settings section.
   - `form()` gains `{ stack }`, fields one under another in one part, so a
     list of ticks is not a section each.
7. **Documented**: One's README has Settings › Notifications.
8. **Legal**: the Privacy Policy gains `notifications`: the bell keeps a record
   of every notification, mail per kind is the person's choice within what the
   workspace allows, and the workspace's administrators decide what each says.
   Recorded as a clarification (new hash): the records existed and the policy
   already covered what the workspace holds. Frappe keeps notification records
   until a workspace clears them, so no period is promised.

#### Notifications, second pass

Against what the pass learned since. Nothing is changed yet.

1. **Notifications**: two kinds come in pairs that are one event said two
   ways: Intake Waiting and Intake Waiting, One Thing; Arrived Through a
   Link and its One File. Each has its own ticks, so a person who ticks one
   and not the other gets mail for some of the same event and not the rest.
   Recommended: one row per pair, and its ticks set both.
2. **OneAI**: the panel offers its two suggestions, and nothing on the page
   says so. Recommended: a OneAI button at the top, **Too Many Emails?**,
   asking the existing question; and the kinds OneAI itself sends (Intake's)
   carry the OneAI tag, since what OneAI does is drawn one way.
3. **Intake**: covered by 1 and 2.
4. **Permissions**: hold.
5. **Cross-module**: nothing new.
6. **UI and UX**:
   - The two switches say what happens when they are off, beside a ticked
     box: "Notifications ✓ — Off, nothing reaches your bell". Recommended:
     say what the tick does ("Everything One tells you reaches your bell"),
     and what unticking stops.
   - Turn On Push is a dark button in the page, a second primary beside
     Save in the head. Recommended: a quiet one; Save stays the page's one
     primary action.
7. **Documented**: Settings › Notifications in `one/README.md` gains what
   is done.
8. **Legal**: nothing new.
9. **Built from frappe**: nothing new.

Your word: all of them, and two more. The ticks made the page cluttered: use
a toggle. And the kinds' sentences had no one way of speaking ("The same,
when only one thing needs you.").

Done:

- **Switches, in columns.** Every tick is frappe's own `Switch` control. Each
  app's heading names the two columns, Email and Push, and each kind is one
  line: its name and sentence on the left, its two switches on the right. A
  switch the workspace decides is dimmed and shows how it stands (frappe
  draws a read-only switch with no input, so an always-mailed kind looked
  off).
- **One way of saying a kind** (`docs/WORDING.md`): every sentence starts
  with when it is sent, from the reader's side, and who it goes to is a
  separate `to`, shown on the workspace's page under the sentence and never
  on a person's own. All fifty-seven declared kinds and frappe's three were
  rewritten; `tests/test_notify.py` holds the rule.
- **Twins are one row.** A kind that `follows` another is not listed, and
  saving sets it with the kind it follows (Intake Waiting, One Thing; Arrived
  Through a Link, One File).
- **OneAI**: **Too Many Emails?** is a OneAI button beside the page's
  sentence; the kinds OneAI sends (Intake's, and the two grievance reads)
  carry the OneAI tag (`oneai` on the declaration).
- The switch sentences say what the switch does, then what off means.
- **Turn On Push** is quiet; Save is the page's one primary action.
- `one/README.md` says all of it; the workspace page and OneAI's
  `notification_type` tool now say who each kind goes to.

Then, on your word:

- **OneIntake** is a product: its name everywhere on screen (the rail, its
  page, Workspace settings, the notification heading, its legal clauses), and
  its own mark, `brand/oneintake.svg` (a page read by a line of light, in
  OneAI's sky-to-violet), registered as a Custom Icon. The ids
  (`one_intake`, the `intake` page and section) stay.
- Each app's heading carries its mark (`settings._mark`); Across One carries
  One's, and Rules none.
- OneIntake's kinds no longer carry the OneAI tag; every one of them is
  OneAI's, so the tag said nothing.
- **New IBAN is not a notification any more.** Its draft bill was already
  held red and its pay panel shows no QR code; now the bill is also marked
  wrong with why (`planning._hold_iban`), so it waits in OneIntake like
  anything else OneAI could not settle, and Intake Waiting tells the person.
  A patch removes the type.

### Push (Notifications, stage 4)

Stage 4 of `docs/NOTIFICATIONS.md`, on both Notifications screens.

1. **Notifications**: a Notification Log is pushed, after it is committed and
   in the background, to every browser its person turned push on in, when they
   ticked push for its type and the workspace allows push for it. A browser the
   push service says is gone is forgotten; so is one that fails five times in a
   row.
2. **OneAI**: `my_notifications` now says, per kind, whether it is pushed, and
   in how many browsers push is on. **Too many emails?** may suggest push
   instead of mail.
3. **Intake**: phishing, a new IBAN and what waits start pushed for a new
   person; the weekly digest does not.
4. **Permissions**:
   - A person registers, lists and removes only their own browsers; Push Device
     has no desk permissions at all.
   - A push goes only to Google's, Mozilla's, Apple's or Microsoft's push
     service, over https (`push.SERVICES`): the address comes from a browser,
     and a server that posts wherever a browser says is one anybody can aim.
   - The VAPID private key is in the site's config, never the database.
   - The worker is served for the whole site, and handles push and clicks
     only; a test holds that it has no fetch handler.
5. **Cross-module**: every module's types can be pushed as they can be
   mailed; frappe's mentions, assignments and shares too.
6. **UI**:
   - You › Notifications: a Push part at the top (on, off, blocked, or
     unsupported in this browser; Turn On Push, Send a Test, Turn Off; the
     other browsers with Remove), and each kind a row with Email and Push.
   - Workspace › Notifications: Push Allowed and Push for New People, and a
     Push badge in the list.
   - Found: headless Chromium is incognito and has no push, so turning it on
     cannot be seen here. The whole path was checked instead against a local
     push service: the push arrived VAPID-signed and aes128gcm-encrypted, and
     decrypted with the browser's key to the notification's text.
7. **Documented**: One's README, both Notifications sections.
8. **Legal**: the Privacy Policy gains `push` (what is kept about a browser,
   and that the push services carry messages they cannot read) and goes to
   revision 2, so everybody is asked again: push is a new thing kept about a
   person, not a clarification. The push services are named, not listed as
   subprocessors, since they are the browser's own and never see content.

### Workspace › General

What the workspace was made with (name, company, country, currency, read
only), then one stack of fields: Company Logo, Language, Time Zone, Date,
Time and Number Format, First Day of the Week, and the Calendar Links switch.
Saved to Company and System Settings.

1. **Notifications**: nothing is sent, and nothing needs to be.
2. **OneAI**: the panel does not know the screen: no page sentence, no
   suggestion. Recommended: the sentence, and with 6c below, **Is signing in
   here safe enough?**, read from the sign-in rules and how many people have
   a second step.
3. **Intake**: nothing here.
4. **Permissions**: hold. Only Workspace Administrator opens the page, and
   `load` and `save` call `roles.require()` first.
5. **Cross-module**:
   - The Company Logo only reaches printed invoices, quotes and orders
     (erpnext's letter head). One itself keeps its own mark. Nothing on the
     page says so. Recommended: say it under the field.
   - Language and Time Zone are only the starting point for people who have
     not set their own in Profile. Nothing says that either. Recommended: one
     line under each.
6. **UI and UX**:
   - a. One long stack, the formats half-width and the switch full-width.
     Recommended: three parts divided by a rule: **Company** (the facts and
     the logo), **Region and Formats** (in two columns), **Calendar Links**.
   - b. Nothing shows what a format looks like until it is saved.
     Recommended: one quiet line under the formats that reads as the choices
     do, "Today reads 27-09-2026 14:05, and a number 1,234.56", redrawn as
     they change.
   - c. The rules for signing in are nowhere an administrator can reach.
     Sign-in tells a person "your workspace decides" two-factor, and the
     passkey sign-in switch (`one_login_with_passkey`) is only in System
     Settings' desk form. Recommended: a **Signing In** part here, from
     System Settings' own fields: two-factor and its method, Login with
     Passkey, how long a session lasts, and the password strength rule.
   - d. It does not save against `modified` or hear `doc_update`: two
     administrators overwrite each other without a word. Recommended: the
     section returns `opened` for System Settings and Company, and saves
     through `_as_opened`, as Profile does.
7. **Documented**: no section in `one/README.md`. Recommended: **General,
   for the Workspace**.
8. **Legal**: holds. Nothing here reaches another company.
9. **Built from frappe**: holds. The fields are System Settings' and
   Company's own, drawn by frappe's FieldGroup.

Your word: all of them.

Done:

- Four parts under headings: **Company**, **Region and Formats** (two
  columns), **Signing In** and **Sharing**. A form that opens on a heading
  has no rule above it (`shell.css`).
- Under the formats, "Now it reads 27-09-2026 18:26:14, and a number
  1,234,567.89.", in the chosen time zone, redrawn as they change.
- **Signing In** writes System Settings' own fields. **Two-Factor Sign-in**
  is Off, Administrators or Everybody: frappe's switch plus its per-role
  flag, where frappe's own "everybody" is the All role, set after the save
  because frappe flags All whenever two-factor is switched on. The code
  comes from an authenticator app or email (SMS needs a gateway nobody has).
  **Signed Out After** is `session_expiry` as 8 hours to 30 days, keeping a
  value set elsewhere. **Passwords** is the policy switch and score as one
  choice. **Passkey Sign-in** is `one_login_with_passkey`.
- The section returns `opened` for System Settings and Company and saves
  through `_as_opened`: a stale save is refused, and another administrator's
  save reloads the page or says so.
- Help lines under Company Logo, Language, Time Zone and each sign-in rule.
- OneAI: the page sentence, **Is signing in here safe enough?**, and a read,
  `workspace_sign_in` (administrators only): the rules, people and
  administrators, passwords over a year old, the last week's failed
  sign-ins.
- `one/README.md` gains General, for the Workspace. `test_settings.py` now
  holds a workspace section OneAI offers anything on to its README section
  too.
- Your question, "anything else to bring from frappe settings?", and your
  word, all of them: **Address in Mails** (`email_footer_address`) under
  Company; **Email Link Sign-in**, **One Device at a Time**, the lockout
  (**Wrong Passwords Before a Lockout**, **Locked Out For**) and **Passwords
  Expire After** under Signing In; **Record Sharing** (frappe's
  `disable_document_sharing`, the other way round) under Sharing. Left out:
  what is the operator's (backups, scheduler, telemetry, API logging, app
  name), what is OneBook's (precision, rounding) or OneCloud's (upload size
  and types), and "disable password login", which can lock everybody out.

### Workspace › People

Everybody on the workspace in one grid: a row per person with five
dropdowns (OneCRM, OneBook, OneInventory, OneProject, OneHR: None, User,
Manager), an Administrator tick and Turn Off. Seats above, Invite beside
them. Each change saves at once through `set_access`, `set_admin`,
`set_enabled`; Invite makes a User and sends frappe's welcome mail.

1. **Notifications**: only the welcome mail. A person is not told when
   they are given an app or made an administrator, and nobody is told when
   somebody becomes an administrator, which is how a taken account widens
   itself. Recommended: **Access Changed** to the person, on the bell
   ("You can now use OneCRM as a manager"); **Administrator Added** to every
   administrator, always mailed, like Password Changed.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence, and **Who has access to what?** and **Who has not signed in
   lately?**, read by a new `workspace_people` (administrators only):
   access, administrators, last active, turned off.
3. **Intake**: nothing here.
4. **Permissions**: hold. Every call asks `roles.require()`; nobody turns
   themselves off or removes the last administrator; a seat is checked
   before turning somebody on or inviting.
5. **Cross-module**:
   - Whether a person is an employee in OneHR is not shown. Recommended:
     their Employee, linked, when they have one.
   - An administrator cannot see where somebody is signed in or sign them
     out: offboarding means Turn Off and hoping. Recommended: in the
     person's dialog (6b), their devices and last sign-ins from
     `signin.py`, **Sign Out Everywhere**, and **Send a Password Reset**
     (frappe's own reset mail).
6. **UI and UX**:
   - a. A wall of thirty "None" dropdowns, a bare checkbox and a Turn Off
     on every row; the app icons sit apart from their names. Recommended:
     frappe's `EmbeddedList`, as What OneAI Remembers now is: Person (photo,
     name, address), Apps (a badge per app they have, "OneCRM · Manager"),
     Administrator, Last Active, and an Off badge; search built in.
   - b. Recommended: a row opens the person in a frappe Dialog: a Select
     per app, an Administrator switch, and Turn Off / Turn On, Sign Out
     Everywhere and Send a Password Reset in its footer. Saved together,
     against the User's `modified`.
   - c. Invite is a button inside the page. Recommended: **Invite
     Somebody** is the page head's primary action, and its dialog also
     asks which apps they get, so nobody needs a second step.
   - d. Turning somebody off asks nothing. Recommended: ask first, and say
     their records stay.
   - e. The seats badge floats alone. Recommended: one quiet line under
     the intro, "6 of 10 seats used".
7. **Documented**: no section in `one/README.md`. Recommended: **People,
   for the Workspace**.
8. **Legal**: with 5b, administrators see where people sign in from. The
   privacy notice must say so. Recommended: a `clause()` in `one/legal.py`,
   "Your workspace's administrators can see where you are signed in and
   your last sign-ins, and can sign you out."
9. **Built from frappe**: the dropdowns are a raw `<select>` and the tick a
   raw checkbox, not frappe's controls. 6a and 6b replace both.

Your word: all of them.

Done:

- The list is frappe's `EmbeddedList`: Person (photo, name, address, an Off
  badge), Apps (a badge per app, or "Every app · Manager"), Administrator,
  Last Active; search past five. The seats are in the line under the intro.
- A row opens the person in a frappe Dialog: a Select per app in two
  columns, the Administrator switch, their employee record, where they are
  signed in (five, then "And N more") and their last sign-ins. Its footer
  has Turn Off (asks first, signs them out now, frees the seat), Turn On,
  Sign Out Everywhere (frappe's `clear_sessions`) and Send a Password Reset
  (frappe's own reset mail). One `save_person` sets the roles in one save
  against the User's `modified`; a stale save is refused. The values are
  set after the dialog is made, because frappe reads a field default of
  "User" as the person signed in.
- A save always keeps Desk User: found when taking the administrator role
  from somebody who held nothing else made frappe turn them into a website
  user, and they dropped out of the workspace.
- **Invite Somebody** is the page head's primary action; its dialog asks
  which apps they get.
- Notifications: **Access Changed** to the person ("Samir Aoun changed what
  you can use: OneCRM as a user."), **Administrator Added** to every other
  administrator, always mailed.
- OneAI: the page sentence, **Who has access to what?** and **Who has not
  signed in lately?**, read by `workspace_people` (administrators only).
- Your word after seeing it: the dialog was too crammed. A person is now a
  page, `?section=people&person=`, as a desk form like Profile: Save in the
  page head, against the User's `modified`, heard through realtime. Each app
  is a Select with its mark and what it holds; Sign Out Everywhere, Send a
  Password Reset and Turn Off sit under their name. The invite dialog shows
  the marks too, and an invited person is not also sent Access Changed:
  their welcome mail says it.
- The invitation is One's own (`one/invite.py`): frappe's welcome mail was a
  reset link that lived twenty minutes (`reset_password_link_expiry_duration`)
  and said nothing of who asked. Ours is the hub's Invitation type, "Samir
  Aoun invited you to Nine X", with the apps they get and a link that works
  for seven days: opening it asks frappe for a fresh reset link and goes
  there, so the password is still set on frappe's page. Choosing it spends
  the link, and a first password is not told as Password Changed. Invite
  Again for somebody who has not joined.
- No mail says "Sent via ERPNext" any more: System Settings'
  `disable_standard_email_footer`, by patch and in `brand.py`.
- Your word on the sub-pages: a person, a notification type and a rule are
  now drawn as docviews (`Editor.as_record`, docs/SHELL.md): "People /
  Rania Sabbagh" in the breadcrumb with the status pill, Actions and Save in
  the page head, full-width parts, frappe's form sidebar. No back buttons.
- `one/README.md` gains People, for the Workspace. The privacy notice gains
  "people-sign-in" and goes to revision 4, since administrators now see
  where a person is signed in: everybody agrees again at their next
  sign-in.

### Workspace › Notifications

Built as stage 2 of `docs/NOTIFICATIONS.md`, and gone over against the eight
points as it was built.

1. **Notifications**: this is where every one of them is decided. Saving sends
   nothing. Turning email off takes the type out of everybody's email choices,
   because frappe would otherwise keep mailing whoever had chosen it; turning
   it back on gives it to everybody if it is on for new people. A new person
   now starts on email only for the types marked for new people (frappe
   started them on every type).
2. **OneAI**:
   - Two tools in `one/ai.py`: `notification_type` reads a type's text, slots
     and channels, and `rewrite_notification` suggests new text as a card,
     refused if it names anything but the type's slots. Applying the card is an
     ordinary save, by the administrator.
   - The panel is told the page and which type is open (`record` in
     `oneai.where()`).
   - It offers **Rewrite this notification**, **Which should be emailed?** and
     **How do notifications work?**. The editor's **Rewrite with OneAI** asks
     the first about the type that is open.
3. **Intake**: six of the types are Intake's, listed and edited here like any
   other.
4. **Permissions**:
   - Only workspace administrators see the section; `load`, `save` and
     `preview_notification` all ask `roles.require()`.
   - The Workspace Administrator gets read and write on Notification Type
     (Custom DocPerm), so OneAI's card applies as them.
   - An edited text is rendered in a Jinja sandbox with nothing but its slots.
     Frappe's own `render_template` would have handed it `frappe.db`, and so
     any record in the workspace. Saving a text that names anything else is
     refused, from the page, from a card, or from the desk.
   - The shared link's code cannot be turned off.
5. **Cross-module**: every module's types in one list, grouped by the app that
   sends them, with frappe's own (mentions, assignments, shares) at the
   bottom, read-only, since their text is frappe's.
6. **UI**:
   - The list is rows on the page, grouped by app, each a link with a
     frappe-ui list-row hover: its name, what it is about, and badges for Off,
     Edited, and Email (blue when on for new people) or Mailed Outside.
   - A type opens as a form: Send This, What It Says (subject as one line,
     message as a small code field), the names it may use, a live preview with
     each name as a chip where its value goes and the refusal in red, then
     Channels. Save is in the page head; it is dirty against what loaded, warns
     before leaving, saves against `modified`, and reloads on `doc_update`.
   - Subjects no longer carry `<b>`: every name in a subject is bolded when it
     is sent, so neither our text nor an administrator's has to say so.
   - Push is declared on every type but not shown until it can be sent
     (stage 4).
7. **Documented**: One's README has Notifications, for the Workspace, which is
   what `how_to` answers from.
8. **Legal**: the Acceptable Use Policy gains `notification-text`: what an
   administrator writes into a notification is the workspace's content, sent
   in its name, including to outside addresses. Recorded as a clarification
   (new hash, same revision): the policy already covered what a workspace
   sends.
   - Found doing it: the gate asked everybody again on a new hash, although
     OneLegal's README says only a new revision does. It now compares
     revisions (`gate.agreed`), and the Agreements page shows a clarified
     document as still Agreed, with a link to the text that was agreed.

### Rules (Notifications, stage 5)

Stage 5 of `docs/NOTIFICATIONS.md`: the workspace's own notifications, on
Workspace › Notifications.

1. **Notifications**: a rule is frappe's Notification, sent to the bell under
   a type of its own, so it is mailed or pushed as each person chose. It tells
   only the people who may read the record.
2. **OneAI**: `draft_notification` drafts a rule as a card, refused when its
   text names anything but the record's fields or its event is not one of the
   seven. The page offers **Make a rule**, and the Rules part has **Ask OneAI
   for One**.
3. **Intake**: nothing of its own. A rule may watch Intake's records like any
   other the administrator can read.
4. **Permissions**:
   - The Workspace Administrator gets Notification (Custom DocPerm), and a rule
     they save is held in the controller (`rules._hold`), so the desk is no way
     round the screen.
   - Frappe renders a Notification's text with its full globals and runs its
     conditions as Python, because only its own administrators may write one.
     A workspace rule has filters for a condition and text that names only
     `{{ doc.field }}`; a rule made on the desk by a workspace administrator
     with Python in it is refused.
   - Recipients: by role, by a person field of the record, or its assignees;
     no copies, no addresses, no conditions. At send time the list is cut to
     people who can read that record.
   - A rule may watch only a kind of record its author can read.
5. **Cross-module**: a rule can watch any module's records, so this is where a
   workspace says "tell the managers about a new expense claim" without a line
   of code. Its person fields come from the record (Allocated To, Assigned By).
6. **UI**:
   - The list gains a Rules part above the types: each rule a row saying when
     it fires, with New Rule and Ask OneAI for One.
   - A rule is a form: the kind of record (a Link that searches translated
     names; frappe's own query cut at two hundred names and found nothing),
     when, the date or field that goes with it, frappe's filter editor for
     "only when", who is told, the text with a preview, and channels. Save in
     the page head against `modified`; Delete asks first. A new rule moves to
     its own address once saved.
   - Found: frappe's default message for a new Notification ("Add your message
     here") was prefilled into the form; a new rule now starts empty.
   - Found: a rule could be saved telling nobody (frappe allows it, and the
     sample rule was one). It is now refused until it names a role, a person
     on the record, or its assignees.
7. **Documented**: One's README, Notifications for the Workspace, has Rules.
8. **Legal**: the Acceptable Use Policy's `notification-text` now names rules
   as the workspace's own content. A clarification (1.cc05bbc3), not a new
   revision: what a workspace sends was already its own.

### What erpnext and hrms send (Notifications, stage 6)

Stage 6 of `docs/NOTIFICATIONS.md`, done at once so both Notifications
screens are whole before the passover comes back to them.

1. **Notifications**: every mail erpnext and hrms send is now a type on
   Workspace › Notifications. Seventeen are told through the hub, four
   standard rules are carried to the bell in their own words, and nine are
   still mailed by the app and listed as such. The table in NOTIFICATIONS.md
   says which is which and why.
2. **OneAI**: `notification_type` says whose words a type is in; a type in
   erpnext's or hrms's words is refused by `rewrite_notification`.
3. **Intake**: nothing of its own here.
4. **Permissions**: nothing new to grant. An approval goes to the approver
   HRMS names, a reminder to the employees of the same company, and a
   carried rule only to the people it names who are in the workspace.
5. **Cross-module**: OneHR, OneBook, OneInventory, OneCRM and OneProject now
   each declare what they send. HR Settings loses its reminder, leave and
   interview mail switches and templates, and Stock Settings its reorder mail
   switch, because Send This decides now. OneHR's two leave Email Templates
   went with them.
6. **UI**:
   - A type in an app's words shows its channels and says whose words they
     are; it has no text to edit and no Rewrite button.
   - A type mailed by the app shows **Mailed by ERPNext** or **Mailed by
     HRMS** in the list, and opens to Send This and a line saying so. Where
     the app has no switch, Send This cannot be turned off.
   - Found: a "What It Says" heading with nothing under it was hidden by the
     form, taking its note with it. The note is a plain line now.
7. **Documented**: One's README, Notifications for the Workspace, names the
   three kinds.
8. **Legal**: nothing new. Nothing is sent to anybody new or through anybody
   new; only which door it goes through changed.

### Workspace › Plan and Credits

Two sections drawn from the `Workspace Account` copy (`account.refresh`,
nightly): Plan (plan, status, seats, a storage bar) and OneAI Credits
(balance, what expires when, OneIntake's line for the month), then Buy
Credits (a dialog of packs, then Stripe in a new tab) and See What Used Them
(the AI Credits report). The same record also has its own desk form,
`/desk/workspace-account`, with a Record Head and its own Buy credits.

1. **Notifications**: nothing about the account is ever sent. Nobody is
   told credits are running out, that 5,000 expire in three days, that a
   pack they paid for has arrived, that storage is at 84%, or that payment
   is overdue and the workspace is suspended in N days. Recommended, in
   `one/notifications.py`, to administrators, sent from `refresh` by
   comparing what it held with what it heard:
   - **Credits Running Low**, on the bell and mailed, when the balance
     falls under a tenth of the last thirty days' use.
   - **Credits Expiring**, on the bell, seven days before.
   - **Credits Added**, on the bell, when the balance rises by a pack.
   - **Storage Nearly Full**, on the bell and mailed, at 90%.
   - **Payment Overdue**, always mailed, with the days left.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence; **How long will our credits last?** and **What used the most
   credits this month?**, read by a new `workspace_plan` (administrators
   only): plan, seats, storage, balance, held, expiring, and the last
   thirty days' use by model and person (the same `ai_usage` ask the report
   makes; no AI call).
3. **Intake**: "OneAI handled 26 of 39 documents this month" is OneIntake's
   and is already on the OneIntake page. Here it answers nothing about
   credits. Recommended: take it off.
4. **Permissions**:
   - The page and Buy ask `roles.require()`, and hold.
   - `Workspace Account` gives read to **All**, so every desk user can
     open `/desk/workspace-account` and read the balance, what is owed and
     the last error; `account.mine` hands the same to anyone and nothing
     calls it. Recommended: read for administrators only; delete `mine`.
5. **Cross-module**:
   - The OneAI rail's **Credits** and See What Used Them are the same
     report. Fine, but the report is where the numbers are.
   - Seats do not link to People, and the storage bar does not lead to
     OneCloud. Recommended: "6 of 10 used" opens People; storage opens
     OneCloud's Home, sorted by size.
   - Two screens for one record. Recommended: `/desk/workspace-account`
     sends administrators here, as the Customize form's own page does.
6. **UI and UX**:
   - a. Buy Credits is a button in the body. Recommended: the page head's
     primary action; See What Used Them its secondary.
   - b. A workspace days from suspension sees nothing: `account_said`
     (the overdue sentence, or "could not reach your account") is only on
     the desk form. Recommended: drawn as a record (`Editor.as_record`):
     the standing badge (heads.py's "Active", "Payment overdue") and the
     sentence at the top, the plan in the side.
   - c. Status says "Live", the admin's word. Recommended: heads.py's
     word.
   - d. Days Left is a bare number. Recommended: only in the overdue
     sentence.
   - e. Held credits are not shown, so a balance that looks fine while
     calls are refused says nothing. Recommended: "Held" under Credits,
     when there is some.
   - f. The page never says how old its numbers are, and a pack paid for
     shows up tomorrow. Recommended: "As of 10:42", **Check Again** (a
     `refresh`), and a refresh when the page is opened and older than an
     hour.
   - g. The storage bar is black at 84%. Recommended: frappe-ui's
     Progress, amber from 90%, red over.
   - h. The pack Select says only the pack's label. Recommended: "5,000
     credits · $50" per pack.
   - i. "OneAI  Credits" has a double space where the brand splits the
     word.
7. **Documented**: no section in `one/README.md`. Recommended: **Plan and
   Credits, for the Workspace**: what each number is, where credits go
   first, how to buy, what expires.
8. **Legal**: the terms say credits are bought ahead and not refunded, but
   not that they expire, that the plan's monthly credits do not roll over,
   or that the soonest-expiring are used first (`topup.py`). Recommended:
   say so in the terms' `credits` clause, and bump the terms' revision
   (material). Stripe is already a subprocessor in `one_admin/legal.py`.
9. **Built from frappe**: the dialog is frappe's; the bar is espresso's
   `frappe.ui.progress` (6g); the facts are a hand-drawn list, which 6b
   replaces with the record view's own parts.

Your word: all of them.

Done:

- Five notices in `one/notifications.py`, sent from `account.refresh` to
  every administrator when a line is crossed: Credits Running Low (under a
  tenth of the last thirty days' use, which `hello` now sends as
  `credits.month`), Storage Nearly Full (nine tenths) and Payment Overdue
  (the suspension date, once per date), all three also mailed; Credits
  Expiring (a week ahead, once per date) and Credits Added on the bell.
  `roles.administrators()` is who hears, shared with Administrator Added.
- The page is the account drawn as a record: the standing in the pill, the
  overdue or out-of-touch sentence above everything (`heads.account_said`),
  Plan (plan, seats leading to People, storage leading to OneCloud, orange
  from nine tenths, red over) and OneAI Credits (left, held, used in the last
  thirty days, expiring). The side has the name, the plan, links and "As of".
  Buy Credits is the page head's primary action; See What Used Them and
  Check Again sit beside it. Opening the page asks the account again when
  its copy is over an hour old, and so does coming back from payment.
- Packs read "1,000 credits · $ 9".
- OneIntake's month line is gone from here.
- `Workspace Account` is read by administrators only, `account.mine` is
  deleted, and `/desk/workspace-account` sends its reader here.
- OneAI: the page sentence, the two suggestions and `workspace_plan`.
- `one/README.md` has Plan and Credits, for the Workspace.
- The terms' credits clause says the plan's monthly credits expire at the
  month's end and are used first, and bought ones never expire; terms
  revision 2, so administrators agree again.
- A section title is one flex item, so "OneAI Credits" no longer splits.

Afterwards, on your word: a **Ledger** section, the account's last ninety
days newest first. Each grant and refund is a line of its own (bought, the
plan's monthly credits, given by One, refunded); spend is summed per day,
because the account keeps a spend row per call and per bucket. A day opens
the AI Credits report for that day, by person. The admin's `ai_usage` now
sends `arrived` (`ledger.arrived`), and `workspace_plan` reads the ledger.

Afterwards, on your word: plans and add-ons are sold here. Change Plan
shows the plans side by side and what a move costs a month; Add, Storage,
Database or Seats is an add-on and how many, and says when the plan above
gives the same for less; the Plan section shows the database beside
storage, what it costs a month, and the add-ons with Remove. How the price
list is built and kept coherent is `docs/INFRASTRUCTURE.md`, Plans, add-ons
and what they cost. Terms revision 3.

Not done: storage leads to OneCloud's Home, not to a list of the biggest
files, because OneCloud has no workspace-wide list by size to open.

### Workspace › Domains

One section, Addresses: each name the workspace answers at, with a status
badge, Primary and Ours, and Make Primary and Remove per row. Add a Domain
and Check Again are buttons in the body. The rows come from the
`Workspace Account` copy (`settings._domains`); every button asks the admin
site, which asks Frappe Cloud (`one_admin/domains.py`) and writes the answer
back into the copy (`account._keep`). The admin site asks Frappe Cloud
nightly about names not yet Active, and `hello` carries the list back
hourly.

1. **Notifications**: nothing is sent. A name goes Active minutes or hours
   after it is added and nobody is told, so the administrator has to come
   back and press Check Again. Nobody is told when a name stops working
   (Frappe Cloud drops it, status Gone), and the other administrators are
   not told when somebody adds a name, removes one or changes the main
   address, which moves the sign-in page and every link in every mail.
   Recommended, in `one/notifications.py`, to administrators, sent from
   `account.refresh` comparing before and after as the credit notices are:
   - **Domain Working**, on the bell and mailed, when a name goes Active.
   - **Domain Stopped Working**, on the bell and mailed, when one that was
     Active is not.
   - **Main Address Changed**, on the bell and mailed, to every other
     administrator, from `domain_primary`.
2. **OneAI**: the panel does not know the screen. Recommended: the page
   sentence, and **Why is our domain not working?**, read by a new
   `workspace_domains` (administrators only): each name, its status, what
   Frappe Cloud last said about it, and what its DNS should say. No AI call
   is needed to read it; the model only explains.
3. **Intake**: nothing here, and nothing should be.
4. **Permissions**:
   - The page is in the Workspace group (administrators), and every call
     asks `_may_rename` (Workspace Administrator). Holds.
   - The guard's names are wrong: `MAY_RENAME` and "Only an administrator
     of this workspace can change its address" also guard buying credits.
     Recommended: `roles.require()`, as Plan and Credits uses, and the
     constant gone.
5. **Cross-module**:
   - The main address is what the site calls itself (`host_name`), so it is
     every link in One's mail, the invite link, the calendar feed and a
     OneCloud share link. The screen does not say so. Recommended: one line
     under Primary saying it.
   - OneMail's mail domain is a separate thing (Settings › Mail) and the
     two are easy to confuse. Recommended: the note says this page is where
     the workspace opens, and names where mail addresses are set.
6. **UI and UX**:
   - a. **A dead end.** Once your own name is primary, Make Primary on
     ours fails ("a name we hand out, so it cannot be added as your own"),
     because `_held` runs every name through `hosts.claimable`. And Frappe
     Cloud refuses to remove the primary name. So a workspace that makes
     its own name primary can never go back or remove it. Recommended: the
     given name is always allowed back as primary (`set_host_name` to the
     site's own name, `primary_domain` cleared).
   - b. **The DNS is never explained.** Add a Domain is one field, "For
     example office.example.com", and nothing says what to point it at.
     `domain_check` exists and nothing calls it. Recommended: the dialog
     says the record to make (a CNAME to the site's Frappe Cloud name, with
     Copy) and that Cloudflare's proxy must be off; Add checks the DNS first
     and shows Frappe Cloud's own sentence when it is wrong; a Pending row
     shows the same record, so the instructions are there when somebody
     comes back to it.
   - c. **Raw JSON.** After Check Again or any action, a custom name's row
     prints what Frappe Cloud said as a JSON string (`Tenant Domain.said`
     via `domains.mine`); after a reload it is gone, because `_keep` drops
     it. Recommended: keep the one sentence worth keeping (Frappe Cloud's
     message) on the copy, and draw it as the row's sub-line.
   - d. Add a Domain is a solid button in the body. Recommended: the page
     head's primary action; Check Again beside it, as on Plan and Credits.
   - e. Hand-drawn rows. Recommended: `shell.table` (Domain, Status, a
     Primary badge, actions), as Invoices is on Plan and Credits.
   - f. Status words are Frappe Cloud's raw ones and all amber: Pending,
     Broken and Gone look the same. Recommended: Active green, Pending
     orange, anything else red; translated.
   - g. The note says "The one we provide", which is first person.
     Recommended: "The t.4dl.app address always works".
   - h. `hosts.Unclaimable` sentences are not translated.
7. **Documented**: `one/README.md` has no Domains section, so OneAI's
   `how_to` cannot answer "how do I use our own domain". Recommended: a
   section on what the page is for, the DNS record, why Cloudflare's proxy
   has to be off, what Primary changes, and who may do it.
8. **Legal**: the terms say nothing about a customer's own name.
   Recommended, a clause in `one/legal.py`: the customer must own or
   control the name, the certificate is issued for it by Let's Encrypt
   through Frappe Cloud, and the name stops answering when the workspace
   is closed. Let's Encrypt only sees the name, which is not personal
   data, so it is not a subprocessor.
9. **Built from frappe**: the dialog is `frappe.ui.Dialog` with a Data
   control and the confirm is `frappe.confirm`. The rows are hand-drawn
   (see 6e), and the page does not update when a name goes Active; with the
   notice in 1 it would, through `frappe.realtime` from `account.refresh`.

Your word: all of them.

Done:

- **The dead end is gone.** Make Main Address on the address One gave the
  workspace puts press's own record back on the press name and writes our
  name into the site's `host_name` again, as provisioning does
  (`domains._back_to_given`). Ours is the main address whenever none of
  the customer's is, so a stale `primary_domain` can no longer hide it,
  and removing a domain that was primary clears it.
- **The DNS is explained.** `hello` sends the CNAME target (the site's
  Frappe Cloud name) and the account keeps it (`dns_target`). The Add
  dialog shows the record to make as the domain is typed, with Copy and the
  Cloudflare note; Add checks the DNS first and says what to do when it
  does not point here yet. Your Own Domain shows the same record on the
  page.
- **No raw JSON.** `mine` no longer sends what press said; a row says in
  our words what Waiting and Not Working mean. A refusal from the admin
  site now reads as the sentence it was (`faults.detail` reads
  `_server_messages`), and `hosts` refusals are sentences, translated.
- **The page.** Add a Domain is the page head's action and Check Again
  beside it; the list is `shell.table`; Working is green, Waiting orange,
  anything else Not Working in red; Main Address and Given by One are
  badges. A line under the list says what the main address changes, and
  the note says email addresses do not change. The page asks the account
  again when its copy is over an hour old, and redraws on `one_domains`.
- **Notices**: Domain Working and Domain Stopped Working, to every
  administrator, on the bell and by mail, told when the account's answer
  changes (`account._tell_domains`, from `refresh` and from every domain
  call); Main Address Changed to every other administrator.
- **Guards**: every call asks `roles.require()`; `MAY_RENAME` and
  `_may_rename` are gone.
- **OneAI**: the page sentence, **Why is our domain not working?**, and
  `workspace_domains`.
- `one/README.md` has Domains, for the Workspace.
- The terms say what having your own domain means (`one/legal.py`,
  own-domain); terms revision 4.

Afterwards, on your word: a customer's own domain is a Cloudflare custom
hostname on our zone, not a Frappe Cloud domain. The customer CNAMEs it to
their `<slug>.t.4dl.app`; Cloudflare issues the certificate; a Worker route
and a `host:` key in KV send it to the site, as ours already are. Frappe
Cloud never sees the name, so `*.frappe.cloud` is never shown and a customer
behind Cloudflare's proxy needs to change nothing. Add no longer waits on the
DNS: the domain waits, and says Cloudflare's own sentence about what is
stopping it. The record is drawn as a DNS provider lists one, with Copy on
each value, and a note on bare domains. Cloudflare is now listed as the
network every workspace is reached through (subprocessors revision 2).
Tested live on `one-test.4dl.dev`: Working in 100 seconds with a valid
certificate, served through the router, then removed with its hostname,
route and key.

### Workspace › OneAI

Two sections. **What Runs on Which Model** lists every enabled AI Action
(seventeen: Chat, Look It Up, Draft a Reply, the five OneIntake reads, the
OneHR ones, Summarise, Transcribe…), each with its model as a badge
("Default", or the model's raw id) and **Change**, which opens the desk
form `AI Action Setting` for it: the model (a Select filled from the
account's catalogue) and Added Instructions, with **Try it**. **Knowledge**
is a count ("1 notes OneAI reads before it answers") and Open, to the desk
list of AI Knowledge.

1. **Notifications**: nothing is sent. Changing an action's model or its
   added instructions changes what OneAI does, and what it costs, for
   everybody, and the other administrators are not told. Recommended: **OneAI
   Changed**, on the bell, to every other administrator, naming the action
   and what changed (model, instructions, back to default).
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and **Which of these costs us the most?** and **Is there a
   cheaper model that would do?**, read by a new `workspace_oneai`
   (administrators only): each action, its model or the default, its added
   instructions, the models the account offers for it with their price, and
   what each action used in the last thirty days. No AI call to read it.
3. **Intake**: five of the rows are OneIntake's (First look, Read a
   document, Place a document, Read scans, Transcribe recordings), mixed
   in alphabetically with Chat and the OneHR ones, and Workspace ›
   OneIntake does not link here. Recommended: the rows grouped by the
   product they belong to (OneAI, OneIntake, OneHR, OneMail), and OneIntake's
   page linking to its group.
4. **Permissions**:
   - The page is administrators'; `AI Action Setting` is written by
     Workspace Administrator (and System Manager). Holds.
   - `AI Knowledge` is read by All. That is needed, because OneAI reads it
     as the person asking (`memory.py`), so everybody can open the list; it
     is what OneAI would tell them anyway. Holds, and the docs should say so.
   - **Try it** charges the workspace's credits, and says so after, not
     before. Recommended: the cost is said on the button's dialog before
     running.
5. **Cross-module**:
   - What each action costs is nowhere: the AI Credits report groups by
     model, person or day, not by action. Recommended: a last-thirty-days
     column here, and **Action** in the report's By (the ledger's
     reference carries it).
   - Knowledge is a count and a link out. Recommended: the notes listed
     here (title, what they apply to), opened and added from the page.
6. **UI and UX**:
   - a. **Raw model ids.** Chosen models show as
     `google-ai-studio:gemini-2.5-flash-lite` in a violet badge, and the
     form says "Empty uses gemma-4-26b-a4b-it". Recommended: the model's
     name from the catalogue ("Gemini 2.5 Flash Lite"), "Default (Gemma 4)"
     in gray, and the price per million tokens in the picker.
   - b. **Change leaves the page** for a desk form that shows the action's
     key ("chat") in a Link field, a Templates button and a blue banner.
     Recommended: a dialog on this page: Model, Added Instructions, Try It
     and Use the Default, saved against `modified`.
   - c. Labels are in two cases ("Look It Up", "Draft a Reply" beside
     "Explain a document", "Read scans"), and "Audit what OneAI did" puts
     gaps round OneAI. Recommended: Title Case throughout, brand span fixed.
   - d. Hand-drawn rows. Recommended: `shell.table`, grouped as in 3.
   - e. "1 notes": the plural is not handled.
7. **Documented**: `one/README.md` has no section for Workspace › OneAI,
   so `how_to` cannot answer "how do I make OneAI answer in Arabic" or
   "what is knowledge". And `one_ai/` has no README at all. Recommended: a
   section, OneAI, for the Workspace (what each part does, what added
   instructions can and cannot change, what knowledge is and who reads it,
   what Try it costs), and the module README when the pass reaches OneAI
   itself.
8. **Legal**: choosing a model chooses who receives the data. The catalogue
   offers two providers, `google-ai-studio` and `workers-ai`, and both are
   listed (Google, Cloudflare). Holds today, but nothing stops an operator
   enabling a provider the subprocessors do not name. Recommended: a guard
   that every provider offered is a listed subprocessor, and the picker
   saying which company runs the model.
9. **Built from frappe**: the setting is a frappe form with frappe
   controls, which is right for behaviour, but it is reached by leaving the
   page (6b). The rows are hand-drawn (6d). No realtime: a change made by
   another administrator does not redraw an open page; it would with
   `doc_update` on AI Action Setting.

Your word: all of them, with model makers' logos (Google's favicon service,
v2), a proper list for the actions, and the page under OneAI in the rail.

Done:

- **Where it lives.** The rail's OneAI group now has **Actions** (this page,
  titled OneAI Actions) and **Knowledge** (the AI Knowledge list) beside
  Credits, Conversations and Suggestions. It left the Workspace group.
- **The list.** `shell.table`: Action (with what it does), Product, Model
  and Last 30 Days. A model is its maker's logo and its name, read from the
  catalogue and made readable (`makers.pretty`: "Gemma 4 26B A4B IT", not
  `gemma-4-26b-a4b-it`), with a gray Default when One picked it. The logo
  is the maker's, not the host's: Meta for Llama even though Cloudflare
  runs it (`one_admin/makers.py`).
- **Change is a dialog on the page**: Model (every model on offer that can
  do it, named with its maker), what the picked one is (made by, run by,
  and about how many credits per thousand words read and written), Added
  Instructions, **Try It** (runs what the dialog holds, saved or not, and
  says it uses credits before it runs), **Use the Default** and **Save**,
  which refuses when another administrator changed it since it was opened.
  The old desk form sends its reader here.
- **What each action costs.** Every reservation now records its action
  (`Credit Reservation.action`, from `actions.run` through the gateway),
  `ai_usage` answers by action, the list shows the last thirty days, and
  the AI Credits report has **Action** in By. Calls from before this show
  as Other.
- **Grouped by product**: `AI Action.product` (OneAI, OneIntake, OneHR,
  OneMail), labels in Title Case. OneIntake's page has **Models**, which
  opens this list showing its actions only.
- **Notice**: OneAI Changed, on the bell, to every other administrator,
  saying what changed ("the model to Gemini 3 Flash Preview", "the added
  instructions"). The page redraws on `one_oneai`.
- **OneAI**: the page sentence, **Which actions cost the most?** and **Is
  there a cheaper model that would do?**, read by `workspace_oneai`.
- **Legal**: `makers.PROVIDERS` is every provider a workspace's data may go
  to; `actions.offered` never offers another, and
  `test_every_model_provider_offered_is_a_declared_subprocessor` holds it
  to the Subprocessors list.
- `one/README.md` has OneAI Actions, for the Workspace, with Knowledge.

Not done: `one_ai/` still has no README of its own; that is the OneAI
product's screen, when the pass reaches it.

### OneAI › The Agent and the Panel

Not a screen of its own but what every screen's OneAI panel runs on: how
a question is answered, on which model, and what the panel lets a person
choose. Measured before and after on `one_ai/evals.py`, about thirty real
requests asked the way the panel asks them, on Gemma 4 (the workspace
default):

| | Passed | Credits | Credits a simple question |
|---|---|---|---|
| Before (every tool, every round) | 21 of 32 | 313 | about 9 |
| After | 31 of 32 | 179 | about 3 |

1. **Notifications**: changing who may pick the model is an OneAI change
   like any other, so **OneAI Changed** now names it to the other
   administrators ("who picks the model, to everybody"). A conversation
   being named tells only its own panel, live (`one_ai_title`).
2. **OneAI**: the findings were in the agent itself.
   - Every request was sent all 120 tools, some 20,000 tokens a round, and
     a small model handed all of them picked badly (the operator's
     `ai_usage` for a workspace's credits). Now a request gets the core
     tools, the person's own, and the groups its page, its words and the
     conversation point to (`one_ai/groups.py`); `more_tools` names every
     group so the model asks for one it was not given.
   - Gemma stated figures it never looked up (41 customers; there are
     4), said it had suggested a lead and called nothing, wrote a tool
     call as text (`<|tool_call>…`), sent extension code on one line with
     `\n` written out, and leaked a `:thought` line. Each is now caught:
     a figure with nothing looked up is looked up, a claimed card with no
     card is asked for, the leaked call is read as a call, the code is read
     as its lines, the marker is cut.
   - A long run ended in the account's refusal ("gone 5 rounds"). The last
     round the account takes now asks the model to answer with what it has.
   - A list asked for one column showed cards called "Customer";
     `list_records` now always returns the record's name and title.
3. **Intake**: nothing on this; OneIntake's own actions are not chat.
4. **Permissions**: the model menu is for administrators always, and for
   everybody when the Chat action's **People Choose the Model** is on.
   `choose_model` refuses anybody else and any model the account does not
   offer, and the account checks the pick again on every call. A pick
   stops counting the moment the person may no longer choose. The menu
   shows makers, never prices.
5. **Cross-module**: a pick goes with the conversation when another part
   of OneAI takes it over (Studio writing an extension, Print Design). The
   workspace's own choice per action is unchanged and is what Automatic
   means.
6. **Bespoke UI**: the pill under the box opens frappe's own
   `frappe.ui.Dropdown`: Automatic (saying what the workspace set), then
   one row per maker with its logo and its models beside it, and for an
   administrator **Model for Everybody…**. The conversation's name in the
   head renames it (frappe's prompt). Settings' Chat action gains the
   checkbox, and "Cloudflare, Inc.." lost its second full stop.
7. **Documented**: "Asking OneAI" in `one/README.md` says what the pill,
   the name and the tool groups do; the OneAI Actions section names the
   checkbox; `docs/ONEAI.md` has the groups, the pick and the test bench.
8. **Legal**: nothing new is sent anywhere; the models are the
   catalogue's, from companies the Subprocessors agreement names.
9. **Built from frappe**: `frappe.ui.Dropdown` (with `image`,
   `description`, `selected`, `submenu`), `frappe.prompt`,
   `frappe.realtime`, `frappe.defaults` for the person's pick,
   `frappe.cache` for the list.

**Done.** The one case left is booking leave on the dev site, where nobody
approves that employee's leave and OneAI says so, which is right. The sales
and people cases are asked as a dev user who holds those roles, so they make
real cards.

Gemini 2.5 Flash: 27 of 32, 276 credits, in 211 seconds against Gemma's
299. Faster, not smarter.

- Its empty answers were an empty STOP with no output, every time, on an
  Arabic question with tools declared; the plain retry was blank too.
  Fixed: the retry now carries a turn only the model sees, "answer the
  question above now", and it called the tool three times out of three.
- After a tool call it could not write, it was told "make your last call
  again", could not see that call, and asked the person for it. The turn
  now says the call is not shown and to write it from the start.
- What is left is its own choice: it asks which mailbox, and builds a saved
  report where a report by mail was asked for.
- The bench now pins the model it is given through a handover, as the panel
  does, so a run names one model from end to end.

### OneIntake › Settings (was Workspace › OneIntake)

Moved on your word before the findings: the One sidebar has a **OneIntake**
group (Inbox, Ready to Submit, Deadlines, Spending, Settings) under OneAI,
and this page is its Settings, titled OneIntake Settings.

The page is `Intake Settings` as one flat form of eight fields, under a
violet line "OneAI handled 26 of 39 documents this month; 13 needed a
person", with **Models** and **Save** in the page head.

1. **Notifications**: nothing is sent when these change, and three of them
   change what OneAI does with money for everybody. **Submit Matching
   E-Invoices** lets OneAI post invoices to the books; **Household** stops
   every draft; **Audit What OneAI Does** off removes the second check.
   Recommended: **OneIntake Changed**, on the bell, to every other
   administrator, naming what was switched and by whom.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and **Is OneIntake set up well for us?**, read by a new
   `workspace_intake`: the settings, this month's numbers (handled, needed a
   person, undone), what waits now, and how often the floor sent things to a
   person. No AI call to read it.
3. **Intake**: this is Intake's own page. The month line answers nothing on
   its own: 13 needed a person, but which, and are they still waiting?
   Recommended: a **This Month** section (handled, needed a person, undone,
   waiting now), each number opening the Inbox on that box.
4. **Permissions**: the page is administrators'; `Intake Settings` is
   written by Workspace Administrator only. Holds. The sidebar group's
   Inbox, Deadlines and Spending are every desk user's, Ready to Submit
   the accounts and purchase roles', and Settings administrators'; frappe
   hides what a person cannot open.
5. **Cross-module**: Household and Submit Matching E-Invoices are OneBook
   decisions made here with no link to OneBook; Read Files Attached to
   Records reaches every module. Recommended: each says where it lands
   (Ready to Submit, Spending), as a link.
6. **UI and UX**:
   - a. **Empty fields that are not empty.** Most Pages Read and Confidence
     Floor show blank, but blank means 60 pages and 70% (`pipeline.py`,
     `act.py`). Quiet Minutes shows 0, which is its real value: OneAI acts
     at once. Recommended: the defaults written in, and each field saying
     what it does now ("60 pages", "70%").
   - b. **One flat list.** Eight settings of four kinds. Recommended:
     sections: What Is Read (attached files, most pages), How Sure (floor,
     audit), Filing (leave in place, quiet minutes), Books (household,
     submit e-invoices).
   - c. The month line is a violet badge. Recommended: the This Month
     section in 3, drawn as the page's own facts, not a badge.
   - d. "Confidence Floor" is a Percent field with no unit shown.
7. **Documented**: OneIntake's README describes each setting where it
   applies, but has no section for this page, so `how_to` cannot answer
   "what should the confidence floor be". Recommended: a section,
   OneIntake Settings, in `one_intake/README.md` (above Under the hood):
   each setting, its default, and who changes it.
8. **Legal**: the AI Addendum's `intake-acts` says OneAI files, links and
   *drafts*. With Submit Matching E-Invoices on, it also *submits* an
   invoice to the books, which the clause does not say. Recommended: the
   clause says a workspace may let it submit e-invoices from known
   suppliers that match an order, off unless switched on.
9. **Built from frappe**: the form is frappe's controls in a FieldGroup
   with Save in the page head, dirty-tracked and saved against the loaded
   values. Holds. It does not redraw when another administrator saves.

Your word: all of them, with switches instead of ticks, and cleaned up.

Done:

- **Switches.** Every on/off setting is frappe's Switch control, as
  frappe-ui draws one, the sentence beside it and the switch at the end.
- **Four parts.** What Is Read, How Sure OneAI Must Be, Filing and Books,
  each a heading and a line saying what it decides. Numbers sit in half a
  row rather than across the page.
- **Defaults written in.** Most Pages Read shows 60 and the Confidence
  Floor 70 where the record was empty, and the doctype now defaults to
  them.
- **This Month** is five numbers for everybody (arrived, handled by OneAI,
  needed a person, waiting now, undone), each opening the inbox on
  everybody's documents (`intake?box=…&everyone=1`), in place of the violet
  line.
- **Books** links to Ready to Submit and Spending.
- **Notice**: OneIntake Changed, on the bell, to every other administrator
  when the audit, household or submitting e-invoices is switched, or the
  floor moves ("Submit Matching E-Invoices on"). An empty floor saved as 70
  is not a change. Saving is against `modified`, so a second
  administrator's save since opening is refused; the page hears the record
  change through `opened`.
- **OneAI**: the page sentence, **Is OneIntake set up well for us?** and
  `workspace_intake`.
- **Legal**: the AI Addendum's `intake-acts` says OneAI drafts and does not
  submit, unless an administrator switches on submitting e-invoices, and
  what it then submits. AI Addendum revision 2.
- `one/README.md` has OneIntake Settings, for the Workspace;
  `one_intake/README.md` points to it.

Afterwards, on your word: OneIntake's settings that lived elsewhere are on
this page too.

- **Where OneAI Reads**: every mailbox, whether OneAI reads it and on whose
  behalf, and every OneCloud folder it reads, as lists. Starting one stays
  its holder's (OneAI then acts as them, `switches.py`); an administrator
  can stop any from here, and **Add a Folder** starts one. A person can
  still switch their own mailbox in OneMail and their own folders in
  OneCloud, since that is their consent rather than a workspace setting.
- **OneHR**: Screen New Applicants, Prepare Interviews, Transcribe
  Interview Recordings and Triage Grievances, still stored on HR Settings
  and hidden there, switched and saved here. Recording consent and how long
  audio is kept stay in HR Settings, which says where the rest went.
- OneCalendar, OneTask, OneProject, OneCRM, OneBook and OneInventory had no
  OneIntake settings to move.
- `workspace_intake` also reads which mailboxes and folders are read.

### Workspace › Holidays

The page is a Select of Holiday Lists ("One 2026"), **Open the List** and
**New List** buttons in the body, and a hand-drawn **Coming Up** list of
the next eight public holidays. Save sets `Company.default_holiday_list`.
The site has one list, One 2026: Friday off, the UAE's public holidays from
erpnext's `get_local_holidays`, made by the setup wizard, with a company
`Holiday List Assignment` from 1 January.

1. **Notifications**: changing the list sends nothing, though it moves
   everybody's leave, attendance and deadlines. HR Settings' **Holidays
   Coming Up** reminds each person of their own holidays; that holds.
   Nobody is told the list is running out (see 5b). Recommended:
   **Holidays Changed** on the bell to the other administrators and the HR
   managers, and **Holidays Run Out Soon** to the same people 60 days
   before the list's last day, when no list follows it.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence, and one suggestion, **Are our holidays ready for next year?**,
   read by `workspace_holidays` (the list, its last day, the next list if
   any, who is on a different list). No AI call to read it.
3. **Intake**: deadlines move past a public holiday (§ 193 BGB) using
   `Company.default_holiday_list`, whatever the date. A deadline in January
   2027 is counted against the 2026 list, which has no 2027 days.
   Recommended: Intake reads the list in force on the date (the
   assignments, as hrms does).
4. **Permissions**: the page is administrators'. `Holiday List` is written
   by HR Manager only, so an administrator without it opens **Open the
   List** read-only and gets refused on **New List**. Recommended: the page
   edits the list itself, under the administrator's own check, so the two
   agree.
5. **Cross-module**:
   - a. **Save does not reach OneHR.** hrms reads only a submitted
     `Holiday List Assignment` (`hrms.utils.holiday_list`), never the
     company field. Choosing another list here changes the OneHR calendar,
     Intake deadlines and ERPNext's reports, and leaves leave, attendance,
     shifts and check-ins on the old one. The two answers disagree.
     Recommended: Save also assigns the chosen list to the company, from its
     first day, as the setup wizard does.
   - b. **The year ends.** One 2026 ends on 31 December. From 1 January
     the 2026 assignment still holds, but its list has no days, so every
     Friday is a working day for leave and attendance and nothing warns.
     Recommended: **Next Year's List**, made from this one (same day off,
     the country's public holidays), assigned from 1 January; plus the
     notice in 1.
   - c. People or branches on another list (an employee's own assignment)
     are not shown. Recommended: the count, with a link to them.
   - d. OneCalendar's sidebar has a **Holiday List** entry that opens
     erpnext's desk list. Recommended: it opens this page.
6. **UI and UX**:
   - a. The page shows eight days of a list and cannot change any of them;
     every change is a trip to erpnext's Holiday List form. Recommended:
     the page is the list: its name and dates, the day off, the country,
     and the year's holidays as a table with add and remove, saved with
     the page's Save.
   - b. The list is a Select, not a Link, so there is no "create new" and
     no search.
   - c. Coming Up is hand-drawn rows. National Day shows twice, 2 and 3
     December, as two identical lines; names stay in Arabic for an English
     reader because they were written in the language the list was made in.
     "(تقديري)" (estimated) is how the package marks lunar dates and is
     worth keeping, as a badge.
   - d. **Open the List** and **New List** are buttons in the body.
7. **Documented**: there is no Holidays section in `one/README.md`, so
   `how_to` cannot answer "how do I add a holiday". Recommended: **Holidays,
   for the Workspace**.
8. **Legal**: nothing to add. The public holidays come from the `holidays`
   package, which runs on the server and sends nothing out.
9. **Built from frappe**: recommended: a Link control; the holidays as
   frappe's EmbeddedList (`onedesk.shell.table`); erpnext's own
   `get_weekly_off_dates` and `get_local_holidays` behind the buttons;
   saving against `modified`; and a redraw on `doc_update` when somebody
   else saves the list.

Your word: all of them. Two changes to the findings as they were built:
the notices go to administrators only, since the page is theirs and an HR
manager could not open it; and the names being in Arabic turned out to be
erpnext's bug, not the list's language.

Done:

- **Save reaches OneHR.** The page edits the list in force today, as hrms
  decides it (`one/holidays.py`, `in_force`). Choosing another list
  (**Use Another List**) submits a company `Holiday List Assignment` from
  today, or from the list's first day, and the company field follows it.
  A daily job keeps the field on the list in force, so erpnext's reports
  move to the new year on 1 January.
- **The page is the list.** Its dates and counts at the top (public
  holidays, weekly days off, the next holiday, the last day and how far
  off it is); **Day Off Each Week**, which remakes every such day on save;
  **Country** and **State or Region**; and the public holidays as frappe's
  own table, add, rename and remove, saved with the page's Save against
  `modified` and redrawn when somebody else saves the list. **Add the
  Country's Public Holidays** adds what the country has that the table
  lacks, without saving. **Open the List** and **New List** are gone.
- **Next year.** **Make Next Year's List** in the page head makes it from
  this one (same day off, the country's public holidays) and assigns it
  from 1 January; the page then opens it (`?list=`), with a line saying
  when it starts and **Back to** this year's. Under 90 days from the end
  with nothing after it, the page says so above everything, with the same
  button.
- **Notices**: **Holidays Changed** on the bell to every other
  administrator, naming what was added, removed or renamed, or the new day
  off; **Holidays Run Out Soon** on the bell and by mail 60, 30 and 7 days
  before the list ends with no list after it.
- **Holidays in the reader's language.** erpnext's `get_local_holidays`
  passes frappe's `en`; the `holidays` package knows English as `en_US`, so
  it fell back to the country's own language. `holidays.local` picks the
  package's own code, and the setup wizard uses it. A patch renames the
  names nobody changed into the workspace's language: One 2026 reads
  "National Day", with lunar dates marked "(estimated)".
- **Intake and OneCalendar read by date**: deadlines count days off from
  every list the company has had, and the calendar shows each holiday from
  the list in force on its day. OneCalendar's sidebar no longer has
  erpnext's Holiday List; the page is One › Workspace › Holidays.
- **People on Their Own List** shows when anybody has an assignment of
  their own, and opens them.
- **OneAI**: the page sentence, **Are our holidays ready for next year?**,
  and `workspace_holidays`, which also lists what the country has that the
  list lacks. No AI call.
- `one/README.md` has Holidays, for the Workspace.

Afterwards, on your word: days off of more than one day, and changing the
holidays by asking.

- **Days Off Each Week** is frappe's MultiCheck, a tick per weekday, so a
  weekend of two (Saturday and Sunday, or Friday and Saturday) is two ticks.
  erpnext keeps one `weekly_off`; saving runs its `get_weekly_off_dates` once
  per day ticked (`holidays.set_days_off`), and the page reads the ticks
  back from the rows (`days_off`). Next year's list keeps them.
- **Ask OneAI**: `change_holidays` suggests a card an administrator
  approves: days added or renamed ("15 November, Founders Day"; a closure is
  a day each), days removed, and the days off. The card lists each change
  and what it was. Approving runs the page's own save as the approver, so
  the same notice goes out, and it is refused as stale if the list changed
  since. A date goes on the list whose year holds it; a date no list holds
  is refused with where to make next year's. A new proposal kind,
  **Holidays**, beside Customize and Signature.

## Products

### One › Home

Home is the `One` workspace: a header that says "One" (the page title
already does) and a `One Onboarding` block that draws nothing, because the
Getting Started panel floats in the corner instead. The rest of the page is
empty. OneCRM, OneHR and OneBook each have a home made of frappe's
workspace blocks (shortcuts, number cards, quick lists); One, where
everybody lands and where every product meets, has none.

1. **Notifications**: Home sends nothing, and needs to send nothing. What
   is waiting for a person is scattered over the bell, the OneIntake inbox,
   OneAI's cards, approvals and tasks, and Home gathers none of it.
2. **OneAI**: the panel does not know the page. Recommended: the page
   sentence and **What needs me today?**, read by a new `my_day` (the
   numbers in 5, and the first few of each). No AI call to read it.
3. **Intake**: what waits for this person in the OneIntake inbox is not on
   Home. Recommended: a number for it, opening the inbox on Waiting.
4. **Permissions**: the workspace is public with no roles, so everybody
   sees it. Holds. Recommended: each block counts only what the reader may
   open (`frappe.get_list`), and the workspace part in 5 shows only to
   administrators.
5. **Cross-module**: Home is where the products meet, and nothing meets
   here. Recommended, for everybody, **Today**, one number each, each
   opening its list:
   - tasks due today or late (OneTask's My Tasks);
   - meetings today (OneCalendar);
   - documents waiting for them (OneIntake);
   - OneAI suggestions waiting for their approval;
   - approvals waiting on them (leave, expense claims, where they approve).
   For administrators only, **The Workspace**, shown only when something
   needs them: a mailbox not connecting, a domain not working, credits
   running low, storage or seats nearly full, the holiday list ending.
6. **UI and UX**: a blank page with a heading repeating the title. The
   Getting Started panel (Set One up, 0 of 4) is the only thing on it, and
   it floats. Recommended: the two parts in 5 as the page; the "One"
   heading goes.
7. **Documented**: `one/README.md` has no Home section. Recommended:
   **Home**, saying what each number counts and who sees the workspace part.
8. **Legal**: nothing to add. Home only counts what the products already
   hold.
9. **Built from frappe**: the workspace is frappe's, and its blocks should
   stay frappe's: each number a `Number Card` of type Custom (a whitelisted
   method that counts for the reader), and the workspace part a
   `Custom HTML Block`, so the page stays editable in frappe's workspace
   editor.

Your word: build it.

Done:

- **Today**, for everybody: five of frappe's `Number Card`s of type Custom,
  each a method in `one/home.py` that counts for the reader and says where
  a click goes. Tasks Due or Late (OneTask's own `mine.tasks`, overdue and
  today) opens My Tasks; Meetings Today (OneCalendar's `events.mine`) the
  calendar; Documents Waiting (OneIntake's `inbox.counts`) the inbox on
  Waiting; OneAI Suggestions the reader's proposals still Proposed; and
  Approvals Waiting, leave and expense claims where the reader is the
  approver, the list with most of them.
- **The Workspace**, for administrators: a `Custom HTML Block` (`One Needs
  You`, a fixture) limited to Workspace Administrator, filled by
  `home.attention`. It reads only what the workspace keeps (the account's
  copy, its mailboxes, its holiday list), draws each as espresso's yellow
  alert linking to where it is fixed, and hides itself when nothing needs
  them. The thresholds are the notices' own (`account.LOW`,
  `account.NEARLY_FULL`).
- The "One" heading and the empty onboarding block are gone; Getting
  Started stays where it floats.
- **OneAI**: the page sentence, **What needs me today?** and `my_day`.
- `one/README.md` has **Home**.
- Checked with a mailbox made to fail for a moment: the block showed it,
  and went when it was cleared.

### OneMail

OneMail is its own page (`public/js/onemail.js`): the mailboxes and their
folders on the left, the conversations in the middle, the reading pane on
the right, and frappe's own email window for writing. All nine of its
README's stages are built; the README says the AI lane waits.

1. **Notifications**: one type, **Mailbox Not Reachable**, to everybody who
   holds the mailbox, once, when it breaks. New mail is the rail's count,
   not a notice. Holds.
2. **OneAI**: the panel knows nothing on this page: no page sentence, no
   suggestions, nothing it can read about the open conversation. The one
   OneAI part is OneIntake's, below. Recommended:
   - the page sentence, naming the mailbox, the folder and the open
     conversation (only one the reader holds);
   - `open_conversation`, reading its messages as text, as the reader;
   - three suggestions: **Summarise this conversation**, **Draft a reply**
     (a card whose Approve opens frappe's email window with the reply
     written in, never sent by itself), and in a folder **What needs an
     answer?** (conversations whose last message is not ours, oldest
     first).
3. **Intake**: a mailbox's ⋯ menu has **Read with OneAI…**, asked of its
   holder, and each message OneAI read carries its panel (`.om-intake`).
   OneIntake Settings lists every mailbox. Holds.
4. **Permissions**: a message opens only for the people who hold its
   mailbox (`access.allowed`), filing it on a record never widens that
   (`linking.py`), and nobody sees into anybody's own mailbox,
   administrators included. Holds.
5. **Cross-module**: mail is filed on the customer, supplier, employee,
   lead or document it is about, with a Mail tab on each; attachments live
   in OneCloud; faces and logos come from contacts. Holds.
6. **UI and UX**:
   - a. The page is titled **Mail**; the product is OneMail.
   - b. **Reply, Reply all and Forward are there twice**: as icons in the
     conversation's head and as buttons under the last message.
     Recommended: the buttons under the message stay (where the eye is when
     it finishes reading); the head keeps star, read, move, archive, delete
     and link.
   - c. **A folded message runs its lines together**: "Hello,Please find
     our quote attached.Rana". `api.snippet` strips the HTML without
     leaving a space where a paragraph or line ended.
   - d. **Every mailbox is open**, six folders each: three mailboxes already
     fill the column. Recommended: the open mailbox unfolded, the others
     folded to their name and unread count, and what a person folds stays
     folded.
   - e. A mailbox's name is its address, cut off
     ("member.probe9x@m.4dl…."). The workspace's says **Workspace** with the
     address under it; recommended: the reader's own says **Yours**, a
     shared one its name, each with the address under it.
7. **Documented**: `one_mail/README.md` is the manual above Under the hood
   and OneAI answers from it. When the AI part in 2 is built, it gets its
   paragraph.
8. **Legal**: the clauses and subprocessors cover mail, OneCloud and faces.
   Asking OneAI about a conversation sends its text to the model, which the
   AI Addendum must say: recommended, a clause in `one_mail/legal.py`
   (only when asked, only a conversation the asker holds, nothing kept).
9. **Built from frappe**: writing is frappe's email window, dates are
   `frappe.datetime`, a new message redraws an open mailbox through
   `frappe.realtime` (`live.py`), and buttons are espresso's. Holds.

Your word: all of them, and a reply drafted from what we tell it ("turn
down their offer", "we agree only if…").

Done:

- **OneAI** (`one_mail/ai.py`): the page sentence names the mailbox, the
  folder and the open conversation, only one the reader holds. Two
  readers, `open_conversation` and `waiting_for_answer`, and a suggest,
  `draft_reply`. Three suggestions: **Summarise this conversation**, **What
  needs an answer?**, and **Draft a reply**, a new kind of suggestion
  (`fill`) that puts "Draft a reply to this conversation that says:" in
  the panel's box for the reader to finish with what the reply should say.
  The reply comes back as a card (a new proposal kind, **Reply**) showing
  it in full; **Approve** opens frappe's email window with it written in,
  addressed and quoted as Reply opens it (`OneMail.reply_to`), to be read,
  changed and sent by the reader. Nothing is sent by OneAI.
- **Legal**: the AI Addendum's `onemail-asks` says a conversation's text
  goes to the model only when asked, only from a mailbox the asker holds,
  and that a drafted reply is never sent by OneAI. AI Addendum revision 3,
  so administrators agree again.
- **The title** is OneMail.
- **Reply, Reply all and Forward** are under the last message only; the
  head keeps star, read, move, archive, delete and file.
- **A folded message** keeps a space where each paragraph or line ended.
- **Mailboxes fold**: only the one open is unfolded, a folded one shows
  its unread count, and what a person folds or unfolds is kept in frappe's
  user settings (not the browser, which the borrowing guard refuses).
- **Mailbox names**: **Workspace**, **Yours** or a shared one's address,
  each with its address under it.
- `one_mail/README.md` has **Asking OneAI**; the line saying the AI lane
  waits is gone.
- Checked without a model: every reader and the card on the dev site, the
  chip filling the box, and Approve's email window with the reply in.

Then, on your word: **mail when storage is full**. Before, an attachment
the store refused failed the whole message, and it was lost. Now:

- The message always arrives. Each attachment is saved on its own
  (`inbound.Arrival.save_attachments_in_doc`, a savepoint each); one the
  store refuses as full (`store.NoRoom`, from the admin site's `NoRoom`) is
  written on the message (`one_unsaved`) instead.
- The reading pane shows it as an amber chip, **Not saved, storage is
  full**.
- **Attachments Not Saved**, a new notification type, to every
  administrator and everybody who holds the mailbox, once a day at most,
  linking Plan and Credits.
- `one_mail/room.py` `again`, hourly, reads the message back (from R2 on
  the workspace's address, from the server on a connected mailbox), saves
  what now fits and clears the mark.
- `README.md` says so under Attachments and faces.
- Checked on the dev site: a message arriving to a full store kept its text
  with the attachment marked and told both people; the hourly run saved it
  and the chip became the file.

Then, on your question "does writing an email have AI text tools": it did
not. Forms have the OneAI mark on every prose field, but the email window
is a dialog, so it never got one. Now (`oneai.js` `compose`):

- The mark sits beside **Message** in frappe's email window, wherever it is
  opened. It points the panel at Communication's own `content` field, so it
  is the same check (`touch.target`), the same card and the same Approve.
- The panel offers Improve it, Make it shorter, Make it longer, Make it
  more formal, Make it friendlier, Fix spelling and grammar, and
  Translate… (finished in the box). On an empty reply, Write a first draft
  and Reply saying….
- The model gets what is written, the subject, the recipients and the
  message replied to (`touch._email`), never the signature. Approve
  replaces only what was written; the signature and the quote stay
  (`oneai.parts`, `oneai.rewrite`). Nothing is saved on the server.
- The panel sits above the window's backdrop, and on a wide screen the
  window moves left to make room.
- Legal: `onemail-asks` says what goes to the model; AI Addendum
  revision 4.
- README: under Asking OneAI. Checked in the browser without a model: the
  mark, the chips, and a card applied into the window with the signature
  and quote kept.

### OneCloud

OneCloud is its own page (`public/js/onecloud.js`, 2,145 lines): an
explorer with a tree on the left (My Files, Recent, Starred, Shared with Me,
Libraries, Company, Records, Mail, Network, Requests, Recycle Bin), the
folder in the middle, and a preview pane with details and activity on the
right. The same explorer opens as a record's Files tab and as the picker.

1. **Notifications**: nine types. Shared with you, added to a library,
   file requests (sent, reminded, answered, complete), uploads through a
   link, a link shared with an address, and its code. Storage Nearly Full
   is One's, and Attachments Not Saved is OneMail's. They read well. Holds.
2. **OneAI**: the panel knows only that this is "Files": no page sentence,
   no suggestions, nothing about the open folder or the selected file. The
   only OneAI part is OneIntake's **Read with OneAI…** on a folder.
   Recommended:
   - a page sentence naming the open folder and the selected file (only
     what the reader may open);
   - a reader, `open_file`, that reads a text, PDF or office file's text as
     the reader;
   - suggestions: with a file selected, **Summarise this file** and **Who
     can see this?**; in a folder, **Find a file…** (a fill chip, "Find the
     file that…", searched by meaning through OneIntake's search) and
     **What is taking the space?**.
3. **Intake**: **Read with OneAI…** turns reading on for a folder, and a
   file OneAI read carries its panel. But the item is on every file's menu
   too, greyed out, because it only works on a folder. **Connect as a
   drive…** is the same. Recommended: hide what cannot apply to a file,
   and on a file offer **Read with OneAI** once, for that file.
4. **Permissions**: My Files is the owner's; Shared, Libraries and Company
   follow their members and roles; anybody on the team may connect a
   server under Network, for themselves or shared with the team, and only
   its owner or an administrator changes it; Storage Check is for
   administrators; a record's files follow the record. Two leaks:
   - **Records counts every file of a type**, not what the reader may
     open: "Employee 3" shows to somebody who may open one employee. The
     list under it is filtered (`get_list`); the count is not
     (`record_doctypes`). Recommended: count what they may read, or show no
     count.
   - **Records lists AI Chat and ToDo**: a OneAI conversation's uploads
     and an assignment's are not "records" anybody files by. Recommended:
     add both to `UNLISTED`.
5. **Cross-module**: mail attachments are under Mail, record files under
   Records, OneWriter and OneWorkbook open from here, and OneIntake reads
   folders. Two gaps:
   - **New has no Document or Workbook**: only folder, upload and file
     request. Recommended: **Document** and **Workbook** in New, made in
     the open folder and opened in their window.
   - Record types show their doctype names ("ToDo", "AI Chat"); the rest
     of One calls them what the product calls them.
6. **UI and UX**:
   - a. The page is titled **Files**; the product is OneCloud (as Mail was
     for OneMail).
   - b. With nothing selected, the preview pane is a large empty column
     saying "Select a file to preview it." Recommended: the folder's own
     details there (items, size, who can see it, reading on or off), which
     is what Windows and Drive show.
   - c. Requested files land in a folder named after the sender's address
     ("vendor@example.org") in the folder the request was made in, so My
     Files fills with email addresses. Recommended: one folder per request,
     named after it, with a folder per sender inside it named by their
     name.
7. **Documented**: `one_storage/README.md` covers finding your way,
   sharing, libraries, versions, the drive, servers, requests and limits.
   Nothing says what OneAI does here (Read with OneAI is not mentioned).
   Recommended: an **Asking OneAI** section, with 2 and 3.
8. **Legal**: R2 is a subprocessor and `onecloud-files` says where files
   are kept. Not said anywhere: that files can be shared outside the
   workspace by link, and that people outside can upload through a file
   request, so the workspace holds what third parties send. Also that a
   connected server's password is kept, encrypted, to reach it. Recommended:
   a clause `onecloud-outside` in the privacy notice, and, if 2 is built,
   a line in the AI Addendum that a file's text goes to the model when
   asked.
9. **Built from frappe**: dialogs are `frappe.ui.Dialog`, and changes
   arrive through `frappe.realtime` (`doctype_subscribe("File")`,
   `onecloud_change`). But the desk ships parts this page draws by hand:
   - the right-click menu is ours (`menu()`), and frappe has
     `frappe.ui.ContextMenu`;
   - the New menu is ours, and frappe has `frappe.ui.Dropdown`;
   - every toolbar button is hand-written `es-button` markup rather than
     `frappe.ui.button.html`;
   - the crumbs are hand-written `es-breadcrumbs` rather than
     `frappe.ui.breadcrumbs`;
   - the empty preview is ours, and frappe has `frappe.ui.empty_state`;
   - the search box is a bare `<input>` rather than a frappe control.
   The path box and the rename-in-place box are explorer parts frappe has
   no equivalent for, so they stay ours, drawn like a frappe-ui TextInput.
   Recommended: move each of the six onto frappe's part.

Your word: all of them.

Two findings were wrong, and are corrected here rather than built:
- **New › Document and Workbook** cannot be built yet: OneWriter and
  OneWorkbook are not rebuilt in OneDesk (only their marks are here), so
  there is no window for a new document to open in. It waits for them.
- **The empty state** was already frappe's (`onedesk.shell.empty` is
  `frappe.ui.empty_state`).

Done:

- **OneAI** (`one_storage/ai.py`): the page sentence names the open folder
  and the chosen file, only what the reader may open (`OneCloud.here`,
  sent by `oneai.where` as the page's folder and record). Three readers:
  `open_file` (what OneIntake read of it, or read now; a scan says to use
  Read with OneAI), `who_can_see` (owner, people, through a folder, links
  without their key) and `largest_files` (the reader's own, and how full
  the workspace is). Suggestions: in a folder **Find a file…** (a fill
  chip, searched by `find_documents`) and **What is taking the space?**;
  with one file chosen (section `file`) **Summarise this file**, **Who can
  see this?** and **Find a file…**. An open panel is told when the chosen
  file changes.
- **Intake**: folder-only rows are no longer shown on a file. A file has
  **Read with OneAI**, which reads that one file now as the person asking
  (`switches.read_now`, `pipeline.read_file(person=)`); a message's
  attachment is read with its mailbox.
- **Records** counts only files on records the reader may open
  (`_readable_files`, through `get_list`), and no longer lists AI Chat or
  ToDo.
- **File requests** make a folder of their own named after the request,
  where they were made, with a folder per person named by their contact's
  or user's name (`_where`, `_called`).
- **The title** is OneCloud.
- **The preview pane**, with nothing chosen, shows the folder: its folders,
  files and size, and for a folder of ours its owner, who it is shared
  with and whether OneAI reads it.
- **Frappe's parts**: the right-click menu is `frappe.ui.ContextMenu`, New
  is `frappe.ui.Dropdown`, every button (toolbar and dialogs) is
  `frappe.ui.button.html`, Details or Tiles is `frappe.ui.tab_buttons`, the
  crumbs are `frappe.ui.breadcrumbs`, and the search box is a frappe Data
  control through a new shared `onedesk.shell.search` (OneMail's box can
  move onto it next). The hand-drawn menu and its CSS are gone.
- **Legal**: `onecloud-outside` in the Privacy Policy (links, file
  requests, a connected server's password), revision 5; `onecloud-asks`
  in the AI Addendum, revision 5.
- **README**: an **Asking OneAI** section; the request folders.
- A guard, `tests/test_onecloud_ai.py`. Checked in the browser: the title,
  the folder pane, a file's and a folder's menus, New, the panel's
  suggestions with a file chosen, Records; `open_file` read a fresh file
  on the dev site. No model was called.

### OneCalendar

OneCalendar is its own page (`one_calendar/page/onecalendar`): the layers on
the left in two groups, Mine and Workspace, and frappe's own FullCalendar on
the right with Month, Week, Day and List. Every dated thing in One is a
layer read as the reader (`layers.py`); nothing is copied. Add Event makes a
frappe Event, Subscribe gives a private link for Google, Apple or Outlook,
and a record's own calendar is the same page with `?doctype=&name=`.

1. **Notifications**: One sends nothing about events.
   - Nobody is told they were invited, or that an event they are on moved
     or was cancelled.
   - The only mail is frappe's own morning digest, "Upcoming Events for
     Today" (`send_event_digest`). It goes around One's notification hub,
     in frappe's template, and it leaves out events you are only invited
     to (frappe's `get_events`). Settings calls it "Mails you before an
     event of yours starts", which it does not do.
   - frappe's Event has a reminders table (a notification some minutes
     before), but nothing sends it.
   Recommended: four types in `one_calendar/notifications.py`, through the
   hub: **Invited to an Event** (to each person added, with when and where),
   **Event Changed** (its time or place, to everybody on it), **Event
   Cancelled**, and **Starting Soon** (from the event's reminders, default
   ten minutes before, as a push and in the bell). And the morning digest
   as One's own **Today's Events**, from `events.mine`, replacing frappe's.
2. **OneAI**: the panel knows only that this is "Calendar": no page
   sentence, no suggestions, nothing it can read. Recommended:
   - a page sentence naming the days shown (and the record, on a record's
     calendar);
   - a reader, `my_calendar(start, end)`, which is `layers.entries` as the
     reader;
   - a reader, `busy_times(people, start, end)`, when colleagues are busy
     and never what the event is;
   - a suggest, `plan_event`: a card that makes the event when approved;
   - suggestions: **What is on this week?**, **Find a time to meet…** (a
     fill chip, "Find a time this week to meet "), and **Plan my day**.
3. **Intake**: an invitation OneIntake reads (an `.ics` in mail or a file)
   becomes an event shared with the person it is for (`planning.make_event`),
   and OneIntake's deadlines are a layer. Holds.
4. **Permissions**: each layer reads as the reader; an event about a record
   is seen by the record's readers and opens the record; Public is kept to
   Workspace Administrator and HR Manager on save (`events.validate`);
   Who's Off needs leave to be readable. Holds.
5. **Cross-module**: tasks, projects, deals and leads, leave and
   interviews, maintenance, and OneIntake's deadlines are all layers; a
   project, deal, lead or employee has a Calendar button. Two gaps:
   - **The workspace's days off are not on it**: Holidays shows the
     holiday list without the weekly days off, and a weekend looks like any
     other day. Recommended: holidays and weekly days off drawn as a shaded
     background, as the desk shades non-working hours.
   - **An event has no people from the calendar**: inviting somebody means
     opening the event's own form. Recommended: **Invite** in Add Event
     (team members by name, shared with them; outside guests by address,
     as participants), and outside guests mailed an invitation with the
     `.ics` so it lands in their own calendar.
6. **UI and UX**:
   - a. The page is titled **Calendar**; the product is OneCalendar.
   - b. **Clicking an event leaves the calendar** for frappe's Event form.
     Recommended: a small card on the event (`frappe.ui.Popover`) with
     when, where, who, the description, a Join link when there is one, and
     Open and Delete; the form stays one press away.
   - c. The page does not update while it is open: an event somebody adds
     or moves appears only on reload.
7. **Documented**: `one_calendar/README.md` is the manual above Under the
   hood and OneAI answers from it. When 1, 2 and 5 are built they get their
   paragraphs.
8. **Legal**: `calendar-link` covers the subscription. Not said: that
   frappe's **Google Calendar** connection (Setup) sends events to the
   Google account it is connected to, both ways, and a Meet link is made by
   Google. Recommended: a line in `calendar-link`'s document, and, if 2 is
   built, the AI Addendum says a calendar is read when asked, and that busy
   times are read without what they are.
9. **Built from frappe**: FullCalendar is the one frappe bundles, the
   toolbar is the desk calendar's own (`frappe.ui.button`,
   `frappe.ui.TabButtons`, `frappe.ui.Popover` date jumper), Add Event is a
   `frappe.ui.Dialog`, and the layers and view are frappe user settings.
   Two things are not:
   - **the layer switches are bare `<input type="checkbox">`**, and
     frappe's Check control is the part;
   - **nothing listens on `frappe.realtime`** (6c): frappe's
     `doctype_subscribe("Event")` and `list_update` are how a screen hears
     of a change.

Your word: all of them, and one sidebar, as OneMail has.

Done:

- **One sidebar**: the page hides the rail (`hide_sidebar`), as OneMail
  does, and its left column is the navigation: **New Event** on top, the
  layers, and at the foot **All Events**, **Deadlines**, **Subscribe**, and
  **Setup** (Google Calendar, Calendar Links) for those who may read them.
  The rail still leads to the list and setup pages themselves.
- **Title**: OneCalendar (page and its record).
- **Layers** are frappe's Check control, each with its colour.
- **Live**: `frappe.realtime.doctype_subscribe` on Event and every layer's
  doctype; a `list_update` draws the calendar again.
- **Days off**: holidays and weekly days off as a background, from the list
  in force on each day (`layers.days_off`); a holiday carries its name.
- **The card**: clicking an event opens a `frappe.ui.Popover` with the time
  clicked (a repeat's, not its first), where, who made it, who is on it and
  their answer, what it says, **Join** for a video call, **Open**, and
  **Delete** for whoever may. Anything else opens its record.
- **Invite and Guests** in New Event (`events.make`): team members by name
  (frappe's MultiSelectPills), guests by address; both are frappe's own
  participants, a guest a Contact. Addresses may also ride in on Event's new
  hidden `one_guests`, which is how OneAI's card carries them.
- **Notifications** (`one_calendar/notifications.py`, `tell.py`): Invited
  to an Event, Event Changed (time or place), Event Cancelled (cancelled or
  deleted), Starting Soon (the event's own reminders, else ten minutes
  before, every five minutes, once per time), and Today's Events each
  morning from the reader's own calendar. Guests are mailed **Event
  Invitation** with an `.ics` (METHOD REQUEST or CANCEL, a growing
  SEQUENCE, the repeat as RRULE). frappe's morning digest is stopped on
  migrate, and its "Event Reminders" switch is gone from Settings.
- **OneAI** (`one_calendar/ai.py`): the page sentence (and a record's
  calendar by name), `my_calendar` (the page's own merge, with days off),
  `busy_times` (times only, never what), and `plan_event`, a Create card
  whose Approve makes the event and invites its people. Suggestions: What
  is on this week?, Find a time to meet… (fill), Plan my day.
- **Legal**: `calendar-guests` in the Privacy Policy (guests kept as
  contacts and mailed; the Google Calendar connection), revision 6;
  `onecalendar-asks` in the AI Addendum, revision 6.
- **README**: the column, days off, invites and guests, the card, Being
  told, Asking OneAI, and Under the hood.
- Checked on the dev site: an invite, a change and a delete told the right
  people; Starting Soon came ten minutes before; the guest's mail carried
  the `.ics`; OneAI's card, approved, made the event with a colleague and a
  guest. In the browser: the column, the card, New Event and the panel's
  suggestions. No model was called.

Your word, after: the New Event dialog wanted polish, and so did any dialog
an earlier pass left as one long column.

Done:

- **New Event**: laid out with frappe's own Section and Column Breaks.
  Subject; Starts On and All Day beside Ends On; Location beside Invite;
  Guests; and a collapsed **More** with the description and, for whoever
  may publish, On Everybody's Calendar.
- **OneCloud's Create link**: Can download beside Can upload, Expires on
  beside Password.
- **OneCloud's Connect a server**: Name and Server beside Kind and Port,
  the folder, **Sign In** (user name beside password), and a collapsed
  **Sign In With a Key**. A frappe dialog hides a section whose fields all
  have `depends_on`, so the key has none and says it is for SFTP.
- **Ask for files** said files land in the folder asked from; they land in
  a folder of their own there, named after the request, one per person
  when several are asked. The note now says so.
- Checked and already right: Connect a mailbox (OneMail) and Ask for files
  were laid out with breaks. Every other dialog from the passes holds one
  to four fields and needs none.

### OneTask

OneTask is where a person's work is kept, and all of it is ERPNext's Task: a
to-do of one's own is a task in no project, a step in a project is a task in
it. The dock opens it on **My Tasks** (`one_task/page/my_tasks`): what is
assigned to the reader and still to do, in frappe tables grouped Overdue,
Today, Tomorrow, Next 7 Days, Later and No Due Date, with a quick add at the
top, a tick to complete and a timer that writes the week's timesheet. The
rail has My Tasks, Inbox (one's own tasks in no project), Tasks (frappe's
list) and Setup. Projects are OneProject's, over the same tasks, and
OneTask is the door to them.

1. **Notifications**: OneTask sends nothing of its own. frappe's do the work,
   and they fall short.
   - Being given a task reads "Samir Aoun assigned a new task **Task**
     *Write the home page copy* to you": "task Task", no due date, no
     project, in frappe's mail.
   - **Nobody is told a task is done.** Checked on the dev site: Rania
     completed a task Samir gave her, and Samir heard nothing.
   - Nothing reminds anybody of what is due. Today's Events, OneCalendar's
     morning note, lists events only.
   Recommended: three types in `one_task/notifications.py`, through the hub.
   **Task Given** replaces frappe's line for a task, and says who, the
   task, when it is due and its project. **Task Done** goes to whoever gave
   the task and whoever made it, when somebody else completes it.
   **Today's Tasks** goes each morning with what is due that day and what
   is overdue, from My Tasks, and is not sent on a day with nothing.
2. **OneAI**: the panel knows only that this is "My Tasks": no page
   sentence, no suggestions, nothing it can read or add. Recommended:
   - a page sentence naming the view shown (My Tasks, the Inbox, or a
     project's tasks);
   - a reader, `my_tasks`, which is `mine.tasks` as the reader, with each
     task's project and what it is about;
   - a suggest, `plan_task`: a card that adds a task when approved. It can
     have a due date, a project, a checklist, and a colleague to give it
     to;
   - suggestions: **What should I do first?**, **Add a task…** (a fill
     chip), and **Break a task into steps…**.
3. **Intake**: the tasks OneIntake makes land on My Tasks, assigned to the
   person they are for (`planning.py`), with the record they are about in
   `one_about` (a supplier, a party). **My Tasks does not show what a task
   is about**: "Decide whether to cancel" appears with nothing beside it.
   Recommended: the About link where the project would be.
4. **Permissions**: `access.py` holds. One's own tasks are theirs. A
   project's tasks are seen by the project's readers. Somebody given a
   task may do it but not delete it. The page runs as the reader, and
   ticking a task is frappe's own save. Nothing to change.
5. **Cross-module, and the door to OneProject**: My Tasks names each
   task's project, and the name opens the project. There is no way from
   OneTask to one project's tasks, though. "What is left on Website
   Relaunch" means OneProject › Projects › the project › its board.
   Recommended: the projects the reader is on, listed in OneTask's column,
   each opening that project's open tasks on the same page, grouped by due
   date, with **Open Project** leading to OneProject. The quick add then
   adds to the project shown. The calendar (drag to move) and the timer
   (the week's timesheet) hold.
6. **UI and UX**:
   - a. **Two sidebars.** My Tasks has the rail's four entries beside it,
     as OneCalendar had. Recommended: one column, as OneMail and
     OneCalendar have. **Add Task** on top; My Tasks, Inbox and All Tasks
     with counts; the reader's projects; Setup (Task Type) at the foot.
   - b. **The Tasks list is cramped**: the subject is cut to ten letters,
     while an ID column and two checkbox columns (Is Group, Is Milestone,
     ERPNext's `in_list_view`) take the room. Recommended: Subject, Status,
     Project, Priority and Due.
   - c. **A task's due date is hidden**: it is in the collapsed Timeline
     section. The Details tab opens instead on Issue, Weight, Type, Color,
     Is Group and Is Template, ERPNext's planning fields. Recommended:
     Timeline open, and Weight, Color and Issue folded into it rather than
     ahead of it. Company goes off More Info, as it has everywhere else.
   - d. My Tasks does not update while it is open: a task somebody gives
     you appears only on reload.
7. **Documented**: `one_task/README.md` is the manual above Under the hood
   and OneAI answers from it. When 1, 2, 5 and 6a are built they get their
   paragraphs.
8. **Legal**: nothing about a task leaves the workspace, and the timer
   writes only the person's own timesheet. If 2 is built, the AI Addendum
   says a person's tasks are read when they ask, and that a task is only
   added when they approve the card.
9. **Built from frappe**: the groups are frappe tables (the shell's
   EmbeddedList), the quick add is frappe's Data and Date controls, the
   badges are `frappe.ui.badge`, and a task is added and ticked through
   `frappe.db`. The tick is a bare checkbox, as frappe's own list rows
   draw theirs (`list-row-checkbox`), so it stays. Not frappe: **nothing
   listens on `frappe.realtime`** (6d). `doctype_subscribe("Task")` and
   `list_update` are how a screen hears of a change.

Your word: all of them but the door. OneTask and OneProject stay two
things. OneTask is one person's work from everywhere, and OneProject is a
team running a project. They share the task, so a project's task given to
you is on My Tasks, and its project's name opens OneProject. That is the
whole of the seam. OneTask lists no projects.

Done:

- **One sidebar**: the page hides the rail, as OneMail and OneCalendar do.
  Its column has **Add Task**; **My Tasks** (how many, and how many late,
  in red) and **Inbox** (how many); and at the foot **All Tasks** and
  **Setup** (Task Type). The open view is `?section=inbox`, which is how
  OneAI knows it. Title: OneTask.
- **Live**: `doctype_subscribe` on Task and ToDo, so a task given, saved
  or ticked elsewhere is drawn again. Checked with a second tab.
- **About**: a task in no project names what it is about and opens it
  (OneIntake's supplier tasks). The column is **Project or About**. A late
  task says how long ago it was due.
- **The Tasks list**: Subject, Status, Project, Priority and Expected End
  Date. frappe's ID column is off (`hide_name_column`), and so are Is
  Group and Is Milestone.
- **A task's page**: Timeline is open, straight after what the task is,
  with the due date in it. Is Template, Issue and Color follow it, and
  Company is hidden.
- **Notifications** (`one_task/notifications.py`, `tell.py`):
  - **Task Given** is frappe's own assignment line said in ours: who, the
    task, the due date and the project. A Notification Log
    `before_insert` turns it, since frappe writes it with no switch.
  - **Task Done** goes to whoever gave the task and whoever made it,
    unless they completed it themselves.
  - **Today's Tasks** goes each morning at 06:40, with what is due and
    what is late, and is not sent on a day with nothing due.
  Checked on the dev site: Samir gave Rania a task, she was told in
  ours, she completed it, and Samir was told.
- **OneAI** (`one_task/ai.py`): the page sentence (My Tasks or the Inbox),
  `my_tasks`, `plan_task` and `plan_steps`. `plan_task` is a Create card
  with a due date, a project, a checklist, and colleagues on the hidden
  `one_for`, who are given the task on approval. `plan_steps` is an Edit
  card that keeps the steps a task has. Suggestions: **What should I do
  first?** and **Add a task…**, and on a task **Break this into steps**.
  Checked by calling the tools and approving the cards; no model was
  called.
- **Legal**: `onetask-asks` in the AI Addendum, revision 7. OneLegal asked
  for agreement to it again on the next visit, as it should.
- **README**: the column, the About column, the task's page, Being told,
  Asking OneAI, and Under the hood.

### OneAdmin › Home

OneAdmin is the operator's console, and only on the admin site
(`"one_admin": 1` in site_config) and for One Operator. Its rail has 15
entries: Home, Workspaces, What is happening (Jobs, Log, Domains), Selling
(Price List, Price Check, Plan Calculator, Signups, Credits), OneAI (Models,
AI Usage) and Settings. They are taken one screen at a time, Home first.

Home is frappe's own Workspace (`one_admin/workspace/one_admin`), headed
"Right now". It has four number cards: Workspaces (live), Building, Owing
and Stuck. Below them are three quick lists: Stuck jobs, Owing, and Domains
waiting. On the dev site these show 6, 1, 1 and 1, one stopped job (PROV-26-00012), Gone Ltd
suspended, and no domain waiting.

1. **Notifications**: OneAdmin tells the operator nothing. Nothing in
   `one_admin` calls the hub. A job that fails, a signup that arrives, a
   payment that fails or a domain that never checks in is found only by
   opening Home. Recommended: operator-only types (roles One Operator) in a
   new `one_admin/notifications.py`:
   - **Job Failed**, with the step and the error;
   - **New Signup**, with the company and the plan;
   - **Workspace Owing**, when a workspace falls overdue and when it is
     suspended;
   - **Domain Waiting**, when a domain has not checked in after a day.
2. **OneAI**: the panel knows only that this is "OneAdmin". It has no page
   sentence, no suggestions and nothing it can read, and no OneAI tool
   reads an operator record. Recommended:
   - a reader, `console_today`, behind `require_admin()`: what needs the
     operator, each with its reason (a job's failed step and error, what
     a workspace owes and since when, what a domain is waiting on, a
     signup waiting);
   - suggestions: **What needs me today?** and **Why did this job fail?**
     (on a job).
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: the records hold: every OneAdmin doctype grants only
   One Operator, and `site.py` refuses them on a site that is not the admin
   site. Two gaps in what is *offered*:
   - **A Workspace Manager who is not an operator sees OneAdmin in the
     dock**, and Home opens on "Insufficient Permission for Tenant".
     frappe gives every workspace to Workspace Manager so it can be
     arranged, so the rail keeps Home and the dock keeps the entry. It
     would happen on a customer's own site to anybody holding that role.
     Recommended: a `boot_session` hook that takes OneAdmin's dock entry
     and rail out of the boot for anybody without One Operator, and for
     everybody on a site that is not the admin site.
   - **Price Check and Plan Calculator are missing from the operator's
     rail**, though both open for them.
5. **Cross-module**: Home counts Tenant, Provisioning Job and Tenant Domain.
   Signups (Account Request) waiting for a workspace are not on it, and
   nor is OneAI spend. Recommended: a signup waiting counts as something
   that needs the operator.
6. **UI and UX**:
   - a. **It is the stock desk**: four boxed cards, and quick lists with
     big grey View List bars and "No Data...". Recommended: Home as a page
     in the shell's look, as One › Home is. The counts sit on the page and
     each opens its list. Below them is one list, **Needs you**, of what
     is stuck, owing, waiting or new, each row saying why, with its one
     action (Retry a job, open the workspace, check the domain again).
   - b. **One thing has four names**: the card says Stuck, the list Stuck
     jobs, the job's status Failed, and its badge Stopped. Recommended:
     one word, Failed.
   - c. Building counts pending and waiting jobs, which Home does not
     list.
   - d. Nothing updates while it is open.
7. **Documented**: `one_admin` has **no README**, so OneAI cannot answer
   how the console works, and nothing says what Home is for.
   `docs/INFRASTRUCTURE.md` and `docs/ACCOUNTS.md` are the builders'
   documents, not the operator's. Recommended: `one_admin/README.md`, with
   Home's section first.
8. **Legal**: Home sends nothing anywhere. If 2 is built, OneAI reads
   customers' account details (company, contact, what they owe) for the
   operator, and the Privacy Policy says so under OneAI.
9. **Built from frappe**: it is all frappe (Workspace, Number Card, Quick
   List), which is why it looks like the stock desk. Rebuilt as in 6a, it
   stays frappe's: the shell's tables are EmbeddedList,
   `frappe.ui.button`, `frappe.ui.badge`, and `frappe.realtime` on the
   three doctypes.

Your word: all of them.

Done:

- **Home stays frappe's workspace**, as One › Home is. It was a page of
  ours for one commit, and it looked worse than the standard dashboard, so
  it went back: frappe's number cards, and Needs You as a Custom HTML Block
  (`OneAdmin Needs You`, for One Operator) drawn with frappe's own quick
  list markup and a number card's border.
- **Who is offered it**: `site.offer` (`extend_bootinfo`) takes OneAdmin's
  rail and Home out of the boot for anybody who is not an operator on the
  admin site, since frappe offers every workspace to Workspace Manager.
  Checked as admin@example.com (Workspace Manager, not an operator):
  OneAdmin is gone from the dock, and `/desk/one-admin` answers "not
  found".
- **The numbers**: Live, Building, Owing, Failed and Paid, Not Built, five
  number cards. Stuck is Failed, and Owing no longer counts archived
  workspaces.
- **Needs You**: one list, most pressing first, each row saying why and
  since when, with its action. A failed job has **Resume**
  (`operator.resume`), a paid signup with no workspace has **Build It**
  (`retry_signup`), and a domain waiting a day or broken has **Check
  Again** (`refresh_domain`). A workspace owing opens. Paid signups are on
  Home now.
- **One word**: Failed, on the count, the badge, the job's list and its
  head ("Failed at Step 3 of 7").
- **Live**: `frappe.realtime` on jobs, workspaces, domains and signups.
- **The rail**: Price Check and Plan Calculator were in the rail's file all
  along; this site had not migrated since they were added. Reloaded.
- **Notifications** (`one_admin/notifications.py`, `tell.py`), to One
  Operator only: **Job Failed**, **Signup Not Built**, **New Signup**,
  **Workspace Owing** (overdue and suspended), and **Domains Waiting**
  each morning. Each is called where its thing happens, since the
  machinery writes with `db_set`. Checked: the failed job told op@one.test
  "Archiving Gone Ltd failed", with the step and the error.
- **OneAI** (`one_admin/ai.py`): the page sentence, `console_today` (Home's
  own list, refused to anybody who is not an operator on the admin site,
  checked both ways), **What needs me today?**, and on a job **Why did
  this job fail?**. No model was called.
- **`one_admin/README.md`**: Home, Being told, Asking OneAI, Under the hood.
- **Legal**: `oneadmin-asks` in the Privacy Policy, revision 7.

### OneAdmin › Workspaces

Workspaces is frappe's list and form of `Tenant`: one row per customer
workspace, with its status, placement, site, plan, Stripe ids, limits and
storage. Everything on it is read-only; it changes through the toolbar's
verbs (Mark Overdue, Suspend, Archive, Delete Files, Restore, and Refresh
for storage and domains) and the sidebar's credit actions. On the dev site
it lists 8: six Live, Probe Ltd waiting to be built, and Gone Ltd
suspended.

1. **Notifications**: the operator is told when a workspace falls
   (Workspace Owing, from Home's pass). The customer is told once, on their
   own site, when they go overdue, with the date it falls
   (`one/account.py`, Payment Overdue, bell and mail). After that, nothing:
   - nobody tells the owner their workspace was **suspended**, and a
     suspended site cannot tell them itself;
   - nobody warns them before it is **archived** or its **files deleted**,
     which cannot be undone;
   - nobody tells them it was **restored**.
   Recommended: three mails from the admin site to `owner_email`, sent
   where the rung is reached (`steps._arrive` and the job's last step):
   **Workspace Suspended** (what to pay and by when before it is
   archived), **Workspace Archived** (when its files go), and **Workspace
   Restored**. Through the hub's templates, so an operator can reword them
   under Settings › Notifications.
2. **OneAI**: on a workspace the panel offers only the generic "Summarise
   this", and nothing it can read knows a workspace's standing, credits,
   jobs or domains. Recommended: **How is this workspace doing?** on the
   form, reading `operator.standing`, `credit_standing`, its last jobs and
   its domains, operator-only as `console_today` is. It changes nothing.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. `Tenant` grants only One Operator, `site.py`
   refuses it off the admin site, every field is read-only, and every verb
   calls `operator._may()`. `fall` refuses a rung that is not the next one.
   Two small things:
   - Assign, Tags and Share are offered on a record only operators can
     read; sharing it with anybody else does nothing. Recommended: hide
     Share.
   - A workspace whose `status_since` is empty never falls: `standing`
     gives no `days_left`, so the nightly walk passes it by. Gone Ltd is
     one (suspended, no date). Recommended: `_arrive` always writes it (it
     does now), and a patch sets it from the last Tenant Event for any
     that lack it.
5. **Cross-module**: a workspace is a Customer in our own books
   (`customer`, `sales.py`) and a plan (`offering`). Neither is reachable
   from the form's connections, which list raw doctype names (Provisioning
   Job, Tenant Event, Tenant Domain, Account Request). The customer's
   invoices, what they have paid and what they owe, are one click further
   than they should be. Recommended: connections named as the rail names
   them (Jobs, Log, Domains, Signups), plus **Invoices** (Sales Invoice by
   the customer) under Billing.
6. **UI and UX**:
   - a. **Two names**: the rail says Workspaces, the list and the
     breadcrumb say Tenant. Recommended: Workspaces and Workspace.
   - b. **The list**: "Used" is storage and reads "nothing" or "21 GB",
     with no limit beside it. The ID filter stays though the ID column is
     hidden, and there is a Plan filter but no Plan column, no owner and no
     credits. Two rows are both "Probe Ltd". Recommended: columns
     Workspace, Status, Plan, Owner, Storage ("21 GB of 25 GB", red over),
     and the site's slug under the name so two alike can be told apart;
     filters Status, Plan, Jurisdiction.
   - c. **The head**: the address banner has a close X, as if it were a
     message to dismiss. **Credits Left** says "None" in red on Acme Co,
     a live workspace on Starter, because the dev tenants were never given
     their plan's allowance (`credits_a_month` 0, `storage_limit` 0), so
     storage is missing from the band too. On a real workspace the band
     is right; "None" should say "0 credits" and the plan should be in the
     band. Recommended: the address as the head's sentence without the X,
     the band Plan, Storage, Credits Left, Used This Month.
   - d. **The sidebar**: "Give credits", "Credit ledger" and "AI usage"
     are lowercase underlined links, not frappe's buttons. Recommended:
     a **Credits** group in the toolbar (Give Credits, Credit Ledger, AI
     Usage) in Title Case, since the toolbar is where frappe puts a
     record's actions.
   - e. **The Workspace tab**: Owner is missing on Gone Ltd because it is
     empty (a workspace built before signups wrote it). Placement shows
     Cluster, Country, Jurisdiction and Bench, which the operator reads
     only when something breaks. Recommended: Placement and Site
     collapsed, the plan and the customer on the first tab.
   - f. Nothing updates while it is open: a job that finishes changes the
     status only on reload. Recommended: frappe's `doc_subscribe` does
     this for a form already; the job's `db_set` does not publish. Publish
     `doc_update` for the tenant when a job changes its status.
7. **Documented**: `one_admin/README.md` has Home and nothing on
   Workspaces: what a status means, how a workspace falls and comes back,
   what each verb does and cannot undo, and how credits are given.
   Recommended: a **Workspaces** section after Home.
8. **Legal**: the Terms' non-payment clause (`one_legal/legal.py`,
   `nonpayment`) promises only "we tell you" when a payment fails. With
   the mails in 1, it says we tell the owner at each step, and before
   anything is deleted, a material change to the Terms. If 2 is built,
   OneAI reads a workspace's billing standing for the operator, which
   `oneadmin-asks` already says.
9. **Built from frappe**: it is frappe's list, form, connections
   (`tenant_dashboard.py`), indicators and Record Head. The sidebar links
   (`add_user_action`) are frappe's too but drawn as bare links; the
   toolbar's group is the frappe way to hold them.

Your word: all of them.

Done:

- **The owner is mailed** from the admin site when their workspace is
  suspended (**Workspace Suspended**, with the day it is archived), archived
  (**Workspace Archived**, with the day it and its files are deleted) and
  restored (**Workspace Restored**, with its address). `tell.owner`, called
  from `steps._arrive`. Operator-only in Settings › Notifications, where
  they can be reworded. Checked: both queue to buyer@acme.test.
- **The clock**: `_arrive` and the live step write `status_since` with every
  status, and `patches/status_since.py` dated the workspaces that had none,
  from their log. Gone Ltd now says "Falls to Archived in 8 days".
- **Live**: every status write publishes (`db_set(..., notify=True)`), so an
  open form and list change as a job moves.
- **Workspaces**: our own lists are called what the rail calls them
  (`one/titles.py` hands down the labels of our doctypes that the rails name
  one way; `reports.js` writes the list's title, the crumb and a record's
  connections). Tenant is Workspaces, and the other OneAdmin lists read Jobs,
  Log, Domains, Signups and so on. erpnext's keep their names.
- **The list**: Workspace (with its slug, so the two Probe Ltds differ),
  Status, Owner, Plan, Storage ("21 GB of 100 GB", red over). Filters
  Workspace, Status, Plan, Jurisdiction; the ID filter is gone.
- **The head**: Plan, Storage, Credits Left (0, not "None"), Used This Month.
  Storage shows even with no limit. The sentence has no close X, on every
  head: it is where a record stands, not a message.
- **The form**: Plan and Customer on the first tab beside Status; Placement
  and Site folded. A **Billing** menu in the toolbar: Invoices (for somebody
  who may read them; an operator alone may not read the books, so the
  Customer connection is not drawn for them either), Give Credits, Credit
  Ledger, AI Usage. Share is gone, and the role can no longer share.
- **OneAI**: **How is this workspace doing?** on a workspace, reading
  `workspace_facts` (standing, plan, storage, credits, domains, last jobs
  and log), refused to anybody not an operator on the admin site. No model
  was called.
- **README**: a Workspaces section after Home; Being told and Asking OneAI
  name the new mails and question.
- **Legal**: the Terms' non-payment clause says the owner is mailed at each
  step and before deletion, revision 5.

### OneAdmin › Jobs

Jobs is frappe's list and form of `Provisioning Job`: one walk of steps that
builds a workspace (Provision, six steps) or moves it on the ladder (Suspend,
Restore, Archive, Drop). `runner.tick` runs every two minutes, advances up
to five due jobs a step each, retries a slow step with backoff, and marks a
job Failed after twelve tries. The list opens on jobs not done. On the dev
site: Nine B's suspension waiting to run, Gone Ltd's archive failed on step
2, Nine X's build waiting on Frappe Cloud after three tries, and Nine S's
build done.

1. **Notifications**: a failed job tells the operators (Job Failed, from
   Home's pass). Two gaps:
   - **Nobody is told a workspace is ready.** When a build finishes, the
     owner learns it only if they are still on the welcome page, which says
     "The workspace is ready" and links to it. A build that waits on Frappe
     Cloud can take a long time. Recommended: **Workspace Ready** mailed to
     the owner from `steps.live`, with the address.
   - **Nothing makes the owner a user of their new workspace.** No step
     invites `owner_email` into the site it built, so "Open it" leads to a
     sign-in page they have no account for. Recommended: a last step,
     `invite_owner`, that asks the new site to invite them as its
     administrator (One's own Invitation mail, with the 7-day link). The
     Workspace Ready mail then says to use that link. This needs a call the
     new site answers with the token `push_config` wrote, so it is the one
     change here that touches the tenant side.
   - The Job Failed text says "At: {step}" and the raw error ("press
     answered 503 three times"). "press" is our word for Frappe Cloud.
     Recommended: "Stopped while asking Frappe Cloud to delete the site",
     and the error as it is under it.
2. **OneAI**: **Why did this job fail?** is offered on every job, done or
   not, and has nothing to read but the fields: the step as a function name
   and the payload as JSON. Recommended: a reader, `job_facts`, with every
   step of the walk in words and which are done, the attempts, when it runs
   next, the error, and the workspace's status; operator-only. The question
   offered only on a failed job; on one waiting, **Why is this job
   waiting?**.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. Read-only for One Operator, refused off the
   admin site, no create or delete; Resume is `operator.resume`, behind
   `_may`. Share is offered and does nothing; recommended off, as on
   Workspaces.
5. **Cross-module**: a job belongs to a workspace, and the workspace's log
   (Tenant Event) records what the job did, but the job does not show its
   log, and the log does not say which job. Home counts only builds as
   Building, so a suspension or archive **waiting to run for a week**
   (Nine B's) shows nowhere. When the scheduler stops, every job stops and
   nothing says so. Recommended: Needs You lists a job whose next run is
   more than fifteen minutes past ("Jobs are not moving: the last ran at
   …"), whatever its kind.
6. **UI and UX**:
   - a. **The list**: the ID column (PROV-26-00013) is the widest thing on
     it; the Tenant column is called Tenant; the step is cut off; there is
     no age, and a job's error is not on its row. Recommended: Workspace
     (named), Kind, Status, Step, and when it last moved ("3 hours ago"),
     with the error under a failed row's step; no ID column or filter.
   - b. **The form repeats the head**: the head says "Failed at Step 2 of
     4 · Asking Frappe Cloud to delete the site", and the fields below say
     Status Failed and Step `archive_site`. Attempts reads 0 and Next Run a
     week ago on a failed job, and both show on a done one. Payload is raw
     JSON. Recommended: the walk as a checklist of its steps in words, done
     ticked, the one it is on marked (the head has this data already,
     `operator.walk`); Attempts and Next Run only while it waits; the error
     in full on a failed one; Payload folded away.
   - c. **Tenant** is the label on the form too. Recommended: Workspace.
   - d. The required stars on read-only fields: nobody types here.
   - e. Nothing updates while it is open: a waiting job moves on while
     the operator watches it and the page stays. Recommended: `db_set(...,
     notify=True)` in the runner, as the workspace now does.
7. **Documented**: the README says what Home does with a failed job, but
   nothing on what a job is, its kinds and steps, what Waiting means, when
   one gives up, or that Resume is safe. Recommended: a **Jobs** section.
8. **Legal**: jobs send the workspace's name, region and config to Frappe
   Cloud and its routes to Cloudflare, both already listed as
   subprocessors in `one_admin/legal.py`. If the owner is invited (1), the
   owner's email goes into their new workspace, which the Terms should say
   when they describe how a workspace is set up. Nothing else is new.
9. **Built from frappe**: list, form, indicators and the Record Head are
   frappe's; the checklist in 6b would be the head's own steps drawn with
   frappe's badge and icon, not a new widget.

Your word: all of them.

Done:

- **The owner is invited.** A build has a new step, **Inviting the owner**,
  between telling the site who it is and marking it live. The admin site
  cannot sign in to a site it built, so the site does it: `proxy.hello` now
  names the owner, and a workspace nobody administers yet makes them its
  first **Workspace Administrator** and mails One's own invitation, from
  "One", with the 7-day link (`one/owner.py`). The step posts to the new
  site's `account.wake` (rate-limited, takes nothing, only makes the site
  ask) and waits until it says it has an administrator. Checked on the dev
  site with the check forced: the user is made, "One invited you to Nine X"
  is queued, and a second call does nothing. Not run against a real Frappe
  Cloud site.
- **Workspace Ready** is mailed to the owner from `steps.live`, saying the
  password link is in a second mail. The welcome page says the same.
- **Job Failed** reads "It stopped on step 2 of 4: Asking Frappe Cloud to
  delete the site", with the error under it.
- **Home**: a job due and not run for fifteen minutes, whatever its kind, is
  under Needs You as "Suspending Nine B has not moved", with **Run Now**
  (`operator.run_now`, operator-only, one step).
- **The list** leads with the workspace (the job's title is now its
  workspace), then Status, Kind, Step; a failed job's error is under its
  step in red. No ID column or filter.
- **The form**: a **Steps** section, the walk in words, done ticked, the one
  it is on marked, with its tries and error under it. The raw step, Attempts
  and Error fields are gone from view; Next Run shows only while waiting,
  Finished only when done or failed; Payload is folded under Collected. No
  required stars, no Share (and the role cannot share).
- **Live**: every job write publishes (`notify=True`), as the workspace's do.
- **OneAI**: `job_facts` reads the walk, attempts, error and the
  workspace's status, operator-only. **Why did this job fail?** is offered
  only on a failed job and **Why is this job waiting?** only on one waiting:
  a suggestion can now name a `when` on the record (`one_ai/suggest.py`).
  No model was called.
- **Translated**: the step words were never in the translation files; they
  are `_lt` now, and read in each operator's language.
- **README**: a Jobs section. **Terms**: the person who paid is made the
  first administrator and emailed an invitation, revision 6.

### OneAdmin › Log

Log is frappe's list of `Tenant Event`: one row for each thing that
happened to a workspace, written by the machinery. A workspace reaching a
rung (Overdue, Suspended, Restored, Archived, Dropped), a plan or add-on
changed, a plan change Frappe Cloud refused (Plan Change Pending), and a
workspace over its storage. Nobody types in it. On the dev site: 12 rows,
all Nine X and Nine S, eight of them add-on changes from yesterday.

1. **Notifications**: the log sends nothing, and needs to send nothing
   of its own: the rungs are told already (Workspace Owing, the owner's
   mails). One gap it shows: **a workspace over its storage** is written
   here every night and told to nobody on our side (its own site tells
   its administrators when it is nearly full). Recommended: over its
   limit is a row in Needs You, not a notice.
2. **OneAI**: the list offers "What stands out here?" and reads the raw
   rows. `workspace_facts` already reads a workspace's last ten entries.
   Holds, once 6c makes the rows say something.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. Read-only for One Operator, refused off the
   admin site. Share is offered and does nothing; recommended off.
5. **Cross-module**:
   - The log does not say **who** did it. A plan changed by the
     customer (through the proxy, so "Guest"), an operator pressing
     Suspend, and the nightly clock all read alike. Recommended: a **By**
     column: the customer, the operator's name, or One.
   - **An operator's manual fall is logged as "the clock".**
     `operator.fall` goes through `lifecycle.fall`, which always writes
     that. Recommended: it says who pressed it.
   - The log does not say **which job** wrote it, and a job does not
     show its entries. Recommended: a Job link on the row, and the job's
     entries under its steps.
   - The same things are also the workspace's story, and its form's
     Activity tab does not show them: they sit behind the Log connection.
     Recommended: frappe's own timeline, through
     `additional_timeline_content`, so a workspace's Activity reads
     "Suspended by the clock · 3 days ago" beside its edits.
6. **UI and UX**:
   - a. **The ID column** (a hash, "teg3ejoa4k") leads every row, and
     the ID filter is first. `hide_name_column` does nothing without a
     title field. Recommended: the workspace leads, as on Jobs.
   - b. The **Status** column holds the kind; **Tenant** is the
     workspace. Recommended: What, Workspace, Detail, By, and when.
   - c. **The detail is the code's own words**: "the clock", "paid",
     "press has stopped serving the site", "team with 2 × database-1"
     (the plan's key and the add-on's key, not their names),
     "holding 22548578304 bytes against a limit of 26843545600". None
     is translated. Recommended: each written as a sentence in words
     at the time, with plan and add-on names and sizes in GB, and `_lt`
     so it reads in the operator's language.
   - d. **Over Storage is written every night** while a workspace is
     over, so a month over is thirty rows. Recommended: once when it
     goes over, and again only when it changes by a gigabyte or more.
   - e. **Drifted** and **Over Database** are kinds nothing writes.
     Recommended: remove them.
   - f. Opening a row shows the same three fields again, with the
     required stars. Recommended: the row opens its workspace; the form
     stays for a link from elsewhere.
7. **Documented**: nothing in the README says what the log is or what
   each kind means. Recommended: a **Log** section.
8. **Legal**: the log is our own record of what happened to a
   customer's workspace, kept on the admin site. Nothing leaves. Holds.
9. **Built from frappe**: frappe's list and indicators; 5's timeline is
   frappe's own `additional_timeline_content`, which OneProject uses
   already.

Your word: all of them.

Done:

- **One writer** (`one_admin/log.py`): every row goes through `log.write`,
  and a test refuses anything else that writes the log.
- **In words**: a rung's reason is a fixed phrase ("A payment failed",
  "Its time on the last rung ran out", "Moved by hand", "Frappe Cloud
  stopped serving the site", "Paid"…), `_lt`, stored in English and shown
  in the operator's language. A plan change names the plan and add-ons
  ("Team + 2 × 1 GB of Database"); storage is "21 GB / 25 GB".
  `patches/log_in_words.py` reworded the rows already written.
- **By**: the customer (a plan they changed, through the proxy), the
  operator by name (a button, or a job they started, from the job's
  owner), or One. An operator's manual fall says "Moved by hand" and names
  them; Nine X's Overdue, which read "the clock", now does.
- **Which job**: a row written by a job links it, and a job's form has a
  Log connection.
- **Over Storage** is written once when a workspace goes over, then only
  when it moves by a gigabyte or a month has passed; and a workspace over
  is in Needs You until it is back under.
- **The workspace's Activity** shows its log (frappe's
  `additional_timeline_content`, `log.timeline`), as "Suspended · Frappe
  Cloud stopped serving the site · by One".
- **The list**: Workspace, What (a coloured badge), Detail, By, and when.
  No ID column or filter. A row opens its workspace. Drifted and Over
  Database are gone, Share is off.
- **README**: a Log section.
- Also fixed on the way: the workspace head said "Team + 1 add-ons".

### OneAdmin › Domains

Domains is frappe's list and form of `Tenant Domain`: one row per name a
customer has put on their workspace (`crm.acme.com`), a custom hostname on
our Cloudflare zone. The customer adds, removes and chooses the main one on
their own site (Workspace › Domains); Cloudflare decides whether it works,
and the admin site asks it when the customer presses Check Again, when an
operator does, and each night for names not yet working. On the dev site:
one, `nine.example.com`, working, for Nine Ltd.

1. **Notifications**: holds. The customer's administrators are told on
   their own site when a name starts or stops working (Domain Working,
   Domain Stopped Working), and the operators each morning when one has
   waited a day or broken (Domains Waiting, from Home's pass).
2. **OneAI**: nothing reads a domain but the generic "Summarise this", and
   the one question anybody opens a domain for is why it does not work.
   Recommended: **Why isn't this domain working?** on a domain not
   working, reading its status, Cloudflare's problem, where its CNAME must
   point, how long it has waited and when it was last asked;
   operator-only.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. Read-only for One Operator, refused off the
   admin site; the one verb asks Cloudflare and changes nothing of the
   customer's. Share is offered and does nothing; recommended off.
5. **Cross-module**: the workspace's form lists its domains, but nothing
   here says which name is the workspace's **main address** (Tenant's
   `primary_domain`), which is the first thing to know before touching
   one. Recommended: a Main column and a line on the form.
6. **UI and UX**:
   - a. **Still written for Frappe Cloud.** Domains moved to Cloudflare,
     and the words did not: the list says "Frappe Cloud is setting it
     up" and "Removed at Frappe Cloud", the head says "Asked for, and
     Frappe Cloud has not answered yet" and "Frappe Cloud no longer has
     this domain", and both handle an **In Progress** status that no
     longer exists. Each is wrong about what is happening.
   - b. **Three words for one state**: Pending is "Waiting on DNS" in the
     list, "Waiting" on the pill; Active is "Working" in the list and
     "Active" on the pill and field; Broken is "Broken" and "Not
     working". Recommended: one set, the customer's own (Waiting,
     Working, Not working).
   - c. **The form says almost nothing**: Workspace and Status. For a name
     that is waiting it should say what the customer has to do ("Point
     crm.acme.com at acme.t.4dl.app with a CNAME record"), Cloudflare's
     problem in full, since when it has waited, and when it was last
     asked. Cloudflare's id and raw answer are for somebody debugging:
     folded.
   - d. **The list** is headed ID, with no age, no problem and no main
     mark. Recommended: Domain, Workspace, Status, Main, and Cloudflare's
     problem under a name not working.
   - e. **The button says Refresh**, and the same action on Home says
     Check Again. Recommended: Check Again, as the customer's own screen
     says it.
   - f. The required star on Workspace; nothing updates while open
     (`_keep` writes without publishing).
7. **Documented**: nothing in the README on domains: how a customer adds
   one, what each status means, what Check Again does, and why an
   operator cannot add or remove a name for a customer. Recommended: a
   **Domains** section.
8. **Legal**: a customer's names go to Cloudflare, which
   `one_admin/legal.py` already lists as the network every workspace is
   reached through. Holds.
9. **Built from frappe**: frappe's list, form and Record Head. Holds.

Your word: all of them.

Done:

- **Cloudflare, not Frappe Cloud**: every sentence about a domain is
  rewritten for Cloudflare, and the In Progress state that no longer exists
  is gone from the list and the head. A test refuses "Frappe Cloud" there.
- **One set of words**, the customer's: Working, Waiting, Not working (and
  Not at Cloudflare for a name Cloudflare has lost), on the list, the pill
  and OneAI. The Status field, which said Pending and Active, is not shown
  on the form; the pill says it.
- **The head says what it needs**: "Waiting for the customer's DNS. It
  needs a CNAME record from crm.acme.com to acme.t.4dl.app. Waiting since
  27 Sep 2026. Cloudflare says: …". A working name says whether it is the
  workspace's main address.
- **Main address**: `is_main` on each domain, kept by `make_primary`
  (`patches/domain_is_main.py` set it from each workspace), a Main badge in
  the list.
- **The list**: Domain, Status, Workspace (by name), Main, and
  Cloudflare's problem on the row. No ID column or filter.
- **Check Again**, as Home and the customer say it.
- **Live**: each answer from Cloudflare is published to an open domain.
- **OneAI**: **Why isn't this domain working?** on a domain waiting, not
  working or lost, reading `domain_facts` (status, problem, the CNAME
  target, main, since when); operator-only. No model was called.
- **The form**: no star, no Share; Cloudflare's id and last answer are
  folded under Cloudflare.
- **README**: a Domains section, including why an operator cannot add or
  remove a customer's name.
- For looking at it, the dev site has a waiting domain now
  (`crm.acme.test` on Acme Co), and Nine Ltd's `nine.example.com` is its
  main address.

### OneAdmin › Price List

Price List is frappe's list and form of `Offering`: every plan, credit pack
and add-on One sells, with its price, trial, Stripe price and quotas. It is
the one screen in OneAdmin an operator writes in: the signup page, the
customer's Plan and Credits screen, the Plan Calculator and Price Check all
read it, and each offering has an Item in our books (`books.synced`). On the
dev site: 13 (five plans, one disabled; three packs; five add-ons).

1. **Notifications**: holds. A change reaches no customer by itself:
   Stripe keeps a subscriber on the price they signed up at, and quotas
   are copied onto a workspace. A change is money, though, and nothing
   but the form's own history records who made it. Holds with
   `track_changes`, which it has.
2. **OneAI**: nothing but "Summarise this". Recommended: **How do our
   plans compare?** on the list, reading every enabled offering (price,
   trial, quotas, what an add-on adds) and saying where the steps between
   plans are uneven; and on a plan, **Who is on this plan?**. Both read
   only.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. One Operator creates, edits and deletes; the
   Key cannot change once set (`set_only_once`); frappe refuses to delete
   one a workspace links to. Share is offered and does nothing;
   recommended off.
5. **Cross-module**:
   - **The head is wrong for add-ons and packs.** "No workspace has bought
     this yet" on 1 GB of Database, which Nine X has. `operator.sold`
     counts only `Tenant.offering`, the plan. Recommended: an add-on
     counts the workspaces carrying it (`Tenant Add-on`), a plan its
     workspaces; a pack says it is bought once and not tracked per pack.
   - **"Changing a price or a quota here does not change theirs" is half
     true.** The price is true (Stripe keeps them on theirs). The quotas
     are copied again, from this row, whenever the customer next changes
     their plan or add-ons (`quota.apply`), so an edit reaches them then.
     Recommended: say that.
   - Nothing on the form leads to the workspaces on it, the signups that
     chose it, or its Item in our books. Recommended: connections
     Workspaces (plan and add-on) and Signups, and the Item for somebody
     who may read the books.
6. **UI and UX**:
   - a. **Every field shows for every kind.** An add-on of 1 GB of
     Database shows Storage 0, Seats 0 and Credits a Month 0, each
     described "Zero means unlimited", which on an add-on is wrong; the
     trial shows on add-ons, which cannot have one. `CARRIES` already
     says what each kind carries. Recommended: show only those fields,
     the trial only on a plan, and "Zero means unlimited" only on a plan.
   - b. **The list mixes kinds** sorted by amount (a pack between two
     add-ons), shows a Status column that is the Enabled tick, the ID,
     and no quotas. Recommended: grouped by kind (plans first), Label,
     Kind, Price ("$30 a month", "$9 once"), and what it gives in one
     line ("20 GB · 1 GB database · 5 seats · 1,000 credits a month");
     disabled rows greyed; no ID.
   - c. **Nowhere to see it as a customer does.** Recommended: **See the
     Signup Page** in the list's menu, opening `/start`.
   - d. Stripe Price ID is shown to an operator who cannot change it;
     folded.
7. **Documented**: nothing in the README on the price list: the three
   kinds, what each carries, what changing a price or quota does to
   existing customers, trials, and why disabling only stops new signups.
   Recommended: a **Price List** section.
8. **Legal**: the Terms describe plans, trials and add-ons in general and
   name no price. Holds.
9. **Built from frappe**: frappe's list, form and Record Head.
   `depends_on` shows each field for its kind; connections are frappe's
   dashboard. Holds.

Your word: all of them.

Done:

- **The head is right for every kind.** An add-on counts the workspaces
  carrying it (`Tenant Add-on`), so 1 GB of Database says "One workspace
  has this, 1 of them live"; a plan counts its workspaces; a pack says it
  is bought once and used up. And it says what an edit does: "They keep
  the price they pay. A changed quota reaches them the next time they
  change their plan or add-ons."
- **Only what the kind carries**: a pack shows Credits; a plan and an
  add-on show storage, database, seats and credits a month, with "Zero
  means unlimited" on a plan and "Fill in the one thing this add-on adds"
  on an add-on. The trial and Recurring show only on a plan; the
  controller sets them for the other kinds.
- **The list**: plans, then add-ons, then packs, each by price (`sort_key`);
  the kind as a coloured badge, Disabled in grey; "$30 a month" or "$9
  once"; and **Gives**, one line of what it gives ("20 GB storage · 1 GB
  database · 5 seats · 1,000 credits a month"), written on save
  (`patches/offering_gives.py` for the rows before). No ID column or filter.
- **See the Signup Page** in the list's menu opens `/start`.
- **Connections**: a plan's Workspaces and Signups; on an add-on,
  **Workspaces With It**; **Item in Books** for somebody who may read the
  books (an operator alone may not, so it does not show for them).
- **OneAI**: `price_list`, operator-only; **How do our plans compare?** on
  the list and **Who has this?** on a plan or add-on. No model was called.
- Stripe's price id is folded under Stripe; Share is off.
- **README**: a Price List section.

### OneAdmin › Price Check

Price Check is a frappe Script Report over the price list
(`report/price_check`, rules in `plans.check`): every enabled offering, what
it holds, its price, what it costs us a month (from the costs in Settings),
how many times its cost it sells for, how much each plan saves over the one
below bought as add-ons, and a sentence on anything that does not hold. Along
the top, how many offerings, how many are wrong, and how many are close
calls. On the dev site: 12 offerings, nothing wrong.

1. **Notifications**: a price that does not cover its cost, or a plan that
   nobody would move up to, is found only by opening this report. Nothing
   warns the operator who just saved the offering, or who just raised a
   cost in Settings. Recommended: saving an offering, or the costs in
   Settings, says at once what `plans.check` finds about it (frappe's
   message on save), and Needs You lists anything **Wrong** until fixed.
2. **OneAI**: nothing but "What stands out here?", reading the rows.
   Recommended: **What should we change?** here, reading every finding
   with its numbers, the costs and the margin wanted, and saying what to
   change first; operator-only, and it changes nothing.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. The report is One Operator's, refused off the
   admin site (`site.require_admin`).
5. **Cross-module**:
   - **Two lines for one thing**: the report's "Holds" is its own
     (`_holds`: "5 seats, 20 GB storage, …"), and the Price List's new
     Gives line is another, in another order. Recommended: one, the
     offering's `gives`.
   - **Where the cost comes from is not said.** Cost is the costs in
     OneAdmin Settings (a workspace, a seat, a GB of storage and of
     database, backups kept, a credit) and the margin wanted there
     (2×). Nothing on the report names them or leads to them.
     Recommended: the summary says the margin wanted, and the report's
     menu opens Settings at the costs.
   - Disabled offerings are left out without saying so (Standard).
     Recommended: an **Include disabled** filter, off.
6. **UI and UX**:
   - a. **The findings are cut off**: Says is the last column, past the
     edge of the screen, and every row reads "Makes sense" in it.
     Recommended: rows with a finding first, Says right after the
     offering, and the rest of the columns narrower.
   - b. **The findings are English only**, built as f-strings in
     `plans.check`. Recommended: `_()` with named slots.
   - c. "Times Cost" and "Saves Over Add-ons (%)": the second is cut off
     in its header. Recommended: **Margin** ("2.0×") and **Saves**
     ("53%").
7. **Documented**: nothing in the README on what Price Check checks: the
   five rules, where the costs come from, and what Wrong and Close Call
   mean. Recommended: a **Price Check** section.
8. **Legal**: nothing leaves the admin site. Holds.
9. **Built from frappe**: a Script Report with its summary; the message
   on save is frappe's `msgprint`. Holds.

Your word: all of them.

Done:

- **Told at once**: saving an offering says what the price list now gets
  wrong about it, and saving the costs in Settings says everything it gets
  wrong (`offerings.warn`, frappe's message on save). Anything **Wrong** is
  on Home under Needs You, as "Wrong Price", until fixed. Checked with 5
  Seats at 1: "5 Seats sells for 1 and costs 2.50 to run, under the 2×
  margin (5.00)", and the Home row; rolled back.
- **Findings in words**: `plans.check` stays frappe-free, and each finding
  now carries its rule and its numbers; `offerings.RULES` says them with
  named slots, translated.
- **The report**: findings first (Wrong, then Close Calls), Says right
  after the offering, the offering's own **Gives** line in place of the
  report's second description, **Margin** as "2.1×" and **Saves** as
  "53%", all on the screen at once. The summary shows the **Margin
  Wanted**; **Costs in Settings** in the menu opens them; **Include
  Disabled** checks withdrawn offerings.
- **OneAI**: **What should we change?** on the report, reading
  `price_check` (findings with numbers, costs, margin); operator-only. A
  report can now carry suggestions (`report:<name>` in
  `one_ai/suggest.py`). No model was called.
- **README**: a Price Check section with the five rules.

### OneAdmin › Plan Calculator

Plan Calculator is a frappe Script Report (`report/plan_calculator`, sums
in `plans.quote`): given how many seats, how much storage and database and
how many credits a month a workspace needs, every enabled plan with the
add-ons that bring it up to that, cheapest first, what each way costs us,
and how much dearer each is than the cheapest. It is the same answer a
customer's own Plan and Credits screen gets (`billing.quote`, through the
proxy). On the dev site, for 10 seats, 50 GB, 2 GB and 2,000 credits:
Team at $70, then Starter with three add-ons at $73.

1. **Notifications**: it sends nothing, and nothing it does needs telling.
   Holds.
2. **OneAI**: nothing but "What stands out here?". The question an
   operator brings here is a customer's: "we have 25 people and 80 GB,
   what should we buy?". Recommended: **What should they buy?**, and a
   reader, `plan_quote`, that answers for any needs said in words, with
   the cheapest way and the next; operator-only.
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: holds. One Operator's, refused off the admin site.
5. **Cross-module**:
   - **It cannot start from a real workspace.** The usual question is
     what an existing customer should move to, and the operator has to
     read their seats, storage, database and credits off the workspace
     and type them in. Recommended: a **Workspace** filter that fills
     the needs from what it uses now, and marks the plan it is on.
   - A plan's row does not say what the plan gives, so "Team, Nothing"
     does not say why nothing is needed. Recommended: the plan's
     **Gives** line (the Price List's).
6. **UI and UX**:
   - a. **The four filters show only numbers** once filled: "10", "50",
     "2", "2000", with no word for which is which (frappe shows a filter's
     label only while it is empty). Recommended: the needs said back in
     the summary ("10 seats · 50 GB storage · 2 GB database · 2,000
     credits a month"), with the cheapest answer beside it.
   - b. "Times Cost" as on Price Check before; recommended **Margin**
     ("2.4×"), and "Against the Cheapest" as **Dearer By**.
   - c. Starter's add-ons are cut off ("1 × 5 Seats, 1 × 50 GB of
     Storage, 1 × 1 G…"). Recommended: the add-ons column wider, the
     rest narrower.
7. **Documented**: nothing in the README on what it is for, or that it
   is the customer's own sum. Recommended: a **Plan Calculator** section.
8. **Legal**: nothing leaves the admin site. Holds.
9. **Built from frappe**: a Script Report and its summary. Holds.

Your word: all of them.

Done:

- The summary says the four needs back with their words (Seats 15,
  Storage 20 GB, Database 1 GB, Credits a Month 3,000) and the cheapest
  answer ("Team at $70.00").
- A **Workspace** filter fills the needs from what it has now (`needs_of`:
  the seats it pays for, storage and database used, its credits a month or
  this month's spend, whichever is more). The summary adds what it **Pays
  Now**, and a **Now** column marks **Their plan**.
- Each row has the plan's **Gives** line. **Margin** reads "2.4×", and
  "Against the Cheapest" is **Dearer By**. Columns resized so the add-ons
  fit.
- Found while fixing: the report counted credit packs as monthly add-ons,
  so Starter reached 2,000 credits a month with a pack the customer's own
  screen never offers. It now counts add-ons only, as `billing.quote` does,
  and a plan no add-on can reach says what it is **Short of**.
- OneAI: **What should they buy?** on the report, and `plan_quote`
  (operator-only) for needs in words or a workspace by name.
- README: a **Plan Calculator** section and an Under the hood line.

### OneAdmin › Signups

Signups is the `Account Request` list: somebody who filled in the signup
page, before and after they paid. `signup.start` writes the request and our
own lead and deal (`sales.py`), sends them to Stripe, and Stripe's
`checkout.session.completed` calls `signup.accept`, which makes the
workspace and starts its job. The list shows each one's state in words
(Not paid, At Stripe, Paid, Being built, Done, Paid and not built); the
record has a Record Head with the failure in red and **Build Workspace**.
On the dev site: six, one failed (Borja SL), two paid with no workspace,
three never paid.

1. **Notifications**:
   - The operators get **New Signup** when somebody pays and **Signup Not
     Built** when the workspace could not be made. Not Built's message is
     the email and the raw error on two lines. Recommended: "It stopped
     because: {error}. Build Workspace on the signup tries again."
   - **The customer hears nothing if it is not built.** They paid, Stripe
     sent a receipt, and no workspace and no word follows until an
     operator fixes it. Recommended: a **Workspace Delayed** mail to them
     when it fails ("We have your payment. Setting up {workspace} hit a
     problem on our side; we are on it and will write when it is ready"),
     then Workspace Ready as now.
2. **OneAI**: nothing but "What stands out here?". Recommended: **Why
   wasn't this built?** on a failed or paid-and-unbuilt signup, and a
   reader, `signup_facts` (operator-only: its state and why, its payment,
   its workspace and job, whether Build Workspace will help).
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: One Operator reads, nobody writes, creates or deletes;
   Build Workspace is the one action. Holds, except **Share** is on, as it
   was on the other operator records. Recommended: off.
5. **Cross-module**:
   - **The status stops at "Being built".** `accept` sets Provisioning and
     nothing sets Done when the job finishes, so every signup ever built
     says "Being built" forever. And nothing sets **Paid** either: a
     request goes from Not paid (or At Stripe) straight to Being built.
     acmeco says **Not paid** and has a workspace. Recommended: the job's
     end sets the request **Done** (or Failed with the job's error), a
     payment sets Paid first, and a patch mends the rows there are.
   - **A signup nobody paid for keeps its name forever.** Not paid and At
     Stripe both hold the slug (`HOLDING`), and the nightly sweep that
     loses their deal after a few days (`sales.abandoned`) leaves the
     request as it was, so "gone2" can never be taken again. Recommended:
     the same sweep marks it **Abandoned**, which lets the name go.
   - The record does not show its Stripe payment events (`Stripe Webhook
     Event.request`) or its workspace's job. Recommended: **Connections**
     to the workspace, its job and its Stripe events.
6. **UI and UX**:
   - a. The list shows the **ID** column and filter (REQ-26-01235), which
     says nothing; the other lists show the workspace instead.
     Recommended: off, as on the others. "Offering" is **Plan**, as on
     Workspaces.
   - b. **Three words for one state.** The list says "Paid and not
     built", the head's pill says "Failed", the Status field says
     "Failed" with "A workspace is only created after payment is
     confirmed" under it. "Not paid" in the list is "New" on the form.
     Recommended: the head's pill in the list's words, and the Status
     field off the form (the pill is it).
   - c. Labels: "Workspace" is the name they typed, while "Tenant" is the
     workspace. Recommended: **Workspace Name** and **Workspace**. "Slug"
     is **Address**.
   - d. The last section has no heading, and repeats the failure the red
     line above it already says. Recommended: headed **What Came of It**,
     the failure only in the head, and the Stripe session as **Open in
     Stripe** in the menu rather than a raw `cs_…` id.
7. **Documented**: nothing in the README on what a signup is, its states,
   or what Build Workspace does. Recommended: a **Signups** section.
8. **Legal**: the privacy notice says nothing about the signup page: that
   it keeps the email, workspace name and country somebody typed, whether
   or not they pay, and that it becomes a lead and a deal in our own
   records. Recommended: a clause in `one_admin/legal.py`. Stripe is
   already a subprocessor.
9. **Built from frappe**: a list, a form and a Record Head. Holds.

Your word: all of them.

Done:

- **A signup moves on its own now.** A payment sets **Paid**, making the
  workspace sets **Being built**, and the workspace going live sets
  **Built** (`signup.built` from `steps.live`). A signup not paid for in
  seven days is **Abandoned** each night (`signup.abandon`), and its name
  is free again. If they pay after all it is still built, unless the name
  was taken in the meantime, in which case it fails and says so.
  `patches/signup_states.py` mended the rows there were: acmeco and Dup
  Ltd are Built, gone2 is Abandoned.
- The list and the head say a state in the same words (Not paid, At
  checkout, Paid, not built, Being built, Built, Paid, build failed,
  Abandoned), and the Status field is off the form.
- **Workspace Delayed** is mailed to the person who paid, once, when their
  workspace cannot be made. **Signup Not Built** says why it stopped and
  that Build Workspace tries again.
- OneAI: **Why wasn't this built?** on a paid, unbuilt signup, with
  `signup_facts` (operator-only).
- List: no ID column or filter; **Plan**. Form: **Workspace Name**,
  **Address**, **Workspace**; the failure only in the head; the last
  section is **Outcome**; the Stripe session is **Open in Stripe** in the
  menu; Share off; Connections to the workspace, our lead and deal, and
  Stripe's events.
- README: a **Signups** section, the new mail under Being told, and an
  Under the hood line.
- Legal: a privacy clause on what the signup page keeps and that it
  becomes a lead of ours; the Privacy Policy is revision 8.

### OneAdmin › Credits

Credits is the `Credit Ledger Entry` list: every movement of every
workspace's OneAI credits, one submitted row each, never edited. A **Grant**
adds (a plan's monthly credits, a pack bought, or an operator's **Give
Credits** on a workspace) and may expire; a **Spend** is one AI call, drawn
from a grant; a **Refund** gives an over-charge back. A balance is a sum of
the rows (`ledger.py`). On the dev site: 459 rows, of which 456 are spends
of about one credit each by Nine X.

1. **Notifications**: the customer's administrators are told on their own
   site: **Credits Running Low**, **Credits Expiring**, **Credits Added**
   (`one/account.py`). Two gaps:
   - An operator's **Give Credits** reaches them only as "OneAI credits
     were added. The workspace now has 3,200." The note the operator had to
     write ("sorry for the outage on the 12th") never reaches them, and
     Credits Added's own description says it is for packs and the plan.
     Recommended: the note travels with the grant (`proxy.hello`), and
     Credits Added says it when there is one.
   - Operators are told nothing, and need not be. Holds.
2. **OneAI**: nothing but "What stands out here?". The question here is a
   customer's: "where did our credits go?". Recommended: **Where did the
   credits go?** on an entry, and a reader, `credit_facts` (operator-only:
   the workspace's balance and held, each grant with what is left of it
   and until when, this month's spend by model, and the last grants with
   their notes).
3. **Intake**: nothing OneIntake reads lands here, and nothing should.
   Holds.
4. **Permissions**: One Operator reads; nobody writes, submits or cancels,
   and grants come only through Give Credits. Two gaps:
   - **A wrong grant cannot be undone.** Give 5,000 instead of 500 and the
     only way back is the database. Recommended: **Take Back** on an
     operator's grant, which writes a Spend of what is left of it (source
     Operator, with a note), so the ledger stays append-only.
   - **Share** is on, as it was on the other operator records.
     Recommended: off.
5. **Cross-module**:
   - A spend's **Note** is the model's id ("workers-ai:@cf/google/gemma-4…")
     and its **Reference** a run on the customer's site. Recommended: a
     spend shows **Model**, linked to OneAI's Models, and says what ran.
   - A plan grant's Reference is the plan's key ("starter"). Recommended:
     it links the plan; a purchase's Stripe session is **Open in Stripe**.
6. **UI and UX**:
   - a. **The list is 456 spends of about one credit.** The rows an
     operator comes here for, grants and refunds, are lost among them, and
     the spends are what AI Usage already sums. Recommended: the list
     opens on grants and refunds, with spends one filter away, and each
     workspace's balance stays on the workspace, where it is.
   - b. The list shows the **ID** column (CR-26-001204) and ID filter, and
     every credit to six places ("-1.047600"). Recommended: the workspace
     leads each row as on the other lists, and credits show two places.
     The **Kind** column repeats the indicator.
   - c. **A grant does not say what is left of it.** CR-26-000053 is 5,000
     credits expiring on 30 September, and nothing says 4,640 of them (5,000 less the 360 spent) are
     still there. Recommended: a Record Head sentence ("4,640 of 5,000
     left, until 30 Sep") and, on a spend, which grant it came from.
   - d. The form shows **Drawn From** and an empty **Grant** field on a
     grant, which is drawn from nothing, and the rows a caller wrote say
     "Created by Guest". Recommended: Drawn From only on a spend or a
     refund; the gateway writes as Administrator.
7. **Documented**: the README mentions Give Credits and the Credit Ledger
   on a workspace, but has no section saying what an entry is, what the
   kinds mean, or how a balance is made. Recommended: a **Credits**
   section.
8. **Legal**: the Terms say a plan's credits expire at the month's end and
   bought ones never do, but nothing about credits we give by hand, which
   may carry any expiry. Recommended: a sentence in the Terms' credits
   section (credits we give may expire on the date we say when we give
   them).
9. **Built from frappe**: a submittable doctype, its list and form. Holds.

Your word: all of them.

Done:

- **Take Back** on credits an operator gave writes a spend of what is left
  of them, with a note (`ledger.take_back`); the grant then says "50 of its
  50 credits were taken back", and the list shows it as **Taken back**.
  Plan and pack credits cannot be taken back.
- **The customer hears the note.** `proxy.hello` carries the last credits
  an operator gave (`ledger.last_gift`, not one already taken back), and
  the workspace says **Credits Added** once with "A note from One: …" and
  when they expire. Its description now names credits One gives.
- A grant's Record Head says what is left of it and until when, and where
  it came from ("4,640.08 of 5,000 credits left, until 30-09-2026. The
  plan's monthly credits."); a spend says which grant it came out of; a
  spend beyond the balance says it is owed.
- The list opens on what people did (grants, refunds, taken back), with
  calls one filter away; the workspace leads each row; no ID column or
  filter; credits to two places. (Kind was a filter, not a column.)
- A call's spend links its **Model** (AI Model) instead of a Note;
  `patches/credit_model.py` linked the 456 old ones. Spends a call wrote
  say Administrator, not Guest. **Drawn From** shows only on a spend.
  **Open Plan** on a plan grant, **Open in Stripe** on a bought one, and
  **AI Usage** in the menu. Share off.
- OneAI: **Where did the credits go?**, with `credit_facts`
  (operator-only). The queries it needs live in `ledger.py`, which stays
  the only module that reads the ledger (`tests/test_ledger.py`).
- README: a **Credits** section and an Under the hood line.
- Legal: the Terms say credits we give expire on the date we tell the
  administrators, and a mistake may be taken back; Terms revision 7.

### OneAdmin › Models

Models is the `AI Model` list: every model the two providers list
(Cloudflare Workers AI and Google AI Studio), synced nightly from each
provider's API with prices parsed from each provider's pricing page
(`catalogue.py`, `prices.py`). Nothing on it is typed. The operator decides
two things per model: whether it is **Offered** (workspaces may pick it) and
whether it is the **Default** for a capability (what an action runs on when
the workspace picked nothing). Its head says the markup in effect, and
**Price a call** makes and charges one real call. On the dev site: 120
models, 30 offered, 44 needing review, one default.

1. **Notifications**:
   - **The sync changes what customers get and tells nobody.** A model the
     provider stops listing is Withdrawn, and one whose price stops being
     readable comes off sale; if it was offered, or the default, the
     actions on it start failing with "not a model this account offers",
     and no operator hears of it until a customer does. Recommended: a
     **Model Withdrawn** notice to operators when an offered or default
     model goes, naming the actions that ran on it, and a Needs You row on
     Home until a default is set again.
   - A workspace that picked the withdrawn model for an action fails from
     then on. Recommended: it falls back to the default for that
     capability, rather than fail.
2. **OneAI**: nothing but "What stands out here?". Recommended: **Is this
   model worth offering?** on a model (its price after markup against the
   offered ones for the same capability, and what it reads), and
   **Which actions have no model?** on the list, with a reader,
   `model_facts` (operator-only).
3. **Intake**: OneIntake's readings run on these models (Read Scans, the
   intake actions), and depend on the defaults below. Nothing else lands
   here. Holds.
4. **Permissions**: One Operator reads and writes; only the operator's two
   decisions, markup and hand prices, are editable (`THEIRS`). Holds,
   except **Share** is on. Recommended: off.
5. **Cross-module**:
   - **Three actions have no model.** Only Text Generation has a default
     (Gemma 4). **Transcribe Interviews** and **Transcribe Recordings**
     (Transcription) and **Read Scans** (Vision) run only in a workspace
     that picked a model for them; everywhere else they fail. A
     Transcription model is offered (Whisper) and six Multimodal ones,
     none of them the default. Recommended: the head of a model says which
     actions it is the default for, and Home lists a capability an action
     needs with no default.
   - A model does not say which actions use it or which workspaces picked
     it. Recommended: both on its head.
6. **UI and UX**:
   - a. **Twelve filters in two rows** (ID, Provider, Name, Capability,
     Default For, Status, Text, Image, Audio, Video, Offered, Priced by
     Hand). Recommended: Provider, Capability, Status and Offered; the ID
     filter off.
   - b. **The list opens on 44 models needing review**, sorted by provider,
     and the 30 on sale are scattered among them. Recommended: offered
     first, then priced, then needing review, then withdrawn.
   - c. Names are cut off ("Model that perfor…", three "Antigravity
     Agent"s). Recommended: the Name column wider and the provider shown.
   - d. **Markup shows "0.0000"** when it is empty and the default applies,
     under a head that says "From the default". Recommended: empty shown
     empty, and the default named in its description ("Empty uses 2×").
   - e. A model needing review says the parser's reasons in a red
     paragraph, and not what to do about it. Recommended: a second
     sentence: price it by hand (tick Priced by Hand, add its rates) or
     leave it off sale.
7. **Documented**: the README has no Models section: what the sync does
   and does not decide, what offered and default mean, what Needs Review
   asks of an operator, and what Price a call costs. Recommended: a
   **Models** section.
8. **Legal**: Cloudflare and Google are OneAI's subprocessors
   (`one_ai/legal.py`), and a model from any other provider cannot appear
   here without code. Holds.
9. **Built from frappe**: a list with a row button, a form and a Record
   Head. Holds.

Your word: all of them, and Gemini is always the default: "gemini models are
much better for everything".

Done:

- **Gemini runs OneAI by default.** Gemini 2.5 Flash is the default for Text
  Generation (`patches/gemini_default.py`; Gemma no longer is). It reads
  text, pictures, sound and video, so **Transcribe Interviews**,
  **Transcribe Recordings** and **Read Scans** run on it too.
- **One rule for which model runs** (`actions.default_model`): the default
  set for what the action needs; else a default for something else that can
  do it; else the cheapest offered model from the **Preferred Provider**
  (One Admin Settings, Google). A workspace whose own pick is withdrawn or
  off sale falls back the same way instead of failing.
- **Model Withdrawn** tells the operators when the nightly sync takes an
  offered or default model off sale, and what runs instead; an action
  nothing can run is on Home, under Needs You (**No Model**).
- List: four filters (Provider, Capability, Status, Offered), no ID filter,
  and it opens on what is offered, then priced, then needing review, then
  withdrawn (`rank`). Share off.
- Head: the markup, which actions run on it for workspaces that picked
  nothing, and how many workspaces called it this month; a model needing
  review says what to do; a withdrawn one says nobody can pick it.
  **Markup** shows "Default, 2×" when empty instead of "0.0000".
- OneAI: **Is this model worth offering?** and **Which actions have no
  model?**, with `model_facts` (operator-only).
- README: a **Models** section, Model Withdrawn under Being told, and an
  Under the hood line.

### OneAdmin › AI Usage

AI Usage is a Script Report over the calls every workspace made
(`ledger.usage`, one settled Credit Reservation per call): from a date to a
date, cut **By** Workspace, Model, or both, with how many calls, the credits
charged, per call, and the last call. On the dev site this month: Nine X, 456
calls, 359.92 credits, on 35 models.

1. **Notifications**: it sends nothing. A workspace running low is already
   told on its own site (Credits Running Low), and a call that cannot be
   paid for is refused before it is made. Holds.
2. **OneAI**: nothing but "What stands out here?". The operator's questions
   here are "who is spending the most, and on what?" and "are we making
   money on AI?". Recommended: **Who is spending the most?** on the report,
   with a reader, `ai_usage` (operator-only: a period cut any of the ways
   below, with what it cost us).
3. **Intake**: OneIntake's readings are calls and are counted here, as
   their actions. Holds, once the Action cut below exists.
4. **Permissions**: One Operator, refused off the admin site. Holds.
5. **Cross-module**:
   - **It does not say what AI costs us.** Credits are what the workspace
     was charged; what the provider charged us is that over the model's
     markup, and the difference is the only margin OneAI has.
     Recommended: **Cost Us** and **Margin** beside Credits, in the
     price list's currency.
   - **It cannot say which OneAI feature spends.** Every call records its
     action (Summarise, Chat, Read Scans, the intake readings), and the
     report cannot cut by it. Recommended: **By Action** (and by Workspace
     and Action). The 456 calls on the dev site predate the action being
     written, so they will show as "Not recorded".
6. **UI and UX**:
   - a. **Everything is counted twice.** Our own Total row (359.92 credits)
     and then frappe's total row under it, which adds ours in: 70 models,
     912 calls, 719.84 credits. The report's JSON says no total row, and
     the site's copy says yes, so the JSON never synced. Recommended: one
     total, ours, bold.
   - b. The Model column shows the id ("workers-ai:@cf/google/gemma-…"),
     not the model's name. Recommended: the name.
   - c. Credits and Per Call to four places; Last Call cut off.
     Recommended: two places, and a wider Last Call.
   - d. The numbers that matter sit in a table row. Recommended: a summary
     over the table (Calls, Credits, Cost Us, Margin, Workspaces).
7. **Documented**: the README mentions AI Usage on the Credits screen and a
   workspace, but has no section. Recommended: an **AI Usage** section.
8. **Legal**: it reads what a call cost and which model and action, never
   what was asked or answered. Holds.
9. **Built from frappe**: a Script Report and its summary. Holds.

Your word: yes.

Done:

- **One total.** The site's copy of the report kept frappe's total row
  beside ours (`patches/ai_usage_one_total.py`), so the page said 912 calls
  and 719.84 credits for 456 and 359.92. Now it counts once.
- **What it cost us.** Each call now keeps what the provider charged for it
  (`Credit Reservation.usd`, written by `ledger.commit` from the gateway's
  bill); the calls before were worked back from their markup
  (`patches/call_costs.py`). The report shows **Charged** (the credits at
  what a dollar buys), **Cost** and **Margin**, per row and in a summary
  over the table (Calls, Credits, Charged, Cost, Margin, Workspaces). On
  the dev site: $0.36 charged, $0.18 cost, 2.0×; the old calls read exactly
  2.0× because their cost was worked back from the 2× markup, and new calls
  will show the real one.
- **By Action**, and Workspace and Action: which of OneAI's features spends.
  The dev calls predate the action being written and say "Not recorded".
- Models by name, credits to two places, money to four (a call costs
  fractions of a cent), Last Call in full.
- OneAI: **Who is spending the most?**, with `ai_usage` (operator-only).
- README: an **AI Usage** section and an Under the hood line.

### OneAdmin › Settings

Settings is `One Admin Settings`, one page: the connections OneAdmin runs on
(Frappe Cloud, Cloudflare, R2, Stripe, the AI Gateway), the money (credits
per dollar, default markup, the preferred provider, what each thing costs
us, the least margin), OneAI's persona, and the grace periods of the
ladder. **Set Up Cloudflare** finds or makes everything Cloudflare needs
from one token; **Try the Gateway** makes one call.

1. **Notifications**: nothing is said when these change. A new markup
   reprices every model and every AI call; new Stripe keys decide whether
   payments land. Changes are kept (Version), but nobody hears.
   Recommended: a **Settings Changed** notice to the other operators when
   anything under money, a key or a grace period changes, naming who and
   what (never the key's value).
2. **OneAI**: nothing but "What stands out here?". Recommended: **Is
   everything set up?**, with a reader, `settings_check` (operator-only):
   which connections are filled in and which are empty, what Set Up
   Cloudflare last said, and the money settings. Never a key.
3. **Intake**: nothing. Holds.
4. **Permissions**: One Operator reads and writes, refused off the admin
   site. Holds, except **Share** is on. Recommended: off.
5. **Cross-module**:
   - **AI Usage's Charged is wrong, and it was mine.** It priced a credit
     at Credits per Dollar (1,000 a dollar, so $0.001), which is what a
     dollar of *provider cost* becomes. A credit *sells* at a pack's
     price: $9 for 1,000, $0.009. So Charged read $0.36 where it was about
     $3.24, and the margin 2.0× where it was nearer 18×. Recommended: Charged
     at the smallest pack's price a credit, and Credits per Dollar's
     description saying it is the cost side, not the price.
   - The money here is used by Price Check, the Plan Calculator, the
     Models list and AI Usage, and none of them links back. Holds: Price
     Check has **Costs in Settings**.
6. **UI and UX**:
   - a. **One long page of eleven sections** mixing credentials with
     prices and the ladder. Recommended: frappe's tabs: **Connections**
     (Frappe Cloud, Cloudflare, Storage, Stripe, AI Gateway), **Money**
     (credits, markup, costs, margin), **OneAI** (preferred provider,
     persona), **Grace Periods**.
   - b. **Last Setup** is raw JSON in a code box. Recommended: the same
     table Set Up Cloudflare shows when pressed.
   - c. Nothing says what is missing. An empty Stripe webhook secret means
     every payment is refused, and the page looks the same as one that
     works. Recommended: a Record Head sentence naming what is not set and
     what it stops.
7. **Documented**: the README points at Settings from five places and has
   no section on it. Recommended: a **Settings** section.
8. **Legal**: the persona is sent to the model before every action, as
   every prompt is (the AI Addendum covers it). Holds.
9. **Built from frappe**: a Single doctype and its form. Holds.

Your word: all of them.

Done:

- **AI Usage prices a credit at what it sells for.** Charged is now the
  credits at the smallest pack's price a credit (`offerings.credit_price`,
  $0.009), not at Credits per Dollar. The dev month reads $3.24 charged,
  $0.18 cost, **18.0×**, where it read $0.36 and 2.0×. Credits per Dollar
  says it is the cost side and not the price of a credit.
- **Four tabs**: Connections, Money, OneAI, Grace Periods.
- **The head says what is missing and what it stops**, reading the site's
  config too where the code does (on the dev site: "Stripe's secret key is
  not set, so nobody can pay"); green when everything is filled in.
- **Last Setup** is the same table Set Up Cloudflare shows, not JSON.
- **Settings Changed** tells the other operators who changed what, with the
  old and new value of a price, markup or grace period, and only "(changed)"
  for a key, which is caught before frappe hides it.
- OneAI: **Is everything set up?**, with `settings_check` (operator-only,
  never a key). Share off.
- README: a **Settings** section, Settings Changed under Being told, and an
  Under the hood line.

OneAdmin is done: Home, Workspaces, Jobs, Log, Domains, Price List, Price
Check, Plan Calculator, Signups, Credits, Models, AI Usage and Settings.

### OneAdmin › Start (the signup page)

`/start` on the admin site, the first portal page: a guest names a
workspace, gives an email, picks where it runs and a plan, and is sent to
Stripe. `/welcome` is where Stripe sends them back. It answers 404 on a
workspace. Both are hand-written Jinja pages over `templates/web.html`
(`www/start.py`, `start.html`, `welcome.py`, `welcome.html`,
`public/css/portal.css`).

1. **Notifications**: the operators hear of a paid signup (Signup Paid) and
   of one not built (Workspace Delayed); the customer gets Stripe's receipt
   and, once built, the workspace's own set-password mail. Two gaps:
   - Somebody who fills the form and closes Stripe hears nothing, though
     the privacy clause already says we follow up. Recommended: one
     **Finish Signing Up** mail a day later, with a link back to the
     request's checkout, and never a second.
   - A signup whose build fails is told on `/welcome` only if they are
     still looking at it. Recommended: the customer gets a short **We Are
     On It** mail when Workspace Delayed goes to the operators.
2. **OneAI**: nothing, and nothing needed on a guest page (every call costs
   us and the guest has no credits). Holds. Operators already have OneAI
   on the Signups list.
3. **Intake**: nothing. Holds.
4. **Permissions**: guest, admin site only, both calls rate-limited at five
   a minute. One bug: the name check fires as you type (300 ms after you
   stop), so a name typed in bursts passes five in under a minute and the
   sixth answers 429, which the page drops silently and the hint freezes.
   Recommended: the name check at thirty a minute and the rejection caught;
   Start stays at five.
5. **Cross-module**:
   - The address preview is hard-coded `.t.4dl.app`, not the Tenant
     Domain in Settings (`tenant.py` reads it). Recommended: the page is
     given the domain.
   - **European Union** only moves the files: `storage._bucket` picks the
     EU bucket, but `_one_cluster()` ignores the choice, so the database
     runs wherever the one cluster is. And with no EU bucket set, the first
     upload fails ("No EU bucket is configured"). Recommended: EU is
     offered only when the EU bucket is set, and its note says what it
     does: "Files are kept in the European Union."
   - The quota line leaves out the database size the plan sells (Price
     List and the Plan Calculator both show it). Recommended: add it.
   - Only Starter has a description, so the four plans read unevenly.
     Recommended: a line each, written in Price List (data, not code).
6. **UI and UX** (a portal page is ours to draw, and should look like One):
   - a. The **email box is grey** and the name box white, so email looks
     disabled. Recommended: both the same, as frappe-ui's TextInput draws
     them (`surface-gray-2`, no border, a ring on focus), which is what
     every field inside One looks like.
   - b. The empty address hint leaves a gap under the name box.
     Recommended: the hint takes no room until there is something to say,
     and says it as "Your address: acme.t.4dl.app".
   - c. The chosen radio boxes are drawn with a heavy black border.
     Recommended: frappe-ui's selected look, a gray-7 ring, lighter.
   - d. The button only disables while it waits. Recommended: frappe-ui's
     loading button (spinner, "Taking you to Stripe…").
   - e. Errors land as raw server text under the button (a 429 reads
     "Too Many Requests"). Recommended: a frappe-ui-style error alert,
     with the rate-limit case in words.
   - f. No way in for somebody who already has a workspace. Recommended:
     a small **Already have one? Sign in** line under the lede, asking for
     the workspace name and sending them to its address.
   - g. `/welcome` does not move: it says "being built" and stays there
     until reloaded. Recommended: it asks every ten seconds while Paid or
     Provisioning and shows **Open it** the moment it is Done.
7. **Documented**: the README's Signups section is about the operator's
   list; nothing says what the page asks, what EU means or what happens
   after payment. Recommended: a **The signup page** section.
8. **Legal**: the customer pays before seeing a single agreement. The Terms
   are agreed on first sign-in, which binds them, but they have paid by
   then. Recommended: "By continuing you agree to the Terms of Service and
   the Privacy Policy" above the button, each a link, which needs the
   agreements readable without signing in: a public `/legal/<document>`
   route on the admin site from OneLegal's `assemble`. The first-sign-in
   acceptance stays; it is the record. The signup privacy clause
   (`oneadmin-signup`) holds.
9. **Built from frappe**: `frappe.call` and `__()` are frappe's; the
   inputs and radios are plain HTML, which a guest page has to be (the
   desk controls do not load on a web page). Holds, drawn to frappe-ui's
   look as 6 says.

Your word: all of them.

Done:

- **The welcome page needs the key.** `Account Request` has an
  `access_key`, Stripe's return links and the reminder carry it, and
  `/welcome` shows nothing without it (`signup.owned`). Found on the way:
  request names count up, so before this anybody could read anybody's
  workspace name and email by counting.
- **Closing Stripe lets the name go.** It was held for a week, so "Start
  again" and the same name answered "taken" to its own owner. Cancelling
  now marks the signup Abandoned (committed from the page, since frappe
  rolls a GET back).
- **Finish Signing Up**: one mail a day after an unpaid signup, never twice,
  with a link to `/welcome`, which offers **Continue to payment**
  (`signup.pay`, a fresh Stripe page: Stripe's own lasts a day). The second
  gap in finding 1 was mine: the customer already gets Workspace Delayed.
- **The agreements before payment**: "By continuing you agree to the Terms
  of Service and the Privacy Policy" above the button, each linking to a
  new public **/legal** page (every document, rendered by
  `assemble.render`, reading records nothing). A Terms clause says the
  signup page is where they are first agreed to (revision 8); the privacy
  clause names the one reminder (hash recorded).
- **The name check** is thirty a minute, and a refusal shows in the hint
  instead of freezing it. **Start** stays at five.
- **The address** reads Tenant Domain ("Your address: acme-labs.t.4dl.app")
  and takes no room until there is one.
- **Where files are kept**: offered only when the EU bucket is set, and
  says the EU keeps the files.
- **The plan line** has the database.
- **The look**: the inputs are frappe-ui's subtle TextInput exactly (the
  grey was already that; the name box was white only because it had focus,
  so 6a was half wrong), a lighter chosen ring, a spinner and "Taking you to
  Stripe…" on the button, and errors in a frappe-ui alert, with a 429 said
  in words.
- **Already have a workspace? Sign in** finds a live workspace by name
  (`signup.where`) and opens its sign-in.
- **/welcome** reloads every ten seconds while it is built, so **Open it**
  appears by itself. The workspace name and email it shows are escaped.
- README: **The signup page**, Finish Signing Up under Being told, and an
  Under the hood line. Plan descriptions (5, last point) are Price List
  data, left for you to write.

### OneAdmin › Welcome (the page after Stripe)

`/welcome` is where Stripe sends somebody back, paid or not. It opens only
with the signup's key (from the start pass), reads the signup, and says one
of six things: not paid yet (with **Continue to payment**), being built or
trial started (looking again every ten seconds), ready (**Open it**), could
not be built, closed without paying (**Start again**), or not found.

1. **Notifications**: the page sends nothing. What it promises is true: the
   set-password mail, Workspace Delayed on a failure. One gap: since the
   account, whoever paid also has a One account, and the page never says
   so. Recommended: ready and being built say "It is in your One account"
   with **Sign in**.
2. **OneAI**: nothing, and nothing needed on a guest page. Holds.
3. **Intake**: nothing. Holds.
4. **Permissions**: guest, admin site only, the key or nothing. One leak:
   the key is in the address, and **Open it** and Stripe are other sites, so
   the browser sends this address to them as the referrer. Recommended: the
   page asks for no referrer (`<meta name="referrer" content="no-referrer">`).
5. **Cross-module**:
   - **Open it** goes to the workspace's given address (`Tenant.domain`),
     not its own domain when it has one, and to the front page rather than
     the sign-in. Recommended: `primary_domain` first, and `/login`.
   - Ready on a trial says nothing about the trial; only "being built" did.
     Recommended: "Free until {date}" under it, from the plan's trial days.
   - **Start again** after closing Stripe opens an empty form, though we
     know the name and plan they chose. Recommended: `/start` filled in.
   - Could not be built gives nothing to quote. Recommended: the signup's
     number and "reply to the mail we sent", so support can find it.
6. **UI and UX**:
   - a. While building, the whole page reloads every ten seconds, which
     flickers and redraws everything. Recommended: ask for the status with
     one `frappe.call` (`signup.state`, key-checked) and swap the text in
     place; reload only when it changes.
   - b. "This takes a few minutes" is said forever. A build stuck for an
     hour still says it. Recommended: after fifteen minutes, "This is taking
     longer than usual. We will mail you when it is ready."
   - c. Ready shows the signup's name, which on a quick signup is the slug
     (`acmeco`). Recommended: the workspace's name from the Tenant.
7. **Documented**: README's The signup page covers it in two lines.
   Recommended: a line each for the states above, once they change.
8. **Legal**: nothing new. Holds.
9. **Built from frappe**: `frappe.call` and a page template. The reload loop
   is ours and goes with 6a. Holds otherwise.

Your word: all of them.

Done:

- **The key stays on this page.** `/welcome` asks for no referrer, so
  **Open it** and Stripe are not told its address.
- **Open it** goes to the workspace's own domain when it has one, and to
  its sign-in.
- **No more reloading.** While it is built the page asks `signup.state`
  (key-checked, rate-limited) every ten seconds and reloads only when the
  status moves; after fifteen minutes it says the build is taking longer
  than usual, and that we will mail when it is ready.
- **Ready** shows the workspace's own name (Acme Co, not acmeco) and "Free
  until" on a trial; **could not be built** gives the reference to quote.
- **The account**: paid, being built or ready say it is in their One
  account, with **Sign in**; a signed-in person gets **Back to your
  account**.
- **Start again** fills `/start` with the name and plan they had chosen,
  and the address check runs at once.
- README: The signup page says what `/welcome` shows now.

### OneAdmin › The lifecycle (Frappe Cloud, benches, sites)

Not a screen: the path a workspace takes from payment to deletion, read end
to end. Payment (`signup.accept`) makes a Tenant and a Provision job; the
runner (every two minutes, five jobs a tick) walks `name_is_free`,
`create_site` on the first bench group and its first region, `site_is_up`,
`route_it` (our name at the edge), `push_config` (token, host name, mail
secret), `invite_owner` and `live`. A failed payment starts the ladder:
Overdue, then Suspended (`deactivate`), Archived (backup noted, site
archived, edge unrouted) and Dropped (files deleted), one rung a night, each
a job. Paying climbs back from Overdue or Suspended. Nothing is stored about
Frappe Cloud but what a Tenant needs; benches, regions and plans are asked
for and cached a minute.

The design holds: every step is safe to run twice, nothing unwinds, a failed
fall leaves the workspace where it was. What does not hold, worst first:

1. **Paying an archived workspace breaks the webhook.** `lifecycle.paid`
   throws for Archived, the webhook re-raises, and Stripe redelivers the
   event for days. The customer has paid and nobody is told. Recommended:
   no throw; the payment is recorded, the operators are told (Paid While
   Archived), and rebuilding or refunding is their decision.
2. **Stripe is never told a workspace has gone.** Archive and Drop leave the
   subscription running, so Stripe keeps invoicing a workspace that no
   longer exists, and a customer who comes back pays for nothing.
   Recommended: the Archive walk cancels the subscription (a step,
   `stop_billing`, safe twice).
3. **Archiving leaves the mail route.** `unroute` deletes the edge key
   `values/{slug}` but not `values/mail:{slug}`, so the mail Worker keeps
   accepting mail for an archived workspace, storing it in R2 and knocking on
   a site that is gone. Recommended: `unroute` deletes both.
4. **The site is created with no Frappe Cloud plan.** `create_site` names no
   plan, so press gives its default, and the plan that fits the database the
   customer bought is only set the next time their plan changes
   (`quota.apply` is never called at signup). Recommended: `create_site`
   asks for `quota.press_plan_for(database)` and records it.
5. **A Frappe Cloud outage stops every signup.** `signup.start` asks press
   for a region before the request is even written, so when press is down
   the signup page answers "That did not work" (seen on the dev site).
   Recommended: the region is chosen by the job, not the page; the signup is
   taken, paid for, and built when press answers.
6. **A slow build is failed at about forty minutes.** Waiting on
   `site_is_up` counts as an attempt, and twelve attempts with the backoff
   is about forty minutes, after which the workspace is marked Failed and
   the customer mailed Delayed, though press may finish at minute
   forty-five. Recommended: waiting on press does not count toward giving
   up; a real error does. A build still waiting after three hours is put on
   Home instead.
7. **The bench and the region are "the first one".** `_bench_for` takes the
   first bench group the team owns and `_one_cluster` its first region, with
   no check that the bench carries erpnext, hrms and onedesk. A second bench
   group (a staging one, an old one) could take new customers.
   Recommended: Settings names the bench group new workspaces go on (chosen
   from press's list), and `name_is_free` refuses a bench missing an app.
   The EU choice picks an EU region when that bench offers one.
8. **Updates are nowhere in OneAdmin.** A new One release reaches customers
   when the bench group is deployed in Frappe Cloud's dashboard; OneAdmin
   neither starts it nor says which release each workspace runs.
   Recommended, smallest first: Home says when the bench group has an
   undeployed update and which release workspaces are on (both are press
   reads); starting the deploy stays in Frappe Cloud for now.
9. **Unchecked: whether Frappe Cloud bills a deactivated site.** Suspended
   workspaces are deactivated, not archived, for fourteen days. If press
   charges for them, a non-paying customer costs us two weeks of hosting.
   Recommended: I check press's billing for inactive sites and say so in
   the README; no code unless it does.

**Your word:** fix all of them, knowing the servers are ours: we rent them
from Frappe Cloud, a server takes unlimited benches and sites, and customers
never know Frappe Cloud is there.

**Done.**
1. `lifecycle.paid` no longer throws for an archived or dropped workspace:
   the payment stands and the operators get **Paid While Archived**
   (rebuild from backup, or refund in Stripe).
2. Archive has a **Cancelling its subscription in Stripe** step
   (`stop_billing`, `stripe.cancel`, safe twice: a subscription already gone
   or cancelled is fine).
3. `cloudflare.forget` deletes `mail:{slug}` with the address.
4. Reversed, given the servers are ours: a site on our own server has no
   press plan and no database limit, so `quota.press_plan_for`, `quota.move`
   and the nightly retry are gone. The database is watched by us: Home shows
   a workspace **Over Database**.
5. The server and bench are chosen by a new first step, **Choosing the
   server it goes on** (`place_it`), not by `/start`, so a Frappe Cloud
   outage no longer stops a signup; the job waits instead.
6. Waiting is not failing: a step waiting on Frappe Cloud is checked every
   minute and never uses up an attempt (`runner._waiting`). A build still
   waiting after three hours is on Home as **Slow**.
7. Settings gains **Server** and **Bench Group**. `place_it` refuses a bench
   group missing erpnext, hrms or onedesk, saying which to add, and an EU
   workspace goes on an EU region when there is one. Checked read-only
   against the real account: bench-46919 is refused for onedesk, which it
   does not carry yet (it has oneapp and oneapp_control); with onedesk
   pretended in, it picks Nuremberg-3.
8. Home shows **An update is waiting for bench-46919** with the apps that
   have one (read from press, seen live). Deploying stays in Frappe Cloud.
9. Moot: the servers are ours at a flat price, so a deactivated site costs
   nothing extra. The Frappe subprocessor entry now says Frappe Cloud runs
   servers rented for One alone, in Nuremberg.

**Proven with a real site** (onetest-8dbda.frappe.cloud, built with frappe
only, then archived). Frappe Cloud's own code showed my first `create_site`
was wrong: naming a server without the bench group's version sends press
down a path that deploys a new private bench group, and a site on our
server only lands there on a free dedicated plan. `create_site` now names
the server, the group's version (read from press) and Settings › **Site
Plan** (default Unlimited - Hetzner), and `place_it` refuses when no Server
is set. Built this way the site was Active in about a minute.

**The server list** (your word, after asking whether it is set and forget).
Settings' one Server became **Servers**, a table (`Workspace Server`): each
row a server bought in Frappe Cloud and added to the one bench group, its
region read back from Frappe Cloud on save, **EU**, **Open** and **Most
Workspaces**. `place_it` puts a new workspace on the emptiest open server
that may take it (EU only on EU rows), has room and carries the bench group
(`press.api.bench.all(server=)`), and records it on the Tenant's new
**Server**. None fitting fails the job saying what to buy; Home warns at
four-fifths full, and when no open server is left for new or EU
workspaces. A patch moves an old Server setting into the first row.

### Frappe's doctypes, against One (before finishing One and OneAdmin)

Not a screen: what frappe does that a workspace cannot reach once the
Framework app is gone. `docs/DESK-COVERAGE.md` answers all 194 doctypes that
are not child tables: 36 are in One, 57 run underneath, 31 are the platform's
and 15 are the website builder. 55 are worth adding. In the order a new
workspace meets them: Import and Export, Numbering, Printing, Mail Templates,
Approvals and Automations (P1); Access, Reports and Dashboards, Recycle Bin,
Audit Log, Privacy Requests and Integrations (P2); and a handful of small ones
(P3).

**Your word:** plan it around frappe's per-doctype Settings dialog; Import and
Export is a different feature, later. The plan is in `docs/DESK-COVERAGE.md`:
One's own Settings item beside Customize opens frappe's dialog, each stage
grants what its tabs read (and a Custom Role for the print and workflow
builders), and every route a tab opens is in One's sidebar. Six stages: the
door, Numbering, Printing, Mail Templates, Approvals, Automations.

**Stage 1, the door: done.** Settings sits beside Customize on a form's and
a list's menu for a workspace administrator, and opens frappe's dialog with
General and the workspace's own Notifications rules; a rule opens, or a new
one starts on that doctype, in Workspace › Notifications with One's sidebar.
Found on the way: since the One account, every desk user on the admin site
was sent to `/account` after signing in, because frappe asks the website-user
home page hook for desk users too; it now answers `account` for Website
Users only.

**Stage 2, Numbering: done.** Settings › Numbering on any record numbered by a
series, and Workspace › Numbering listing them all with the real next name.
Series are added, renamed, made the default or deleted, and moved on (never
back), through `one/numbering.py` rather than Document Naming Settings, whose
methods run for anybody who can read it. Frappe's General tab is held back:
it saved Accounts Settings just by opening.

**Stage 3, Printing: done.** Settings › Print Formats on any record: preview,
star the default, New, and open one in frappe's print format builder, which
the administrator now reaches. Workspace › Printing lists the letter heads
(an image at the top and one at the foot) and the formats the workspace made.
A printed page runs on the workspace's own address, so what the workspace
writes into one is held to the builder's escaped blocks: no raw HTML or Typst,
no hand-written format, no HTML letter head, no style that loads from
elsewhere, checked on save and on the builder's live preview. Found on the
way: a letter head picture kept in One's store never printed.

**Stage 4, Mail Templates: done.** Settings › Mail Templates on any record
(new, edit, set the default the composer starts with) and Workspace › Mail
Templates listing all of them, each opened in One's own editor. A template the
workspace writes may only add field names, `{{ customer_name }}`; what a
shipped template already did stays, so HR's leave and interview mails can be
reworded but not given new code, since a template runs as whoever sends it.

**Stage 5, Approvals: done.** Settings › Approvals on any record and
Workspace › Approvals, each opening frappe's workflow builder, which the
administrator now reaches. An approval the workspace writes runs no code: no
condition on an action, no worked-out value, no tasks, and a state sets only an
ordinary field. Steps waiting on one of your roles count in Approvals Waiting on Home.

**Stage 6, Automations: done.** Settings › Automations on any record and
Workspace › Automations, each opening frappe's own automation form with One's
rail. An automation the workspace writes runs as whoever saved it, decides by
its field rules only (no code condition, no If step), runs no script, names
only fields in its values, and calls webhooks over https. That completes the
six stages of the door.

**Passed together: stage 1, the door.** Found: the Numbering tab was labelled
Naming; the panel cannot be opened over the dialog, and should not be. Done:
the tab reads Numbering. OneAI works the numbering from outside the dialog
instead: `workspace_numbering` reads a kind of record's series, the name the
next one gets, its counter, and the highest number its records already carry
(read from their names), and `change_numbering` suggests series added,
changed, reordered or removed and a counter moved on, as a Numbering card the
administrator approves; it is told every part a series may have, frappe's and
erpnext's (`YYYY`, `YY`, `MM`, `DD`, `JJJ`, `WW`, `FY`, `TFY`, `ABBR`,
`{field}`, `timestamp`, `#`), and checks a series the way frappe will before
suggesting it. A counter can no longer be moved below the highest number a
record already has, by hand or by OneAI, and the edit window says what that
is. Workspace › Numbering offers two suggestions.

Then, on your word: the Add Series window shows the name a series would give
next as it is typed, or what is wrong with it. A Customer, Supplier, Item or
Employee can be named by its name or by a series, from the top of its
Numbering (the app's own setting, applied by the app's own method; OneAI can
suggest it too). **Rules** (frappe's Document Naming Rule) name a record by a
prefix of their own when its fields match, held to the kinds Numbering covers,
a plain prefix and the record's ordinary fields. How a Series Is Written is
One's own text, naming no product.

Then: any kind of record can be named by one of its fields, not only the four.
**Name each new ... by** says Naming Series or Field, and Field asks which one:
frappe's `autoname` written as `field:<fieldname>`, as Customize Form writes
it, with the series hidden and the field made required; a second record with
the same value is refused by the name itself. The kinds that name themselves
in code (Customer, Supplier, Item, Employee, and now Campaign) ignore that, so
they keep their app's own choice. On the way: switching those four never took,
because their code reads a global default the Settings' save writes and the
switch did not; it writes it now. Workspace › Notifications says Mailed by
OneHR, OneBook, OneInventory or OneCRM, read from the type's product rather
than typed, instead of ERPNext or HRMS.

Then the three gaps, closed as frappe closes them. **Unique**: a field a record
is named by is marked unique with the index Customize Form adds, refused first
with frappe's own duplicate query, and unmarked when the kind is named some
other way. **Every kind**: Numbering is on frappe's own tab condition (read on
Document Naming Rule, now granted), and offers frappe's own naming choices on
any kind the administrator can make: Naming Series where it has one, Field,
Expression (old style, written as a series is, with the next name shown as it
is typed), Set by User and Random. Autoincrement, UUID and By script are not
offered; ledgers, logs and One's own kinds are named by the code that writes
them, so they only take rules. **OneAI**: `workspace_numbering` reads the
naming, the series and the rules with their conditions; `change_numbering`
suggests any naming choice and rules added, changed or removed, each checked as
frappe checks a rule before the card is offered, and saved as frappe's own
Document Naming Rule on approval. Nothing renames a record already made.

Then Workspace › Numbering was brought into line with the dialog: it read only
series, so a Customer named by its name showed a series' next name, and a kind
named by a field or an expression was missing. Each row is now read from the
dialog's own `naming_by`: Named By, Series or expression, Next only where it
can be known, and Rules. It lists kinds with a series, kinds the workspace
changed and kinds with rules; **Set Up Naming** opens any other; the list is
read again when the dialog closes.

**Stage 2, Numbering: passed, most of it during stage 1.** Checked on the nine
points:

1. Notifications: nothing is sent, and nothing should be. Every change is kept
   by frappe already: Property Setter and Document Naming Rule both track
   changes, and a counter moved is a Version on Document Naming Settings.
2. OneAI: reads naming, series and rules, suggests any of them as one card
   (done in stage 1). Workspace › Numbering offers two suggestions.
3. Intake: **finding.** Intake makes Task, Event, Contract, Purchase Invoice,
   Bank Transaction and Employee records in code, without a name. Set by User
   on any of them makes Intake's save fail ("Please set the document name"),
   and so does naming by a field Intake does not fill.
4. Permissions: workspace administrators only (roles.require), each door
   guarded to a kind they can read, naming changes only on kinds they can make.
   Holds.
5. Cross-module: the same as 3 for any module whose code makes records (OneHR's
   check-ins, OneBook's payments): the kinds a module makes are not declared
   anywhere Numbering can read.
6. Bespoke UI: frappe's dialog, FieldGroup and EmbeddedList, sections on the
   page. **Finding:** Add Series shows the next name as it is typed; Add Rule
   does not.
7. Documented: the README's Numbering section and A Form's Settings are
   current; `docs/DESK-COVERAGE.md` stage 2 still says rules are not offered
   and only series kinds are covered. **Finding.**
8. Legal: nothing leaves the workspace; no clause.
9. Built from frappe: frappe's own naming, NamingSeries, Document Naming Rule,
   Customize Form's autoname and unique, frappe's Settings dialog.

Fixed, all three. `hooks.py` `one_makes_records` names every kind a module's
code makes without a name (found by reading every insert in the app: ten
modules, 63 kinds), and on those Numbering offers no Set by User and only
fields that are always filled, and says why; OneAI is told the same. Add Rule
shows the name the rule would give next, as frappe's Document Naming Rule makes
it, or what is wrong with the prefix. DESK-COVERAGE's stage 2 says what is
built.

Then, on your word, one reading of a kind for everything that fills one in.
`one_ai/kind.py` is it: `describe` (every field, its type, choices, links,
required, unique, and how a new one is named), `fields_of`, `missing` (frappe's
required fields plus the name where the kind is named by a field or typed) and
`ready` (frappe's own checks, rolled back). OneAI's cards, its describe_type
tool and its messages read it; a card now knows a typed name (`__newname`).
Intake uses it at the save: while Intake makes a record, `one_intake/fill.py`
asks OneAI (`intake_fill`) for the name before frappe names it and for every
required field still empty after validate, from the document only; what the
document does not say stays empty and the record waits for a person. So a
required field added on Customize no longer breaks Intake, and Intake is off
`one_makes_records`: the list is now only code that has no model to ask.
Checked live, two calls: a Task typed by name with a required description, made
from the Stadtwerke invoice, was named `RE-2026-1100` and described "Pay invoice
RE-2026-1100 from Stadtwerke Köln GmbH for 84.2 by 2026-09-15" (rolled back).

**Stage 3, Printing: done.** Seen as a workspace
administrator: Workspace › Printing, the Print Formats tab, a letter head, the
builder, and printing an invoice.

1. Notifications: nothing is sent and nothing should be.
2. OneAI: **finding.** Nothing. No suggestions on Workspace › Printing, no tool
   that reads the formats, the defaults or the letter heads, and no card to set
   a default format or letter head.
3. Intake: nothing to take in here.
4. Permissions: the held door (printing.py) and the builder through a Custom
   Role hold. The print view's own checkboxes are per print, not saved.
5. Cross-module: **finding.** Printing an invoice on the Modern formats or the
   Company Letterhead opens ERPNext's "Enter Company Details" (logo, website,
   phone, email, address) every time until the company has them, while
   Workspace › General already asks for the logo and an address, in other words.
   **Finding:** a new letter head does not start with General's logo.
6. Bespoke UI: **findings.** The print view's sidebar is frappe's Printing
   workspace (Print Format, Print Heading, Letter Head, Builder, Print Settings
   lists), not the record's app. A new print format starts from every field the
   kind has, internal switches included (Is Consolidated, Update Billed Amount
   in Sales Order, Scan Barcode). The letter head window shows Height as
   `40.000` and the logo as its storage address, and has no preview.
7. Documented: the README's Printing section is current.
8. Legal: a PDF is made on the workspace's own server; nothing leaves it.
9. Built from frappe: frappe's builder, its tab and its dialogs.

All five fixed:

- General has an **On Documents** section: the logo, phone, email, website
  and the company's address. They are the Company fields and the company's
  own primary Address that ERPNext's prompt checks, so with them filled an
  invoice prints with its logo, address and contacts and nothing asks.
  (ERPNext reads the address with the printer's own Address permission,
  which OneBook's User level carries.)
- The print view keeps the record's app sidebar: `desk.js` reads
  `print/<doctype>/<name>` as that doctype for frappe's sidebar lookup.
- **New** on the Print Formats tab asks for a name and what to start from: a
  copy of a format the kind already prints with (its default first, blocks
  the builder would refuse left out), or every field. `printing.new_format`
  copies with `frappe.copy_doc`.
- The letter head window shows the top of a page as it will print, Height
  as a whole number, the logo by its file name, and a new one starts with
  General's logo.
- OneAI reads the letter heads, formats and defaults (`workspace_printing`)
  and suggests a letter head from the logo, the default letter head or a
  kind's default format as a Printing card (`change_printing`); two page
  suggestions on Workspace › Printing.

**Printing, second pass: HTML, the letter head builder, OneAI designs.** Asked
for after the five: whether formats should be HTML, a builder for letter
heads, and OneAI designing both.

- Builder formats stay the base, with **HTML blocks allowed**
  (`one/print_html.py`). A block's Jinja is checked to read the record and
  nothing else, since frappe's render globals read any table
  (`frappe.db.sql`) and fetch any address (`make_get_request`). A block the
  workspace saves is marked, and onedesk's copy of frappe's HTML block macro
  renders it in a sandbox holding only the record, escaping every value, with
  the markup cleaned (nh3: no scripts, forms, frames or media; pictures only
  this site's files). Typst stays refused. An Image block's `image_url` is now
  checked too, which it was not.
- **Letter heads may be HTML**, top and foot, with no template tags (frappe
  renders them raw at print), stored cleaned. They are designed in **frappe's
  builder**, whose letter head zones already edit both. `Design` points a
  designer format, kept off and out of every list, at the letter head. Our
  window shrank to name, Default, Off and a sandboxed preview.
- **OneAI**: `print_layout` reads a kind's fields and a format as sections;
  `design_print_format` takes sections of columns of blocks, compiled to the
  builder's layout and held by the same checks; `change_printing` takes
  `top_html`/`foot_html`. Cards carry **See the Page**. Checked live on
  gemini-2.5-flash-lite: the whole builder layout as one argument came back
  malformed, which is why the tool takes the compact form.
- Found on the way: frappe's XSS filter rewrote an AI Chat's JSON once a tool
  answered with markup, so the conversation would not load. `turns` now
  carries `ignore_xss_filter`.

**Letter heads, one part at a time: the header. Fixed.**

1. A header is one picture (aligned, sized) or HTML written by hand. The usual
   header, a logo with the company's name, address and contacts beside it,
   needs HTML, which an administrator does not write.
2. A header does not follow the company. It may hold no template, so a header
   written from General's details keeps them as they were when it was written.
   ERPNext's own Company Letterhead reads the logo, name, address and contacts
   when the page prints.
3. The builder's picture mode offers "or image URL", which the save then
   refuses for any address off this workspace.
4. The header is designed on a page called "Print Format / Letter Head
   Designer", beside a whole invoice and its layer tree. The letter head's
   own name is only in the inspector.

Fixed with presets. A header is now one of five tops (Classic, Centred,
Banner, Minimal, Logo Only) that `one/letter_heads.py` draws from General: the
logo, name, address, phone, email, website, tax ID and a new **Brand Colour**
on Company. The letter head keeps its choice (`one_top`), and the top is
drawn again whenever the letter head, the Company or its address is saved, so
it follows the company as ERPNext's own letter head does. The window shows
the five as they print with the company's details, what they show, the logo's
height and a page preview. Write It Yourself is the builder, for the rare
hand-written top. OneAI's `change_printing` suggests a preset. The picture
URL box and the designer's framing are left as they are: the builder is now
only the advanced route. Found while checking the print: frappe's stylesheet
stretches any picture inside a table cell to the cell's width, so the presets
lay out with table-display divs and give the logo its width from its own
proportions.

Then, on the renders: Classic's contacts line wrapped the tax ID, so the tax
ID now prints on its own line in every preset. Minimal carries the logo
beside the name. A sixth preset, **Logo and Details**, puts the logo on the
left and the company in two columns beside it, where it is and how to reach
it, each line after one of frappe's Lucide icons in the Brand Colour. frappe's
XSS filter takes inline pictures out of a letter head's top, so the top is
filtered in `validate_letter_head` instead: a drawn top is ours and escaped,
any other gets frappe's own `sanitize_html`. The other presets that show details (Classic,
Centred, Banner, Minimal) carry the same icons inline, the contacts kept whole
each on one line; Logo Only shows none. Logo and Details was then drawn again: the logo with
the name and the address under the name beside it, and the contacts and tax
ID on the right. The Brand Line, the line in the colour under the top, is a
tick in the letter head window (`one_top.line`) and every preset leaves it out
when it is off.

**Letter heads, the foot. Fixed.**

1. The foot was the builder's alone: a picture or HTML written by hand, with
   nothing drawn from General, so the usual foot (the company and its
   contacts, a thank-you) needed HTML nobody writes.
2. frappe's XSS filter took the icons out of a foot as it did from the top.
3. A foot that carried a page number would print it twice: frappe's new
   print formats draw their own (Print Format's `page_number`) on every page,
   and the browser's print preview repeats the foot on every page with no way
   to count them.

Fixed the way the top was: three feet (Centred, Two Sides, Band) that
`letter_heads.draw_foot` draws from General, kept on the letter head as
`one_foot`, drawn again when the company changes, and left alone once changed
by hand in the builder. The window has a Foot section under the Top: the three
and None as cards, Shows, a Note and the Brand Line. `footer` skips frappe's
XSS filter as `content` does, and `validate_letter_head` filters any foot not
drawn here with frappe's own `sanitize_html`. OneAI's `change_printing` takes a
`foot`. Page numbers stay the print format's. Then, on the renders: each foot said
everything the top already says, on two or three lines, and had no logo. A foot
is now one quiet line: a new one shows the website and the tax ID, a Logo tick
puts a small mark at its start, Two Sides has the logo and name on the left and
the rest on the right, and the note sits under the line. Two more followed, Logo Above and Spread,
and Band, which had ignored it, takes the Brand Line like the others. The window,
one long scroll by then, splits into a Top tab and a Foot tab under the page they
make, with Default and Off below both (a FieldGroup inside the dialog, since a
dialog with tabs puts every field in one). The tabs are frappe's own
`frappe.ui.Tabs` (frappe-ui's Tabs as the desk ships them), a FieldGroup in
each; the form's tab row restyled by hand is gone, and `test_borrowing` now
refuses a stylesheet or template that draws tabs of its own (`.form-tabs`,
`.nav-link`, `role="tablist"`). Then the words: the window says Header and
Footer, not Top and Foot, and so do its messages and OneAI's card. And Spread,
whose cells were each as wide as their text so the middle one sat off the
page's centre, gives every detail an equal share of the width (`table-layout:
fixed`): with three, the middle one is centred on the page, measured.

**Letter heads and OneAI. Fixed.** OneAI could make a letter head from any
preset or write one in HTML, but not change one well:

1. `workspace_printing` named each letter head without saying what its header
   and footer were, so "change our letter head" was a guess.
2. A change replaced the whole preset: asking only to turn off the footer's
   line reset its ticks and note. It could not set the footer to None.
3. HTML it wrote could not carry the icons the presets draw.
4. Its suggestions still said "top" and none was about the footer.

Now `workspace_printing` gives each letter head's header and footer as they
are (`_letter_head_part`: the preset and its settings, or the HTML or picture,
inline pictures shortened) and every preset to choose from; `change_printing`
merges what it is given into what is there, takes a footer of `none`, and
refuses a partial change to a header or footer that is not drawn from a
preset; `[icon:name]` in any letter head's HTML is drawn as that Lucide icon
(`letter_heads.icons_in`, called by `print_html.letter_head_html`); and the page
offers Suggest a Letter Head, Tidy Our Footer and Design a Letter Head. Checked
against the site: a footer-line change left the preset, ticks and note alone
and touched no header, None cleared the footer, `[icon:phone]` drew while an
unknown name stayed as written, and a change to what is already so was
refused.

**Print formats and OneAI. Fixed.** OneAI already designed with the builder's
blocks, not HTML, but its results would not have been consistent:

1. It knew the grammar of a layout and nothing of what a good one is, so two
   requests for the same invoice came out as two pages.
2. It wrote its own CSS for every format.
3. It had part of the builder: no label changes, hidden or inline labels,
   alignment, bold, barcodes, table headings, and no page number setting.
4. Nothing checked a layout before the card: an empty section or a table wider
   than the page reached the person.

Now `print_layout` offers a `starting_layout` from `print_recipes.py` (a
document of trade: party left, dates right, items table, totals beside the
amount in words, terms last; anything else: main fields in two columns, up to
three tables, long text last) and the rules say to change only what was asked;
the format prints in frappe's own style with no CSS unless a look is asked for;
blocks take `label`, `show_label` (hide or inline, frappe's words), `align`,
`bold`, `show_empty`, table headings and `bordered`, and `{barcode, format}`;
`page_number` is a format setting; and `_built` sends back a layout with an
empty section, a table without columns or wider than the page, a field given
columns that is not a table, or a barcode of a missing field. Checked on the
site: Sales and Purchase Invoice formats made from their starting layouts
print in the same look as frappe's Standard, tidier; tables no longer print a
label frappe's own formats leave off.

**The house style, Jinja, and two live runs. Fixed.** The spacing was frappe's
default: the table touched the totals, every table was boxed, and the totals
read as `Net Total:` far from its figure. Now:

1. **A house style.** `print_recipes.HOUSE_CSS` goes on every format OneAI makes
   unless a look is asked for. It uses frappe's own print classes and greys:
   - labels small and muted, and room between sections;
   - tables lined under a soft rounded header;
   - the grand total set off above a rule.

   The totals are a `labels_beside` section (frappe's `field_orientation`) with
   `spread` fields (its `label_justify`) in a 45% column (a column `width`).
   Tables are lined unless `bordered` or `striped`, because frappe boxes a
   table unless told not to.
2. **Their taste wins.** Their own CSS replaces the house style, or goes over
   it with `house_style`. Left out on a changed format, it keeps that format's
   own CSS. `print_layout` reads the house style back as `house_style: true`.
   A typeface is frappe's own `font` (Google Font) on the format, so Google
   Fonts is now a subprocessor (subprocessors revision 4).
3. **Jinja.** `LAYOUT_HELP` now names exactly what the sandbox in
   `print_html.py` allows:
   - `doc`, `loop`, `_`, `get` and `get_formatted`;
   - conditions, loops and `set`;
   - every allowed test and filter.

   It also says what is not there: no `frappe`, `frappe.db` or other records,
   no macros or `|safe`. A test reads the lists back from the sandbox.
4. **Live, on the workspace's own model (flash-lite).** Both runs found real
   faults, and both now hold:
   - It never called `print_layout`. It wrote the table as
     `"items", {columns}`, columns as `{field, width}`, widths as `"45%"`, and
     Python's `True` inside the JSON. These are now read as meant.
   - Its first layout had no customer and no total. A document of trade now
     has to print both (`print_recipes.essentials`).
   - Given an error, it apologised to the person instead of retrying. A failed
     design now comes back with `mend`, the starting layout and the rules, and
     the loop asks once for the call again (`MEND_IT`). The superseded apology
     is taken back (`_unsaid`).
   - When a design still did not hold, the "now answer" nudge made it say the
     format was created. It now says nothing was made (`GAVE_UP`).
   - Left out, `sections` prints the starting layout, or keeps a changed
     format's own layout, so a restyle changes only its look.

   House run ("a clean, polished invoice"): the starting layout in the house
   style. Creative run ("boutique, serif, charcoal band, striped rows, teal
   total"): Playfair Display, the band, the striped rows and the teal grand
   total, all written over frappe's classes.

**The company's lines in the header. Fixed.** Classic printed the address a
line at a time, gave the company only half the width so the contacts wrapped,
and put the room between contacts after each one, so a wrapped line ended 12px
short of the right edge. Every preset now reads as the name, the address on
one line, the contacts on one line and the tax ID on its own. The room is
before each contact after the first, and Classic's logo cell is as wide as the
logo, in pixels. It cannot be sized to its content, because frappe's print
style holds every letter head picture to its cell, and the logo came out at
nothing.

**Which way OneAI builds a page, and what it knows of the kind. Fixed.** Its
instructions said "prefer fields to html" and nothing more. They now set out
the order:
1. the builder's blocks;
2. one HTML block in place for a part blocks cannot draw;
3. one HTML block across the whole body only for a page designed end to end.

A format written by hand is not a step: `validate_format` refuses it, because
it is Jinja with all of frappe behind it. `print_layout` also read the kind
through `fields_of`, which gives a name and a label, a type only for links and
selects, and nothing about printing, cut at 150 fields and 30 a table. It now
reads it through `kind.fields`, the describer OneAI and Intake share, told it
is for a page. That gives every field with its type, each table with its rows,
and "not printed" where frappe's own formats leave a field off (97 of Sales
Invoice's 148). It is written a line a field, which puts Sales Invoice at 25KB
rather than 42KB.

**Print design on a stronger model. Fixed.** Live, on the chat's flash-lite:
- of four requests (a bill with a QR code, a PAID stamp, a receipt, a fully
  custom page), two failed;
- the other two made poor pages: six fields squeezed into one row, and a
  "custom" page that was a yellow background.

Now:
- `AI Action` has **Runs On**, a model an action names for itself ahead of the
  default for what it needs (`actions.action_default`, used wherever a
  default is worked out).
- A **Print Design** action runs on gemini-2.5-flash with 4000 output tokens.
- The two tools that lay a page out name that action, and the loop hands the
  conversation over the moment the chat's model reaches for one
  (`tools.action_of`, `handed`).
- A second fault was hiding behind "answered with nothing in it": Gemini's
  `MALFORMED_FUNCTION_CALL`, which a long multi-line stylesheet brings on. The
  gateway now recognises it (`faults.Malformed`) and asks once more for the
  arguments on one line.

The same four requests all made cards:
- a bill with its QR code;
- the invoice with a PAID stamp in an HTML block beside the builder's totals;
- a tidy receipt;
- a centred receipt with the amount large.

A design costs about 15 to 35 credits against about 4 on flash-lite. Still
wrong on the last one: it printed the naming series where the receipt's number
belongs, and the amount unformatted. Fixture action labels are not in the
translation files, for any action.

**Every property of the builder, and the house's parts for HTML. Fixed.**
OneAI set about a third of what frappe's builder offers. `print_props.py` now
holds every property the builder sets and its renderer reads (read from
frappe's inspector and macros), for:
- sections;
- columns;
- fields;
- tables and their columns;
- each palette block;
- the page.

OneAI writes them by frappe's own names and values.

- **Checking.** Styles go through `printing._style`, conditions through a
  grammar check (frappe runs them in its own `safe_eval`), and linked paths,
  repeater fields and merged column lines against the kind.
- **Round trip.** `_written` hands every property back, so a changed format
  keeps what it had.
- **Save guard.** It now checks a section's `custom_style`, `background` and
  `border_color`, which it never read before.
- **House parts for HTML.** `HOUSE_CSS` gains the house's parts for an HTML
  block (`one-card`, `one-figure`, `one-badge--*`, `one-stamp`, `one-table`,
  `one-kv` and the rest) in frappe-ui's greys and colours. The instructions
  name them and add two rules: the record's number is `doc.name`, and a figure
  or date prints through `get_formatted`.
- **Blank answers.** A blank answer is asked again past Cloudflare's cache
  (`cf-aig-skip-cache`): measured, the cache handed back the same blank, same
  response id, on every retry.
- **Sections written by hand.** They are read with raw line breaks and stray
  backslashes in their strings.

Live on Print Design:
- **New format.** A new "Summary Invoice" (an amount-due card, a status badge,
  then the items and totals) came out right on the first attempt.
- **Changed format.** A change to an existing format kept every property it
  had and added striped rows, a zero-quantity filter and the page at 13px with
  10mm margins.
- **Header colour.** It set the table header colour in CSS, which frappe's own
  `!important` overrides. The instructions now say to use the property.

**Workspace › Printing drawn as the dialog draws it. Fixed.** The page listed
letter heads and formats in two tables, where a record's Settings › Print
Formats shows each format as a card with its page on it.
- **Formats.** The page now runs frappe's own Print Formats tab, once for each
  kind of record the workspace made a format for. Its cards, preview, default
  star and New are frappe's, with One's New and default wiring.
- **Letter heads.** Each is a card in the same classes, showing the whole page
  with the top and the foot. The star makes it the default, the card opens
  it, and badges show Standard and Off.
- **Standard letter heads showed their code.** The ones that came with the
  apps are Jinja templates. The page and the letter head window now show them
  run for a record of the company, as frappe prints them.
- **Making a standard letter head the default failed.** Frappe's save exports a
  standard letter head back into its app's files in developer mode, and was
  refused. It is now made the default or turned off by frappe's own
  `set_as_default`, without the save.

**Stage 4, Mail Templates: done.** Seen as a workspace administrator:
Workspace › Mail Templates, a record's Settings › Mail Templates, the editor,
and the email window in OneMail and on a record. The user asked for OneMail
in particular.

1. Notifications: **finding.** A template is what the composer and the leave
   mails, interview reminders, salary slip and dispatch notice send. Amounts
   and dates filled in by a template read `9.0` and `2026-09-21`, since
   frappe gives raw values and a template written here may not format them.
2. OneAI: **finding.** Nothing at all: no suggestions, no read, no way to
   write one.
3. Intake: nothing here. Intake files mail on records, which is what makes a
   reply's templates the record's (point 5).
4. Permissions: held. Everybody reads a template (frappe's), the workspace
   administrator writes them, and one they write may only name fields.
   **Finding:** the check let `{{ doc.customer_name }}` through, and frappe's
   composer, the leave mails and the salary slip all render a template with
   no `doc`, so such a template failed wherever it was used.
5. Cross-module, OneMail: **findings.**
   - Frappe's composer asks its form for the kind of record, and OneMail's
     has none, so a new message or a reply offered every template, the leave
     mails in a mail to a customer among them.
   - A reply on a conversation filed on an invoice passed only its name, so a
     template came out blank, and a new message passed no record, so picking
     a template failed.
   - Four templates the apps made on setup (the interview reminders, the exit
     questionnaire, the dispatch notice) had no kind, so they were offered
     on every record.
6. Bespoke UI: the page's table and the dialog's list are One's; the email
   window is frappe's.
7. Documented: the README said nothing of OneMail, formatting or OneAI.
8. Legal: nothing new; the mail it starts is sent as any mail is.
9. Built from frappe: frappe's composer, its template field and its
   `get_email_template`, each met where it falls short.

Fixed:
- **The composer offers the record's templates.** `mail_compose.js` points
  the template field at the record the composer is about, form or not, and
  with none at the templates for any record.
- **Filled in from the record, as it shows it.** `get_email_template` is
  One's (`override_whitelisted_methods`). It reads the record when only its
  name is given, as the reader, and a template that only names fields gets
  each as the record shows it: `$ 9.00` and `21-09-2026`. A template the
  apps wrote that does more gets frappe's raw values, which it may work on.
- **Fields are named bare.** `{{ doc.x }}` is refused with the right way
  to write it.
- **The apps' templates say what they are for.** `settle` sets their kind
  from the setting that names each, or the name it was made with.
- **OneAI.** `workspace_mail_templates` reads every template, which setting
  sends it and the fields a kind may name. `write_mail_template` suggests a
  new one or new wording as a card, rewriting `{{ doc.x }}` to `{{ x }}`
  itself. The page offers three suggestions.
- **The card's title.** It said "Create a Email Template"; a new record's
  card now says "New Email Template: Invoice Due Reminder".

Live, twice, on "Write a payment reminder": a card on the second call each
time, the first being refused (`{{ doc.name }}`, then `{{ amount }}`, which
is not a field). Still wrong: the model signs off with a name ("One Team")
though the mailbox signs, which the card shows before it is approved.

**Stage 5, Approvals: done.** Seen as a workspace administrator: Workspace ›
Approvals, a record's Settings › Approvals, frappe's workflow builder, a bill
under an approval, OneIntake's Ready to Submit and the bell. Checked with a
Bill Approval on Purchase Invoice: Pending, then Approved by an accounts user
up to 5,000 or a manager above it, or Rejected by a manager.

1. Notifications: **finding.** Whoever a step waits on was told only by
   frappe's own mail (Send Email Alert), in frappe's words, and not listed on
   Workspace › Notifications.
2. OneAI: **finding.** Nothing: no suggestions, no read, no way to suggest an
   approval.
3. Intake: **findings.**
   - With an approval on bills, Ready to Submit still listed OneIntake's
     drafts as ready, and Submit All failed on each with an empty error,
     since frappe refuses a submit that skips the approval.
   - With e-invoices set to submit themselves, OneAI would have submitted a
     bill past its approval.
4. Permissions: held. An approval is on a kind the administrator can open; a
   kind they cannot open is refused (Purchase Order, without OneInventory).
   **Finding:** any condition on a step was refused, so the commonest
   approval, a bill over an amount to a manager, could not be made at all.
5. Cross-module: Approvals Waiting on Home counts the steps; OneBook's bills
   and OneIntake's drafts are where it shows (point 3).
6. Bespoke UI: **findings.**
   - The builder opened under frappe's own Workflow sidebar, out of One.
   - Its controls show every field, hidden or not, so a workspace
     administrator was offered tasks and worked-out values that saving
     refuses, and frappe's mail settings.
   - An approval made without the builder had every step drawn on one spot.
7. Documented: the README said a condition could not be set, and nothing of
   OneIntake, the bell or OneAI.
8. Legal: nothing new.
9. Built from frappe: frappe's Workflow, its builder, its Workflow Action and
   `apply_workflow`.

Fixed:
- **Conditions that compare fields.** `plain_condition` allows a
  condition made only of the record's own fields (first permission level),
  plain values, comparisons, `and`, `or` and `not`, read with Python's own
  parser. Anything else is still refused.
- **Told through the hub.** `send_email_alert` is off on every approval, and
  a new type, **Approval Waiting**, tells whoever holds a role the step is for
  and may open the record, on the bell and by mail as they chose.
- **OneIntake.** A draft under an approval says it waits for it ("It waits for
  its approval: it is Pending"). Submit All takes the approval's own step to a
  submitted state when the reader may (`apply_workflow`), and the e-invoice
  auto-submit leaves any bill under an approval alone.
- **The builder.** It opens in One's rail. Frappe's mail settings are hidden
  for everybody, and tasks and worked-out values for a workspace
  administrator. An approval saved without a layout is given one: states in
  columns by distance from the first, each state's steps stacked beside it.
- **OneAI.** `workspace_approvals` reads every approval, the roles in One's
  words and the fields a kind may use. `suggest_approval` suggests one, new
  or changed, as an Approval card, checked as the guard checks it; approving
  it makes any new state or action word first (frappe checks they exist before
  anything else), then saves the approval. The page offers two suggestions.

Still as frappe has it: records already made keep the state they are in when
a different approval is turned on for their kind, which may be a state the
new one does not have.

**Live, through the chat.** On flash-lite the chat never made a card: it
wrote `doc.amount` and a role called Manager, made the first state submitted,
and repeated the same call when told what was wrong (its tools' refusals did
not ask to be mended yet; now every one does). `suggest_approval` now hands
the conversation to **Workspace Setup**, gemini-2.5-flash, as Print Design
does. On it, "an invoice over 10,000 needs an accounts manager" read the
approvals and the kind first and made a card on the first call (about 25 to
45 credits); approving it made the approval, on and laid out. Its design left
a gap: an invoice of 10,000 or less reached Pending Approval with no way out
but Reject. The instructions now say every record must be able to finish, and
the card is what a person reads before approving. A suggestion identical to
the approval already there is refused rather than carded.

**Stage 6, Automations: done.** Seen as a workspace administrator: the
Automation Flow list and form, a record's Settings › Automations, and a flow
that tells somebody when an invoice is paid.

1. Notifications: **findings.**
   - Frappe's Send Notification mails past One's hub, so what an automation
     sends was on no list and could not be turned off.
   - It renders a mail template with only `doc`, while a template names the
     record's fields bare (the email window, the leave mails and the salary
     slip need it so). A template sent by an automation printed its tags.
2. OneAI: **finding.** Nothing.
3. Intake: nothing here; OneIntake's own work is not an automation.
4. Permissions: held. A workspace's flow runs as whoever saved it, decides by
   its field rules, runs no script, names only fields in its values, sends a
   webhook over https, and is on a kind they can open.
5. Cross-module: Mail Templates (point 1).
6. Bespoke UI: **finding.** The list and form opened under frappe's own
   Automation sidebar, though the code said they kept One's rail.
7. Documented: the README listed "notify or mail somebody", the step that
   went past the hub.
8. Legal: a webhook sends a record's data to the address the workspace
   gives, as the workspace's own choice; nothing new for One to declare.
9. Built from frappe: frappe's automation engine, its form and its steps,
   with One's step added through the engine's own `automation_actions` hook.

Fixed:
- **Tell People.** One's own step (`one/automation_steps.py`) tells
  whoever it names through the hub, as Automation Notice, and fills a mail
  template in as the email window does (`mail_templates.filled`), with
  amounts and dates as the record shows them. Send Notification is refused
  to a workspace's own flows, which are pointed at Tell People.
- **One's rail.** desk.js reads the Automation Flow list and form as
  Workspace › Automations, as it does the approval builder.
- **The step editor** (after the pass: the browser view the pass had
  skipped). Frappe's form left Action Type with no choices and a step's
  settings as a JSON box, upstream too (Automation Flow is marked beta there),
  so nobody could make a step by hand. Frappe's engine says what each step
  takes (`params_schema`, `get_automation_capabilities`), so a step's row
  now draws that as frappe's own controls in a FieldGroup and writes the JSON
  back: Action Type offers what the workspace may keep (Send Notification is
  gone from it, not just refused on save), people are picked from frappe's own
  `get_param_options` (whoever made the record, its assignees, the team),
  Mail Template offers the kind's own templates as the composer does, and a
  Wait asks how long. The engine's own labels are translated (`steps`,
  `WORDS`). `one/automations.py` `steps`, `doctype_settings.js`.
- **OneAI, live** (after the pass). Asked on the automations list to tell
  whoever made a paid invoice and assign it to them, the chat's small model
  reached for the notification rule three times, which cannot assign, and
  answered with its argument error. The rule now says that telling with
  anything else is an automation, its refusals ask to be mended, and it is
  run by Workspace Setup as approvals and automations are, whose instruction
  now tells a rule from an automation. A token in an assign step is refused
  (frappe's step assigns users only). Run again: handed over, one card, Tell
  People to whoever made it, and a plain answer that assigning to them cannot
  be done; approved, it runs as the administrator.
- **One table in the dialog** (after the pass, on the user's word that
  Approvals and Automations did not look like Numbering). Frappe draws its
  Naming tab in EmbeddedList and its Workflow, Email Templates and
  Notifications tabs in an older, flatter list panel, and ours had followed
  each. Approvals, Automations, Mail Templates and Notifications are now drawn
  as Numbering is: the panel's own heading and button over the shell's table
  (frappe's EmbeddedList), On, Off and Default as badges by the name, and one
  button on the row (turn on or off, make the default).
- **The Settings dialog** (after the pass). Automations sits under Approvals
  rather than after Print Formats, which is Printing as in Workspace ›
  Printing; its When column says "When Status changes to Paid" rather than
  frappe's trigger name. Printing drew erpnext's disabled Italian eInvoice,
  whose preview failed on a field this workspace lacks; the tab lists the
  enabled formats only, as the print view does.
- **One's rail from anywhere** (after the pass, on the user's word that the
  sidebar was still frappe's). A flow opened from a record's Settings ›
  Automations in OneCRM kept OneCRM's sidebar, since frappe keeps the one on
  screen, and `/desk/automation` was frappe's own Automation workspace with
  its sidebar and rail. desk.js now takes One's sidebar for the builder and
  every flow wherever it is opened from, gives the space it left back on the
  next record One does not list, and `frappe.re_route` sends
  `/desk/automation` to the flow list. One's Automations item carries
  frappe's `is_default_module`, so frappe itself names One as the flows'
  home.
- **OneAI.** `workspace_automations` reads every flow and what a kind has
  (fields, dates, mail templates). `suggest_automation` builds a flow from
  when, only_when and set/tell/assign steps, checks it with frappe's own
  validate and the workspace's, and suggests it as a card; it runs on
  Workspace Setup. Two suggestions on the list. Tried directly: "when an
  invoice's status changes to Paid, tell its owner" made a card, approving it
  made the flow running as the administrator, and both Tell People steps,
  one with a template, arrived on the bell filled in ($ 9.00, 21-09-2026).

**P2, Access: done.** Asked for on the user's word: "should we also introduce
new custom roles builder like currently each app is either a user or manager
but maybe for specific user we want somewhere in between". Seen as a
workspace administrator: Workspace › Access, a level's, a profile's and a
group's page, a person's page, and a record's Settings › Access.

Before it, People set None, User or Manager per app and nothing else. Frappe
has the rest underneath, each with no screen in One: Role and Custom DocPerm
(what a role may do), User Permission (which records), Role Profile (roles by
job) and User Group (a team to assign to).

1. Notifications: what changes a person's access tells them, as Access
   Changed, now including a level, a profile and what they are held to.
   Changing what a level adds tells everybody at it.
2. OneAI: `workspace_access` reads the levels, what each adds, who is at
   each, the profiles, the groups and who is held to what; the page offers
   "Who can do more than a user?" and "Who sees only part?".
3. Intake: nothing here.
4. Permissions: only workspace administrators see Access. A level adds only
   what its app's own Manager roles may do on that kind (`save_level` refuses
   the rest by name). Record access lists and changes only the eight kinds One
   offers; HR's own holds (Employee, Company) are not shown and cannot be
   taken away.
5. Cross-module: a level is offered wherever an app's roles are, People's
   app selects, the invite, and Approvals' "who approves" ("OneBook at the
   level Senior Accountant"). A profile keeps HR's Employee role.
6. Bespoke UI: Levels, Profiles and Groups as Numbering's tables; each page
   is a desk record (dirty, leave warning, save against `modified`); a level's
   rights are a frappe Table of Autocomplete and Check controls.
7. Documented: "Access, for the Workspace" in `one/README.md`.
8. Legal: nothing leaves the workspace; no clause.
9. Built from frappe: Role with One's `one_app`, Custom DocPerm written as the
   Role Permissions Manager writes it, User Permission, Role Profile and User
   Group, all frappe's own.

Fixed or built:
- **Levels.** A level is a Role marked with its app (`Role.one_app`). Its
  people hold the app's User roles and the level. `one/access.py`.
- **Profiles** are frappe's Role Profile, applied by One (`put_on`) rather
  than by frappe's own sync, which replaces every role a person has and would
  take HR's away. `User.one_profile` says which profile a person's apps came
  from; changing an app by hand takes them off it.
- **Groups** are frappe's User Group, of workspace people only.
- **What They See** on a person's page holds them to a record through User
  Permission, everywhere or on one kind.
- **Settings › Access** on any record shows its kind's users, levels and
  managers side by side.
- Tried: Senior Sales adding delete on Opportunity let Rania delete a deal
  and not a lead; a level asking for more than OneCRM's manager was refused;
  Accountant set OneBook and OneInventory and kept Employee, and changing it
  changed her; held to the territory United Arab Emirates, she saw its
  customers and not one in Rest Of The World. A customer with no territory
  still shows, as frappe does unless System Settings asks for strict user
  permissions.

**Access, every level editable** (after the pass, on the user's word: "they
can have the full control over what a user get to do or any custom roles in
between or even a manager", and "for its link fields it must have the linked
doctype at least at read"). A level could only add to the app's User, never
past its Manager, and User and Manager could not be changed at all.

- Every level opens alike: User, Manager and the workspace's own are rows in
  Levels, each with a tick per right on every kind of record the app works
  with, given or taken away. A level of the workspace's own **Starts As**
  User, Manager or another level, and can go below User.
- Every level still holds the app's User roles, because twenty-odd places in
  One and erpnext ask for "HR User" or "Sales User" by name (who hears HR's
  mails, who opens a report, who sees the workspace). So `_set` writes what
  every level of the app shares on those roles, and each level's own on its
  own roles: Manager's on the app's Manager roles, a level's on itself, and a
  plain user's on a companion role only they hold (`OneCRM User`, made the
  first time it is needed).
- Smart on save: a right brings what it needs (Delete brings Read, Cancel
  brings Submit and Edit, as frappe refuses otherwise), and a kind a level
  may create or edit gives it Pick, frappe's `select`, on every kind its form
  must name and somebody fills in, on it and on its tables, where it could
  not already pick or read them. The page says which and why. Only mandatory
  links, since each kind given a rule of the workspace's own stops following
  the app's updates to its permissions.
- Tried as wsadmin: Senior Sales reads leads and may not edit them while plain
  users still may; Customer taken away from it came back as Pick for its sales
  orders; Export of leads taken off Manager; Address edit ticked off and back
  on from the page.
- Found on the way: every record page under Settings (a person, a level, a
  profile, a group, a rule) drew its side panel a second time after a save,
  inside its own main column. A record now redraws from a fresh body, and one
  saved under a new name opens under it.

**P2, Reports and Dashboards: done.** Kept in One rather than a OneInsight,
on the user's word: saved reports and reports by mail belong to their app,
and only dashboards across apps have no app, so One holds them. Seen as a
workspace administrator and as Rania: a list's Report view saved under a
name, OneBook's and OneCRM's sidebars, One › Dashboards, a dashboard, and
Workspace › Reports by Mail.

Before it: frappe's Report view offered Save As to everybody and refused it
to everybody but a Report Manager; nobody on a workspace could make a
dashboard, a chart, a card or a report by mail; and a saved report went
nowhere but the view switcher.

1. Notifications: a report by mail is the workspace's own mail, sent by
   frappe on its schedule from the workspace's outgoing account; One sends
   nothing new.
2. OneAI: `workspace_reports` reads every saved report, dashboard and report
   by mail; the dashboards and report-mail lists offer one suggestion each.
3. Intake: nothing here.
4. Permissions: anybody may save a Report Builder report (frappe's own
   `save_report` writes nothing else), and only its owner or an administrator
   changes it. Administrators make dashboards, charts, cards and reports by
   mail. Refused to a workspace: a report of any other type (a Custom Report
   runs the report it copies with no check of who may open that one), a chart
   or card of type Custom, and a report by mail run as somebody else. A chart
   or card shows only to who may read what it counts, as frappe does.
5. Cross-module: a saved report goes in the sidebar frappe opens its kind in
   for whoever saved it (`build_entity_module_map`): invoices in OneBook,
   customers in OneCRM.
6. Bespoke UI: frappe's own Report view, dashboard view and lists, in One's
   sidebar wherever opened (desk.js `OneSidebar.KEPT`); saved reports under a
   Saved Reports section shaped like the app's own.
7. Documented: "Reports and dashboards" in `one/README.md`.
8. Legal: a report by mail sends records to addresses the workspace chooses,
   through the mail it already sends with; no new processor and no clause.
9. Built from frappe: Report, Dashboard, Dashboard Chart, Number Card, Auto
   Email Report, and the sidebar's own site and user layers (`Custom
   Sidebar`).

Fixed or built (`one/reports.py`):
- **Saved reports in the sidebar.** Saved by an administrator, into the site's
  layer of the app's sidebar for everybody; by anybody else, into their own
  layer. Deleted, out again, with the section when it was the last.
- **Two frappe gaps, worked around without touching frappe.** A report link
  a layer adds is never drawn, because frappe gives the report's type only to
  an app's own rows: boot and the refresh fill it in (`reported`). And frappe
  keeps each person's reports for an hour, so a new one stayed hidden until
  then: the cache is dropped when a sidebar changes, and the sidebar is
  fetched and redrawn over realtime, as frappe's own sidebar editor does. A
  realtime handler added before frappe's socket exists is dropped silently,
  so it waits for `app_ready`.
- **One › Dashboards** lists the workspace's own; erpnext's module dashboards,
  with a company on every chart, are left out.
- Tried: Unpaid Invoices saved by wsadmin landed in OneBook for everybody;
  Rania's My Items only in her OneInventory; Customers by Group, saved from
  the Report view's Save As, appeared in OneCRM's sidebar without a reload; a
  Custom Report and a Custom card were refused; a report by mail set to run as
  Administrator ran as wsadmin; the Money In dashboard drew its card and two
  charts.

**Show In** (after the pass, on the user's word: where a report or dashboard
shows should be chosen, not decided). **Show In…** on a saved report's menu
and a dashboard's (and on a dashboard's form) asks which app's sidebar, or
none, and, for an administrator, just me or everybody who uses the app. The
list offers One and the apps the reader works in. A report just saved says
where it went and offers the same choice. Only whoever saved a report, or
an administrator, moves it; dashboards are an administrator's. Tried: Money
In shown in OneBook for everybody from the dashboard's menu; Rania moved her
My Items to OneBook for herself and was refused everybody, Money In and
somebody else's report.

**P2, Recycle Bin: done.** One › Recycle Bin is frappe's Deleted Document.
Seen as a workspace administrator and as Rania: the list, a deleted record,
Restore from both, and the privacy notice asked again.

Before it: frappe keeps every deleted record whole, but showing them and
putting one back were its System Manager's, so nobody on a workspace could
undo a deletion.

1. Notifications: nothing new; a record put back carries a comment saying
   what it was restored from.
2. OneAI: `recycle_bin` reads what the reader may see was deleted lately;
   the list offers "What was deleted lately?".
3. Intake: nothing here.
4. Permissions: everybody sees what they deleted; an administrator also what
   any person or OneAI deleted of the kinds they may read, never the
   system's own cleanups (deleted as Administrator); only an administrator
   empties it for good. Tables, frappe's Core and Custom machinery and the
   platform's records stay out. Putting back keeps frappe's checks: whoever
   restores must be able to make and read that kind of record.
5. Cross-module: every app's deletions land here.
6. Bespoke UI: frappe's own list and form, in One's sidebar; Deleted and
   Restored as the list's indicator; Restore as the form's primary button
   and a list action.
7. Documented: "Recycle Bin" in `one/README.md`.
8. Legal: **finding.** The privacy notice said content stays until you
   delete it; a deleted record is in fact kept until the bin is emptied. A
   clause says so (`one/legal.py`, recycle-bin), and the privacy notice is
   at revision 10, so everybody agrees again.
9. Built from frappe: Deleted Document, and frappe's restore, followed line
   for line in `one/recycle.py` because frappe's own refuses anybody but a
   System Manager.

Tried: Rania deleted a to-do and found it, and only it, and put it back; the
administrator saw a task a person deleted and a supplier OneAI deleted, not
the hundreds of setup rows and test cleanups; Net 45, a payment term the
administrator deleted, put back from its page in the browser.

**OneAI sets it up: done** (after the Recycle Bin, on the user's word). The
chat drafts seven things as cards, each made only when somebody presses
**Approve**, by the page's own code and as them (`one/ai_setup.py`, on
Workspace Setup): a saved report (columns, filters, sort, and Show In), a
dashboard (charts and cards, then Show In), a report by mail, a level (made,
or rights given and taken away), a profile, a group, and what a person sees
(a hold, or letting one go). The checks are the page's: a report or chart
only of what the reader may read, everything else for administrators. A
level's card names only the rights that would change and goes Stale if the
level changes before it is approved. Tried each through approval as the
administrator, the refusals as Plain, and a level asked for in the panel in
plain words.

**P2, Audit Log: done.** One › Audit Log is three of frappe's own lists:
**Changes** (Version), **Sign-ins** (Activity Log) and **Exports and Prints**
(Access Log). Seen as the workspace administrator and as Rania.

Before it: frappe writes all three, and reading them was its System
Manager's, so nobody on a workspace could ask who changed a price.

1. Notifications: nothing new. A sudden large export could tell the
   administrators; not built, worth it once a workspace asks.
2. OneAI: `audit_log` reads changes (each field from what to what), sign-ins
   or exports, by kind, record, person and days; each list offers its
   question (What changed today?, Any odd sign-ins?, What left as a file?).
3. Intake: nothing here; what OneAI changes is written as OneAI and listed.
4. Permissions: workspace administrators only, read only, nobody writes or
   deletes a line. Changes and exports only of the kinds of record they may
   read (plus people's accounts and levels), never frappe's machinery, the
   platform's records or what the system did (Administrator, Guest, OneAI's
   own user). **Finding:** a change carries every field's value, so a change
   now shows only the fields its reader may read (`audit.seen`, on the form
   and in OneAI's answer). Rania sees no Audit Log and is refused a change.
5. Cross-module: every app's changes, exports and prints land here; one
   record's changes stay on its own timeline for its readers.
6. Bespoke UI: frappe's lists, headed as the sidebar names them, each row a
   sentence ("Wren changed One", "You printed Grant Plastics Ltd.") with an
   Open button to the record, no hash column, filters by kind, person and
   whether a sign-in failed. The Recycle Bin is headed Recycle Bin too.
7. Documented: "Audit Log" in `one/README.md`.
8. Legal: **finding.** The privacy notice did not say every change is kept
   with its values, or that exports and prints are logged, or who reads it.
   A clause says so (`one/legal.py`, audit-log); privacy revision 11.
9. Built from frappe: Version, Activity Log and Access Log as they are, with
   frappe's list settings and property setters. Audit Trail (comparing a
   submitted record's amendments) stays out: each record's timeline shows
   every version already.

**P2, Privacy Requests: done.** You › Profile › **Your Data** and Workspace ›
**Privacy Requests**, on frappe's Personal Data Download and Deletion
Requests. Seen as Rania (her profile, the delete dialog) and the workspace
administrator (the list, a waiting request); the whole flow tried on three
throwaway people, two of them erased.

Before it: both doctypes were System Manager's, the deletion's approval mail
went to System Managers no workspace has, and its mails read "Dear User".

1. Notifications: five of One's own types instead of frappe's mails. Your
   Data Is Ready (the person), Deletion Asked (every administrator, always
   mailed), Deletion On Hold with the reason (the person, always mailed),
   Account Deleted (the person, before they are signed out) and Person
   Deleted (the other administrators).
2. OneAI: `privacy_request` says what approving would do (deleted outright,
   name taken out, still assigned to them, an employee record, anything
   that blocks it); the request offers "What would deleting them remove?".
3. Intake: nothing here. A mail asking to be forgotten is for an
   administrator to answer.
4. Permissions: anybody asks for their own copy (once an hour) and their own
   deletion, with their password. Only administrators see requests and
   decide them, through Approve and Delete or Hold, never by editing. Nobody
   deletes the last administrator, the person billed, or approves their own.
   Rania is refused the list and the approval.
5. Cross-module: approving deletes OneAI conversations and memories,
   notifications, devices, calendar feeds and drive passwords, then runs
   frappe's erasure: contacts, mail, comments, the Audit Log, and (added in
   `user_data_fields`) the Recycle Bin, to-dos and notifications lose the
   name and address; every owner and modified-by becomes the anonymous
   account. **Finding:** frappe left the name in to-dos and the bin. An
   employee record is HR's and stays.
6. Bespoke UI: Your Data at the foot of the profile, three buttons, a
   password dialog with a red button. The requests list says who asked and
   "Waiting for You"; a request is headed by the person, with Approve and
   Delete in the page head and Hold beside it.
7. Documented: "Your Data" under Profile and "Privacy Requests" in
   `one/README.md`.
8. Legal: **finding.** The privacy notice said to write to us; a clause says
   what a person can do themselves in a workspace and what deletion keeps
   (`one/legal.py`, privacy-requests). Privacy revision 12.
9. Built from frappe: its two doctypes, its gathering (`get_user_data`) and
   its erasure (`_anonymize_data`) as they are. The insert-time mails are
   skipped because the password typed confirms who asks; frappe's mailed
   link is for somebody not signed in.

**Privacy Requests, second round** (on the user's questions: why a password
and not our own mail, and what a copy gives away).

- Deleting is confirmed with the password, or, for somebody who signs in by
  mailed link or passkey and has none, by a signed link in One's own mail
  that works for a day (Confirm Deletion). Tried: the link confirmed once,
  was refused the second time, and refused when altered.
- **Finding:** frappe's copy (`get_user_data`) gave every row the person's
  address appears in, whole: deleted records, printed pages, other people's
  values in their changes, a reset key. The copy is now One's own
  (`one/privacy_copy.py`), kind by kind, and an administrator reviews it
  first under Workspace › Data Copies. What is about the person always goes
  (account and profile, sign-ins, contacts, OneAI's memories, agreements);
  mail, comments, to-dos, OneAI conversations, changes (field names only),
  exports (no pages) and notifications go unless withheld, with a reason
  the person is told (GDPR article 15(4)); deleted records, printed pages,
  values and secrets never go. Tried: Rania's copy with her mail and chats
  withheld; withholding her account, or without a reason, refused.
- Administrators are reminded each day a request has waited a week.
- Legal: the clause says a copy is reviewed and what may be left out;
  privacy revision 13.

**Privacy Requests, third round: people who are not users.** A customer's
contact, a supplier, a lead or an applicant has the same rights and no
account, so each workspace now has a public page, **/your-data**
(`www/your_data.py`, `one/privacy_public.py`).

- They give their address and choose a copy or a deletion. One mails a
  signed link that works for a day (Confirm Your Request), and nothing is
  filed until it is opened. The page answers the same whatever the address,
  and one network address may ask five times an hour.
- Opened, the request lands in Data Copies or Account Deletions under their
  address (a new Address column), for an administrator to decide as for a
  user. Their copy holds contacts and the records with their address
  (leads, deals, customers, suppliers, applications), which always go, and
  mail, which may be withheld for a reason. It is mailed as a signed
  download link good for a week (Your Data Is Ready to Download).
- Deleting runs frappe's own redaction without the step that renames an
  account they do not have; Job Applicant joins `user_data_fields`. They are
  told when it is approved, or held and why.
- **Findings, fixed:** `/your-data` 404'd (www routes are filenames; a route
  rule now maps it); the copy said "Withheld: Mail…: why" twice over, now
  only the reason; the "Never included" list spoke of printed pages and
  reset keys to people who have neither, now one line for outsiders.
- Tried: Maya, a lead and contact with mail, asked as a guest; the link
  confirmed (opening it twice files one request), a tampered link refused;
  her copy reviewed with mail withheld and downloaded as a guest; then
  deleted: the lead reads [REDACTED], her mail and copies gone, the request
  under an anonymous address.
- Legal: the rights clause says how a non-user asks; privacy revision 14.

**Close Workspace, with a full download** (on the user's question: can a
customer leave and take everything). Workspace › Plan and Credits, section
Closing the Workspace; `one/closing.py` and `one_admin/closing.py`.

- Only the person the workspace is billed to sees the buttons; other
  administrators see who that is. Everybody else cannot open the page.
- **Full Download** builds one zip in the background: frappe's own
  database backup (restores on any Frappe site), every kind of record as a
  CSV, every file from OneCloud's store under its folder, and a README that
  lists any file that could not be read. Written under a temporary name
  and renamed, so a download never meets half a zip. Tried: 438 entries,
  19 MB, every entry reads; the payer was told on the bell and by mail.
- **Close Workspace** asks for the password and a tick. The account sets
  Closing On 14 days out (`ladder.NOTICE_DAYS`), ends the subscription with
  its period, logs it and tells the operators; everybody in the workspace
  is told the day by bell and mail, which cannot be turned off. The page
  head says Closing and a red line says both days. **Keep It Open** undoes
  it before the day, and everybody is told. On the day the nightly run
  starts the ladder's own Archive job; the owner is mailed Workspace Closed,
  and it falls to deleted on the Archived clock. /account shows Closing,
  then Closed, and never asks a closed workspace to pay.
- **Finding, fixed before it shipped:** the nightly pass first read
  `closing_on <= today`, and frappe reads a missing date as 0001-01-01, so
  it picked six other workspaces that never asked. It now requires the
  date to be set; the test says why.
- **Finding, fixed:** two builds at once (a queued one and a direct one)
  wrote the same zip and corrupted it; hence the temporary name.
- OneAI's plan answer carries who may close, whether it is closing, and
  the download. Legal: Terms 9 (closing yourself, the notice, no refund for
  the period, deleted 30 days later, the full download) and DPA 2.

**P2, Integrations: webhooks only** (the user's call: sign-in with Google
or Microsoft, OAuth clients and connected apps are later, marked so in
docs/DESK-COVERAGE.md). Workspace › **Webhooks** and **Webhook Calls**,
frappe's own Webhook and Webhook Request Log, given to the administrator
(`one/webhooks.py`).

1. Notifications: **Webhooks Failing**, each morning, the webhooks whose
   calls gave up the day before, to the administrators; none when none did.
2. OneAI: `webhooks` answers how each one's calls went and what the other
   system said when they gave up; offered on both lists.
3. Intake: nothing reaches here.
4. Permissions: administrators only, on the kinds of record they may read;
   the calls are read only. **Finding, fixed:** frappe's plain sender
   follows redirects and resolves the name only when it calls, so a public
   address could hand a call to an internal one. Every request and job now
   sends through frappe's own guarded sender from its automation engine,
   which checks each hop. At save: https only, a public address, no
   template address, no code condition, `{{ doc.field }}` only, and no
   field above the writer's level. Tried as wsadmin: loopback, localhost
   and the metadata address refused, http refused, a code tag refused, a
   kind they cannot read refused; Rania refused outright.
5. Cross-module: any kind of record; an automation's Call Webhook step is
   the way to send only some.
6. UI: frappe's list and form on One's rail; the form hides what would be
   refused. **Finding, fixed:** the calls list opened in frappe's own
   Integrations sidebar (Connected App, Google); it is in One's now.
7. Documented: "Webhooks, for the Workspace" in one/README.md.
8. Legal: privacy (sharing) 15 and DPA (instructions) 3: a webhook is the
   organisation's instruction, and its recipient is theirs, not ours.
9. Built from frappe: its Webhook, its log, its retries, its guarded
   sender; ours is the guard and the morning note.

Tried end to end: a webhook on new customers to a Zapier address; a
customer made; the call went out through the guarded sender, Zapier
answered 404 for the made-up hook, and the call reads Exhausted with what
was sent; the morning note reached both administrators.

**P3, Announcements.** frappe's Note, under Dashboards in the sidebar
(`one/announcements.py`).

1. Notifications: **Announcement**, to everybody but its writer, on the bell
   and by mail, once, when it becomes public.
2. OneAI: `announcements` answers what is up and who has not read it.
3. Intake: nothing.
4. Permissions: frappe holds public and shown-on-sign-in at a level only its
   System Manager writes, so Rania's attempts to broadcast were quietly
   made private; the administrator is given that level and the one that
   shows who has seen it.
5. Cross-module: none.
6. UI: frappe's form; the administrator's starts public and shown on
   sign-in, with plain labels; anybody else sees only a private note.
7. Documented: "Announcements" in one/README.md.
8. Legal: privacy 16, who has read an announcement is kept and shown to the
   administrators.
9. Built from frappe: its Note, its pop-up and its Seen By; ours is who may
   post, the bell, and the fix below.

**Finding, fixed:** frappe never showed anybody a note. It works out the
unseen ones in `on_login`, which runs before the session exists, so it
works them out for Guest. `extend_bootinfo` now works them out again for
the person whenever frappe has cleared the list. Tried: Rania signed in and
met it; closed, it stayed closed, and Seen By names her.

**The second audit: is frappe now wired to One?** Every one of frappe's 194
non-child doctypes has its row in docs/DESK-COVERAGE.md; none was missing
and none is gone. The table had gone stale, so its answers were read again:
P1 and P2 are all In One now, bar Import and Export (Later), and a few that
were down as Add are underneath or a developer's (Document Naming Settings,
Module Profile, Print Style, Workflow Transition Tasks). What is left went
into **docs/BACKLOG.md**, with the deferred P2, the stages not finished and
what was noticed along the way.

**Finding, fixed: thirty rail links opened for nobody they were for.** A
space's rail links to erpnext's and hrms's kinds, and each kind decides who
may open it. Read against the roles People hands out (settings.APPS), 30
refused every one of them:

- OneBook: Bank, Bank Statement Import, Opening Invoices and Purchase Tax
  Templates. The workspace administrator, an Accounts Manager, met "not
  permitted" on Bank.
- OneInventory: the whole equipment register (assets, categories,
  maintenance and its log and teams, repairs, value adjustments,
  capitalization), item prices and quality inspections.
- OneHR: Travel Request, Purpose of Travel, Employee Advance, Vehicle Log.
- OneProject: Projects Settings.
- OneCRM: Email Campaign, Email Group, Lead Source, Lead Assignment and
  Inboxes, and a link to Newsletter, which frappe no longer ships.

Each space's `access.py` now gives them to its own roles through
`roles.give`, once, leaving a role that reads already alone. The Newsletter
link is gone, and so is Inboxes: a workspace's mailboxes are Settings ›
Mail, and an enquiry by mail becomes a lead through OneIntake. A Sales
Manager's Assignment Rule is held to leads and deals, and to a condition
that compares the record's fields with plain values; frappe evaluates it
with its globals, which read any record. Tried: Bank opens for the
administrator; Lead Assignment opens for a Sales Manager, a rule on tasks
and one with a call in it are refused, `utm_source in ("Website", "Email")`
saves. `one/reach.py` is the check, run with `bench execute`, and finds
none now.

### OneStudio

Built during the pass, on the user's call: Client and Server Scripts, which
the frappe audit had marked "not a customer's", are offered after all, but
strictly: OneAI writes them, nobody on the workspace reads or writes the
code, and an administrator turns each on. Beside them, the Customize page
moved in as Forms, and a workspace can keep kinds of record of its own,
Record Types. One module, One Studio, for workspace administrators only;
its own mark, a row in the dock before OneAdmin.

1. Notifications: **Extensions Failing**, each morning, the extensions that
   ran into a mistake the day before, to the administrators. Nothing else is
   sent; an extension's own messages are shown where it runs.
2. OneAI: `write_extension` and `design_record_type` make cards, on their
   own action (OneStudio), a stronger model told what each may be;
   `extensions_here` and `record_types_here` read what there is. A second
   action, Review an Extension, reads the code against its explanation with
   none of the conversation, and an extension it does not pass cannot be
   turned on. Suggestions on both lists and forms. Tried live: an extension
   stopping a customer saved without a mobile number, and a Company Van
   record type, each from one sentence, each made by approving its card.
3. Intake: nothing reaches here, and nothing here is ever written from what
   OneAI read in a mail or a file: only on an administrator's own ask.
4. Permissions: workspace administrators only. The code is at permission
   level 1, which only frappe's System Manager reaches, so it is in no form,
   list or API answer; `write_extension.unshown` keeps it out of the chat as
   it is streamed and kept. The guard refuses what reaches past the
   administrator (SQL, get_all, db_set, ignore_permissions, flags, mail,
   requests, jobs, unseen kinds and fields; on the screen the server, the
   network, markup and storage). frappe's scripts and DocTypes are made as
   Administrator, since frappe keeps both to its managers. A record type's
   fields run nothing, and its users may not delete.
5. Cross-module: an extension runs on any app's records the administrator
   may open; a record type belongs to one app, whose roles use it, and is in
   that app's rail under Your Records; Forms lists every app's forms.
6. UI: frappe's own list and form for Extensions and Record Types, with
   heads (On, Off, Refused by Review, Cannot Run Here; what it does;
   mistakes this week; Turn On and Turn Off; records with a link to them).
   Forms is the Customize page with no form named: a search, the changed
   ones first, then by app.
7. Documented: one_studio/README.md, Extensions, Forms, Record Types and
   Asking OneAI above Under the hood.
8. Legal: Terms 10 (OneAI writes extensions, an administrator turns them
   on, they are the customer's responsibility; record types are customer
   content) and AI Addendum 8 (the writer, the second reading, nothing runs
   unapproved).
9. Built from frappe: its Client Script and Server Script, its custom
   DocType, its list, form, Link and Data controls, its sidebar layers; ours
   is the guard, the review, the record of what was asked, and the rules.

**Found on the way:** a server script that trips on a mistake stops the
save of whoever triggered it. Every extension's code runs wrapped: a
`frappe.throw` still stops the save as meant, anything else is logged
under the extension's name and the record saves. Tried: a deliberately
broken extension, the customer saved and the mistake logged.

**For the operator:** server extensions run only where the bench has
`server_script_enabled` in `common_site_config.json`; it is on the dev bench,
and it is a step when a bench is made. Without it an extension on the server
says Cannot Run Here.

### OneStudio › Extensions

The first screen of the pass over OneStudio. Extensions is frappe's list of
the Extension doctype, and an extension opens on frappe's form with a head:
its state (On, Off, Refused by Review, Cannot Run Here), what it does,
Mistakes This Week, and Turn On or Turn Off. On the dev site there is one,
Customer Mobile Number Required, on the server, on. Looked at as wsadmin
(Workspace Administrator) and as rania (not one: refused).

1. **Notifications**: only **Extensions Failing**, each morning. Turning an
   extension on or off, or deleting one, tells nobody, though a server one
   runs on everybody's saves from that moment. Recommended: **Extension
   Turned On** to the other administrators, naming who turned on what, where
   it runs and what it does; the same when one is turned off or deleted.
2. **OneAI**:
   - The panel has no sentence for OneStudio: `one_ai_page` has no
     `one_studio.ai.page`, so OneAI does not know it is on the Extensions
     list or on one extension.
   - There is no **Change this one…** on an extension, though changing one is
     asking OneAI. Recommended: on the form, filled in, expecting
     `write_extension`, which writes this one again, has it reviewed again
     and leaves it off until it is approved.
   - Nothing answers "what went wrong" when Mistakes This Week is not 0.
     Recommended: **What went wrong?** on an extension with mistakes, reading
     the last few mistakes' messages for it (never a line of its code).
3. **Intake**: nothing OneIntake reads lands here, and nothing should: an
   extension is only ever an administrator's own ask. Holds.
4. **Permissions**:
   - **A reviewed extension can be pointed somewhere else.** Where it runs,
     on which record, in which view and on which event are `read_only`, and
     frappe keeps `read_only` only in the form. Tried as wsadmin through
     `frappe.client.set_value` (rolled back): the Customer extension moved
     to Supplier, Before Delete, and frappe's Server Script moved with it,
     still on. The guard and the review were of Customer, Before Save.
     Recommended: the review's fingerprint covers the code *and* where and
     when it runs, so any change to those turns it off until it is written
     and reviewed again; and the Extension refuses a change to them that
     does not come from `write_extension`.
   - **Share** is on: sharing an extension lets somebody who is not an
     administrator read what it does and what was asked. Recommended: off,
     with Assign.
   - Who sees it holds: Workspace Administrator only, the code at level 1;
     rania gets frappe's refusal.
5. **Cross-module**: an extension runs on another app's record, and Forms
   counts the extensions on each form. A message an extension stops a save
   with shows on that record. Holds.
6. **UI and UX**:
   - a. **One state, three words**: the list's Status says Enabled and its
     filter is an Enabled tick, the head says On, the button Turn Off.
     Recommended: On and Off everywhere; the list's indicator is the head's
     state (On, Off, Refused by Review, Cannot Run Here).
   - b. **The list** shows the ID, a random name, as a column and a filter,
     and cuts the title off. Recommended: no ID; Title, state, Runs, Record
     and When.
   - c. **The form says the explanation twice**, in the head and as a field,
     and shows the Enabled tick under the head that already says On.
     Recommended: both off the form.
   - d. **Save sits in the head with nothing to type**: every field is
     OneAI's or the review's. Recommended: no Save.
   - e. **Files** (a tab and in the sidebar), **Assign** and **Tags** on a
     record that has nothing to attach or hand to anybody. Recommended: off.
   - f. **Asked By** shows the email, not the person.
   - g. **Mistakes This Week** is shown only for a server extension, because
     a screen extension's mistakes are never written down (9).
7. **Documented**: `one_studio/README.md` has Extensions and Asking OneAI
   above Under the hood. The panel does not know the screen (2).
8. **Legal**: nothing new goes anywhere. If 9 is built, a screen extension's
   mistake is written to the workspace's own error log, as a server one's
   is. Holds.
9. **Built from frappe**: the list, the form and the head are frappe's, the
   scripts are frappe's Client and Server Script. One part is not yet the
   same as its server half: **a screen extension runs unwrapped**. A mistake
   in it breaks that form's other scripts for whoever opens it, and is
   recorded nowhere, so neither Mistakes This Week nor Extensions Failing
   ever counts one. Recommended: each handler it gives `frappe.ui.form.on`
   runs inside a `try`, as the server's code does; a mistake is logged under
   `OneStudio: <name>` through one rate-limited method, and the form goes on.

Your word: all of them.

Done:

- **The review is of where and when, not only the code.** `review.fingerprint`
  takes the code, where it runs, the record and the event or view; an
  extension turns on only if all four are what passed
  (`extensions.reviewed_as`). `extensions.validate` refuses any change to what
  OneAI wrote (`WRITTEN`) that does not come through `write`, so through the
  API an administrator turns one on and off and nothing more. Tried as wsadmin
  again: moving it to Supplier, Before Delete, and setting its review by hand
  are both refused; Turn Off still works. A patch re-fingerprints the
  extensions that passed.
- **Screen extensions run wrapped** (`guard.WRAPPED_ON_SCREEN`): each handler
  inside a `try`, a `frappe.throw` it means still stops the save, anything
  else goes to `extensions.tripped` (rate-limited, only for an extension that
  is on and on the screen) and is logged under its name. Tried on a customer
  with a deliberately broken one: its line showed, the mistake was logged
  ("frm.boom is not a function"), the form worked, and Mistakes This Week
  read 1. Mistakes This Week and Extensions Failing now count both kinds.
- **Notifications**: Extension Turned On (by mail), Extension Turned Off and
  Extension Deleted (on the bell), to the other administrators, naming who,
  where and when it runs, and what it does. Tried: admin@example.com heard
  "Wren turned on Customer Mobile Number Required"; Wren did not.
- **OneAI**: **Change this one…** on an extension, and **Has this one run
  into mistakes?** on one that is on, reading `extension_mistakes` (when, on
  which record, the last line of what went wrong; never the code). The panel
  already names the Extensions list and the record by their doctype;
  `one_ai_page` is for desk pages, which is Forms, next.
- **Share off** (and Assign, Files, Tags gone from the sidebar); no Files tab.
- **One word**: On, Off, Refused by Review, Cannot Run Here, in the list as in
  the head (the bench's server-script switch is in the boot for it).
- **The list**: no ID column or filter; Title, state, Record and When (the
  event, or Form or List on the screen).
- **The form**: no Save; the explanation and the Enabled tick off the form
  (the head says both; the explanation shows when the review refused it);
  Asked By is the person's name.
- README: what you see, changing one, Being told, what goes wrong, Asking
  OneAI, and Under the hood on the fingerprint, `WRITTEN` and the screen
  wrapper.

**Then, on your questions:** "Mistakes This Week" is now **Errors in the Last
7 Days**: the times this version of the extension crashed (a message it means
to show is not one), counted from when OneAI last wrote it (`written_on`), so
errors about older code drop out.

- **An Errors tab** on the extension (frappe's EmbeddedList through
  `onedesk.shell.table`, a record tab declared in `mend.TABS`): when, which
  record (a link), and the one line of what went wrong, never the code. A
  screen error now carries the record it was open on.
- **Fix With OneAI** at the top of an extension with errors, and
  `mend_extension` in the chat: a separate call (`studio_mend`, the AI
  Addendum's revision 9) shown the code and its last five errors on the
  server, which says what went wrong in plain words and writes it again
  through `extensions.write`, so the guard and the review read it and it is
  kept off. The button runs it as a job and tells whoever pressed it.
- Tried live, twice. The first mended version made an empty mobile number
  stop the save and did not say so; the review refused it, rightly. The
  mender is now told to keep behaviour, to choose what stops nobody's work
  for a case the explanation does not cover, and to say it in the
  explanation. The second: answered in 3 seconds, told in 11 — "The script
  stopped saving a customer when their mobile number was left blank because
  it tried to check the first digit of an empty number. The mended version
  checks if a mobile number is entered before looking at its first digit" —
  review passed, explanation updated, off until turned on. The first run
  took 185 seconds inside a request, which is why it is a job now.

**Asking back.** Asked for "a warning on a customer's form when it has no
email address", OneAI rightly asked which field (a customer's email is on its
Contact), and the panel pressed it at once to "call write_extension with what
you just wrote", which it refused. `run._asks`: a reply that ends by asking the
person something is not pressed for the card; they answer, and the card comes
after. Not yet tried live: to test with that same request.

**Server extensions taught frappe's sandbox.** Read against frappe's own
`safe_exec` and probed on the site: no import, no underscore names but `_()`,
and `str.format` refused (`UNSAFE_ATTRIBUTES`), so `_("…{0}").format(x)` would
have run into an error on every save; f-strings, `+`, `%`, `try`, `def`,
`doc.is_new()`, `doc.has_value_changed()`, child tables and `frappe.utils` all
work. The writer is now told which event does what (a Before event's changes
are saved, an After event's are not, and a throw there undoes the save), what
there is and what fails; the guard refuses `.format` with what to do instead;
the mender and the reviewer know it too. Three more events: Before and After
Save (Submitted Document), and After Delete.

**Gemma 4 for testing.** `patches/gemma_default.py`: text runs on Gemma 4
(`gemma-4-26b-a4b-it`, Workers AI, 200/600 credits a million against Gemini
2.5 Flash's 600/5000), and OneStudio's writer and mender with it. Gemini 2.5
Flash stays where it was measured to be needed (Print Design, Workspace Setup)
and on the second reading of extension code. Tried: "What do our extensions
do?" on Gemma first answered "none", having narrowed to the kind "Extension";
`extensions_here` now ignores that, and it answers all three, in 11 seconds.

**Tried on six hooks** (Before Validate, Before Insert, Before Save, After
Insert, Before Delete, Before Submit), each asked for in the panel and then
run against real records:

- **Code quality.** Five of six were right first time and short:
  `has_value_changed("customer_name")` for a name that may not change,
  `frappe.db.count` for "how many invoices", a Before Submit check on
  `grand_total` and `remarks`. Messages go through `_()`. Where a value goes
  into a message it uses `.replace("{0}", …)`, clumsy but what the sandbox
  allows.
- **The sixth, After Insert, made no task and logged nothing.** It wrapped
  the work in `if doc.is_new():`, which frappe has already made false by
  After Insert, and used bare `add_days(today(), 3)`. The guard now refuses
  `is_new()` in any After event (as it does bare `frappe.utils` names), and
  the writer and the mender are told why. It was fixed through OneAI with
  the person's words ("it never makes the task"): the mender now takes what
  the person says goes wrong when there is no error to read. Asked in the
  chat, the fix runs as a job, like **Fix With OneAI**, because it takes
  about a minute. The tools take an extension's title as well as its name,
  since that is what a model passes. Measured afterwards: the task is made,
  due three days on.
- **Two requests answered nothing.** Gemma spent all 800 of the chat's
  tokens thinking (`finish_reason: length`, empty `content`). The gateway
  now tells a Workers AI model not to think below 2000 tokens (`THINKS`);
  the writer, at 8000, still thinks. The other failure: Gemma asking for
  two tools at once comes back as one call with
  `{"doctype": "Customer"}{"doctype": "Sales Invoice"}` as its arguments.
  We read that as no arguments, the tool failed, and the model wandered until
  the round limit. `gateway._arguments` splits it into two calls. Both
  requests now give a card first time.
- **The request lost words.** "make a task called 'Call <customer name>'" was
  stored as "'Call '": frappe's sanitiser took `<customer name>` for a tag.
  The Request field now skips that filter (`ignore_xss_filter`). The form
  escapes it when it shows it, so it is still never read as HTML.

**The form reads as a page.** Every field on an extension is OneAI's or the
review's, so the column of greyed-out inputs became one Summary field
(`extension.js`, drawn with `onedesk.shell` sections and rows and frappe's
badge): where it runs, as a sentence ("After a new Customer is saved for the
first time"); what was asked, by whom and when, with each fix OneAI made
under it marked **Fixed**; and the review, with its badge. The fields stay
on the doctype for the list, the filters and OneAI, and are only hidden on
the form.

**Changing one edits it.** OneAI used to change an extension by writing it
again from its explanation, since nothing gave it the code. `extension_code`
now hands the code to the run, and its answer's code is `unshown` like
`write_extension`'s argument: `chat._keep` keeps "…" in its place, so the
code is still in the extension alone. Tried: "make the limit 75,000 instead
of 50,000" changed the number and nothing else, passed the review, and made a
card. On the way, Gemma sent the new code with no event; a change that
leaves out where or when now keeps what the extension has.

**Sorting mail, asked from any screen.** Two requests from the Customer
list: a CocaCola folder for mail with the word cola, then a Beverages folder
for anything about soft drinks. At first OneAI said it could not, calling no
tool and giving a made-up reason; there was nothing it could call. Now:

- Mail Rule has **Subject or Text Contains** and **About** (plain words).
  An About rule waits for OneAI: Intake's first look, already made for each
  new message where OneAI reads the mailbox, is also asked which of the
  mailbox's topics it is about, so it costs no extra call.
- `one_mail.ai.suggest_mail_rule` is a card. Approving it makes the folder,
  switches OneAI reading on for an About rule, makes the rule, and can sort
  what is in the Inbox now.
- The chat is told to look for a tool and read `how_to` before saying
  something cannot be done, and an empty answer is asked for once more
  even when no tool was called (Gemma once answered nothing at all).

Tried end to end: both cards made and approved; the two cola mails already in
the Inbox moved; a new "Coca-Cola Zero" reply went to CocaCola as it
arrived; a Sprite and Fanta price list, which never says cola, went to
Beverages once OneAI read it; the rent reminder stayed in the Inbox. On the
way, the dev site's workspace mailbox was missing and every mailbox read
tried to make it and failed on the old `probe9x` addresses; it was made once
by hand.

**Found on the way:** the panel's brief of the record being looked at was
drawn from the whole record, levels the reader cannot read included.
`chat._brief` now applies frappe's `apply_fieldlevel_read_permissions` first.
Nothing of an extension's code reached it (a Code field is never on a card),
but a level-1 field on another record could have.

**On One's own pages.** A Client Script reaches a kind of record's form and
its list and nothing else, so OneMail, OneCalendar and a record's head, all
drawn by One's own code, could not be changed by any extension. Now they can,
within a contract:

- `one_studio/places.py` is the one list of pages, what happens on each that
  an extension may hear, what it is told (a copy), and the few things it may
  do there: OneMail when a conversation is opened (a note, a button beside
  Reply) and when a message is being written anywhere (a note, fill subject,
  cc or bcc); the head of a record each time it is drawn (a verb, a figure in
  the band, a note); OneCalendar when an event's card is opened (a note, a
  button).
- An extension says `one.on("conversation", (mail, page) => …)`. It comes
  with the boot only once it has passed the review, runs once
  (`public/js/places.js`), and each handler is guarded: what it trips on is
  logged under its name as a form's are, and the page goes on. The guard
  refuses an event the page does not have; the review reads the place.
- Screen code may now look records up as the person (`frappe.db.get_value`,
  `get_list`, `count`, `exists`; frappe answers with their permissions);
  every other `frappe.db` call is still refused. A label passed to `__()` is
  words on the screen, not the kind of that name (`__("Domain")` was refused
  as the Domain doctype).
- OneAI reads the list through `extension_places`, and the studio
  instruction now teaches the form's events, child tables, frm's methods, the
  list's settings and the pages. Four new cases in the eval suite (form,
  list, OneMail, head): 4 of 4 pass on Gemma.
- The reviewer (Gemini 2.5 Flash) answered with cut-off JSON, read as a
  refusal: its thinking shared an 800-token budget. Now 4000, as the other
  two Gemini actions have.
- Tried on dev with three extensions, each turned on: a OneMail note
  counting the messages, a Customer head figure (the email's domain) and
  note, and a OneCalendar note on an event with no place. All three drawn;
  Reply still opens. The notes use the desk's own tone pairs, the same as
  frappe's form dashboard draws its note in.

**Closing the gaps, and OneAI checking its own work.** Asked to make
everything customizable and to keep OneAI from writing bloated or failing
code:

- **Checked before it is kept** (`checks.py`, pure; `trial.py`). Every field
  the code names, on `doc`, `frm.doc`, `frm.set_value`, `toggle_*`,
  `set_df_property` or in a lookup's fields and filters, must be one the
  kind has; the refusal gives the nearest ("Did you mean mobile_no?"). A form
  handler must be a field or an event frappe calls (`refesh` is refused).
  More than 120 lines is refused as more than one change. Node parses screen
  code (a missing bracket comes back with its line). Server code is run once
  on the newest record the person may read, in a savepoint rolled back: an
  error refuses it, and what it did comes back to OneAI as `tried` ("it
  stopped the save, saying…", "it changed customer_name"). All before the
  review, so a refusal costs no second reading. Tried on dev: each refusal as
  above, and the customer it ran on was untouched after.
- **Scheduled extensions**: Every Hour, Day, Week, Month, or On a Schedule
  with a cron line, at most hourly (`*/5` is refused). A Server Script of
  type Scheduler Event; frappe makes the job and stops it when the script
  goes. No `doc` (the guard refuses one that reads it); its kinds are still
  held to the administrator's. Tried: written, reviewed, turned on, frappe's
  Scheduled Job Type made at `0 8 * * 1-5`; deleted, the job stopped.
- **Five more pages** for page extensions: OneTask (the view listed),
  OneCloud (a file chosen), OneIntake (a document opened), the pipeline
  board (what each stage is worth), and every space's home (frappe's
  Workspace page, wrapped from places.js, not edited). Tried on dev: OneTask
  showed "1 of your tasks are overdue", OneCloud a file's owner, a space home
  a note and a My Tasks button, OneIntake fired its event.
- **The guard** no longer reads `add_comment("Comment", …)` as touching the
  Comment kind.
- **OneAI**: the studio instruction teaches schedules, the pages, the checks
  and "the shortest code that does it"; the mender no longer says screen code
  may not look things up. Three new eval cases (schedule, OneTask, a field
  name). Two habits caught in the run (`run.py`): saying "I cannot" before
  looking at every tool is answered with `more_tools` (`SEEK`), and offering
  ("I can write an extension that…") is answered "you were asked, make it"
  (`OFFERED`). A refused extension mended "with extension=" its own title is
  written as new. Measured: the schedule case wrote code that read `doc`, was
  refused, mended it, and made the card. Last full run 5 of 7, then the two
  failing alone both passed; Gemma varies run to run.
- **Timeouts**: a call allowed to think waits 110 seconds, not 60
  (`gateway.THOUGHT`); the schedule case timed out three times out of three,
  each billed. The tenant waits 120.
- **The reviewer's budget** (studio_review) stays at 4000 tokens.
- **Legal**: Terms 11 and the AI Addendum 10 say extensions also run on One's
  pages and on a schedule, and are tried once on a record first, what
  happened being told to OneAI.
- **The mender kept no place**: `mend.py` dropped a page extension's place
  when writing it again, so Fix With OneAI could not mend one. It keeps the
  place and the schedule now.

**Left for you to decide**:

- **Server scripts on every workspace.** frappe runs a server extension only
  where the bench's config allows it. Setting that key on Frappe Cloud bench
  groups from `steps.place_it` was refused by the session's safety check as
  opening a code-execution surface, so it is not done. It is one key per
  bench group (Frappe Cloud, Bench Group, Config: `server_script_enabled`).
- **API-endpoint and record-visibility (permission query) extensions** were
  not built: an AI-written HTTP endpoint, and AI-written SQL deciding who
  sees which records, are the same kind of surface. Who sees what is already
  covered by levels, record access and groups (ACCESS 1 to 6), which OneAI
  drafts.

**Found on the way, then fixed**: OneCRM's sidebar showed **Pipeline** to a
workspace administrator without a sales role, and opening it ended in "No
permission for Page" (frappe's router, not finding Opportunity in what they
may read, asks for a page of that name). frappe leaves out a DocType link a
person cannot read but takes an address link as it is; `reach.unopened`, at
boot, now leaves out an address into a kind's views (`/desk/<kind>/…`) for
somebody who may not read that kind. Tried: wsadmin's OneCRM rail has no
Pipeline; a user with a sales role keeps it.

**Headings over nothing**: frappe leaves a space home's block empty for
somebody who may not see what it holds, and keeps its headings. `desk.js`
`tidy_home`, run after frappe's `Workspace.show_page` and as its blocks draw,
marks an empty block, and a heading with nothing shown before the next with
the spacers between; desk.css hides them except in Edit. A custom block that
hides itself (One Needs You, when nothing needs you) counts as nothing.
Tried: wsadmin's OneCRM ("My Day", "The Pipeline"), OneHR and One ("Today")
are gone; Rania's OneHR keeps "Today" and all its blocks; OneBook's cards stay.
A home with nothing shown at all says so, in frappe's empty state ("Nothing
here for you yet", that the links beside it are theirs and an administrator
can give more), and the empty state goes as soon as a block draws; not in
Edit. Tried: on wsadmin's OneCRM and One; not on OneBook, nor Rania's OneHR.

### OneStudio › Forms

The list of every form a workspace administrator may change, and each form's
Customize page (frappe's controls and grids on the shell's Editor: dirty
against what loaded, Save in the head, a save refused against a newer one,
`one_customized` realtime).

1. Notifications: nothing was sent when a form changed for everybody. Now
   **Form Customized** (OneStudio), on the bell, to the other
   administrators: "Wren changed Supplier", and that its Customize page shows
   how it is now. Sent on Save, on Reset and on an approved OneAI card, since
   all three go through `customize.save` or `reset`. Tried: wsadmin saved
   Supplier; admin@example.com and Administrator were told, wsadmin was not.
2. OneAI: the page's suggestions were all about one form, so on the list
   (no form open) it offered "Suggest changes to this form" with no form. A
   suggestion may now say `record: True` or `False` (`suggest.for_page`),
   and the list offers **Which forms have we changed?** and **Change a
   form…**; a form adds **What have we changed here?**. A new read,
   `forms_here`, answers both: the changed forms with their counts, or on
   one form each field added and each property changed, and its extensions.
   The page's sentence for the list says what it is, not "no form is open".
3. Intake: nothing reaches here. A field added here is a field of the
   record, so Intake's describe and ready read it as any other.
4. Permissions: workspace administrators only (`roles.require`,
   `customize.may`). The list holds only forms they may read (119 for
   wsadmin, of 382); Lead, which wsadmin may not read, is refused when
   opened by its address. The extensions on a form are read through `may`
   too.
5. Cross-module: 256 of 382 forms were under **Other Forms**, because only a
   form some rail links to had an app. The app now falls back on the
   form's module (Accounts to OneBook, Stock and Buying to OneInventory, HR
   and Payroll to OneHR, Selling and Support to OneCRM, Projects to
   OneProject) and on One's own modules (Reading under OneIntake); 29 shared
   forms (Address, Department, Country) stay under Other Forms. "Changed
   Here" counted only fields and their changes; it now counts the head's,
   the connections' and the buttons' rows the workspace added too. A form's
   Customize page ends with **Extensions**: what runs on it, on or off, each
   leading to its own page.
6. UI: Save in the head. The list and a form's Extensions keep up as forms
   are saved and extensions change (`one_customized`, `list_update`),
   keeping what was searched.

   **Your word, after: why is Forms not a table?** It was rows under a
   heading per app, the look every other list had already left for
   frappe's table. Now Forms is one `onedesk.shell.table` (frappe's
   EmbeddedList): Form, App, Changes, Extensions, the changed first, its
   search and Load More, a row opening the form. A form's Extensions is a
   table too (Extension, What It Does, When, On).

   Why it kept coming back: the guard (`tests/guards/test_shell.py`) refused only a
   row that opened through `link:`, and these opened through `href:`. It now
   refuses, outside a mailbox's pane, any `shell.list`, a row that goes
   anywhere, rows made one per record in a `.map`, and the row's markup
   written by hand; each of the three would have caught the old Forms list.
   docs/SHELL.md, Lists, says so.

   The same sweep found the look in four more places, now tables:
   Settings › Mail (the mailboxes: Mailbox, Kind, Signature and Connection,
   a click on either cell signs or reconnects, a row opens OneMail),
   Settings › Notifications (the other browsers with push), Settings ›
   Agreements (Yours, Your Organisation's and Published, a row opens the
   document), and Plan and Credits (Added to the Plan). Sign-in's Password
   and Two-Factor stay rows, one fact each, drawn by the shell rather than
   by hand. An extension's Asked is prose, so paragraphs.
7. Documented: one_studio/README.md, Forms (what it lists, who sees and
   changes what, the notification, OneAI on it); One's Customizing a Form
   names Extensions and who is told.
8. Legal: nothing new. Customizing is the customer's own configuration;
   what OneAI suggests is already in the AI Addendum.
9. Built from frappe: FieldGroup and its grids, frappe's badge, empty
   state, `xcall` and `realtime`; ours is the list's grouping and counts.

**Your word, after: the form is customized only through OneAI.** "Just show
the custom fields in a table, and to add one, speak with OneAI, which asks step
by step, recommends from common sense, and works out which other forms should
have it too (an Item field onto Sales Invoice Item and the rest)."

- **The page reads; OneAI changes.** The Customize page is tables of what the
  workspace changed: Fields Added Here (each with its kind, its rules and the
  forms it was carried to; a field the form came with and carried shows too,
  marked so), Fields Changed Here, Above the Fields, Connections and Buttons,
  Extensions. A part with nothing in it is not drawn. **Add a Field** (a
  OneAI button) and a click on a field ask OneAI. No grid, no Save.
- **The tool** (`one/ai.py customize`) takes every property a field may have
  (required, unique, default, in the list or a filter, shown, required or
  read only when, filled from a linked record, never below zero, a length,
  Email, Phone or URL checked by frappe, and the rest), `also_on` to carry a
  new field and `carry` for one the form has, `remove`, and the buttons,
  charts, connections and links it could not set before. One card, checked
  as the save will check it before it is made.
- **Carrying** (`customize._carries`, `_carry`): to a table of another form
  (Sales Invoice Item) only through a form the administrator may customize;
  filled from this form through the table's own Link field (item_code before
  fg_item), read only; or copied, under the same name, when one document is
  made from another. Each is noted in this form's ledger, so its Reset takes
  them back too.
- **Research**: `form_relations` lists the tables and forms that link to a
  form and the fields it has, so nothing is added twice.
- **The layer holds it**: a field filled from a linked record only reads a
  Link field of the same form, a field there at the first level and not a
  secret, of a kind the person may read; a Data field holds only frappe's
  own checked kinds.
- **OneAI**: the chat goes step by step (what it holds, then form_relations,
  then a recommendation, then which forms carry it); the studio instruction
  says what common sense recommends, and that a check no property can say is
  an extension. The Customize page gives OneAI OneStudio's tools.
- **Tried live** (four turns on Item): it asked what the field holds; told
  "the country it was made in", it found Item has Country of Origin already;
  asked to carry it, it named the item tables; on yes, one card for Sales
  Invoice, Sales Order, Purchase Invoice and Purchase Order items, each filled
  through item_code. Approved: all four written, read only. Its first try
  named Sales Invoice Item as the form, was refused, and mended it.
- **Found on the way**: the "Add a field" suggestion expected a card on the
  first turn, so the run pressed for one before anything was asked; it now
  expects nothing.

**Your word, after: the writing.** "This shitty way of typing and writing...
so disturbing and cringe", about the note under Fields Added Here. Made the
tenth point.

- **This screen, rewritten.** Fields Added Here is **Custom Fields**, with
  "Ask OneAI to add or change a field." Fields Changed Here is **Changed
  Fields**, Above the Fields is **Form Header**. Columns are Type, Properties,
  Also Added To. Badges use frappe's words (In List View, Depends On, Fetched
  From, Non Negative, Length, Standard Field). Empty states are "No custom
  fields", "No extensions". Add a Field is **Add Field**. Reset asks "Reset
  Item? This removes all custom fields and changes." The Forms list heading is
  **Forms**, "Customized forms are listed first."
- **Docs.** One's Customizing a Form and OneStudio's Forms are rewritten in
  the same plain style.
- **The rule.** `docs/WORDING.md` gains On a Screen. `tests/guards/test_wording.py`
  gains `test_what_a_screen_says_is_plain`: no colon or semicolon joining
  clauses, no em dash, nothing over 140 characters, in every `__()` in
  `public/js`. A label and its value ("Default: {0}") is allowed.
- **Fewer notes, after your word** ("too much instructions", about Levels).
  Most section notes are gone. The ones left say a fact in a few words
  ("Custom levels sit between User and Manager."). The guard refuses
  "Open one to…", "Click a…" and any note over 70 characters.
- **The other 48, after your word.** Every older string the guard found is
  rewritten (Settings, OneCloud, OneMail, privacy, webhooks, numbering and
  the rest), so the guard holds the whole desk with no exceptions.

**Your word, after: the tenth point on everything already passed.** One,
OneAdmin, OneMail, OneCalendar, OneTask, OneCloud and OneIntake had their
nine points done. Point 10, plain words, is now done on all seven.

- **READMEs.** Each product's README, above Under the hood, is rewritten as
  plain help docs: what the screen is for, numbered steps, short bullets,
  who sees and changes it. The facts are kept and the machinery talk is cut.
- **Screens.** About 1,000 strings rewritten across the seven products' JS
  and the Python text that shows on screen: notes removed or cut to one
  fact, frappe's words (Record Type, Restore, Disable, Link), verb + noun
  buttons, short empty states, confirmations that ask and say the effect,
  no somebody/bell/is told/kind of record. Notification descriptions and
  mails read the same way.
- **Names that changed**, with the READMEs and OneAI's page texts following:
  Needs a Look → Needs Review, Take Back → Revoke Credits, Build It → Build
  Workspace, File → Link (OneMail), Signing In → Sign-in, On Documents →
  Contact and Branding, What They See → User Permissions, Only When →
  Conditions, Who Is Told → Recipients, and the rest.
- ar and de for all of it.

**Your word, after: Custom Fields, and the Extensions look.** "Extensions
page look much cleaner than forms, and can we rename forms to Custom Fields."

- **Custom Fields** replaces Forms in OneStudio's rail. It is frappe's own
  list, like Extensions, over a virtual doctype (`Workspace Field`) read from
  the workspace's ledger: one row a field, with its form, type, status
  (Added or Changed) and the other forms it was also added to. Filters by
  form, status and app, frappe's search, sort and paging. A row opens the
  form's Customize page, **Add Field** asks OneAI, and the list refreshes on
  `one_customized`. Administrators only; nothing can be written through it.
- The count that disagreed (Item "8 changes" against two fields) is gone with
  the old list.
- **Extension page.** Where It Runs says where in words ("On My Tasks", "In
  the header of each Customer") with "On the server" or "In the browser"
  under it, and the record type as a link beside that. Every place has its
  words now, not its hook name. Code is said once.
- The eight test extensions (asked "test") are deleted.
- OneAI's Custom Fields suggestions, the page text, the Form Customized
  message and the OneStudio README follow the new name.

**Your word, after: the inner view goes.** "The inner view in custom
fields is weird and pointless."

- The Customize page is removed (its page, `public/js/customize.js`, and a
  patch deleting the Page record). Custom Fields is the one screen.
- A row asks OneAI to change that field. Add Field asks OneAI to add one.
  Actions on ticked rows are only **Export** and **Reset**, per form.
- **Custom Fields** on a form's menu (was Customize) opens the list filtered
  to that form, as does an applied OneAI card and the Form Customized
  notification.
- OneAI's page text and suggestions for the old page are gone; the list's
  own suggestions stay. OneAI calls a list what the rail calls it (Custom
  Fields, not "Workspace Field list").
- One's Customizing a Form and OneStudio's Custom Fields docs say the same.

**Your word, after: Add on Extensions too.** The Extensions list gets
**Add Extension**, for workspace administrators, which opens OneAI with "I
want a new extension." as Add Field does on Custom Fields. A row still opens
the extension's page: its code, review, Errors tab and Turn On live there.

### OneStudio › Custom Collections (was Record Types)

Your word: "Now it's time for record types, of course to a new name, Custom
Collections."

1. **Notifications**: none of its own at first. After your word, three like
   Extensions': **Collection Added** (in One and by email, with its fields
   and where its records are), **Collection Changed** and **Collection
   Deleted** (in One only by default), to the other administrators.
2. **OneAI**: **Add Collection** on the list and **Add Field** on a
   collection open OneAI. Its suggestions say "Make a collection…". The
   studio instruction tells the model to call it a collection.
3. **Intake**: nothing reads into a collection yet.
4. **Permissions**: administrators only, as before. The page is read-only,
   with no Save, and nothing on it can be typed.
5. **Cross-module**: its records live in its app's rail under Your Records.
   The page says where and opens them.
6. **Bespoke UI**: the list drops the repeated ID column and gets App as a
   choice. The page was a column of greyed inputs with a Save button and
   never showed the collection's fields. It now reads as a page: Where It
   Is, Fields (frappe's table, with Required and In List View) and Asked.
   Files, Assign, Tags and Share are gone from it.
7. **Docs**: OneStudio's README has Custom Collections, plainly, and its
   intro and Notifications section were rewritten too.
8. **Legal**: `one_studio/legal.py` still says "record type" in its clause.
   Changing it is a revision of the agreement, so it is left for a legal
   pass.
9. **Built from frappe**: list view and its settings, EmbeddedList for the
   fields, frappe's meta, badges and buttons.
10. **Plain words**: renamed throughout the screen, its errors and OneAI's
   words. The doctype id stays Record Type.

**No page of its own.** Your word: "What's the point of opening the record?
The first page is mostly pointless." A collection's page only repeated the
list and pointed at its records. It is gone, as Custom Fields' was:

- A click on a collection opens its records. An old link to its page does
  the same.
- The list shows Collection, App and Description. **Actions** has
  **Change**, which asks OneAI, and frappe's own **Delete**.
- The head (Records, the description) and the page's fields are removed.
  The notification links to the records, and so does OneAI's card.
- OneAI's second suggestion is now "Change a collection…".
- "Delete them first; deleting it would delete them too" is now "Delete
  them first."

**Deleted, then restored.** Your question: "Does a deleted custom field or
collection go into Deleted like frappe and can be restored, or does it
orphan?" Tested live, it orphaned:

- A custom field went to frappe's Deleted Documents, but the Recycle Bin
  hid it as frappe's machinery. Its column and values stayed in the table
  with no way back.
- A collection was in the bin, but restoring it brought back only its row.
  Its DocType went to the bin as Administrator's, which the bin hides.

Now a custom field and a collection are in the bin for administrators, each
with its own restore (`RESTORERS` in one/recycle.py). A field comes back into
the ledger and the Custom Fields list, with its values. A collection comes
back with its DocType and its place in its app's rail. The bin names a field
"Loyalty Tier on Customer" and calls a collection a Custom Collection.
Verified in the browser as wsadmin: both restored, the field's value back,
the collection's records list opening.

Deleted extensions showed in the bin by their random ID. Now every entry
keeps its record's title (a `one_title` field on Deleted Document, set as the
record is deleted and backfilled after migrate), so an extension reads "No
Territory Indicator".

### OneStudio › Custom Collections, second pass

Looked at again as a workspace administrator with a Company Van collection:
the Custom Collections list, the vans' list in One's rail, a new van and a
saved one.

1. **Notifications**: unchanged. Collection Added, Changed and Deleted reach
   the other administrators.
2. **OneAI**: it chose a decimal number for mileage, so a van read "48,210.000
   km". Its design tool now says whole numbers (counts, mileage, seats) are
   whole, and decimals are only for a measure that has them.
3. **Intake**: nothing reads into a collection yet.
4. **Permissions**: unchanged, and checked: the list is the administrators',
   the records are the app's people's.
5. **Cross-module**: a collection's numbering is now in Workspace ›
   **Numbering** beside every other kind of record, where it can be changed.
6. **Bespoke UI**: every record showed a random ID ("4g34bmn19o") in the
   list's ID column, its ID filter and the record's sidebar. Records are now
   numbered from the collection's initials, CV-00001 for a Company Van, as
   the workspace's documents are (`record_types.series`). Collections made
   before keep their records' IDs and number new ones
   (`patches/number_collections`); changing one does the same.
7. **Documented**: the README's Custom Collections section says how records
   are numbered and where to change it.
8. **Legal**: the terms and the AI terms said "record type". They say
   "custom collection" now. The meaning is the same, so the new versions are
   recorded rather than the revisions bumped.
9. **From frappe**: the numbering is frappe's own naming expression, checked
   by Numbering's `check_pattern` so no other kind of record shares the
   prefix.
10. **Plain words**: nothing new on screen.

**Where a collection sits.** Your question: "does custom collections now show
wherever the user wants it, like under an app or a custom app in the rail?"
It went to one app, always under a Your Records group at the bottom. Now a
collection sits in the group of its app's rail an administrator chooses, one
the rail already has (OneInventory › Assets) or a new one:

- **Actions › Move** on Custom Collections: frappe's dialog with the app and
  the group, the group offering that app's own groups. Its records stay as
  they are; who uses them follows the app.
- OneAI's card says where it will be ("OneInventory › Assets"), and OneAI
  knows each app's groups.
- The link is written into the app's site layer as a whole arrangement, as
  frappe's own sidebar editor saves one, so it can sit inside a group the app
  ships. A group of ours left empty goes, which also cleared an empty Your
  Records OneCRM had kept.
- The list has a Group column. Saved Reports and Dashboards are kept for
  their own.

Custom apps of a workspace's own, with their own icon and rail in the dock,
are in `docs/BACKLOG.md`.

### Shared by every app: the Address Book and Masters

Your question: "Where would you put salutation, gender and other small
doctypes?", and then: "contacts, addresses and other stuff also belong to the
workspace since companies, employees, customers, etc. use it."

1. **Notifications**: none. These are settings, changed by administrators.
2. **OneAI**: answers from the README (how_to) for each new section.
3. **Intake**: a contact Intake makes is in the Address Book like any other.
4. **Permissions**: Salutation, Gender, Print Heading and Address Template
   were frappe's System Manager's alone, so no administrator could add one,
   not even from a field. They are given to the workspace administrator
   (`one/masters.py`, `roles.grant`), and frappe's own "Create a new" under a
   field now works for them. Contacts and Addresses keep erpnext's rules: you
   see the ones your work lets you open.
5. **Cross-module**: Contacts and Addresses left OneCRM's rail for One's new
   **Address Book** group, since customers, suppliers, the company and
   employees all use them, and opened cold they open there.
6. **Bespoke UI**: a first cut put Salutations and Genders on Workspace ›
   Lists and the two print lists under Printing. Your word: "I don't like the
   lists idea. Maybe a masters manager tool they can open from One
   workspace?" Now **Masters** is a page of its own in One's rail
   (`one/page/masters`): the kinds down the left as a sidebar, as OneMail's
   folders and OneTask's views, under Shared, OneCRM, OneInventory and OneHR,
   each with its count; the open kind's values beside them in frappe's
   EmbeddedList, with **Add** in the page head. A value opens in frappe's
   dialog to rename or **Remove**, and says how many records use it. Print
   headings and address templates keep dialogs of their own (the template in
   frappe's Code control). A tree's root ("All Customer Groups") isn't
   listed, and a department shows its own name, not erpnext's "Sales - ONE".
7. **Documented**: One's README has the Address Book in Finding Your Way,
   and a Masters section (what each group holds, who sees it, add, rename,
   remove, the address template rule). OneCRM's README points to the Address
   Book. OneAI is told the page (`one/ai.py`) and answers from the README.
8. **Legal**: nothing new is sent anywhere.
9. **From frappe**: frappe's doctypes and Page, EmbeddedList, Dialog, Code
   control, frappe's insert, `rename_doc` and delete with its own permission
   checks, `get_linked_doctypes` for the used count, and frappe's own refusal
   to remove a value records still use.
10. **Plain words**: "Masters", "Shared", "Customer Groups", "Lead Sources",
    "Units", "Used on {0} records", "Not used on any record", "Remove {0}?".

**Who sees Masters.** Administrators see every group. An app's managers see
their app's group: Sales Manager OneCRM's, Stock, Purchase and Item Manager
OneInventory's, HR Manager OneHR's. erpnext keeps several of these for roles
of its own (Customer Group and Territory for its Sales Master Manager, Supplier
Group for its Purchase Master Manager), so One's managers are given them once
for each kind (`masters._give_managers`), and a change made later in Access
stands. Checked in the browser as a Sales Manager: OneCRM's five lists only,
each with Add and Remove, and Departments refused.

**Every simple list, one home.** Your question: "did you move all masters
from all doctypes into here?" Not then. Your word: "move them and remove the
rail links".
- Masters gains Market Segments and Lost Reasons (OneCRM), Tax Categories and
  Finance Books (a new OneBook group), Unit Categories (OneInventory), Project
  Types (a new OneProject group), and Skills, Key Result Areas, Grievance Types
  and ID Document Types (OneHR). Accounts and Projects Managers see their groups.
- The rail links to what Masters holds are gone: Territory, Customer Group and
  Lead Source from OneCRM's Setup; Item Groups, Units and Brands from
  OneInventory's; Project Type from OneProject's; and Branch, Department,
  Designation, KRA and Grievance Type from OneHR's Setup page.
  `test_a_master_has_one_home` keeps it so.
- Not moved, because each carries settings of its own: Sales Stage (position,
  probability, outcome; it goes back to OneCRM's Setup, where the first cut
  had taken it from), Employee Grade (salary structure, base pay), Employee
  Group (its people), Interview Type (interviewers, skills), Incoterm (code
  and title), UTM Campaign, and the leave, pay, shift and expense types.
- A value that holds more than its name, such as a department's approvers or
  a customer group's price list, has frappe's **Edit Full Form** in its
  dialog, as quick entry has.
- Your word: "some stuff in those masters have other fields beyond the name,
  for example units". Now a value's dialog draws the kind's own fields from
  frappe's meta, as quick entry does: a unit's symbol, common code, category,
  Enabled and Must Be Whole Number; an item group's parent; a customer group's
  price list and payment terms; a print heading's description; an address
  template's country, default and template. The name comes first (a Name
  field for kinds named as they are asked to be). A new value goes through
  `masters.add` with all of them; a change is frappe's rename for the name,
  then `frappe.client.save` against `modified` for the rest. Tables (a
  department's approvers, a customer group's accounts) stay behind Edit Full
  Form. The list shows what frappe's own list does beside the name
  (in_list_view): a unit's category, an item group's parent. Print headings
  and address templates no longer need dialogs of their own.

**The Masters tool, passed over.** Your word: "oneai already has full access
to those right, they are basically doctypes. Just double check and do a
passover for the new masters tool."
1. **Notifications**: none. These are settings; nobody needs telling.
2. **OneAI**: its record tools reach every kind through frappe's own
   permissions, and every write is a card a person approves. Four gaps, fixed:
   - A customer group, territory, item group, supplier group or department
     made by a card had no parent (frappe refuses a second root) and a
     department no company. `masters.place` is now their `before_insert`, so
     every path fills it in: the page, a card, frappe's form, an import.
   - No card could rename. A card that changes the field a value is named
     from (a unit's name) now renames it with frappe's `rename_doc`
     (`proposals._renamed`); saving the field alone left the name and every
     link to it behind.
   - The panel did not know which list was open: the page now keeps it in
     `?type=`, which oneai.js sends, and tells the panel when it changes. One's
     page note names the open list.
   - The page offers **Add several at once** (one card per line of a pasted
     list) and **What is this list for?** (how_to).
   Checked as the workspace administrator: a card made a customer group under
   All Customer Groups, a department "Zz Support - ONE" for the company, a
   lead source by its typed name, and renamed a unit with its symbol changed.
3. **Intake**: none. Intake matches what it reads to existing values; it does
   not make them.
4. **Permissions**: unchanged; page and cards both answer to frappe's.
5. **Cross-module**: each app's lists in one place; Edit Full Form opens the
   value in frappe's form, in One's rail.
6. **Bespoke UI**: on a phone the panes stack, so choosing a list scrolls to
   it.
7. **Documented**: README says where a new tree value goes.
8. **Legal**: nothing new is sent anywhere.
9. **From frappe**: `before_insert`, `rename_doc`, `frappe.realtime`
   (`doctype_subscribe`, `list_update`): a value added anywhere redraws the
   open list and its count.
10. **Plain words**: **Add Unit** rather than Add, **New Unit** as the
    dialog's title, "Used on 1 record".

Your word, last: "make sections collapsible and add the svg logo to each app
so it's more organized". Each group's name now carries its app's mark (One's
own for Shared), and folds away with a chevron, as the rail's sections do.
What a person folded is kept in frappe's user settings, as OneMail keeps its
own; the open list's group stays open.

**An address template runs as code.** It is Jinja, drawn wherever an address
is shown or printed, so one the workspace writes is held as a mail template is:
every tag it adds names a field of the address, is an `if` on one and its
`endif`, or a plain label in the reader's language (`{{ _("Phone") }}`);
the tags it already had stay. Checked in the browser: a template reading
another table through `frappe.db` is refused with "An address template can
name a field of the address, as {{ city }}, and nothing else."

### Breadcrumbs, everywhere

Your word: "when you go to Masters and open a record, Masters doesn't show in
the breadcrumbs. Fix this all over the app, I noticed many similar issues."

A crawl opened every DocType and Page link in every One rail, as an
administrator, then each list's newest record, and read the trail. Four kinds
of fault:
1. **The record's crumb disagreed with its own list.** Recycle Bin, Data
   Copies, Account Deletions, Changes, Sign-ins, Exports and Prints, Chart of
   Accounts, Cost Centers, Warehouses and Locations: the list said the rail's
   name, the record went back to "Deleted Document", "Version", "Account".
   The renaming was installed only once a list had been opened, so a record
   opened by its address, or after a reload, missed it.
2. **41 more said the doctype, not the row**: Contacts, Items, Payments,
   Exemption Declaration and the rest, on the list and on its records.
3. **A kind whose home is a page** (every Masters value) led to a list no
   rail links: "Department / Engineering - ONE".
4. **Three rail rows carried another row's filter**: Contacts and Addresses
   had the Recycle Bin's `restored = 0`, Announcements the Dashboards'
   `is_standard = 0`, copied when the Address Book was made. Fixed, and
   `test_a_rail_row_filters_only_its_own_list` keeps it so.

Now, set at load in shell.js: a crumb says what its row in the rail says
wherever the rails call a kind one thing (a kind that is two rows, Sales
Invoice, keeps its name); a list's and a tree's heading say the same; and a
kind a module keeps on a page leads to the page, "Masters / Departments /
Engineering", with Masters lit in the rail, by Edit Full Form or by address.
A second crawl after the change found every record's crumb matching its list
and its row.

### One's rail, grouped

Your word: "Now one sidebar has become massive lets group it into collapsible
sections".

Before, Workspace held 20 rows: settings, setup, automation and privacy
together. Now One's rail reads:

- Home, Dashboards, Announcements, Recycle Bin
- **Address Book**: Contacts, Addresses
- **You**: Profile, Notifications, Mail, Calendar, Sign-in, What OneAI
  Remembers, Agreements
- **Workspace**: General, People, Access, Holidays, Plan and Credits, Domains
- **Setup**: Masters, Numbering, Printing, Mail Templates, Approvals
- **Automation**: Notifications, Automations, Reports by Mail, Webhooks,
  Webhook Calls
- **Privacy**: Data Copies, Account Deletions
- **Audit Log**, **OneAI**, **OneIntake**

Every group folds by its name, as frappe's sidebar does (`collapsible`).
Automation, Privacy, Audit Log, OneAI and OneIntake start folded
(`keep_closed`), and the group holding the open screen opens. Who sees which
group is unchanged: administrators see Workspace, Setup, Automation, Privacy
and Audit Log; app managers see Masters.

Paths that named the old group now name the new one: the README, OneAI's page
notes, OneStudio's README, and the Data Copy notification ("Review and send it
in Privacy › Data Copies within one month"), in English, Arabic and German.

Then, "Do you think more subgroups or enough", "Idk figure it out":

- **Enough groups.** Each holds 2 to 7 rows, and frappe's sidebar is one
  level deep. More would mean groups of two and a sidebar of our own.
- **Setup starts folded** too. It's set once and rarely opened after.
- **Workspace Notifications**: Automation's Notifications row shared its name
  with You › Notifications. The page, its heading, the README section,
  OneAI's note and the paths in OneBook's README now say Workspace
  Notifications.
- **Recycle Bin stays at the top.** Everyone uses it, and Audit Log is for
  administrators only, so inside it the bin would have sat alone under an
  administrator's heading.
- **Fixed**: a settings page in a folded group, such as Workspace
  Notifications or Approvals, left its group folded on a cold load. Frappe
  looks for the active row's group before the sidebar has opened, and only
  lists look again. shell.js looks again once it has opened
  (`test_a_folded_group_opens_around_the_page_it_holds`).

Then, "Why is that ask oneai button not styled with the uniform ai style
button?": Workspace Notifications' **Ask OneAI**, beside New Rule, was a
plain ghost button with sparkles, drawn before `onedesk.oneai.button`
existed. **Fixed**: it is the shared OneAI button, and it asks the panel's
own **Make a rule** question. `test_no_oneai_button_is_drawn_by_hand` keeps
any page from drawing one by hand again. It was the only one.

### The desk around the doctypes (gaps 1 to 4)

Your word: "Yes", to starting with the four that came from the same place.
The audit (`docs/DESK-COVERAGE.md`) found frappe still booting all 46 of its,
erpnext's and hrms's sidebars and 35 workspaces for every person, and its
sidebar resolver picking among them.

- **Fixed** (`one/outside.py`): for everyone but the platform's own people,
  the boot carries One's 15 sidebars, One's first, and One's workspaces. The
  same holds when a sidebar is swapped in after a change (`reports.sidebars`).
- **Fixed**: the addresses of the workspaces taken out, and `/desk` itself,
  go to One's Home (`one_elsewhere`, desk.js). Signing in no longer shows
  frappe's apps screen.
- **Fixed**: a private workspace can no longer be made (`has_create_access`).
- Checked in the browser as the workspace administrator and as Rania (an
  ordinary user): `/desk`, Accounting, erpnext's Home and Build go to One's
  Home; ToDo, Notification Log, Address, User, Quality Goal, Communication and
  Print Settings open cold in One's sidebar; an address opened from
  Customers keeps OneCRM's; search offers no erpnext workspace. The
  Administrator keeps frappe's whole desk (51 sidebars).

### The desk around the doctypes (gaps 5 and 6)

Your word: "Yes do 5 and 6".

- **Fixed** (`public/js/outside.js`): View Audit Trail, Setup Auto Email and
  the print page's Print Settings are offered only to whoever can read where
  they go, on frappe's own check, so an administrator keeps the last two.
- **Fixed**: Help › System Health has a navbar condition on the same check
  (`declutter.SHOW_IF`, and a patch for sites already installed).
- **Fixed**: Import is gone from every list (`can_import` empty in the boot),
  since Data Import is the platform's.
- **Fixed**: Edit Sidebar and Manage Dock are not offered on One's desk.
- Checked as the workspace administrator and as Rania: a list's menu is
  Customize Quick Filters only, the user menu is Settings, Reload and Logout,
  the help menu is empty, Setup Auto Email and Print Settings show for the
  administrator only.

### Frappe's records in One's menus

Your questions: where do frappe's own records live, should they move (into
OneCRM, say), and who can open the four menu items, and why would they.

Only Contact and Reports by Mail were in a One menu; the rest opened in
whichever menu they were reached from. One already had a screen for most of
them, so:

- **Fixed**: Address is in OneCRM beside Contact, as frappe's Contacts module
  keeps them.
- **Fixed** (`outside.js`): frappe's screens open One's instead, replacing
  the history entry so Back does not return to them. The bell's gear opens
  You › Notifications; the User list Workspace › People, a person's form
  their page there, one's own form Profile; the File list OneCloud; the ToDo
  list My Tasks; Print Settings and the Print Format and Letter Head lists
  Workspace › Printing.
- **Fixed**: the print page's Print Settings is gone for everyone. An
  administrator could only read it.
- Answered: View Audit Trail and System Health are the platform's only; a
  record's Activity tab already shows every change. Setup Auto Email is the
  administrator's, and is One › Reports by Mail.

### The desk around the doctypes (gaps 7 to 9)

Your word: "Yes do 7 to 9".

- **Fixed**: Help is **Ask OneAI** (it asks "How does this page work?"),
  in place of erpnext's documentation links. All apps is gone from the same
  menu, since it only led Home.
- **Fixed**: **Theme** is in the user menu, opening One's theme dialog,
  which was reachable only by a shortcut.
- **Fixed**: frappe's mail list and its Inbox view open OneMail.
- **Fixed**: search offers the pages and reports One's sidebars list or One's
  modules hold. Point of Sale and the Sales Funnel are gone; General Ledger
  and Stock Balance stay. Its Calendar entry is OneCalendar only.

### The desk around the doctypes (gaps 10 and 11)

Your word: "10 and 11".

- **Fixed** (`outside.js`): a desk address that is not found, or not
  permitted, shows frappe's empty state with Home, on a page that keeps the
  rail and the panel. Frappe drew its sorry picture over a bare page, and
  "No permission for Page" for an address naming no page at all.
- **Fixed** (`www/`): frappe's web pages for not found, a message, an error
  and `/me` are drawn as One's portal. `/me` sends someone with a desk to
  Profile and an account holder to `/account`. An error's details are folded
  under Show Error.
- **Fixed**: Set Password showed Sign in with a Passkey. The passkey button
  is the sign-in card's only.
- **Fixed**: **Addresses and Contacts** is in OneCRM › Sales, opening on
  customers. It is erpnext's report: frappe's own filed every row under the
  first party. Its party filter was a link to DocType, which only the
  platform may read, so it refused every pick; it is a choice of the kinds
  the reader can open.
- Kept as the platform's: Permitted Documents For User (frappe allows only
  its System Manager), Document Share Report (on DocShare, the same) and User
  Doctype Permissions (frappe's raw doctypes). Who sees what is Workspace ›
  Access and a person's page in People.

### Error pages

Your word: "I hate our error pages, not centered not spaced not fun not nice
not creative".

- **Fixed**: one scene for the web's 404, error and message pages and the
  desk's not found and no access (`templates/includes/one_lost.html`,
  `css/lost.css`, `outside.js`). It is centred on the page, with One's ring
  as the 0 of 404 and 500, turning, with the products' colours in orbit.
  Your word: "Maybe the 1 in our one logo can become 0 for 500 and 404 and
  make the entire logo the size of the font's 0", then "without the 0
  inside". So on a code the ring alone is the 0, its core empty, the height
  of the digits and on their line. Then "the same for the no access page":
  no access is 403, and a message page with any code that has a 0 in the
  middle (401, 410, 502, 503) draws it the same way. Frappe's own
  not-permitted page, which a signed-out visitor meets, says "No access"
  with "Sign in to see this page." and Sign In, in place of its "Not
  Permitted" and Login. Without a code the
  core shows a tick for a message that went well, and the 1 otherwise.
- **Fixed**: the words. "Page not found" with "The link may be broken, or
  the page has moved.", Go Back and Go Home. "Something went wrong" with
  "Try again in a moment.", Try Again and Go Home. Frappe said "Server
  Error" and "There was an error building this page".
- Light and dark, phone width, and still for anyone who asks for less motion.

### The 11 gaps, checked again

Your word: "Are you sure all 11 gaps are done or did we skip some", then
"Fix all except 12 and 13".

- Checked each of the 11 live as Rania: all hold (one commit per batch,
  1 to 4, 5 and 6, 7 to 9, 10 and 11).
- **Fixed**: a web page that does not exist (`/projects` with no project)
  showed 500 and a traceback. Frappe calls it a 404; the error page now draws
  the code frappe gives it, and the traceback only for a failure.
- **Fixed**: a kind of record the reader may not read (Pricing Rule for
  Rania) said Page not found. It is not in the reader's boot, so the router
  takes it for a page; `outside.kind_of` asks whether the address names a
  kind of record, and it says No access, 403.
- **Found, for their own pass**: gap 12, the customer portal, is erpnext's;
  gap 13, frappe's account pages (Edit Profile, Request Account Deletion,
  Third Party Apps), are frappe's.

### Portals 1: the shell, home and every list

Your word: "Ok now the gaps starting with all portals, the customer portal,
the supplier portal and whatever else... follow the pattern".

What there is: Portal Settings lists the tabs by role (a customer's
Projects, Quotations, Orders, Invoices, Shipments, Addresses, Timesheets; a
supplier's Quote Requests, Quotes, Purchase Orders, Purchase Invoices).
frappe's `portal` page lists each through the kind's own `get_list_context`;
a row template draws each row; erpnext's `order`, `rfq`, `addresses` and
`material_request_info` pages draw a record.

1. **Notifications**: nothing new. Invite as User sends frappe's welcome
   mail, already One's.
2. **OneAI**: none on the portal; a customer is not a OneAI user.
3. **Intake**: nothing lands here.
4. **Permissions**: **Fixed**: a supplier's contact invited as a user saw
   nothing, since erpnext reads the supplier's Portal Users and Invite as
   User never fills them; `one/portal.invited` now does for suppliers as for
   customers. Each still sees only their own party's records, erpnext's check.
5. **Cross-module**: the lists are OneCRM's quotations and orders, OneBook's
   invoices, OneInventory's shipments and purchase orders, OneProject's
   projects and timesheets. **Fixed**: Issues (no place in One) and
   Material Request (the workspace's own) are off the customer's tabs.
6. **Bespoke UI**: **Fixed**: the portal is One's, as /account and a
   project's page are: One's mark, the tabs as frappe-ui's TabButtons, a
   search well, one row a record as frappe-ui's ListView, pills for status,
   Show More. Home says how many of each the person has and how many
   invoices are to pay (purchase orders to deliver, for a supplier).
   Light, dark and phone.
7. **Documented**: The Portal in One's README; OneAI answers from it.
8. **Legal**: **Fixed**: the DPA says whom a workspace lets in and what they
   see (revision 4).
9. **Built from frappe**: frappe's own portal page, list contexts and
   Portal Settings; only the templates are One's.
10. **Plain words**: **Fixed**: "Request for Quotations" and "Supplier
    Quotation" are Quote Requests and Quotes; each list's heading is its tab's.

Then your word: "the portal pages can be more refined with more usage of
frappe ui components and it seems on mobile its thick in padding".

- **Fixed**: every part is drawn as frappe-ui (beta.76) draws it, read from
  its source, on espresso's tokens from frappe's website stylesheet: the head
  is One's mark and an Avatar opening a Dropdown (Sign out); the tabs are
  TabButtons (subtle) with frappe's Lucide icons; the title row has a
  TextInput (subtle) with its search icon; a list is ListView's gray head row
  and rounded rows with inset hairlines; the home is ItemListRows with icons;
  statuses are Badges. Dark values of the tokens are restated for a browser
  that prefers dark, since web pages set no data-theme. frappe-ui's own Vue
  components are not in onedesk's build, so these are its look in HTML.
- **Fixed**: on a phone the page sits 16px from the edge, the tabs scroll in
  one line with the one being read in view, and the search spans the width.
- **Fixed** (1c): on a wide screen the tabs are frappe-ui's Sidebar instead.
  SidebarHeader names the customer or supplier with the person under it and
  opens the Dropdown (Sign out); a SidebarItem for Home and each tab; the
  title row is PageHeader (48px, a hairline, the search on the right), which
  stays as the page scrolls. The page is edge to edge (`full_width`). A phone
  keeps the head and the scrolling tabs.

### Portals 2: a record's page

The seven kinds (quotation, order, invoice, shipment; quote, purchase order,
purchase invoice) share erpnext's `order` page.

1. **Notifications**: none from the page. erpnext's own mails link here.
2. **OneAI**: none; the portal reader is not a desk user.
3. **Intake**: nothing lands here.
4. **Permissions**: erpnext's context checks `has_website_permission` first.
   Another party's record is 403. **Fixed**: the refusal repeated "Not
   Permitted" as its message, so frappe's wording showed; it now says "No
   access" like every other refusal.
5. **Cross-module**: the invoice's totals come from OneBook's ledger
   (outstanding amount), the shipment from OneInventory's delivery note.
6. **Bespoke UI**, **Fixed**: the portal's shell (sidebar, PageHeader) with
   Breadcrumbs ("Invoices / ACC-SINV-…"), the status Badge and Download PDF in
   the head; the record's facts (date, due, valid until, delivery, their own
   reference, ship to); its items as ListView (item, quantity with its unit,
   rate, amount; on a phone the quantity and rate go under the item); the
   totals (subtotal, discount, each tax, total; paid and to pay once part is
   paid); attachments and terms. Before, erpnext's Bootstrap grid, Print
   behind an Actions menu, no dates, and totals that wrapped.
   **Fixed**: Home was lit beside the current tab on a record page.
7. **Documented**: the README's Portal section says what a record shows.
8. **Legal**: covered by the DPA's portal clause.
9. **From frappe**: erpnext's context unchanged (order.py runs it); the PDF is
   frappe's `download_pdf`, which lets a portal reader print their own record.
   Pay stays erpnext's, shown only when a payment gateway (the payments app)
   is set up, which One does not install.
10. **Plain words**: "Download PDF", "To pay", "Your reference".

### Portals 3: a supplier answers a quote request

erpnext's `rfq` page, where a supplier prices a Request for Quotation.

1. **Notifications**, **Added**: Quote Received tells whoever made the
   request, in the bell and by mail, with the supplier, the total and the
   items. erpnext's own mail to the supplier is listed as Quote Request Sent
   (mailed by erpnext, with the link to the page).
2. **OneAI**: none; the reader is a supplier.
3. **Intake**: none.
4. **Permissions**, **Fixed**:
   - erpnext's page handed its script the whole request as JSON, the other
     suppliers' names and addresses with it. One's page sends nothing but the
     rows' names; the server reads the rest from the request.
   - erpnext's script sent the whole edited request back, so a supplier could
     change items or prices of rows they did not quote. `send_quote` takes a
     rate, a quantity and notes, nothing else.
   - It checks the reader is a portal user of the supplier and that the
     request was sent to that supplier, as erpnext's mapper does.
5. **Cross-module**: the quote is OneInventory's Supplier Quotation, linked
   to the request's rows, for the buyer to compare and order.
6. **Bespoke UI**, **Fixed**: the portal's shell with Breadcrumbs, a Badge
   (To quote, Quoted) and Send Quote; the buyer's message, the date and when
   it is needed; the rows as ListView with TextInputs for quantity and rate,
   the amount and the total worked out as they type (frappe's
   `format_currency`); a Textarea for notes; Your Quotes; the terms. The
   list says To quote or Quoted for each request; a quote waiting on the
   buyer says Sent rather than erpnext's Draft. On a phone each row stacks
   its fields.
7. **Documented**: the README's Portal section.
8. **Legal**: the DPA's portal clause covers it.
9. **From frappe**, **Fixed**: erpnext's flow did not work for any supplier.
   - Its page crashed on a row with no item name.
   - Making the quote fills its defaults by reading each Item, which a portal
     user may not, so Make Quotation always failed.
   - `send_quote` takes the mapper's own steps (`add_items`,
     `validate_existing_supplier_quotation`) and saves with the session's
     user switched, as frappe's web form does for a save it has authorized.
     The quote is then set back to the supplier's user.
10. **Plain words**: "Send Quote", "To quote", "Needed by", "Notes" (was
    "Notes: ", "Quotations: ", "UOM:Nos", "Make Quotation").

### Portals 4: addresses, timesheets, projects

1. **Notifications**: none.
2. **OneAI**: none.
3. **Intake**: none.
4. **Permissions**: an address or project of another customer is refused
   (403), checked live. **Fixed**: frappe's web form refused in its own
   words ("You don't have the permissions to access this document"); every
   Not Permitted page now says No access.
5. **Cross-module**: a customer's address is OneCRM's and OneBook's (the
   customer's addresses); a project is OneProject's, its invoices OneBook's.
6. **Bespoke UI**, **Fixed**:
   - **Addresses**: One's row (title, the address on one line, a Type
     badge, the city), and Add Address in the head.
   - **An address** is frappe's web form, its fields frappe's controls, now
     inside the portal's shell (website/doctype/web_form/templates/
     web_form.html extends frappe's by its app prefix). Its head reads
     "Addresses / Mansour Warehouse" with Save Address and Discard in it; the
     boxed card is gone; after saving it goes back to the list at once
     instead of frappe's five-second "Thank you for spending your valuable
     time" page. Anyone without portal tabs gets frappe's page as before.
   - **Timesheets**: erpnext lists a row per time entry, so a timesheet came
     back once per entry. Now once, with its projects by name, what was done
     and its total hours, opening the project.
   - **Projects**: the list no longer shows a project's code where it has no
     end date. A project's page moves into the portal's shell (it had
     frappe's old sidebar and a second One mark): Breadcrumbs and status,
     progress with tasks done, the end and how far off it is, what it is part
     of, frappe-ui's Progress, then milestones, sub-projects, tasks and
     order and invoices as ListViews.
7. **Documented**: the README's Portal section.
8. **Legal**: covered by the DPA's portal clause.
9. **From frappe**: frappe's web form and controls kept; erpnext's list
   contexts kept, the timesheet's repeated rows folded in One's row template
   since no hook replaces its list.
10. **Plain words**: "Add Address", "Save Address" (was "Submit"), "Tasks"
    (was "The Work").

Not done: the Material Request page stays off with its tab (Portal 1).

### Portals 5: the account pages

1. **Notifications**: frappe's own. Deleting an account mails a link to
   confirm, then waits in Workspace › Account Deletions (Privacy Requests).
   Changing a password signs out the other sessions.
2. **OneAI**: none. A portal user has no OneAI panel.
3. **Intake**: none.
4. **Permissions**: each page is the signed-in person's own. Edit Profile
   opens only their own user (frappe's web form checks it), Third Party
   Apps lists and revokes only their own tokens, and a guest is sent to sign
   in. Someone with a desk is still sent to their Profile.
5. **Cross-module**: Delete Account feeds Workspace › Account Deletions,
   where an administrator approves it.
6. **Bespoke UI**, **Fixed**:
   - **Your Account** (`/me`) was a card of links with a heading in
     frappe's look. Now it is in the portal's shell: name and email as facts,
     then frappe-ui's rows for Edit Profile, Change Password, Third Party
     Apps, Sign out and Delete Account (in red, as frappe-ui's red menu
     option). It is in the menu under their name, on a computer and a phone.
   - **Third Party Apps** was a grey Bootstrap card, offered whether or not
     an app had been let in. Now it is offered only once one has, as a
     ListView in the shell, with Revoke on each row. frappe's confirm view
     (Cancel and a red Revoke in the head) and its revoke call are kept.
   - **Edit Profile** and **Delete Account** are frappe's web forms, in the
     shell with "Your Account /" Breadcrumbs. Home was lit beside them;
     now Home is lit only on Home. A section's heading lines up with its
     fields. Delete Account comes with their email filled in, and frappe's
     narrow card is gone. Its "Request sent" view sits on the page, with
     its tick in green.
   - **Change Password** is frappe's Set Password. For someone signed in it
     says Change Password and leads Back to Your Account, not "Back to sign
     in".
7. **Documented**: the README's Portal section (Your Account).
8. **Legal**: the Privacy Policy's rights section named only You › Profile
   › Your Data and the /your-data page. It now says a portal contact asks
   under Your Account, decided the same way. A clarification, so the new
   hash is recorded.
9. **From frappe**: frappe's web forms, controls, Set Password page and
   Third Party Apps context and script are kept. Only how they look is
   One's.
10. **Plain words**: "Delete Account" (was "Request to Delete Data"), "Send
    Request" (was "Submit"), "Request sent" and "Check your email to
    confirm." (frappe's introduction spoke of personally identifiable
    information), "No apps", "Back".

Delete Account is always offered, as it is on the desk's Settings. frappe's
setting that hid it cannot be reached in One.

### Portals 6: Account in the sidebar, and Your Data

Portals 5 put the account pages in the shell but left them behind a Your
Account page reached only from the menu, sent deletion through frappe's web
form (a lone Email field, then a bare "Request sent"), and gave a portal
reader no way to ask for a copy of their data. Change Password was still
frappe's sign-in card, outside the shell.

1. **Notifications**: a copy made ready ("Your Data Is Ready") and a deletion
   put on hold now link a portal reader to Your Data, not to a desk profile
   they cannot open (`privacy.where`). The rest are the desk's own (Copy
   Asked and Deletion Asked to the administrators, Account Deleted).
2. **OneAI**: none. A portal reader has no OneAI panel.
3. **Intake**: none.
4. **Permissions**: each page is the reader's own: `privacy.py` asks for the
   session's user only, a deletion is confirmed with their password, and an
   administrator decides. Third Party Apps lists only their own tokens.
5. **Cross-module**: Your Data files into Workspace › Data Copies and Account
   Deletions, the same requests a desk user makes.
6. **Bespoke UI**, **Fixed**:
   - **Account** is a section of the sidebar under the tabs, as frappe-ui's
     SidebarSection draws it: Profile, Password, Your Data, and Third Party
     Apps once an app is let in. On a phone they are in the avatar's menu.
     The Your Account page is gone; /me opens Profile.
   - **Profile** opens ready to edit, Save and Discard in the head, labels
     as frappe-ui's FormLabel. Saving stays on the page and says Saved, as a
     desk form does, instead of frappe's five-second thanks page.
   - **Password** is frappe's Set Password in the shell, Change Password in
     the head; frappe's script, strength meter and errors run unchanged.
   - **Your Data**: Copy of Your Data (Request My Data, its state, Download My
     Data) and Delete Account (Delete My Account in red, frappe's Dialog
     with the password, then its state and Cancel Deletion), the same calls
     and words as the desk's You › Profile › Your Data. It updates through
     `frappe.realtime` when a copy is ready.
   - frappe's deletion form (/request-for-account-deletion) now leads to
     Your Data, for guests as well.
7. **Documented**: the README's Portal section (Account).
8. **Legal**: the Privacy Policy's rights section says a portal contact asks
   for both under Your Data. A clarification, so the new hash is recorded.
9. **From frappe**: frappe's web form and controls (Profile), Set Password's
   ids and script (Password), frappe's Dialog and Password control loaded
   from its controls bundle (Your Data), `frappe.xcall`, `frappe.realtime`.
10. **Plain words**: "Account", "Profile", "Password", "Your Data", "Copy of
    Your Data", "Saved"; the desk's words for every state and button.

### Portals 7: inviting a contact to the portal

Nobody could reach the portal. Self-signup is off, and frappe's Invite as
User needs its System Manager role, which no one on a workspace holds, so
it was refused for every workspace user. Even when a login existed, erpnext
gave the Customer or Supplier role (which the portal's tabs need) only when a
System Manager added the portal user. Linking also saved the whole Customer,
so a workspace's own server script on Customer could block it.

1. **Notifications**: Portal Invitation (One, mailed to the contact): who
   invited them, to which workspace, what they will see, and a link to choose
   their password that works for 7 days, the same key as the team's
   Invitation (`invite.py`). Invite Again sends a new link and stops the old.
2. **OneAI**: none.
3. **Intake**: none. A contact Intake makes is invited the same way.
4. **Permissions**: a workspace administrator; for a customer's contact also
   Sales Manager, for a supplier's contact also Purchase Manager
   (`portal_invite.MANAGERS`). Checked in the browser and by role: a Sales
   User is refused, a Sales Manager may, a Purchase Manager may not for a
   customer's contact. An address that is a workspace user's is refused.
   Revoke turns the login off and signs it out at once, and the old link
   stops working.
5. **Cross-module**: the contact is OneCRM's (customers) or OneInventory's
   (suppliers); the login sees OneBook's invoices, OneProject's projects and
   the rest through the portal.
6. **Bespoke UI**: a Portal menu in the contact's head (frappe's custom
   button group) with Invite to Portal, Invite Again, Revoke Access and
   Restore Access as they apply, and the contact's state as frappe's form
   intro ("Invited to the portal. Not signed in yet.", "Signed in to the
   portal 2 hours ago.", "Portal access revoked.").
   - The invited contact sets a password on frappe's page and now lands on
     the portal's Home (`accounts.home_page`), not frappe's /me.
7. **Documented**: the README's Portal section (who can invite, the states,
   the buttons).
8. **Legal**: the DPA's portal clause already says a workspace invites its
   customers' and suppliers' contacts from their contact.
9. **From frappe**: frappe's form buttons, intro, confirm and alerts; the
   login is frappe's User, its password set on frappe's page; erpnext's
   Portal User row and role, added as erpnext would add them.
10. **Plain words**: "Invite to Portal", "Invite Again", "Revoke Access",
    "Restore Access", "Invitation sent".

### Portals 8: the portal again, and the public Your Data page

Every portal screen was looked at again as a customer (Karim Mansour) and a
supplier (Sara, Gulf Office), on a desktop and a phone.

**What was still wrong, and is fixed**

- Home was headed "Welcome"; it is **Home**, as its tab is.
- A project read 0% in the list and 17% on its page. Both now count the
  same way (`one_project.portal.progress`).
- A project whose work is all in sub-projects showed an empty Tasks section
  with a note. The section shows only when there are tasks or no
  sub-projects, and is empty as "No tasks yet".
- Statuses were the seller's: an order "To Deliver and Bill", a purchase
  order "To Receive and Bill". The reader sees **Confirmed**, **Delivered**
  and **To deliver** (`SAID_TO_READER`), and a quotation reads the same in
  its list and on its page.
- Tax lines read "VAT 5% @ 5.0"; the rate erpnext appends is dropped.
- Quantities and hours read "10.00 Nos" and "9.0 h"; whole numbers show
  whole (`one_portal_number`).
- Home counted three timesheets where the list had one; a row is counted
  once.
- Quote requests had an empty Total column; their columns are Number, Status
  and Needed by. Your Quotes shows each quote's total.
- An address opened as "Not Saved". The badge now compares with what was
  loaded, as a desk form does, and clears when a change is undone.
- Checkbox labels on the address form were bold; they read as frappe-ui's
  Checkbox.

**The public Your Data page** (`/your-data`, for someone without an account)

1. **Notifications**: Confirm Your Request, Your Data Is Ready to Download,
   Your Request Is On Hold and Your Data Is Being Deleted, and the users'
   Confirm Deletion. Each mail was a sentence with a bare URL after a colon.
   They now link a button-like line (**Confirm Request**, **Download Your
   Data**, **Confirm Deletion**) and say how long it works.
2. **OneAI**: none on the page. The two answers on a request (What would
   this copy give? What would deleting them remove?) are the
   administrator's.
3. **Intake**: none. The copy includes the records Intake filed under the
   address.
4. **Permissions**: anyone. The answer is the same for any address, five
   tries an hour per network address. A portal reader gets Your Data in the
   portal; someone with a desk is now taken to their profile instead of a
   note telling them to go there.
5. **Cross-module**: requests land in Workspace › Data Copies and Account
   Deletions, the same as a user's.
6. **Bespoke UI**: it was a hand-drawn form with radio cards, a long lede
   and two notes. It is now frappe's own sign-in card (`login.bundle.css`,
   the same head, field, alert banner and solid button), since the sign-in
   page links to it: Email, a **Request** choice between **Copy of My Data**
   and **Delete My Data**, one line on what that choice leaves out or
   keeps, and **Send Link**. The answer shows in the card's green banner; a
   refusal in its red one. **Back to sign in · Privacy Policy** sit where
   the sign-in card's links do. The passkey button and footnote the sign-in
   page adds stay off it.
   - A link that no longer works says how long links work and offers **Ask
     Again**. An opened link says **Request Confirmed** and when the
     workspace will answer.
7. **Documented**: the README's Privacy Requests section, with where signed-in
   customers and desk users ask.
8. **Legal**: unchanged. The Privacy Policy already says how a person who is
   not a user asks.
9. **From frappe**: frappe's sign-in card and styles, `alert_banner`,
   espresso's TabButtons for the choice, `frappe.call`, frappe's message
   page for the link pages.
10. **Plain words**: "Your Data", "Ask Four Degree Labs for a copy of your
    data, or to delete it.", "Send Link", "If Four Degree Labs knows this
    address, a link to confirm is on its way.", "Enter a valid email
    address."

### OneProject › Projects

Your word: "Ok time for OneProject officially". Projects is the first row of
OneProject's rail: frappe's list of ERPNext's Project, and a project's page
with its Record Head (Health, Done, Due, Cost, Billed, Margin, Overdue Tasks,
Next Milestone and the hours chart) over ERPNext's tabs: Details, Costing,
Progress, More Info, Connections, then Mail, Files and Activity. Looked at as
the workspace administrator, given OneProject's Manager level on People.

1. **Notifications**:
   - Being listed under **Users** sends ERPNext's own mail, outside the hub:
     "Project Collaboration Invitation", "You have been invited to
     collaborate on the project Villa Windows (PROJ-0005)", in English
     whatever the person's language, with no bell. Being made **Project
     Manager** sends nothing.
   - **Health** turning At Risk or Off Track tells nobody, though it is the
     one judgement a project's people need to hear.
   - The update ask and the morning summary (Project Update Asked, Project
     Summary) are One's and hold.
2. **OneAI**: OneProject has no `ai.py`. On a project the panel offers
   nothing of its own and has nothing that reads a project as its page does:
   the figures, what is late and what it holds up, the next milestone, the
   team's updates. On the list it cannot say which projects need attention.
3. **Intake**: nothing Intake reads lands on a project. A supplier's bill for
   the villa's glass is drafted with no project, so the project's **Cost**
   misses it until somebody sets it by hand.
4. **Permissions**: `members.py` holds. A Projects Manager sees every project,
   anybody else the ones they made, run, are listed on, or that list nobody,
   and what is under them, in the list and the page alike. The **Users**
   table is labelled "Project will be accessible on the website to these
   users", which is wrong here: it decides who on the team sees the project.
   Its **View attachments** column is a portal setting nobody here uses.
5. **Cross-module**: **Customer** (OneCRM, OneBook) and **Sales Order** sit
   in a folded More Info section, though billing, sub-projects and the
   portal all hang on the customer.
6. **Bespoke UI**:
   - a. **The list is cramped**: eleven columns cut the name to eight
     letters ("Villa Al Ba"). ID, Expected Start, Estimated Cost and Project
     Type take the room, and Project Manager shows an email.
   - b. **The status reads wrong**: ERPNext shows "33%" in orange in place of
     Open once a task is done, and Open in red otherwise. The same pill sits
     beside the page's title, beside **Done 33%**.
   - c. **Two rows of filters**: ID, Project Name, Parent Project, Status,
     Health, Project Manager, Project Type, Priority.
   - d. **The dates are hidden**: Expected Start and Expected End are in a
     folded Timeline at the foot of Details, under Department, Is Active,
     % Completed (the head's Done again), % Complete Method and Project
     Type. **Users** and **Customer** are folded under More Info.
   - e. **A negative amount reads backwards**: the margin says
     "1,210- د.إ" in the head and on Costing. Frappe writes "د.إ -1,210",
     and the dirham's Arabic letters make the browser read the number right
     to left. Every amount in dirhams has it, everywhere in the desk.
   - f. **Costing** is ERPNext's words: "Total Costing Amount (via
     Timesheet)", "Total Consumed Material Cost (via Stock Entry)", "Gross
     Margin %".
   - g. **Progress** asks for a Subject and a Message as soon as Collect
     Progress is ticked, though One asks in its own words when they are
     empty. Villa Windows has it ticked and both empty, so the page cannot be
     saved. "Frequency To Collect Progress" and "Weekly Time to send" are
     ERPNext's labels.
7. **Documented**: the README's project sections are the manual and OneAI
   answers from them, but they are written in the old style: dashes,
   "Health — whether it is going to plan", colons joining clauses. "Users"
   is called members in one sentence and Users in the next.
8. **Legal**: OneProject has no `legal.py`. The portal's projects are in the
   Privacy Policy (one/legal.py). If OneAI reads projects (2), the AI
   Addendum says so.
9. **Built from frappe**: the list is frappe's list, the page is frappe's
   form with the Record Head, the board is ERPNext's Kanban, the schedule
   frappe's Gantt. The page hears changes through the form's own
   `doc_subscribe`. Holds.
10. **Plain words**: the notes under Task Prefix ("Tasks made in this project
    are named with it, as WEB-14. Leave empty to use the standard series."),
    Parent Project, Health and Project Manager explain what the README
    explains, and are instructions. ERPNext's note under Message too.

**A record answers first**: the head answers (Health, Done, Due, Cost,
Billed, Margin, what is late, the next milestone) and holds, apart from the
pill (6b) and the backwards margin (6e).

Your word, earlier: "Idk figure it out". All of them, done:

- **Notifications** (`one_project/tell.py`): **Added to Project** (to each
  person added), **Made Project Manager** (to the new manager) and **Project
  Health** (to the manager and members when a project is marked At Risk or
  Off Track), all through the hub, in each person's language, never to
  whoever did it. ERPNext's English invitation is never sent
  (`members.invite`). Checked on the dev site: each arrived, and no
  invitation mail was queued.
- **Found on the way, and fixed**: a member could not be taken off a project
  by anybody in a workspace. ERPNext takes back the share with frappe's
  `share.remove`, which needs System Manager's delete on DocShare;
  `members.unlist` takes it back first. And seven of the eight projects could
  not be saved at all: they still said Hourly, which OneProject had taken off
  the choices. `patches/no_hourly_asks.py` moves them to Weekly, now the
  default.
- **OneAI** (`one_project/ai.py`): `project_facts` reads a project as its
  page does, with its late tasks, who is on each and what waits on them, the
  milestones to come and the team's updates; `projects_needing_attention`
  reads the list as the reader sees it. A `projects` group gives them on a
  project's page or when the request says "project". Suggestions on a
  project: **How is this project going?**, **What is late?**, **Write the
  customer an update**, **Plan the tasks** (OneTask's `plan_task` cards). On
  the list: **Which projects need attention?** Checked by calling the tools
  as the administrator and as Rania, who is refused; no model was called.
- **Intake**: a supplier's bill that names one open project, by its whole
  name, is drafted for that project, on the bill and each line
  (`one_project/intake.py`, `one_intake/money.py`). Two projects or none is
  left for a person.
- **The list**: Project Name, Status, Customer, Health, Project Manager (a
  name, since every link to a person now reads as one:
  `show_title_field_in_link` on User), Expected End Date and % Completed. No
  ID column or filter. One row of filters: name, customer, status, health,
  manager. Status is Open in blue, Completed in green, Cancelled in grey.
- **The page**: Details has the name, Customer and Parent Project beside
  Status, Health and Project Manager, then **Dates** (open: expected start
  and end, first and last time logged, hours logged), then **Members**. Costing
  carries the Sales Order and plain labels (Time Cost, Expense Claims,
  Purchases, Materials Used, Ordered, Billable Time, Billed, Margin). Progress
  asks How Often, Day and Time, and Subject and Message are optional. More
  Info has the priority, type, department, task prefix and how % done is
  worked out. Is Active is hidden, and % Completed shows only when it is set
  by hand. The notes under our fields are gone.
- **Amounts read the way they are written**, everywhere in the desk:
  `onedesk.shell.ltr` puts a left-to-right mark after a right-to-left symbol,
  in frappe's `format_currency` and in every Record Head's figures. "د.إ
  -1,210" now reads as written.
- **README**: rewritten in plain words, with Projects, A project's page,
  Members, Being told and Asking OneAI. OneIntake's README says a bill can
  land on a project.
- **Legal**: `one_project/legal.py`, `oneproject-asks` in the AI Addendum,
  revision 11. OneLegal had never assembled a new module's `legal.py` unless
  it was listed by hand; `test_every_modules_legal_file_is_assembled` now
  fails when one is missing.
- Arabic and German for every new string.

Noticed, not this screen's: syncing every customization on the dev site
stops at OneHR's Employee Advance ("Currency cannot be hidden and mandatory
without default"). Nothing in the repo hides it, so it is this site's own
data; it would stop `bench migrate` here.

### OneProject › Templates

Your word: "pass Templates with those fixes". Templates is OneProject's
fourth tab: frappe's list of ERPNext's Project Template, a template's own
page with its tasks in the Tasks table, and From the Library on the list, in
New Project and in Add from Template. Looked at as Samir, the project
manager, against the seventeen points.

1. **Demo coverage**: held. Aluminium & Glazing is in the demo, copied from
   its library file, and `a_template_is_laid_out_and_changed_on_its_page`
   reads and changes it, copies a preset, starts a project from one and adds
   one to a running project. Now it also checks the list's numbers.
2. **Rules on the server**: held. A template task never begins before the
   project or lasts fewer than no days (`templates.days_kept`, Task
   before_validate). **Fixed**: the list's counts are kept by the records'
   own hooks, so a bulk edit of a template task, or a project's template
   changed on import, still counts (`templates.measured`, `task_measured`,
   `used`).
3. **Hand-offs**: held. The OneProject README says where a template goes (a
   new project's tasks, a running project's) and where one comes from (Save
   as Template, the library, OneAI).
4. **Tier declared**: held (`tiers.py`: the page, and the list with From the
   Library).
5. **Our look**: **fixed**. The list showed a name, Enabled and an empty
   Project Type. It now shows **Tasks**, **Days** and **Projects**, how many
   were started from it, and Project Type is off the list.
6. **Nothing lost**: held. **Edit Details** opens frappe's form.
7. **Extensible**: held (`oneproject_template.template`).
8. **Built from frappe**: **fixed**. From the Library was a bare Select
   showing only names, empty until opened. It is now frappe's Autocomplete
   in all three places: a list to pick from or search, each preset with its
   tasks, its days and what it is for, or **In your templates** once there
   is a copy. The page's line keeps its own count. Opening Add from
   Template still drops the Template list open, as every frappe dialog does
   with a Link first.
9. **Overrides recorded**: nothing of ERPNext's is changed. The three
   fields and the hidden column are a customization of Project Template.
10. **Notifications**: none, and none needed. A template is nobody's work.
11. **Printed**: nothing leaves the company.
12. **Plain words**: held. The new words are Tasks, Days, Projects, "{0}
    tasks, {1} days" and "In your templates", in Arabic and German.
13. **Documented, and OneAI**: README updated. OneAI drafts a template as a
    card and reads the library first (`oneai_drafts_a_template_as_a_card`).
14. **Intake**: nothing Intake reads makes a template.
15. **Permissions**: held. A Projects Manager makes and changes templates,
    a Projects User reads and uses them.
16. **Legal**: nothing personal is kept on a template.
17. **Clean code**: held.

### OneProject: the project, built in stages

The design is `docs/PROJECT.md`, built one stage per commit.

**Stage 1, the project on every document.**

- **Project** on Quotation, Request for Quotation and Material Request, named
  `project` as on every other document, so ERPNext's "make from" carries it.
- **`one_project/chain.py`**: on save, lines with no project take the
  document's, and a document with no project takes its lines' when they all
  name the same one. Nine documents, both chains.
- **Extra work** is now an **Extra Work** tick beside the project, in place of
  a second "Sub-project Of" field. **Quote Extra Work** on the project starts
  one. Once ordered, the order and its lines move onto the new sub-project.
  `patches/extra_work.py` moved the old field's values over.
- **Connections** groups every document: Sub-projects, Work, Customer,
  Suppliers, Payments.
- `hooks.py` named Material Request twice, so the later entry dropped OneInventory's
  "raised" notice. `test_no_hook_table_names_a_doctype_twice` now guards it.

**Stage 2, costing in two sides.**

- **`one_project/money.py`** adds up the project and its sub-projects from
  the submitted lines that name them, before tax, as ERPNext adds up Billed
  and Purchases.
  - Customer: Quoted, Ordered, Delivered, Invoiced, Paid.
  - Cost: Ordered, Received, Billed and Paid with suppliers, then the team's
    Time, Stock Used and Expense Claims.
  - Forecast: Contract, Budget, Forecast Cost, Forecast Margin, Margin So Far.
- **The forecast cost** is spent plus what suppliers still have to bill on
  open orders, and never less than the budget. A supplier order past the
  budget shows the day it's placed.
- **Each figure opens its list**, filtered on the lines' project
  (`Purchase Order Item.project`).
- **Costing** has the Budget (ERPNext's Estimated Cost), Cost Center and Sales
  Order, then three sections drawn with the band's own figures. ERPNext's
  stored totals are hidden from the form.
- **The head** gains Forecast Margin. Margin becomes Margin So Far, which
  counts expense claims; ERPNext's gross margin leaves them out.
- **Realtime**: every submit and cancel naming a project tells that page,
  and the pages above it, to redraw (`money.moved`, after commit).
- `onedesk.shell.ltr` marked a symbol twice when given money already marked.
  It now marks once.
- Found for stage 3: ERPNext won't let a supplier bill change the order's
  rate, and "Nos" must be whole, so Bill Progress can't bill a share by
  changing the rate or quantity. Stage 3 has to work within that.

**Stage 3, subcontracts.**

- **Bill Progress** (`one_project/progress.py`, under Create on a submitted
  purchase order) drafts ERPNext's own bill from the order, each line cut to
  the share done less what's billed. ERPNext keeps the order's rate, so a
  share is a part of the quantity. `settle` makes a **Lump Sum** unit that
  can be split, and the dialog refuses a whole-number unit in plain words.
- **Retention** and **Retention Due** on the order's Terms tab. Each bill's
  payment schedule holds the retention under a **Retention** payment term
  due on that date.
  - ERPNext worked the share out on what was left after the advance (2,400
    held instead of 3,200 on a 32,000 bill with 8,000 advanced).
    `retained` sets it again after ERPNext's split, as the share of the work
    billed.
  - Changing Retention Due on the order moves it on every bill made from it.
- **Advances** paid against the order are set off by ERPNext on each bill
  (`allocate_advances_automatically`).
- **Suppliers** on Costing lists each order on the project: ordered, billed,
  left to bill, retention held, advance left and paid. The supplier opens
  the order.
- Checked on the site with an 80,000 glazing package, 10% retention and an
  8,000 advance. Billing 40% gave 32,000: 20,800 due now and 3,200 held,
  with Suppliers and the forecast to match.

**Stage 4, the customer's contract.**

- **Bill Progress** on a submitted sales order, the same code as for a
  supplier (`progress.py` covers both sides). **Retention** and **Retention
  Due** on the sales order, and on both orders they can now be set after
  submitting, since retention is often agreed late.
- **Customer** on Costing gains **Retention Held**.
- Checked with a 200,000 fit-out order and 5% retention. Billing 30% gave
  60,000: 57,000 due now and 3,000 held. After the customer paid 57,000,
  Retention Held read 3,000.

**Stage 5, budget by cost type.**

- **Cost Types** on Costing (`one_project/budget.py`): a cost type is
  ERPNext's own Budget against the project, one per expense account,
  submitted. It shows Budget, Committed (open order lines on that account),
  Spent (the ledger) and Left.
- **Add Cost Type**, changing one and Remove are ERPNext's own: a new
  Budget, or the old one revised as Revise Budget does it (cancel, copy,
  submit). Once a project has cost types, its Budget is their total and the
  field is read-only.
- **Found**: ERPNext's budget check now takes orders and spending each on
  their own. A 30,000 order with 48,000 already ordered and 32,000 spent
  passed a 100,000 budget. Cost types also turn on ERPNext's cumulative
  check, and the same order was then refused under Stop ("collectively
  exceeded by 10,000").
- **Permissions** are ERPNext's: only Accounts Manager may make a budget.
  Everybody who sees the project sees the cost types.

**Stage 6, told, asked, written down.**

- **Notifications**, both through the hub:
  - **Over Budget** goes to the project's manager and whoever set the
    budget. It's checked after every submit naming the project, and sent
    once for each budget.
  - **Progress Bill Drafted** goes to the project's manager when someone
    saves a bill or invoice made by Bill Progress. The bill shows **Work
    Done**, the share it brings the order to.
  - Checked on the site: a 30,000 order took Cost of Goods Sold to 110,000
    of 100,000, and saving a 70% bill told the manager.
- **OneAI**: `project_facts` reads the Costing tab too: both sides, the
  subcontracts, the cost types and the forecast. Two suggestions: **Where is
  the money going?** and **What's left to pay the subcontractors?**
- **Legal**: the AI Addendum's OneProject clause names the money OneAI
  reads. Revision 12.
- **README**: Budget by cost type, Subcontracts, Billing the customer, Being
  told and Asking OneAI, and Under the hood for money.py, progress.py and
  budget.py.
- **Open**: a bill holding retention shows the retention date as its Due
  Date. ERPNext sets an invoice's due date to its last payment term. The
  Payments tab shows what's due now, and "Based On Payment Terms" on
  Accounts Payable ages each part.

### OneProject: the project page, built in stages

The design is `docs/PROJECT-PAGE.md`.

**Stage 1, kinds and New Project.**

- **A project has a kind** (`one_kind`): Fixed Price, Time and Materials,
  Retainer or Internal. Retainer also has Monthly Fee and Hours a Month.
  `patches/kinds.py` gave every existing project the kind its records say:
  Fixed Price with a sales order, Time and Materials with billable time or a
  customer, Internal otherwise. A project made elsewhere (HR's checklists,
  an import) gets the same on save.
- **Add Project** is frappe's quick entry for Project, made our own
  (`ProjectQuickEntryForm`). It shows the four kinds as cards, then only
  the picked kind's fields.
  - For Fixed Price it makes the customer's Sales Order for the contract
    value, submitted, so Bill Progress works from the first day.
  - **Contract Work**, a service item in Lump Sum, is there to bill it as.
  - Checked on the site: a Fixed Price project, its order and its retention
    were made from the dialog, and Retainer and Internal from the server. A
    customer project with no customer is refused.
- **Found**: a quick entry takes each field's label and hidden flag from the
  doctype when the fieldnames match, which showed the hidden Kind and named
  the dates "Expected Start Date". The dialog's fieldnames are its own.

**Stage 2, the page.**

- **Opening a project opens its page** (`page/project_view`,
  `public/js/project_page.js`), at the project's own address. The list, a
  link, a search result and New Project all land on it. **Edit Details** is
  the same address with `?edit=1`, the form with every field; Back returns to
  the page. A new project's form is untouched.
- **The page head is frappe's**: Projects / name, the status as its
  indicator, Board and Schedule, the rest under **···**, and the kind's main
  action as the primary button (Bill Progress on a Fixed Price contract,
  Invoice Time for Time and Materials, Post Update otherwise). Each shows
  only to whoever may do it.
- **The title line**: the name with its kind and health as frappe-ui
  badges, then the parent, customer, dates and manager, and the team as
  frappe's avatar group.
- **Four figures by kind**, as the desk draws a figure (`onedesk.band.stat`,
  which gained a line under the value): label, value, a note, and
  frappe-ui's Progress where there's a whole. Red when something's wrong.
- **Tabs** are frappe's Tabs; Overview only for now (stages 3 and 4 add the
  rest).
- **Overview**: Needs You (cost types over budget, bills to check, time not
  invoiced, late tasks), milestones, hours by week and by activity, who
  logged time, the latest update, About, sub-projects and subcontracts.
  Every list is the shell's table (frappe's EmbeddedList) inside a shell
  section; a row opens what it's about.
- **Built from frappe**: one read call (`one_project/view.py` `said`, as
  the reader, checked for read permission); the record followed through the
  shell's Editor (`doc_subscribe`, `doc_update`) and money through
  `one_project_money`; the shared actions moved to
  `public/js/project_actions.js` for the page and the form alike.
- **Found and fixed on the way**:
  - A project whose contract was made before kinds had no `sales_order`, so
    Bill Progress couldn't find it. `view.contract` takes the first
    submitted order against the project.
  - This month's time read the timesheet's user through a join that frappe
    already makes for the parent filter ("Not unique table/alias"). It's
    read in a second query.
  - The mockups had boxed cards. The shell's rule is that a page draws no
    card or section of its own (`tests/guards/test_shell.py`), so the figures are
    the desk's metric, unboxed, and lists are its table.
- Checked on the site with Villa Al Barsha (Fixed Price), Villa Windows
  (Time and Materials), Halcyon Support (Retainer) and Office Move
  (Internal); list to page, Edit Details to the form and Back again.

**Stage 2, again: the page as a frappe-ui island.** The jQuery page still
did not look like frappe-ui. Frappe Books (frappe/frappe-books) builds every
screen from frappe-ui itself, and frappe's desk islands let us do the same
without leaving desk. docs/ISLANDS.md is the plan and the rule.

- The body is now `frontend/src/project/ProjectPage.vue`, drawn with
  frappe-ui:
  - the figures are NumberCard;
  - the lists are `frappe-ui/list`;
  - hours by week is frappe-ui's BarChart;
  - badges, tabs and progress are frappe-ui's.
- Desk keeps the head, filled from what the island reports: the title, the
  status and the actions.
- `onedesk.island_page` and the kit (`frontend/src/kit`) are for every app's
  screens from now on. `tests/guards/test_islands.py` guards them.
- `bench build` builds the islands through the root `package.json`, as
  Frappe Books does.
- **Found on the way**:
  - frappe-ui's `call` looks for the CSRF token on `window`, where desk
    doesn't keep it. The kit calls through desk's `xcall` instead.
  - A chart's class beside frappe-ui's own `h-full` loses; a chart is sized
    by the box around it.
  - A production build needs `esbuild` for minifying under Vite 8.

**Stage 2, a third time: the project as a workspace.** The island looked
like frappe-ui, but it still presented a project as a record with tabs of
facts. monday and Asana present it as a place where the work is done: a head
that says what it is and how it's going, then views of the same tasks, each
changed where it's shown.

- **The head** is the project's own: kind, name (click to rename), status
  and health as pills that change in place, customer, dates, manager, how
  far along and the team. Desk's head keeps only the trail, **···** and the
  main action.
- **Views in one bar**: Overview, Tasks, Board, Timeline, Files, Activity,
  kept in `?view=`. Tasks, Board and Timeline share a toolbar: Search,
  Group by, Done and New Task.
- **Tasks** is monday's table: a group per project in the tree, owner,
  status, due date and priority changed in the row, **Add Task** at the foot
  of each group. **Board** changes status by dragging. **Timeline** shows the
  dated tasks over the weeks and counts the rest.
- **A task opens beside the page**, as Asana's does, with its fields,
  description and comments; the arrow opens its full form.
- **Overview** gains the brief and an update box (health and a note, then
  Post Update). **Files** lists what's attached to the project and its
  tasks. **Activity** is `@framework/ui`'s timeline with a comment box.
- **Everything follows frappe**: tasks change through `set_value`, `insert`
  and `assign_to`; the views follow the Task list through `list_update` and
  the project through `doc_update`. Each change shows at once and is read
  back from the server.
- **Found on the way**:
  - frappe-ui 1.0 has its own tokens. `bg-surface-white` and Tailwind's
    `rounded`, `rounded-md` and `rounded-lg` draw nothing there: the task
    panel was see-through and every corner square. They're now
    `surface-base`, `surface-elevation-1` and `rounded-1` to `rounded-7`,
    and `test_an_island_uses_frappe_ui_tokens` keeps them out.
  - Importing all of `@framework/ui` pulls in parts that need a newer
    frappe-ui and fails the build. Each part is imported by its own path.
  - The timeline brings frappe-ui's editor, which put the island over
    frappe's 2 MB budget. It loads when first shown (1.3 MB now).
  - The activity timeline asked for its data at a path under the page
    (`/desk/project/frappe.desk...`) and always said "No activity yet".
    frappe-ui's resources need `frappeRequest` set as their fetcher, as a
    Frappe UI app does at start; the kit sets it now.
  - The head said 13% done and the Done figure 12%. Both read one figure
    from the server now.
  - Dates in the table were ISO and on the board "Sep 25". Both use desk's
    date format now.
  - Wording: "Add a brief", "Write an update", "Group by Project",
    "Unassigned"; the notes that read as instructions are gone.
- Checked on the site with Website Relaunch (Internal, eight tasks) and
  Villa Al Barsha (Fixed Price, three sub-projects): every view; adding a
  task, changing its status in the row and by dragging on the board,
  commenting in the task panel. The test data was put back.

**Stage 3: Money and Suppliers on the page.** The money was HTML drawn into
the form's Costing tab. It is now two views in the page's bar.

- **Money**:
  - the forecast as figures: Contract, Budget, Forecast Cost, Forecast
    Margin and Margin So Far. A project without a customer has no contract,
    so it shows Budget, Spent, Forecast Cost and Left;
  - the customer's side and the cost side as rows, each with a bar against
    what was ordered and opening the documents behind it. A side with
    nothing yet says so instead of a column of zeros;
  - Cost Types as a table (Budget, Committed, Spent, Left, Used), with **Add
    Cost Type**. A row opens the cost type to change or remove;
  - the budget changes from its figure's pencil until there are cost types.
- **Suppliers**: a card per subcontract with how much is billed, what's left,
  paid, retention and advance, **Open Order** and **Bill Progress**, and the
  totals and **New Purchase Order** above. Shown on a Fixed Price project,
  and on others once they have an order.
- **Permissions**: Money shows when the reader may see any of its documents,
  Suppliers when they may read purchase orders. Bill Progress needs Purchase
  Invoice create, New Purchase Order needs Purchase Order create, and cost
  types stay with whoever may create a Budget. A view the reader may not see
  opens Overview instead.
- **Built from frappe**: the budget, the cost type and Bill Progress open
  desk's own dialogs (`project_actions.js`, `progress.js`), the ones the
  form used, so their controls and checks are frappe's. The page redraws on
  `one_project_money` and on the project's `doc_update`, as before.
- **The form**: the Costing tab keeps the Budget and ERPNext's fields; the
  ten HTML fields that drew the money are gone
  (`patches/costing_on_the_page.py`), and project.js no longer draws them.
- **Found on the way**: the page's Budget is the whole tree's (Villa Al
  Barsha 140,500), the form's is the project's own (100,000). The pencil
  shows only where the two are the same (no cost types, no sub-projects),
  and the dialog starts from the project's own figure.
- `money.py` names each figure's doctype, so a side knows its "Ordered"
  without reading a translated label, and gives each order its status, date
  and whether it can be billed further.
- Checked on the site with Villa Al Barsha (Fixed Price, three
  subcontracts), Villa Windows (Time and Materials) and Website Relaunch
  (Internal): every figure; changing the budget (then putting it back);
  Add Cost Type and Bill Progress opening desk's dialogs.

**Stage 4: Time, Invoices and Team.** The last three views a project needed,
and Board and Timeline folded into Tasks.

- **Tasks** has a switch for **Table**, **Board** and **Timeline** (frappe-ui's
  TabButtons), as monday's views of one board, so the bar holds the views
  that show different things: Overview, Tasks, Time, Money, Invoices,
  Suppliers, Team, Files, Activity. `?view=board` and `?view=timeline` still
  open those layouts.
- **Time** (`hours.py`): the tree's timesheet entries with where each stands
  (Draft, To Invoice, Invoiced, Not Billable), figures for this month, all
  time, to invoice and invoiced, filters for To Invoice and Draft, and **Log
  Time**. Log Time writes into the reader's draft timesheet for the week, the
  one the task timer writes into, after the day's last entry so two never
  overlap. **Invoice Time** sits on the To Invoice figure.
- **Invoices** (`billing.py` `invoices`): the customer's invoices naming the
  tree on the invoice or a line, with Invoiced, Paid, Outstanding and
  Overdue, and **New Invoice**.
- **Team** (`team.py`): members, manager, assignees and whoever logged time,
  with open and late tasks and hours; **Add Member** and removing one change
  the project's Members as the form does, for whoever may change it.
- **Permissions**: Time shows to whoever may read timesheets, Invoices on a
  project with a customer to whoever may read invoices, Team to everyone who
  sees the project. Every read is the reader's own (`get_list`), so somebody
  who may see only their own timesheets sees only their hours.
- **Realtime**: Time and Invoices follow their doctype's `list_update`; Team
  follows the project's `doc_update`.
- **Found on the way**: the timesheets seeded here, as many made by HR or an
  import, have an employee and no user, so the person showed blank and Team
  counted nobody's hours. `whose` takes the employee's user, the employee's
  name to show, and with no employee the timesheet's maker, as the timer
  keeps it.
- Checked on the site with Villa Windows (Time and Materials) and Villa Al
  Barsha (Fixed Price): every view; Log Time (1.5 h, then taken out); adding
  and removing a member (the members put back).

**Stage 5: the Retainer.** A fee each month for a set number of hours.

- **Months** on a retainer's Overview: newest first from its start, the hours
  used of the allowance as a bar (red past it), the hours over, and the
  month's invoice, or **Invoice Month** for a month that has ended without
  one. Those months are also under **Needs You**, and the fourth figure is
  **Not Invoiced Yet**, the fees waiting. **Monthly Fee** says when it renews.
- **Invoice Month** (`retainer.py`), the main button on a retainer: a desk
  dialog for the month and the item, showing the hours used and any on
  timesheets not submitted, with a tick to bill the hours over when the
  month went over. It opens a draft invoice, as Invoice Time does: the month's fee, the
  hours over at the month's average billing rate, and the month's billable
  time on the Time Sheets table, so submitting it marks that time invoiced.
  The invoice carries its month (`one_retainer_month`, a read-only field on
  Sales Invoice), and a month is invoiced once.
- **No billing twice**: Invoice Time refuses a retainer, and neither the page,
  the Time view nor the form offers it on one; the form offers Invoice Month
  instead.
- **Permissions**: the months read time as the reader reads timesheets and
  invoices as they read invoices; Invoice Month needs Sales Invoice create.
- **Found on the way**: frappe's `sync_customizations` for the app stops at
  hrms's Employee Advance, so a new custom field in a fixture has to be
  synced by its own file on a dev site. `bench migrate` does the same on a
  real one.
- Checked on the site with Halcyon Support, seeded from August with 32 h,
  46 h (6 over the 40) and 10 h: the months, the dialog (46 h of 40 h, 6 h
  over for 1,800), the draft it opens (the fee, 6 h at 300, six time entries,
  13,800), and a submitted August invoice marking the month and its time
  invoiced, refused a second time, then cancelled and deleted.

**Stage 6: the phone, OneAI, notifications.** The last stage.

- **Phone** (point 6, 9): every list takes frappe-ui's columns by breakpoint
  and hides its minor cells below `md` (`max-md:hidden`), as the List's own
  docs show: Time keeps the day, who and the hours; Team the person and
  their open tasks; Invoices the invoice, status and total; the cost types
  their left and used; a retainer's months the hours and the invoice. The
  views scroll sideways in their own strip, and the task toolbar wraps with
  Search on its own line. No page scrolls sideways at 390 px.
- **Found on the way**:
  - The Activity timeline said "in 3 hours" for a change made 30 minutes
    ago: frappe-ui reads times in `systemTimezone` and shows them in
    `localTimezone`, which a Frappe UI app sets from its boot. The island
    now sets both from `frappe.boot.time_zone` (`kit/mount.js`).
  - A retainer's Time view showed **To Invoice** and **Invoiced** amounts,
    though its hours are billed with the month. It now shows this month's
    hours against the allowance, and its Invoices view has **Invoice Month**
    in place of **New Invoice**.
- **OneAI** (point 2, 7):
  - The panel names the open view as the page's section (`?view=` in
    `oneai.where()`), and the page tells it when the view changes, since
    switching views is no route change (`setQuery`).
  - `one_project.ai.page` tells the model the project, its kind and the
    view; suggestions are keyed per view (`page:project-view/<view>`, the
    board and timeline sharing Tasks'). A suggestion for some kinds only
    carries `when: {one_kind: …}`, checked on the record the page is open
    on (`suggest.py` now reads a page's `record`, and only one the reader
    may read). A retainer starts with its hours; an internal project isn't
    offered the customer update or what's still to invoice. New: **Who has
    too much on?**, **Where did the time go?**, **What's still to
    invoice?**, **How much of this month's hours are used?**
  - `project_facts` gains the kind, the time (totals, this month by person
    and task), the team's load and a retainer's months.
- **Notifications** (point 1): **Retainer Month to Invoice**, on the first of
  the month for each open retainer whose last month isn't invoiced, and
  **Retainer Hours Used**, when a submitted timesheet takes this month past
  the allowance. Both to the manager, or whoever made the project. A member
  added from Team is told by **Added to Project**, as from the form.
- **README**: the phone, a retainer's Time and Invoices, the two
  notifications, and what OneAI offers in each view.
- Checked on the site: the panel on Halcyon Support's Time view (the hours
  question first), then Team after a tab click; Villa Al Barsha's Money;
  both notifications sent to the manager; every view at 390 px.

**The OneProject rail.** Eleven rows to five: what's across projects stays,
what's a way of seeing projects becomes a view of them, and what's one
project's is on its page.

- **Projects**, **Workload** and **Time** (Timesheet, renamed) stay.
- **Project Tree** is the Projects list's **Tree View**: frappe's treeview
  over `tree.nodes`, each project with how far along it is and its health
  when at risk, **Show Completed**, a project opening its page, and
  **New Project**. frappe's add, move, rename and delete on a node are left
  out; a project is moved by its Parent Project. The report is deleted
  (`patches/tree_is_a_view.py`), and the sub-projects measure on a project
  leads to the Tree.
- **Milestones** is the **Gantt View**: frappe's, over the project's dates,
  opening by the week, with each project's milestones to come as rows of
  their own under it that can't be dragged (they're tasks). frappe's switcher
  calls it Gantt View, frappe's own word, so it's left. Onboarding and exit
  checklists are left off, as on the Tree.
- **Tasks** leaves: OneTask has the list, and a project's tasks are on its
  page.
- **Setup** is **Project Templates** and **Rates**. Rates is the Activity
  Type list; an Activity Cost, a person's own rates for one activity, is now
  its connection (**Rates for a Person**, with +) and leads back to Rates,
  and ERPNext's button opening the same list goes.
- **Projects Settings** is in the Projects list's ··· menu, for whoever may
  change it, and leads back to Projects.
- Found on the way: frappe's tree sends its root tick as the string "true",
  which `cint` reads as 0, so the first Tree was empty; and frappe's Gantt
  reads its view mode off a fresh object each time, so the default is set
  through frappe-gantt's own `change_view_mode`.

**The Projects list.** Eight columns shared the width, so the name, the one
column people scan by, was cut to "Marina Offic".

- **One pill.** Status read "Open" on nearly every row beside a Health pill.
  The pill is now an open project's health (green, orange, red) and a
  finished one's Completed or Cancelled, and filters by what it says; the
  Health column goes (`get_indicator`, `one_health` off the list view).
- **A sub-project reads after its parent**, "Villa Al Barsha › Handrails", the
  parent's part quieter (`formatters.project_name`; parents off the page are
  asked for once). frappe writes the name as text, so the quieter part is
  set after the rows are drawn.
- **Room for the name**: 260 px (a `width` property setter, which frappe's
  list reads for a column's width).
- **Due Date** and **Start Date** for Expected End and Start Date, on the
  list and the form.
- **Quick filters**: name, status, health, manager and kind, on one row;
  Customer is under Filters.
- **Sorted by Last Updated**, the projects being worked on first.
- **Add Project** on the Tree too, frappe's own words for the list's button.
- **Phone**: frappe draws the rows in a table that grows to its longest name,
  so with the parent's name the pill went off the edge. On the Projects list
  the table is a block, each row as wide as the list, and the pill no longer
  reserves 130 px for a 65 px pill.
- Money columns stay off: the list is everyone's, and the money is on each
  project's page for whoever may see it.

**The other views of Projects.** Report, Dashboard and Kanban were frappe's
defaults over ERPNext's records; Calendar drew the Gantt's bars on a month.

- **Report View** raised "Not permitted" once per manager. frappe fetches a
  person's name for a link through `get_link_title`, which asks for read on
  their User, and most people may only select a colleague. It now gives the
  name to whoever may select or read the record, and the plain name to anyone
  else, without an error (`one/link_titles.py`, an
  `override_whitelisted_methods` row). Two projects were run by Administrator,
  whom nobody else may see at all: the manager field defaults to whoever makes
  the project, and a script made them. Administrator now runs nothing
  (`members.nobody`, and `patches/nobody_runs_it.py` for the two).
- The ID column already reads as the project's name and opens it, so it is
  **Project**, and the Project Name column that repeated it is off the default
  columns.
- **Every view leaves out HR checklists** by default (`filters` in the list
  settings), as the rail's Projects row does; clearing the filter shows them.
- **Dashboard View** showed ERPNext's two: Completed Projects by when each was
  last changed, and an Open Projects count with the HR checklists in it. It is
  now OneProject's own: three numbers (Open Projects, At Risk or Off Track,
  Past Due) and four charts (open projects by kind, by manager and by
  customer, and projects started each month), standard records in
  `one_project/number_card` and `one_project/dashboard_chart`. One blue, thin
  bars, the counts over them, labels uncut.
- **Kanban View** opened on a dialog asking which field to group by. A board,
  **Projects by Health**, is now made once (`board.settle`), so it opens
  straight on it; dragging a card sets the health and tells the project's
  people.
- **Calendar View** is gone from Projects: a project is weeks long, and the
  Gantt draws it better.
- **The dashboard in colour.** Health is a donut in the pill's own green,
  orange and red; kind a pie with a colour per kind; manager and customer
  violet and orange bars; projects started a blue line across the page. A
  Group By chart lists its groups by count and frappe paints them in that
  order, so a colour belonged to whichever group was largest. A chart may now
  name a colour per label (`one_colors` in its Custom Options), set from its
  labels each time it draws (`public/js/chart_colors.js`), and a pie or donut
  so coloured has its legend as a wrapping row under it: frappe-charts spaced
  items 150 px apart with one too many on a row, so "Time and Materials" ran
  into the next and the fourth went off the edge.

**New Project in three steps.** The dialog was the four kinds above eight
fields split by three rules, with no kind looking picked, money fields reading
0.00 and 0, and the fields of a kind nobody had chosen yet.

- frappe-ui has no stepper or wizard in any version on the bench; the desk
  has `frappe.ui.Slides`, the setup wizard's, so the dialog is three Slides:
  **Kind** (the cards; a click picks and moves on), **Details** (name, customer
  and what the kind needs) and **Plan** (dates, manager, template). The dots
  are frappe's; the dialog's own footer carries **Previous**, **Next** and
  **Create Project**, and the first step has none, since a card moves on.
- Next checks the step's own fields with frappe's missing-fields message;
  Previous keeps what was typed. Every step is the same height, so the dialog
  doesn't jump and the date's calendar has room.
- Two things frappe's Slide doesn't do in a dialog: a Slide's fields are a
  plain field group, where frappe applies `mandatory_depends_on` only for a
  dialog's, so Customer is marked required by setting `is_dialog`; and a Slide
  copies its fields as JSON, so Bill As's item filter is set after.
- Money fields start empty.
- A retainer has no end: Plan asks only when it starts, and an end typed
  before the kind became Retainer is left out.
- The kind cards were square: they asked for `--border-radius-lg`, a token
  frappe no longer has, so the corner fell back to none. They now use frappe's
  `--radius-md`, a grey surface on hover and a dark ring once picked, as
  frappe-ui's padded Radio does. Four other corners in desk.css and
  settings.css (the Domains DNS table among them) used the old names too, and
  a test keeps them out.


**Featured Media.** Every project's folder in OneCloud has a Featured Media
folder: the photos and videos the project is shown with.

- Nothing is stored for the folder. Like the project's own folder, it is worked
  out from the files attached to the project: those marked `one_featured`
  (File). Putting a file in attaches it to the project and marks it; dragging it
  back to the project's folder clears the mark. A folder of that name anywhere
  else is just a folder (`@featured/<project>`, namespace.py).
- Only photos and videos go in, and they are public: shown on the project's page,
  on the customer's portal, and anywhere else by link. Taken out, a file needs a
  sign-in again. The privacy notice says so (revision 17).
- The newest photo is the project's **Cover** (`one_cover`, Project's image
  field), kept in step as files come and go. frappe refuses to delete a file a
  record's field still names, so `CloudFile.on_trash` hands the Cover to the
  next photo first.
- The customer's portal page for a project opens with them: the newest large,
  up to four beside it, two rows on a phone.
- A drive (WebDAV) can drop files into it, and a file request made from it
  lands in the project.


**The page per kind.** Every kind had the same page: the brief box empty at the
top, four figures, a full update form, and Needs You repeating what sections
already showed.

- The head has the cover from Featured Media with the next three beside it,
  opening the rest in frappe-ui's Dialog with **Add Photos** and **Open
  Folder**. With none yet, **Add Cover** opens frappe's upload dialog, sending
  the file to Featured Media (`media.add` as its `method`). The rest of the
  head is the kind's: the contract on Fixed Price, the start and hours a month
  on a Retainer (no progress bar, since it doesn't end), days left on Internal.
- The Overview is laid out per kind, each thing once:
  - Fixed Price: Contract, Billed, Cost against the budget, Forecast Margin;
    Work and Billing (done, billed, paid), Budget by cost type, Milestones;
    Subcontracts and Retention (held, rate, due) beside.
  - Time and Materials: Not Invoiced Yet, Hours This Month, Invoiced, Budget
    Used; Hours by Week, Not Invoiced Yet by person with Invoice Time; By
    Activity beside.
  - Retainer: This Month, Monthly Fee, Months Not Invoiced, Invoiced; Months
    (the one place a month waiting for its invoice shows), Hours by Week; By
    Person and By Activity beside.
  - Internal: Done, Due, Overdue Tasks, Budget Used with a budget; Tasks by
    status as one bar, Milestones, Due Soon; Who's On It beside.
- Needs You keeps cost types over budget (not on Fixed Price, where Budget
  shows them), bills to check and late tasks.
- The brief shows only once written; until then **Add Brief** is under About.
- Updates is the latest update and one line to post the next, with the health
  beside it; earlier ones open under it.
- Budget Used read 100% at most. It now says the real share, 156% when over.
- Hours This Month counted this project only, Hours by Week its whole tree,
  and nothing said the chart was twelve weeks. Both count the tree; the chart
  says "5.5 h in 12 weeks".
- A task with no due date counted as late, in Needs You and in the late
  count: frappe reads a missing date as the earliest one. Both ask for a date.
- By Person was empty on a retainer whose timesheets have an employee and no
  user. It now names the employee.

**Featured Media turning.** Of four heads drawn with real photos (one photo
across the page with the name over it, a mosaic, the project beside its
photos, a strip), the first is the project page's and the third the portal's.

- Both turn on their own: the cover, then each photo for six seconds with a
  slow draw-in, and each video muted to its end. A single video plays on a
  loop. A bar per item shows where it is; the pointer over it pauses it.
  Someone whose system asks for less motion gets the photos still.
- The portal's is plain JavaScript (`public/js/one_gallery.js`) beside the
  project's facts, with arrows, a count and the small photos below; on a
  phone the photos come first.
- Both show the cover first (`media.shown`), so the page and the portal open on
  the same photo.
- ERPNext lets a Project have four attachments, which stopped Featured Media
  and the project's folder at four files. A property setter lifts it.

**One row under the photo.** Under the photo were a row of facts and a row of
tabs, two thin lines of grey text that read as one. The facts and status now
sit on the photo under the name, the team in its corner, the photo's own
buttons at its top right, so the views are the only row under it. Progress
was there twice and is now only in Overview's figures. On a phone the facts go
under the photo. Without photos the head was still the kind's icon, the name and
a badge, then a row of facts, then the tabs; it is now a plain panel laid out as
the photo is (kind, name, facts, team, **Add Cover** in the corner), so every
project's page is a head, the views, then the page.

**The contract, and before it.** A Fixed Price project's contract could only
be set in the New Project dialog. One made without it, or started from a
quotation, showed a contract of 0 and a forecast margin of 0, with no way to
set it from the page.

- While the customer's quotation is open and nothing is ordered, the first
  card is **Quoted** with the quotation's value, "Not ordered yet" and **Make
  Order**, which runs ERPNext's quotation mapper (a quotation with
  alternatives opens instead). The forecast margin is against the quote.
- With neither, the card offers **Add Contract**: Contract Value, Bill As and
  Retention, making the same submitted Sales Order the dialog makes.
- The contract's order was made in the company's currency, which ERPNext
  refuses for a customer billed in another one ("can only be made in
  currency: USD"). It now takes the customer's currency, in the dialog too.
- **···** offers **New Quotation** on such a project, and **Quote Extra Work**
  once there's a contract.
- Figures gained a button under a figure, frappe-ui's Button.

**Quotes and currencies, after the contract work** (checked against "What
ERPNext already does"):

- **Invoice Time** (`billing.py`) and **Invoice Month** (`retainer.py`) made
  their sales invoice in the company's currency, which ERPNext refused for a
  customer billed in USD. OneInventory's reorder did the same for a supplier.
  All of them, and the contract, now go through OneBook's `currency.py`
  (`bill_in`), which sets the party's currency and its rate as the form would.
  Hours are turned into the invoice's currency from each timesheet's own, as
  ERPNext's Fetch Timesheet does. ERPNext keeps one rate per pair and doesn't
  read it backwards, so `rate` inverts the other way's when that's all there
  is.
- A retainer's monthly fee and a contract's value are agreed in the customer's
  currency. The New Project dialog asks for them in it, the page shows the fee
  in it, and Invoice Month bills it as it is.
- **Quoted** under Money counted every quotation that wasn't Lost, so an
  expired one and an earlier revision counted too. It now counts those still
  standing (Open, Replied, Partially Ordered, Ordered).
- The Overview showed only the newest open quotation. With several it now
  says "2 open quotes" and opens them as a list, so the right one is ordered.
- A quotation made from a deal had no project. The Project field now offers
  the customer's open projects, and names the one Fixed Price project with
  nothing ordered yet when there's exactly one.

**Quoting from the page.** Looking again at a quoted project:

- **New Quotation** hid once a quote existed, which is just when a revised
  quote or a second option is wanted. It now stays in **···** until the
  project is ordered.
- The main button was **Post Update** while the next step was the customer's
  order. With one quote open it's **Make Order**, which left the figure.
- The page never listed its quotations. **Quotations** on the Overview lists
  them, newest first, drafts too, each with where it stands.
- **Work and Billing** showed three empty bars before anything was ordered.
  It shows once there's an order.
- **Billed** read "0%, 0 invoiced" on a quoted project. While quoted it's
  **Valid Till**, the quote's last day and how far off it is; with no quote
  and no order it isn't shown.

**Status.** ERPNext has four (Open, On hold, Completed, Cancelled) and sets
the status again on every save from the project's tasks.

- Marking a project with open tasks Completed didn't hold. The save set it
  back to Open while the pill still said Completed. Completing or cancelling
  now asks about the open tasks and sub-projects ("Al Manar Fit-out still has
  2 open tasks. Complete them too?") and closes them with it; No leaves it as
  it was. A task already closed keeps its own status, unlike ERPNext's
  `set_project_status`, which overwrites them all.
- Completing a project with no tasks of its own turned its progress to by
  hand at 100% for good. Opening it again puts progress back on its tasks.
- Opening a project whose tasks are all done would complete itself again on
  save. It now says so and asks for a new task.
- **On hold** wasn't offered anywhere. The pill, the Projects list and the
  portal have it, in amber.
- A project completed with money still owed said nothing. **Needs You** lists
  the contract not invoiced, invoices not paid and retention held, and the
  manager gets **Project Completed** with what's still owed.
- The health pill showed on a completed project. Health is how an open
  project is going, so it shows only while Open, as the list and head do.
- A completed project read 0% done when it had no tasks of its own, since
  done is counted from tasks. Completed reads 100% on the page, the head,
  its parent's sub-projects, OneAI and the portal.

**Several orders on one project.** **Contract** already added up every
submitted order on the project and those under it, as ERPNext's own total
sales figure does. But the head, **Bill Progress**, **Retention** and About
each read one order, the project's own or its first. A variation ordered as a
second order on the same project was counted and then couldn't be billed from
the page.

- With more than one order, the head says "2 orders" and opens them as a
  list.
- **Bill Progress** asks which order to bill, each with what's left on it,
  then opens the same Bill Progress as before.
- **Retention** adds up across the orders, gives the rate only when they all
  hold the same, and the first day any is due.
- **Orders** on the Overview lists each with its amount and how much is
  billed, in place of About's single Contract line.

**Numbers, one by one.** Contract, Billed, Cost and Forecast Margin, each
over the project and those under it, in the company's currency.

- Cost turned red when the forecast passed the budget, with only "of 140,500
  budget" under it, so 63,210 read as fine and red at once. The note now says
  "Forecast over by 710" when it is.
- What suppliers still have to bill on their orders counts in the forecast,
  but showed under Cost only when there was no budget. It shows either way
  ("78,000 on order"), each part on its own line.
- Billed, Cost and Forecast Margin led nowhere. Billed opens Invoices, and
  Cost and Forecast Margin open Money, for whoever sees those views.

**Work and Billing.** Three bars, Work Done, Billed and Paid, each a share of
the contract.

- Work Done counted every task the same and ignored the project's own %
  Complete Method. It now follows it over the project and those under it:
  tasks completed, each task's progress, or progress by weight, with a
  completed task all done (`overview.progress`).
- Billed repeated Numbers. In its place the gap, as an amount: Not Invoiced
  Yet with Bill Progress beside it, or Billed Ahead of the Work.
- Paid read as a late payment when the gap was retention. In its place Owed,
  saying how much is overdue and how much is retention, and Paid in Advance
  when the customer has paid more than is invoiced.
- Nothing said when the customer was last billed. Last Billed now gives the
  newest invoice's date and the share of the contract billed by then: the
  invoice's own Work Done when it's a progress invoice, or else invoiced over
  contract. A return isn't counted.

**Budget.** A row for each cost type with a bar, used of budget, and left or
over.

- It covered the project alone while Numbers covers its sub-projects too, so
  Villa Al Barsha read 10,000 over in Budget and 710 over in Numbers. It now
  adds up each cost type over the tree. A cost type counts only what's spent
  and ordered on the projects that budget for it, as ERPNext's own check
  does (`budget.across`).
- What fell outside the cost types (budget not split, a sub-project's bills,
  the team's time, which ERPNext books to no account) showed nowhere. Other
  now carries it, so the rows add up to Numbers' Budget and Cost
  (`budget.other`).
- "110,000 of 100,000" mixed spent with ordered. The row now says each, and
  the bar shows spent dark and on order light.
- No way to Money, where cost types are set, and nothing when there were
  none. The heading's arrow opens Money, "No cost types" shows when there are
  none, and a count shows when the rows are cut short.

**Milestones.** Tasks marked Is Milestone over the tree, on a line.

- Handover sat on Glass for handrails, two levels down, and read as Villa Al
  Barsha's own. A milestone on a sub-project now says where it is, as a path.
- A late milestone looked like one to come. Each now says how far off it is,
  or how late in red.
- The first 8 by date could all be done, and an undated one came first. Now
  the last two done, then the ones to come, undated last (`milestones.pick`).
- No way in. Add Milestone asks for the name, the project in the tree, the
  due date, and on a Fixed Price project the share to bill. The task panel
  has a Milestone switch.
- Billing on milestones, optional: Bill on Completion (`one_bill_share` on
  Task). Only when a milestone has one does Work and Billing count the
  shares of the milestones done (Billable on Milestones) instead of the work
  done, Bill Progress start from it, and Milestone Done tell the manager of
  the project with the order. ERPNext's own payment terms stay as they are.

**Updates.** The team's latest note and a line to post the next one.

- The Health pill on the line saved only with a post and the head's saved at
  once. Health is set in the head; the line shows it read-only.
- An update kept no health. Each answer now keeps the project's health when
  written (`one_health` on Project User), shown on it.
- Nothing on the page said an update was due. "Your update is due today"
  shows on a day you're asked (`updates.asked`).
- Whether and how often the team is asked was on the desk form only. The
  heading says it ("Asked every Monday", `updates.asking`), and Ask for
  Updates opens ERPNext's own Collect Progress fields, saved against the
  project as loaded.
- Another person's update showed only on reload. A post tells the page
  (`one_project_update`).
- Line breaks were flattened and notes cut at 600 characters. Lines are kept,
  and a long note opens with Show More.
- Post Update in the menu opened a second, separate dialog. It now brings the
  reader to the line.
- OneAI: Draft my update reads the reader's week (`project_facts` `you`) and
  suggests a card; approving puts the draft in the line. Nothing is posted.

**Needs You.** What wants somebody now, worst first.

- "Bill from Gulf Office Supplies to check" lost its verb to the cut. Rows
  now lead with it: Check bill from, Check invoice to.
- Late tasks didn't say where they were. A task on a sub-project now says
  which, as Milestones does.
- Nothing was the reader's own. Their tasks and bills come first, marked You.
- A task due today showed nowhere on a Fixed Price Overview. It's here, in
  orange, "Today".
- The count was of the rows shown, at most 8. It now counts everything, and
  Show All opens the late tasks in the desk's list.
- Over budget read the project alone on the other kinds. It now reads the
  tree's cost types, as Budget does.

**Subcontracts.** Each supplier's order on the tree, with how far it's billed.

- Two Gulf Office Supplies rows looked the same. Each now says what it's for
  (its first line, and how many more, `money.bought`).
- Al Noor's order is on Villa Windows and read as the villa's own. It says
  where, as Milestones does.
- "Billed" with a full bar hid that Al Noor billed the frames in full with
  Villa Windows half done. An order billed ahead of the work on its project
  gets an amber dot and how far the work is.
- What's owed to suppliers was nowhere on the Overview. Each row says what's
  to pay, retention aside (`to_pay`), and a bill with a payment past due is
  in Needs You as Pay the supplier, read from the payment schedule since
  ERPNext only marks a bill Overdue overnight.
- No way to Suppliers, and a count of the rows shown. The heading's arrow
  opens Suppliers, the count is of every order, and Show All goes there.
- The right column is narrow, so the bar gave way to lines under the name
  (`lines` on Rows). "1 days late" reads "1 day late" across the page.

**Orders.** The customer's orders, with what's left to bill.

- It read the project's own orders only, 160,000 of Villa Al Barsha's
  375,000, both at 0% while 60,000 was invoiced, on Handrails' order. It now
  lists every order on the tree, oldest first, and says where each is.
- Two Window Works rows were told apart by number alone. Each says what it's
  for (`money.bought`), and extra work has an Extra Work badge (`badge` on
  Rows, frappe-ui's Badge).
- Only a percentage. A part-billed order says what's left, and one on hold or
  closed shows ERPNext's status instead of a share it can't be billed on.
- No way to the orders. The heading's arrow and Show All open them across
  the tree, and the head's "4 orders" counts the same.
- Bill Progress offered only the project's own orders, so Handrails' couldn't
  be billed from the villa. It offers each open order on the tree, with where
  it is, and the milestones' share starts only the project's own.
- Retention read the same own orders and hid the 3,000 held on Handrails. It
  shows, at 5%, due 30-09-2027.

**Retention.** What the customer holds back, and what's held from suppliers.
ERPNext has no retention of its own. One's is ERPNext's invoice and payment
schedule, so the accounts are ERPNext's in any country.

- Every workspace saw Retention on every order, though only contractors hold
  it. **Hold Retention** in Projects Settings is off for a new workspace, and
  was turned on by the update where an order already holds it. Off, it leaves
  the orders, the New Project and Add Contract dialogs and the Overview.
- Only the customer's side. The Overview sets **From the Customer** 3,000 at
  5%, due 30-09-2027, beside **To Suppliers** 3,200 at 10%, due 31-03-2027,
  with the arrow to Money.
- One release date, where building work releases half at handover.
  **Released at Handover** on the order splits each invoice's retention in
  two: that part due on the delivery date, or the day the project is marked
  Completed, and the rest at Retention Due (`retention.parts`,
  `handed_over`).
- Nothing reminded anyone a year on. Needs You asks for the customer's
  retention a month ahead, says "Pay retention to" a supplier when theirs is
  due, and the manager gets **Retention Due** on the day.

**About.** The project's facts.

- Four of its five rows repeated the head: customer, manager, order, dates.
  About now has what the head doesn't: Progress, Due with how far off or
  late, Team and Priority.
- Where a sub-project sits was its last row. The breadcrumb names its
  parents, Projects / Villa Al Barsha / Handrails / Glass for handrails
  (`trail`'s `between`, frappe's custom breadcrumb).
- How Work Done is measured wasn't on the page, so Handrails read 0% done at
  30% billed with no reason given. Progress shows ERPNext's % Complete Method.
- Nothing changed in place. The pencil opens Manager, dates, Progress (with
  % Complete when Manual) and Priority as frappe's own controls, from the
  Project's fields. Saved with the `modified` the page loaded, a change made
  meanwhile is refused with frappe's "has been modified after you have opened
  it".
- Add Brief opened the whole desk form. It writes the brief in frappe's text
  editor, and the Brief section has its own pencil.
- "About" as a heading read "Worum" in German, the Mail Rule's sense. It
  has its own context ("About", "Project") and reads "Angaben".

**Sub-projects.** The projects under this one.

- Villa Windows is 7 days late, At Risk and 11,210 over its 20,000 budget,
  and its row was a grey bar at 50% like the rest. Each row now says its
  kind, when it's due or how late, and who runs it, with a red dot for late,
  Off Track or over budget and amber for At Risk.
- `tree.totals` added up each branch's money and the section dropped it.
  Each row says what's ordered and billed, or what's spent against the
  budget (`branch_money`).
- Pergola, ordered as extra work, read as the contract. It has the Extra
  Work badge, and Handrails says "1 sub-project".
- The count was of the rows shown, at most 6. It counts them all, and Show
  All opens the Projects list under this one.
- A sub-project could only come from extra work, Group Under New Project or
  the desk form. Add Sub-project, in the section and the menu, opens New
  Sub-project with this project and its customer filled in.

**Tasks.** Settled first, ERPNext's own everywhere and fit for any company:
the same task as OneTask's; order is ERPNext's Depends On, with what's
waiting shown and the people told when it's ready, no harder lock; templates
are ERPNext's Project Templates, added to a running project too; one
progress figure, ERPNext's % Complete; a User Group assigns its members, as
frappe's Assign does; Pending Review tells whoever made the task.

- The tab read the projects directly under, so Glass for handrails' Fit the
  rails (9 days late) and Handover (a milestone) were missing, though Needs
  You and Milestones showed them. It reads every project under, at any
  depth, titled by path, and Board and Timeline with it.
- Villa Al Barsha's page said 29% done while ERPNext's % Complete, which the
  Projects list, board and reports read, said 0%: ERPNext counts a project's
  own tasks only. A project with sub-projects now stores its tree's figure
  as its % Complete, the way ERPNext measures (a cancelled task is
  finished), whenever a task or project under it changes
  (`overview.roll_up`), and the page reads it. The villa reads 28.57% in
  both, and completing Measure the openings moves Villa Windows to 75% and
  the villa to 42.86%.
- Install the handrails, due today, looked ready though it waits on Fit the
  frames, 3 days late. A task with an open Depends On says "Waiting on Fit
  the frames" under its name.
- Hours were in the panel only. Hours is a column, changed in place
  (frappe-ui's TextInput), and each group's heading adds them up: Villa
  Windows 27 h.
- Sub-tasks were drawn flat. Each sits under its Parent Task, indented, and
  a parent says how many of its own are done (`nest`).
- The panel was a smaller task than OneTask's. It has the checklist (ticked
  and added, the task saved so its progress follows), sub-tasks, what it
  waits on, the timer, Repeat (frappe's own Auto Repeat prompt), and Edit
  Details: type, hours, parent task, Waits On as frappe's table, Bill on
  Completion and the description, saved against the task as loaded.
- Task links named tasks by number (TASK-2026-00032). Task shows its title
  in links (frappe's Show Title in Link Fields), everywhere.
- A task could be given only to one person at a time. The Owner menu lists
  the workspace's groups too, and a group gives it to each member, as
  frappe's Assign To does (`_user_groups`). No shared queue: ERPNext has
  none.
- A template could only start a new project. **Add from Template** adds one
  to a running project, through ERPNext's own copy, dated from the day
  chosen (`templates.add`).
- Nobody heard when a task could go ahead, was sent for review, or moved.
  OneTask tells them: Task Ready (its last dependency done), Pending Review
  (to whoever gave and made it) and Due Date Changed (to whoever has it).
  Order stays ERPNext's Depends On, which already stops a task being
  completed early, with no lock on starting. A formal sign-off is a Workflow
  under Approvals.

**Time** (the project page's Time view).

- Every project was treated as billing its hours. A project now says how its
  time is counted, apart from how it's paid for: Timesheets, Attendance on
  Site (with its site, a Shift Location) or Not Tracked (`hours.fill`),
  asked in New Project's Plan step, changed in About, defaulted from Projects
  Settings' Count Time By. Existing projects kept Timesheets
  (patches/time_counted.py).
- Time logged on a Fixed Price project with a customer was billable, so it
  turned up as To Invoice. Billable now follows the kind, in Log Time and the
  task timer (`bills_hours`): Time and Materials and Retainer bill hours,
  Fixed Price and Internal count them as cost.
- Invoice Time on the villa did nothing: its To Invoice counted the tree,
  the button only the villa. Invoice Time now takes the whole tree's billable
  hours for the same customer, each Time Sheets row naming its project
  (`billing._rows`), so the villa invoices the windows' 9 hours, 2,560.
- A Projects User saw To Invoice 0 and "–" amounts, because ERPNext keeps
  time rates to Accounts Users. Money now shows only to those who may read
  rates (`sees_rates`), and is ERPNext's base amounts, in the company's
  currency.
- The figures were the same for every kind. Now Logged against the tasks'
  planned hours (9 of 45 on the villa), This Month, To Invoice and Invoiced
  where hours are billed (on the villa, "On Villa Windows"), and Labour Cost
  (1,210).
- No breakdown: Group By person, activity, task or sub-project, with totals.
  The filters have all four states. The Task column shows the task with its
  sub-project under it.
- Log Time from a parent put the hours on the parent. It asks which project,
  and a task picks its own. Old drafts are in Needs You as Submit your
  timesheet (`late_drafts`). A project that doesn't track time has no Time
  view unless time was logged on it.
- Site crews' time had nowhere to come from but timesheets they don't fill
  in. On a project counted by Attendance on Site, a submitted attendance at
  the site (a check-in inside it, or the shift that names it) becomes a
  submitted timesheet on the project, at the Activity for Days on Site, and
  cancelling the attendance cancels it (`site_time.py`). The villa's crew,
  Tarek and Omar on 1 and 2 October, shows as 35 h and 1,575 of labour cost.
- Legal: the Privacy Policy says a day at a project's site becomes time on
  that project, the day and its hours only (`oneproject-days-on-site`,
  revision 18).
- Time and Materials said "plus what's bought for it", but Invoice Time billed
  only hours. It now offers Bill Costs: supplier bills' lines, stock issued
  and approved expense claims on the job's Time and Materials projects, at
  cost plus the project's Markup on Costs, each line naming the cost it bills
  (`one_rebills`), so nothing is billed twice (`billing.costs`). Villa
  Windows' aluminium frames, 30,000 at 10%, bill as 33,000 beside its 9 hours.
- Submitting a timesheet completed every task it timed: Log Time and the
  timer both ticked the row's Completed, which ERPNext reads as "the task is
  done". They no longer do, so a timed task goes to Working.
- Nobody heard when a task ran past its hours. **Hours Over Plan** tells
  whoever has it and the project's manager, once, as its logged hours pass
  its planned hours (`tell.over_plan`).
- Bill Progress took one share for the whole order, so work measured line by
  line against a bill of quantities couldn't be billed. **By Line** gives each
  order line its own share done, in frappe's table in the same dialog
  (`progress.bill_progress` `lines`, `overall`). Showroom Lighting's contract
  billed at 50% of the lights and 30% of the cabling comes to 13,500, Work
  Done 34.62%.

**Money** (the project page's Money view, and buying on Suppliers).

- Cost Types listed only the project's own budgets (the villa: 100,000, 32,000
  spent) while the Overview's Budget, which opens it, added up the tree with
  Other. Money now shows the tree and Other too (`budget.types`), and a cost
  type only a sub-project budgets for adds the project's own.
- The forecast took the larger of the whole budget and spent plus on order,
  so one cost type over its budget hid behind another under. It's now worked
  out per cost type, then the rest (`money.forecast`): the villa's Cost of
  Goods Sold was 10,000 over, so the forecast cost was 150,500, not 142,785.
- A Fixed Price project with no budget forecast the whole contract as margin
  (Showroom Lighting, 39,000, 100%). With no budget there's no forecast: "–",
  No budget.
- Contract was hours at their rates when nothing was ordered, wrong for a
  retainer (Halcyon Support showed 26,400) and for time and materials, which
  rebills costs too. The forecast is now by kind: time and materials shows
  Earned (invoiced and not invoiced yet, time and costs with markup), Cost
  and Margin So Far, under So Far, with Ordered and Forecast Margin when
  there's an order; a retainer shows its Monthly Fee, Invoiced, Cost and
  Margin So Far. Villa Windows: Earned 35,560, Cost 31,210, 12% margin.
- Paid counted only payments carrying the project, so a payment matched to
  invoices later, or covering several, was missed or misplaced. Paid is now
  read from the project's invoices and bills, whatever paid them, in the
  project's share of each, with order advances not yet set off and payments
  on account naming the project (`_paid_on`). A payment with no project
  takes the one its invoices and orders all name (`chain.paid_for`).
- Journal entries charged to the project (payroll, depreciation, accruals)
  weren't counted. Journal Entries is a cost row, read from the ledger's
  expense accounts, and counts in spent and the forecast.
- Rows at nothing (Delivered, Received on a services job) are no longer
  shown.
- Buying had nowhere on the page: Suppliers now lists the tree's material
  requests, requests for quotation, supplier quotations and receipts
  (`buying.papers`), with New Material Request and Request Prices. The page's
  menu has Issue Stock and New Expense Claim. A new sales order, delivery
  note or invoice for a customer with one open project names it
  (`chain.customer_project`).
- Checked end to end, quotation to payment and material request to payment:
  every document and its ledger entries carry the project.

**Invoices** (the project page's Invoices view).

- A row was a number. Each now says what it's for, from the invoice itself
  (`billing.for_what`: Work done 50%, hours of time and costs, a retainer's
  month, Credit note, its first item) and which sub-project it's on: the
  villa's 60,000 is Fit-out Works on Handrails.
- The villa's 3,000 outstanding is retention, and Due said 30-09-2027 as if
  the invoice were due then. Outstanding is now what's owed now, Retention
  Held its own figure, and a row owing only retention says so under Due.
- An invoice partly another project's counted whole here and its share in
  Money. Both count the project's share now; this view with tax, as paid.
- Work and Billing's Owed took invoiced before tax from paid with tax, so a
  fully paid 5% VAT invoice showed a false advance. Owed and the advance now
  come from the invoices (`money.owed_share`, `_paid_on`).
- Nothing could be done from the list. **Record Payment** is OneBook's own
  verb, offered through the record head (`head.offer`); **Send** opens the
  invoice with frappe's Email, its print attached (`emailRecord`).
- An overdue invoice reached Needs You only once the project was Completed.
  **Chase** the customer now shows it with how late. The past-due amount is
  worked out from what's owed, earliest term first (`view.past_due`):
  ERPNext's per-term outstanding moves only when a payment names the term, so
  the villa's paid invoice read as 57,000 overdue and supplier bills as more
  than owed. The Pergola's 7,500, 17 days late, is the one shown.
- An advance on the order shows under Paid. A project with no invoices shows
  only "No invoices". Payments redraw the view, not only invoices.

**Suppliers** (the project page's Suppliers view).

- Every purchase order was a subcontract card with Bill Progress, the villa's
  1,960 of handrail brackets among them. An order with a Lump Sum line or for
  anything not kept in stock is a subcontract (`money.subcontract`); goods
  are on Buying, with how much is received and billed, amber when billed
  ahead of delivery.
- A card didn't say what it was for: the two Gulf Office Supplies orders
  read alike. It says Glazing Package, and Aluminium Frames · Villa Windows.
- What was owed wasn't on the card, nor that Al Noor's 30,000 was two days
  late. **To Pay** shows, red with how late, or when it's due
  (`money.past_due`, `next_due`). The line above adds To Pay and Overdue
  (50,800).
- Supplier bills were nowhere on the page. **Bills** lists them as Invoices
  lists the customer's (`billing.bills`, sharing `_listed`), with Record
  Payment. Lateness is read from the due dates, as ERPNext marks Overdue only
  overnight.
- Nothing could be paid from here. **Pay Advance** opens ERPNext's payment
  against the order (`project.pay_advance`).

**Contacts** (the project page's Team view, and Add Supplier on Suppliers).

- A project had no place for anyone outside the company: the architect, the
  consultants, the client's representative, a subcontractor not yet ordered
  from. Project Contact rows (Role, Supplier or Company, Contact, Note) are
  listed under **Contacts** on Team, with **Add Contact** (`contacts.py`).
- A supplier could only reach the project with a purchase order. **Add
  Supplier** adds one as a contact, shown under **No Order Yet** until
  there's an order.
- The Contact lists the project among its links, as frappe links contacts
  to customers and suppliers. Email and phone are read from the Contact,
  the mobile when there's no phone.
- OneAI reads the contacts in `project_facts`.
- Left for later: giving a consultant the portal.
- Team listed six people on the villa but only Wren could be removed, and
  the head showed one avatar: both read the project's Users table, where
  only Wren was. The head and About now show everyone Team lists (`view.py`
  "people"), five avatars and "+1", opening Team. A row that isn't a member
  offers Make Member, when the person is a user.

**Activity** (the project page's Activity view).

- It was frappe's timeline of the Project record only. The villa had 298
  rows, 293 of them single "attached" lines for featured photos, and none of
  its orders, invoices or payments. Project kept no changes either, as
  ERPNext turns tracking off.
- `activity.py` adds the tree's documents (made, submitted, cancelled, from
  their Versions), tasks added (a day's as one row) and completed, updates,
  hours per person per day, files per person per day, and sub-projects
  started. Project now tracks changes (a property setter), and frappe's
  timeline gives its comments, emails and field changes. Both render in
  frappe's ActivityTimeline, our rows through its `item-{type}` slots.
- All, Money, Work and Comments filter it. The comment box moved to the foot,
  as frappe has it.

**The sidebar** (OneProject as a whole).

- Five links in a 220px panel beside every OneProject page, one of them
  doubled in the list's menu, and on a project's page it narrowed the hero.
  Removed then, as OneMail and OneCloud have none: Projects, Workload and
  Time were frappe's TabButtons in the page head, and the pages set
  frappe's `hide_sidebar`.
- **Changed back on your word** (The panel, above). The panel lists the four
  places and is open on each of them. A project's page and a template's page
  close it. On a phone the place's name in the breadcrumb, **Projects ▾**,
  is a menu of the four (`project_places.js`). On a project's or a
  template's page, **Projects ▾** or **Templates ▾** before its name is that
  menu at any width. The head tabs are gone. Before,
  the template page kept the panel while the project page closed it, which
  is why it came and went.
- Found on the way, and fixed for every module:
  - The panel marked no row on Projects. The row leads to
    `/project/view/list` and the list opens at `/project`, so frappe never
    matched them. Now every view of a list marks its row (`shell.js`).
  - Back on a list after a record, its name read "Project", not "Projects".
    The rename reached only the last page's head (`shell.js`).
  - The board had no name at the top. It now has its place's name.
  - The browser checks now say whether the panel is open (`panel`) and what
    a phone's breadcrumb lists (`phone`), in `tests/browser/screens.mjs`.
- Left for the Time screen: Time's list is called "Timesheet", and opened by
  its address it shows OneHR's panel, since OneHR lists timesheets too.
- Project Templates and Rates moved to the Projects list's ··· menu.
- A project's name in its breadcrumb opens the others: parent and
  sub-projects, then open projects (`view.picker`), through frappe's
  breadcrumb `menu_items`.
- Workload failed for a task with an empty assignment (`_assign` of ""),
  and so did OneTask's daily reminder. Both read it as none.
- With the sidebar gone, a project's views are frappe-ui's vertical Tabs in
  a column on the left on a desktop (`ProjectPage.vue`, `Page wide`), and a
  row of tabs on a phone. Both stick under desk's page head at a z-index
  under its 6; the tab bar had been `z-10`, over it.

**Overview** (the project page's first view).

- It read as one column of text: four figures without edges, then section
  after section of rows. The figures are now frappe-ui's NumberCard in
  ChartCard's bordered surface, across the full width (`Figures boxed`), and
  Needs You sits in the same card (`Section boxed`). The rest stays on the
  page.
- Under the figures, two charts for every kind: **Tasks**, frappe-ui's
  DonutChart of the tasks by status in their badges' colours, and **Hours by
  Week**, the BarChart that only Time and Materials and Retainer had. A task
  past its due date counts as Overdue, as the Overdue Tasks figure does;
  ERPNext only marks one so overnight. The Internal kind's status bar
  (`Statuses.vue`) went, as the ring says the same.
- **Budget** is a stacked BarChart per cost type, spent, on order and left,
  in the ramp's blue at two strengths and the axis gray. A cost type over its
  budget is a row under it with how far over. The rows with thin bars went.
- The colours come from frappe-ui's tokens through `useChartTokens`, read on
  the island's own root, as its CSS variables are not on the page's. The
  ring draws its largest slice first, so the colours follow the same order.
- The demo projects' photos were re-uploaded (`media_seed.py`) after the
  file store lost them.
- Rules ran under the Brief, above and below the charts, and under every
  section, so cards sat between lines. A group of cards (`data-cards`) is now
  its own divide: the section before one draws no rule
  (`[&:has(+[data-cards])]:border-b-0` in `Section.vue`), and the group draws
  none. The four figures are two to a row in the main column, beside Needs
  You, not four across the page (`Figures :columns`).
- Quotations were in the main column and Orders in the right one, though
  they're one flow, and each ordered quotation showed again as its order.
  Orders now follows Work and Billing, Quotations after it, and Quotations
  lists only what isn't ordered yet (`view._quotes`).
- About's Team avatars were cropped: the row truncates, which clips what
  stands outside the line, and their ring named a colour frappe-ui's preset
  doesn't make (`ring-surface-base`), so it fell back to Tailwind's blue.
  About now draws them with the kit's People, unclipped, and People rings
  each avatar in `outline-base`, the page's own colour, so one cuts the next
  cleanly here and in the hero.
- Half the project's avatars showed initials whoever had a picture: the
  manager, updates, the Time list, Not Invoiced Yet, By Person, Who's On
  It and Team's contacts were given a name and no image. Each now carries
  the user's picture, the employee's for someone with no user
  (`view._faces`, `hours._faces`), or the Contact's own.
- Faces and logos (`one_mail/faces.py`) dressed contacts, leads, customers,
  suppliers and banks only, so everyone who works here showed initials.
  User, Employee, Company and Manufacturer are dressed now: a user or
  employee takes the photo on their other record first, then their
  Gravatar face, never a logo (their domain is our own); a photo put on one
  goes to the other. The company gets its website's logo and its drawn
  letter heads redraw. Administrator and Guest are left alone. The privacy
  clause says so (revision 19), and a patch dresses what exists.
- The Suppliers tab named each supplier with no logo, though suppliers were
  dressed. Each subcontract card now leads with the supplier's logo
  (`money._suppliers` reads `Supplier.image`), as do the Overview's
  Subcontracts rows (square, as an organisation is) and a supplier contact
  on Team with no person. The demo suppliers had no website to look a logo
  up by; they were given real firms' sites to show it.
- The Bills and Buying lists show each supplier's logo beside its name
  (`billing._listed` carries `party_image` for bills and invoices alike,
  `buying.papers` for orders, quotations and receipts). A contact who is
  not a supplier shows their own picture: their Gravatar face, else their
  company's logo by the domain of their address.
- The Invoices list names the customer with their logo, as Bills names the
  supplier, and keeps Date on wide screens only. On a tablet both lists ran
  their row menu off the edge; their first two columns are narrower now.
  The demo customers were given real firms' sites to show it.
- The customer chip in the project's head shows the customer's logo in
  place of the building icon (`view.py` sends `customer_image`), on a white
  backing over the cover photo so a see-through logo still reads.
- The Overview's Orders rows and Retention's From the Customer row lead with
  the customer's logo, as Subcontracts lead with each supplier's. To
  Suppliers takes the Suppliers tab's icon in the same square so both rows
  line up (`Rows` takes an `icon` in place of an avatar).
- A parent's page added up everything under it, with no way to see the
  project's own work alone. **Main** now leads the Overview's Sub-projects
  with the project's own value, billing and progress, and opens the page for
  that alone (`?only=1`): every tab's call takes `only`, and `tree.narrow`
  makes `tree.scope` the project itself for the rest of the request. A
  **Main ×** chip in the head goes back. Nothing moves in the data. The
  whole-job Contract card says how much was ordered as extra work, and
  OneAI's project facts carry `main`. Wrapping the original under a new
  parent automatically was weighed and left out: the original's ID, link,
  portal, team and submitted documents would all have to move.
- On a whole job the milestones were one line sorted by date, so parts read
  as one sequence and the cap of eight could hide a part entirely. They are
  now a row per part on one dated line with today across them
  (`milestones.lanes`, MilestoneLanes.vue), each row's next one named and the
  rest on hover (frappe-ui Tooltip); on a phone, a row per part. The Main
  view and a project without sub-projects keep the single line.

#### What's agreed with the customer (2026-10-07)

Asked how a project sets its payment terms, whether a contract and terms and
conditions are the same, and whether the books stay ERPNext's. Five gaps,
each closed on ERPNext's own records, each with a demo check:

- **Works (1, 2)**: moving an order's Retention Due moved only the invoice's
  schedule. Accounts Receivable ages by the Payment Ledger Entry and GL Entry
  due dates, so it kept the old date. `progress._due` moves both
  (`oneproject_a_new_retention_date_reaches_the_receivables`).
- **What ERPNext already does**: a project had no payment terms. ERPNext's
  mapper leaves `payment_terms_template` off a Sales Order's invoice, and
  `set_missing_values` dates it by the party's terms, so Bill Progress
  invoices were due on the day. The project now holds its Payment Terms and
  Terms and Conditions (`one_payment_terms`, `one_terms`), from the customer,
  the template or the company. Every quotation, order and invoice for it
  starts with them, and one made from an order keeps the order's
  (`terms.carried`, before_insert). Bill Progress dates the invoice by the
  order's terms with the retention after
  (`oneproject_its_terms_travel_from_quotation_to_invoice`).
- **Stays desk (5, 6)**: the New Project dialog's Details step asks for the
  template (moved from Plan, since it now sets the terms), Payment Terms and
  Terms and Conditions. About shows both. Add Contract asks for both.
- **Presets (13)**: each library preset names its payment terms and terms
  and conditions (`library_terms.json`, translated through `babel.py`), and
  the building presets their retention. Copying one in makes any the
  workspace lacks (`oneproject_a_project_starts_with_its_customers_and_its_templates_terms`).
- **Signed contract**: the sales order is the contract value. What the
  customer signs is ERPNext's Contract, naming the project. **Draw Up
  Contract** makes one, About says **Signed** or **Not signed yet**, and
  Needs You asks for the signature, or to renew one ending within a month.
  Contract keeps ERPNext's roles, since employment contracts are Contracts
  too. Whether it is signed is shown to the project's readers
  (`oneproject_its_signed_contract_is_on_the_page`).
- **OneCRM › Contract**: the list was there under Sales but read **Draft**
  for an unsigned contract, showed each contract's whole wording and the
  project as its ID. It now reads Unsigned, Active or Inactive, the end date
  and the project by name (`contract_list.js`, `one_crm/custom/contract.json`).
- **Knows (13)**: OneAI's project facts carry the payment terms, the terms
  and conditions and the contract. README: What's agreed with the customer,
  The signed contract, and terms.py and agreement.py under the hood.
- **Demo (1)**: the villa takes Net 30 and Construction Works from its
  template and has a signed contract. Bayview takes Net 45 from the customer
  and has a contract waiting for a signature. Acme, the showroom and Marina
  have theirs.

## OneLegal

Founded during the pass, so that each screen can add its lines as the pass
reaches it (point 8). `one_legal/README.md` is the reference.

- **Ported from OneApp's `onelegal`**:
  - the registry, the eight documents and `revision.hash` versions;
  - the two parties (the organisation, agreed by an administrator; the
    person, agreed by each person);
  - Legal Acceptance and Legal Document Version.
- **The desk's own parts**:
  - A dialog that cannot be closed asks when the desk starts. The documents
    open on the Agreements page (`/app/legal`), which is never behind the
    dialog.
  - Only a Workspace Administrator agrees for the organisation. A person
    whose workspace has not agreed yet is told so, rather than shown a button
    that would refuse them.
- **The text is OneDesk's, not OneApp's**:
  - Intake acts without being asked each time, and the AI Addendum says so.
  - The lifecycle's periods are read from `one_admin/ladder.py`.
  - Nothing is promised that is not built.
- **Every company One calls is declared**, and `tests/guards/test_legal.py` fails on a
  new outside host that is not:
  - Cloudflare (R2, AI Gateway and Workers AI, sending mail);
  - Google (Gemini, and the favicon lookup);
  - Automattic (Gravatar, by a hash of the address);
  - Stripe;
  - Frappe (Frappe Cloud).
  - Gravatar and the favicon lookup were in no document before.
- **Not yet built**, for the screens they belong to:
  - an Agreements section in Settings showing what you and the workspace
    agreed to, and when;
  - asking at sign-up, before the workspace exists;
  - `gate.require()` on turning an application on.
