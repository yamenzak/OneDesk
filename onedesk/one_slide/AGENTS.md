# OneSlide

What OneSlide is, how it works and why; for agents, OneAI and us. What is
known to be wrong is `SCRATCHPAD.md`, and the Help people read is `docs/`.

Presentations in OneCloud: a tender pitch, a monthly review, the slides a
screen in the showroom plays. Made in the desk, kept beside everything else in
the company's files, and opened by anybody the file is shared with.

## Making and opening one

**New › Presentation** in OneCloud makes one in the folder you are in and opens
it, on its title slide in the Light theme. A presentation opens wherever its
file is clicked.

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

**Theme** changes the theme the layouts come from. **Present** plays the
presentation from this slide or from the start, and can loop.

## History, templates and paper

**File › Version History** lists what the presentation was, a version every
ten minutes of work, newest first. Name one to keep it by name; **Go Back to
This** puts the slides back as they were, and keeps what they were just
before, so going back can itself be undone.

**File › Save as Template** keeps a copy in OneCloud › Presentation Templates.
Everyone in the company may start from it: **New › Presentation** offers it,
and **Theme** lists it beside Light and Dark, so its slides become layouts.
Keeping one is OneSlide's one ability, `template` (`abilities.py`, the
Permission Type `slide_template` on Presentation): a Manager has it, a User
does not, and the item is left out of **File** for whoever lacks it.

**File › Export as PDF** draws every slide as it looks on the screen, a page
each, and keeps the PDF in OneCloud beside the presentation, or on its record,
and opens it.

A record's **Files** tab is OneCloud, so **New › Presentation** there files a
presentation on the record: whoever may open the record may open it.

If the same presentation is open in another tab, only one of them may change
it; the other says so and offers **Edit here**. If somebody else saved it in
the meantime, the editor says so and offers **Reload**.

## On a screen

A OneDisplay slide playlist plays presentations: a row links one, and every
slide of it plays on the screens in turn, each for its own **Advance** time
or the row's seconds. **New Presentation** on a playlist makes one filed on
the playlist and opens it here. What you change is on the screens at their
next look.

## A screen's layout

A OneDisplay widget collection is edited here too: **Edit Layout** opens its
backdrop, a one-slide presentation filed on the collection, at the screen's
shape. Its widgets are elements on the slide, **Add a Widget** adds one, and
the panel shows a chosen widget's source and settings. The slides rail,
Theme, File and Present are left out. How it works is docs/ONESLIDE.md, The
channel builder; this module only calls the `one_slide_loaded` and
`one_slide_saving` hooks, and draws the frame `shim/frame.js` gives.

## Connections

- **From OneCloud**: A presentation is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
- **To OneCloud**: A presentation lists in its folder with the other files, and its pictures go with it to the Recycle Bin.

## Under the hood

### What it is made of

A presentation is two rows, as a document is. The **File** is what OneCloud
lists, moves, shares and deletes; its `file_url` is
`/api/method/onedesk.one_slide.api.download?presentation=…` (`api.URL`). The
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

### OneAI

`ai.py`. The jobs are OneDisplay's (`display_design`, `display_picture`,
`display_video` in `one_ai/jobs.py`), so their credits and history carry on.
A design comes back as OneDisplay's blocks, in percent of a 1920 by 1080
screen, and `convert.py` redraws them as Suite's elements on its 960 by 540
slide: text as Suite's paragraphs, OneDisplay's shapes as Suite's or ours,
a fade as a fade, a QR code as a picture of one. Stage 5 of docs/ONESLIDE.md
turns every designed slide a playlist holds into a presentation with the
same function. A picture is kept on the presentation as an upload is; a
video is made in the background, put on a slide of its own across the whole
of it, and whoever asked is told (`tell.py`; the kinds are with OneCloud's
in `notifications/one_storage` until OneSlide is a module of its own).
OneWriter's **Make a Picture with OneAI** is the same picture job
(`one_doc/api.py`, `make_picture`).

### On a screen

A screen is a 2017 TV that cannot run this editor, so `public/js/one_slide/
play.js` draws a saved slide again in ES5: text as its sanitised HTML,
shapes as SVG with Suite's geometry and ours, fades, blur, free CSS, crops,
videos; eight-digit colours as `rgba()`, and every number, colour and address
checked again. `play.for_screen` gives a screen a presentation's slides with
hidden elements left out, tables drawn to HTML, and pictures and videos at
`api.shown` addresses sealed with the site's key (`play.seal`), since a
screen signs in as nobody. A playlist row links the presentation's File,
offered by `api.search` only to who may open it and checked again when the
playlist is saved. OneDisplay's AGENTS.md has the rest.

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
pictures a PDF a page each. The same pictures are what a screen plays
(stage 5 of docs/ONESLIDE.md).

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
