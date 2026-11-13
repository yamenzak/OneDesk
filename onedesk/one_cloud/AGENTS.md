# OneCloud

The one file for agents, OneAI and us: what OneCloud is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `help/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `updates/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

## Connections

- **From OneMail**: Each mailbox has a folder under Mail with the files its messages sent and received. An attachment in OneMail can be saved to My Files.
- **From OneAI**: A document is attached to the record it belongs to, or filed in a folder for its type and year. It is renamed and tagged.
- **From OneAdmin**: OneAdmin keeps the workspace's storage limit. A file is refused when there isn't room.
- **To OneAdmin**: Open in OneOS starts a session in OneAdmin, which charges the workspace's credits for each minute it is open.
- **To One**: Every record has a Files tab that opens its folder in OneCloud. Letter heads print their pictures from OneCloud, and the full download includes every file.
- **To OneMail**: An attachment too large to send goes as a link to the file instead.
- **To OneAI**: Every new file can be found by its text. A folder OneAI reads has each new file handled in Intake.
- **To OneProject**: Photos and videos in a project's Featured Media folder are shown on its page and its portal. The newest photo is its cover.
- **To OneSheet**: New › Workbook makes a workbook in the folder you are in, and opening one opens it in OneSheet.
- **To OneAI**: OneAI answers questions about a file you can open and finds files by what they say. It also lists your largest files and how full the storage is.

## Under the hood

For the people who build OneCloud. OneAI's `how_to` reads `help/`, never this file.

**What OneAI makes** (`made.py`). Four jobs in `one_ai/jobs.py`,
`cloud_picture`, `cloud_music`, `cloud_video` and `cloud_voice`, each with its
words in `one_ai/words/`, billed through OneAdmin like OneDeck's and
OneDisplay's. A picture and speech are made in the request; music and a video
on the long queue (`made_later`), and the asker hears `File Ready` or `File
Not Made`. The video waits as OneDeck's
does (`one_deck.ai._video`). Speech comes back as raw samples and is kept as
a WAV (`one_display.voices._wav`). The file goes in through `upload._place`,
so the folder's add permission is the check.

**Office files** (`office.py`). What a browser can't draw is sent to
OneAdmin (`proxy.office_convert`), which bills it and asks One's office
containers (`deploy/office`, `one_admin/office.py`). The PDF is kept in the
cache for a day by the file's `content_hash`, so stepping back to it costs
nothing.

**Viewer and editor** (`CloudViewer.vue`, `CloudEditor.vue`, `editor.js`,
`pdf.js`). Bytes come from `api.content`, our own address, so pdf.js and the
canvas can read a stored file. The picture editor is cropperjs 2, as
@framework/ui's ImageCropper uses it, and saves through the explorer's upload
(`version_of` for Save). `pdf.combine` joins PDFs and pictures with pypdf and
Pillow.

**Where a requested file goes** (`targets.py`). A target is a file field: one
on the record itself (`image`), or one in a row of one of its tables
(`one_documents.attachment`). Everything is read from the record's own
fields, so any kind of record works and no app declares anything. A table's
row is picked by its kind: the first required Link or Select column of the
table (an identity document's Type). The person asking sets it; the file goes
on the row of that kind, or on a new one. The row's other plain columns (a
number, dates) are asked of whoever sends the file, with it. A table with
another required Link column is not offered, since the sender could not fill
it.

**OneOS** (`oneos.py`, `one_admin/oneos.py`, `deploy/oneos`). The workspace
keeps the lease on the File itself, the File's one lease below with kind
`oneos`: taken under a row lock in `start`, one person per file and never
while anybody may write in it live, renewed for two minutes each time the
every-minute `tick` hears from OneAdmin (`proxy.oneos_state`) that the
session runs, and let go when it stopped or OneAdmin has not answered for
those two minutes. The container is given two addresses on the workspace,
`oneos.file` and `oneos.save`, each sealed with the site's key over the use,
the File, the lease and an expiry eight hours on, so a download address
cannot upload, an address names one file, and a lease taken by somebody else
voids the old session's (409). `file` redirects to a signed R2 address
(follow it), or sends the bytes from the disk. `save` takes the request's
body raw, or the first file of a multipart form, up to 200 MB, and writes it
as a new version (`history.replace`) as the person holding the lease, after
checking they still may change it; the same content is not a version. A stop
in OneAdmin posts `oneos.stopped`, which, like `account.wake`, takes nothing
on trust and asks OneAdmin itself. A stop the person did not make (idle, the
time limit, credits, not answering, an operator) is a toast through
`onecloud_oneos` and the **Closed in OneOS** notification. Read-only for
somebody else's lease is the viewer, since the container has no read-only
mode yet.

A workbook, document or presentation of One's own (`opening.own_of`) goes
to the container as the file the drive serves (`opening.exported`:
`excel.xlsx`, `word.docx`, `drive.pptx`, named by `opening.office_name`),
and `save` reads each one back with `dav.write_own`, as a drive save does,
inside `saving.through(lease.ONEOS)`: the editors' `saving.check` lets the
lease's own holder through, the version kept first is named by
`saving.before` ("Before a OneOS save"; a workbook's is still Excel's own),
and `saving.outside` notes `in` so the bar says OneOS. The drive's save of
its own lock goes through `saving.through(lease.DAV)` the same way. A save
is once per content a session sends (`onecloud_oneos_saved:<lock>`, seeded
with what `file` sent). `start` refuses what `opening.kept_inside` names, the
same three the drive refuses. `opening.download` is Edit's **Download as**.

