# OneDeck

What OneDeck is, how it works and why; for agents, OneAI and us. What is
known to be wrong is `SCRATCHPAD.md`, and the Help people read is `help/`.

Presentations in OneCloud: a tender pitch, a monthly review, a training
session. Made in the desk, kept beside everything else in the company's
files, and opened by anybody the file is shared with.

## Making and opening one

**New › Presentation** in OneCloud makes one in the folder you are in and opens
it, on its title slide in the Light theme. It asks which template to start
from and what size the slides are: Wide (16:9), Standard (4:3), A4 either
way, Square, Standing (9:16), or a size of your own; a template keeps the size
it was made at unless another is chosen. **File › Slide Size** changes it
later, redrawing everything on every slide to fit, and keeps a version first.
A presentation opens wherever its file is clicked.

The path at the top says where the presentation belongs, and each step is a
way back. Click its name there to rename it. It saves itself as you work; the
head says **Saving…** and then **Saved**.

## Working on slides

The rail on the left is the slides: click one to work on it, **Add Slide** for
a new one from the theme's layouts, drag to reorder. The bar under the slide
adds text, pictures and videos, shapes, lines and connectors, and tables.
Click anything on the slide and the panel on the right shows everything it
has: frame, arrangement, font and paragraph, fill, border and shadow, crop for
a picture, playback for a video. With nothing chosen, the panel is the slide's
own: its background, how it moves to the next one, and when.

Besides Suite's shapes there are a star and a block arrow. Any fill, and a
slide's background, can **Fade** into a second colour at an angle. **Effects**
blurs anything, and its **CSS** box takes CSS for the rest: corners, blend
modes, text shadows, clip paths. What the box cannot use is listed under it
as **Not used**; position, size and turn stay with the panel above.

**Layers**, beside **Design** at the top of the panel, lists what is on the
slide, the top first. Click one to choose it, double-click to name it, drag
to restack, and use its eye and lock to hide it or keep it from being moved.
A hidden element is not drawn in the editor, the slideshow or a PDF.

**OneAI** in the head, when OneAI is on, makes three things from a sentence.
**Design a Slide** puts a new slide after the one you are on, laid out with
the business's colour; everything on it is an ordinary element to change.
**Make a Picture** puts a picture on this slide. **Make a Video** takes a few
minutes: it arrives on a new slide at the end, and you are told when it is
there or that it could not be made. Each costs credits like any OneAI request.

**Speaker Notes**, a drawer under the slide, holds what the presenter says
over it. **Theme** changes the theme the layouts come from. **Present** plays
the presentation from this slide or from the start, and can loop; **Present ›
Presenter View** keeps the notes, the next slide and the clock in this tab
and plays the slides in a window of their own for the projector.

## History, templates and paper

**File › Version History** lists what the presentation was, a version every
ten minutes of work, newest first. Name one to keep it by name; **Go Back to
This** puts the slides back as they were, and keeps what they were just
before, so going back can itself be undone.

**File › Save as Template** keeps a copy in OneCloud › Presentation Templates.
Everyone in the company may start from it: **New › Presentation** offers it,
and **Theme** lists it beside Light and Dark, so its slides become layouts.
Keeping one is OneDeck's one ability, `template` (`access.py`, the
Permission Type `slide_template` on Presentation): a Manager has it, a User
does not, and the item is left out of **File** for whoever lacks it.

**File › Export as PDF** draws every slide as it looks on the screen, a page
each, and keeps the PDF in OneCloud beside the presentation, or on its record,
and opens it. **Export as PDF with Notes** puts each slide on an A4 page above
its speaker notes.

A record's **Files** tab is OneCloud, so **New › Presentation** there files a
presentation on the record: whoever may open the record may open it.

If the same presentation is open in another tab, only one of them may change
it; the other says so and offers **Edit here**. If somebody else saved it in
the meantime, the editor says so and offers **Reload**.

## Played elsewhere

