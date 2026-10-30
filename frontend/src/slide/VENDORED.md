# Vendored: Frappe Suite's Slides editor

Taken from **frappe/suite** at `2831a5d` (29 October 2026),
`frontend/src/apps/slides/`. Copyright (c) Frappe Technologies Pvt. Ltd.,
AGPL-3.0, like this repository. Every file says at its top what it was derived
from. Nothing here may move to a permissive licence. The two themes, Light and
Dark, are Suite's fixtures (`suite/fixtures/presentation.json`), kept in
`onedesk/one_slide/templates/system.json`; their pictures and the Anton and
Courier Prime faces (OFL) are in `onedesk/public/slide/`.

Left out: `SlidesShell.vue`, `router.ts`, `routes.ts`, `routerState.ts` and
`runtime.ts` (`PresentationPage.vue` and `shim/routes.js` replace the shell and
its routes), `pages/Home.vue` and `components/PresentationList.vue` (OneCloud is
the list), `pages/errorPages/`, `components/Navbar.vue`,
`components/EditorNavbar.vue`, `components/SharePopover.vue` (OneCloud shares a
presentation as it shares any file) and the offline copy: `service-worker.js`,
`stores/offlineCopy.js`, `components/OfflineCopyButton.vue`,
`utils/pinTargets.ts` and `utils/serviceWorker.ts`, with their tests.

Suite's unit tests are kept beside what they test. They need vitest with jsdom.

## Seams: where Suite's shell is replaced, without editing the import

`seams.mjs` resolves these imports, from this folder only, to `shim/`:

| Import | Stand-in | Why |
|---|---|---|
| `@/boot/session` | `shim/session.js` | the desk's own session, through the kit |
| `@/stores/root`, `@/utils/documentTitle` | `shim/shell.js` | the desk has Ctrl+K and sets the title |
| `@/utils/confirmLeave` | `../sheet/shim/confirmLeave.js` | the same dialog the sheet uses |
| `@/apps/slides/router` | `shim/router.js` | the island's own router, held when the page mounts |
| `@/apps/slides/components/EditorNavbar.vue` | `shim/EditorNavbar.vue` | One's head: the way back to the folder or record, the title, whether it is saved, Theme, Export and Present |
| `@/apps/slides/stores/offlineCopy`, `@/apps/slides/utils/serviceWorker` | `shim/offlineCopy.js`, `shim/serviceWorker.js` | the desk registers no slides service worker |
| `frappe-ui` | `shim/frappe-ui.js` | every server call Suite makes by Suite's name is answered by `onedesk/one_slide/api.py`; uploads go to `api.upload`; keyboard shortcuts ask the island what has focus |
| `@/apps/slides/…` | this folder | Suite's alias for itself |

## Edits inside vendored files

Each is marked `One:` where it is.

- `stores/presentation.js`, `stores/element.js`: text is measured in
  `slideBody()` (`shim/root.js`), a shelf inside the island, because the
  editor's styles are in the island's shadow root and not on the page's body.
- `stores/copyPaste.js`, `stores/slideshow.js`, `composables/useShortcuts.js`,
  `components/DropTargetOverlay.vue`: `document.querySelector`,
  `document.activeElement` and `document.elementFromPoint` are asked of
  `slideRoot()`, and an event's target is `targetOf(e)`, the element it began
  at, which a listener on the window otherwise sees as the island's host.
- `pages/PresentationEditor.vue`: the island's height, not the screen's, and
  the body clipped, so the dimming Suite draws around the slide stays under
  the head.
- `utils/domToWebp.js`: `captureDOM` takes a scale, and a reused capture
  context takes the scale its capture asked for, so a slide can be
  photographed at twice its size for a PDF or a screen.
- `components/VideoElement.vue`: a video keeps its `length` on the element
  when it loads, so a screen can hold its slide while it plays
  (`one_slide/play.py`, `length`).
- A presentation of any size (`shim/frame.js`, `shim/resize.js`):
  `stores/presentation.js` sets the frame from the presentation before the
  canvas mounts, `stores/slide.js` fits a layout drawn for another size to it,
  `pages/Slideshow.vue` fits a slide to the screen both ways rather than by
  width alone, `components/SlidePreview.vue` takes the presentation's shape
  rather than 16:9, and `pages/PresentationEditor.vue` mounts the slide rail again
  when the frame changes, since the rail measures it once.
- Speaker notes and the presenter view (`shim/NotesDrawer.vue`,
  `shim/PresenterView.vue`, `shim/presenter.js`): `stores/presentation.js`
  sends a slide's `notes` with the rest of it, `components/Toolbar.vue`
  stands above the notes drawer, `components/PresentButton.vue` offers
  Presenter View, `stores/slideshow.js` opens it instead of the slideshow and
  closes the audience's window when its slideshow ends, and
  `pages/Slideshow.vue` plays in the audience's window without filling the
  screen until asked, tells the presenter view where it is, and goes where
  it is told.
