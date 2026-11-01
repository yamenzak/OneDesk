---
name: docs
description: How to write a module's Help — the pages in onedesk/<module>/docs/ that people open from the question mark — with the pictures and short clips (GIFs of nine seconds at most) beside them, and how Help links with What's New. Load it before writing or changing a Help page, taking a picture or recording a clip for Help or a version, and before changing what a screen does without changing its page.
---

# Docs

Help is for the person using One, in their words, about what they do. It is
not about the code: what a claim rests on goes in the module's AGENTS.md.
The `wording` skill decides the words; this one decides what a page is,
when it needs a picture or a clip, and how it links to What's New.

## A page

- **One page per thing people do,** named as they would say it: Connecting
  a Mailbox, Rules and Out of Office. Listed in the module's
  `ready.MODULES[...]["help"]` with an icon, in reading order; the first is
  What <Module> Is.
- **Scanned, not read:** a line or two that says what the page is for,
  then `##` sections of five words or fewer; a table for anything parallel,
  numbered steps for anything done in order, one blockquote for the one
  thing worth knowing.
- **Says where things are** by the names on the screen, in bold: **Save**,
  **Settings**, the cog at the foot of the rail.
- **Links pages** by their id: `[Settings](settings)`. A page that only
  points elsewhere is a section of that page instead.
- **Never names code,** a doctype that isn't on the screen, frappe or
  ERPNext. English only, like the agreements; the screens around it are
  translated.
- **Changes with the screen.** A commit that changes what people see
  changes the page and its picture in the same commit.

## When a page needs a picture

A picture earns its place when the words would otherwise have to describe
where something is or what a result looks like. One per section at most,
usually one per page.

- **Cropped** to the part the section is about, not the whole window,
  taken at 2x (`DSF=2` in the shot scripts) and scaled down, so it stays
  sharp.
- **Demo data only,** signed in as the person whose work it is. No real
  names, addresses or anything from a customer.
- **Light theme, English, the Canvas look,** no tour, no open menu that
  isn't the point.
- **Under 1 MB,** `.png` for screens, `.webp` or `.jpg` for photographs.
- **Its alt text is its caption:** what it shows, in a sentence,
  "OneMail with a conversation open". Help shows it under the picture.

## When a page needs a clip

A clip is for motion the eye has to follow: dragging, something appearing
after a click, a short sequence of two to four steps. Not for a screen
that sits still, which is a picture.

- **Nine seconds at most,** 4 MB at most, a `.gif`. The guard refuses
  longer or larger.
- **Made with `scripts/clip.mjs`,** which records the demo workspace while
  a list of steps runs, starts once the screen settles, moves the pointer
  to each click and stops half a second after the last step:

      ONE_DEMO_PASSWORD=… PLAYWRIGHT_FROM=… CHROMIUM=… \
        node scripts/clip.mjs onedesk/<module>/docs/<page>/<name>.gif \
          --url /desk/<route> --user <demo user> --steps steps.json

- **Scope every selector** to what is on top (`.modal.show …`): a field of
  the same name behind a dialog takes the typing otherwise.
- **Look at it** before keeping it: a frame from the middle
  (`ffmpeg -i x.gif -vf "select=eq(n\,40)" -vframes 1 f.png`) and its length
  (`ffprobe`). Re-record rather than trim a clip that wanders.

## Where pictures and clips live

Beside the page that shows them, in `docs/<page>/`, named for what they
show (`docs/rules/new-rule.gif`), and named in the page as
`![What it shows](<page>/<name>.png)`. Never a link to an image anywhere
else.

Help draws each one from R2: the public `one-docs` bucket, at
`media.4dl.app/docs/<hash>.<kind>` (`one/media.py`), so the same picture
has the same address on dev and in production. Nothing to do by hand: an
admin site sends what R2 lacks whenever it migrates
(`one_admin/media.py`), so on dev `git pull` and `bench --site all migrate`
publish it. Until then the page falls back to the workspace's copy. To send
now: `bench --site <admin site> execute onedesk.one_admin.media.push`.

## Help and What's New read on to each other

A version names the pages it changed in its front matter
(`docs: settings, rules-and-out-of-office`). What's New lists them under
the version as Read More, and each of those pages ends with Changed In,
the versions that named it. So when a page changes because something new
shipped, name the page in that version's `docs:` (the `changelog` skill);
that is the whole of the link, both ways.

## Before handing back

    python3 -m pytest -q tests/guards/test_ready.py tests/guards/test_docs_media.py

`test_docs_media.py` fails on a picture that isn't there, one nothing
shows, one too large, a clip too long and a kind a browser might not show;
`test_ready.py` on a page not listed, a heading over five words, code
named in a page and a link to a page Help doesn't have. Then open Help on
the page and read it as the person it is for.
