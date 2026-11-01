---
name: ui
description: How a screen of One is built and laid out. Load it before making or changing anything a person sees or clicks — a list, form, dialog, page, island, record page, settings section, button, column, filter, tile, card, empty state or rail row — in doctype JSON, a client script, desk JS/CSS or a Vue island, and before calling any UI work done.
---

# UI

**Do not design. Place frappe's parts.** Nearly everything a screen needs,
frappe already draws: a list, a form, a filter, a status colour, a switch, a
dialog. The job is to find the property or component that makes frappe draw
it, and put it where OneInterface says it goes. Drawing it ourselves is the
last resort, and every time it was the first resort here it was wrong.

Words on the screen follow the `wording` skill; whether the job gets done is
the `ux` skill. Load all three.

## Before anything: which kind of screen

1. **Frappe's own list or form, on the window.** The default for nearly
   everything. What we add is a small piece inside it: a column, a filter, a
   head with figures (`one/head.py`), a record tab, a button, a client script.
2. **A Vue island**, only for what is genuinely more than a list or a form:
   a product (OneMail, OneCloud, OneCalendar), an app's home, an editor, a
   record run from all day (`tiers.PAGES`). Declared in `tiers.SCREENS` with
   the reason it isn't a list or a form.

If you cannot say why a list or a form won't do, it is 1.

## Where frappe draws it for you

Look for these before drawing anything:

| You want | Frappe does it with |
|---|---|
| A list split by state (Showing / Ended) | a Select field with `in_standard_filter`, and `listview_settings.filters` to open on one |
| A column in a list | `in_list_view` |
| A coloured state on a row | `get_indicator` in `listview_settings` |
| A yes/no on a form | a Check: the window draws it as frappe's switch |
| Figures or a chart on a record | the head in `one/head.py`: it lands in the record panel already laid out |
| Making a record | the window's create dialog (`onedesk.interface.create`), never a page of our own |
| A record's files | OneCloud's mark beside print and like, never a Files tab |
| An action inside a field | frappe's `.link-btn`, the icon a Link field shows |
| A button | `frappe.ui.button` / frappe-ui `Button`; inputs are frappe's `form-control` |

In an island the order is: frappe-ui, then `@framework/ui` (Link,
FormLayout, ListView, Filter, ActivityTimeline), then `frontend/src/kit`
(`Page`, `Section`, `Rows`, `Figures`, `Facts`, `Pill`, `OneAlert`), and
our own component only when none of those has it.

## The parts of a screen that serve the job

Whether the job can be done at all, in how many steps, and what happens when
it goes wrong is the `ux` skill. On the screen itself:

- **The one main action is the solid button, first on the left of the
  command row.** Everything else is outline, after it, then the `···` menu.
- **A row that stands for a record opens it.** The whole row, the title, the
  card. No Edit or Open button on rows.
- **A create dialog asks the deciding question first**, as cards when the
  answer changes the rest of the form.
- **A picker scrolls inside itself and shows each choice's face.**
- **Nothing the rail already has is repeated on the page.** No heading that
  repeats the rail row, no link list to places the rail lists.
- **A home holds what only its app can gather.** Not shortcuts.

## Where things go (OneInterface)

The frame decides placement; a view only says what it has
(`page.interface.view({ primary, commands, menu, controls, views, search, row, status })`).

- **Address row:** Back, Forward, Up, the breadcrumb, the record's status
  pill, Refresh, search.
- **Command row:** the main action (solid), the view's other commands, then
  `···`. The right end holds only ways of looking (views, Filter, Sort, the
  details switch) and a form's Cancel, last.
- **View row:** a list's quick filters; a form's tabs.
- **Details pane / record panel:** Overview (the head), Activity, Mail,
  Connections. Who changed it is the status row, not sidebar rows.
- **Status row:** the count, what is chosen, paging.
- **A rail row is a place** (a list, a page, a board), never a dialog. A
  page keeps its app's rail; what it lets a person pick from is a section of
  that rail, not a column of its own.

Never reach into the frame's rows from a screen. A change to how every
screen looks is made once, in `public/js/one_interface/` or `public/css/one_interface/`.

## How it looks

- **Tokens only.** Colours are `--ink-*`, `--surface-*`, `--outline-*` (or
  `--one-*` built from them), corners `--radius-*`, borders 1px. No shadows,
  no literal colours, no Tailwind palette classes like `bg-gray-100`.
  `test_tokens.py` refuses the rest.
- **Sections are space, not lines.** No rule between groups. A list keeps
  its row dividers inside itself only.
- **Most sections have no note.** The heading and the content say enough.
- **Colour only says what needs somebody:** red for overdue, amber for
  waiting. Never decoration.
- **An empty list is not drawn as an empty box.** A quiet line ("No custom
  fields"), or nothing.
- **Rows, tiles, cards:** many of a kind are list rows; a few parallel
  things each with a state and one action (password, two-factor, passkey)
  are tiles; choices that each have a picture are cards. Liking tiles on
  one page is no reason to use them on the next.
- **A small form gets a small dialog.** No tabs and at most six fields is
  one column, 36rem, as tall as its fields, with no section rail.
- **A switch means "on shows it":** Currency Symbol, not Hide Currency Symbol.
- **An OneAI button does one thing in place:** violet, OneAI's mark, a small
  popover with Use and Try Again. It never opens the panel.

## Claude's UI habits, and what to do instead

Each of these happened in this app.

- **Building a screen frappe already has.** The Recycle Bin was a Vue
  island; frappe's Deleted Document list with Restore does the job.
- **Drawing a control where a property makes frappe draw it.**
  Announcements got tabs, then a redirect page, then a hand-drawn picker;
  the answer was a Status field marked `in_standard_filter`.
- **Explaining the screen on the screen.** "How Do I Add It?" sections,
  notes under every heading, a second heading repeating the first. Delete
  them.
- **Saying things twice.** A "Stats" heading over rows that name
  themselves; a figure in the head and again in the panel; My Tasks drawing
  a column with the rail's own rows.
- **Decoration.** Cards around everything, separator lines, shadows,
  eyebrow labels above headings, an icon on every row. Take it off until
  something is missing.
- **A heading that says the section, not the thing.** "Details" over the
  only section of New News Source.
- **Desktop only.** Every screen is looked at on a phone and in Arabic too.

## Before calling it done

Walk the job, as the person who does it, to the end:

1. Sign in as a demo user with the role (`tests/browser/screens.mjs` lists
   who does what: samir runs projects, huda keeps the books, karim the
   stock, omar sales, mariam HR, tariq and nadia are employees, wsadmin
   administers).
2. Click what they would click and finish the job: make the record, not
   just open one that exists.
3. Look at it at 1440 wide and at 390 wide, in Arabic (right to left), and
   in the dark theme.
4. Read every string with the `wording` skill.
5. Run the UI guards, which take seconds:

       python3 -m pytest -q tests/guards/test_tokens.py tests/guards/test_interface_frame.py \
         tests/guards/test_islands.py tests/guards/test_layout.py tests/guards/test_shell.py \
         tests/guards/test_record_page.py tests/guards/test_rail.py

A guard failure means the screen is wrong, not the guard.

`onedesk/one_interface/AGENTS.md` is the full contract and `docs/UI-NOTES.md` the walk
each rule came from.
