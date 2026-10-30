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
