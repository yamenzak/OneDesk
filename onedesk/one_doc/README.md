# OneWriter

Documents in OneCloud: a scope of works, a covering letter, a method
statement, minutes. Written in the desk, kept beside everything else in the
company's files, and opened by anybody the file is shared with.

## Making and opening one

**New › Document** in OneCloud makes one in the folder you are in, blank or
from a template, and opens it. A document opens wherever its file is clicked:
in OneCloud, in a record's Files, from a link in a mail.

The path at the top says where the document belongs, and each step is a way
back: `OneCloud / My Files / Scope of works`, or for a record's document
`Quotation / RC-QTN-2600002 / Covering letter`. OneWriter's mark goes one step
back.

An untitled document takes its name from its first line when you press Enter
at the end of it. **File › Rename** names it yourself.

It saves itself two seconds after you stop typing, and when you leave it.
The head says **Saving…** and then **Saved**.

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

## Who can open it

Whoever may open the File: its owner, whoever it is shared with, and, for a
document on a record, whoever may open the record. Reading is enough to
comment.

## What is not built yet

Version history, live editing together, OneAI in the document, Open in
OneWriter for a record's long text, printing under the letter head, record
fields in a document, and `.docx` on the network drive, through links and in
mail. Each is a stage of its own.

## Connections

- **From OneCloud**: A document is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
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

`frontend/src/writer/` is Frappe Suite's Writer editor, taken whole
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
