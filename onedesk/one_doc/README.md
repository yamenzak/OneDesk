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

## On a record

A record's **Files** tab is OneCloud, so **New › Document** there files a
document on the record: a covering letter on a quotation, minutes on a
project. Whoever may open the record may open its documents, and whoever may
change the record may change them.

Every text with a formatting toolbar on a saved record, a quotation's terms
or a project's notes, has **Open in OneWriter** under it. The text opens as
a document filed on the record, and what is written there becomes the text
through the record's own save, two seconds after you stop typing. The record
checks it as it checks a save from its form; if it refuses, the reason shows
under the head and nothing is written. A submitted record's text opens read
only, unless the field may change after submitting.

If the text is changed on the record while its document is open, the
document does not write over it: it says so, and opening it again from the
record starts from what the record says.

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

**Ask OneAI** in the head takes a request about the selection, or about the
whole document when nothing is selected. OneAI either writes words, which go
in place of the selection or at the cursor as one edit undo takes back, or
answers in the dialog. It is charged to the account's credits like any other
request.

In the OneAI panel it finds documents by name, reads them, and suggests a new
document or something to add at the end of one, as a card nothing happens
until you approve.

## What is not built yet

Printing under the letter head, record fields in a document, and `.docx` on the network drive, through links
and in mail. Each is a stage of its own.

## Connections

- **From OneCloud**: A document is made, kept, moved, copied, shared and deleted in OneCloud, and opens from it.
- **From OneCRM**: A quotation's terms, like any record's formatted text, open in OneWriter and go back through the record's save.
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

`assist.ai_assist` sends the document's text, the selection's text and the
request through the `doc_assist` action and returns sanitised HTML or an
answer; the editor inserts it, so nothing is written server-side. The panel's
tools are `ai.py`. An approved addition is appended to the stored HTML and
the editor state cleared, so the next open builds from the HTML; the
approver's open copy is told over `one_document_written` and draws it in
straight away, which saves the state again. Somebody else with it open at
that moment would save over the addition, which is the one gap here.

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
