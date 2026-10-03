# OneCloud

Written by hand. What OneCloud does and how to use it. Everything above
**Under the hood** is written for the people who use it, and OneAI reads it to
answer "how do I…" questions. Under the hood is for the people who build it.

OneCloud holds the company's files in one place: your own files, files your
team shares, and every file attached to a record in One, such as an
invoice's PDF or an employee's passport scan. It works like the file
explorer on your computer. Files are kept in cloud storage, not on the
server.

## Finding your way

**OneCloud** in the dock opens the explorer at full width. The folder tree on
the left is the navigation, so the side panel starts closed.

Workspace administrators can open **Storage Check** by right-clicking an
empty space in the explorer. It shows whether files are going to cloud
storage and moves any still on the server.

## What is in OneCloud

- **My Files**: your own folders and files. No one else sees them unless you
  share them.
- **Recent**: files you opened or added lately, newest first.
- **Starred**: files and folders you starred (right-click › **Star**).
- **Shared with Me**: what other people shared with you.
- **Libraries**: folders shared by a team (see below).
- **Company**: folders everyone in the company can open and add to. You can
  rename, move and delete what you added. So can a workspace administrator.
- **Records**: a folder for each record type that has files (Sales Invoice,
  Employee, Project…), with a folder for each record inside it. You only see
  records you can open. Dropping a file on a record's folder attaches it to
  that record.
- **Network**: SFTP and WebDAV servers you connected (see below).
- **Requests**: files you requested from people, and their progress (see
  below).
- **Recycle Bin**: deleted items, kept for 30 days. **Restore** puts an item
  back where it was.

### Files on a record

Every record in One has a **Files** tab at the end of its form, with the
number of files beside it. The tab is this explorer, opened on the record's
folder. You can drop files in, preview, rename, share and request files
with **New › File request**. Click the path to open the record's folder in
OneCloud. The tab appears once the record is saved. **Files** in the side
panel opens the same tab.

### Attaching from OneCloud

