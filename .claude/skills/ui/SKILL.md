---
name: ui
description: How a screen of One is built and laid out. Load it before making or changing anything a person sees or clicks — a list, form, dialog, page, island, record page, settings section, button, column, filter, tile, card, empty state or rail row — in doctype JSON, a client script, desk JS/CSS, the registry or a Vue island, and before calling any UI work done.
---

# UI

**Do not design. Place frappe's parts.** Nearly everything a screen needs,
frappe already draws: a list, a form, a filter, a status colour, a switch, a
dialog. The job is to find the property or component that makes frappe draw
it, say in the registry what this record type has, and let OneInterface draw
it where it goes. Drawing it ourselves is the last resort, and every time it
was the first resort here it was wrong.

Words on the screen follow the `wording` skill; whether the job gets done is
the `ux` skill. Load all three. Help pages and their pictures are the
`docs` skill; a review of screens already built is the `passthrough`
skill.

## Change the renderer, never the page

A change to a part is made where the part is drawn, for every place it
appears. Restyling one pill on one screen is how drift starts.

- **How every screen looks** lives in `public/js/one_interface/` and
  `public/css/one_interface/`, nowhere else.
- **What one record type has** (an icon per tab and field, head cards, its
  track, its list's states, its shortcuts) is declared in
  `ready.MODULES[module]["interface"]` and reaches the browser as
  `frappe.boot.one_interface`. Nothing page-specific is written outside the
  registry, and the engine names no doctype (`test_interface_frame.py`).
- **A screen never reaches into the frame's rows.** It tells the frame what
  it has: `page.interface.view({ primary, commands, menu, controls, views, search, row, status })`.

## Look, Theme, Palette

Three layers, three words; never call one by another's name.

- **Look**: the design language. `look.js` declares them
  (`onedesk.interface.LOOKS`), boot picks one (`one_look`, Canvas by
  default) and sets `data-one-look` on the page. A look is a stylesheet
  scoped to that attribute plus the renderer parts it turns on
  (`onedesk.interface.uses(part)`: `head`, `strip`, `thread`, `quiet`,
  `icons`). Classic turns none on. Dialogs are the kit's in every look.
- **Theme**: frappe's light, dark or automatic. Every look defines its
  tokens for both.
- **Palette**: every value a look draws with, colour, corners, shadows,
  type, set on `data-one-palette`. Standard is frappe's own; Sand is the
  one One ships, and the default. A palette is a full set of roles (below), never a hue.
  Each person picks look, theme and palette in Appearance (`theme.js`); a
  picture of the window there is a `.one-sample`, which takes the roles
  afresh, so draw any preview of a theme or palette with one.

The HTML is the same in every look. A look that needs a different
arrangement adds a part to the renderer; it never forks it.

## Which kind of screen

1. **Frappe's own list or form, on the window.** The default for nearly
   everything. What we add is a registry entry, a column, a filter, a
   figure, a button, a client script.
2. **A Vue island**, only for what is genuinely more than a list or a form:
   a product (OneMail, OneCloud, OneCalendar), an app's home, an editor.
   Declared in `tiers.SCREENS` with the reason. An island page carries the
   stamp until the walk replaces it with a framework screen.

If you cannot say why a list or a form won't do, it is 1.

## Where frappe, or the registry, draws it for you

| You want | It is drawn by |
|---|---|
| A list split by state | the registry's `states` (the strip over the rows), or a Select with `in_standard_filter` |
| A column | `in_list_view`; its icon from the registry's `fields` |
| A coloured state | `get_indicator`, drawn as frappe's es-badge |
| A yes/no | a Check: frappe's switch |
| Figures on a record | the registry's `cards` (at most four), from `one/head.py`'s rows |
| A record's progress | the registry's `track` |
| "New invoice from this", "its tasks" | the registry's `links`, drawn as panel rows |
| Making a record | `onedesk.interface.create`, never a page of our own |
| A record's files | OneCloud's mark at the bar's end, never a Files tab |
| A dialog | `frappe.ui.Dialog` and frappe's helpers; the kit sizes and dresses it |
| A button | `frappe.ui.button` / frappe-ui `Button` |

In an island: frappe-ui, then `@framework/ui`, then `frontend/src/kit`
(`Page`, `Section`, `Rows`, `Figures`, `Facts`, `Pill`, `OneAlert`), and
our own component only when none of those has it. A figure is the kit's
`Figures` on homes and record heads alike.

## The record (Canvas)

Top to bottom: address bar, actions bar, then the head, the tabs, the sheet.

- **The head is the record's Overview.** Picture (frappe's own wrapper,
  moved, so upload still works), name, state pill, the ID on a quiet line
  under the name only when it is not the name, the track, then up to four
  cards of one size. The panel loses its Overview tab; nothing is said
  twice.
