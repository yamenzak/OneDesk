# OneDeck

A presentation is a file in OneCloud, the way a document is a OneWriter file
and a workbook a OneWorkbook file. OneDeck is the editor that opens it.
OneDisplay stops drawing slides of its own: a playlist links presentations
and plays them. Pictures and videos made with OneAI are made in OneDeck,
and the picture half is offered in OneWriter too.

This is the plan. Each stage is marked as it is built.

## Where the editor comes from

Frappe Suite ships Slides beside the Writer and Sheets we already took
(`frappe/suite`, `frontend/src/apps/slides`, about 29,600 lines with ~45
test files, AGPL-3.0 like this repository). It is taken the same way:

- whole, into `frontend/src/slide/`, with a `VENDORED.md` saying the commit,
  what was left out and every `One:` edit
- Suite's shell reached through `seams.mjs` and `shim/`, so a refresh is a
  copy (session, router, Drive's rename, page title, leave confirmation)
- the vendored files are held to Suite's rules, not our island guards
  (`scripts/tree.py`, `vendored`)

The older standalone `frappe/slides` repository is the same editor a year
behind; Suite's copy is the one that is maintained.

What Suite's editor has that ours does not: text with real paragraphs, lists
and per-word styling (TipTap), tables, connectors with arrowheads, image crop,
video elements with playback settings, slide transitions with matched
elements, themes and layouts, templates, a presenter mode with loop and
advance-after, copy/paste across decks, a command history with tests.

What ours has that Suite's does not, and goes in as additions (stage 3):
triangle, diamond, star and arrow shapes; two-colour fades on any fill; blur;
a free CSS box per element, re-sanitised on the server and in the player;
named, hidden and locked elements in a Layers panel. That is the Builder half
of "Slides plus Builder".

## Storage

Suite keeps a `Presentation` doctype with a child `Slide` (background,
elements JSON, transition, advance_after) and backs each with a Drive file
of mime `frappe/slides`. We keep the same shape on core `File`, as
`one_doc` and `one_sheet` do:

- a presentation is a `File` in OneCloud; its content is the presentation's
  JSON, saved through `one_deck/api.py`
- versions go in the history doctype the document and the workbook share
- a presentation filed on a record follows the record's permission, like a
  document does
- Suite's slides have no co-editing; two tabs take a lock
  (`stores/editLock.js`) and a save carries `base_modified`. We keep that.

Text elements store HTML from TipTap and tables store TipTap JSON. The server
sanitises every element's HTML on save (`frappe.utils.html_utils.sanitize_html`
with the tags TipTap writes), and refuses anything over 25 MB.

## OneDisplay

A playlist row becomes **Presentation** (a link to the File) plus the kinds
that are not slides: **Web Page** stays. **Image** and **Video** rows are
moved into a one-slide presentation each by a patch, so there is one way
to put something on screen.

A row plays the whole presentation, each slide for its own advance-after (or
the row's seconds when it has none), with its transitions where the TV can
draw them.

The TV runs Chromium 53, which cannot run Suite's editor (Vue 3, TipTap,
modern CSS). So the player is a small ES5 renderer of Suite's stored slide,
`public/js/one_deck/play.js`, replacing `one_display/blocks.js`:

- text: the sanitised HTML, inside a box with the element's styles
- shapes: Suite's rectangle, oval and line with markers, plus ours as SVG
- tables: drawn to HTML on the server when the slide is saved, so the TV
  never reads TipTap JSON
- images, videos and QR codes as they are now
- transitions: fade and slide only; the rest fall back to fade

A test runs `play.js` under node against Suite's own sample slides and under
acorn at `ecmaVersion: 5`, as `blocks.js` is tested now.

The existing designed slides are converted by a patch: each `design` becomes
a one-slide presentation filed in OneCloud under the playlist, and the row
links it. `blocks.py`, `blocks.js`, `slides.py`'s designer endpoints and
`frontend/src/display/designer/` are deleted after the patch.

## OneAI

| Job | Moves to | Also in |
|---|---|---|
| Design a slide from a sentence (`slide_design`) | OneDeck, writing Suite's element JSON | |
| Make a picture | OneDeck's Image section | OneWriter's insert menu |
| Make a video (Veo, minutes, in the background) | OneDeck; the video arrives as an element on a new slide | |
| Make music | stays in OneDisplay: it is a playlist's soundtrack, not a slide | |
| Speak (calls and announcements) | stays in OneDisplay | |