The upload dialog (any attach button, an image in the text editor, a
comment's attachment) has a **OneCloud** option next to My Device, Link and
Camera.

1. Choose **OneCloud**.
2. Double-click a file, or select several and press **Attach**.

The file is attached without uploading it again. A file uploaded through the
dialog that isn't attached to a record goes to your My Files.

### Copying and moving

- Dragging a file between a record and one of your folders copies it. The
  record keeps its file and your folder gets a copy.
- Dragging between your own folders moves it.
- Two items with the same name in one folder are kept as *Report.pdf* and
  *Report (2).pdf*.

## Using the explorer

- **Folder tree**: click a folder to open it, or the arrow to expand it.
- **Address bar**: back, forward and up, then the current path. Click part of
  the path to go there, or click the empty space, type a path such as
  `My Files/Projects/2026` and press Enter.
- **Search**: searches the current folder and its subfolders. **Search
  everywhere** widens it to every file you can open: My Files, Company,
  Shared with Me, your libraries and the files of every record you can see.
  At the top level of OneCloud it searches everywhere by default.
  Right-click a result for **Open file location**. Servers under Network
  aren't searched.
- **New**: create a folder, or upload files or a whole folder. You can also
  drag files or folders from your computer onto the page or onto a folder.
- **Details** and **Tiles** switch the view. Click a column heading to sort
  by it.
- **Preview pane**: shows the selected file (images, PDFs, text, video and
  audio) with its size, date and owner.
- **Right-click** an item to open, download, copy a link, cut, copy, paste,
  rename or delete it.
- **Drag** items onto a folder to move them. Hold Ctrl to copy instead.

Changes other people make appear in the open folder without refreshing.

**Keyboard shortcuts**

| Key | Action |
| --- | --- |
| Enter | Open |
| Backspace | Back |
| F2 | Rename |
| Delete | Move to Recycle Bin |
| Shift+Delete | Delete permanently |
| Ctrl+A | Select all |
| Ctrl+X, Ctrl+C, Ctrl+V | Cut, copy, paste |
| Ctrl+Shift+N | New folder |
| Ctrl+F | Search |
| Ctrl+Shift+F | Search everywhere |
| F5 | Refresh |

Click, Ctrl+click and Shift+click select one item, several items or a range.

The current folder is in the page's address, so the browser's back button
works. A link you send to someone opens the same folder for them, if they
have access to it.

## Sharing with the team

1. Select a file or folder and press **Share** (or right-click › **Share…**).
2. Add people and choose **View** or **Edit**.
3. Press **Share**. They get a notification that opens it.

- Sharing a folder shares everything in it, including what's added later.
- People who can edit can add, rename, move and delete inside it, and share
  it with others. People who can view can open and download.
- **Shared with Me** lists what was shared with you and who shared it. You
  can copy items from it into your own folders, but not move them, since
  they still belong to the owner.
- The Share dialog lists everyone with access. You can change their access
  or remove them. Anyone can remove themselves.
- A file attached to a record is shared by sharing the record.
- Only people on the team can be added. For anyone else, create a link.

## Sharing outside the team

In the Share dialog, **Create link** makes a link for people outside the
team, such as a customer, supplier or accountant. The link is copied so you
can paste it into an email or chat. You choose:

- **Who can open it**: anyone with the link, or only invited people. Each
  invited person is emailed the link. When they open it, they enter their
  email address and get a code, so a forwarded link doesn't work for anyone
  else.
- **What they can do**: view, download, and for a folder, upload. With
  upload on, people can send you files without an account. You're notified
  when files arrive.
- **Expires on**, and a **Password** for a link anyone can open.

People with the link see the file, or the folder and its current contents.
Files you add later appear, and files you delete don't.

A file's Share dialog lists its links and how often each was opened. The
cross removes a link at once. Anyone who can edit a record can create a link
to its files.

## Libraries

A library is a folder shared by a team, such as a department's documents or
a project's files, with its own members.

1. Go to **Libraries** and choose **New › Library**. You're its owner.
2. Inside the library, press **Members** to add people with a role:
   - **Reader**: can view and download.
   - **Member**: can also add, change and delete files.
   - **Owner**: can also rename the library and manage members.

Only members see a library. If you leave or are removed, you lose access,
including to files you added. A library always has at least one owner.
Workspace administrators can open every library.

## Versions and activity

When you upload a file with the same name as one in the folder, you can
**Replace** it or **Keep both**. Replacing keeps the old file as an earlier
version. So does **Upload new version** (right-click a file).

The preview pane shows a file's versions. You can open any of them, or
**Restore** one, which keeps the current file as a version. It also shows the
file's activity: who created, renamed, moved, shared, linked or replaced it.
A replaced file keeps its shares and links.

## As a drive on your computer

You can open a OneCloud folder as a network drive on your computer.

1. Right-click a folder and choose **Connect as a drive…** (or right-click an
   empty space for the current folder).
2. Copy the address and add it as a drive: *Map network drive* on Windows,
   *Connect to Server* on macOS, *Other Locations* on Linux.
3. Sign in with your email and a drive password. Press **Create password**,
   name the computer, and copy the password. It's shown only once.

Create one password per computer. Each is listed with when it was last used,
and the cross removes one without affecting the others. A drive password
only opens your drive. It doesn't work for One in a browser or for the API.

The drive works like any other: open, save, drag in, rename, create folders
and delete. It shows exactly what you can open in OneCloud. Saving over a
file keeps the old one as a version, and deleting moves it to the Recycle
Bin.

## Servers as folders

**Network › New › Server connection** connects an SFTP or WebDAV server, such
as a supplier's upload folder, an old file server or a NAS, and shows it as a
folder.

1. Enter a name and the server.
2. Enter the user name and a password, or a private key for SFTP.
3. Optionally set the folder on the server to start from.

Files are read live from the server each time you open the folder. You can
open, preview and download them, create folders, rename and delete, and drag
files between the server and your folders, which copies them. Deleting on a
server deletes the file on the server. There's no Recycle Bin there.

A connection is private to you unless a workspace administrator ticks
**Share with everyone on the team**. Right-click it for **Edit connection…**
or **Disconnect**, which leaves the server unchanged. OneCloud doesn't
connect to addresses on a private network.

## Asking for files

A file request asks people, such as a supplier, new hire or customer, for
specific files by name: *Trade licence*, *Bank letters*, *Passport*.

1. In any folder or record, choose **New › File request**.
2. Enter a title, the recipients' email addresses, and optionally a due date
   and a message.
3. Add each file you need (see below) and press **Send request**.

Each person gets their own link by email. If the workspace can't send email
yet, copy each link and send it yourself. The link opens a page listing the
files. They upload each one there without an account, and can replace a file
they got wrong.

For each file:

- **File**: its name, as they'll see it. What they send is saved under this
  name, so *Photo.jpg* rather than *IMG_4418.jpg*.
- **Required**: whether the request is complete without it.
- **Multiple**: whether they can send more than one.
- **File Types**: allowed types, like `pdf, jpg`. Other types are refused.
  Leave empty to allow any type.
- **Record Field**: on a record, a field the file fills. For example, asking
  a new hire for *Photo* with the field *Image* sets the employee's photo
  when it arrives. A request that fills fields can go to one person only.

Where files go:

- From a folder: a new folder inside it, named after the request, with a
  folder for each person when you ask several people.
- From a record: attached to the record.
- From **Requests**: a new folder in My Files.

**Requests** lists each request and how many people have sent everything.
Open one to see what arrived and from whom. Right-click › **Progress…** shows
each person against each file, with their link to copy, **Remind** and
**Close request**. Once closed, the links no longer accept files.

You're notified as each file arrives. People who haven't finished get an
email reminder three days and one day before the due date, and on the day.

## Where files are kept

Every file uploaded anywhere in One goes to cloud storage, whether it's
attached to an invoice, dropped in a chat or added to OneCloud. Files open
straight from cloud storage, so large files don't slow the workspace down.
Attaching and opening files works the same as before.

Files added before cloud storage was turned on stay on the server until
they're moved. **Setup › Storage Check › Fix** moves them all.

## How big a file can be

Up to 5 GB per file, the most R2 accepts in one upload. This applies however
the file arrives: the explorer, a record's attach button, a drive or a link.
The real limit is the workspace's storage. An upload is refused when there
isn't room for it.

## Opening a file

Clicking a file anywhere in One opens it from cloud storage in a new tab.
Downloading saves it under its own name.

A private file opens only for you and for people who can see the record it's
attached to. Anyone else who gets the link sees nothing. Public files, such
as a logo on a web page or an image in an email, open for anyone.

## Asking OneAI

The OneAI panel in OneCloud knows the open folder and the selected file.

- With a file selected: **Summarise this file**, **Who can see this?** and
  **Find a file…**
- With nothing selected: **Find a file…** and **What is taking the space?**

**Find a file…** starts the question "Find the file that" for you to finish,
for example "…has our trade licence in it". It searches the contents of
files, not just their names. **What is taking the space?** lists your largest
files and how full the workspace's storage is.

OneAI only reads files you can open, and only when you ask. It doesn't change
anything in OneCloud. Sharing, moving and deleting are done in the explorer.

**Read with OneAI** on a file's menu has OneAI read that file now, file it
and act on it. On a folder, **Read with OneAI…** reads every new file that
arrives there. Scans and photos use OneAI credits.

With nothing selected, the preview pane shows the folder: how many folders
and files it holds and their total size. For your own folders, it also shows
who can see the folder and whether OneAI reads it.

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

- `public/js/record_files.js` — the Files tab on every record, declared as
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
