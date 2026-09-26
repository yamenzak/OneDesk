# The shell, and a desk the workspace can customize

Two questions, answered together because the second decides the first:

1. **One shell.** Every page of ours should look like one product, and like
   the desk it sits in.
2. **Customizable like the desk.** A workspace, or OneAI acting for it,
   should be able to change a page the way frappe lets a System Manager change
   a form: add a field, move one, change what the header says. That makes our
   code mostly a renderer of records, and lets us ship less of it.

The answer in one paragraph: **keep the desk form and list as they are**,
because they are already customizable from the database, and put our own
changes to them into records a renderer reads rather than 39 form scripts.
Our nine pages get **one shell** on `frappe.ui.Page`, taken out of Settings,
which already behaves like a desk form. The two genuinely bespoke products,
OneMail and OneCloud, keep their insides and take the shell's head, panes and
parts. A workspace customizes through a **held layer**: frappe's own Custom
Field and Property Setter, frappe's own DocType Links and Actions, and one
doctype of ours, **Record Head**, for the part above the fields. Nothing a
workspace writes is code.

## What there is today

Measured, not remembered.

**Pages: nine, and nine layouts.** Every one calls
`frappe.ui.make_app_page({single_column: true})` and then appends HTML it
built itself. None shares a layout with another.

| Page | Drawn by | Lines | CSS | Saves |
|---|---|---|---|---|
| Settings, Workspace Settings | `public/js/settings.js` | 1168 | `settings.css` (`.os-*`, 450) | FieldGroup from meta, Save in the head, dirty snapshot, `modified`, `doc_subscribe` |
| OneMail | `public/js/onemail.js` | 1044 | `onemail.css` (`.om-*`, 739) | actions |
| OneCloud | `public/js/onecloud.js` | 2149 | `onecloud.css` (`.oc-*`, 904) | actions |
| OneCalendar | its page folder | 370 | its own (`.one-calendar-*`) | dialogs |
| Intake, Ready to Submit | page folders, `public/js/intake.js` | 280 + 384 | `intake.css` (`.oi-*`, 490) | actions |
| My Tasks | its page folder | 167 | its own (`.one-tasks-*`) | inline insert |
| Legal | its page folder | 45 | `legal.css` (`.ol-*`) | read-only |

Empty states are written five times (`.os-empty`, `.oi-empty`, `.om-none`…),
rows four times, and OneMail and OneCloud each size themselves to the window
with their own `fit()`. The only thing every page shares is `theme.css`, the
palette. **Settings is the one page that already behaves like a desk form**,
and its `form()` is the nearest thing to a shell.

**Forms: 39 scripts on 43 doctypes, six patterns.** They change the desk form in six
recurring ways, and the content of each is computed per doctype, usually from
one whitelisted "overview" method:

| Pattern | How | Files |
|---|---|---|
| A. The status pill | `frm.page.set_indicator` | the operator records, Employee |
| B. A band of numbers under the title | `onedesk.band.show` → `dashboard.set_headline` | Employee, Lead, Opportunity, Project, Invoice, Item, Asset |
| C. A sentence under the title | `decision.headline` → `set_headline_alert` | twelve HR records |
| D. Buttons and sidebar actions | `add_custom_button`, `sidebar.add_user_action` | about twenty |
| E. Tabs on every form | patching `Layout.get_doctype_fields` | Files, Mail, Activity |
| F. Field wiring | `set_query`, `toggle_display`, defaults | a handful |

**Already data:** 177 Custom Fields and 287 Property Setters as fixture JSON,
eleven Sidebars, six Workspaces, the Dock, nineteen Number Cards. A tenant
customizes none of it today: Client Script, Customize Form and DocType Layout
appear nowhere in the app, and no OneAI tool writes schema or layout.

## What frappe already gives

Read in `apps/frappe` at develop, not assumed.

- **Customize Form** writes Property Setters (labels, order via `field_order`,
  hidden, read-only, `depends_on`, `in_list_view`, `title_field`,
  `image_field`, `default_view`…) and Custom Fields (any fieldtype, sections
  and tabs included, placed with `insert_after`). System Manager only.
- **DocType Links** ("Connections") and **DocType Actions** are child tables
  of DocType, editable in Customize Form. An Action is a button that either
  routes or calls a whitelisted method with the record (`execute_action`), so
  buttons are already data.
- **Client Script**: JS per doctype, form or list, run with `new Function`
  after the app's own scripts. System Manager only. It is code in every
  reader's browser.
- **DocType Layout**: a second arrangement of a form's fields, chosen by URL
  or by a JS condition. Presentation only (its `reqd` is not enforced on
  save), it cannot add fields, and **a form opened in a layout skips the
  doctype's Client Scripts**. Not a foundation.
