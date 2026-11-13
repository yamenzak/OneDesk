# OneDoc

What OneDoc is, how it works and why; for agents, OneAI and us. What is
known to be wrong is `SCRATCHPAD.md`, and the Help people read is `docs/`.

Documents in OneCloud: a scope of works, a covering letter, a method
statement, minutes. Written in the desk, kept beside everything else in the
company's files, and opened by anybody the file is shared with.

## Making and opening one

**New › Document** in OneCloud makes one in the folder you are in, blank or
from a template, and opens it. A document opens wherever its file is clicked:
in OneCloud, in a record's Files, from a link in a mail.

The path at the top says where the document belongs, and each step is a way
back: `OneCloud / My Files / Scope of works`, or for a record's document
`Quotation / RC-QTN-2600002 / Covering letter`. OneDoc's mark goes one step
back.

An untitled document takes its name from its first line when you press Enter
at the end of it. **File › Rename** names it yourself.

It saves itself two seconds after you stop typing, and when you leave it.
The head says **Saving…** and then **Saved**.

A document left for another screen waits on the bar under its title, with
OneDoc's mark, as a workbook does; clicking it goes back, and × drops it.

## Writing

The toolbar is Suite's Writer: headings, bold, italic, underline, strike,
links, colour, alignment, the format painter, font size and typeface, lists,
task lists, quotes, code, pictures, video, embeds, tables, page breaks and
page setup. The outline on the left follows the headings. Select text to
comment on it; comments sit in the margin.

**File › Page Setup** sets the typeface, size, line and paragraph spacing,
and what prints in the header and footer, for this document or, under
**Everywhere**, for every document you open. **File › Lock** stops accidental
typing until somebody unlocks it.

## Templates

**File › Save as Template** keeps the document in OneCloud › Document
Templates, where everyone in the company can start from it. **File › Insert
a Template** puts a template's content where the cursor is; **New › Document**
offers them too. A template is its own content and nothing else.
Keeping one is OneDoc's one ability, `template` (`abilities.py`, the
Permission Type `doc_template` on Writer Document): a Manager has it, a User
does not, and the item is left out of **File** for whoever lacks it.

## On a record

A record's **Files** tab is OneCloud, so **New › Document** there files a
document on the record: a covering letter on a quotation, minutes on a
project. Whoever may open the record may open its documents, and whoever may
change the record may change them.

Every text with a formatting toolbar on a saved record, a quotation's terms
or a project's notes, has **Open in OneDoc** under it. The text opens as
a document filed on the record, and what is written there becomes the text
through the record's own save, two seconds after you stop typing. The record
checks it as it checks a save from its form; if it refuses, the reason shows
under the head and nothing is written. A submitted record's text opens read
only, unless the field may change after submitting.

If the text is changed on the record while its document is open, the
document does not write over it: it says so, and opening it again from the
record starts from what the record says.

## Printing

**File › Print**, or Ctrl+P, opens the Print dialog: pick a letter head (the
default is chosen) and the orientation, then **Print** opens the PDF in a new
tab to print from there. **Save PDF to OneCloud** keeps it beside the
document; for a document on a record, **Attach PDF to** the record instead.

Page setup's header and footer text, page numbers and separator lines print
on every page. Pictures print as they are in the document; typefaces print
as their nearest serif, fixed-width or sans.

## A record's fields in a document

A document filed on a record works like a print format for it. **File ›
Insert a Field** lists the record's fields with what each says now; the one
you pick goes in as a grey block with its label. On paper the block is what
the record says at that moment, formatted as a print shows it: a total as an
amount, a date as a date, and a table of lines as a table. So a covering
letter on a quotation reads "Dear Mansour & Sons, … AED 9,135.00" and stays
right when the quotation changes.

The record's own print page lists its documents under the letter head, and
each prints under the letter head chosen there.

## Word

On the network drive a document is a Word file, `Scope of works.docx`, and so
is a document downloaded through a link or attached to a mail. Its headings,
lists, tables, pictures and page breaks come with it, and a record's fields
are filled in as on paper. Open it in Word, change it and save: the document
takes Word's version, and what it said before is kept in Version History as
**Before a Word save**. A document with a record's fields in it opens in Word
but can only be changed in OneDoc, since Word would keep the values and
lose the fields.

