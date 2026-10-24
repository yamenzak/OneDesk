# The window

Every screen of One in one frame, the way every folder in Windows Explorer
looks the same whatever is in it. OneCloud is the frame's first tenant
because it already looks like this; every list, form, report and page of
ours follows, one by one.

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
   the nav pane (`win.nav_slot()`), a button. Making a record is the create
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
| Masters | 1, moved: each kind's frappe list, the kinds as a tree in the nav pane |
| Ready to Submit | 1, moved: a script report with a checkbox column and Submit |
| Intake | 2, moved: the island `onedesk.intake`, the document open in the details pane |
| Agreements (legal) | 2, moved: a reader, the island `onedesk.legal` |
| OneCalendar | 2: a product |
| OneMail | 2, moved: the island `onedesk.onemail`, its mailboxes in the nav pane |
| OneCloud | 2: a product |
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
  has a tree of its own (OneCloud's folders) puts it under its row in the
  pane (`window.nav_slot()`), so there is one place to go somewhere.
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
  (`onedesk.window.place_status`, on every page change); without the bars,
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
corners rounded, with a strip of the frame on its far side.

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
**Frame Colour** (Company `one_frame_colour`, Workspace › General › Contact and
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

## Making a record

Every create opens one dialog (`onedesk.window.create`, in `window/form.js`), in place of frappe's
quick entry and its full-page new form alike: `make_quick_entry` is where
`frappe.new_doc`, a list's New and a link field's Create a new all arrive,
and it is wrapped there. The dialog is frappe's own form mounted in frappe's
`SettingsDialog`, as frappe's Data Import dialog mounts one (`frm.in_dialog`),
so the doctype's scripts, depends_on and validation run as on the page and a
refused save leaves the dialog open. The form's tabs that show are the
dialog's rail (one, Details, for a form without tabs), redrawn when a tab
comes or goes; close is each panel's head. Save is fixed at the foot of
the dialog, whatever tab is open, and stays disabled while anything frappe
would refuse for is still empty (`onedesk.window.missing`, frappe's
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
public/js/window/frame.js      the window, and the one place that decides where anything goes
public/js/window/chrome.js     the frame around it: the top and bottom bars, the frame colour
public/js/window/page.js       any desk page frappe loads by name: its primary button and menu
public/js/window/list.js       frappe's list and every view made from it (report, kanban,
                               calendar, gantt, image, map, dashboard, inbox, file)
public/js/window/board.js      a Kanban v2 board
public/js/window/report.js     a query report: its rows and footer in the status row
public/js/window/tree.js       a tree (accounts, cost centres...): views and search as a list's
public/js/window/form.js       a form
public/js/window/print.js      a record's print: Up goes back to the record
public/js/window/workspace.js  an app's workspace
public/css/window/chrome.css   the frame: its colour, the bars, the rail's tokens, the inset
public/css/window/frame.css    the window's rows, panes and address box
public/css/window/views.css    what a view brings into those rows (list rows, a report's footer)
```

A view tells the window what it has in one call, and the frame decides where
each part goes:

```js
page.window.view({
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
through `onedesk.window.adapt(kind)`, which runs it only where the kind is
covered: `ON`, which now holds every kind, for everybody.

Two of frappe's views are defined only when their code first loads, after
ours: Kanban v2 and the print view. Their adapters wait with
`onedesk.window.when(owner, name, then)`, which runs `then` as soon as
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

`onedesk.window.of(page)` makes or returns a page's window.
`frappe.ui.make_app_page` gives one to every page but one inside a dialog
(a record being made), whose page is the dialog's.

Below 992 px nothing moves: frappe's own phone and tablet head stay, and
the window's buttons hide.

## The address box

At rest the address box is frappe's breadcrumbs, each crumb a link. Clicked
in an empty part, or with Ctrl+K, or with the search button in the top bar,
it becomes a box to type in, answered by frappe's own search bar
(`onedesk.window.AddressBar`, a `frappe.search.AwesomeBar` that draws under
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

## What it replaces, when every view is on it

OneCloud's own bar, address bar, tree and status line (done), OneMail's
pane heads, the shell's `panes` and `fit`, the breadcrumb switchers drawn
per page, and every page that sizes itself to the screen. Each is a part the
window now has once.

## The guards

`tests/guards/test_window.py`: the window is its two folders, every file of
them loaded and the frame first; an adapter installs through `adapt` and
only hands parts to `view`, never reaching into the frame's rows; the window
adds and never replaces frappe's head (it keeps `page.$title_area` and the
actions where frappe made them); only `css/window/` styles `.one-window-*`; OneCloud on a page draws no bar,
address bar, tree or status of its own; the nav width stays inside its
limits and is kept; every kind of view is on it, for everybody, with no
preview left to turn on.

The engine names no screen. `window/` and `band.js` work from what frappe
says a screen has, so no doctype, field or route of one screen appears in
them (`test_the_engine_names_no_doctype`); the only doctype read by name is
frappe's `Note`, which is the top bar's news. A rule for one screen goes to
the module that owns it.
