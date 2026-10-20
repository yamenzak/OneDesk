# OneWorkbook

Written by hand. What OneWorkbook does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneWorkbook is One's spreadsheet: sheets, formulas, formatting, charts, pivot
tables and notes, in a workbook that lives in OneCloud with the rest of your
files.

## Making a workbook

In **OneCloud**, open the folder it belongs in and choose **New › Workbook**
(or right-click an empty space › **New workbook**). It opens straight away,
named "Untitled Workbook". Click the name at the top to rename it.

A workbook sits in OneCloud like any file: you move, copy, star, share and
delete it there. Copying a workbook makes a second workbook with the same
content. Deleting it sends it to the Recycle Bin with everything else.

## Working in a workbook

- Type into a cell, or into the bar above the grid. A value starting with
  `=` is a formula, such as `=SUM(B2:B5)` or `=B2*D2`.
- A formula can read another sheet: `=Labour!D5`.
- **+** at the bottom adds a sheet. Right-click a sheet's name to rename,
  copy, hide or protect it.
- The toolbar formats numbers, text and cells, merges cells, adds borders,
  filters and sorts, and inserts charts and pivot tables.
- **File** imports a CSV or an Excel file and exports to CSV, Excel or PDF.
- **Notes** (the speech bubble) lists every note in the workbook; Shift+F2
  adds one to the cell you are on.
- **?** lists the keyboard shortcuts.

Everything is saved as you type. "Saving…" and "Saved" beside the name say
where it stands; if a save fails, **Retry** sends it again.

## Version history

The clock at the top opens **Version history**: the workbook as it stood at
points along the way, newest first, with who changed it.

- Click a version to see it. **Restore** makes it the workbook again; the
  versions after it stay in the history.
- **Name** a version to keep it. Named versions are never thinned out.
- **Make a copy** puts that version in a new workbook beside this one.
- Right-click a cell › **Cell history** shows every change to that cell,
  with its value before and after.

Versions are taken as you save: the first save, then every 25 edits or half
a minute. Older ones are thinned as they age: all from the last day, one an
hour for a week, one a day for a month, one a week for three months.

## Working on it together

Everyone who has a workbook open sees the others' changes as they make them,
cell by cell, without saving or reloading. Their faces sit at the top right,
and each person's selection shows in the grid in their colour, with their
first name. Somebody who may only read it sees the changes and can't make
any.

## Asking OneAI

**Ask AI**, at the top beside **File**, opens the Ask bar. Select the cells it is about,
then say what you want: "total this column", "a formula for the margin in
F2:F5", "which line costs the most?". OneAI either answers in words or fills
cells, and what it fills is one edit: **Undo** takes it all back. It sees the
sheet you are on, up to 25 rows and 40 columns of it, and nothing else. Each
question costs credits like any other OneAI request, and Ask is there only
when OneAI is on for the workspace. Somebody who may only read the workbook
can't ask.

## Who can open it

The same people who can open the file in OneCloud. Your own files are yours
until you share them; a workbook in a company folder or a library is open to
whoever can open that folder. Somebody who may read it but not change it sees
**View only** at the top.

## What is not built yet

- Filling a record's table from a workbook, or opening one in a workbook.

## Connections

- **From OneCloud**: A workbook is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
- **To OneCloud**: A workbook lists in its folder with the other files, and its history goes with it to the Recycle Bin.

## Under the hood

### What it is made of

A workbook is two rows. The **File** is what OneCloud lists, moves, shares and
deletes; its `file_url` is `/api/method/onedesk.one_sheet.api.download?workbook=…`
(`api.URL`), which Frappe treats as a remote file, so the File has no bytes of
its own. The **Workbook** holds the content: every sheet, its formats,
merges, comments, validation, protection, conditional formats, filters,
slicers, pivots, charts, named ranges and view, as one gzipped JSON blob
(`storage.py`, after Suite's). OneCloud's node carries `workbook` when the URL
names one (`namespace._workbook`), and the explorer opens it on the
`workbook` page instead of downloading it. Whether somebody may open or save a
workbook is `namespace.may` on its File, never the Workbook's own permissions,
which are System Manager's only: one share model for one object.

A File naming a workbook another File already holds is a copy (OneCloud's
Copy, `_copy`), so `copied` gives it a copy of the workbook rather than a
second pointer at the same one, and `file_gone` deletes the workbook and its
history with the File. OneIntake does not read workbook files.

### The editor

`frontend/src/sheet/` is Frappe Suite's Sheets editor (frappe/suite
`df7f341`, `frontend/src/apps/sheets`), taken whole: the formula engine, the
canvas grid, the editor, the dialogs, and about 750 unit tests. Each file
says so at its top. It is AGPL-3.0, like this repository. It reaches into
Suite's own shell in a dozen places (session, app switcher, theme menu,
command palette, page title, leave confirmation, Drive's rename input, the
Hocuspocus provider, a second socket); `seams.mjs` points each at a stand-in
in `shim/`, so the vendored files keep Suite's imports and a refresh is a
copy. The edits made inside vendored files, each marked `One:`, are listed in
`frontend/src/sheet/VENDORED.md`. `WorkbookPage.vue` is the island; the
`workbook` page mounts it full-bleed, the desk's rail beside it and the
page's own head hidden, because the editor draws its own.

