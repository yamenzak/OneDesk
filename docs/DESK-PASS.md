# The desk pass

The last pass before the first tenant. Every screen, screen by screen, made
to look and behave as one product, while keeping everything frappe, erpnext
and hrms ship so that their upgrades keep reaching us. It ends lighter than
it starts.

The rules this page settles are applied through `.claude/skills/ui` and
`.claude/skills/ux`. This page is the plan and the reasons.

## What we start from

Measured on 2026-11-01, before any of it:

- **The desk loads 83 of our JavaScript files and 18 stylesheets on every
  page**, 697 KB and 189 KB raw, unminified, one request each. That includes
  every centre's code (AccessCenter, AICenter, NotificationCenter, four
  ControlCenters) whether anybody opens one or not.
- **24 stylesheets, 10,981 lines.** 225 border declarations, 87 of them
  taking off a border frappe drew. Nine different corner radii. 52
  `!important`.
- **Four kinds of dialog.** frappe's `Dialog` (our code opens 101, plus 50
  `frappe.confirm`, 31 `msgprint` and 7 `prompt`, and every one frappe,
  erpnext and hrms open), frappe's `SettingsDialog` under the centres, module
  settings and the create dialog, frappe-ui's `Dialog` in the islands (32),
  and OneCloud's own.
- **6.4 MB of built islands**, loaded per page, the two editors 412 and 368 KB.

## What it keeps

- **Frappe's parts, placed and restyled by the renderer, never redrawn.**
  A list stays frappe's ListView, a dialog stays frappe's Dialog. The window
  already works this way (`onedesk/one_interface/AGENTS.md`); this pass takes the same
  approach to dialogs, surfaces and motion. Because nothing is copied, a
  frappe, erpnext or hrms upgrade arrives in our screens by itself.
- **Seams, not forks.** We change frappe by wrapping one of its methods and
  calling the original, recorded in `scripts/overrides.py` and checked by
  `test_override_signatures.py` against the frappe we run, so an upgrade
  that moves a seam fails a test instead of a screen.
- **Frappe's own scales.** Its shadow scale (`--shadow-xs` to `--shadow-2xl`),
  its radius scale, its colour tokens and its Lucide icons. No new design
  tokens on top. What we add is decisions about which of theirs goes where.

## Decisions

Each is a recommendation until agreed.

**D1. One place decides how things look.** Borders, corners, shadows,
motion and type sizes are declared only in the window's system layer
(`public/css/one_interface/`) and the island kit (`frontend/src/kit`). A screen's
own CSS holds layout and nothing else: grid, gap, width, order. A guard
refuses a `border`, `border-radius`, `box-shadow`, `transition`, colour or
`font-size` anywhere else. Making a screen look different from the rest
means editing the system layer, where every screen changes with it. This is
how consistency stops depending on remembering.

**D2. Shadows only on what floats.** Today nothing casts one, which
leaves dialogs and menus flat on the page. A dialog uses `--shadow-xl`;
a popover, dropdown or toast uses `--shadow-md`. Nothing that sits in the
page casts a shadow, ever. This replaces the rule in `test_tokens.py`
that nothing casts one.

**D3. Three corners, by what a thing is.** A control (button, input,
select, segmented switch) is `--radius-md`. A surface that holds content
(dialog, popover, card, tile, panel) is `--radius-lg`. The window's inset
is `--radius-xl`. Avatars, badges and pills are `--radius-full`. Nothing
else, from nine today.

**D4. A border is the last way to separate two things.** First space, then
a change of surface, then a line. Regions differ by tint, not by line; a
thing has a border, a fill or a shadow, one of them; no two lines within
16px of each other; a list keeps its row dividers inside itself only.

**D5. Surfaces, so a page is neither plain white nor boxed.** The frame
is dark. The window is white. The regions beside the content (the nav
pane, the record panel, a settings rail) are on frappe's first grey
surface, with no line where they meet the content. Inside the content,
groups are separated by space. Cards are only for items: a record, a
choice with a picture, a tile with a state. Nothing is more than two
containers deep, so a box never holds a box that holds a box.