Another app may play a presentation or edit in this editor; OneDeck knows
nothing about it beyond two doors. `play.for_screen` and
`public/js/one_deck/play.js` draw saved slides anywhere the editor cannot
run, and the hooks `one_deck_loaded` and `one_deck_saving` let an app add
to what the editor opens and take back what it saves. OneDisplay uses both;
its AGENTS.md says how.

## Connections

- **From OneCloud**: A presentation is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
- **To OneCloud**: A presentation lists in its folder with the other files, and its pictures go with it to the Recycle Bin.

## Under the hood

### What it is made of

A presentation is two rows, as a document is. The **File** is what OneCloud
lists, moves, shares and deletes; its `file_url` is
`/api/method/onedesk.one_deck.api.download?presentation=…` (`api.URL`). The
**Presentation** holds the slides, a **Presentation Slide** each, in the shape
Suite's editor writes: background, elements as JSON, transition and its
duration, and advance-after.

Whether somebody may open or save a presentation is `namespace.may` on its
File, never the Presentation's own permissions, which are System Manager's
only. A picture or video on a slide is a private File kept on the
Presentation and read through `api.media`, which asks the same question; a
slide pasted from another presentation brings copies of its pictures
(`get_updated_json`). A File naming a presentation another File already holds
is a copy, so `copied` gives it a copy of the presentation and its pictures;
`file_gone` deletes the presentation with its File.

Every save passes each element through `play.cleaned`: a text box's HTML is
sanitised as any HTML from a browser is, and a picture's address that is not
ours, an asset or a page's is dropped. A save built on an older version than
the server's is refused (`save_slides`, Suite's rule), which is what the
editor's **Reload** answers.

The Light and Dark themes are Suite's fixtures, kept in
`templates/system.json` and put in place on every migrate (`setup.themes`).

### Size

A presentation's `width` and `height` are its slides' size in pixels, 960 by
540 unless it was made otherwise (`api.frame`). `shim/frame.js` sets the
editor's frame from them before the canvas mounts, and everything that draws
a slide reads the frame: the canvas, the rail, thumbnails, the camera, the
slideshow (which fits both ways), the PDF and `play.js`. `resize.py` redraws
slides drawn for one size on another: positions and sizes on their own axis,
type, borders and corners by the smaller of the two, so words never grow past
their box. `make` fits a template's first slides to the size asked,
`resize.resize` fits a whole presentation (File › Slide Size), and
`shim/resize.js`, the same rule, fits a layout from a template of another
size as it is inserted. A version keeps the size it was taken at, and going
back to it puts that size back. A PDF page is the slide at 96 pixels to the
inch, so an A4 presentation prints on A4.

### Notes and presenting

A slide's `notes` (Presentation Slide, Long Text) are plain words, kept as
typed and drawn as text wherever they show, so nothing in them can run;
`save_slides` caps them at `MOST_NOTES`. The editor's drawer is
`shim/NotesDrawer.vue`; the toolbar stands above it (`shim/notes.js`).

The presenter view is `shim/PresenterView.vue` over the editor, and the
slides play in a window `startPresenter` opens on the island's own page with
`?audience=1`, which `PresentationPage.vue` sends straight to the slideshow.
That window plays without filling the screen until **Fill the Screen** is
clicked, since a window opened by a script has no click to ask with, and it
closes itself when the slideshow ends. The two talk over a BroadcastChannel
named for the presentation (`shim/presenter.js`): the presenter says `go`,
`hello` and `end`; the slideshow answers `at` on every change of slide and
`ended` when it closes. Nothing goes through the server, so it works with no
network, and only between windows of one browser.