**Previews** (`office.py`). A preview is billed when OneAdmin converts it.
The PDF is kept by the version's content: in the cache for a day, and in R2
under `previews/<content_hash>.pdf` (on the disk under
`private/onecloud-previews` where there is no store), with the File's
`one_preview_of` naming the version it was made from, so the listing says
`previewed` and the viewer opens it as the PDF without asking. The viewer
opens the clicked file as its PDF when the editors can't show it
(`opening.row` has no `edit`, or `loses` is not empty); `weigh` says
`waiting` when the editor holds changes back, and then the editor opens.

### One lease per file (lease.py)

Every File has one lease, and a workbook or document leases the File it
sits behind. **Alone** is one holder, a OneOS session (`oneos`) or a
desktop app's WebDAV lock (`dav`, dav_locks.py below), kept on the
File (`one_lease_kind`, `_lock`, `_session`, `_user`, `_until`,
custom/file.json; patches/one_lease_on_file moved OneOS's own fields onto
it), so it outlives the cache and a restart. **Live** is anybody in
OneSheet or OneDoc, in the cache as a hash per File of `user|socket id`
to `{seen, write, app}`: realtime/handlers.js asks `one_sheet/live.admit`
on join (which records it), `live.here` every minute while the room is open,
and `live.leave` on leave and on disconnect; a holder not heard from for two
minutes is gone. A person who is live in two tabs writes if either may. The
rules are pure (`refused`, `reading`, `present`, tested in
tests/test_lease.py): alone is refused while somebody else holds it alone,
the asker holds it another way, or anybody, the asker included, may write
live, and a reader does not stop it; while alone is held, the editors open
read-only with `lease.told` ("Samir is editing this in OneOS"), their saves
are refused, a WebDAV PUT is 423 Locked and a version is not restored.
`lease.of(target)` answers the UI for a File, workbook or document: the
mode, who holds it alone and who is live.

**A sitting.** `history.replace(item, new, sitting=…)` takes the place of
the last version instead of adding one when the File still holds what the
same person last saved in the same sitting, under ten minutes ago
(`history.merges`, pure). The sitting is the alone lock while the saver holds
one (OneOS passes its lock), else the way in: `editor` for a write-back,
`drive` for a WebDAV PUT. An upload in the explorer has none and is always
a version. The last save is in the cache (`onecloud_sitting:<file>`, ten
minutes), with the URL it left, so a restore or anybody else's save between
breaks the sitting; losing the cache only adds a version. The object a
merged save takes the place of is dropped from R2 once nothing names it.
The version from before the sitting is the one the first save kept.

### Nothing lost silently (fidelity.py, saving.py)

`fidelity.workbook` and `fidelity.document` read an office file's parts
(zip names and a few XML markers) for what the native editors drop, pure
and tested in tests/test_fidelity.py. OneSheet writes into the Excel file
itself with openpyxl (one_sheet/patching.py), so for Excel it is what
openpyxl does not save: macros, threaded comments (the plain note stays),
charts (rewritten through its model), slicers and timelines, WMF and EMF
pictures, the x14 data validation, conditional formatting and sparklines in
a sheet's extLst, shapes and text boxes, embedded objects, form controls,
and connections and query tables. `fidelity.read_in` is the longer list for
an Excel file read into a workbook of One's own from the drive. For Word: macros, comments, tracked changes, headers and footers,
footnotes, charts, text boxes, equations, embedded files, links, fields and
fonts, sizes and colours for Word, plus the styles mammoth said it did not
know (its `messages`, kept by `word.read`, less those `word.build` writes).
The list is kept on the Workbook or Writer Document (`would_lose`) when the
file is read in: `get_sheet` when it is fresh, `word.open_file`.
`saving.state` is what both editors and `live.admit` open with: `can_write`
off while alone is held or for macros (.xlsm, .docm, or a vbaProject inside)
and .xls, with `notice` saying why, and `loses`, the line naming what saving
over drops. `saving.write_back` returns `held` and stamps `held_back` while
the list is not empty and nobody chose; `over` writes (the file as it was
kept as a version) and clears the list, `copy` writes a File beside it and
moves the record onto it. A new version arriving while `held_back` is set
(`file_replaced`) sets the record aside as One's own copy, "Name (Huda's
copy)", rather than reading the file in over the changes. A save from the
drive into One's own record (`word.write`, `excel.write`) keeps a named
version first ("Before a Word save", "Before an Excel save") and notes what
the file had that was not kept (`outside_dropped`, shown until dismissed).

### Opening an office file (opening.py)

`opening.way(file_name)`, pure, is what Edit offers by extension: `edit` in
OneSheet (xlsx, csv) or OneDoc (docx), `make` a OneDeck deck (pptx,
ppsx), `copy` into a workbook or document of One's own (xlsm, xltm, xls,
docm, dotm). `namespace.node` puts it on the row as `office`, with `loses`
once this version has been read. `opening.weigh` reads it the first time
(`fidelity.workbook`, `fidelity.document` without mammoth's messages, so a
style it does not know is only found when OneDoc reads the file in) and
keeps the list on the File (`one_fidelity`) with the version it was read
from (`one_fidelity_of`, the `content_hash`, else the URL), so a listing
never opens a file. The island (`OneCloud.vue` openItems, editChoices)
opens a file with nothing to lose in its editor and anything else in
CloudViewer's PDF preview; Edit in OneSheet on a file with losses asks
first (`onecloud_dialogs.js` edit_anyway), and step 1's bar does the rest.
`opening.one_copy` makes One's own workbook (`excel.read`, an .xls through
xlrd as values) or document (`word.read`) beside the file. `opening.editing`
reads every row's live hash in one Redis pipeline and puts who writes on it
(`editing`); `one_sheet/live.admit` and `leave` redraw the folders it shows
in (`opening.redraw`). Edit in OneOS is not offered inside the editors:
whoever is in an editor to write is live, and alone is refused while
anybody is.

