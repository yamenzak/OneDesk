# OneInterface

The rules as they are applied are `.claude/skills/ui/SKILL.md`, which Claude
Code loads before building any screen. This page is the contract behind them.

OneInterface is every screen of One in one frame, the way every folder in Windows Explorer
looks the same whatever is in it. OneCloud is the frame's first tenant
because it already looks like this; every list, form, report and page of
ours follows, one by one.

OneInterface is the name, and in code it is the only one: the module is
`onedesk/one_interface/`, its desk scripts and styles are
`public/js/one_interface/` and `public/css/one_interface/`, its namespace is
`onedesk.interface`, its classes are `one-interface-*`, a page's frame is
`page.interface`, and the kit's helpers are `InterfacePart` and
`interfaceModuleFoot`. `tests/guards/test_interface_frame.py` refuses the old
`window` names. The browser's own `window` is the only window left.

The rule the frame is built on: **frappe's parts, placed; never redrawn.**
A list stays frappe's ListView, a form stays frappe's Form, the sidebar stays
frappe's Sidebar, the head stays frappe's page head. What the window adds is
where they sit, three buttons, a search box, a status line and a details
pane. So socket updates, the frappe object, formatting, permissions, keyboard
shortcuts, Customize, Record Head, record tabs and anything frappe ships next
keep working, because nothing of theirs was replaced.

## The screen contract

Every screen of One is one of two kinds, so a person meets the same parts
in the same places everywhere and a change to one is a change to all.

1. **Frappe's own list or form.** The default, and nearly everything: a
   doctype's List, Report, Kanban, Calendar, Gantt, Tree or Dashboard, and its
   Form, on the window. What we need on top is a small piece inside it,
   never a page beside it: a head (`one_head`, its figures and track), a
   record tab, a client script, a column, a nav tree under the view's row in
   the nav pane (`win.tree()`), a button. Making a record is the create
   dialog; its files are OneCloud's dialog; its checkboxes are frappe's
   switch. Nothing here names a doctype (`test_the_engine_names_no_doctype`).
2. **A Vue island.** Only for a screen that is genuinely more than a list or
   a form: a product (OneMail, OneCloud, OneCalendar), a space's home, an
   editor (OneWorkbook, OneWriter), a record page that is run from all day
   (`tiers.PAGES`). It is built from frappe's Vue parts first (frappe-ui,
   `@framework/ui`), ours last, mounted by `island_page`, and declared in
   `tiers.SCREENS` with the reason it is not a list or a form.

A screen that does not pass the test for 2 is 1. Our own JavaScript pages on
`onedesk.shell` (`docs/SHELL.md` decision 2) go away: each page moves in one
commit that deletes its old code, so there is never a page in two versions,
and `tests/guards/test_shell.py` keeps the pages and the files still on the
shell, lists that only shrink; when they are empty the shell is deleted.

| Page on the shell | Becomes |
|---|---|
| Masters | gone: each module's lists at the end of its ControlCenter, frappe's list for each, the module's lists as a tree in the nav pane (docs/ONE.md, stage 5) |
| Ready to Submit | 1, moved: a script report with a checkbox column and Submit |
| Intake | 2, moved: the island `onedesk.intake`, the document open in the details pane |
| Agreements (legal) | 2, moved: a reader, the island `onedesk.legal` |
| OneCalendar | 2: a product |
| OneMail | 2, moved: the island `onedesk.onemail`, its mailboxes in the nav pane |
| OneCloud | 2, moved: the island `onedesk.onecloud`, also in a record's files and the picker |
| Settings, Workspace Settings | not sorted: `public/js/settings.js` is 3,355 lines and over twenty sections, several of them a frappe document already (User, Notification Settings, System Settings), so each section is sorted on its own |

## The parts

```
 dock │ nav pane            │ ← → ↑  Breadcrumb / Path   ● pill        ⟳  [ search ]  │ address row
      │ frappe's sidebar,   │ [ the view's commands ]          [ frappe's actions ] ▣ │ command row
      │ resizable by its    │ [ the view's controls: filters, sort, a form's tabs ]   │ view row
      │ edge, collapsible   ├──────────────────────────────────────────┬──────────────┤
      │ to its rail, with a │ the view: frappe's list, form, report,   │ details pane │
      │ view's own tree     │ page, or One's own (OneCloud's files)    │ (resizable)  │
      │ under its row       ├──────────────────────────────────────────┴──────────────┤
      │                     │ status: what is here, what is chosen   paging, more     │ status row
```

- **Nav pane** is frappe's sidebar (`.body-sidebar-container`), unchanged in
  what it lists. Its edge, which frappe uses to fold it to the rail, can also
  be dragged: a drag sets `--sidebar-width` (frappe's own variable) between
  180 and 440 px and keeps it per browser; a click still folds. A view that
  has a tree (OneCloud's folders, OneMail's mailboxes, a module's lists) hands
  its rows to the window's tree (`win.tree()`, `one_interface/nav_tree.js`, and
  `interfaceTree` from an island), which draws them as the rail's own rows
  under the view's row, so there is one place to go somewhere and one way
  it looks. Where that row is the rail's only one (OneCloud, OneMail) the
  row is kept, since it is what claims the page for the rail, and only the
  tree is shown.
- **Address row** is the first line of frappe's page head: Back, Forward,
  Up, then frappe's breadcrumbs and status pill where they already were,
  then Refresh and the view's search. Back and Forward are the browser's;
  Up is the breadcrumb before the last; a view may answer all three itself.
- **Refresh** is frappe's own reload button wherever frappe makes one (a
  list, a report, a board, a tree: `page.add_action_icon("refresh-cw")`),
  moved into the address row with its click and its tooltip. The window
  draws its own Refresh only where frappe has none (OneCloud, a form).