- **The form head**: `page.set_title` and `set_indicator`, `dashboard`
  (headline, progress, indicators, sections, Connections), `add_custom_button`
  and groups, the sidebar's user actions. Everything patterns A–D need.
- **`fetch_from`** copies a linked record's field onto this one; **virtual
  fields** compute one with a Python expression. Neither edits the other
  record, and there is no built-in way to.
- **Workspace, Custom Sidebar, List View Settings, List Filter layouts,
  Number Card, Kanban, Form Tour, Document Template** are all per-site data
  already.
- **`@framework/ui`** (`apps/frappe/ui`) ships `FormLayout`, fields, lists and
  the island host in Vue. The desk form does not use it; it mounts only in
  "Frappe UI" pages and chart widgets.

## Decisions

### 1. The desk form and list stay the renderer for records

They are frappe's, maintained by the people who own the schema, and every
customization frappe has already works on them. A record page of ours would
have to reimplement all of it, which is what OneApp's 22,000-line screen
engine did and what its own audit (OneApp `docs/DESK.md`) said to delete.

What we change on a form stops being a script per doctype and becomes rows a
renderer reads (decision 4). What is genuinely a program (the interview
recorder, a timer, OneCloud inside the Files tab) stays code, registered by
name.

### 2. Our pages get one shell, on `frappe.ui.Page`

`onedesk.shell` (one JS file, one CSS file with `.one-shell-*`), taken out of
`settings.js` rather than written new. It has exactly these parts, and a page
composes them rather than drawing its own:

- **Head**: frappe's page head, nothing else. Title and breadcrumbs set one
  way; the indicator; Save as the primary action with Ctrl+S; secondary and
  inner buttons; the menu.
