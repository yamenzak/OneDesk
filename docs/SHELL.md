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
| Sentence | a condition → a sentence naming only `{{ doc.field }}` | `decision.headline`, `set_headline` |
| Band | label, value, where it links, tone | `onedesk.band.show` and each "overview" method |
| Block | a named block from a registry (the employee's attendance heat map) | the few drawn by hand |

A band value is one of: a field of the record; a field of a record it links
to; a count or sum of another doctype with filters naming the record; or a
**measure**, a Python function a module registers by name
(`one_measures` hook). The arithmetic stays Python and tested; where it goes
on the page is data. A workspace can place a measure, never write one.

**Buttons are frappe's own DocType Actions**, not a new table. A Server Action
may name only a verb we registered (`one_verbs`), so a row cannot call an
arbitrary whitelisted method.

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
   then the rest.
5. **The Linked Section** and its save.
6. **The workspace layer**: the holds on Custom Field, Property Setter, DocType
   Link and Action, and Record Head; the Customize page; Reset.
7. **OneAI's `customize`.**
8. **Record tabs** (Files, Mail, Activity) declared as registered blocks
   instead of patching the layout.

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