A phone is the remote through `remote.py`: **Phone Remote** in the presenter
view asks `pair` for a token kept in the cache for this presentation and
person (eight hours at most) and shows the QR code of `/slide-remote?t=…`
(`www/slide-remote.html`, `www/slide_remote.py`,
`public/js/one_deck/remote.js`). Phone and presenter view both join the
token's room through `realtime/handlers.js` (`onedesk_remote_join`, which
asks `admit`; the room is a hash of the token, never the token) and say
`hello`, `go`, `point` and `state` to each other with `onedesk_remote_say`,
which relays only those, small and rate-limited, and never to the sender.
Nothing the phone says reaches the server. Each side joins with a key:
the screen's own (`screen`, returned by `pair` and never in the QR code), or
the phone's, which `phone_key` gives its page and keeps in a cookie; the first phone's key
is written to the token and every other phone is turned away (`taken`), so
somebody else who scans a code on a projector drives nothing. `notes` gives
the paired phone each slide's notes only if whoever holds it is signed in
and may read the presentation. The presenter view (`shim/phone.js`)
turns `go` into its own Next and Back, sends `state` (the slide, the count,
the notes) on every change, and passes `point` on to the audience's window,
whose slideshow draws the dot over the slide (a One: edit). The pointer is
the phone's `deviceorientation` turned into a place: pressing takes the
phone's aim as the middle, and 40 degrees across or 30 down is the whole
slide; a phone that gives no reading in 600 ms, or refuses, gets a pad
instead. Closing the presenter view `unpair`s, and only the person who
paired may.

The presenter view also offers Present Live (`shim/live.js`), told every
change of slide however it was made. The mouse held on its **Now** slide
points too: it sends the same `point` over the BroadcastChannel, at most
thirty times a second, and lifting it hides the dot.

A page showing the presentation through a link pairs a phone too
(`pair_link`, **Phone Remote** in `viewer.js`), so a meeting room's
computer needs nobody signed in: the page's sealed ticket proves it passed
the link's gates, and the phone drives that page alone, which is why being
in front of it is the right to it. The token remembers the link, and
`admit` refuses it once the link is turned off or runs out. The page fills
the screen on the click that shows the code, draws the pointer over the
slide, and ends the pairing with a beacon when it is closed.

`paper.notes_pages` writes the notes pages as HTML (each slide's picture, its
number and its notes, escaped) and prints them through frappe's own
`get_pdf` on A4, so the notes are words a PDF reader finds.

### Rulers and guides

A presentation's `guides` (Long Text, hidden) are a JSON list, each an `id`,
an `axis` (`x` a line down the slide, `y` one across it) and `at`, a place in
slide pixels. `guides.cleaned` keeps at most `MOST` and drops anything off
the slide; `guides.keep` writes them without touching `modified`, since a
guide is not an edit to a slide, and `resize.resize` moves them with the
slides (`guides.scaled`). Versions do not keep them.

The editor's side is `shim/guides.js` (the list, the person's choice to see
them, kept in their user settings on Presentation, and a write 600ms after
the last change) and `shim/Rulers.vue`, drawn over the canvas in screen space
from `slideBounds`, so they follow pan and zoom without being scaled. A guide
is made by dragging out of a ruler and removed by dropping it off the slide.
Hidden, they snap nothing: `useSnapping.getGuideAlignments` (a One: edit)
adds each shown guide as one more line to snap to, and the guide itself is
the line, so `SnapGuides.vue` draws nothing for it.

The canvas fits the room between the slides rail and the panel when it
mounts (`fitted` in `SlideContainer.vue`, a One: edit), no larger than
Suite's 900 by 700, so the rulers and the slide's edges are never under a
panel.

### Decks and the library

