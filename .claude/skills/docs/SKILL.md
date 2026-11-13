---
name: docs
description: How to write a module's Help — the pages in onedesk/<module>/help/ that people open from the question mark — with the pictures and short clips (GIFs of nine seconds at most) beside them, and how Help links with What's New. Load it before writing or changing a Help page, taking a picture or recording a clip for Help or a version, and before changing what a screen does without changing its page.
---

# Docs

Help is for the person using One, about what they do, in their words. What a
claim rests on in the code goes in the module's AGENTS.md. The `wording`
skill decides the words; this one what a page is, when it needs a picture
or a clip, and how it links to What's New. Point 14 of `docs/STANDARD.md`
holds it (`python3 scripts/lint.py --point 14`); `docs/READY.md`, Docs and
Help, is the mechanism.

## A page

- **One page per thing people do,** named as they would say it: Connecting
  a Mailbox. Listed in the manifest's `help`, with an icon, in reading
  order (`help-listed`); the first says what the module is.
- **Scanned, not read:** a line or two on what the page is for, then `##`
  sections of five words or fewer (`help-sound`); a table for anything
  parallel, numbered steps for anything in order, one blockquote for the
  one thing worth knowing.
- **Says where things are** by the names on the screen, in bold.
- **Links pages** by id, `[Settings](settings)`. A page that only points
  elsewhere is a section of that page.
- **Never names code** (`help-names-no-code`), a doctype not on the screen,
  frappe or ERPNext. An app is `{one_cloud}`, One `{one}`, filled from its
  manifest (`names-are-code`). English only.
- **Changes with the screen,** page and picture in one commit.

## Where what a page says comes from

frappe, ERPNext and HRMS explain most of what their records do
(docs.frappe.io/erpnext, docs.frappe.io/hr). Read them for what is true,
then write it in our words. Never copy or closely follow their sentences,
link to them or name them: their docs are CC BY-SA, and a copied sentence
would carry their licence. Where they are thin, read the code.

Explain each field, status and step a label doesn't, once, where it is
used. No history, theory or tour of every setting; and a page that only
restates the labels says nothing, so it is no page.

## Pictures and clips

A picture earns its place where words would have to describe where
something is or what a result looks like; one per section at most.

- **Cropped** to the part, taken at 2x as the person whose work it is
  (`~/tools/browser/helpshot.mjs`), scaled to 1600 wide. Demo data only;
  light, English, no tour or stray menu.
- **Under 1 MB,** `.png` for screens (`help-pictures-small`). Its alt text
  is its caption: "OneMail with a conversation open".
- **A clip** is for motion the eye must follow: a drag, something
  appearing, two to four steps. Nine seconds at most, 4 MB, a `.gif`
  (`help-clips-short`), made with `scripts/clip.mjs` (its docstring has
  the flags). Scope every selector to what is on top (`.modal.show …`).
  Look at a middle frame and its length before keeping it; re-record a
  clip that wanders rather than trim it.
- **Beside the page,** in `help/<page>/`, named for what it shows, and
  named in the page as `![What it shows](<page>/<name>.png)`
  (`help-pictures-there`, `help-pictures-used`).

Help draws them from R2 (`one/media.py`). An admin site sends what R2
lacks when it migrates; to send now, `bench --site <admin site> execute
onedesk.one_admin.media.push` and read what it says. AccessDenied means the
storage token predates the docs bucket: the user runs **Set Up Cloudflare**
again.

## Help and What's New

A version names the pages it changed in its front matter (`docs: settings,
rules`). What's New lists them as Read More, and each page ends with
Changed In. Name the page in that version's `docs:` (the `changelog`
skill); that is the whole link, both ways.

## Before handing back

`../../env/bin/python scripts/lint.py`, then open Help on the page and read
it as the person it is for.