- **Three bodies**, and only three: **column** (the desk form's width, for a
  record or a settings section), **wide** (a table's width), and **panes**
  (the mail and files layout, fitted to the window once, for everybody).
- **Section**: heading, note, and what is under it, divided by a rule, never
  boxed.
- **Row**: title, a quiet line, badges, a chevron; frappe-ui's list-row hover.
  Replaces `.os-row`, `.om-row`, `.oi-row` and the rest.
- **Empty, quiet, loading**: one of each.
- **Editor**: Settings' save core, lifted out: a FieldGroup from meta, dirty
  against what loaded, a warning before leaving, saving against `modified`,
  `doc_subscribe` and the conflict message. Any page that edits a record uses
  it.

Every part is built by point 9: a frappe-ui component's look, the desk's own
part, then frappe's utilities. **Not Vue islands.** An island would draw with
frappe-ui's components beside a desk drawn with espresso, which is two looks
on one screen, and the desk form itself is not an island yet. When frappe
moves the form onto `@framework/ui`, the shell moves with it; until then it
matches what the reader sees on every other screen.

A guard (`tests/test_shell.py`) fails when a page draws its own head, its own
empty state or row, sizes itself to the window, or ships CSS for a part the
shell has.

### 3. OneMail and OneCloud keep their insides

They are products, not screens: a three-pane mail client and a file
explorer. They take the shell's head, the panes body, its rows, empty states
and buttons, and keep their own reading pane, tree, grid and upload tray.
That is the difference between "bespoke" and "a different app".

### 4. Record Head: the part above the fields, as data

One doctype of ours, **Record Head**, one per doctype, holding what patterns
A–D do in code today:

| Rows | What it declares | Replaces |
|---|---|---|
| Indicator | a condition (frappe filters) → label and colour | `set_indicator` in scripts |
| Sentence | a condition → a sentence naming only `{{ doc.field }}`, or what a measure says | `decision.headline`, `set_headline` |
| Band | label, value, where it links, tone | `onedesk.band.show` and each "overview" method |
| Block | a named block from a registry (the employee's attendance heat map) | the few drawn by hand |

A band value is one of: a field of the record; a field of a record it links
to; a count or sum of another doctype with filters naming the record; or a
**measure**, a Python function a module registers by name
(`one_measures` hook). The arithmetic stays Python and tested; where it goes
on the page is data. A workspace can place a measure, never write one.

**Buttons are verb rows**, each naming a verb a module registered
(`one_verbs`), so a row cannot call an arbitrary whitelisted method. The plan
was frappe's own DocType Actions; as built, they could not carry it. A DocType
Action shows on every saved record whatever its state, and calls its method
with the record and nothing else, while every button we have shows only when
it can be done (Take Back only while somebody holds the asset) and most ask
something first (whom to give it to; how much was paid, and into which
account). A verb says both, in Python, and the row only places it. DocType
Actions stay what they are for a plain route.

**Connections are frappe's own DocType Links.**

**The server works it out.** A `doc_events["*"]["onload"]` hook evaluates
the record's head as the reader, with their permissions, and hands it over in
`__onload`; one `frappe.ui.form.on("*")` renderer draws it. A number the
reader could not see in its own list is never in the band.

Our 39 form scripts become Record Head fixtures in the module that owns them, and
the scripts are deleted as each is ported.

### 5. Fields from another doctype, edited in place

The request "put the employee's mobile number on this form" means a field of
a different record. Frappe's `fetch_from` copies it, which gives two values
that drift apart, and it cannot be edited.

**A Linked Section**, declared on the Record Head: a Link field of this record,
and fields of the record it points at. It draws as a section of the form,
with frappe's controls, and is saved like this:

- **One save, one transaction.** The form sends the linked record's changes,
  and the `modified` it loaded, with its own document (`__one_linked`; frappe
  keeps extra keys on the document it saves). A `doc_events["*"]["on_update"]`
  saves the linked record in the same request. If either fails, both roll
  back, so there is never half a save.
- **Clashes are frappe's.** The linked record is saved against the `modified`
  it loaded, so a change made elsewhere is refused with the linked record
  named, and nothing is overwritten. Its `doc_update` is subscribed too, so
  the form says so before Save is pressed.
- **Permissions are the linked record's.** Its fields are read-only for a
  reader who may not write it, and hidden for one who may not read it. A
  submitted record's fields are read-only unless `allow_on_submit`.
- **What it does not do**: child tables of the other record, a record that
  links back to this one, or more than one level of links. Those are a
  Connection, not a section.

This is the only new save path, and the most expensive part of the plan.

### 6. The workspace layer: held, never code

A workspace administrator customizes with frappe's own records: Custom
Field, Property Setter, DocType Link, DocType Action, and Record Head. They
are the **workspace layer** (`tests/test_declarative.py`'s `LAYERS`): no file
behind them, written for the tenant, exportable, and removed with **Reset**
per doctype.

Frappe trusts whoever writes these, because only its System Managers can. A
workspace administrator is not that, so a row they save is **held**, as a
workspace notification rule already is (`one/rules.py`):

- **Nothing that runs.** No Client Script, no Server Script, no virtual field
  (its options are Python), no Custom HTML Block script. A `depends_on` must
  be a field name or a comparison of fields and values, parsed by a grammar
  rather than evaluated. The desk runs `eval:` strings as JavaScript, and a
  row anybody can write that runs in every reader's browser turns "may
  customize a form" into "may act as whoever opens it".
- **Nothing that weakens a guard.** Frappe's own Customize Form limits hold (a
  standard field cannot lose `reqd`), plus ours: no `permlevel`, no
  `ignore_user_permissions`, no change to a field another module depends on.
- **Only doctypes they may read**, only verbs we registered, only measures we
  registered.

**Where they do it**: a **Customize** item on every form's menu, opening a
shell page (column body) on that doctype: fields and their order, the head,
connections, actions. It is a shell page, not frappe's Customize Form, which
refuses anybody who is not a System Manager.

### 7. OneAI customizes through the same door

One suggestion tool, `customize`, proposes a set of layer rows as one card:
"add Mobile to the Employee head", "show the customer's credit limit on a
quotation". Applying the card saves them as the administrator, so the same
hold refuses what it would refuse from them. OneAI never writes code, because
nobody in the workspace can.

## What it saves

- The 39 form scripts (3,329 lines) become fixtures and one renderer, which
  should be a few hundred lines. What stays as code is the registered blocks, verbs and
  measures, which are the actual logic.
- The light pages' own CSS (1,218 lines across Settings, Intake, Legal,
  OneCalendar and My Tasks) shrinks to what is really theirs, and OneMail and
  OneCloud lose their heads, rows and empty states to the shell.
- Every future customization, ours or a tenant's, is a row.

## Stages

Each deletes what it replaces in the same commit.

1. **The shell**, taken out of Settings with no visible change: head, column
   and wide, section, row, empty, editor. The guard. Done.
2. **The light pages** onto it: My Tasks, Legal, Intake, Ready to Submit,
   OneCalendar. Done.
3. **OneMail and OneCloud** take its head, panes, rows and empty states.
   Done.
4. **Record Head**: the doctype, the onload hook, the renderer, measures and
   verbs. Ported first where the pattern is plainest (Item, Asset, Invoice),
   then the rest. Item, Asset, the invoices, Customer, Supplier, Lead, Deal,
   Project and Employee are done; the HR records' sentences and the operator
   records' pills are not yet.
5. **The Linked Section** and its save. Done.
6. **The workspace layer**: the holds on Custom Field, Property Setter, DocType
   Link and Action, and Record Head; the Customize page; Reset. Done.
7. **OneAI's `customize`.** Done.
8. **Record tabs** (Files, Mail, Activity) declared as registered blocks
   instead of patching the layout. Done.

Stages 1–3 stand alone and are what the passover needs next. 4–8 can follow
product by product.

## Stage 1, as built

- `public/js/shell.js` and `public/css/shell.css`, loaded on every desk page.
  `onedesk.shell` has `page`, `body` (column, or `wide`), `name` (breadcrumb,
  tab title, and OneAI told where the reader is), `button`, `section`, `row`,
  `actions`, `empty` and `quiet`. `onedesk.shell.Editor` is Settings' save
  core: `form()` with its row layout, dirty against a snapshot, the warning on
  leaving, `doc_subscribe` and the conflict alert, and saving from the page
  head with Ctrl+S. A page extending it says only `saver`, `redraw` and
  `refresh`.
- Settings extends the Editor and lost 190 lines. Its stylesheet keeps only
  what is its own (the profile's photo, People's grid, the notification
  preview); the rest moved to the shell under `.one-shell-*` names.
- Verified by screenshots of eleven sections before and after, compared pixel
  for pixel: ten identical, and the eleventh showed the one class the server
  writes (`settings.py`, a notification kind's quiet line), which was renamed
  too. Dirty, undo back to clean, a save elsewhere raising the conflict,
  Refresh, and Ctrl+S were each tried in the browser.
- `tests/test_shell.py`: every page is on the shell or named with the stage
  that moves it; a page on the shell is made by `onedesk.shell.page`; only
  `shell.css` styles the shell's parts; a page on the shell styles no row,
  empty state, quiet line, card or section of its own, and writes no
  `beforeunload`, `doc_subscribe` or timestamp check; the old names are gone.

## Stage 2, as built

- **The shell grew what the five pages needed, and nothing more:**
  - `panes`: side by side, divided by a rule, never boxed, fitted to the
    window by `fit()`, the one place a page is sized to it. Intake and
    OneCalendar are its first two; OneMail and OneCloud are stage 3.
    `pane_head` is a pane's own head on a rule.
  - `row` gained `lead` (a tick), `meta` (a date or a count on the right),
    `active` and `unread` (as a mailbox marks them) and `attrs`. `list` holds
    rows, at a section's text size wherever it sits.
  - `section` takes an `aside` beside its heading, for a count.
  - `empty` is frappe's own `frappe.ui.empty_state`, sized for a section.
- **My Tasks**: the column, a section per due group with its count, and each
  task a shell row: its tick as the lead, the priority beside the title, the
  project and the day on the right, the timer as its action.
- **Legal**: the document in the shell's column; the name through
  `shell.name`.
- **Ready to Submit**: the wide body, a Ready section and a Needs a Look First
  section, each counted; frappe's empty state when nothing is ready.
- **Intake**: panes, the list with frappe's `TabButtons` for Waiting and Done
  (the count a badge) in its head, each document a shell row, and the one
  open beside it. It was a bordered box; it is not now. The Intake panel
  that also appears in OneCloud, OneMail and on records lost its own chips
  (frappe's badges now) and quiet lines (the shell's).
- **OneCalendar**: panes, the layers in one, the week in the other with its
  toolbar as the pane's head. `shell.name` takes a `route`, so a record's
  calendar still leads back to the record.
- About 280 lines of page CSS went, with every row, empty state, box and
  window size the five pages drew for themselves. Settings, compared again
  against stage 1's screenshots, is pixel for pixel the same.
- Found: switching Intake from Done back to Waiting kept the last document
  marked as open with nothing beside it. Opening a box now forgets it.
- The guard now holds all seven pages, and refuses a page stylesheet that
  sizes itself to the window or a page script that draws its own empty
  state.

## Stage 3, as built

- **OneMail** is the shell's page (`hide_sidebar`, since its mailboxes are
  its navigation) and three of the shell's panes: the mailboxes, the list
  with its search or its picked bar as the pane's head, and the reading
  pane. Each conversation is a shell row: the face, or its tick on hover, as
  the lead; the sender and the date on one line, the subject and the snippet
  under it, the star as its action; `active`, `unread` and the new `picked`
  for the one open, the ones unread and the ones ticked. Its own window
  sizing, resize listener, row, empty and gutter-dot rules went (about 150
  lines of CSS). A record's Mail tab draws the same rows, as links (the new
  `href`), and frappe's empty state.