`decks.py` builds the five decks One ships (a pitch, a project update, a
tender response, a monthly review, a training session) from eleven kinds of
slide (`KINDS`), in code, so a deck comes in the reader's language and the
business's colour and logo (`brand`, the Company's). `sync` keeps each as a
template presentation (`one-deck-<key>`, English, One's blue) so it is
listed beside the themes and Add Slide reads its slides; `api.make` builds a
deck afresh rather than copying that row, and `layouts._layouts` reads a
deck as built now, so Restyle from Layouts keeps the business's colour.

`library.py` is the slide library in Add Slide (`shim/SlideLibrary.vue`
inside `LayoutDialog.vue`, a One: edit): One's shelf is a slide of every
kind from the decks; the company's is a template presentation no theme list
shows (its name in the `one_deck_library` default), filled with Save to
Library on a slide's menu (`utils/slideMenu.js`, a One: edit) by whoever
keeps company templates. A kept slide is fitted to the shelf's size and its
pictures copied. An inserted slide remembers where it came from like any
layout.

### Data from records

`data.py`. A presentation's `sources` (JSON, `cleaned`) name records: `this`
(the record its File is attached to, else a sample while it is a
template), `record`, `linked` (a Link field of another source), or `list`
(a doctype, filters whose value may be another source's chip, an order, at
most 50 rows). A text holds chips, `{key.field}`, a list's `{key.N.field}`,
`{key.count}` and `{key.sum.field}`; they stay in the stored words and are
filled each time the slide is drawn (`evaluate`), as the reader, with
`frappe.has_permission` on each record and permlevel on each field, so a
value nobody may read is never stored and never sent. Values are formatted
by `frappe.format`, as a print formats them.

The editor gets the values with the presentation (`api._loaded` adds
`data`), asks again for chips put on since the last save (`values` with
`asked`), and follows each record it read (kit `follow`), so a saved record
redraws the slide. `shim/data.js` fills chips in `TextElement` and
`TableElement` (One: edits); a chip with no value stays visible in the
editor and is empty when presenting. Without the editor, `poured` fills the
rows `master.under` returns: the TV as the presentation's owner (a screen
has no reader), PowerPoint as whoever exports. `freeze` writes the values in
after a version; `for_each` enqueues `made_for_each`, which inserts a File
naming the presentation on each record, so the `copied` hook makes each its
own copy whose `this` is that record.

A picture bound to an image field and a slide repeated per row are not
built: a table of `{key.N.field}` chips covers the list case.

### Shared by link

**File › Share…** opens OneCloud's own sharing dialog (`onecloud_dialogs.js`,
`onedesk.cloud.share`) on the presentation's file: people inside the
workspace by *Can view* or *Can edit*, and links for anyone else.

`shared.py`, with OneCloud's links (`one_cloud/links.py`) deciding who
gets in. A presentation opened through `/s/<token>` is played on the page
(`www/s.py`, `www/s.html`, `public/js/one_deck/viewer.js`) by `play.js`, as
a screen plays it: `play.for_screen` with the records read as the link's
owner, so a guest gets words, never records. `links.get` redirects a
presentation's open to that page and downloads it as PowerPoint, filled the
same way.

Present Live (`shim/live.js`, from the Present menu) keeps the presenter's
slide in the cache (`present_live`, `stop_live`, six hours at most) and tells
the room `onedesk:slide/<name>`. A guest page joins it through
`realtime/handlers.js` (`onedesk_slide_join`) with a ticket `page` sealed when
the page passed the link's gates, because the socket server forwards only
the session cookie; `admit` checks the ticket. A page without a socket asks
`where` every four seconds. The slideshow's own page tells `live.at` each
slide (a One: edit), and the slideshow ending ends it.

Every look is a Presentation View: the link, the invited address if any,
and the seconds each slide was on screen, sent as the guest goes
(`viewed`) and read back by **File › Views** (`views`, for those who may
write). They go with the presentation (`api.file_gone`).

### PowerPoint

`powerpoint.build` writes a .pptx with python-pptx (MIT) from PowerPoint's
own pieces, so the file can be edited there: a slide is the presentation's
size at 96 pixels to the inch, on the blank layout, with its background (a
colour or a two-colour fade), the master underneath (`master.under`), and
its notes. A text becomes a text box whose paragraphs keep their alignment,
bullets and right-to-left, and whose runs keep font, size, colour, bold,
italic and underline (`paragraphs`, a small HTML reader). A shape becomes
PowerPoint's own (rectangle, rounded when it has corners, oval, triangle,
diamond, pentagon, star, right arrow) with its fill, fade, outline and
words; a line a straight connector between its ends; a picture or video
the bytes it points at; a table PowerPoint's table of its words. What has no
PowerPoint equivalent (blur, free CSS, a widget, a picture from another
site) is left out, and `export` names the slides that lost something. The
file is kept beside the presentation like the PDF (`paper.beside`). Fades
turn from a CSS angle into PowerPoint's.

