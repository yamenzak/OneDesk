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

**OneCloud** in the dock opens it. The rail has:

- **Files** — every file in the workspace you may open.
- **Setup › Storage Check** — whether files are going to cloud storage, and
  moving the ones that are still on the server.

## Where files are kept

Every file uploaded anywhere in One — attached to an invoice, dropped in a
chat, added to OneCloud — goes to cloud storage. Opening one fetches it
straight from there, so a large file never slows the workspace down. Nothing
changes in how you attach or open a file.

Files added before cloud storage was switched on stay on the server until
they are moved: **Setup › Storage Check › Fix** moves them all.

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
   restore; who may do what, decided in one place.
3. **The explorer.** The page itself: navigation pane, address bar, details
   and tiles, preview, context menu, drag and drop, keyboard, search; uploads
   straight to R2.
4. **Sharing inside the team.** People, view or edit, reaching everything in
   a folder; Shared with Me.
5. **Sharing outside.** Links and email invitations, and the page a guest
   sees.
6. **Libraries and versions.** Team libraries with members and roles, version
   history, recent and starred.
7. **WebDAV.** Any folder as a network drive in Windows, macOS and Linux.
8. **Mounts.** SFTP and WebDAV servers as folders.
