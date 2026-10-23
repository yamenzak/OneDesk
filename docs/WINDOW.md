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
- **Command row** is the rest of frappe's page head: the view's own
  commands on the left (`window.$commands`), frappe's actions, menu and
  primary button on the right, and the details pane's switch last.
- **View row** is what frappe already draws under the head for the view: a
  list's filters and sort, a form's tabs. Styled as a row, not moved.
- **Details pane** (`window.details()`) sits right of the view, can be
  dragged wider, and is switched from the command row; both are kept per
  view kind. A form's own sidebar is already there.
- **Status row** (`window.status()`) is pinned at the foot: what is here,
  what is chosen, and on the right whatever the view puts there (a list's
  paging).

Two ways to fill the height. A **fitted** window (OneCloud, OneMail, the
calendar) is exactly the screen, and its view scrolls inside. A **flowing**
window (a list, a form) scrolls the page as frappe always has, with the head
held at the top and the status row at the foot, so frappe's infinite scroll,
scroll-to-field and restored positions are untouched.

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
| A form | the browser's; Up is the list | `frm.reload_doc()` | none | (next) saved, by whom | frappe's form sidebar |

## What it replaces, when every view is on it

OneCloud's own bar, address bar, tree and status line (done), OneMail's
pane heads, the shell's `panes` and `fit`, the breadcrumb switchers drawn
per page, and every page that sizes itself to the screen. Each is a part the
window now has once.

## The guards

`tests/guards/test_window.py`: the window adds and never replaces frappe's
head (it keeps `page.$title_area` and the actions where frappe made them);
only `window.css` styles `.one-window-*`; OneCloud on a page draws no bar,
address bar, tree or status of its own; the nav width stays inside its
limits and is kept; the trial switch is the only thing that puts lists and
forms on it.