`from_powerpoint.read` goes the other way, for OneCloud's Open on a .pptx
(`open_file`): the slides at the file's size, each shape as the element it
draws (a text, a shape PowerPoint and the editor both have, a picture kept
on the presentation, a table's words, a line between its ends), groups
placed where they show, and theme colours read from the master's theme and
from a shape's own style (`fillRef`, `lnRef`, `fontRef`), which python-pptx
leaves unread. A chart, SmartArt or a video is left out and the slide named.
The presentation is made beside the file and remembers it (`from_file`), so
opening the file again opens the same one. Sizes a placeholder inherits from
its layout are guessed (44pt for a title, 24 for a body), and bullets a
layout gives are read as plain paragraphs.

### On the drive

On the WebDAV drive (`one_cloud/dav.py`) a presentation is "Name.pptx",
like a workbook's .xlsx and a document's .docx. `drive.pptx` is
`powerpoint.build` for the reader (chips filled as they may see them), kept
in redis per presentation, master and reader until either changes. A
PROPFIND never builds it: the length listed is the File's `file_size`, or
the built file's when one is already kept, and a GET or HEAD builds it. The
etag and last-modified are the later `modified` of the presentation and its
master (`drive.stamp`), so they stay put until it changes. `build` names each
master shape after its element (`master-<id>`), and `drive.write`, a PUT,
reads the file with `from_powerpoint.read(mastered=True)`, which leaves those
shapes to the master. It replaces the slides, keeps a named version first
("Before a save from the drive"), and writes the slides that lost something
into `lost`, which the editor shows on opening and its next save clears. A
file python-pptx cannot open is a 415; a presentation with `sources` is a
403, since its chips would come back as their values. Slide ids,
transitions, animations, hidden elements and anything `build` leaves out
are not in the file, so they do not survive a save from outside.

### Fonts

`fonts.py` is the workspace's font library, which every editor and the TV
read. One ships seven Arabic families (IBM Plex Sans Arabic, Noto Naskh
Arabic, Noto Kufi Arabic, Cairo, Tajawal, Almarai, Amiri, all OFL, licences
beside them) as app assets in `public/slide/fonts/`, declared with their
Arabic and Latin subsets in `public/slide/fonts.css`; `SHIPPED` is the list
the picker groups, the faces every computer has included. A workspace's own
fonts are Files in OneCloud › Fonts, so their bytes are wherever its other
files are (R2 once linked). Each File is named `<Family> <weight>[ Italic]`
when it is added, read from a TrueType or OpenType file's name table where
it can be; `fonts.css` declares them at `fonts.face`, our own address, which
streams the bytes with an immutable cache because a browser loads a font
from another site only with CORS, and the address carries the content's
hash. Both are guest-readable: fonts are no secret, and a screen signs in as
nobody. The TV's worker keeps the files.

Adding is for whoever keeps company templates (`slide_template`):
`fonts.upload`, or `google_search` and `google_add` through
`services.call("google_fonts", …)`. Google's catalogue is asked once a day
and a family's TTF files once, by our server; nothing is fetched from Google
when anyone reads. The service, its Google use and the privacy clause are in
`trust.py`.

A text paragraph takes its direction from its first letter
(`unicode-bidi: plaintext` in `TextElement.vue` and `play.js`); a box's `dir`
(the panel's Direction) sets it one way. `api.make` in a workspace whose
language is Arabic starts the words right to left in IBM Plex Sans Arabic
(`fonts.arabic`).

`api.media` and `api.shown` return their response (frappe sends one only
when the method returns it) and redirect to R2 for a file kept there.

### Master and layouts

A master is a second Presentation of one slide, `master_of` the one it
belongs to and no File of its own; `api._file` answers for it with its
presentation's File, so the editor opens it at `/desk/presentation/<master>`
like any other and Suite's whole save path works on it unchanged
(`master.edit` makes it blank the first time). `api.get` hands the editor
`master`, its elements; `shim/master.js` puts them under every slide that
does not set `hide_master`, with ids of their own (`master-<id>`) and each
`field` text (`number`, `date`) filled for that slide: `MasterLayer.vue`
under the canvas, `SlidePreview.vue` (rail, camera, PDF, presenter) and
`Slideshow.vue`. The TV gets it from `master.under` in `play.for_screen`,
and PowerPoint will from the same. A master goes with its presentation
(`file_gone`), comes with a copy or a template (`master.copy`), and is
resized with it.

A slide inserted from a layout keeps `layout` (`<template>:<client_id>`)
and each element `from`, the layout element's id: `getNewSlide` in
`stores/slide.js` (a One: edit) and `api._first_slides` for a new
presentation. `layouts.restyle` puts every such element back where its
layout has it, in its look, with the slide's own words poured into the
layout's first paragraph (`layouts.poured`; a list keeps its own markup)
and its own picture kept, and the slide takes the layout's background. A
version is kept first. Elements added to a slide since are left alone, and
one the slide deleted does not come back.

### The Builder half

A fade, a blur, free CSS, a name and whether an element is hidden are kept
on the element as Suite keeps everything else (`fade`, `blur`, `css`, `name`,
`hidden`), and a fade on a slide's background is the background itself, a
`linear-gradient`. `css.json` is the one list of what free CSS may say: the
editor reads it to draw (`shim/looks.js`) and `play.cleaned` reads it again
on every save, so a declaration that is not on it, or a value that loads
anything (`url(`, `@import`, `expression`), never reaches a screen. The
editor's half is in `frontend/src/slide/shim/`; `VENDORED.md` lists where it
joins Suite's files.

### Things that come and go

An element's `motion` says how it comes in and goes out: `in` (Fade, Fly In,
Zoom, Rise), `out` (Fade, Fly Out, Zoom, Sink), `from` (the side it flies),
`start` (With the Slide, On Click), `wait`, `speed`, `stay` and `again`.
`motion.json` is the one table: `play.motion` keeps only what it names on
every save, the editor's **Motion** section (`shim/MotionSection.vue`) and
its slideshow (`shim/motion.js`) read it, and `play.js` carries a copy that a
test holds equal. A moving element sits on a box as large as the slide and
is moved by one keyframe track of `transform` and `opacity` only, named by
the element so a click that only unpauses it does not restart it; a zoom
grows from the element's middle.

In the slideshow a click, a key, the presenter view's **Next** (which sends
`step` to the audience's window) and the phone remote bring in the next
element waiting for a click before the slide moves on (`clicked`,
`clickWaiting`). A shared link steps through `play.step`. A guest following
Present Live, and a screen in OneDisplay, draw with `auto`: nobody clicks, so
each waiting element comes a second after the one before it. A slide entered
by Magic Move keeps its own fade and does not move its elements.

### OneAI

`agent.py`. The jobs are OneDeck's own (`slide_design`, `slide_picture`,
`slide_video` in `one_ai/jobs.py`). A design comes back as blocks placed in
percent of the slide, told the presentation's size, and `convert.py`
redraws them as Suite's elements on that frame: text as Suite's paragraphs,
shapes as Suite's or ours, a fade as a fade, a QR code as a picture of one
(`one/qr.py`). A picture is kept on the presentation as an upload is; a
video is made in the background, put on a slide of its own across the whole
of it, and whoever asked is told (`tell.py`; the kinds are with OneCloud's
in `notifications/one_cloud` until OneDeck is a module of its own).
OneDoc's **Make a Picture with OneAI** is the same picture job
(`one_doc/api.py`, `make_picture`).

