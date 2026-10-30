# OneSlide

A presentation is a file in OneCloud, the way a document is a OneWriter file
and a workbook a OneWorkbook file. OneSlide is the editor that opens it.
OneDisplay stops drawing slides of its own: a playlist links presentations
and plays them. Pictures and videos made with OneAI are made in OneSlide,
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
  JSON, saved through `one_slide/api.py`
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
`public/js/one_slide/play.js`, replacing `one_display/blocks.js`:

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
| Design a slide from a sentence (`display_design`) | OneSlide, writing Suite's element JSON | |
| Make a picture | OneSlide's Image section | OneWriter's insert menu |
| Make a video (Veo, minutes, in the background) | OneSlide; the video arrives as an element on a new slide | |
| Make music | stays in OneDisplay: it is a playlist's soundtrack, not a slide | |
| Speak (calls and announcements) | stays in OneDisplay | |

The jobs keep their names in `one_ai/jobs.py` so credits and history are
unbroken; only where they are offered moves.

## The channel builder

A channel's widget layout is a **Widget Collection**: rows of **Display
Widget**, each a kind (queue board, clock, ticker, list, number, QR code,
custom…), a box in percent of the screen, a layer, a source, the fields it
shows and its settings. `frontend/src/display/Layout.vue` edits it today:
a list to add from, dashed boxes dragged and resized over a live preview of
the screen, and a panel drawn from each kind's schema (`widgets.py`). It has
no snapping, no layers, no undo, no multiple selection, no alignment, and
nothing on the screen but widgets.

Stage 7 opens a Widget Collection in OneSlide's editor instead, so the
screen gets everything the slide got in stages 1 and 3, and the two
editors stop being two.

**What a widget is on the canvas.** A new element kind, `widget`, which
Suite's stores move, size, snap, align, group, stack, lock, hide, name and
undo like any other. It carries the row's own fields (`widget_type`,
`source`, `mapping`, `settings`, `shown`, `from_time`, `to_time`). The
canvas draws it as a framed box with its label; what it shows is drawn by
the screen itself, in one preview frame under the canvas
(`/tv?preview=<collection>&bare=1`, widgets only), as Layout.vue does now,
so there is still one renderer of a widget and it is the TV's.

**The panel.** With a widget chosen, the panel's Design tab is Frame and
Arrange (Suite's) and a **Widget** section: Layout.vue's source, fields
shown, the live "Shows now" peek and the kind's settings, moved as they
are. With nothing chosen it is the screen's: orientation and background.

**What else goes on the screen.** Text, shapes, pictures and video from the
bar, as on a slide, for the backdrop a screen has around its widgets: a
heading, a brand band, a logo. They are kept as a one-slide presentation
the collection links (`backdrop`, a File in OneCloud filed on the
collection), which the TV already draws with `play.js`. Widgets keep their
rows. The editor holds both on one canvas and saving splits them: every
`widget` element writes its row (box back to percent, `layer` from its
place in Layers), everything else writes the backdrop's one slide. On the
TV the backdrop's elements and the widgets share one stacking context, so
a heading can sit above a widget as Layers says.

**The frame.** Suite's frame is 960×540 in ten places. It becomes one
`frame` in the editor's store, 960×540 or 540×960, set from the
collection's orientation; a presentation always asks for 960×540, so
nothing about a presentation changes.

**What it is not.** A channel's schedule, its slide playlist and its music
stay on the channel's form: they are lists and times, not a layout.

### Its stages

7a. **The frame.** One `frame` in the store in place of the ten constants;
    portrait draws, snaps, thumbnails and presents. Nothing else changes.
7b. **The widget element.** The `widget` kind, its box on the canvas over
    the preview frame, **Add a Widget** in the bar, and the Widget section
    in the panel, moved from Layout.vue.
7c. **Load and save.** `one_display/layout.py` turns a collection into
    the editor's one slide and back, with the backdrop presentation; the
    TV draws the backdrop under and among the widgets; a check proves a
    round trip changes nothing and a backdrop heading shows on the screen.
7d. **One editor.** The Widget Collection form opens the builder;
    Layout.vue and its island are deleted; Help, versions, translations.

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
6. **OneSlide as a product.** Its mark and name in `gen_brand.py`, the
   registry next to OneWriter and OneWorkbook, READY's fourteen points,
   translations into ar and de, Help with pictures, the demo.
7. **The channel builder** on the same engine: 7a to 7d above.

Stage 6's registry work is done for OneWriter and OneWorkbook in the same
pass, since neither is registered yet and all three share the same pieces.