A Word file put into OneCloud opens in OneDoc, and what you write is saved
back into the same file when you leave it, its old content kept in the file's
versions. A new version of it put in from Word is read in the next time it
opens. When the Word file has what OneDoc doesn't keep (comments, tracked
changes, headers and footers, and the rest `one_cloud/fidelity.py` reads
for), nothing is saved over it until the person chooses **Save Over
Original** or **Save as Copy**; a .docm never opens here, and the file opens
read-only while somebody has it in OneOS.

## Who can open it

Whoever may open the File: its owner, whoever it is shared with, and, for a
document on a record, whoever may open the record. Reading is enough to
comment.

## Version history

**File › Version History** lists what the document said: under
**Automatic**, one taken every ten minutes while somebody writes; under
**Manual**, the ones somebody named with **+**. Clicking one shows what
changed since the one before; **Restore** puts it back as an edit everyone
sees, which undo takes back. Unnamed versions past the newest
hundred go each night; named ones stay.

## Writing together

Everybody with the document open writes in the same copy. Each sees the
others' cursors and selections in their colour, and their faces in the head.
Somebody who may only read sees the writing as it happens and can comment.

## Asking OneAI

OneAI is asked in its own panel, at the bottom right, as everywhere else. On
a document it is told which document is open, what it says, the record it
is on with that record's fields, and what you have selected, or the
paragraph your cursor is in. So "make this shorter", "translate this into
Arabic" or "add a paragraph on the payment terms after this" is about your
selection. What it writes is a card you approve: in place of the
selection, after the paragraph, or at the end. Approving puts it in the
open document as one edit undo takes back.

It also finds documents by name and reads them, and makes new ones: in a
folder or on a record, from a template or not. "Make a covering letter on
this quotation from the template" makes one whose fields print what the
quotation says. Each question costs credits like any other OneAI request.

**Make a Picture with OneAI**, beside the picture button in the bar, asks
for a sentence and a shape (wide, square or tall) and puts the picture OneAI
makes where the cursor is. It is kept on the document as an uploaded picture
is (`api.make_picture`, with OneCloud's picture job through
`one_cloud/made.py`, billed as "OneDoc picture").

## Connections

- **From OneCloud**: A document is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
- **From OneCRM**: A quotation's terms, like any record's formatted text, open in OneDoc and go back through the record's save.
- **To OneCloud**: A document lists in its folder with the other files, and its pictures go with it to the Recycle Bin.

## Under the hood

### What it is made of

A document is two rows, as a workbook is. The **File** is what OneCloud
lists, moves, shares and deletes; its `file_url` is
`/api/method/onedesk.one_doc.api.download?document=…` (`api.URL`), so the File
has no bytes of its own. The **Writer Document** holds the content:

- `content`, the editor's Yjs state in base64, which the editor opens from;
- `html`, the same document as HTML, written on every save, which everything
  that is not the editor reads: printing, search, exports, mail;
- `settings`, the page setup, only the keys `api.SETTINGS` names;
- `comments`, the comments' Yjs state.

Both representations are saved together because the browser has both in hand
at the moment it saves, so nothing in Python needs ProseMirror to read a
document. A document with HTML and no editor state yet (made from HTML, or
from Word) opens from its HTML, once.

Whether somebody may open or save a document is `namespace.may` on its File,
never the Writer Document's own permissions, which are System Manager's
only. OneCloud's node carries `document` when the URL names one
(`namespace._document`), and the explorer opens it on the `document` page.

A File naming a document another File already holds is a copy, so `copied`
gives it a copy of the document; `file_gone` deletes the document with its
File.

Pictures put into a document are private Files kept on the Writer Document
(`add_picture`) and read through `picture?id=…`, which asks whether the reader
may open the document.

### The editor

`frontend/src/doc/` is Frappe Suite's Writer editor, taken whole
(`VENDORED.md` says what was left out, where Suite's shell is replaced, and
the few edits inside its files). `DocumentPage.vue` is ours: the head, the
File menu, and the document and file objects the editor reads, over
`one_doc/api.py`. The `document` page mounts it full-bleed, as the workbook's
page does.

Suite's writer shared a document peer to peer through Frappe's signalling
server and kept a copy in the browser. Here `shim/yjs.js` saves through
`save_document` and shares changes, cursors and comments over the same relay
the workbook uses (`realtime/handlers.js`, a `document` room that
`one_sheet/live.admit` lets a reader into, and a writer write in).

### History, the relay and OneAI

A version is a **Writer Document Version** row holding the document's HTML
at that moment (`versions.py`). The editor offers one every ten minutes of
writing and `new_version` keeps it only if the last unnamed one is ten
minutes old; Suite's history panel restores by setting the HTML into the
editor, so a restore is an ordinary edit and travels to everybody.