**D6. Every screen is one of six layouts.** List, form, record page, home,
centre and dialog. Each has one arrangement, so a person who has seen one
list has seen them all: where the main action is, where the filters are,
where the totals are. A new screen picks one and fills its slots; if none
fits, the layout is added to the renderer for everybody, not drawn for
one screen. Slots are the renderer's (the window's rows, the record panel's
tabs, a home's sections) and accept frappe's parts or an island.

**D7. One dialog.** Every dialog, frappe's or ours, desk or island, has one
anatomy, drawn by wrapping `frappe.ui.Dialog` once:

- **Size by content, not by caller.** Small (36rem): a confirm, a prompt,
  a message, a form of up to six fields with no tabs. Medium (48rem): a
  longer form. Large: anything with a rail (settings, centres, a create
  dialog with tabs). Full: a product inside a dialog (OneCloud's files).
- **The head** is the title, an app's mark or the record's pill when there
  is one, and close. No grey bar, no line under it.
- **The foot** holds the actions in frappe's order: secondary, then the
  primary at the end. A destructive primary is red. It stays in view while
  the body scrolls, with no line above it.
- **A confirmation asks the question and states the effect, and its button
  is the verb** (Delete, Reset), never Yes and No. `onedesk.confirm`
  replaces our 50 bare `frappe.confirm`s, and a guard keeps them out.
- **On a phone a dialog is a sheet** rising from the bottom edge.
- **A dialog over a dialog** dims the one beneath it.
- **Islands** open the same anatomy through one kit `Dialog`, and a guard
  refuses frappe-ui's `Dialog` imported anywhere else.

**D8. Motion that answers, never decorates.** Three durations: 120ms for a
press or hover, 180ms for something opening, 240ms for a panel moving. One
easing. A thing appears from where it was asked for: a menu from its
button, a panel from its edge, a dialog rising slightly as it fades in.
What changes by realtime shows it: a new row lands highlighted, a count
moves to its new value, a saved form says so where the person looks.
Loading is a skeleton in the shape of what is coming, not a spinner in an
empty page. Nothing loops, nothing bounces, and `prefers-reduced-motion`
turns all of it off.

**D9. Icons from one set.** frappe's Lucide icons only, at one stroke, 16px
by default, 14 in dense rows, 20 in heads. Icons go where they help
someone find a thing: the rail, menus, empty states, alerts, a tile's
state. Not on every button and not beside every heading. An app's
coloured mark is for the app alone.

**D10. Not made by a model.** The tells to stay away from: identical
rounded cards with soft shadows, a gradient wash, an uppercase label above
every heading, a big number with a small label and a coloured accent as
every section, emoji, decoration that encodes nothing. What makes a screen
feel considered instead is consistency, real data in it, motion that
answers the person, and one thing on the screen that matters most.

**D11. What we ship is code, not records.** Client Scripts, Custom HTML
Blocks and workspace JSON in the database are how a tenant makes One their
own, in OneStudio, and the renderer must draw theirs as natively as ours.
Our own UI stays in the repository: versioned, reviewed, held by guards,
translated, the same for every tenant, and upgraded by a deploy rather
than a migration per site. What is content rather than UI (a dashboard's
charts, number cards, a workspace) ships as fixtures from files, as now.

**D12. Lighter as it gets better.** Our desk code is one bundle and one
stylesheet (`onedesk.bundle.js`, `onedesk.bundle.css`), built and minified
by frappe's build. What only a centre or a dialog uses is loaded when it
is opened (`frappe.require`). Every stage below says what it did to the
load, measured the same way as the baseline.

## Stages

Each stage ends with its rule written into the `ui` or `ux` skill, its
guard, the gates, and its effect on load measured.

0. **Baseline.** Requests, KB and time to a usable screen on a list, a form,
   a home and a centre; screenshots of twelve reference screens on desktop,
   phone, Arabic and dark.
1. **Bundle and load late.** One bundle each; centres and module dialogs
   loaded when opened.
2. **The system layer.** Every border, corner, shadow, colour, size and
   transition moves into `css/one_interface/` or the kit; D1's guard; D2 to D4
   applied there.
3. **One dialog.** D7, for frappe's dialogs, ours, the centres and the
   islands.
4. **Surfaces and the six layouts.** D5 and D6 in the renderer.
5. **Motion, icons and loading.** D8 and D9.
6. **Screen by screen.** Every module's screens walked as their people with
   the three skills, READY's fourteen points, and what the walk finds
   fixed in the renderer where it is shared.
