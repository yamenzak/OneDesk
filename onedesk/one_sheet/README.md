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

## Excel and CSV files

An Excel (.xlsx, .xls, .xlsm) or CSV file in OneCloud opens in OneWorkbook
when you open it, sheets, formulas, number formats and merged cells and
all. What you change is saved into the same file, a minute after you stop
and again when you leave, so downloading it, or opening it in Excel, gets
the file as it is now. What it held before each time is kept as a version,
under **Versions** in OneCloud. A CSV keeps only the first sheet, as a CSV
can hold only one.

Upload a new version of the file and it is read in again the next time it
is opened.

Any workbook downloads as an Excel or CSV file from OneCloud: right-click
it › **Download as Excel** or **Download as CSV**. It opens, works its
formulas out, and the file downloads.

## Working in a workbook

- Type into a cell, or into the bar above the grid. A value starting with
  `=` is a formula, such as `=SUM(B2:B5)` or `=B2*D2`.
- A formula can read another sheet: `=Labour!D5`.
- **+** at the bottom adds a sheet. Right-click a sheet's name to rename,
  copy, hide or protect it.
- The toolbar formats numbers, text and cells, merges cells, adds borders,
  filters and sorts, and inserts charts and pivot tables.
- **File** prints, imports a CSV or an Excel file, and exports to CSV or Excel.
- **Notes** (the speech bubble) lists every note in the workbook; Shift+F2
  adds one to the cell you are on.
- **?** lists the keyboard shortcuts.

Everything is saved as you type. "Saving…" and "Saved" beside the name say
where it stands; if a save fails, **Retry** sends it again.

## Printing

**File › Print** prints this sheet or every sheet under the company's letter
head, drawn as it looks: the numbers as they show, colours, borders, merged
cells, column widths, pictures. Hidden rows and columns aren't printed.

- **Orientation**: a sheet wider than a portrait page starts on its side.
- **Fit to page width** shrinks a wide sheet to the page. Without it, the
  columns that don't fit print on the next pages, as Excel does.
- **Letter head** is the workspace's default, any other letter head, or
  none. With no letter heads at all, one is drawn from the company details.
- **Gridlines** can be left off.

**Print** opens the PDF in a tab of its own, where the browser prints or
saves it. **Save PDF to OneCloud** keeps it beside the workbook; a record's
workbook has **Attach PDF to** the record instead.

## On a network drive and through a link

On a network drive connected to OneCloud, through a public link, and
attached to an email, a workbook is an Excel file: `Glass prices.xlsx`. Excel, LibreOffice and
Numbers open it with its formulas, number formats, merged cells and column
widths. A formula only OneWorkbook knows (RECORD, FIELD, BRAND, IMAGE) is
written as the value it last showed.

Saving it from Excel saves into the workbook: values and formulas come back,
the workbook's own formatting stays as it was, and the earlier state is kept
in Version History. A formula Excel only saw as a value keeps its formula if
the value was not changed. A record's workbook opens read-only on the drive;
its table is edited in OneWorkbook.

## Who can open a record's workbook

A workbook made from a record's table is attached to that record, so whoever
can read the record can open it and whoever can edit the record can edit it.
Sharing its file on its own in OneCloud changes nothing.

## Going back

The path at the top says where the workbook belongs, and each step is a
way back. A record's workbook reads `Quotation / RC-QTN-2600002 / Items`:
the record's number goes back to its form. Any other reads
`OneCloud / My Files / Glass prices`: a folder opens OneCloud there.
OneWorkbook's mark goes one step back, to the record or the folder.

## Leaving a workbook to look something up

Go anywhere else: the workbook is saved as you go, and waits on the bar,
after the date, under OneWorkbook's mark and its name. Click it to come back; × takes it off. Leave
several and the bar says how many, with a list to pick from. The bar
remembers the last five you left, in every tab and on every device you
sign in on.

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

OneAI is asked in its own panel, at the bottom right, as everywhere else.
On a workbook it is told which workbook is open, its sheets, and the cells
you have selected with what they hold, so "total this column" or "a margin
formula in F2:F5" is about what you selected. Writing cells is a card you
approve. Each question costs credits like any other OneAI request.