- **OneCloud** keeps its bars, tree, grid, preview and upload tray, and sits
  on the shell's panes inside its own window (`fit: false`, so they fill it
  under its bars). The preview pane is hidden by its `hidden`, and the tree
  by it in a record's room, so the rules close up on their own. On its page
  the window is fitted by the shell's `fit()`; in a record's tab and in the
  upload picker its height stays its stylesheet's. An empty folder and an
  empty preview are frappe's empty state.
- **The shell grew:** `page` takes `hide_sidebar`; panes are flex, with
  `fit: false` for panes inside something that sizes itself; `fit()` runs to
  the bottom of the window, and the shell drops its bottom padding under
  panes, so a click no longer scrolls the page; a pane list's rows sit their
  meta and actions by their first line; an empty state that is all of a pane
  sits in its middle; `row` takes `href` and `picked`.
- Checked in the browser: open, Ctrl-click to pick with the picked bar,
  clear, star and unstar; the narrow mail layout; OneCloud's page, the
  preview toggle, a record's Files tab and the upload picker, each against
  screenshots from before. Settings, compared again, is pixel for pixel the
  same; Intake and the other stage 2 pages were looked at.
- The guard holds all nine pages and nothing is left in `NOT_YET`. It now
  refuses `height: calc(100vh …)` in a page's stylesheet, a page sized to the
  window, rather than any `vh`: a popup's `max-height` and a tab's capped
  `clamp()` are not that.