- **Command row** is the rest of frappe's page head: the view's own
  commands on the left (`window.$commands`), led by New (OneCloud's New,
  a list's primary button, which is frappe's own node, moved; a form's
  Save, Submit or Update, or where it has none its own solid button, such
  as Record Payment). The rule everywhere: the one main action, solid, is
  first on the left; the view's other actions follow; a list's or a form's
  menu (…), frappe's node too, follows them after a line, as OneCloud's
  commands do. The right end is only for ways of looking (views, Filter,
  Sort, the details switch) and a form's Cancel, last, away from the main
  action. frappe's other actions stay on
  the right, and the details pane's switch is last.
- **Views** sit at the command row's far end, beside the details switch:
  OneCloud's Details and Tiles, and a list's List, Report, Dashboard,
  Kanban, Image... as one toggle each, from frappe's own view switcher
  (its views, icons and actions). frappe's menu follows as a chevron, for
  what is inside a view: saved layouts, kanban boards, saved reports.
- **Filter and Sort** are commands, as in Explorer: frappe's own buttons
  (its filter popover, its sort menu), moved before the view toggles.
- **View row** is what frappe already draws under the head for the view: a
  list's quick filters (Filter and Sort went up to the commands). Styled as a
  row, not moved. A form's tabs are moved into it instead (`row`), so they sit
  in the same place on a new record and a saved one, above its alerts and
  head, and stay on screen as it scrolls; tabs that do not fit fold into More
  at its end, and the tab you are on is always shown. A list's column heads are drawn as
  OneCloud's: words with a line under them, not a grey box.
- **Details pane** (`window.details()`) sits right of the view, can be
  dragged wider, and is switched from the command row; both are kept per
  view kind. A form's own sidebar is already there.
