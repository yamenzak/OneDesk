# ShareCenter

One way to share anything. Planned on 30 October while building how a
presentation is shared, and kept here because it is not one module's.

Today there are three ways to share, each built for one module:

- **Inside the team:** frappe's `DocShare`, drawn by OneCloud's Share dialog
  (`one_storage/share.py`) for files and folders, and read by AccessCenter
  as "what one person was given on one record".
- **Files to outsiders:** OneCloud's `Cloud Link` (`one_storage/links.py`,
  `/s/<token>`): anyone with the link, optional password and expiry, or
  invited people with a mailed one-time code; download, upload, opened count.
- **Records to a customer or supplier:** OnePortal's `Portal Link`
  (`one_portal/share.py`, `/portal/l/<token>`): a quotation or a quote request
  sent to a party's contact, used up by the answer, not by being opened.

Forms will need a fourth (a token per recipient), and a code editor a fifth.
Plan: one ShareCenter, a service in `one` beside AccessCenter and AICenter,
that every module uses instead of writing its own.

- **One link doctype.** `Share Link` replaces Cloud Link and Portal Link:
  what (a file, a folder or any record), who (anyone with the link, invited
  people by mail, a party's contacts, or signed-in people only), the gates
  (password, last day, one-time mailed code, used up by an answer), and what
  the guest may do (view, comment, download and in which formats, upload,
  answer, edit). Token stored hashed, as both are now. Old rows move over and
  `/s/` and `/portal/l/` keep working.
- **One dialog.** The same Share dialog on every file, document, workbook,
  presentation, record and form: People (inside the team, `DocShare` as now),
  Link, and Invite. A module only says which of these it allows and what a
  guest may do.
- **One guest page, viewers per kind.** `/s/<token>` checks the gates once,
  then hands the guest to the viewer the module registered in a hook
  (`one_share_viewers`): the presentation player, a document reader, a
  read-only workbook, a folder listing, the portal's record page, a form, and
  later the code editor. Anything with live data is filled as the person who
  shared it and frozen for the guest.
- **One place to see it all.** Shared by Me for each person (every link and
  invite, opened when and by whom, revoke, extend), and for a workspace
  administrator every outside link in the workspace, with a switch per module
  (no public links, password always, longest life) and Revoke All for a person
  who leaves.
- **One log.** Every open, code asked, download and answer is a row the owner
  can read and AccessCenter can show; the Views count on a presentation is
  this log read back.
- **Order.** Build the doctype and guest page under OneCloud's links first,
  since its rules are the most complete; move OnePortal onto it; then add the
  viewers (presentation, document, workbook); forms and the code editor
  arrive already using it.


## Where it stands

The first viewer exists without the doctype: a presentation opened through a
OneCloud link (`/s/<token>`) is played on the link's page instead of being
downloaded, drawn as a screen draws it, filled as the person who shared it,
with Present Live and Views (`one_slide/shared.py`, `one_slide/AGENTS.md`).
The link's gates are OneCloud's, unchanged. When `Share Link` and the
`one_share_viewers` hook exist, this becomes the presentation's viewer.
