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
changes to them into records a renderer reads rather than a form script per
doctype.
Our nine pages get **one shell** on `frappe.ui.Page`, taken out of Settings,
which already behaves like a desk form. The two genuinely bespoke products,
OneMail and OneCloud, keep their insides and take the shell's head, panes and
parts. A workspace customizes through a **held layer**: frappe's own Custom
Field and Property Setter, frappe's own DocType Links and Actions, and one
doctype of ours, **Record Head**, for the part above the fields. Nothing a
workspace writes is code.

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
  and groups, the sidebar's user actions. Everything a pill, a sentence, a
  band and a button on a form need.
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
- **Record**: a record a page opens on (a person, a notification type, a
  rule) is drawn as a docview, never with a head of its own. `as_record` puts
  its name after the page's in the breadcrumb ("People / Rania Sabbagh"),
  its status in the page head's pill ("Not Saved" takes it while something
  is changed, as on a form), what can be done to it as the page head's own
  buttons, its fields in full-width parts, and frappe's form sidebar beside
  them (`side`: the photo or mark, the name, links, when). No back buttons:
  the breadcrumb goes back. A record that is not edited (an agreement's
  text) uses `onedesk.shell.record` directly; a page that only opens on
  something (a doctype's Customize, a record's Calendar) still names it with
  `trail`: "Forms / Customer", "Client Example Ltd / Calendar".
- **A form's trail**: frappe's form leads back through its list. Where the
  rail calls that list one thing, the crumb says it ("Items / A4 Paper Box",
  "Recycle Bin / …"), on the list, the tree and every record under them
  (`one/titles.py`, `Crumb`). A kind whose home is a page says the page
  instead, and the rail lights it: a department reads "Masters / Departments
  / Engineering" (`one_homes` in hooks.py, `one/homes.py`). Both are set in
  `shell.js` at load, so a record opened by its address reads the same as one
  reached by a click. `tests/test_crumbs.py`.
  `tests/guards/test_shell.py` fails on a back button in a page, on `shell.name`
  given a route, and on a page that opens on a record from its address
  without the trail. It fails too on a table made anywhere but the shell,
  a row that opens a record outside a pane, sessions drawn by hand, a modal
  of a page's own, and a `www/` page out of the portal's look.