In OneAI's panel (Una's tools, since OneDeck has no agent of its own), `page`
tells the model which presentation and slide are open (the editor's
`aiSees`), the record it is filed on, its chips, the kinds of slide and the
words each takes (`decks.WORDS`) and One's decks as recipes. Its tools are
`read_presentation`, and three cards: `draft_deck` (slides built by
`decks.build` from the words given, at the presentation's size, after the
slides there are or in place of a blank first one), `write_slide` (new
words poured into each text's look, `layouts.poured`) and `remake_slide`
(a slide built again as another kind). `approved` (from
`one_studio/ai_setup.apply`) keeps a version first and tells an open
editor to reload (`one_deck_written`). The OneAI menu's panel requests
open the panel with a question (kit `askOneAI`). The model reads records
with OneAI's own tools; nothing here reads for it.

### Drawn without the editor

`public/js/one_deck/play.js` draws a saved slide again in ES5, for a
browser too old to run the editor: text as its sanitised HTML, shapes as SVG
with Suite's geometry and ours, fades, blur, free CSS, crops, videos;
eight-digit colours as `rgba()`, and every number, colour and address
checked again. It empties a slide's videos when the slide is taken off
(`release`), since an old browser holds a decoder until then.
`play.for_screen` gives a presentation's slides in that shape: hidden
elements left out, tables drawn to HTML, pictures and videos at `api.shown`
addresses sealed with the site's key (`play.seal`) for a reader signed in as
nobody, each slide's own transition, and how long it stays (`play.length`):
a video that does not loop is watched to its end first, since the editor
keeps a video's `length` when it loads it, then the slide's Advance.

### History, templates and paper

`versions.py`. Before `save_slides` writes, what the slides were is kept as a
**Presentation Version** unless the last unnamed one is under ten minutes old;
a hundred unnamed ones are kept, and every named one. `restore` keeps the
current slides as "Before going back" and writes the version's in; the
editor then opens the presentation again (`shim/EditorNavbar.vue`, `reload`).

`templates.py`. A template is a Presentation with `is_template` and a public
File in Presentation Templates, its pictures copied onto it. `get_templates`
lists Suite's two themes and every template the reader may open.

`paper.py`. The editor photographs each slide in Suite's own preview at twice
its size (`shim/SlideCamera.vue`, modern-screenshot), and Pillow makes the
pictures a PDF a page each.

### The editor

`frontend/src/slide/` is Frappe Suite's Slides editor, taken whole
(`VENDORED.md` says what was left out, where Suite's shell is replaced, and the
edits inside its files). `PresentationPage.vue` is ours: it opens the
presentation the route names on the island's own router, after asking what
the reader may do with it. The head is ours too (`shim/EditorNavbar.vue`).
Every server call the editor makes by Suite's name is answered by `api.py`
under the same name (`shim/frappe-ui.js`).

The island draws inside a shadow root, which Suite's editor was not written
for: it measures text on a shelf inside the island and looks things up in the
island, not the page (`shim/root.js`).

### The name before

The folder was `one_slide`, the module One Slide and the app OneSlide until
13 November 2026. `patches/slide_is_deck.py`, first in patches.txt, renames
the Module Def and the roles OneSlide User and OneSlide Manager with frappe's
`rename_doc` (merged into what a migrate already made), which moves every
Link to them. It then moves what holds the names as plain text: Workspace
Sidebar's and Block Module's `module`, Record Head's folder, Patch Log and
Scheduled Job Type rows naming the old path, `one_app` on Role and
Notification Type, every saved default whose key names `one_slide` or
`oneslide` (tours seen, versions read, the slide library, abilities
settled), and every Icon field that says `oneslide`; the old Custom Icons go.
`onedesk/one_slide/__init__.py` makes any old dotted path import the new
module for one release (RUN.md D7).

Kept on purpose: a presentation's File URL (`api.URL`) and a picture's or
video's on a slide (`api.MEDIA`, `play.MEDIA`) keep the `one_slide` address,
since every File and every slide holds them; hooks.py's
`override_whitelisted_methods` sends them, and a screen's cached
`api.shown` and `fonts.face`, here for good. The seals of a screen's address
(`play.seal`) and of a live presentation's ticket (`shared._signed`) keep
`one_slide` in what they sign, so links and screens already given one keep
working. `public/slide/` (the editor's fonts and layout pictures, at
`/assets/onedesk/slide/`) and `frontend/src/slide/` (Suite's Slides editor,
taken whole) are named for what they hold, and saved slides name the first.
