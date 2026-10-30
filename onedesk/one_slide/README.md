# OneSlide

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

**Theme** changes the theme the layouts come from. **Present** plays the
presentation from this slide or from the start, and can loop.

If the same presentation is open in another tab, only one of them may change
it; the other says so and offers **Edit here**. If somebody else saved it in
the meantime, the editor says so and offers **Reload**.

## What is not built yet

History, templates of your own, printing to PDF from the server and
presentations filed on a record come in the next stage (docs/ONESLIDE.md).
Two people cannot work on one presentation at the same moment.

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