From any page it also knows workbooks: "find the C-28
costing", "what does the Gulf sheet charge for powder coating?", "make me a
workbook for this week's deliveries with a total", "put a margin formula in
column G and make the header bold", "leave a note on D14 that the rate is
from June". It finds and reads a workbook as it answers. Making one,
writing cells, formulas and formatting, or leaving a note is a card you
approve, and nothing changes until you do; an open copy of the workbook
reloads when it is approved. It reads formulas as they are written, not
what they work out to, and it never writes into a record's table sheet:
change the record instead.

## A record's table in a workbook

Under every table on a saved record, beside **Add row**, is **Open in a
workbook**. The first time, it makes a workbook attached to the record (it
lists in the record's Files) whose first sheet is the table: a line for
each row, a column for each column the table shows on the form. After that
the same button opens the same workbook. Its columns are the ones the
table shows on the form: choose others with the table's gear before opening
it the first time, and those are the columns.

- Change a cell, add a line or delete one, and the record saves itself
  with it a moment later, the way typing saves the workbook. Amounts,
  totals and anything else the record works out come back into the sheet.
- A new line needs only what the record can't work out for itself, such as
  the item; the rest fills in when it saves.
- The record checks everything as if you had typed it on the form. When it
  refuses (an item that doesn't exist, a quantity of nothing), the reason
  shows at the top beside the name, and the record keeps what it had until
  the sheet is right.
- A formula is fine anywhere in the first sheet: the record gets what the
  formula comes to. The other sheets are yours, and the first can read
  them: `=Rates!B4`.
- The header and the columns the record works out are locked. A list
  column offers its choices.
- A column that names other records, such as the item, searches them the
  way a field on a form does: type in the cell, or click the arrow at its
  right, and the matches show under it, with **Create a new …** and
  **Advanced Search** at the bottom. Up, Down and Enter pick one.
- What the record refuses shows on the cell it is about, tinted with a red
  corner, as Excel marks an error: a name that isn't a record yet, a word
  in a number, or the record's own reason, such as a quantity of zero on
  row 4. Select the cell to read why; for a name that isn't a record yet,
  **Create Item** (or whatever it names) makes it from its name and saves
  again.
- A formula that works out to an error (#VALUE!, #REF!, #DIV/0! and the
  rest) reads red with a red corner, and selecting it says in plain words
  what is wrong.
- When somebody changes the table on the form while the workbook is open,
  the first sheet is drawn again in place, formulas kept. If you have
  changes not yet saved, the workbook says the record changed instead; open
  it again from the record to bring the change in.
- Once the record is submitted, the first sheet can only be read.

What a column takes: numbers, money, percentages and durations; text;
links to other records (checked when the record saves); lists (a
dropdown); tick boxes (TRUE or FALSE); dates (2026-10-21), dates with a
time, and times; colours; files and pictures, by their address. Formatted
text, code and Markdown become columns only when they are picked on the
form's table, and are shown and taken as plain text.
Rules a record keeps only on its form, as it is being typed, don't run
from a workbook; every rule it checks when it saves does.

## Templates

**File › Add Sheets From a Template** adds a template's sheets to the
workbook that is open, such as a costing sheet, beside the ones it has; a
sheet whose name is taken gets a number after it, and the template's
formulas that read it read the numbered one. To bring a costing sheet's
lines into a record's table, type the formula in the table, such as
`=Costing!C6:C` under Quantity.

**File › Save as Template** keeps a copy of the workbook in OneCloud ›
Workbook Templates, where everyone in the company can start from it; you,
and administrators, can change it there like any workbook. **New ›
Workbook** in OneCloud then asks which template to start from, or a blank
one.

A template is its own sheets and nothing else. Saved from a record's table
workbook, it keeps the sheets beside the table and leaves the table out,
since the table is the record's. **Open in OneWorkbook** under a table
opens the table as it is; templates are added from inside.

## Branded sheets

A sheet can carry the company and the record it is for:

- `=BRAND("logo")` inside `=IMAGE(...)` draws the company's logo in the
  cell, fitted to it; `=BRAND("name")`, `"address"`, `"phone"`, `"email"`,
  `"website"`, `"tax_id"`, `"currency"` and `"colour"` read the rest from
  General.
- `=RECORD("customer_name")`, `=RECORD("transaction_date")` or any other
  field read the record a table's workbook belongs to, as its form shows
  them. In any other workbook they are blank.
- `=FIELD("Project", E1, "project_name")` reads a field of any record the
  reader may open, named in a cell. Pick a project in E1 and the cells that
  read it fill in a moment later.

A sheet can say which formulas each of its lines gets, as an Excel table's
calculated columns do: type an item on a new line and the line's area,
prices and totals appear on it. Nothing is laid out before it is used, so a
template has no hundred empty lines, and the totals over the header sum
the whole column, however long the list grows. A cell typed over keeps
what was typed.

A record's table sheet is formatted when it is made: the header on the
company's colour, money in the record's currency, numbers to the field's
own decimals or else the workspace's, what the record works out in grey,
and widths by what each column holds. Formatting it yourself afterwards
stays. Each cell takes what its field takes: a whole number in a count, a
number (negative too) in an amount, a date in a date, one of the choices
in a select, TRUE or FALSE in a tick. Anything else is refused as it is
typed; a formula is let through, and the record says when what it works out
to doesn't fit.

In any workbook the currency button offers the workspace's currency first,
and Ctrl+Shift+4 applies it.

A number format can show a zero as blank, as a finished costing does on
its empty lines.

A tab can carry a colour, picked in the tab's menu, drawn as a band along
its foot as Excel and Google Sheets draw it; it goes with the sheet when it
is renamed or copied.

## Filling the table from another sheet

Type a formula in the table's first line that reads a whole column of
another sheet, and it fills the column down, one line for each line there:

- `=Costing!A4:A` puts Costing's column A, from line 4 to its last line, in
  this column.
- `=IF(Costing!A4:A="","",Costing!P4:P/Costing!C4:C)` works line by line:
  P over C on every line that has something in A.

This is what Google Sheets and Excel call a formula that spills. Add a line
to Costing and the table gains a line; change a price there and the record
follows when the workbook saves. If something is typed in a cell the
formula wants to fill, the formula shows `#SPILL!` until it is cleared.
Pasting values works as well, and so does a formula on each line.

Formulas in the table stay when the table is drawn again after a change on
the form. A column whose first line is a formula belongs to that formula;
the record's values aren't written over it.

## Who can open it

The same people who can open the file in OneCloud. Your own files are yours
until you share them; a workbook in a company folder or a library is open to
whoever can open that folder. Somebody who may read it but not change it sees
**View only** at the top.

## What is not built yet

- An Excel file's charts, pictures, colours and column widths aren't read
  in, and aren't written back: its values, formulas, number formats and
  merged cells are.

- A picture column shows the picture's address, not the picture.
- Frozen rows are meant to head every printed page, as Excel's print titles
  do; the wkhtmltopdf on the dev bench prints them once, at the top.
- A print has no page numbers, and the letter head's foot comes after the
  last sheet rather than at the foot of every page.
- A link column searches every record of its type, not only the ones the
  form would offer for that field.

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

### OneAI on the page, `ai.py`

The editor tells the panel the sheet and range selected on every selection
(`kit/desk.js`, `aiSees`); the panel sends it with the question, and
`ai.page` tells the model the workbook, its sheets, a record's table sheet,
and the selected cells with what they hold, up to 200. Suite's own Ask bar
and AI settings are taken out; `cells.py` keeps the cell helpers they shared.

### A record's table, `table.py`

`open_table` makes a Workbook with `bound_doctype`, `bound_name`,
`bound_field` and `bound_sheet` set, behind a File attached to the record,
so who may open or save it is who may read or write the record
(`namespace.may` already answers attached files that way). `columns` takes
the columns the opener chose on the grid's gear (`GridView` in their user
settings), else the child table's list-view fields, at most 20, with the
row `name` first: the grid's columns and no more. A required field the grid
does not show is left to the record's save, which fills it as it does for
the grid (on a purchase order line the item's name, units, conversion
factor, date, warehouse and company-currency twins) or refuses naming it,
and the gear adds it; adding every required field put Stock UOM and the
company-currency rate and amount in every order's sheet. `style.table`
leaves an optional Int, Float or Percent blank at zero (`;` on its format),
so a profile's unused width and height are empty, not 0.000; their headers are stored in `bound_columns` once, so the
sheet is read by the headers it was drawn with whatever language the next
person reads in. `laid` draws the sheet: the row ids in a hidden first
column, the header frozen, the header, id and worked-out columns (read
only, or fetched) protected, a list rule on Select columns and a number
rule on number columns for 200 lines past the end.

The browser works formulas out, so a save of a bound workbook also sends
the bound sheet's values (`shim/table.js`); `save_sheet` stores the
workbook as always, then `apply` reads the values into the table. Columns
are found by their header, so moving one or putting your own column
between them changes nothing. `taken` checks each value against its field
type before the record sees it, and hands dates and times over as dates and
times, not text, because records compare them; a line with nothing typed is skipped; a
line whose id is a row keeps that row, every field the sheet doesn't show
included, and a row no line names is removed. When anything differs, the
record is saved with `doc.save()` under a savepoint, so its validation,
links, server scripts and totals all run; a refusal rolls back to the
savepoint and its message goes back to the editor (`tableNotice`), its
"Row #1" turned into the sheet's line (`lined`), and the
workbook's own save stands. `back` answers the cells the sheet should take:
the ids of new rows, the worked-out columns, what the record filled where
the sheet was empty. The editor writes them through the engine, so
co-editors see them too, and saves again; that save finds nothing to do.

A link column's rule is `{type: "link", doctype}` (`_rule`); the editor
draws its caret, and `shim/LinkSearch.vue` lists `search_link`'s answers
under the edit as the desk's link field does (its markup and its
`awesomeplete.scss` look, through the desk's own colour variables, which
reach into the editor), Create a new through the desk's quick entry and
Advanced Search through its `LinkSelector`. Before
the record is saved, `missing` looks up every name the sheet gives in a
link column and answers them by type instead of saving; `make_missing`
makes each from its name alone (`_made`: the name field and title set to
it, and a required link left empty set from the user's default, the top of
a tree, or the only record there is), as the person, so their own right to
make one is checked. A refusal comes back with `faults`, each a cell and
why: `read` collects a wrong value where it is, `unknown` each name that
isn't a record, and `pinned` the record's own reason, its line from "Row 4"
and its column from the header it names first. The editor tints those cells
and marks them through the conditional-format seam the painter already
reads (`fault`, `faultFill`, `faultInk`), and `shim/CellProblem.vue` says
why under the selected cell, with the fix that calls `make_missing` for the
one name (`shim/problems.js` also explains a formula's error code).

A record saved anywhere but from the workbook (`doc.flags.from_workbook`)
calls `changed` from `doc_events`, which publishes `one_table_changed` to
the record's own realtime room, the one its form already listens on; the
open editor asks `redrawn` for the bound sheet drawn again and writes it
through the engine. Which record types have a workbook at all is cached
(`BOUND_KEY`) so a save of anything else costs one cache read.

The hidden header holds `fingerprint`, a hash of the table as the sheet
last matched it (its rows, the shown values, and whether it is
submitted). A sheet whose mark doesn't match the record is refused, so a
row somebody added on the form is never deleted by a sheet that never saw
it; `refresh`, on every opening, draws the bound sheet again when the
marks differ and keeps the other sheets and the column widths. A copy of
the File is a plain workbook.

### Templates, `templates.py`

A template is a Workbook with `is_template` set, behind a public File in
the company's Workbook Templates folder, so `namespace.may` lets every staff
member read it and only its owner or an administrator change it.
`listed` answers every template the reader may open, `data_of` one's
content, which `api.make` starts a workbook from, and `sheets_of` its
sheets as cells for File › Add Sheets From a Template. `save_as` copies
the workbook; from a record's table workbook, the table's sheet and
everything kept for it are left out (`table.without`). Until October 2026
a table's template kept the table's sheet, its header and the formulas
under it, and was offered only for that table; the patch
`templates_are_their_sheets` took those sheets out.

`laid` writes the formulas typed in the table back where they were. A column with
one on its first line is fed by it, so `laid` leaves the record's values out
of it and puts no rule on it, and `refresh` keeps every formula when it
draws the sheet again. In the browser, `takeBack` writes nothing into a
formula or a cell a formula spilled into, which would block it.

The engine taken from Suite had no spill: a range in a cell showed its
first value, `A4:A` meant A4 alone, and `Sheet!A4:A` meant a million lines.
`engine/sheet.js` now lays a formula's range over the empty cells below and
right of it (`_spill`), read through `getCellValue` and `getDisplayValue`
without writing them, so the stored sheet keeps one formula; `_settle`
works out the formulas that could spill over a cell before it is read,
`getExtent` counts spilled lines for `tableValues`, and while anything
spills an edit drops every worked-out value, since a cell reading a spilled
one isn't in the dependency graph. A range to the end of a column stops at
the sheet's last line in use. `engine/formula.js` works operators and the
one-value functions (`_BY_CELL`) over a range cell by cell (`_each`). An
empty cell now reads as `""`, so `=A7` shows blank as in Google Sheets, and
`COUNT` no longer counts empty cells.

A real costing sheet showed three faults in the engine taken from Suite, mended
in place (`VENDORED.md`): `"CW01"=""` was true, because both sides were
read as the number 0; `Sheet!$A4` didn't read; and a cell such as "120cm
Glass Handrail" was the number 120. Excel's `_xlfn.CEILING.MATH` and the
other dotted names are read as the classic functions on import
(`shim/excel.js`).

### Branded sheets, `style.py`

`brand` is General's company (`letter_heads.company`) with its currency;
`record` is a record's own fields through `frappe.format`, stripped of
markup. `get_sheet` sends both (`brand`, `record`, the latter only for a
table's workbook whose record the reader may see), `redrawn` sends the
record again, and the editor hands them to the engine's `setContext`, which
`RECORD()` and `BRAND()` read; `IMAGE()` answers a spec the sparkline
painter's path draws as a picture (`shim/pictures.js` loads each once and
repaints). `table` is a record's table sheet's formats, laid in by
`table.placed` the first time only, or anew (`fresh`) for a workbook just
made from a template whose columns may lie in another order. `branded` lays
out a sheet under the company's logo: the logo over three rows, what the
sheet is for beside it, up to nine fields from column D in columns of
three, each a label on the company's colour and a value: a doctype makes it
a link cell, `{"typed": True}` a figure somebody types, and both are a white
box; any other is worked out and grey, as the worked-out columns are, in its
own `numberFormat` or text. `{meta0}` names the first field's cell in another
field's formula, so `FIELD()` can read the record picked there, and in a
line's formula as `$E$1`, so a line copied by hand still reads it. The
totals on row 4 sum open ranges (a total may carry its own look), the header on row 5 in whichever of
white or ink reads on the company's colour (`letter_heads.on`, also
`BRAND("on_colour")`), and a `lines` rule rather than lines: what each
line works out, in grey, and the key figures marked, are column formats,
and a zero there is blank (`;` at the end of a number format). Only the
item column is frozen. Rua's costing templates are built with it. Formats are the
editor's own shapes: `formats` per sheet as `cells`, `cols` and `rows`;
`merge` as `masterMap` and `slaveMap`; `view` as widths, heights and frozen
rows and columns; `lines` as `{from, key, formulas}`, `{r}` the line, which
the engine's `setLines` keeps and `setCell` and `batchSetCells` apply.
`api.records` answers `FIELD()`: `shim/fields.js` asks once for every record
the formulas named within a moment, `{doctype: {name: fields}}` comes back
through `style.record` with the fields the reader may not see taken out
(`apply_fieldlevel_read_permissions`), a record they may not open is left
out, and the editor drops its results and draws again. File › Add Sheets
From a Template brings each sheet with its formats, merges, view, link
cells and lines (`templates.sheets_of`), from any template, a table's own
sheet left out.