- **The track is read, not clicked:** a filled tick per step done, an open
  dot where it stands (red when late), a dashed line to steps not reached,
  each step's date under it. Anything that looks like a segmented control
  is read as a choice.
- **A card's title says what and over what span** ("Billed in 12
  months"); the value is only the number.
- **One sheet per tab.** Sections are space and a hairline, never a card
  each; a heading sits over its fields in one grid. A tab with nothing in
  it goes, and the record opens on the first tab that has something.
- **A box means it can be changed.** An editable field shows its outline at
  rest; one that cannot be changed is plain text. On a saved record an
  empty field nobody must fill waits behind Show N Empty Fields.
- **A value is never cut, and nothing changes size because of what it
  holds.** Plain text wraps; a box keeps its width, ends in an ellipsis and
  shows the whole value on hover and while typing. (A list's resizable
  column is the reader's choice, and may cut.)
- **The panel sits on the canvas**, outlined, not filled. Assign,
  Attachments, Tags, Share, the registry's shortcuts (a trailing mark says
  what happens: + makes, an arrow opens a list, a chevron a dialog), then
  Activity, Mail, Connections. It never grows past the window; only the
  activity scrolls inside it.
- **Activity is one thread.** One entry per person per hour ("You changed 5
  fields", opening to `field old → new`), submit and cancel as verbs, empty
  to empty dropped, long text "edited". A comment carries a 20px face and
  is plain text; a change is a small hollow dot.

## The list (Canvas)

- **Each row of the head holds one kind of thing.** The address island:
  where you are, refresh, search, the view's … menu. Under it, what
  narrows: frappe's quick filters from the edge, Filter and the sort as
  icons at the end. The heading: icon, name, New beside it, the views at
  the far end. Then the states, then the rows. Nothing is said twice (the
  count is the All tab's, not the heading's).
- **A look places, the Frame fills.** The Frame keeps its command groups
  and its views by reference (`win.group(name)`, `win.ways_slot()`), so a
  look moves them (`list.place`) and the Frame still fills them where they
  are. Never copy a frappe node to show it twice; move it.
- **One edge** (`--one-inset`) for every row of the window; only a box
  (an island, the head pill, a row) sets its own content in.
- **A row's activity is always shown** in quiet ink at its end. Hover may
  add, never reveal what was always meant to be seen. Bold for an unread
  record is frappe's and stays.

## The bars and controls

- **Every control is 28px,** `--one-radius-control`, 16px icons, 13px
  words, on `--one-head-button-bg`. The island's own controls (refresh,
  search, the menu) are on the island's `--one-address-bg`.
- **One colour for what is chosen:** the side pane's row, the state tab, the view and the
  column heads' pill all read `--one-chosen` (New's colour washed into the
  canvas). The main action is the only solid thing; a solid band of it is
  a bright bar in dark.
- **Three corners, by what a thing is:** a control
  (`--one-radius-control`), a surface or island (`--one-radius-sheet`), a
  pill for counts, states and the column heads (`--radius-full`).
  frappe's checkbox keeps its own: a palette's rounder one makes a 14px
  box a circle.
- **One pill:** frappe's es-badge at its small size, for every state, tag
  and count.
- **A group is one control.** Filter and its clear, sort and its field, the
  view switcher: one fill, inner corners square, a hairline between
  parts. A field's own switch is a quiet icon inside it.
- **Frappe's `.icon` has `margin: auto`.** Any row of ours that puts an
  icon beside text resets it (`margin: 0`, `flex: none`).

## The record (Canvas), as rendered

- **One material:** islands, the side pane, sections, head cards and the
  panel are all `--one-sheet`/`--one-head-bg` on the canvas. Each section is
  its own card; there is no sheet around them.
- **The head is one row** when the commands fit beside a readable address;
  the track stands across from the name.