## Stage 4, as built

- **Record Head** (module One) is one record per doctype with four tables:
  Indicators (a condition, a label, a colour), Sentences (a condition and a
  sentence naming only `{{ doc.field }}`), Band (a label and a value, from a
  field, a linked record's field, a count or a sum, or a measure; a
  condition, a link, a tone, and whether an empty one hides), and Verbs. It
  has no desk permissions yet; stage 6 gives the workspace its door.
- **`one/head.py`** works a head out as the reader in every record's
  `onload` and sends it in `__onload.one_head`. A condition is frappe's
  filters (`evaluate_filters`); a template is read by a regular expression
  that knows only `{{ doc.field }}`, so nothing in a row is evaluated. A
  count or a sum is `frappe.get_list`, so it is the reader's own list's
  number. `validate` refuses a row naming a field the record lacks, a
  measure or verb nobody registered, or a verb for another doctype. `run`
  does a verb after checking again that the record's head offers it and that
  it can still be done.
- **Modules declare**: `one_record_heads`, `one_measures` and `one_verbs` in
  hooks, each a list of paths to a module's `HEADS`, `MEASURES` and `VERBS`.
  `install` writes the heads on every migrate and removes one a module no
  longer declares. The measures are thin: `one_inventory/heads.py` and
  `one_book/heads.py` read the same `said` and `paid` code the scripts
  called, once per request (`request_cache`).
- **`public/js/head.js`** draws any head: the indicator, the sentence as a
  form message, the band through the band's existing markup, and each verb as
  a button that asks in frappe's own Dialog. A primary verb is the one dark
  button, which is the Record Payment fix made general. It touches only what
  it drew, and nothing on a form without a head.
- **Ported**: Item, Asset, Sales Invoice and Purchase Invoice. `item.js`,
  `asset.js` and `invoice.js` are deleted (206 lines) and replaced by two
  declarations. Eight records, stock and fixed-asset items, a depreciating
  asset held and not, an invoice late and one repeating, and a draft bill,
  are pixel for pixel what they were. Give To, Hand To, Take Back and Record
  Payment's dialog were each tried; a verb asked for on a record that does not
  offer it is refused. An indicator and a sentence, added for a moment to
  the Asset head, drew beside and under the title.
- Found on the way: a record's Activity tab vanished whenever frappe
  refreshed the tabs a second time, because it hid the one section the tab
  had and frappe shows only a tab with a visible section. Drawing the band in
  the same refresh made it happen on every asset. The section now stays,
  with no room taken (`desk.css`), and the tab stays.
