# OneCloud

Written by hand. What OneCloud does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneCloud is where the company's files are: the ones you keep for yourself,
the ones a team shares, and every file attached to a record anywhere in One —
an invoice's PDF, an employee's passport scan, a project's drawings — in one
place that works like the file explorer on your computer. Files are kept in
cloud storage, not on the server, so there is room for all of them.

## Finding your way

**OneCloud** in the dock opens the explorer, full width: its own folder tree
is the navigation, so the side panel starts closed. A workspace
administrator finds **Storage Check** — whether files are going to cloud
storage, and moving the ones still on the server — by right-clicking an
empty space in the explorer.

## What is in OneCloud

- **My Files** — your own folders and files. Nobody else sees them unless you
  share them.
- **Recent** — what you opened or added lately, newest first.
- **Starred** — what you starred (right-click › **Star**), to find it again.
- **Shared with Me** — what other people have shared with you.
- **Libraries** — your team's shared folders (below).
- **Company** — folders everybody in the company can open and add to. What
  you put there, you (or a workspace administrator) can rename, move and
  delete.
- **Records** — a folder for every kind of record that has files (Sales
  Invoice, Employee, Project…), and inside it a folder for each record, with
  the files attached to it. You see the records you may open, and nothing
  else. Dropping a file on a record's folder attaches it to the record.
- **Network** — SFTP and WebDAV servers you connected, as folders (below).
- **Requests** — the files you asked people for, and how far each has got
  (below).
- **Recycle Bin** — what you deleted, for thirty days. **Restore** puts it back
  where it was.

Every record in One — an invoice, an employee, a task — has a **Files** tab
at the end of its form, with the number of files beside it. It is this
explorer, opened on that record's folder: drop files in, preview, rename,
share, ask for files with **New › File request**, or click the path to open
the record in OneCloud. It appears once the record is saved. In the side
panel, **Files** with the same number opens the tab.

The upload dialog — behind every attach button, a picture in the text
editor, a comment's attachment — offers **OneCloud** beside My Device, Link
and Camera. It opens this explorer to choose a file from anywhere you may
open: double-click it, or select several and press **Attach**. The file is
attached without being uploaded again. A file uploaded through the dialog
that belongs to no record goes to your My Files.

Dragging a file between a record and one of your folders copies it — the
invoice keeps its PDF and your folder gets one too. Moving between your own
folders moves it. Two things with the same name in one folder are kept apart
as *Report (2).pdf*, the way your computer does.

## Using the explorer

It works the way the file explorer on your computer does.

- **The folder tree** on the left: click a folder to open it, the arrow to
  unfold it.
- **The address bar**: back, forward and up, then where you are. Click a
  part of it to go there, or click the empty space and type a path —
  `My Files/Projects/2026` — and press Enter. The search box looks through
  the folder you are in and every folder inside it; **Search everywhere**
  above the results widens it to every file you may open — My Files,
  Company, what is shared with you, your libraries and the files of every
  record you can see. At the top of OneCloud it searches everywhere to
  begin with. Right-click a result for **Open file location**. Servers
  under Network are not searched.
- **New** makes a folder (you name it straight away) or uploads files or a
  whole folder. Dragging files or folders from your computer onto the page,
  or onto a folder, uploads them there.
- **Details** and **Tiles** switch the view; click a column heading to sort
  by it. The **preview pane** shows the file you selected — pictures, PDFs,
  text, video and sound — with its size, date and owner.
- **Right-click** anything for what you can do with it: open, download, copy
  a link, cut, copy, paste, rename, delete.
- **Drag** files onto a folder to move them; hold Ctrl to copy instead.

What somebody else adds, moves or deletes shows up in the folder you have
open without refreshing, as it does in any list in One.

The keys you already know work: Enter opens, Backspace goes back, F2
renames, Delete deletes (Shift+Delete deletes for good), Ctrl+A selects
everything, Ctrl+X, Ctrl+C and Ctrl+V cut, copy and paste, Ctrl+Shift+N
makes a folder, Ctrl+F searches, Ctrl+Shift+F searches everywhere and F5
refreshes. Click, Ctrl+click and
Shift+click select one, a few or a run of files.

Where you are is in the page's address, so the browser's own back button
works and a link you send somebody opens the same folder for them, if they
may open it.

## Sharing with the team

