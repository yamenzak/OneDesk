# Vendored: Frappe Suite's Writer editor

Taken from **frappe/suite** at `df7f3417d3344b0ec654883cd2779227230fc659`
(19 October 2026), `frontend/src/apps/writer/`. Copyright (c) Frappe
Technologies Pvt. Ltd., AGPL-3.0, like this repository. Every file says at its
top what it was derived from. Nothing here may move to a permissive licence.

Left out: `pages/` (`../DocumentPage.vue` replaces the document page, and
OneCloud is the list), `router.ts` and `routes.ts`, `components/Navbar.vue`
(the page draws its own head), `components/Dialogs.vue` and
`components/SearchDialog.vue` (OneCloud shares, moves and finds files),
`components/WriterDocumentsSkeleton.vue` and `components/RoundedListView.vue`.

## Seams: where Suite's shell is replaced, without editing the import

`seams.mjs` resolves these imports to `shim/`:

| Import | Stand-in | Why |
|---|---|---|
| `@/boot/session` | `shim/session.js` | the desk's own session, through the kit |
| `@/stores/root`, `@/utils/documentTitle` | `shim/shell.js` | the desk has Ctrl+K and sets the title |
| `@/utils/confirmLeave` | `../sheet/shim/confirmLeave.js` | the same dialog the sheet uses |
| `@/apps/drive/sdk` | `shim/drive.js` | renaming is OneCloud's, and who may be mentioned is the company's staff |
| `@/apps/writer/resources` | `shim/resources.js` | templates and comments through one_doc/ |
| `@/apps/writer/composables/useYjs` | `shim/yjs.js` | saved through one_doc/api.py and shared over One's relay, in place of y-webrtc against Frappe's signalling server and a copy in IndexedDB |
| `@/apps/writer/router` | `shim/router.js` | the desk routes; the export helpers find nothing to read |
| `~icons/lucide/…` | frappe-ui's `lucideIconsPlugin` | Suite's icons, from lucide-static |
| `@/apps/writer/…` | this folder | Suite's alias for itself, with its `?inline` and `?raw` kept |

## Edits inside vendored files

Each is marked `One:` where it is.

- `components/CoreEditor.vue`: `styleClipboard: {}` in `RichTextKit.configure`,
  because Suite's frappe-ui turned the format painter on by default and ours
  does not; the upload endpoint is `onedesk.one_doc.api.add_picture`.
- `components/CoreEditor.vue`, `ToC.vue`, `FloatingComments.vue`:
  `document.querySelector` is `writerRoot().querySelector`
  (`shim/root.js`), because the page draws inside the island's shadow root.
- `components/CoreEditor.vue`, `VersionsSidebar.vue`: their CSS `@import`
  is relative, because CSS imports do not go through the seams.
- `components/FloatingComments.vue`: `$store` is null; Suite's global store
  is not here and the template never reads it.
- `utils/index.js`, `utils/docximporter.js`: Suite's endpoints for pictures
  in a document are `onedesk.one_doc.api.picture`, `add_picture`,
  `picture_extension` and `drop_pictures`.
- Every word a template shows goes through `__()`.