- **Lists**: a list of records a person searches or opens (people, memories,
  notifications, rules, their tasks, where they are signed in and their
  sign-ins) is `onedesk.shell.table`, frappe's EmbeddedList, made in that
  one place: a heading and a note, search past five, a row opening its
  record, buttons beside the search, a Select narrowing it by one value
  (`choose`: Forms by app), Load More. That holds for every list
  of things: forms, extensions, mailboxes, browsers, agreements, add-ons,
  never rows under a heading per group (a group is a column). A **row**
  (`onedesk.shell.row`) is one fact and what to do about it (Password and
  Change Password, Passkey, where an extension runs), never one per record,
  never a link, and never drawn by hand; `onedesk.shell.list` of rows, and a
  row that opens something, belong only to a pane beside them (OneMail,
  OneIntake, a record's Mail). The guard (`tests/guards/test_shell.py`)
  refuses a list of rows, a row that goes anywhere, rows made one per
  record, and the row's markup written by hand.
- **Dialogs** are frappe.ui.Dialog; nothing draws a modal of its own.
- **Pages outside the desk** (`www/`: /start, /welcome, the share and
  request pages, a customer's project) are frappe's web pages in One's
  portal look (`public/css/portal.css`), without frappe's footer, and
  without styles of their own.
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

A guard (`tests/guards/test_shell.py`) fails when a page draws its own head, its own
empty state or row, sizes itself to the window, or ships CSS for a part the
shell has.

### 3. OneMail and OneCloud keep their insides

They are products, not screens: a three-pane mail client and a file
explorer. They take the shell's head, the panes body, its rows, empty states
and buttons, and keep their own reading pane, tree, grid and upload tray.
That is the difference between "bespoke" and "a different app".

### 4. Record Head: the part above the fields, as data

One doctype of ours, **Record Head** (module One), one per doctype, holding
what form scripts used to draw above the fields:

| Rows | What it declares | Replaces |
|---|---|---|
| Indicator | a condition (frappe filters) → label and colour | `set_indicator` in scripts |
| Sentence | a condition → a sentence naming only `{{ doc.field }}`, or what a measure says | `decision.headline`, `set_headline` |
| Band | label, value, where it links, tone | `onedesk.band.show` and each "overview" method |
| Chart | a chart a module registers (the employee's attendance heat map) | the few drawn by hand |
| Verb | a button, naming a registered verb | `add_custom_button` |
| Linked | a section of another record's fields (decision 5) | `fetch_from` |

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

**The server works it out.** `one/head.py` evaluates the record's head as
the reader in every record's `onload` and hands it over in
`__onload.one_head`; `public/js/head.js` draws it. A condition is frappe's
filters, and a template is read by a regular expression that knows only
`{{ doc.field }}`, so nothing in a row is evaluated. A count or sum is
`frappe.get_list`, so a number the reader could not see in its own list is
never in the band.

A module declares its heads, measures, verbs and charts in hooks.py
(`one_record_heads`, `one_measures`, `one_verbs`, `one_charts`), and every
migrate writes them, keeping rows a workspace marked `custom`. A sentence may name a
measure that says it; a head may name the fields it redraws on (`redraw_on`),
which asks `head.preview` for the unsaved record's head; a verb may name a
`group`, which puts it under a toolbar dropdown.

Every head is ported. No form script draws a pill, a headline, a band or a
progress bar on a doctype with a head, and `tests/test_head.py` refuses one
that does. What a script still does is not its head (Log a Call, a tenant's
credit dialogs).

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
- **Child tables** are the linked record's table in frappe's grid, sent
  whole with the save and set on the linked record with its rows' names, so
  frappe updates, inserts and deletes as that record's own form would.
- **Permission levels are the reader's.** A field above level nought is
  hidden and never sent without read at that level, read-only without write,
  and a save that changes it anyway is refused with the field named.
- **What it does not do**: a record that links back to this one, or more than
  one level of links. Those are a Connection, not a section.

As built: a section is a `Record Head Linked` row (a heading, the Link field,
the linked fields, and where it goes). `head.js` puts the fields into the
layout where frappe builds it, named `one_linked__link__field`, and the
changes are gathered in `frappe.ui.form.save`, which Save, Submit and Update
all pass through. `linked.save` runs on `on_update`, `on_update_after_submit`
and `on_submit`. A clash is drawn as frappe-ui's row alert
(`onedesk.shell.changed`), as frappe's own conflict message now is. This is
the only second save path. No module ships a section; a workspace adds its
own.

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
  customize a form" into "may act as whoever opens it". The one code that
  does run is what OneAI writes in OneStudio, read by a guard and a second
  model and turned on by an administrator (`one_studio/README.md`).
- **Nothing that weakens a guard.** Frappe's own Customize Form limits hold (a
  standard field cannot lose `reqd`), plus ours: no `permlevel`, no
  `ignore_user_permissions`, no change to a field another module depends on.
- **Only doctypes they may read**, only verbs we registered, only measures we
  registered.

**Where they do it**: a **Customize** item on every form's menu, opening a
shell page (column body) on that doctype: fields and their order, the head,
connections, actions. It is a shell page, not frappe's Customize Form, which
refuses anybody who is not a System Manager.

As built: the page is `/app/customize/<Doctype>` (`one/customize.py`), the
shell's Editor on frappe grids, with Export and Reset. A Property Setter or
Custom Field carries no mark frappe keeps, so each one the page writes is
noted in a ledger, **Workspace Customization**, and Reset removes what the
ledger names and puts back what a module's setter held before. The holds
(`one/layer.py`) are validate hooks on Custom Field, Property Setter, Client
Script and Server Script, so they hold for a direct API call too. A condition
is read by `plain`, a grammar, and never run. Only business forms: not a
child table, a single, or the framework's or One's own modules. Every refusal
is checked before anything is written, because adding a field alters the
table and the database commits there and then.

### 7. OneAI customizes through the same door

One suggestion tool, `customize`, proposes a set of layer rows as one card:
"add Mobile to the Employee head", "show the customer's credit limit on a
quotation". Applying the card saves them as the administrator, so the same
hold refuses what it would refuse from them. OneAI never writes code, because
nobody in the workspace can.

As built: `customize` is in `one/ai.py`. It applies the asks to the page's
own state and checks the result with the page's `_check`, so a card that
reaches the administrator is one that applies. The card is a proposal of kind
`Customize`, one line per change, and a card made before somebody else
changed the form is refused as stale. Every save, Reset and approved card
publishes `one_customized`, and an open Customize page reloads on it.

## Record tabs

Files, Mail and Activity are declared by the module that draws them, under
`one_record_tabs` in hooks.py (`one/tabs.py`): a name, a label, an order, and
which records carry it. `public/js/record_tabs.js` is the one script that adds
them to a form's layout. A tab is a module's, like a measure or a verb,
because what it draws is code.

## Charts in the head

A chart is a Record Head row naming a chart a module registers under
`one_charts`. It is drawn with `frappe.Chart`, a part of a whole with
frappe-ui's Progress, and a change with frappe's Number Card pill. Every chart
is one series in the desk's blue (`--blue-500` light, `--blue-400` dark); the
bar the record is about keeps the hue and the rest go grey. No legends, no
animation. A chart appears only when the record has figures to draw; where a
number is the answer, the band's number stays.

## The risks

- **The Linked Section is a second save path**: every save can carry two
  documents, so the tests must cover a clash on either and a permission
  failure on the linked one.
- **Frappe may ship this.** `@framework/ui`'s `FormLayout` is heading for the
  desk form. The shell is kept thin so that moving is a change of renderer,
  not of records: Record Head, Custom Fields and Property Setters mean the
  same whatever draws them.