Select a file or folder and press **Share** (or right-click › **Share…**).
Pick people, choose whether they can **view** or **edit**, and press Share.
They get a notification that opens it.

- Sharing a folder shares everything in it, including what is put there
  later.
- Someone who can edit can add, rename, move and delete inside it, and share
  it with others. Someone who can view can open and download.
- What was shared with you is in **Shared with Me**, with who shared it. You
  can copy things out of it into your own folders; moving them out is
  refused, since they are still the owner's.
- The Share dialog lists everyone who has it, and lets you change what they
  can do or take them off. Anybody can take themselves off.
- A file attached to a record is shared by sharing the record.
- Only people on the team can be given something here. For anybody else,
  make a link (below).

## Sharing outside the team

In the Share dialog, **Create link** makes a link for people who are not on
the team — a customer, a supplier, an accountant. It is copied for you to
paste into an email or a chat. You choose:

- **Who can open it**: anyone who has the link, or only people you invite by
  email. An invited person is emailed the link, and when they open it they
  type their address and are sent a code, so a forwarded link opens nothing
  for anybody else.
- **What they can do**: view; download; and for a folder, upload — a folder
  somebody can send you files into without an account. You are told when
  files arrive.
- **Until when**, and a **password** for an anyone-link.

The page they see shows the file, or the folder and everything in it now
(something you add later is there; something you delete is not). The links
on a file are listed in its Share dialog, with how often each was opened;
the cross takes one away at once. A link to a record's file can be made by
whoever may change the record.


## Libraries

A library is a folder a team shares — a department's documents, a project's
files — with its own members. **Libraries › New › Library** makes one, and
you are its owner. **Members** (the button at the top when you are in one)
adds people as:

- **Reader** — opens and downloads.
- **Member** — also adds, changes and deletes what is in it.
- **Owner** — also renames the library and says who is in it.

Only its members see a library, and leaving it (or being taken off) closes
it, even to what you put there yourself. A library always has an owner; a
workspace administrator can open every library, so none is ever lost.

## Versions and activity

Uploading a file with a name already in the folder asks whether to
**Replace** it or **Keep both**. Replacing keeps what it held as an earlier
version, and so does **Upload new version** (right-click a file). The
preview pane shows a file's versions — open any of them, or **Restore** one,
which keeps the current one as a version in turn — and its activity: who
made it, renamed it, moved it, shared it, made a link to it or replaced it.
A replaced file keeps its shares and its links.

## As a drive on your computer

Right-click a folder and choose **Connect as a drive…** (or right-click an
empty space for the folder you are in). The dialog gives its address and
how to add it — Windows *Map network drive*, macOS *Connect to Server*,
Linux *Other Locations*. You sign in with your email and a drive password:
**Make a password** makes one for a computer (say which), shown once. Make
one per computer; each is listed with when it was last used, and the cross
takes one away without touching the others. A drive password opens your
drive and nothing else — not One in a browser, not the API.

The drive then works like any other: open, save, drag in, rename, make
folders, delete. It holds exactly what you can open here and nothing else;
saving over a file keeps what it held as a version, and deleting sends it to
the Recycle Bin.

## Servers as folders

**Network › New › Server connection** connects an SFTP or WebDAV server — a
supplier's upload folder, an old file server, a NAS — and shows it as a
folder. Give it a name, the server and the sign-in (a password, or a private
key for SFTP), and optionally which folder on the server to start from. Its
files are read live from the server each time you open it; open, preview and
download them, make folders, rename and delete there, and drag files between
the server and your folders, which copies them. Deleting on a server deletes
on the server — there is no Recycle Bin there.

A connection is yours alone unless a workspace administrator ticks
*Everyone on the team*. Right-click it for **Edit connection…** and
**Disconnect**, which leaves the server as it was. OneCloud does not connect
to addresses on a private network.

## Asking for files

**New › File request** in any folder or record asks people — a supplier, a
new hire, a customer — for particular files by name: *Trade licence*, *Bank
letters*, *Passport*. Each person gets their own link by email (or, when the
workspace cannot send email yet, you copy each link and pass it on). The
link opens a page listing what is asked for; they send each file there
without an account, and can replace one they got wrong.

For each file you say:

- **File** — its name, as they will see it. What they send is saved under
  that name, so *Photo.jpg* rather than *IMG_4418.jpg*.