- **Status** (`window.status()`): what is here, what is chosen, and
  whatever the view puts beside it (a list's paging). The window on screen
  shows it at the start of the frame's bottom bar, as a taskbar would
  (`onedesk.interface.place_status`, on every page change); without the bars,
  on a phone, it is a row pinned at the window's foot.

Every row of the window sits on one gutter, the command row's 8px: Back,
New, the quick filters, a list's checkboxes, OneCloud's file icons and the
status line all start on one edge and end on the other. frappe's list keeps a
side margin of its own and insets its rows; in the window it runs edge to
edge instead.

Two ways to fill the height. A **fitted** window (OneCloud, OneMail, the
calendar) is exactly the screen, and its view scrolls inside. A **flowing**
window (a list, a form) scrolls the page as frappe always has, with the head
held at the top and the status row at the foot, so frappe's infinite scroll,
scroll-to-field and restored positions are untouched.

## The frame

Around every window is the frame, which is the shell: frappe's rail of apps
down the left (frappe's own `.dock`, drawn from its own `--dock-*` tokens,
which `chrome.css` points at the frame's; the app you are in is marked by a
bar on the rail's edge, as Discord marks a server), a bar across the top and one
across the bottom (`chrome.js`), and the window inset between them, its
corners rounded, with the same strip of the frame (`--one-frame-gutter`)
above it, below it and on its far side; the rail pads itself on the near
side. The rail is frappe's 56px with no border, so every tile sits on a
whole pixel, and the nav pane's foot row is as tall as the rail's picture of
the person and sits as far from the bottom, so the two read as one row.

- **Top bar**: the workspace and what reaches you. Its name on the left,
  the announcements in the middle, then Search (an icon, which opens the
  address box), OneIntake, Notifications and Background Tasks.
- **Bottom bar**: this window and what is running, as a taskbar. The
  window's status (its count and paging) and open workbooks on the left;
  Check In, Timers, OneAI, and the date and time (OneCalendar) at the end,
  where Windows keeps its clock. OneAI's floating dial is not drawn while
  the bars are.

The frame's colour is `--one-frame`: frappe-ui's darkest grey in a light
theme, and in a dark one a grey a step lighter than the page (which is
already the darkest surface), with the inset's edge drawn; there frappe's
sidebar takes the page's colour, so the inset reads as one surface. A workspace's
**Frame Colour** (Company `one_frame_colour`, One's ControlCenter ›
Branding) replaces it for everyone: `chrome.js` sets `--one-frame-brand`
and marks the root `data-one-frame="brand"`, with `data-one-frame-ink`
dark on a light colour, by the rule the letter heads use for text on the
Brand Colour (`company.frame_ink`, `letter_heads.on`); a dark theme mixes it
toward the page. Everything on the frame (text, icons, the rail's marker,
badges) draws in that ink, and on a workspace's colour the rail shows each
app's flat mark, since a mark of the frame's hue would vanish: the same shape
in that ink with its white parts cut back to the frame, generated beside the
coloured one by `scripts/icons.py` as `NAME-flat`, the app you are in as
well. Saving it reaches open screens at once (`one_frame`).

## The record panel

A form's sidebar is the window's details pane (`details({ pane })`): the
switch at the end of the command row folds it, as it folds OneCloud's, and
its edge drags it from 200px to most of the window, kept per person. Under
Assign, Tags and Share it holds the **record panel**, four tabs drawn with
frappe's own `frappe.ui.Tabs`, sharing the bar's width, each an icon
(frappe's own for it) with its name as the tooltip and the screen reader's:

- **Overview**: the record's head (its charts, its track, its figures),
  drawn here by `onedesk.band.put` instead of above the fields, so a record
  opens on its fields; under it frappe's own dashboard sections (its stats,
  heatmap, graph and progress, and any a doctype adds), its stats as figure
  rows. Where our head declares a figure frappe's dashboard already shows
  by the same name, frappe's is kept and ours steps aside: the framework's
  answer wins, and our copy is left for the doctype pass to delete. It is
  all automatic, for every doctype, and styled once by frappe's own classes
  (`.form-stats`, `.form-heatmap`, `.form-graph`).
- **Activity**: frappe's comments and timeline (`frm.footer`), moved here.
- **Mail**: the record's mail (`onedesk.record_mail.open`), drawn when the
  tab is first shown.
- **Connections**: frappe's links to the records made from this one
  (`frm.dashboard.links_area`), grouped as the doctype's dashboard file
  groups them: a row per group, its name on the left and its kinds of
  record as chips. A kind with records is a filled chip with its count and,
  in amber, how many are still open; one with none is a dashed chip whose +
  makes the first. They are frappe's own nodes restyled, so its counts,
  clicks and + still work, and its Connections tab, left with nothing,
  hides itself.

A form's checkboxes are frappe's own switch (`ControlSwitch`, its Check with
a switch's markup and the same 0/1), built by a wrap of `make_control` for
the form's own fields only; a table's rows and a dialog keep their boxes.
The track says the value, read-only too (dimmed), where frappe builds no
checkbox to read; frappe's read-only tick is not drawn, since on a form it
sat inside the switch's label ahead of the real checkbox and took its clicks.

The record's files are not a tab in the row: beside frappe's print and
like in the sidebar's head, OneCloud's mark, with the file count, opens the
record's folder (`@records/<doctype>/<name>`) in a dialog over the record
(`onedesk.record_files.dialog`), OneCloud edge to edge under its title;
closing it leaves the record exactly as it was. The Files record tab is not
built while the panel is there, which gives the record's own tabs the room.

A tab with nothing for the record is not shown; a new record has no panel.
The tab somebody picks is kept per doctype. The Activity and Mail record
tabs leave the tab row while the panel holds them. All of it only where the
window covers forms and the screen is wide enough for frappe's sidebar
(992px); below that each part stays where it was.

**The widget standard.** In the panel a record's head is quiet context
beside the record, never the stage, and it is laid out by the panel's own
width (a CSS container), never the screen's, so it reads the same at any
width the edge is dragged to. In order: where the record stands (the
track, upright: a step a line, its note on the right, its mark joined to
the next); then its figures, each a row with its name on the left and its
value on the right and a hairline under it, no box and no large number,
two columns of rows from 520px; then its charts as a short strip (120px,
no value axis: its shape and the bar marked say it, the numbers are on
hover). Colour only says what needs somebody: a red amount overdue, an
amber one waiting. The tab bar runs edge to edge with no room above it. A
new widget for a record is a figure or a chart in its head (`one/head.py`),
and it lands in the panel already in this form; nothing is laid out for it
by hand.

## A record page

A record run from all day has a page of its own (`tiers.PAGES`: a project, a
task, an item, a project template), drawn by an island, and on the window it
is laid out as its form would be (`island_page`, with `record`):

- its sidebar is the details pane, with the switch at the command row's end
  and the edge that drags it;
- its own buttons are the command row's, after its main one (a task's Start
  Timer beside Complete Task);
- its state is the pill in the address row, frappe's own indicator for it
  (`indicator` in the kit);
- its views are the view row, where a form's tabs are, drawn as they are:
  words, the one you are on underlined (`InterfacePart` `row`);
- its activity is the record panel's Activity tab (`InterfacePart` `activity`,
  the window's `panel_slot`), beside Mail, and its files are OneCloud's mark
  beside print and like, so neither is a view of its own;
- who made and changed it is the status, not rows in the sidebar.

Only where the record panel is (`interfaceRecord`); on a phone the page keeps its
views, files and activity in itself, as it always has.

## Making a record

Every create opens one dialog (`onedesk.interface.create`, in `one_interface/form.js`), in place of frappe's
quick entry and its full-page new form alike: `make_quick_entry` is where
`frappe.new_doc`, a list's New and a link field's Create a new all arrive,
and it is wrapped there. The dialog is frappe's own form mounted in frappe's
`SettingsDialog`, as frappe's Data Import dialog mounts one (`frm.in_dialog`),
so the doctype's scripts, depends_on and validation run as on the page and a
refused save leaves the dialog open. The form's tabs that show are the
dialog's rail (one, Details, for a form without tabs), redrawn when a tab
comes or goes; Enlarge and Close are the dialog's own, in its corner (dialogs.js). Save is fixed at the foot of
the dialog, whatever tab is open, and stays disabled while anything frappe
would refuse for is still empty (`onedesk.interface.missing`, frappe's
`check_mandatory` read without its scrolling and message, rows of tables
and `mandatory_depends_on` included), the foot saying what is still
needed; Ctrl+S saves when it can.

Saved, it does what quick entry did: fills the link field it was opened
from and leaves the person on their record, else hands the record to
whoever asked (`after_insert`), else opens it. Closed unsaved, the new
record is dropped. A table's row and a Single are frappe's as before, and a
page inside a dialog never gets a window of its own.

The form sits beside the panel's body, not in it: the SettingsDialog styles
its body's fields as settings rows (a line over every headed section, a
line between switches), and this is a form, drawn as on the page. Made
from a field of another record being made, the new record fills that field
where it is, in its dialog: frappe's way back (`update_calling_link`)
routes to the calling record, which has no page yet. A table's row opened
in the dialog covers the dialog, not the screen.

## Where it lives

The window is two folders, and nothing of it is anywhere else:

```
public/js/one_interface/frame.js      the window, and the one place that decides where anything goes
public/js/one_interface/chrome.js     the frame around it: the top and bottom bars, the frame colour
public/js/one_interface/page.js       any desk page frappe loads by name: its primary button and menu
public/js/one_interface/list.js       frappe's list and every view made from it (report, kanban,
                               calendar, gantt, image, map, dashboard, inbox, file)
public/js/one_interface/board.js      a Kanban v2 board
public/js/one_interface/report.js     a query report: its rows and footer in the status row
public/js/one_interface/tree.js       a tree (accounts, cost centres...): views and search as a list's
public/js/one_interface/form.js       a form
public/js/one_interface/print.js      a record's print: Up goes back to the record
public/js/one_interface/workspace.js  an app's workspace
public/css/one_interface/chrome.css   the frame: its colour, the bars, the rail's tokens, the inset
public/css/one_interface/frame.css    the window's rows, panes and address box
public/css/one_interface/views.css    what a view brings into those rows (list rows, a report's footer)
```

A view tells the window what it has in one call, and the frame decides where
each part goes:

```js
page.interface.view({
  kind,       // what the view is, for the stylesheet (data-one-view)
  primary,    // its one main command (a list's New): leads the command row
  commands,   // its own commands, after the primary
  menu,       // frappe's … menu, { $button, dropdown }: last, opening rightwards
  controls,   // what narrows it (a list's Filter and Sort): before its views
  views,      // its ways of looking: frappe's view switcher, or its own toggles
  search,     // { placeholder, on_input, on_key } for the address row's box
  steps,      // its own ‹ › to the one before and after: at the address row's end
  row,        // what it shows across the window under the commands (a form's tabs)
  status, more,                     // the status row
  back, forward, up, refresh, path, // what it does for those itself
});
```

Every part is optional and may be said again. Between two groups of
commands that are shown the frame draws a line, as OneCloud does. OneCloud
is a view like any other: it says its commands, views, search, Up, Refresh
and paths through `view`, and asks for a nav slot and a details pane.

An adapter is one file per kind of frappe view. It wraps the one frappe
method where that view has what the window wants, hands those nodes (frappe's
own, which frappe still shows, hides and relabels) to `view`, and installs
through `onedesk.interface.adapt(kind)`, which runs it only where the kind is
covered: `ON`, which now holds every kind, for everybody.

Two of frappe's views are defined only when their code first loads, after
ours: Kanban v2 and the print view. Their adapters wait with
`onedesk.interface.when(owner, name, then)`, which runs `then` as soon as
frappe assigns the class.

Every kind gets the same parts where it has them. Where one differs it is
because the view does:

| | primary · menu | views | search | status | Up |
|---|---|---|---|---|---|
| A list, report, image, gantt, map | New, … | toggles | the title field | count, paging | the app's home |
| A calendar, a dashboard, the older board | New, … | toggles | the title field (not a dashboard) | none: it shows all it holds | the app's home |
| A Kanban v2 board | Add, … | toggles | none | none | the app's home |
| A query report | its primary (Generate), … | none | none | rows, frappe's footer | the app's home |
| A tree | New, … | toggles | the tree's own search | none | the app's home |
| A print | Print, … | none | none | none | the record |
| A workspace, a dashboard page, a page of ours | its primary, … | none | none | none | the breadcrumb |

A board keeps Filter, Group and Settings in its own filter row: it places
its quick filters beside them, so moving them would move those too.

So a change to how every screen looks is made in frame.js or frame.css, once.

## How it is placed

The head's rows are one CSS grid on frappe's `.page-head-content`, so
nothing frappe holds a reference to moves: `page.$title_area`, the actions,
the menu and the indicator stay the nodes frappe made. The window only adds
siblings. The status row and the details pane are added once to the page's
own wrapper. A list's paging is moved into the status row as a node, which
frappe keeps a reference to, so its buttons keep their handlers.

`onedesk.interface.of(page)` makes or returns a page's window.
`frappe.ui.make_app_page` gives one to every page but one inside a dialog
(a record being made), whose page is the dialog's.

Below 992 px nothing moves: frappe's own phone and tablet head stay, and
the window's buttons hide.

## A record's head

A record has nothing to narrow, so in Canvas its commands join the address
row, as a browser's toolbar does: nav, the address and its star, the
commands (primary first, then its own, then print and OneCloud), frappe's
Cancel, refresh, the steps, the menu, the details switch. The address row
is held at the top, so Save and Submit stay in reach. `Frame.one_join`
measures what the parts need (not what a row stretched them to) and sets
`.one-head-joined` only when they fit beside an address of at least 220px;
otherwise the commands keep their own row under the island. The head
measures its own height into `--page-head-height` (a ResizeObserver), so
whatever sticks under it sits right either way.

A record's tabs and its panel's tabs are the list's state tabs: 28px pills,
no line, the chosen one in `--one-chosen`. A panel tab whose say the head
has taken (`one-gone`) is never the one the panel opens on.
A table in a record (frappe's grid) has the list's heads, `--one-chosen`, and
the details switch wears it while the pane is open.

The record's body in Canvas: each section is a card (`--one-sheet`,
`--one-line`, `--one-radius-sheet`, 10px apart) on the canvas, with no sheet
around them, so nothing is a box in a box; frappe's `--page-max-width` on a
section is lifted so a section fills its card. Sheet, cards and islands are
one material in every palette (Sand's `--one-sheet` and `--one-card-bg` were
a step whiter than `--one-head-bg`). The track stands at the head's far end,
across from the name. A field to type in is a control: filled with
`--one-head-button-bg`, no edge, `--one-head-button-hover` on hover, the
card's ground and `--one-focus` while typing; what cannot change reads as
text. A switch is off on `--one-edge-strong`, on in `--one-check`. The head
keeps an 8px band of canvas under the address row and a short fade below,
so content scrolls under it, not against it. The record's tab rules live in
views.css, the one file the borrowing guard lets name frappe's form tabs.

A section counts its page's width, not the window's: `.form-page` is a
container (`one-page`), and the three columns drop to two under 860px and
one under 520px, so a phone and a page beside an open pane both read. A
section with no heading (`one-headless`, set by `record.fields`, since
`:has()` cannot nest) goes on in the card above it when the two are next to
each other: the items table under "Items", the taxes under theirs. Under
768px the head's name wraps and the track takes its own line, and frappe's
fixed phone height on `.page-title` is lifted so the address row's contents
sit in its pill. Panel panes that carry no padding of their own (Overview)
take the panel's 16px edge. In dark an off switch's thumb is
`--one-ink-quiet`, since frappe's thumb is the dark surface.

## Fields

A field in Canvas is filled, with no edge, and a red edge
(`--outline-red-4`, frappe's own error red) on `.has-error`, which frappe sets only once the form has
been touched or saved, never on load. A select's arrow is centred on its box
and sits at its end in either direction. A Select opens the Link's list
(`select.js`): the native list never opens; frappe's awesomplete list is
drawn in a fixed layer under the box (over it near the window's foot), so a
scrolling filter strip, a table cell or a dialog cannot clip it; arrows,
Home/End, Enter, Escape, Tab and type-to-jump work; the empty choice is a
quiet dash; a pick is set on the `<select>` and sent as `input` and
`change`. A table's cell is a cell: its input fills it square and unfilled,
with the focus edge inside while typing.

Every field type is that one control, walked type by type on a form that
holds them all, light and dark, empty and filled. A field fills its cell
(frappe's 50% `.input-max-width` cap in a one-column section is lifted). A
required value is not bold; the label's mark says it is required. Small
Text, Text and Long Text grow with what is written (`field-sizing:
content`, 88px or 132px up to 480px) instead of frappe's fixed 150px and
300px boxes, which frappe sets inline, so the height is `!important` and
the resize handle goes. The rich text editor is one box: its toolbar on the
field's fill, a hairline above the writing, and the editor grows to 480px.
Code, JSON, Markdown and HTML editors (ace) and Signature take the fill and
corner with no frame, the gutter and current line quiet. Table MultiSelect's
typing line is part of its box. Attach is a field the width of its cell,
"Attach" in the placeholder's ink; an attached file already reads as one.
Pickers (date, time, duration, colour, phone country, a Link's list) are
frappe's popovers and already match.

Check renders as a switch on forms already (Canvas's switch rules), so it
is not a second control. Icons inside a field sit on its middle line at its
start or end in either direction: the colour swatch, the password eye, and
an attached file, whose box is the field's 36px with a quiet Clear.
Placeholders are `--one-ink-muted`, the ink of Attach's word, readable in
dark. A read-only JSON value is `json_view.js`: one filled box like any
field, its heading row a search with no box of its own, the key count (or
the path pointed at), and its tools as icons named by their tooltips
(expand, collapse, raw or tree, copy); it takes the section's width.
An editable JSON field (JSON, or Code whose options say JSON) is the same
tree, edited in place: a value or a key is clicked and typed where it
stands (a text value stays text; a number, true, false or null is that), a
row shows add, copy and remove on hover, the heading's add puts a key at
the top, and each change is written back with `set_value` as JSON text
(frappe's one-space layout). Raw is frappe's code editor under the same
heading; back to the tree reads the text again, and text that is not JSON
yet stays in Raw with "Invalid JSON". JSON kept as text inside a value is
shown, never edited. The tree follows `set_formatted_input` as well as
`refresh`, because a value set from a script reaches the input without a
refresh.

## Stars

A like is a star (`star.js`), the mark a browser and a file manager use for
a favourite. frappe's like is untouched (`toggle_like`, `_liked_by`, the
liked-by list, the list's filter); `star.js` swaps the heart symbol for the
star wherever frappe draws it (a MutationObserver on the body) and wraps
`toggle_like` to pop the star as it fills. A chosen star reads `--one-star`.
In Canvas a record's star leaves the sidebar for the end of the address row,
before refresh, as a browser's ends its address bar.

## The address box

In Canvas the window is one canvas from its left edge, and the side pane is
an island on it like the address row: `--one-head-bg`, `--one-line` and
`--one-radius-sheet`, 8px in, its top level with the address row's. The
pane is drawn by a `::before` on `.body-sidebar` (pinned and expanded
only), so frappe's sidebar markup is untouched. One role for both, so they
stay the same material in every palette.

In Canvas the whole head is on the canvas, like the record under it: the
address row is one island in from the window's edges (`--one-head-bg`, a
softer white than a sheet in Sand), its box drawn without an edge of its
own since the island is the box, and the actions row sits under it on the
ground, its plain buttons on `--one-head-button-bg` so they stand off the
canvas in every palette. No line runs under either row. Classic keeps the
two rows as a band.

Everything in the window starts and ends on one edge, `--one-inset` (10px)
in from its sides: the island, the actions, the heading, the tabs, a list,
and a record's figures, alert and sheet. Only a box sets its own content in
(the island, a row, the list's head). A list's column heads are a filled
pill of the island's material, held at the top while the rows scroll and
whole while they scroll sideways: a sticky layer as wide as the list's
window (`100cqw` of `.result-container`) draws the pill, the heads ride
over it.

A list's head in Canvas is three rows, each holding one kind of thing. The
island holds where you are, and the view's … menu at its end (every view:
the look wraps `Frame.view` and moves the menu group into the tools, its
dropdown aligned to the end). The row under it narrows: frappe's own quick
filters (the fields marked for the standard filter bar, which anyone
changes in Customize Form; we add none), moved there by `list.filters` and
sliding sideways when they overflow, then Filter and the sort at the end as
icons (their words hidden for the eye only; an applied count stays). The
heading row acts on the whole list: its kind's icon
(`onedesk.interface.icon_of`: the module's declared `icon`, else the icon
of its row in frappe's module sidebars) and name, New beside them (the count
is the All tab's, not said twice),
and the view switcher at the far end (`list.place`). The Frame keeps its
command groups and its views (`ways_slot`, apart from the filters) by
reference, so a look can put them anywhere and the Frame still fills them;
classic leaves them where they were. A view without a heading (Report,
Kanban) keeps New and the views in the row under the island. The column
heads' pill is washed with New's colour (12% of `--one-primary-bg` on the
canvas, no edge; a solid band was a bright bar in dark), and the states over the
rows are pills of the palette, the chosen one filled like the chosen view. What is chosen (the side pane's row, the state tab,
the view, the heads' pill) reads one derived role, `--one-chosen` (12% of
`--one-primary-bg` on the canvas, canvas.css); every other control in the
head is 28px on `--one-head-button-bg` with `--one-radius-control`, and the
island's own (refresh, search, the menu) are on `--one-address-bg`.

At rest the address box is frappe's breadcrumbs, each crumb a link. Clicked
in an empty part, or with Ctrl+K, or with the search button in the top bar,
it becomes a box to type in, answered by frappe's own search bar
(`onedesk.interface.AddressBar`, a `frappe.search.AwesomeBar` that draws under
the box instead of in its modal): the record types, reports, pages and
"New ..." rows it always offered, filtered to what One shows
(one/outside.py `shown`), and its `awesomebar_search` hooks. Two of those
are ours: records named like what was typed (`outside.awesomebar`, frappe's
global search ranked so a record whose name starts with it comes first, and
a record named by it, a customer, before a document about it, their
invoice), and OneIntake's search by meaning. Esc puts the breadcrumbs back.

A view with paths of its own is asked first when what is typed has a "/":
OneCloud opens `Company/Document Templates` as a folder.

So there is one way to go somewhere (the address box) and one way to narrow
what is here (the search box beside it, which filters this list or this
folder). Below 768 px, where the address row is not drawn, Ctrl+K opens
frappe's own search as before.

frappe's global search tells the reader, in a message, about every record
it leaves out because they may not read it. Typed into a box that searches
on every key, that was a dialog on every key, so `outside.search` keeps the
records left out and drops the messages.

## Who it covers

Everybody, on every kind of view: page, list, board, report, tree, form,
print and workspace. Each was walked before it joined, and the Window
Preview switch that held them back is gone. Below 992 px frappe's own
phone and tablet head stay, as before.

## What each view tells the window

| | Back · Forward · Up | Refresh | Search | Status | Details |
|---|---|---|---|---|---|
| OneCloud | its own history; Up is the parent folder | re-lists | the folder, or everywhere | items, chosen, size | the chosen file's preview, versions, OneIntake |
| A list | the browser's; Up is the app's Home | `list.refresh()` | the title field, as a filter | frappe's count, chosen | (next) the chosen record |
| A form | the browser's; Up is the list; ‹ › its records, at the address row's end | `frm.reload_doc()` | none | who edited it and when, who made it | frappe's form sidebar, as frappe draws it, less who edited and made it (the status says); who else has it open (frappe's avatars) as a row above Assign; OneCloud's mark beside print and like for its files; the record panel |

## Views

Every way of looking at a list wears the list's head: the list's name with
New, the ways at the far end, the quick filters in the row under the address
with Filter and Sort at its end. That is List, Report, Kanban, Gantt,
Calendar, Image, Map and Dashboard (`list.FAMILY` in look.js). The states
strip under the name is left off a board, whose columns are the states, and
a dashboard, whose charts count their own (`list.STATELESS`). The report view
draws itself without the list's `after_render` and the board is frappe's own
page, not a list view, so look.js wraps each. A board's Filter, Group and
Settings live in a row of their own beside its quick filters, so that row
moves with them.

A tree and a query report wear the same head under their own name: Chart of
Accounts with its Add (as New) and its ways, or Accounts Receivable with the
icon of the doctype it reports on and its own buttons (Accounts Receivable
Summary) where the ways would be. A tree's search fields and a query report's
whole filter form fill the row under the address. look.js runs the head after
TreeView's set_primary_action and again after its post_render (ERPNext's
Account tree sets its button anew there), and after QueryReport's
setup_page_head, which runs once per report opened.

In Canvas each view's body reads the page's roles rather than its library's
own colours: a report's table (and a query report's) has its heads on the
list's head fill and its filter boxes filled like a field; a Gantt chart's
bars are `--one-fill` with progress in `--one-edge-heavy`, where frappe-gantt
draws a white bar on a white row; a calendar's grid is the sheet with Sunday
on the tint. A calendar event keeps frappe's colour, which is its state's. A chart's labels, legend and tooltip read the page's inks: frappe's dark theme
sets the chart's label colour but not `--charts-legend-value`, so a legend's
figures stayed the light theme's dark grey on a dark sheet.

A map view was blank in frappe: ListView's constructor sets `this.load_lib`
to a promise, hiding MapView's own `load_lib`. list.js gives MapView a
`setup_view` that calls the class's method by name.

## What it replaces, when every view is on it

OneCloud's own bar, address bar, tree and status line (done), OneMail's
pane heads, the shell's `panes` and `fit`, the breadcrumb switchers drawn
per page, and every page that sizes itself to the screen. Each is a part the
window now has once.

## The guards

`tests/guards/test_interface_frame.py`: the window is its two folders, every file of
them loaded and the frame first; an adapter installs through `adapt` and
only hands parts to `view`, never reaching into the frame's rows; the window
adds and never replaces frappe's head (it keeps `page.$title_area` and the
actions where frappe made them); only `css/one_interface/` styles `.one-interface-*`; OneCloud on a page draws no bar,
address bar, tree or status of its own; the nav width stays inside its
limits and is kept; every kind of view is on it, for everybody, with no
preview left to turn on.

The engine names no screen. `one_interface/` and `band.js` work from what frappe
says a screen has, so no doctype, field or route of one screen appears in
them (`test_the_engine_names_no_doctype`); the only doctype read by name is
frappe's `Note`, which is the top bar's news. A rule for one screen goes to
the module that owns it.

## Looks

A **look** is how the frame and frappe's screens in it are drawn; it is
not a theme. Three words, three layers:

- **Look**: the design language. `public/js/one_interface/look.js`
  declares them (`onedesk.interface.LOOKS`) and sets `data-one-look` on the
  page: the person's own (Appearance), else the workspace default
  `one_look` from the boot, Canvas when unset. A look is a stylesheet scoped to its attribute
  (`public/css/one_interface/canvas.css` is Canvas) and the parts of the
  renderer it turns on (`onedesk.interface.uses(part)`): `head`, `strip`,
  `thread`, `quiet`, `icons`. Classic turns none on, which is frappe's desk
  on the frame as it was.
- **Theme**: light, dark or automatic. Frappe's (`desk_theme`), untouched.
- **Palette**: everything a look's parts are drawn in, part by part:
  colours, the primary and plain buttons, the chosen row, corners, heading
  and button weight. Below, under Palettes.

Every look defines its tokens for every theme; palettes ride on both. The
HTML the renderer builds is the same in every look: a look changes tokens
and turns parts on, and a future look that wants a different arrangement
adds a part here rather than forking the renderer.

**What Canvas's parts do**, each idempotent, drawn on `form-refresh` and
once more after the form settles:

- `head` (`record.head`): the record's picture (frappe's own wrapper, moved
  so upload and remove still work), its name and state, its ID under the
  name when the ID is not the name, the track (the steps of the head row
  the module names as `track`, else the first with steps), the cards its
  module declares (`cards`, at most four, the `onedesk.head` island drawing
  the kit's Figures) and the tabs under the head. The panel's Overview tab
  goes when the head says what it said. Print, like and OneCloud sit at
  the bar's end, before Cancel.
- `quiet` (`record.fields`): on a saved record an empty field nobody must
  fill waits behind Show N Empty Fields, a section with nothing shown goes,
  a tab with nothing shown goes, a field's help is a mark beside its label,
  and a box shows its whole value on hover.
- `icons`: the icons a module declares for tabs and fields, on the record
  and on a list's column heads, drawn again whenever the list is.
- `thread` (`record.thread`): the activity as one thread, redrawn after
  frappe's timeline each time (it wraps `render_timeline_items`).
- `strip` (`list.strip`): over a list's rows, its name and count, then the
  states its module declares (`states`; `status` by default), each a
  filter, with frappe's quick filters at the strip's end. It wraps
  `ListView.after_render`.

The registry is `ready.MODULES[module]["interface"]`; `ready.interface()`
merges it and boot hands it over as `frappe.boot.one_interface`.

## Levels

Every surface stands on one of four levels, back to front, each a role in
tokens.css that a palette sets for its light and its dark:

- `--one-level-page`: the page behind everything (`--one-canvas`).
- `--one-level-island`: what stands on the page. The address row, a record's
  section cards, a report's table (`--one-sheet`, `--one-card-bg`,
  `--one-head-bg`).
- `--one-level-control`: a field or button in an island, set apart from it
  further than the island is from the page (`--one-head-button-bg`,
  `--one-button-bg`). A field reads as a dip in its card. Every table's
  column heads are this band too: a list's, a record's table's, a report's
  and a query report's, the tone of the quick filters over them. A list's
  rows stand on an island like a report's.
- `--one-level-float`: what floats over all of it. Menus, dialogs, the details
  pane, the status line (`--one-menu-bg`, `--one-dialog-bg`,
  `--one-details-bg`, `--one-status-bg`).

A dark palette may come forward by going darker: Sand's islands are darker
than its page. tests/guards/test_palettes.py holds every surface to its level
and the levels to that order. The rest are bridges to frappe's own variables
(`--one-surface`, `--one-raised-bg`, `--one-control-bg`, `--one-sidebar-bg`)
or states and marks drawn on a level (hover, press, fill, tint, chosen).

## Palettes

Every rule of the frame and of Canvas reads a **role**, never a step of
frappe's grey scale: `--one-sidebar-active-bg`, not `--surface-gray-2`.
`public/css/one_interface/tokens.css` names the 61 roles (the frame, the
sidebar and its chosen row, the window's head and status line, the canvas
and its sheets, ink, lines and fills, the accent, the primary and plain
buttons, fields and focus, tabs and counts, corners, heading and button
weight) and holds Standard's value for each, which is frappe's own, so
Standard draws exactly what frappe draws.

Frappe's own parts read frappe's variables, so tokens.css bridges them:
`--btn-primary`, `--btn-default-bg`, `--control-bg`, `--desk-sidebar-bg`
and `--dock-*` read the roles, and inside `.body-sidebar` the steps frappe's
sidebar rows read are the sidebar's roles. Frappe's CSS follows a palette
without being edited.

A palette (`palettes.css`, on `data-one-palette`) sets its own grey scale,
keeping frappe's lightness at every step so contrast stays Standard's, and
then every role for its light and its dark; shape and type are set once.
Sand is the one palette One ships, with the Canvas look, and what everyone
sees until they choose.

Each person chooses their look, theme and palette in Appearance (frappe's
Toggle Theme, `theme.js`). A look marked `offered` is shown there (Canvas
only, for now; Classic is kept but not offered), and names the palettes
drawn for it (`LOOKS.canvas.palettes`, look.js), the first being its
default; Standard is always offered. Look and palette are kept in the
window's user settings (`look`, `palette`, frame.js), the look falling back
to the workspace's `one_look`; look.js sets `data-one-look` and
`data-one-palette` before the first screen. Changing the look reloads the
page, since it turns parts of the renderer on. Every card is a
`.one-sample`: tokens.css and palettes.css declare their roles on it as on
`:root`, and frappe declares its greys on every `[data-theme]`, so a
sample in any theme and palette draws from the same roles as the window.
A palette's blocks name both, which `test_palettes.py` checks.

Under a palette nothing frappe draws is left on a value the palette did not
choose. tokens.css points, only while a palette is on:

- frappe's named steps (`--ink-gray-3`…`9`, `--surface-base`,
  `--surface-gray-1`…`4`, `--outline-gray-1`…`4`, the elevations,
  `--surface-sidebar`, `--ink-base`) at the roles, so every rule of
  frappe's that reads a step follows; a palette therefore writes its roles
  against the raw scale (`--gray-900`), never a named step;
- frappe's component variables (`--text-color`, `--border-color`,
  `--card-bg`, `--modal-bg`, `--popover-bg`, `--checkbox-color` and the
  rest) at the roles;
