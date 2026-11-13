---
name: ui
description: How a screen of One is built and laid out. Load it before making or changing anything a person sees or clicks — a list, form, dialog, page, island, record page, settings section, button, column, filter, tile, card, empty state or rail row — in doctype JSON, a client script, desk JS/CSS, a manifest or a Vue island, and before calling any UI work done.
---

# UI

**Do not design. Place frappe's parts.** Nearly everything a screen needs
frappe already draws: a list, a form, a filter, a status colour, a switch, a
dialog. Find the property that makes frappe draw it, declare in the app's
manifest what the record type has, and let OneInterface draw it.

Words are the `wording` skill; whether the job gets done is `ux`; Help and
its pictures `docs`; a review of what is built `passthrough`. The standard
is `docs/STANDARD.md`, points 6 to 10; `python3 scripts/lint.py --point 7`
lists the rules that hold the look. `onedesk/one_interface/AGENTS.md` is the
full contract: the frame, the record panel, a record's head, on a phone,
Looks, Levels, Palettes, Layers, Dialogs.

## Which kind of screen

The app's manifest says how its screens are made (`ui`): **native** (the
apps on ERPNext and HRMS) is frappe's own lists and forms but for the
regions it declares; **bespoke** draws its own from frappe and frappe-ui
parts; **mixed** says which is which. Every desk page of ours is a region
of its app (`screens-declared`, point 6).

A Vue island earns its place by doing what a list or a form cannot: a file
browser, an inbox, a calendar, an editor. A table frappe's list already
draws fails that test (`list-is-frappes`, point 9). If you cannot say why a
list or a form won't do, it is frappe's. A Home follows OneBook's and
OneInventory's: figures with their trends, then real charts.

## Change the renderer, never the page

A change to a part is made where the part is drawn, for every place it
appears: `public/js/one_interface/` and `public/css/one_interface/`, or the
manifest's `interface` (an icon per tab and field, up to four head cards,
the track, a list's states, its links), which reaches the browser as
`frappe.boot.one_interface`. A screen never reaches into the frame's rows;
it hands them over with `page.interface.view({...})`. The rules hold where
each thing lives (`window-*` and `frame-*` under point 7).

## Where frappe draws it for you

| You want | It is drawn by |
|---|---|
| A list split by state | the manifest's `states`, or a Select with `in_standard_filter` |
| A column | `in_list_view`; its icon from `interface.fields` |
| A coloured state | `get_indicator`, frappe's es-badge |
| A yes/no | a Check, frappe's switch (`setting-is-a-switch`) |
| Figures on a record | `interface.cards`, at most four, from `one/head.py` |
| "New invoice from this", "its tasks" | `interface.links`, panel rows |
| Making a record | `onedesk.interface.create`, never a page of our own |
| A dialog, a button | `frappe.ui.Dialog`, `frappe.ui.button` (`dialog-is-frappes`, `button-is-frappes`) |

In an island: frappe-ui, then `@framework/ui`, then the kit in
`frontend/src/kit` (`Page`, `Section`, `Rows`, `Figures`, `Facts`, `Pill`,
`OneAlert`), and our own component only when none has it
(`island-frappe-ui`, `figures-through-kit`, `alerts-one-alert`).

## What the rules can't see

- **The address row is where you are, not what you do.** What acts on the
  record stands by its name in the head, as New stands by a list's.
- **The track is read, not clicked.** Anything that looks like a segmented
  control is read as a choice.
- **A card's title says what and over what span** ("Billed in 12 months");
  the value is only the number.
- **A box means it can be changed.** A value that cannot be changed is
  plain text. A value is never cut, and nothing changes size for what it
  holds.
- **Each row of a head holds one kind of thing,** and nothing is said
  twice, not a figure in the head and again under the tabs.
- **Hover may add, never reveal** what was always meant to be seen.
- **A border is the last way to separate things:** first space, then a
  change of surface, then a line. A line is drawn only when it joins two
  things. An empty list is not drawn at all.
- **A row that stands for a record opens it,** never an Edit button
  beside it. A handful of parallel things are tiles, each with its state as
  a badge and its one action; a list row is for many of a kind.
- **A page keeps its app's rail,** and repeats nothing the rail has.
- **Colour says only what needs somebody:** red overdue, amber waiting.
- **Not made by a model:** no cards around everything, soft shadows,
  gradients, uppercase eyebrows, emoji, an icon on every row, or anything
  that encodes nothing.
- **A mail is a screen too,** declared in `notifications.py`, drawn by
  `one/notify.py` (`one-sender`). Look at one rendered, in Arabic, at 390.

## Claude's UI habits, and what to do instead

Each happened in this app.

- **Building a screen frappe already has.** The Recycle Bin was an island;
  frappe's Deleted Document list does the job.
- **Drawing a control where a property makes frappe draw it.**
  Announcements got tabs, a redirect page and a picker; the answer was a
  Status field marked `in_standard_filter`.
- **Fixing one screen.** One pill restyled on one record; the next record
  drifted.
- **Trusting what happens to be next to it.** The bar's icons were pushed
  right by the track; the track moved and they fell left on every record.
- **Explaining the screen on the screen,** and saying things twice.
- **A dialog that sizes itself per caller,** a Yes where the verb should
  be, two close buttons because the kit and the caller both drew one. The
  kind (`one_kind`) sets a dialog's size and parts, never the caller.
- **Raising a z-index until it shows.** Name the layer (`layers-tokens`).
- **A new colour per new state.** One role, `--one-chosen`, answers every
  chosen thing (`palette-one-chosen`).
- **Filling a band with the main action's colour.** Fine in light, a
  near-white bar in dark.
- **Styling one palette and calling it done.** Give every role a garish
  value under a throwaway palette and shoot the screens: what still looks
  standard is a part no role reaches.
- **Looking at 1x on a desktop only.**

## A layout pass

Moving where things sit, not fixing a part drawn wrong.

Show two to four options as real screenshots first, light and dark, the
same crop; dark is where they are decided. Measure, don't eyeball: each
control's computed height, fill, corner, border and ink from the DOM in
one table, edges as x positions. Ask what the person meant before mocking
the wrong thing: "the bar" was the address row.

## Before calling it done

Name the renderer part that draws the thing and change it there. Then check
as much as the change is big:

- **A style rule or a part fixed:** `../../env/bin/python scripts/lint.py`,
  then shots of the part in each kind it covers, at 2x cropped, at 390, in
  dark and in Arabic. Restart the web workers first: an asset's address
  carries its hash (`one/stamp.py`), worked out once per process.
- **A screen of its own, or a part rearranged:** a layout pass.
- **How a job is done:** the `ux` skill.
- **Before a release or an upstream checkpoint:** the whole screen run,
  `node tests/browser/run.mjs` with `ONE_URL` and `ONE_DEMO_PASSWORD`
  (`ONE_SHOTS=folder` keeps a shot of each).

A rule that fails means the screen is wrong, not the rule.