### Excel and CSV files, `api.open_file`

`open_file` makes a Workbook whose `file` is the Excel or CSV File itself
(`source_kind` xlsx or csv), so it is that File's permissions that count,
and answers the same one the next time. `get_sheet`'s `source` says where
the File's bytes are and whether the workbook has read them yet (`fresh`);
the editor reads them in through the importer it already had
(`useExportImport.readSource`), then writes itself back a minute after a
save and when it is left (`fileContent`, SheetJS) to `write_back`, which
puts the bytes in a new File and hands them to OneCloud's
`history.replace`, keeping what the File held as a Cloud File Version.
`history.replace` calls `file_replaced`, which empties the workbook when
the new version came from anywhere else, so it reads the file in again.
`save_sheet` leaves such a File's size alone. OneCloud's Download as Excel
or CSV opens the editor with `?export=`, which exports once the workbook has
loaded: only the browser can work a workbook's formulas out.

### Printing, `paper.py`

The editor sends what it draws, never HTML: for each sheet the text every
cell shows (number formats applied, a tickbox as ✓), the format keys that
print, merges, widths and heights from the sheet's own view, hidden rows and
columns, and the frozen rows (`shim/printing.js`). `paper.style` turns only
those keys into CSS and only safe values through (a colour, a font name, a
border style); text is escaped; a picture prints only from this site's
files (`printing.FILE_URL`). `paper.page` writes the page under the chosen
Letter Head's top and foot (`letter_heads()` lists them, the default
first), the default when none is named, nothing for `NO_HEAD`, or one drawn
from the company when the workspace has none (`letter_heads.draw`), and `pdf` renders it with frappe's `get_pdf`,
the wkhtmltopdf every record print uses. Fitting is CSS `zoom`; not fitting
cuts the columns into runs that each fit (`bands`). `PX` is wkhtmltopdf's
pixel as measured without smart shrinking (500px is 288pt), so a run is as
wide as the paper. Kept, the PDF is a File beside the workbook's File, or on
the bound record, under the reader's own permission to add there.