**OneOS offered** (`oneos.offered`). OneAdmin's hello says `oneos`: on
while OneOS is set up there and the workspace is not in its trial
(`one_admin/oneos.on_trial`), and an hour's credits at the size it opens.
The account keeps it (`oneos_on`, `oneos_credits_an_hour`); the listing
sends it, the island shows Edit in OneOS only with it, and `oneos.start`
refuses without it. OneAdmin's own start refuses a trial too.

### An editor turned off (editors.py)

OneDoc, OneSheet and OneDeck are apps of their own (P6.2), each a rail row
(its `sidebar/`): Recent Documents (Workbooks, Presentations) is OneCloud's
page on `@made/<kind>` (`namespace.made_in`: every one the reader may open,
the last changed first), and New is OneCloud's page with `?new=<kind>`,
which `OneCloud.vue` newAsked turns into its own New in My Files. An editor
is off when its rail row is in `apps.hidden()`; `editors.off()` reads it
once a request. Off, nothing of its kind is made: each record type's
`before_insert` calls `editors.making` (but while installing, migrating or
patching, so OneDeck's themes still sync), which covers New, a template, a
copy (`api.copied`), a Word or Excel file opened in place, a record's table
and OneAI's approved card; `draft_document` and `draft_workbook` say so
before proposing. What was made still opens: each editor's `_may(..,
"write")` refuses with `editors.read_only`'s line, `saving._read_only` puts
it on the editor as its notice, OneDeck opens in view, `opening.kept_inside`
keeps OneOS from editing it, and the drive's saves are refused through the
same `_may`. Exporting only reads, so Word, Excel and PowerPoint still come
out. A listing's `office` leaves out what would open or make an off kind
(`editors.ways`), so such a file opens as its preview; the boot's
`one_editors` hides OneCloud's New entries and says Open, not Edit, on One's
own. Tested in this folder's `tests/test_editors.py`; `one_doc/checks.py`
walks it on the demo.

### The bars at the foot of the rail (api.capacity)

A linked workspace's files are what the account measured in R2 last night
(one_admin/storage.measure), the only count that sees every object; an
unlinked one keeps them on this server's disk, and they are added up there.
The database is asked when the bars are drawn, as the nightly report to the
account asks it (account.database_bytes).

### What it is made of

Frappe's own **File**. Every attachment in the framework is a File row —
`attached_to_doctype`/`attached_to_name` say which record, `folder` says which
folder, `is_private` says who may fetch it — and folders are File rows with
`is_folder`. OneCloud adds no second file model: the explorer, sharing, WebDAV
and mounts are all views and verbs over File, so a file attached from an
invoice and a file dropped in a folder are the same kind of thing.

**The bytes are R2's, the permission is the workspace's, and the key is
admin's.** INFRA 6 settled the shape (one_admin/storage.py): a tenant site
holds no R2 credential; it asks admin for a URL signed for one object
(`one.account.put_url`, `get_url`, `drop`), admin checks the quota and puts
the key under `tenants/<slug>/`, and the bytes go between R2 and whoever is
reading or writing — never through admin. OneCloud is a client of that and
not a second R2 integration.

- `store.py` — where a File's bytes are. Frappe gives two hooks,
  `write_file` and `delete_file_data_content`, and reads everything else
  straight off the disk; so new content is written through the hook to R2,
  and `file.CloudFile` (the File class, overridden) reads it back. A stored
  file's URL is `/api/method/onedesk.one_storage.store.fetch?key=…` (the
  folder's name before the rename, kept because every File and every field
  a file is put in holds it; hooks.py's `override_whitelisted_methods`
  sends it to `one_cloud.store.fetch`, and the drive's `dav.serve` address
  the same way, since computers keep it): Frappe
  counts any `/api/method/` URL as remote (`URL_PREFIXES`), so none of its
  disk checks apply to it, and fetching it checks the reader may open the
  file and redirects to a URL admin signed for a quarter of an hour.
  Keys are content-addressed (`files/<private|public>/<md5><ext>`), which is
  Frappe's own de-duplication by `content_hash` carried over: the same PDF
  attached to ten records is one object, deleted when the last File naming
  it goes.
  A workspace not linked to an account (a bench of one's own, the test
  site) keeps using the disk. `enabled` is the switch, and it is the
  account's configuration, not a setting anybody on the workspace can
  change. A signed URL in a saved page is dead in fifteen minutes, while
  ours is good for as long as the file is.
- `file.py` — `CloudFile`, Frappe's File with three methods sent to R2
  instead of the disk: `get_content`, `exists_on_disk` (so de-duplication
  finds a stored twin) and `make_thumbnail` (made from the bytes and stored
  beside them).
- `store.daily` — files still on the disk once the workspace is linked to
  storage move by themselves, a batch each night. `store.move` copies them
  to R2 and points their rows, and the attach field each came through, at
  the stored copy; the copy on disk stays, because a public file's old URL
  may be written into a web page or an email template no row knows about.

- `namespace.py` — one tree of node ids over File: `@my`, `@company`,
  `@shared`, `@records[/<DocType>[/<name>]]`, a project's `@featured/<name>`
  (one_project/media.py), `@bin`, and any File by name.
  Record folders are derived from `attached_to_*` each time they are opened,
  so there is nothing to keep in step with the record. **Who may do what is
  `may` and nothing else**: a record's file answers to the record, and
  adding to a record's room to `may_add` (who may change the record, and a
  person to their own Employee's, for their papers); its owner
  may do anything; a portal user gets nothing more; a person's own folder is
  theirs; Company is every member of staff's to read and add to, and an item
  in it is its owner's or a Workspace Administrator's to change. `inside`
  works out a folder's space once for a listing rather than walking the
  chain per file. A folder's id is its path (Frappe names folders so), so
  renaming or moving one gives it and everything under it new ids — callers
  read ids fresh from a listing, never keep them.
  The node ids in full:
  - `@root`, the top: My Files, Shared with Me, Company, Records, Recycle
    Bin.
  - `@my` and `@company`, stored folders under other names: the reader's
    own folder (`home`), and Frappe's own Home less everybody's own folders
    and Frappe's Attachments folder.
  - `@shared`, what other people have shared with the reader (stage 4).
  - `@records`, `@records/<DocType>`, `@records/<DocType>/<name>`, derived:
    the doctypes the reader may read that have files, the records of one,
    and the files attached to one. A record's folder is always exactly its
    attachments and is seen by exactly who may read it.
  - `@mail`, `@mail/<mailbox>`, derived like records: the reader's
    mailboxes, and the files that came or went with a mailbox's messages
    (one_mail/cloud.py). A message's files are here and not under Records.
  - `@featured/<project>`, derived, inside a project's own folder: its
    Featured Media, the files of the project marked `one_featured`
    (one_project/media.py). Only projects have one.
  - `@tasks/<project>`, derived, inside a project's own folder: each of its
    tasks with files, as `@records/Task/<task>` (`project_tasks`). A
    project's folder lists its sub-projects as `@records/Project/<sub>`.
  - `@own/<project>`, derived: a project's folder without its sub-projects,
    the project page's Main. Things put in it go to the project.
  - `@bin`, what the reader deleted, for thirty days.
  - anything else, a File by its name.
  Sharing (stage 4) and libraries (stage 6) add to `may` and to nowhere
  else.
- `api.py` — the verbs: listing, folders, resolve, make_folder, rename,
  move, copy, delete, restore, purge, empty_bin. Between a record and a folder a move is a
  copy, and a copy is a new File row naming the same object. Deleting a
  folder's item is a flag (`one_deleted`, custom/file.json) that hides it and
  everything under it; `purge_old` erases what is thirty days old, daily.
  So File's own permissions, written for attachments, do not decide who may
  rename a folder in somebody's My Files. Within the stored folders a move
  is a move. Between a record and a folder it is a copy, the way an explorer
  copies between two drives. Dragging an invoice's PDF into My Files must
  not take it off the invoice, and dropping a file on a record attaches a
  copy to it. No bytes move either way. Deleting a record's file removes the
  attachment, as it does on the record's own page.

- `upload.py` — putting files in. `begin` checks the target and asks admin
  for a signed PUT per file, holding a ticket (who, where, which key) in the
  cache for an hour; the browser sends the bytes to R2 itself; `done` checks
  the object arrived (a one-byte ranged GET) and writes the row. A ticket is
  its asker's and is used once. Uploads get a random key under
  `files/private/u/`, since a browser cannot hash a large file before sending
  it; copies made inside OneCloud still share their object. Without an
  account, or if the browser cannot reach R2, `here` takes the file as a form
  post through the same `_place`, which also makes the folders of a dropped
  folder. An uploaded picture's thumbnail is made in the background.
  The browser shows its own progress, and a gigabyte of video costs this
  server two small requests. The ticket is the whole of the trust. `done`
  believes nothing else the browser says except the path inside a dropped
  folder. Frappe's own files are keyed by their MD5 (`store.key_for`), which
  a browser cannot work out cheaply for a large file.
- `frontend/src/cloud/` — the explorer, one island (`onedesk.onecloud`, `island.js`)
  with four hosts: `page/onecloud` on the window, a record's Files tab and
  files dialog (`onedesk.mount_cloud`, `public/js/one_cloud/onecloud_picker.js`), the
  attach picker, and the Files views of a project, a task and an item. The
  dialogs it opens — share, links, libraries, mount, request, Drive — are
  desk dialogs in `public/js/one_cloud/onecloud_dialogs.js` (and `public/css/one_cloud/`), loaded with
  `frappe.require` the first time the explorer is opened, so a desk that never
  opens OneCloud never downloads them. It draws and never decides: every list and
  every change is a call above, and a refused one shows the server's reason.
  The place is `?node=` in the address, so history, bookmarks and pasted
  links land in the same folder. View, sort and the preview pane are the
  reader's user settings (under File), and follow them to another browser.
  R2's bucket must allow a browser `PUT` from the workspace's origin (CORS);
  where it does not, uploads fall back to `here` on their own.
- `public/js/one_cloud/onecloud_picker.js` and `api.attach` — the upload dialog.
  Frappe's FileUploader has an extension point, `UploadOptions`: a button
  beside My Device that is handed the dialog, the mounted uploader and the
  doctype, name and field. OneCloud is one, and opens the explorer in
  picker mode. The picker walks without the address, keeps its own
  back/forward, has no command bar, no context menu, no drag and none of
  the keys that change things, and treats a file opened as a file chosen.
  `attach` does what the dialog's Library did through `upload_file`'s
  `library_file_name`: a new File row on the same object, attached to the
  doctype, name and field. But it asks `namespace.may` where
  `upload_file` asks Frappe's File permission, which refuses a file
  reached through a shared folder. The dialog's own `on_success` is then
  called with each row, so an Attach field takes the URL and the editor
  inserts the image as they would after an upload. Frappe's component
  keeps its props to itself, so a subclass of FileUploader keeps each
  dialog's options in a WeakMap keyed by the mounted uploader. The same
  subclass turns Library off (`disable_file_browser`): two pickers
  answering "may I use this file" differently is worse than one.
  `CloudFile.set_folder_name` sends a loose upload from `upload_file` to
  the uploader's My Files instead of Frappe's default Home, which OneCloud
  shows as Company. Only that request is redirected; OneCloud's own verbs
  put things in Company on purpose.

- `live.py` — live updates. An open folder, a record's Files tab, Recent,
  Shared with Me and the rest redraw when somebody else changes what they
  show, the way a list view does. The list view's own `list_update` cannot
  be shared: it unbinds every listener on that event before binding its
  own. Binning, restoring, moving and new versions are also `db.set_value`,
  which publishes nothing. So OneCloud sends `onecloud_change` to the same
  place, File's socket room, once per request after the commit. It comes
  from File's on_update and on_trash, and from each verb that writes around
  `save`. The event carries keys, not names: an HMAC, under the site's
  encryption key, of each folder or record touched, because every desk
  user may join that room and a folder's id is its path. A listing returns
  the keys it `watch`es: one for a folder or a record room, `*` for views
  that span folders. The explorer re-lists when it hears one, after a pause,
  and not while a menu, a rename or a drag is open. A hidden explorer waits
  until it is looked at. The re-listing goes through `may`, so the event
  tells nobody about a file they cannot open.
  The list view calls `frappe.realtime.off("list_update")` before binding
  its own handler, so opening any list would silence OneCloud. The explorer
  joins File's room the way a list view does. A folder's id is a path such
  as `Home/alice@x.com/Salaries`, hence the HMAC. Recent, Shared with Me,
  the Recycle Bin, Requests and a search watch everything (`ANY`) and
  redraw on any change, at most once a second or so. Sending after the
  commit means nobody re-reads a folder before the change is in it.

- `public/js/one_cloud/record_files.js` — the Files tab on every record, declared as
  `TABS` in `namespace.py` and added to the form by `record_tabs.js`, as
  every record tab is (one/tabs.py). So the tab is on every doctype,
  erpnext's and hrms's included, and no field is written to any of them.
  Child tables, Singles and File are left out. The HTML field holds the explorer in room
  mode: `room` is `@records/<doctype>/<name>`, there is no tree and no
  back/forward, going anywhere else opens the OneCloud page, and the address
  is not touched. The tab hides on an unsaved record. Its count starts from
  the form's docinfo and then follows each listing. When the two disagree,
  the sidebar reloads its docinfo, so the timeline notices a file added
  through the tab. The sidebar's own Attachments section is reduced to one
  row, Files and the count, that opens the tab. Its list, Show All and its
  uploader are hidden (desk.css).

- `public/js/one_cloud/record_activity.js` — the Activity tab, last, on every record
  that has Files. Comments, mail, changes, assignments and shares used to
  sit under every tab; under Mail and Files they repeated what the tab
  showed, and on a long form nobody scrolled to them. The tab holds
  Frappe's own footer (`frm.footer.wrapper`), moved in rather than rebuilt,
  so the comment box, the timeline and its email actions all still work.
  It goes into the tab's pane, not into the HTML field that makes the tab:
  inside a control, Frappe's `.frappe-control .action-btn` pins the
  timeline's buttons as if they were a link field's. The tab counts the
  record's comments and follows `refresh_comments_count`, and hides on an
  unsaved record, as Frappe hides its footer.

- `share.py` — people on a file or folder. A share is Frappe's own DocShare:
  read to view, write to edit, written and taken away through `rights.share`
  and `rights.unshare` (one/rights.py), as every module's grants are. `namespace.granted` reads the shares on an
  item and on every folder above it (`chain`, asked once a request per
  folder; `grants`, one query a request), and `may` honours them for staff
  after their own things and before a home is its owner's alone. Whoever may
  change a thing may share it; only System Users can be given one; a record's
  file is refused and shared through its record. `api.move` will not carry
  something out of somebody else's files (`_leaves_its_owner`) — copying out
  is how to take a copy. Shared with Me lists the top of each shared branch.
  The notification links to the explorer, not to File's form. Frappe checks
  its own File permission when a new row names a private file's URL, which
  knows nothing of folder shares, so `CloudFile.validate_private_file_access`
  accepts any row `may` lets the reader open (an override, listed).
  A folder shared is everything in it shared, including what is put there
  later, and File's own permission (which already honours DocShare) agrees
  for a file shared on its own. Whoever may change a thing may share it,
  the way it works in every drive people know: its owner, a Workspace
  Administrator, or somebody it was shared with to edit. A customer or a
  supplier gets a link (stage 5), not a seat. A record's file is shared by
  sharing the record, because its permission is the record's and a second,
  file-only door beside it would drift from it.

- `links.py`, `doctype/cloud_link` and `www/s.py` — links for people outside
  the team. A `Cloud Link` names a File, an audience (anyone, or invited
  addresses in `Cloud Link Invitee`), download and upload, an expiry and a
  password. Its token is kept encrypted (a Password field, for the owner to
  copy again) and found by its SHA-256, so the table alone opens nothing.
  `/s/<token>` (a route rule to `www/s.py`) asks what `needs` says — a
  password, or an address and the six-digit code mailed to it — and answers
  with a cookie `seal`ed with the site's key over the link, the address and
  twelve hours, so no guest state is kept and a cookie opens only its own
  link. Asking for a code answers the same whether the address was invited.
  Every guest verb asks `_within`: the link's item, or something in its
  folder's chain, not in the bin. `get` redirects to a signed R2 URL (or
  sends from disk); `put` is a plain form post whose files belong to the
  link's owner, who is notified. The four guest doors are rate-limited. The
  page is plain forms on the portal stylesheet, no script. A link on a File
  goes when the File does (`forget_file`, on_trash); an invitation needs an
  outgoing email account and says so rather than failing silently.
  A link may let its guests view, download, and for a folder upload.
  Anyone-links with no password open straight away. A password or code is
  asked once. A guest reaches the link's file, or what is in its folder
  now, so something added to a shared folder later is there and something
  deleted or moved out is not. `_within` is the whole of that rule. Whoever
  may change the thing may make a link (`namespace.may` write): its owner, a
  Workspace Administrator, an editor it was shared with, or for a record's
  file whoever may change the record.

- `library.py` — team libraries. A library is a folder flagged `one_library`
  under `Home/Libraries` (hidden from Company like Attachments), and its
  members are DocShares on it with the role in the bits: Reader (read),
  Member (write), Owner (write and share). `namespace._library_may` is asked
  before an item's owner is, so membership is the only way in; renaming or
  deleting the library itself is an owner's; a Workspace Administrator may
  do anything. The last owner cannot be taken off.
  It is what SharePoint calls a document library and a team drive calls a
  shared drive. Living under Libraries, it does not go when the person who
  made it does, and it is its members' rather than everybody's the way
  Company is. Since membership is a share, `namespace.granted` already
  gives a member what is in the library. Only an owner changes who is in
  it.
- `history.py` and `doctype/cloud_file_version` — versions, Recent, Starred
  and activity. Replacing points the File at the new object and writes the
  old one down as a `Cloud File Version`; the File keeps its name, so shares
  and links follow. `store._named_elsewhere` counts versions, `fetch` opens a
  version for whoever may open its file, and a File's versions (and their
  objects, if unnamed) go when it does. Recent is a capped list per person in
  the cache, fed by `fetch` and uploads; Starred is `_liked_by`, written
  directly so a star neither comments nor notifies. Activity is Info comments
  written by the verbs, read back with the versions.
  Objects are never overwritten (a key is its content, or a random one for
  an upload), so a version is the object a file used to name. Restoring an
  old version is the same move the other way, with what was current written
  down first. Recent holds what the reader opened or put somewhere, newest
  first. It is a convenience, and losing it loses nothing. A version's
  bytes go only when the file itself does (`forget`).

- `dav.py` — WebDAV. `serve` is whitelisted for every DAV method and hands
  the request to wsgidav (MIT); `/api/method/<name>/<rest>` leaves the rest
  of the path alone, so the drive is at `…/dav.serve/My Files/…` with no
  process or port of its own. Signing in is with the person's email and a
  drive password (`Cloud Drive Password`, one per computer): `sign_in`, a
  before_request hook, checks it on the drive's address only, signs the
  person in and removes the header before Frappe's API-key check would
  refuse it — so it opens nothing else, and an email is never mistaken for
  an API key. Drive passwords are sixteen random letters, stored as a
  SHA-256 (a slow hash is for passwords people choose, and a drive checks
  one on every request). A Guest gets a Basic challenge. The provider walks names with
  `namespace.children` and changes things only through `api` and `upload`,
  so a drive can do exactly what the explorer can. Frappe answers OPTIONS
  itself, rolls back methods it does not know change things, reads the
  whole body before any method runs, and offers OAuth on a 401 — so
  `headers` (after_request) adds `DAV:` to OPTIONS and answers it 200,
  `serve` sets `flags.commit` for MKCOL, MOVE, COPY, LOCK and PROPPATCH and
  reads the body from werkzeug's cache, and the challenge goes through
  `response_headers`, which Frappe applies last. Locks are kept in Frappe's
  redis under the site's name, so every worker sees them. The empty file a
  client writes before the real one is not kept as a version. Bytes are
  read into memory on a PUT (Frappe has read them already), so a drive is
  for documents rather than for very large video.
  Windows (Map network drive), macOS (Connect to Server), Linux file
  managers and apps like Cyberduck all speak WebDAV. The whitelisted
  function may accept any HTTP method and return a response of its own, so
  PROPFIND, MKCOL, MOVE and LOCK reach `serve`, which gives back what
  wsgidav answers. Each drive password (`make_password`) is shown once and
  taken away on its own. Anywhere but the drive the same password is just a
  wrong API key. The Basic challenge is what makes the client ask. Every
  verb runs as the same person, under the same `namespace.may`. Writing a
  file whose name is there replaces it and keeps a version, and deleting
  sends it to the Recycle Bin. A folder is its own drive at the same URL
  with the folder's path after it, since clients mount any collection.

- `dav_locks.py` — a drive lock is the File's lease. wsgidav's lock
  storage (redis, under the site's name) is subclassed: a LOCK on a file
  takes the `dav` lease for its person with the lock's token as the
  lease's lock (so it is the sitting for merged versions) and its timeout,
  clamped to a minute to an hour (`seconds`); a refresh extends it, or takes
  it again once lapsed; UNLOCK, and wsgidav purging an expired lock, let it
  go; a lock that simply runs out ends with the lease's own `until`. A LOCK
  `lease.refused` for the DAV kind (somebody else alone, the asker in
  OneOS, anybody writing live) is deleted again and answered 423. A
  PROPFIND of the file's lockdiscovery, asked of the file itself, lists a
  made-up exclusive lock owned by "Samir Haddad (OneOS)" when it is held
  another way, which is what Word and Excel read to say who has it. A file
  first made under a lock (Finder locks a name, then writes it) adopts
  that lock as its lease (`adopt`). `FrappeSignIn.require_authentication`
  gives wsgidav the person's name, which it empties just before asking, so
  each lock has its principal and only they may UNLOCK it.

- `dav_saves.py` — saves from the drive (`save_into`). Refused 423 while
  somebody else holds the file alone. Without the saver's lock, a save from
  a version the file no longer holds goes beside it as "Name (Huda's
  copy).ext" (`copy_name`), and that person's saves on the file go into the
  copy for ten minutes. A version is its ETag, `tag`: id, a hash of the
  content's URL and size, so a rename does not change it. Where a save
  started is its If-Match, judged in `serve` before wsgidav would answer
  412, else the tag the same person last downloaded (twelve hours in the
  cache); neither means as before, over the file. The empty first write of
  a save from an older version writes nothing. Safe saves stay saves of
  the same File: a MOVE or COPY onto a file defers wsgidav's delete of it
  (`Document.delete` during MOVE or COPY at the destination) and makes the
  source the file's new version (Mac Office, Pages, TextEdit's `.sb-`
  files); a file moved aside to a temporary name (`temporary`: Word's
  ~WRL0001.tmp, Mac Office's Work File, `.sb-`, "(A Document Being Saved
  By …)") or deleted leaves its name for two minutes (`left`), and the same
  person's MOVE or PUT into that name brings it back (out of the Recycle
  Bin, or renamed back) and saves into it, the name it was put aside to
  answering DELETE as a `Ghost` (Word on Windows). The lease and the lock
  follow the File's id through all of it. A file deleted in OneCloud while
  somebody has it open (`lease.in_it`: the alone holder and everybody
  live) goes to the Recycle Bin and they get Deleted While Open.

- `mounts.py` and `doctype/cloud_mount` — servers as folders. A `Cloud
  Mount` keeps where a server is and the sign-in (password and key in
  Password fields, never sent to a browser); node ids are
  `@mount/<mount>/<path>`, so `api`'s verbs delegate to it without the
  explorer knowing — `make_folder`, `rename` and `delete` go to the server,
  and `_across` turns any move or copy between a server and OneCloud (or two
  servers) into bytes read and written, while a move within one server is
  its own rename. Paths are normalised under the mount's folder so none
  climbs out. SFTP is paramiko (LGPL, as a library); WebDAV is plain
  requests with a PROPFIND reader. Every connection is opened for one
  request and closed. `reachable` refuses an address that resolves to a
  private, loopback, link-local or reserved range — a mount is the
  workspace fetching an address somebody typed — unless the bench sets
  `onestorage_mounts_private`. Uploads into a server go through the
  workspace (`upload.here`), which holds the keys.
  A `Cloud Mount` also says who in the workspace may open it, and shows
  under **Network** as a folder like any other. Nothing is copied into File
  unless somebody copies it. Deleting on a server is deleting on the
  server, as there is no bin there. A mount is its maker's unless a
  Workspace Administrator has shared it with everyone on the team, and then
  every member of staff reads and writes it with the credentials it was
  made with. So only an administrator shares one.
  `onestorage_mounts_private` is for a developer's own machine.

- Search. `search` walks down from a folder (`below`) and matches names
  there. `everywhere` matches names across every live File, newest first,
  and keeps what `may` allows. Working out each file's space by walking up
  its folders would be a query per step per file, so `_folders` loads every
  folder once per request and `placed` walks that in memory. It also drops
  a file whose folder is in the Recycle Bin, since binning marks only the
  folder itself. Candidates are capped at ten times the 200 shown, so a
  reader who may open little of a large workspace can see fewer than they
  might. Servers are left out because they are read live.

- `file_requests.py`, `doctype/cloud_file_request` and `www/r.py` — asking
  for files. A `Cloud File Request` names where files land (`folder`, or
  `reference_doctype`/`reference_name`), what is asked (`items`: a label,
  required, several, extensions, and optionally an Attach field of the
  reference), who is asked (`recipients`, each with their own token) and
  what came (`uploads`). A token is 32 random characters shown once, in the
  email or the dialog; the row keeps its sha256 to find it by and the token
  itself encrypted, to put in a reminder. `/r/<token>` is a plain web page
  with a form per item posting to `send` — guest, POST, 120 an hour — which
  checks the kind, then works as the request's owner: `upload._place`
  writes each file, named after its item, and an item asked for once that
  is sent again becomes a new version of the first (`history.replace`), so
  the record's field and anybody's link keep pointing at one file. A field
  item sets `attached_to_field` and writes the file's URL into the field.
  `Requests` is a virtual node over the reader's own requests, and a
  request's node lists its uploads. `remind_due` runs
  daily. Why a doctype and not a flag on a folder: a request has people,
  a due date and a state per person, and a record's request has no folder
  at all.
  Items are named the way people ask, such as *passport copy* or *last
  three bank statements*. The page shows what has been sent and takes a
  replacement until the request is closed. An item that is not for a field
  goes into the request's own folder, made where the request was made and
  named after it, with a folder per person, by name, when several are
  asked. With no folder and a record, it goes onto the record. Either way it
  is a File like any other, with versions and a place in the explorer, and
  the request only lists it. A link is somebody's own, so it asks for
  nothing more. The person who made the request owns what arrives, and is
  told as it does.

- Size: `store.LARGEST` (5 GB) is every size limit Frappe has. The attach
  button's is System Settings (`unlimit`, on install and every migrate);
  every other request's is the site's `max_file_size`, which the site cannot
  set for itself, so admin writes it in `push_config` when it builds the
  site. Uploads that pass through the workspace (the attach button, a
  drive, a link, a server) hold the file in memory on the way; only the
  explorer's go straight to R2.
  It is what R2 accepts in one PUT. Size is not what a tenant is limited
  by. Their storage is, and admin refuses a put there is no room for.

### The rename from one_storage (P2.1)

The folder was `one_storage` and the module One Storage until 13 November
2026. `patches/storage_is_cloud.py`, first in patches.txt, renames the
Module Def with frappe's `rename_doc` (merged into the One Cloud that a
migrate's `sync_module_defs` has already made from modules.txt), which moves
every Link to it. It then moves what holds the names as plain text: Workspace
Sidebar's and Block Module's `module`, Record Head's folder, the Patch Log of
the five patches that moved with the folder (so none runs again), the
Scheduled Job Types' methods, and every Icon field that says `onestorage`;
the old Custom Icons go. `onedesk/one_storage/__init__.py` makes any old
dotted path import the new module for one release (RUN.md D4). Two
addresses keep the old name for good, since they are stored outside the
code: a stored file's URL (`store.FETCH`) and the drive's (`dav.MOUNT`);
hooks.py's `override_whitelisted_methods` sends both here. The site-config
keys `onestorage_on_disk` and `onestorage_mounts_private` keep theirs, since
a site that set one would silently lose it.

### Research and decisions

What was asked for, and what each became.

- **Files on R2.** Admin signs, R2 carries (above). A file uploaded through
  Frappe's own attach control passes through the workspace once on its way
  to R2 (the hook has the bytes); the explorer uploads straight from the
  browser to a signed URL, so a large file never touches the site at all.
- **Folders like a bucket's.** Folders are rows, not places: an object's key
  never says which folder it is in, so moving or renaming a folder is one
  database update and never copies a byte. That is what makes the next three
  cheap.
- **A folder per doctype and per record.** Derived, not stored. *Records ›
  Sales Invoice › ACC-SINV-2026-00001* is the files attached to that invoice,
  worked out from `attached_to_*` when it is opened; there is no folder row to
  keep in step with the record, and a record anyone may read shows its files
  to them and to nobody else. Dropping a file into a record's folder attaches
  it to the record.
- **A person's own folders.** Real folders under **My Files**, one per
  person, created the first time they open it.
- **SharePoint.** Team **libraries**: a folder with members and roles (read,
  edit, own), version history when a file is replaced, and the activity on
  it. Frappe's DocShare is the grant for one person on one file or folder,
  and a grant on a folder reaches everything in it.
- **Sharing outside.** A link (anyone with it, until a date, optionally with a
  password, view or download or upload) or an invitation to one address,
  which asks for a code sent there before it opens.
- **Any folder as a network drive.** WebDAV, served by wsgidav (MIT) from
  inside Frappe: `/api/method/` accepts any HTTP method and passes the rest of
  the path to the function, so PROPFIND and MKCOL reach it with no process of
  our own. A person signs in with their own API key and secret, which Frappe
  already accepts as Basic auth.
- **SFTP and WebDAV servers as folders.** A mount is a record — where, who as,
  which folder it appears in — and its contents are listed live from the
  server through the same namespace the explorer and WebDAV read. Nothing
  from it is copied into File unless somebody copies it.
- **An explorer everybody knows.** A navigation pane, an address bar that is
  also a path you can type, details and tiles, a preview pane, a context menu,
  drag and drop, and the keyboard shortcuts of Windows.

### The module's own files

What every module keeps (docs/READY.md, A module's folder), and what is
OneCloud's in each:

- `manifest.py` — its place in One: its Help pages in reading order, its
  screens (`frontend/src/cloud/`), and `no_roles`, since who may open a file
  is who it is shared with or who may open its record.
- `notifications.py` — the fourteen kinds of notification it sends, each
  with its channels and sender. Those that go to an address outside the
  workspace (`outside`) go by mail alone.
- `agent.py` — OneAI's three reads (`READS`), and `NOT_FOR_AI`: every call that
  changes something, with why OneAI suggests no card for it.
- `setup.py` — no steps: files go to storage from the first upload, and
  every folder, share and library is made where it is used.
- `tour.py` — one tour, of the explorer, at `onecloud-items`.
- `trust.py` — what OneCloud adds to the agreements: files kept in R2, links
  and file requests to people outside, OneAI's reading and making, office
  previews and OneOS.
- `public/js/one_cloud/cloud_control.js` — Settings, which has no tabs of
  its own yet and ends with the centres every module's does
  (`onedesk.centers.part("settings", …)`), opened from the top bar's tray; its foot is
  OneInterface's, as every module's is.
- `public/js/one_cloud/record_files.js` and `public/js/one_cloud/record_activity.js` are
  OneCloud's too: the Files and Activity tabs on every record.

### agent.py

Everything is read as the reader, through the explorer's own rule
(`namespace.may`), so a file OneAI may read is a file the reader may open. A
file's text goes to the model only when the reader asks about it, and
nothing of it is kept but the answer. Finding a file by what it says is
OneAI's `find_documents`, which already checks each hit the same way.
Sharing, moving and deleting stay the explorer's, where the reader sees what
they are doing.

What OneAI read of a file is read once per content, so a copy of a file
is found by what it holds. The reader may open the file (`_file`, the
explorer's own rule), so what OneAI read of it is theirs to see. Nobody
may read a Reading row by itself, which is why that read is not `get_list`.
