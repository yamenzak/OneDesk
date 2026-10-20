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
| `../../collab/realtime-adapter.js` | `shim/live.js` | One's relay (`realtime/handlers.js`) instead of `publish_realtime` to everybody |
| `@/apps/sheets/…` | this folder | Suite's alias for itself |

## Edits inside vendored files

Each is marked `One:` in the file.

| File | Edit |
|---|---|
| `components/SheetEditor/index.vue` | Suite's brand menu replaced by the OneWorkbook mark, back to OneCloud; the breadcrumb starts at OneCloud; the Share button and dialog are off (OneCloud shares); Ask calls `onedesk.one_sheet.assist.ai_assist`, and AI settings never show (nothing sets `ai_assist_can_configure`); `tableNotice` says why the record refused its table |
| `components/SheetEditor/usePersistence.js` | calls `onedesk.one_sheet.api`; Drive's `track_visit` dropped; a workbook bound to a record's table sends that sheet's values and takes back what the record answers (`shim/table.js`) |
| `components/SheetEditor/useCollaboration.js` | starts only when `frappe.boot.one_sheet_live` is set (`one_sheet/live.py`) |
| `components/SheetEditor/useVersionHistory.js` | a copy opens at `/desk/workbook/…` |
| `services/versions.js` | calls `onedesk.one_sheet.versions`; Make a copy is `make_copy` |
| `services/linkPreview.js` | calls `onedesk.one_sheet.api.get_link_preview` |
| `components/SheetEditor/index.vue` (again) | File › Save as Template, opening `shim/TemplateDialog.vue` |
| `engine/formula.js` | `=` and `<>` compare as Excel does (`_equal`): text with text, numbers with numbers, empty with "" and 0; `Sheet!$A4` reads; `A4:A` runs to the end of the column, not to A4; operators and the one-value functions (`_BY_CELL`: `IF`, `ROUND`, `LEN`…) work a range cell by cell (`_each`) |
| `engine/sheet.js` | a cell is a number only when all of it is one (`Number`, not `parseFloat`); an empty cell reads as `""`, so `=A7` shows blank; a formula that works out to a range spills into the empty cells below and right, `#SPILL!` when one holds something (`_spill`, `_settle`, `getExtent`, `isSpilled`); a range to the end of a column stops at the sheet's last line in use |
| `components/SheetEditor/index.vue` (menus), `PivotFieldPicker.vue` | a click outside a menu is told from the event's path (`composedPath`): in the shadow root `document` finds no menu and the target is the host, so every mousedown closed the tab and right-click menus before their items' clicks landed |
| `components/SheetEditor/index.vue`, `useShortcuts.js`, `canvas/index.js` | `document.activeElement` read through `shim/focus.js`: in the island's shadow root the page only ever names the host, so paste and copy were dropped and some shortcuts misread focus |
| `canvas/index.js` (again) | a link cell (`type: 'link'`) starts its edit from the caret (`beginEdit`); `commitWith` ends an edit with a picked value; `onEditKey` lets the list under the cell take Up, Down, Enter, Tab and Esc; clicking cells while typing a formula in the cell itself picks them, as from the formula bar (`_pickTarget` took only an input, and the cell's editor is a textarea) |
| `canvas/painters/cell-painter.js` | an empty link cell shows the dropdown caret |
| `components/SheetEditor/index.vue` (links) | a link column's search (`shim/LinkSearch.vue`), Create Them for names the record can't find, File › Add Sheets From a Template (`shim/AddSheetsDialog.vue`), and the table's sheet drawn again when the record changes on its form (`one_table_changed`) |
| `engine/formula.js` (brand) | `RECORD()`, `BRAND()` read `setContext`'s record and company; `IMAGE()` answers a picture spec on the sparkline path |
| `canvas/painters/cell-painter.js` (picture) | a spec with `image` is drawn as a picture fitted to the cell (`shim/pictures.js`); `canvas/index.js` repaints when one loads |
| `utils/format-number.js` | `currency:` takes any ISO code (AED was shown as USD); a format ending in `;` shows a zero as blank |
| `components/SheetEditor/usePersistence.js` (brand) | hands `get_sheet`'s `record` and `brand` to `setContext` on load |
| `engine/sheet.js` (lines) | a sheet's `lines` rule gives a line its formulas when its key column is filled, as an Excel table's calculated columns do (`setLines`, `getLines`, kept through rename, copy and delete); `usePersistence.js` saves and restores it as `lines` |
| `engine/sheet.js`, `components/SheetEditor/index.vue` (tab colours) | a tab's colour (`setColour`, `getColours`, kept through rename, copy and delete), picked in the tab's menu and drawn as a band along the tab's foot; `usePersistence.js` saves it as `colours` |
| `components/SheetEditor/index.vue`, `usePersistence.js` (currency) | the workspace's currency (`get_sheet`'s `brand.currency`) comes first in the currency menu, is what the button shows and what Ctrl+Shift+4 applies |
| `engine/validation.js` | a number rule takes all of the text as a number (`Number`, commas as thousands, a minus allowed), `whole` takes whole numbers only (an Int field), and a `date` rule takes 2026-10-21 or a day number; a formula typed in a checked cell is let through, and the record checks what it works out to |
| `canvas/painters/cell-painter.js`, `canvas/constants.js`, `components/SheetEditor/index.vue` (problems) | a cell with something wrong (a formula's error, or a value the record refused, `shim/problems.js`) gets a red or amber corner, a refused one a tint and an error code red ink, through `getCondFormat`'s `fault`; selecting it opens `shim/CellProblem.vue`; a rule's marker checks the cell's value, not its formatted text (`raw` on `getValidation`), so EUR 99,125.00 is no longer marked as not a number; the header's Create Them is gone |
| `components/SheetEditor/useExportImport.js`, `index.vue`, `usePersistence.js` (files) | an Excel or CSV File opened from OneCloud is read in once (`readSource`) and written back after saves (`fileContent`, `write_back`); `exportAs` exports once loaded; an export of a workbook named "x.xlsx" isn't called "x.xlsx.xlsx" |
| `engine/formula.js` (fields) | `FIELD(doctype, name, field)` reads another record through `setContext`'s `field` (`shim/fields.js`); the editor draws again when the record comes |
| `canvas/index.js` (edit) | Enter, F2, a double-click and `beginEdit` open the edit on what the cell holds (`getRaw`), not on what it shows: a formula cell opened and left unchanged was written back as its formatted result |
| `components/SheetEditor/index.vue` (template sheets) | File › Add Sheets From a Template brings each sheet's formats, merges, view, link cells and lines with its cells |
| `engine/xlsx-io.js` | an imported formula goes through `shim/excel.js`, which drops `_xlfn.` and maps `CEILING.MATH` and the like to the classic names |
| every `.vue` and the menus' `.js` | the words go through `__` (imported from `kit/desk` in scripts) so they reach Arabic and German; not marked, since there are about 730 |

## Refreshing

Copy the folder over again from a newer commit, keep the headers, and redo
the edits above. The seams need nothing.
