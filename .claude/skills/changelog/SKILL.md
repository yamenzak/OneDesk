---
name: changelog
description: How to write a module's version — the entry in onedesk/<module>/docs/changelog/<version>.md that What's New shows — what kind it is, what its title and words say and never say, when it carries a picture or a clip, and how it links to Help. Load it whenever test_ready.py says a module changed since its version, before running scripts/version.py, and before writing or editing any changelog entry.
---

# Changelog

Every change to what a module ships is a version (`test_ready.py` holds the
fingerprint), and What's New shows each one to the people using it, with a
dot until they have read it. So an entry is written for them: what they
can do now, or what changed for them. It is not a commit message, and it is
not for us.

## Making one

    python3 scripts/version.py <folder> <major|minor|fix> "<Title>"

writes the next file with its front matter (version, date, kind, title,
fingerprint, `legal:`); fill in the words and, when it applies, `docs:`.

- **fix**: something worked wrongly and now works, or a small thing
  changed that nobody has to learn.
- **minor**: something new to do, or a screen people know works
  differently. Most versions.
- **major**: the module is a different thing to use: a new way of working,
  a screen replaced. Rare, and decided with the user.

Several changes on one day in one module are one version, not one each.
After the first, add each change to its words and run `scripts/close.py`,
which gives a version dated today the module's fingerprint even once it is
committed. `version.py` refuses a second version the same day, and a
bigger kind renumbers today's (a fix becomes the minor), keeping its words.
Order the words by what matters to the reader, not by when each was done.

## The title

Five words or fewer, sentence case, naming the change from the reader's
side: "One shape for dialogs", "Delete buttons are red again", "Pay
several invoices at once". Not a feature's internal name, not "Improvements",
not a version number.

## The words

One short paragraph, or a short list when there are several separate
things. Say:

- **What people can do now,** or **what looks or works differently**, by
  the names on the screen, in bold where they would click.
- **Who it is for,** when not everybody: "If you approve leave, …".
- **What they need to do,** if anything: "Turn it on in **Settings**."

Never:

- File, function, doctype or commit names; frappe, ERPNext, Cloudflare or
  any other supplier's name unless it is on the screen.
- What we refactored, renamed or moved, if nobody sees it. If nothing
  changes for anyone, say the one thing they might notice ("Opening a
  record is quicker.") and never invent one.
- "We're excited", "improved experience", "various fixes", "bug fixes and
  performance improvements", "as requested", blame, apology.
- A promise of what comes next.
- Anything the `wording` skill forbids. English only, like Help.

## Pictures and clips

Only when the change is something to see and new: a new screen, a control
that moved, a result that looks different. One picture or one clip per
entry, beside it in `docs/changelog/<version>/`, named in the words as
`![What it shows](<version>/<name>.png)`. The same limits and the same way
of making them as Help's (`docs` skill): cropped, demo data, a clip nine
seconds at most made with `scripts/clip.mjs`. They reach R2 the same way.

A fix almost never needs one. A clip is for a change you have to see
moving to understand.

## Linking to Help

`docs:` names the Help pages this version changed, by id:

    docs: settings, rules-and-out-of-office

What's New shows them under the entry as Read More, and each page ends
with Changed In, listing this version. Name a page whenever the version
changed what it says; change the page in the same commit. A version with
nothing in Help to read on to leaves `docs:` out.

## Legal

`legal:` is written by `version.py`: a hash of the module's own part of each
agreement. When a version changes what the module agrees to, the `legal`
skill applies and the words say what changed for the reader in plain
terms, never the clause.

## Before handing back

    python3 -m pytest -q tests/guards/test_ready.py

It fails on a title over five words or not in sentence case, words naming
code, a `docs:` page Help doesn't have, versions out of order for their
kind and a fingerprint that isn't the module's. Then open What's New on the
version and read it as somebody who missed the change.
