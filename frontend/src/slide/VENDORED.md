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
- Every word a template shows, and the labels, descriptions and messages its
  scripts give, go through `__()` (`shim/words.js`, the desk's translations).