- **Since**: Lead and Deal, Project and Employee, each pixel-identical to
  the script it replaced. They needed three things a head had not done: a
  pill a measure says (where a person is today), a measure that answers
  several numbers (one per leave type), and a heat map as a chart kind (a
  quarter of named days). A time since is sent as the moment and said by the
  desk (`when`, and `short` for the clock's "5 d"). What each page's script
  still does is not its head: Log a Call, a project's Board and Schedule, a
  person's sidebar actions and Reset Passkey.
- **Then the HR records**: fourteen sentences and eight Approve and Reject
  verbs, `decision.js` and eleven scripts deleted. A sentence row may name a
  measure that says the sentence (`{text, colour}`), because every one of
  these is arithmetic and a choice between wordings, never one template. A
  head may name the fields it redraws on (`redraw_on`): a change to one, or
  to a row of a table among them, asks `head.preview` for the head of the
  record as it stands in the form, saved or not, so a leave encashment says
  what it pays before it is saved. Twenty-five records are pixel for pixel
  what they were, but for three changes on purpose: a submitted overtime slip
  no longer says "Submitting this pays"; Expense Claim's Approve and Reject,
  which called `decision.ask` with the wrong arguments and so did nothing,
  work; and a clock attempt's Accept is the primary verb in the toolbar
  rather than in Save's place, with no Save on a record nothing can edit.
- **Then the operator's records and OneAI's**: Tenant, Provisioning Job,
  Account Request, Tenant Domain, Offering and AI Model (`one_admin/heads.py`),
  AI Proposal and AI Action Setting (`one_ai/heads.py`), and the workspace's
  own Workspace Account (`one/heads.py`). `job.js`, `tenant_domain.js` and
  `ai_proposal.js` are deleted; the rest keep what is not a head (a tenant's
  credit actions and storage sentence, a model's Price a Call and an action's
  Try It, which answer inside their own dialog, and a workspace's domain and
  credit dialogs). The text on each is what it was. Frappe's progress bars
  (`add_progress`) became metric cards with a meter, like every other band,
  and a value that was a whole sentence is now a label and a short value
  ("Step 2 of 4" over "Asking Frappe Cloud to delete the site"). A verb may
  name a group (`group`), which puts it under a toolbar dropdown as frappe
  groups a button: a tenant's Measure Storage and Refresh Domains. A record's
  sentence now goes above its band, the news before the numbers.
- **Every head is ported.** No form script draws a pill, a headline, a band
  or a progress bar on a doctype with a head, and `tests/test_head.py` refuses
  one that does.

## Stage 5, as built

- **A Linked Section** is a row on the Record Head (`Record Head Linked`): a
  heading, the record's Link field it goes through, the linked record's
  fields one to a line, and a field of this record whose tab it ends. Record
  Head's validate refuses a link that is not one, a field the linked record
  lacks, and one a person does not type: a table or layout field, a fetched,
  computed or read-only one, or one above permission level nought.
- **The form draws it with frappe's controls.** The boot carries each
  doctype's sections for this person, leaving out any through a doctype they
  may not read; `head.js` puts them into the layout where frappe builds it
  (`Layout.get_doctype_fields`), each field named `one_linked__link__field`,
  which no field of a record is. `onload` sends the linked record's values,
  the `modified` they were read at, and which fields the reader may not
  change: all of them without write permission or on a cancelled record, and
  on a submitted one those not allowed on submit. The section shows only
  while the record links where it did when it loaded.
- **One save, one transaction.** Each change sets `__one_linked` on the
  record: the linked record, the `modified` it was loaded at, and the values
  that differ. Frappe runs no client validate on Update, so it is kept as
  each field changes rather than gathered at the end. `linked.save`, on
  `on_update` and `on_update_after_submit`, saves the linked record in the
  same request after checking its write permission, that the record still
  links to it, that only the section's fields are sent, and that its
  `modified` is the one loaded; any refusal rolls back the record's own save
  with it.
- **Clashes are frappe's.** The form subscribes to the linked record's
  `doc_update` and does what frappe does for the record itself: reloads when
  nothing is unsaved, and otherwise says who changed and offers Refresh. A
  save made anyway is refused, naming the record, and nothing is written.
- Checked on a trial section (an asset holder's mobile and personal email)
  on a submitted asset, so through Update: the employee's mobile saved with
  the asset; a stale `modified` refused, and the asset's own change rolled
  back with it; a field outside the section refused; an unsaved form warned
  when the employee changed elsewhere, and a clean one reloaded; changing the
  holder hid the section. A Stock User without Employee access gets no
  section; with HR User it is there and editable. The trial was removed.
- **No module ships one yet.** The first real sections come with the
  workspace layer (stage 6), where a workspace adds its own, and with the
  passover where a screen needs one.

## Stage 5, second pass: a record inside a record

Asked after stage 5: is the clash warning frappe's desk message or
frappe-ui's alert, and does a section hold a child table and a field kept to
some people. It was the desk's message; the other two it refused. Now:

- **Every clash warning is frappe-ui's row alert** (`onedesk.shell.changed`,
  espresso's alert drawn as `Alert.vue` draws it): a shell page's, a linked
  record's, and frappe's own for the record itself, whose
  `show_conflict_message` now draws it where it drew a bootstrap button.
- **A child table is the linked record's table in frappe's grid.** Rows are
  added, edited, moved and deleted there; the table goes whole with the save
  and is set on the linked record, rows keeping their names, so frappe
  updates, inserts and deletes as that record's own form would. The rows
  here are copies under names of their own, so the linked record's form, if
  it is open, keeps its rows. The child doctype's meta comes with the boot,
  as a form's tables come with its meta.
- **Fields above permission level nought follow the reader's levels**:
  hidden, and never sent, without read at that level; read-only without
  write; and a save that changes one anyway is refused with the field named.
- **The linked fields are the record's own**, as far as frappe is concerned:
  they are in its per-document field copy, as a custom field is, so the grid,
  `set_df_property` and frappe's refreshes find them.
- **What changed is gathered where frappe saves** (`frappe.ui.form.save`),
  which Save, Submit and Update all pass through, since Update runs no
  validate and a grid edit fires no event of ours. Submit runs no on_update,
  so `linked.save` is on on_submit too.
- **The section is laid out as the linked record's own form lays it**
  (`placing`): fields from one column of that form stay in one column, the
  next column goes beside it, and a table, or a field from another section,
  starts a section of its own with no rule above it.
- Checked with an asset holder's Mobile (put at level 1 for the trial:
  HR Manager writes it, HR User reads it), Personal Email and Education: a
  row added, a row edited and another deleted, each landing on the employee
  through Update; an HR User saw Mobile read-only and the table editable, and
  a save forged past the form to change Mobile was refused; without read at
  level 1, Mobile was not sent at all. The trial is removed at the end of
  this arc.

## Stage 6, as built

- **The Customize page** (`/app/customize/<Doctype>`, from **Customize** on
  every form's menu for a Workspace Administrator) is the shell's Editor on
  one FieldGroup of frappe grids: the form's fields in order (label, kind,
  choices, hidden, required, in the list), the head's rows (band, verbs,
  linked sections), and the form's connections and buttons. Save is in the
  page head, dirty is measured against what loaded (rows included), and a
  save made against a state another administrator changed is refused.
  Export downloads the rows; Reset takes them back.