### Excel on the drive, `excel.py`

The editor saves each formula's worked-out value (`values`, in
usePersistence) beside the cells, since only the browser can work a
formula out. `excel.build` writes the workbook with XlsxWriter: a formula
with that value cached, so a previewer that does not calculate still shows
it; an open-ended range such as `H6:H`, which Excel does not have, closed at
row 1,048,576; a OneWorkbook-only formula as its value. `xlsx` keeps the
bytes in the cache until the workbook changes. `dav._as_file` names the
node `Name.xlsx`, `Document` serves those bytes and sends a save to
`excel.write`, `links.get` hands them to a link, and `one_storage/file.py`'s
`get_content` hands them to anything else that reads a File, an email
attachment above all, naming it `Name.xlsx` while it is read. `excel.read` takes
Excel's save back with openpyxl: values and formulas in, `_xlfn.` dropped
and the range opened again, the other slices (formats, widths, notes)
kept, and a OneWorkbook-only formula restored where Excel's value equals
the one sent. `write` goes through `save_sheet`, so a change and a version
are kept, and refuses a record's workbook. Tested with a direct save, as
Windows' drive and LibreOffice save; an app that saves by writing a new
file and swapping it in leaves a plain Excel file beside the workbook,
which goes to the Recycle Bin.

### Back to a workbook, `public/js/workbooks.js`