- Rulers and guides (`shim/Rulers.vue`, `shim/guides.js`):
  `components/SlideContainer.vue` mounts the rulers over the canvas and fits
  the slide to the room between the rail and the panel when it mounts rather
  than to a fixed 900 pixels, `composables/usePanAndZoom.ts` takes that
  measure as its starting scale, `composables/useSnapping.js` snaps to the
  guides that are shown, and `stores/presentation.js` hands the guides over
  when a presentation loads.
- The master and linked layouts (`shim/master.js`, `shim/MasterLayer.vue`,
  `shim/MasterSection.vue`): `components/SlideContainer.vue` draws the master
  under the canvas and, open on a master, lays the slide out with no rail;
  `components/SlidePreview.vue` and `pages/Slideshow.vue` draw it under the
  slide's own; `components/PropertiesPanel.vue` offers Show the Master;
  `pages/PresentationEditor.vue` has no rail or notes on a master;
  `stores/presentation.js` sends and compares a slide's `hide_master` and
  `layout`; and `stores/slide.js` has a slide inserted from a layout keep
  the layout and where each element came from.
- Fonts and direction (`shim/fonts.js`, `shim/FontsDialog.vue`):
  `components/FontSection.vue` offers the workspace's fonts by group, each
  in its own face, and Add a Font; `components/ParagraphSection.vue` has
  Direction; `components/TextElement.vue` gives a box its `dir`, runs each
  paragraph the way its first letter does, and puts a list's markers on the
  side its words start. The seven Arabic families One ships are OFL faces in
  `onedesk/public/slide/fonts/`, each with its licence.
- The slide library (`shim/SlideLibrary.vue`, `shim/libraryKeep.js`):
  `components/LayoutDialog.vue` has a Slide Library tab beside the layouts,
  and `utils/slideMenu.js` offers Save to Library to whoever keeps templates.
- Data from records (`shim/data.js`, `shim/DataDialog.vue`):
  `components/TextElement.vue` and `components/TableElement.vue` fill a
  text's chips with what the records say before drawing it, and
  `stores/presentation.js` hands the sources and their values over when a
  presentation loads.
- Present Live and Views (`shim/live.js`, `shim/ViewsDialog.vue`):
  `components/PresentButton.vue` offers Present Live, `stores/slideshow.js`
  starts it and ends it with the slideshow, and `pages/Slideshow.vue` tells
  it each slide.
- `pages/Slideshow.vue` covers the whole window (`fixed`, over the desk's
  frame) rather than the island's box, so Present and the audience's window
  show only the slide when they fill the screen.
- The phone remote (`shim/phone.js`, in `shim/PresenterView.vue`):
  `pages/Slideshow.vue` draws the pointer the phone moves over the slide, as
  the presenter view tells it through `shim/presenter.js`.
- Every word a template shows, and the labels, descriptions and messages its
  scripts give, go through `__()` (`shim/words.js`, the desk's translations).
- The Builder half (stage 3 of `docs/ONESLIDE.md`), every piece of it ours in
  `shim/` and joined to Suite's files in these places:
  - `utils/shapeGeometry.js`, `utils/toolbarTools.js`, `stores/element.js`: a
    star and a block arrow, drawn as polygons on a unit box beside Suite's
    regular ones, so connectors find their outline as they do a triangle's.
  - `components/ShapeElement.vue`, `components/ShapeStyleSection.vue`: a
    shape's fill may fade into a second colour (`element.fade`, an SVG
    gradient; `shim/FadeRows.vue`).
  - `components/BackgroundSection.vue`, `SlideContainer.vue`,
    `SlidePreview.vue`, `ThumbnailContainer.vue`, `pages/Slideshow.vue`,
    `utils/color.js`: a slide's background is a colour or a
    `linear-gradient(…)` fade, drawn as `background` rather than
    `backgroundColor`, and read as its first colour where Suite asks whether
    it is dark.
  - `components/SlideElement.vue`: every element's box takes its blur, its
    free CSS and whether it is hidden (`shim/looks.js`), before Suite's own
    position, size and turn, which nothing in the free CSS can reach.
  - `components/PropertiesPanel.vue`: a **Design** and **Layers** tab
    (`shim/LayersPanel.vue`), the **Effects** section (`shim/EffectsSection.vue`),
    a named element called by its name, and a layer row free to drag.
  - `stores/commands.js`: hiding and naming are, like locking, allowed on a
    locked element.
- Icons: Suite writes `<lucide-…>` tags that its own build resolves by name.
  The island's build resolves an icon only by import, so each file that draws
  one imports it from `~icons/lucide/…`.