- **Required** — whether the request is finished without it.
- **Several** — whether they may send more than one.
- **File Types** — which kinds it may be, like `pdf, jpg`; anything else is
  refused on the page. Empty means any kind.
- **Record Field** — on a record, a field the file fills. Asking a new hire
  for *Photo* with the field *Image* sets the employee's photo when it
  arrives. A request that fills fields goes to one person.

Asked from a folder, files land in that folder, in a folder per person when
you ask several people. Asked from a record, they are attached to the
record. Asked from **Requests**, a folder for them is made in My Files.

**Requests** shows each request and how many people have sent everything.
Opening one shows what has arrived and from whom; right-click › **Progress…**
shows each person against each file, with their link to copy, **Remind**,
and **Close request**, after which the links take nothing more. You are told
as each file arrives. People who have not finished are reminded by email
three days and one day before the due date, and on it.

## Where files are kept

Every file uploaded anywhere in One — attached to an invoice, dropped in a
chat, added to OneCloud — goes to cloud storage. Opening one fetches it
straight from there, so a large file never slows the workspace down. Nothing
changes in how you attach or open a file.

Files added before cloud storage was switched on stay on the server until
they are moved: **Setup › Storage Check › Fix** moves them all.

## How big a file can be

Up to 5 GB, the most R2 takes in one upload, however it arrives — the
explorer, the attach button on a record, a drive, a link. What limits a
workspace is its storage, not the size of a file: an upload there is no
room for is refused.

## Opening a file

Clicking a file anywhere in One opens it from cloud storage in a new tab, or
saves it under its own name when you download it. A file only you may see
opens only for you and for people allowed to see the record it is attached
to; a link to it passed to anybody else shows them nothing. Public files —
a logo on a web page, a picture in an email — open for anybody.

## Under the hood

For the people who build OneCloud. OneAI does not read past this heading.

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
  file's URL is `/api/method/onedesk.one_storage.store.fetch?key=…`: Frappe
  counts any `/api/method/` URL as remote (`URL_PREFIXES`), so none of its
  disk checks apply to it, and fetching it checks the reader may open the
  file and redirects to a URL admin signed for a quarter of an hour.
  Keys are content-addressed (`files/<private|public>/<md5><ext>`), which is
  Frappe's own de-duplication by `content_hash` carried over: the same PDF
  attached to ten records is one object, deleted when the last File naming
  it goes.
- `file.py` — `CloudFile`, Frappe's File with three methods sent to R2
  instead of the disk: `get_content`, `exists_on_disk` (so de-duplication
  finds a stored twin) and `make_thumbnail` (made from the bytes and stored
  beside them).
- `ready.py` and `report/storage_check` — the Storage Check, on the shared
  check page (`public/js/check.js`). **Move** copies files still on the disk
  to R2 and points their rows, and the attach field each came through, at
  the stored copy; the copy on disk stays, because a public file's old URL
  may be written into a web page or an email template no row knows about.

- `namespace.py` — one tree of node ids over File: `@my`, `@company`,
  `@shared`, `@records[/<DocType>[/<name>]]`, `@bin`, and any File by name.
  Record folders are derived from `attached_to_*` each time they are opened,
  so there is nothing to keep in step with the record. **Who may do what is
  `may` and nothing else**: a record's file answers to the record; its owner
  may do anything; a portal user gets nothing more; a person's own folder is
  theirs; Company is every member of staff's to read and add to, and an item
  in it is its owner's or a Workspace Administrator's to change. `inside`
  works out a folder's space once for a listing rather than walking the
  chain per file. A folder's id is its path (Frappe names folders so), so
  renaming or moving one gives it and everything under it new ids — callers
  read ids fresh from a listing, never keep them.
- `api.py` — the verbs: listing, folders, resolve, make_folder, rename,
  move, copy, delete, restore, purge, empty_bin. Between a record and a folder a move is a
  copy, and a copy is a new File row naming the same object. Deleting a
  folder's item is a flag (`one_deleted`, custom/file.json) that hides it and
  everything under it; `purge_old` erases what is thirty days old, daily.

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
- `public/js/onecloud.js` (and `public/css/onecloud.css`) — the explorer,
  with two hosts: `page/onecloud`, and a record's Files tab. Each loads it
  with `frappe.require` the first time it is opened, so a desk that never
  opens OneCloud never downloads it. It draws and never decides: every list and
  every change is a call above, and a refused one shows the server's reason.
  The place is `?node=` in the address, so history, bookmarks and pasted
  links land in the same folder. View, sort and the preview pane are the
  reader's user settings (under File), and follow them to another browser.
  R2's bucket must allow a browser `PUT` from the workspace's origin (CORS);
  where it does not, uploads fall back to `here` on their own.