OneWorkbook has no sidebar of its own: frappe would make one listing
Workbook, Workbook Change and Workbook Version raw, so `outside.UNSHELLED`
leaves it out and `one_module_heirs` opens its records in OneCloud.


Desk's router tells `onedesk.workbooks.moved` of every route: the workbook
just left goes to the front of a list kept in the person's Workbook user
settings (`frappe.model.user_settings`, five at most), the one opened comes
off it. `api.titles` names only the ones the reader may
still open, so one deleted or unshared drops off. The tiles sit in the
bar's lead, the `open` group after the date; one workbook is a tile and an
×, several a tile that opens a list. Workbooks only: a record left half
edited has frappe's own unsaved-changes guard and its own place in
breadcrumbs.

### OneAI's tools, `ai.py`

`my_workbooks` and `read_workbook` run as the person asking (OneCloud's
answer for the workbook's File); `draft_workbook`, `write_cells` and
`comment_on_cell` write a Setup card (`one/ai_setup.apply` hands it back to
`ai.approved`), which on approval writes into the saved shape (`written`,
`noted`) through `save_sheet`, so it is a version like any save, and tells
the approver's open editor (`one_workbook_written`), which reloads when it has nothing
unsaved. The tools are the `workbooks` group (`one_ai/groups.py`), given
on the workbook page or when a request says sheet, formula, cell or the
like. A cell's result is worked out only in the browser, so a read says a
formula as written.

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
- **Suite's Ask bar and AI settings.** Suite calls a model provider with a
  key typed into a settings form, from a bar of its own. OneAI is asked in
  its panel, through the account's gateway and credits, so both are gone.
- **Suite's two co-editing transports.** One is a Hocuspocus server of its
  own: a second process, an nginx route and a shared secret. The other relays
  through `publish_realtime` with no room, which sends every workbook's edits
  to every signed-in user. Ours is below.
- **Link previews.** Suite fetches the page a cell links to. One fetches
  nothing a cell names; `get_link_preview` answers with the address.
- **Suite's Home and Trash pages.** OneCloud is both.