- **A field is a control:** filled, no edge, the focus edge only while
  typing. A read-only value is plain text.
- **Island record pages (Item, Project, Task) are not on this yet.** They
  draw their own head, panel header and star; they wait for their own
  passover, with the user, and must take the address-row star, the pill
  tabs, the section cards and the filled fields from here when they do.

## How a layout pass is done

- **Show before building.** Two to four options as real screenshots, side
  by side, light and dark, the same crop. A colour that reads well in light
  is often a glaring bar in dark; that is where options are decided.
- **Measure, don't eyeball.** Read every control's computed height, fill,
  corner, border, font size and ink from the DOM in both themes and line
  them up in one table; the odd ones out are the findings. Edges are
  checked as x positions, not by eye.
- **Ask what the person meant before mocking the wrong thing.** "The bar"
  was the address row, not the top bar; one question costs less than a
  sheet of the wrong options.

## Surfaces

- **Only the work is a sheet.** The panel and the record's alert sit on the
  canvas; a second white surface beside the record competes with it.
- **A line is drawn only when it joins two things.** No rule down a feed,
  no border under a head that already has space.
- **One edge per column.** Head, alert and sheet share a gutter; panel rows,
  tabs, comment box and activity share theirs. Framework padding (`.col`)
  is zeroed by the renderer, not page by page.
- **Roles, not the scale,** in the frame and Canvas: `--one-sidebar-active-bg`,
  `--one-primary-bg`, `--one-radius-control`, never `--surface-gray-2` or
  `--radius-md`. A new part gets a role in `tokens.css` (Standard's value)
  and a value in every palette in `palettes.css`, in the same commit;
  `test_palettes.py` fails otherwise. Elsewhere, frappe's tokens:
  `--ink-*`, `--surface-*`, `--outline-*`, `--radius-*`, 1px borders. No
  shadows, literal colours or Tailwind palette classes. A token that does
  not exist fails silently, so `test_tokens.py` checks each one resolves.
- **Frappe's parts follow through bridges, not edits.** Under a palette,
  tokens.css points frappe's named steps, its component variables, the
  radius scale, shadows and font at the roles; islands get the same through
  the sheet look.js adopts. A palette writes against the raw `--gray-*`,
  never a named step, or it reads itself.
- **Audit a palette with a loud one.** Give every role a garish value under
  a throwaway palette and shoot the screens: whatever still looks Standard
  is a part no role reaches. Bridge it, then shoot again.
- **Layers by name.** A z-index is `var(--one-layer-*)` (sticky, panel,
  frame, backdrop, dialog, menu, tooltip, toast, tour), `calc()` of one
  plus a small step, or a local order under 100 inside its own part. Never
  9999. `test_layers.py`; the ladder is in AGENTS.md, Layers.
- **Colour only says what needs somebody:** red overdue, amber waiting.

## Dialogs

Every dialog is frappe's, told its kind (`one_kind`, else the kit infers
it); the kind sets its size and parts, never the caller.

| Kind | Opened by | Size |
|---|---|---|
| ask | `onedesk.interface.ask`, `frappe.confirm`, `warn`, `prompt` | small |
| tell | `frappe.msgprint` | small |
| task | any other `frappe.ui.Dialog` | medium |
| create | `onedesk.interface.create` | medium |
| centre | a `SettingsDialog` | large |

- **The header is where you are and the window:** Back once a page deep
  (`panel.one_back`), the title, its state; Help (`dialog.one_help`),
  Enlarge and Close. Only `dialogs.js` draws these; a centre or a creator
  asks for them and never draws its own. Nothing you *do* is in the header.
- **The footer:** what is still needed on the left (`dialog.one_need`), the
  verbs on the right, the main one last and solid, red only when it cannot
  be undone.
- **Ask and Tell lead with a round mark;** the question is the title, the
  effect the line under it, the verb names the act.
- **Enlarge fills the window, not the browser.** A centre opens at the size
  it was left at.
- **Making a record has three shapes in one dialog.** Standard: the
  record's own fields. Search first: when the thing exists out there (a
  place, a company), a search fills the rest. Kind first: when kinds mean
  different things, cards first, then that kind's few answers. A creator
  decides the body, never the chrome.