Live writing is Yjs over Frappe's socketio, not y-webrtc: `shim/yjs.js`
sends updates, awareness (cursors) and comment state to the `document` room,
asks whoever is there for the current state when it joins, and saves two
seconds after the last change. Two people saving the same state is harmless
because each save is the whole document.

The page tells the panel the selection and the cursor's paragraph on every
selection change (`kit/desk.js`, `aiSees`), the panel sends it with the
question, and `ai.page` tells the model the document, what it says, its
record's fields and the selection. `chat._ran` keeps the page in
`frappe.flags.one_ai_page`, so `write_document` takes the selected text from
it rather than from the model. On approval, `ai.placed` puts the words into
the stored HTML where it can find the place (a whole paragraph, or text
inside one) and clears the editor state; the approver's open copy is told
over `one_document_written` and puts them in at the selection, after the
paragraph, or at the end, which saves the state again. A selection across
paragraphs is put in by the open copy alone. Somebody else with the document
open at that moment would save over a change the server made, which is the
one gap here.

### A record's text

`field.py`. `open_field` finds or makes the Writer Document whose
`bound_doctype`, `bound_name` and `bound_field` name the text, filed on the
record as the workbook for a table is; only Text Editor fields that are not
read only open, because they already hold HTML. `save_document` hands each
save to `field.put`, which writes the field through `doc.save()` under a
savepoint, and keeps as the document's HTML what the record kept, so the two
compare equal next time. What the document held before the save is what the
field held when it was opened; when they differ, the record was changed
elsewhere and `put` refuses rather than write over it. An addition OneAI
makes on a card goes through `put` too.

### Paper

`paper.py`. What prints is the document's stored HTML, cleaned again, never
what the browser sends. The page is the letter head's top (from
`one_sheet/paper._letter_head`, rendered with the record as `doc`), the
document, and the foot; Frappe's `get_pdf` makes the PDF. Page setup's
header, footer, page numbers and lines become wkhtmltopdf's own
`header-left`, `footer-right`, `[page]` and `footer-line` options, which, as
with Frappe's repeated headers, need the patched-Qt build of wkhtmltopdf.

A field block is `<span data-field="…">label</span>` (`shim/field.js`, a
TipTap node). `fill` swaps each for `value_of` the record: `frappe.format`
of the field, or for a child table a table of its list-view columns, which
replaces the paragraph it stood alone in. A field the reader may not see at
its permlevel prints nothing; with no record, the label in brackets.
`fields_of` offers every field that holds a value or rows, hidden ones
included, since a quotation's customer sits in a field its own print hides.

The record's print page (Frappe's `print` page) gets `public/js/one_doc/print_documents.js`
through `page_js`; it wraps `PrintView.show` to list `on_record`'s documents
under the letter head.

### Word

`word.py`, with python-docx (MIT) to write and mammoth (BSD-2) to read,
the converter Suite's writer runs in the browser. `build` walks the stored
HTML, filled as on paper, into paragraphs in python-docx's own styles
(Heading n, List Bullet, List Number, Quote, Table Grid), with pictures read
from their Files; `docx` keeps it in the cache until the document changes.
The drive (`one_cloud/dav.py`), a File's content (`one_cloud/file.py`)
and a link (`one_cloud/links.py`) ask for it where they ask the workbook
for its Excel file. `write` is Word's save: `read` turns it into HTML, its
pictures into the document's pictures, the old HTML becomes a version and
the editor state is cleared so the next open builds from the HTML.

A `.docx` File opened from OneCloud gets a Writer Document whose `file` is
that File and `source_kind` is `docx` (`open_file`); its title keeps the
`.docx`. The page calls `write_back` when it is left, which builds the file
and puts it in through `one_cloud/saving.write_back` and `history.replace`,
so the File keeps its versions, one per sitting; `file_replaced` empties the
HTML when a version comes in from outside, and `get_document` reads the file
again. `open_file` keeps `fidelity.document`'s list (from the file's parts and
mammoth's `messages`, which `read` now hands back) in `would_lose`; while it
is not empty `write_back` answers `held` until `choice` is `over` or `copy`,
and a version arriving meanwhile sets the document aside as One's own copy
(one_cloud AGENTS.md, Nothing lost silently). `write` keeps the old HTML as
**Before a Word save** and notes in `outside_dropped` what Word had that
`read` left out; `get_document` shows it as `dropped` until
`dismiss_dropped`.
