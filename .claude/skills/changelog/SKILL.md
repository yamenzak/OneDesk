---
name: changelog
description: How to write a module's version — the entry in onedesk/<module>/updates/<version>.md that What's New shows — what kind it is, what its title and words say and never say, when it carries a picture or a clip, and how it links to Help. Load it whenever lint.py says a module changed since its version (module-versioned), before running scripts/version.py, and before writing or editing any changelog entry.
---

# Changelog

Every change to what a module ships is a version (`module-versioned`, point
15), and What's New shows it to the people using the module, with a dot
until read. So it is written for them: what they can do now, or what
changed for them. It is not a commit message. `docs/READY.md`, Versions and
What's New, is the mechanism.

## Making one

    python3 scripts/version.py <folder> <major|minor|fix> "<Title>"

writes the next file with its front matter; fill in the words and, when it
applies, `docs:`. READY.md's **Which number moves** decides the kind
(`versions-follow`): major when something people already use works
differently or is gone, minor for something new to do (or any change to
what the module agrees to), fix when it now does what Help already says.
Torn between two, take the bigger. A major is decided with the user.

A day's work in a module is one version. `version.py` refuses a second the
same day (a bigger kind renumbers today's, keeping its words), and
`scripts/close.py` keeps today's version on the fingerprint after it is
committed: add each later change to its words. Order the words by what
matters to the reader, not by when each was done.

## The title

Five words or fewer, sentence case, the change from the reader's side:
"Pay several invoices at once", "Delete buttons are red again". Not a
feature's internal name, not "Improvements", not a number.

## The words

One short paragraph, or a short list for several separate things. An app is
`{one_mail}`, One `{one}` (`names-are-code`). Say:

- **What people can do now,** or what looks or works differently, by the
  names on the screen, in bold where they would click.
- **Who it is for,** when not everybody: "If you approve leave, …".
- **What they need to do,** if anything: "Turn it on in **Settings**."

Never (`versions-for-people` catches the code names):

- Code names, or a supplier's unless it is on the screen.
- What we refactored, if nobody sees it: say the one thing they might
  notice ("Opening a record is quicker."), never invent one.
- "We're excited", "improved experience", "various fixes", "as requested",
  blame, apology, a promise of what comes next. English only.

## Pictures and clips

Only when the change is new and something to see: a new screen, a control
that moved. One per entry, beside it in `updates/<version>/`, named as
`![What it shows](<version>/<name>.png)`, made and limited as Help's (the
`docs` skill). A fix almost never needs one.

## Help and legal

`docs:` names the Help pages this version changed, by id; What's New shows
them as Read More and each page lists the version under Changed In. Change
the page in the same commit; with nothing to read on to, leave `docs:` out.

`legal:` is written by `version.py`. When a version moves what the module
agrees to (`legal-said`), the `legal` skill applies, and the words say what
changed for the reader in plain terms, never the clause.

## Before handing back

`../../env/bin/python scripts/lint.py`, then open What's New and read the
entry as somebody who missed the change.