- **What it writes is frappe's own**: a Property Setter for a label, hidden,
  required, in-the-list or the order (`field_order`), a Custom Field for a
  field of the workspace's own, the DocType's Links and Actions marked
  `custom` as frappe's Customize Form marks them, and Record Head rows marked
  `custom`, which `head.install` now keeps through every migrate. A property
  setter or custom field carries no mark frappe keeps (ours from modules have
  no module either), so the page notes each in a ledger, **Workspace
  Customization**, and Reset removes what the ledger names and nothing else.
- **The holds** (`one/layer.py`) are validate hooks on Custom Field, Property
  Setter, Client Script and Server Script. They apply to every row the page
  writes (`frappe.flags.one_workspace_layer`) and to anybody frappe does not
  let customize, so they hold for a direct API call as much as for the page:
  - A field is one a person types or picks (`KINDS`): no HTML, button, code,
    table, read-only or virtual field.
  - A property is one of `PROPERTIES`: no permission level, no ignoring user
    permissions, no changed kind or options, no field made optional that the
    record requires.
  - A condition is read by `plain`, a grammar of the record's fields, plain
    values and comparisons, and is never run: `eval:doc.status != 'Closed'`
    passes, `eval:doc.x()` and `eval:frappe.call(...)` do not.
  - Client and Server Scripts are refused outright from the page.
- **Only business forms**: not a child table, not a single, and not the
  framework's or One's own modules; only a form the administrator can read.
- **Checked before written.** Adding a field alters the table, which the
  database commits there and then, so the page checks every refusal first
  (`_check`), including the head's rows through Record Head's own validate,
  and writes only once nothing will be refused.
- **Found on the way**: nobody, System Manager or not, could add a field to
  any of the 139 forms whose Company `company.py` hides, because frappe holds
  that a hidden mandatory field has a default. The hidden Company now
  defaults to the workspace's company.
- Checked as a Workspace Administrator who is not a System Manager: renaming
  a field, hiding one, adding one after Location, a number in the band, a
  linked section with a child table, and a button, all on the Asset form
  after one save; then an HTML field, removing Location, making Item Code
  optional, hiding it, a `javascript:` button, a stale save, an unregistered
  verb, the User form, a permission-level property setter and a calling
  condition, each refused with the reason; a migrate kept the workspace's
  rows; Export downloaded them; Reset from the menu took them all back.

## Stage 7, as built

- **One tool, one card.** `customize` (`one/ai.py`) takes what to add, what
  to change about the fields the form has, numbers under the title and
  linked sections, loads the page's own state (`customize.load`), applies
  the asks to it, and checks the result with the page's `_check`, so a card
  that reaches the administrator is one that applies. A field named by its
  label is that field; a name that is not there is answered with the form's
  fields, so the model corrects itself in one step.
- **A proposal kind of its own**, `Customize`. The card says one line per
  change ("Date of Birth: called Birthday", "New field: Shirt Size (Select)")
  rather than the page's whole state, and carries the state it was made
  against. Approve is the page's own `save`, as the administrator pressing
  it, under the same holds; a card made before somebody changed the form is
  marked stale and refused. Only whoever may open the Customize page on that
  form may be proposed to or approve.
- **The page hears it.** Every save, Reset and approved card publishes
  `one_customized`, and a Customize page open on that form reloads, or, with
  changes in it, says the form was changed, as it does for a record.
- **The panel knows the page.** `where()` names the form in the page's
  route, `page()` tells the model which form it is and what the page can and
  cannot do, and the page offers three suggestions: changes to this form, a
  field, and how customizing works (`how_to`).