The jobs keep their names in `one_ai/jobs.py` so credits and history are
unbroken; only where they are offered moves.

## The channel builder

A channel's widget layout is a **Widget Collection**: rows of **Display
Widget**, each a kind (queue board, clock, ticker, list, number, QR code,
custom…), a box in percent of the screen, a layer, a source, the fields it
shows and its settings. Until stage 7 it had an editor of its own,
`frontend/src/display/Layout.vue`: dashed boxes dragged over a live preview,
with no snapping, layers, undo, alignment or anything but widgets on the
screen. Stage 7 opens a Widget Collection in OneDeck's editor instead.

**A screen is a presentation.** Each collection links a one-slide
presentation, its **backdrop**, made the first time **Edit Layout** is
pressed (`one_display/screen.backdrop`) and filed on the collection. The
editor opens it like any presentation, so loading, saving, the edit lock,
undo, Layers and the panel are the editor's own. OneDeck learns of screens
only through two hooks, `one_deck_loaded` and `one_deck_saving`
(`one_deck/api.py`), which `one_display/screen.py` answers.

**Widgets join the slide as it loads, and leave it as it saves.** On load,
each row becomes an element of the kind `widget` on the one slide, its box
turned from percent into the frame's pixels and its fields carried on the
element. On save, every `widget` element is written back to its row by id,
in percent, its layer its place among the widgets, and the slide is stored
without them. The slide's background is the collection's background: the
brand's colour shows when it has none, and saving that colour stores none.

**What the canvas shows.** A widget is drawn as a framed box with its name,
its kind and its source; what it shows is drawn by the screen itself, which
**Preview** opens. A live frame behind the canvas was planned, and left out:
it doubled every box and fought the canvas for the pointer.

**The panel.** With a widget chosen it is Frame and Arrange and a section
named for its kind (`shim/WidgetSection.vue`): the source, the fields shown,
a peek at what it shows now, the kind's settings and when it is shown,
moved from Layout.vue. Each change is one undoable step on the element.

**Words and pictures** from the bar are the backdrop's own elements. The TV
draws them with `play.js` on the screen's frame, transparent, under every
widget (`programme.layout` sends them as `backdrop`), so a heading sits
behind a widget whatever Layers says; in the editor they can be stacked
anywhere, and the screen lifts the widgets above them.

**The frame.** Suite's frame was 960×540 in ten places. It is now one
`frame` (`shim/frame.js`), 960×540 or 540×960, set from the collection's
orientation before the canvas mounts; a presentation always gets 960×540.

**What it is not.** A screen has one slide, so the slides rail, Theme, File,
Present, a designed slide and a video are left out of its editor. A
channel's schedule, slide playlist and music stay on the channel's form.

## Stages

1. **The editor in OneCloud.** Vendor Suite's slides, the seams, the island
   page, **New › Presentation**, save and open, lock, thumbnails. Present
   mode in the browser.
2. **History, templates, printing.** Versions in the shared history doctype,
   presentation templates, PDF export through the print service, a
   presentation filed on a record.
3. **The Builder half.** The four shapes, fades, blur, free CSS, Layers
   with names, hide and lock.
4. **OneAI.** Design a slide, make a picture (also in OneWriter), make a
   video, all through the existing jobs.
5. **OneDisplay plays presentations.** The link field, `play.js`, the
   patches that convert designed, image and video rows, the old designer
   deleted, the TV tests.
6. **OneDeck as a product.** Its mark and name in `gen_brand.py`, the
   registry next to OneWriter and OneWorkbook, READY's fourteen points,
   translations into ar and de, Help with pictures, the demo.
7. **The channel builder** on the same engine: one frame, the widget element,
   load and save through the backdrop, and one editor.

Stage 6's registry work is done for OneWriter and OneWorkbook in the same
pass, since neither is registered yet and all three share the same pieces.

All seven are built. What came after them (any size, speaker notes and the
presenter view, rulers, the master, fonts, PowerPoint, decks, data from
records, OneAI's whole decks, sharing by link and the phone remote) was
planned in the module's own scratchpad and is described in
`onedesk/one_deck/AGENTS.md`; each step is a version in its changelog.
