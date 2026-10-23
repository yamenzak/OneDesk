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
Assign, Tags and Share it holds the **record panel**, three tabs drawn with
frappe's own `frappe.ui.Tabs`:

- **Overview**: the record's head (its charts, its track, its figures),
  drawn here by `onedesk.band.put` instead of above the fields, so a record
  opens on its fields.
- **Activity**: frappe's comments and timeline (`frm.footer`), moved here.
- **Mail**: the record's mail (`onedesk.record_mail.open`), drawn when the
  tab is first shown.

A tab with nothing for the record is not shown; a new record has no panel.
The tab somebody picks is kept per doctype. The Activity and Mail record
tabs leave the tab row while the panel holds them. All of it only where the
window covers forms and the screen is wide enough for frappe's sidebar
(992px); below that each part stays where it was.

**The widget standard.** Whatever the Overview holds is laid out by the
panel's own width (a CSS container), never the screen's, so it reads the
same at any width the edge is dragged to: charts, the track and anything
that is not a figure take the whole width; figures are frappe's stat cards,
two to a row, three once the panel is 520px wide. A new widget for a record
is a stat card or a chart in the head (`one/head.py`), and it lands in the
panel already styled; nothing is laid out for it by hand.

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
  steps,      // its own ‹ › to the one before and after: beside Up
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
covered: `ON` (pages that ask) for everybody, `TRIAL` (every other kind)
for whoever turned the preview on. A kind leaves the trial by moving from
one list to the other.

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
`frappe.ui.make_app_page` gives one to every page that asks
(`{ one_window: true }`, which `onedesk.shell.page` passes on) and, while
the trial is on, to every page.

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

## The trial

OneCloud is on the window for everybody. Lists and forms are on it for
whoever turns on **Window Preview** in the user menu (kept per browser),
until each kind has been walked like the screen walks before it. Nothing
else changes for anybody who has not.

## What each view tells the window

| | Back · Forward · Up | Refresh | Search | Status | Details |
|---|---|---|---|---|---|
| OneCloud | its own history; Up is the parent folder | re-lists | the folder, or everywhere | items, chosen, size | the chosen file's preview, versions, OneIntake |
| A list | the browser's; Up is the app's Home | `list.refresh()` | the title field, as a filter | frappe's count, chosen | (next) the chosen record |
| A form | the browser's; Up is the list; ‹ › its records, beside Up | `frm.reload_doc()` | none | who edited it and when, who made it | frappe's form sidebar, as frappe draws it, less who edited and made it (the status says) and its files (the Files tab holds them); who else has it open (frappe's avatars) as a row above Assign |

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
limits and is kept; the trial switch is the only thing that puts lists and
forms on it.