- **Found on the way**, both in the page and not the tool:
  - Adding a field alters the table, which commits whatever the transaction
    holds, so a ledger note written after the insert could be lost to a later
    refusal and leave a field Reset could not find. The note is written
    first now.
  - A property a module had already set (the Employee's field order, Bio's
    label) was taken over by the workspace's setter and then deleted by
    Reset. The ledger now keeps what the module's setter held, and Reset
    puts it back.
- Checked as the probe administrator, with no model call: a field that is not
  there, an HTML field, hiding a required field and the User form each came
  back as words; a card hiding Middle Name, renaming Date of Birth and adding
  a Shirt Size after Gender was approved from the panel, and the open
  Customize page showed it without a reload; a second card made before
  another save was refused as stale; Reset put the module's field order and
  label back.

## Stage 8, as built

- **Declared by the module that draws it.** A record tab is a row under
  `one_record_tabs` (one/tabs.py): a name, a label, an order, and which
  records carry it. Mail is `one_mail/linking.py`'s, with the fifteen kinds
  of record mail is about, which had been a list in JavaScript; Files is
  `one_storage/namespace.py`'s, on every record but File; Activity is One's
  own. The boot hands them to the desk in the reader's language.
- **Drawn in one place.** `record_tabs.js` is the one script that adds to a
  form's layout for them, a Tab Break and an HTML field each, and does what
  all three did alike: hides them on an unsaved record, asks frappe to
  refresh its tab strip once rather than three times, opens a tab the first
  time it is clicked, and draws the count beside its name. What is left in
  each script is what that tab does: OneCloud on the record's room, the
  record's conversations, frappe's footer moved in. Three patches of the
  layout became one, and head.js's linked sections are the only other.
- **Not yet declared by a workspace.** A tab is a module's, like a measure
  or a verb, because what it draws is code. A workspace hiding one per form
  is a Record Head row away and not built.
- Checked on a customer (Mail, Files, Activity, in that order, after
  Connections), an item (Files and Activity, no Mail), an employee (Files
  with its count of three), a new customer (none) and a new ToDo (no strip
  at all); each tab opened on click and drew as before.

## Charts in the head, as built

Asked for after stage 8: headers with charts that mean something, from the
desk's metric cards and charts or frappe-ui's.

- **What is used, and why.** frappe-ui at our version ships no charts (its
  echarts ones went); what it has is Progress, and the desk has
  `frappe.Chart`, the one Dashboard Charts and reports draw with. So a chart
  is `frappe.Chart`, a part of a whole is frappe-ui's Progress drawn in the
  band, and a change is frappe's Number Card's own pill and wording
  ("↗ 18% since last year").
- **A chart is a row.** Record Head has a Charts table; a row names a chart a
  module registers under `one_charts` (its doctypes, its label, and a
  function of the record that answers labels and values, a line saying what
  they add up to, where the title leads, and which figure the record is
  about). The Customize page places them like verbs. A measure may add
  `delta` and `meter` to what it answers.
- **One hue.** Every chart is a single series in the desk's own blue, the
  step of it that passes contrast on each theme (`--blue-500` light,
  `--blue-400` dark), checked rather than guessed. Where a chart is about
  one figure (this invoice's month, this week), that bar keeps the hue and
  the rest go grey, which is the whole of the emphasis. No legends, no
  animation; the tooltip is frappe-charts' own.
- **Where they are.** An invoice and a bill: the customer's or supplier's
  year, this one's month marked, and Paid against the total. A customer and
  a supplier, new heads: owed (against the credit limit), overdue with the
  oldest's age, this year against the same days last year, the last
  invoice, open orders, and their year. An item: a year of what left stock,
  and free against on hand. An asset: its worth over its life, and written
  off against its life. A project: hours logged a week for twelve weeks, and
  done, cost and billed each against its whole. An employee: each leave
  balance against its allocation. A deal: its probability, and its time in
  the stage against the usual.
- **Found on the way.** frappe-charts works on the arrays it is given in
  place and animates its bars up from nought, so a band drawn again from the
  same head drew noughts. The band hands it copies and turns the entry
  animation off. A date beside an amount in a right-to-left currency ran
  into it; the day goes in the label now ("Last Invoice · 10-09-2026").
- Not a chart where a number is the answer: the band's numbers stay the
  first thing read, and a chart only appears when the record has figures to
  draw.

## The risks

- **Stage 5 is a second save path.** It is small, but every save now has two
  documents in it; the tests must cover a clash on either one and a
  permission failure on the linked one.
- **The `depends_on` grammar** must accept what our own 287 setters use, or
  our fixtures fail their own hold. They are app content and not held, but the
  grammar should still read them, as a witness.
- **Frappe may ship this.** `@framework/ui`'s `FormLayout` is heading for the
  desk form. The shell is deliberately thin so that moving is a change of
  renderer, not of records: Record Head, Custom Fields and Property Setters
  mean the same whatever draws them.