- the whole radius scale (`--radius-1`…`8`, `sm` to `2xl`) at the six
  corner roles, every shadow and elevation at the three shadow roles, and
  `--font-stack` at `--one-font`;
- the surfaces frappe paints with a general colour (a dialog and the form
  in it, Bootstrap's and espresso's menus and popovers, a figure card) at
  their roles.

Islands draw in a shadow root with frappe-ui's own copy of the greys, so
look.js adopts one sheet into every island and island part that points the
same steps at the same roles, the steps no role stands for at the page's
(`--one-page-*`), and the island's corners and font at the palette's, and
copies the palette onto the island's root. Standard leaves frappe and
islands exactly as they draw.

`tests/guards/test_palettes.py` fails when a rule reads the scale, a role is
read and never declared, a palette leaves a role out or writes one against
a named step. A new part gets a role in tokens.css and a value in every
palette in the same commit. To audit, give every role a loud value under a
throwaway palette and shoot the screens: whatever still looks like Standard
is a part no role reaches.

## Layers

Whatever stacks over the page names its layer, so a bar, a dialog, a menu
and a tour cannot take each other's place. tokens.css holds the ladder,
which is Bootstrap's own (frappe's dialogs and menus already sit on it):

| Layer | Value | What sits on it |
|---|---|---|
| `--one-layer-sticky` | 1020 | a list's sticky head |
| `--one-layer-panel` | 1029 | OneAI's panel, just under the bars |
| `--one-layer-frame` | 1030 | the top and bottom bars, a floating field |
| `--one-layer-backdrop` | 1040 | a dialog's scrim, a slideshow over the window |
| `--one-layer-dialog` | 1050 | a dialog |
| `--one-layer-menu` | 1060 | a menu, a listbox, a popover, a context menu |
| `--one-layer-tooltip` | 1070 | a tooltip, a drag cursor |
| `--one-layer-toast` | 1080 | a toast |
| `--one-layer-tour` | 100003 | a tour (driver's own numbers), only over a dialog when the tour is in it |

A z-index of ours is one of these, or `calc()` of one plus a small step
when two of ours share a layer (the sheet's slicer, comment box and context
menu are menu +1, +2, +3), or a local order under 100 inside its own part.
A tour's highlight drops back to `auto` while a dialog is open and the tour
is not in it, which is what drew the search box over a dialog.

The one exception is the slide canvas: a slide's elements number one per
element inside the slide's own stacking context, and the handles sit above
any count of them. `tests/guards/test_layers.py` holds the list.

## Dialogs

Every dialog is frappe's own (`frappe.ui.Dialog`, `SettingsDialog`,
`frappe.confirm`, `frappe.warn`, `frappe.prompt`, `frappe.msgprint`), told
its **kind** after frappe builds it, and the kind decides its size and
parts, never the caller. `public/js/one_interface/dialogs.js` wraps
`Dialog.make` and the four helpers; `public/css/one_interface/dialogs.css`
draws them. Both hold in every look: a look restyles the parts through
its tokens (Canvas lays a dialog's fields on its grid, `canvas.css`) and
never draws parts of its own.

| Kind | What opens it | Size | Parts |
|---|---|---|---|
| ask | `frappe.confirm`, `frappe.warn`, `frappe.prompt`, `onedesk.interface.ask` | 420 | round mark, the question as the title, the effect under it, the verb |
| tell | `frappe.msgprint` | 420 | round mark (red for an error), the message, OK |
| task | any other `frappe.ui.Dialog` | 580, 820 when frappe asks for large | title, Enlarge and Close, fields in one column, footer |
| create | `onedesk.interface.create` (`one_kind: "create"`) | by its shape | the form's tabs as a rail, Save at the foot with what is missing |
| centre | any other `SettingsDialog` | 1000 | rail, Help, Enlarge and Close in the corner, Back one page deep |

A new record's shape is `dialog.one_shape({ rail, small })`: with its
rail it is 960 wide, so the form keeps two columns beside it; without, 720
and as tall as its fields; a few fields and no tabs, 560 and one column.

**The window's controls are the kit's alone.** A dialog with a header
holds them in frappe's `.modal-actions`; a dialog with a rail, which has
no header, in `.one-dialog-controls` in its corner. In order:

- **Help**, `dialog.one_help(open)`: a centre or the Help dialog says what
  opens; nothing else draws a Help button.
- **Enlarge**, `dialog.one_enlarge()`: a task, a new record or a centre
  fills the window, not the browser. A centre opens at the size it was
  left at (`centre_large`, in this browser).
- **Close**.

**Back**, `panel.one_back(go)`, before a panel's title once it has gone a
page deep: a centre's view (`module_settings.kit.view`) and a record in a
centre (`center_section.js` `as_record`) both ask the kit for it. frappe's
`set_header` and `set_view` draw the title again, which takes it away.

The footer says what is still needed on the left (`dialog.one_need(html)`)
and holds the verbs on the right, the main one last, red when it cannot
be undone.

**Asking.** A question is asked with `onedesk.interface.ask({ question,
effect, verb, danger })`, which resolves true or false: the question is
the title, the effect is one line under it, and the verb names the act
(Delete Customer, not Yes), in frappe's own solid red button when it
cannot be undone. frappe's own confirm keeps its words; a short plain
message under a generic Confirm becomes the title.

A toast is frappe's `show_alert`, an island's dialog is frappe-ui's, and
the create dialog still keeps a foot of its own inside its panels; none
is drawn to this anatomy yet (SCRATCHPAD).

## Stamps

On a dev site only (`developer_mode` or `one_dev` in its config), the
bottom bar says how far a screen has come in review
(`public/js/one_interface/stamps.js`, `onedesk.interface.stamp`):

- **Island**, amber, with the island's name, on a page an island still
  draws (`island_page.js`), until the walk replaces it.
- **Passed**, green, with its day, on a screen the final passthrough has
  finished: `stamps.py` `PASSED`, keyed as frappe routes to the screen
  (`Form/<doctype>`, `List/<doctype>`, `query-report/<report>`, a page's
  route). The passthrough skill adds a screen in the commit that finishes
  it; a change that undoes the pass takes it out.

A customer never sees one: `stamps.for_boot` sends nothing to a site that
is not dev. `tests/guards/test_stamps.py` holds how a screen is named.
