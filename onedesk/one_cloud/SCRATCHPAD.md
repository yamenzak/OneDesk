# OneCloud: scratchpad

Known issues and plans, kept short. Something done leaves it.

## Not built

- **OneCode's repositories**, which will be folders with history.
- **Settings of its own.** OneCloud's ControlCenter has no tabs yet and opens
  on its centres. Drive passwords and the server connections are the first
  candidates, both kept in dialogs today.
- **OneAI cards.** Every call that changes something is in `ai.py`
  NOT_FOR_AI. Sharing, moving and making a folder are the first that could
  be cards.
- **Read-only in OneOS.** Somebody else's OneOS lease opens the viewer,
  since the container has no read-only mode yet.

## Known issues

- **OneCloud inside something else** (a record's files, the picker) still
  draws its own bar, frappe-ui's white view toggle and a filled preview;
  on its page it wears the list's head and card since 8 November 2026. Give
  the dialog the same card, band and outlined preview. (From docs/BACKLOG.md.)
- **The drive's upload is read whole.** frappe can now stream a request
  (`streaming_request_paths`, since the 2026-11-03 checkpoint); a drive PUT
  is still read into memory. (From docs/BACKLOG.md.)
- **Help has no pictures yet.** What OneCloud Is, Using the Explorer,
  Sharing Outside the Team and Asking for Files each want one, taken on the
  demo workspace.
- **Who may share is OneCloud's own.** Its shares and library members go
  through `rights.share`, but with frappe's read, write and share bits, not
  abilities; docs/BACKLOG.md, OneAccess, is where they become one Share.

## How it was built

1. **The place and the store.** OneCloud in the dock; every new file kept in
   R2 through admin's signed URLs; files already on the server moved each
   night.
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
9. **File requests.** Ask people for files by name, into a folder or onto a
   record's fields, through a link that needs no account.
