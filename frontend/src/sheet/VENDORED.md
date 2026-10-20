# Vendored: Frappe Suite's Sheets editor

Taken from **frappe/suite** at `df7f3417d3344b0ec654883cd2779227230fc659`
(19 October 2026), `frontend/src/apps/sheets/`. Copyright (c) Frappe
Technologies Pvt. Ltd., AGPL-3.0, like this repository. Every file says at its
top what it was derived from. Nothing here may move to a permissive licence.

Left out: `pages/Home.vue` and `pages/Trash.vue` (OneCloud is both),
`pages/SheetEditor.vue` (`../WorkbookPage.vue` replaces it), `routes.ts`, and
`engine/difftest/` (it needs HyperFormula, which is not a dependency).

## Seams: where Suite's shell is replaced, without editing the import

`seams.mjs` resolves these imports to `shim/`:

| Import | Stand-in | Why |
|---|---|---|
| `@/boot/session` | `shim/session.js` | the desk's own session, through the kit |
| `@/composables/useAppSwitcher`, `useThemeMenuOption`, `useSettingsMenuOption` | `shim/shell.js` | the desk has the app switcher and the theme |
| `@/stores/root` | `shim/shell.js` | the desk has Ctrl+K |
| `@/utils/setupTheme`, `@/utils/documentTitle` | `shim/shell.js` | the desk sets the theme and the title |
| `@/utils/confirmLeave` | `shim/confirmLeave.js` | the same dialog, with translated words |
| `@/apps/drive/components/InlineRenameInput.vue` | `shim/InlineRenameInput.vue` | Drive's input depends on Drive's selection store |
| `~icons/lucide/globe` | `shim/GlobeIcon.vue` | no unplugin-icons here; a lucide class |
| `@hocuspocus/provider` | `shim/hocuspocus.js` | One co-edits over the desk's socket, never a second server |
| `socket.io-client` | `shim/socket.js` | the desk always has its socket |
| `@/apps/sheets/…` | this folder | Suite's alias for itself |

## Edits inside vendored files

Each is marked `One:` in the file.

| File | Edit |
|---|---|
| `components/SheetEditor/index.vue` | Suite's brand menu replaced by the OneWorkbook mark, back to OneCloud; the breadcrumb starts at OneCloud; the Share button and dialog are off (OneCloud shares) |
| `components/SheetEditor/usePersistence.js` | calls `onedesk.one_sheet.api`; Drive's `track_visit` dropped |
| `components/SheetEditor/useCollaboration.js` | starts only when `frappe.boot.one_sheet_live` is set |
| `components/SheetEditor/useVersionHistory.js` | a copy opens at `/desk/workbook/…` |
| `services/versions.js` | calls `onedesk.one_sheet.versions`; Make a copy is `make_copy` |
| `services/linkPreview.js` | calls `onedesk.one_sheet.api.get_link_preview` |

## Refreshing

Copy the folder over again from a newer commit, keep the headers, and redo
the edits above. The seams need nothing.