The guards written for our islands (frappe-ui only, tokens, translated
words, formatting through the kit) skip the vendored files
(`scripts/tree.py`, `vendored`): they are held to Suite's rules. The page and
the shims are ours and checked like the rest.

Formulas are worked out in the browser; the server never parses one. It
checks only that a save is under 75 MB unpacked and reads as JSON.

### Live, `live.py` and `realtime/handlers.js`

Suite's Yjs layer is kept as it is: cells bound into a Y.Doc
(`collab/cells-binding.js`), updates batched every 16 ms
(`collab/frappe-provider.js`), presence and cursors (`collab/awareness.js`).
Only the transport is ours. `realtime/handlers.js` is loaded by Frappe's own
socketio process for every app (`frappe/realtime/index.js`), so live editing
needs no second service. A browser joins a workbook's room with
`onedesk_join`; the relay asks `live.admit` once, as that socket's session,
and the server names the room and says whether the person may write. After
that a change goes browser → node → the others, never through Python. A
reader may ask for the state and be seen, nothing else; only a writer may
send cell updates or answer with a whole state. Who somebody is in the
presence strip is stamped from `admit`, not taken from their browser. A
message over 2 MB is dropped, and a socket sending more than 300 in five
seconds is ignored for the rest of the window. On the client, `shim/live.js`
replaces Suite's `collab/realtime-adapter.js` at build time (`seams.mjs`).
Each browser still saves the whole workbook itself, as before; Yjs makes
every open copy the same, so the saves agree. `boot.one_sheet_live` turns it
on for everybody signed in. A late joiner loads the saved workbook, then asks
the room and is answered by whoever is there.

### Ask, `assist.py`

The editor's Ask bar is Suite's; only the call is ours. `ai_assist` checks
the person may write, reads the saved workbook, and shows the model the
sheet's used range (at most 25 rows by 40 columns and 12 KB, `context`) with
the selection, through `run.once("sheet_assist", …)`, so the account's
gateway, credits and logs apply like every other OneAI job. The model
answers JSON, `{"actions": [...]}`; `cleaned` keeps only `setCell` on a real
cell address with a formula under 1,000 characters and `answer` text, at
most 200 of them, and drops the rest. Nothing is written on the server: the
editor applies the cells as one undoable edit and saves them like typing,
so live co-editing and history see them too. `boot.ai_assist_enabled` shows
the bar only when OneAI is on and the account is set up.

### History, `versions.py`

After Suite's `sheets/versioning`, written again in our style. Every save
appends the editor's edits (`ops`) and a `save` entry to **Workbook Change**
under a lock on the Workbook row (`select … for update`), so the order is
the order of saves; a request id sent twice is recorded once. `head_seq` on
the Workbook is the last entry. A **Workbook Version** is the whole blob at
a point: taken on the first save, then after 25 edits or 30 seconds
(`maybe_take`); a restore and the moment after it are milestones; a name
pins one. `tidy`, daily, thins unnamed automatic versions by age (`THINNED`)
and drops edits older than 30 days that the oldest version already holds.
Cell history is a `LIKE` on `cell_refs`, filtered exactly in Python.

### What was left out, and why

- **Suite's sharing dialog.** A workbook is a File, and two share models for
  one object is the bug; OneCloud shares it.
- **Suite's AI settings.** Suite calls a model provider with a key typed
  into a settings form. Ask goes through the account's gateway and credits
  instead, so the form is gone.
- **Suite's two co-editing transports.** One is a Hocuspocus server of its
  own: a second process, an nginx route and a shared secret. The other relays
  through `publish_realtime` with no room, which sends every workbook's edits
  to every signed-in user. Ours is below.
- **Link previews.** Suite fetches the page a cell links to. One fetches
  nothing a cell names; `get_link_preview` answers with the address.
- **Suite's Home and Trash pages.** OneCloud is both.