- `public/js/onecloud_picker.js` and `api.attach` — the upload dialog.
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

- `public/js/record_files.js` — the Files tab on every record. Frappe draws
  a form from `Layout.get_doctype_fields`; that is wrapped to append a Tab
  Break and an HTML field. So the tab is on every doctype, erpnext's and
  hrms's included, and no field is written to any of them. Child tables,
  Singles and File are left out. The HTML field holds the explorer in room
  mode: `room` is `@records/<doctype>/<name>`, there is no tree and no
  back/forward, going anywhere else opens the OneCloud page, and the address
  is not touched. The tab hides on an unsaved record. Its count starts from
  the form's docinfo and then follows each listing. When the two disagree,
  the sidebar reloads its docinfo, so the timeline notices a file added
  through the tab. The sidebar's own Attachments section is reduced to one
  row, Files and the count, that opens the tab. Its list, Show All and its
  uploader are hidden (desk.css, loaded always, unlike onecloud.css).

- `public/js/record_activity.js` — the Activity tab, last, on every record
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
  read to view, write to edit. `namespace.granted` reads the shares on an
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

- `library.py` — team libraries. A library is a folder flagged `one_library`
  under `Home/Libraries` (hidden from Company like Attachments), and its
  members are DocShares on it with the role in the bits: Reader (read),
  Member (write), Owner (write and share). `namespace._library_may` is asked
  before an item's owner is, so membership is the only way in; renaming or
  deleting the library itself is an owner's; a Workspace Administrator may
  do anything. The last owner cannot be taken off.
- `history.py` and `doctype/cloud_file_version` — versions, Recent, Starred
  and activity. Replacing points the File at the new object and writes the
  old one down as a `Cloud File Version`; the File keeps its name, so shares
  and links follow. `store._named_elsewhere` counts versions, `fetch` opens a
  version for whoever may open its file, and a File's versions (and their
  objects, if unnamed) go when it does. Recent is a capped list per person in
  the cache, fed by `fetch` and uploads; Starred is `_liked_by`, written
  directly so a star neither comments nor notifies. Activity is Info comments
  written by the verbs, read back with the versions.

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

- Size: `store.LARGEST` (5 GB) is every size limit Frappe has. The attach
  button's is System Settings (`unlimit`, on install and every migrate);
  every other request's is the site's `max_file_size`, which the site cannot
  set for itself, so admin writes it in `push_config` when it builds the
  site. Uploads that pass through the workspace (the attach button, a
  drive, a link, a server) hold the file in memory on the way; only the
  explorer's go straight to R2.

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

What is not built: creating documents, sheets and slides here (OneWriter,
OneWorkbook and OneSlide will make them into OneCloud folders), and OneCode's
repositories, which will be folders with history.

### The plan

1. **The place and the store.** OneCloud in the dock; every new file kept in
   R2 through admin's signed URLs; files already on the server moved by the
   Storage Check. *Done.*
2. **The namespace.** My Files, Shared with Me, Libraries and Records as one
   tree of paths; create, rename, move, copy, delete to a recycle bin and
   restore; who may do what, decided in one place. *Done.*
3. **The explorer.** The page itself: navigation pane, address bar, details
   and tiles, preview, context menu, drag and drop, keyboard, search; uploads
   straight to R2. *Done.*
4. **Sharing inside the team.** People, view or edit, reaching everything in
   a folder; Shared with Me. *Done.*
5. **Sharing outside.** Links and email invitations, and the page a guest
   sees. *Done.*
6. **Libraries and versions.** Team libraries with members and roles, version
   history, recent and starred. *Done.*
7. **WebDAV.** Any folder as a network drive in Windows, macOS and Linux.
   *Done.*
8. **Mounts.** SFTP and WebDAV servers as folders. *Done.*
9. **File requests.** Ask people for files by name, into a folder or onto a
   record's fields, through a link that needs no account. *Done.*