- **A new record's size follows its shape** (`dialog.one_shape`): with a
  rail, wide enough for two columns beside it; without, the form alone and
  as tall as its fields; no tabs and at most six fields, small and one
  column.

## Mails

A notification is a screen too, read in somebody's inbox. Every mail One
sends is drawn by `one/notify.py` `compose` (`templates/emails/one_mail.html`)
and laid in one frame (`templates/emails/standard.html`, ours), so a module
declares a mail and never draws one.

- **Declared, never hand-built.** A module's `notifications.py` `TYPES`
  says when it goes, to whom, its subject, message and button; no
  `frappe.sendmail` with HTML of our own.
- **The frame:** the workspace's name and logo over a white card on a grey
  page, 560 wide; in the card the heading (what happened), the message, one
  button, and under a hairline why this person got it; the footer under the
  card. A mail One sends about itself wears One's mark instead
  (`ones`).
- **One button,** a verb and a noun (Review Request), in the company's Brand
  Colour, opening the record. A second thing to do is a second mail or
  nothing.
- **Facts on one line,** separated by a middle dot: `Due 20 Oct · Mansour
  Villa`. No table for layout, no picture but the logo, no colour but the
  button's.
- **Light only** (`color-scheme: light`): mail clients invert dark mail
  badly. Right to left for a reader of Arabic, decided by the reader's
  language, not the sender's.
- **Words by the `wording` skill:** the subject says what happened to
  what, the message what to do next.

Look at a mail before calling it done: render the type for a demo record in
English and Arabic, and read it at phone width.
`tests/guards/test_notifications.py` holds every type declared and worded.

## Claude's UI habits, and what to do instead

Each happened in this app.

- **Building a screen frappe already has.** The Recycle Bin was an island;
  frappe's Deleted Document list does the job.
- **Drawing a control where a property makes frappe draw it.**
  Announcements got tabs, a redirect page and a picker; the answer was a
  Status field marked `in_standard_filter`.
- **Fixing one screen.** One pill restyled on one record; the next record
  drifted. Change the part where it is drawn.
- **Trusting what happens to be next to it.** The bar's icons were pushed
  right by the track; the track moved and they fell left on every record.
- **Explaining the screen on the screen,** and saying things twice: a
  heading repeating the rail row, a figure in the head and in the panel.
- **Decoration.** Cards around everything, separator lines, shadows,
  eyebrow labels, an icon on every row.
- **A dialog that sizes itself per caller,** a Yes/No where the verb should
  be, two close buttons because the kit and the caller both drew one.
- **Looking at 1x on a desktop only.**
- **Raising a z-index until it shows.** The search box drew over a dialog
  because a tour's 100004 outranked it; name the layer instead.
- **A new colour per new state.** The chosen tab, the chosen view and the
  head pill each got their own; one role (`--one-chosen`) answers all of
  them.
- **Filling a band with the main action's colour.** Fine in light, a
  near-white bar in dark; wash it into the canvas instead.
- **Styling Standard and calling the palette done.** Sand's widgets kept
  Standard's white until the islands and frappe's menus were bridged.

## Before calling it done

1. Sign in as the demo user with the role (huda the books, samir projects,
   karim stock, omar sales, mariam HR, tariq and nadia employees, wsadmin
   the administrator) and finish the job: make the record, not just open
   one that exists.
2. Screenshot it (`ONE_SHOTS=folder node tests/browser/run.mjs <screen>`
   keeps one per screen) and look at the part you changed at 2x, cropped
   to it. Then 390 wide, Arabic (right to left), dark.
3. Read every string with the `wording` skill.
4. Run the UI guards, which take seconds:

       python3 -m pytest -q tests/guards/test_tokens.py tests/guards/test_interface_frame.py \
         tests/guards/test_interface.py tests/guards/test_islands.py tests/guards/test_layout.py \
         tests/guards/test_shell.py tests/guards/test_record_page.py tests/guards/test_rail.py \
         tests/guards/test_icon_margins.py tests/guards/test_overrides_recorded.py \
         tests/guards/test_palettes.py tests/guards/test_layers.py

A guard failure means the screen is wrong, not the guard.

`onedesk/one_interface/AGENTS.md` is the full contract (Looks, Palettes, Layers,
Dialogs, the record panel, the guards) and `docs/UI-NOTES.md` the walk each rule came
from.
