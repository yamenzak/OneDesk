---
name: passthrough
description: How to do a passthrough — one careful pass over a stated scope (a screen, a module, a flow, a set of files, the whole app) against named standards, ending with every finding fixed or written down and the scope marked passed. Load it before any review, walk, audit, sweep, cleanup or "go through X" request, whatever the code and whatever its focus (UI, words, docs, legal, performance, security, tests), and before calling one finished.
---

# Passthrough

A passthrough is one pass, not a tour. It has a scope you can list, a
standard you can name, and an end you can prove: every finding fixed or
written down, the gates green, the scope marked. Many passes have been done
here, each with its own focus; what keeps the next one from repeating them
is that this one says exactly what it covered and leaves a mark.

## Before starting: write the three lines

In the conversation, before touching anything:

- **Scope.** The list, item by item: the screens (as the stamp names them,
  `Form/Sales Invoice`, `List/Customer`, `onemail`), the files, or the flows
  ("pay a supplier invoice"). If it can't be listed it is too big; split it.
- **Standard.** The skills and documents this pass checks against: `ui`,
  `ux`, `wording`, `docs`, `changelog`, `legal`, a module's AGENTS.md, a
  READY point, a guard. A pass with no named standard turns into taste.
- **Done.** What has to be true at the end of each item, usually: looked
  at, fixed, gates green, docs and version updated, stamped, committed.

Then check what earlier passes already did: `docs/PASSOVER-LOG.md` (where
every area stands, and when it was last passed), `git log --grep` the
scope, the module's SCRATCHPAD, and `one_interface/stamps.py` `PASSED`. A
screen stamped Passed is not passed again unless it changed since its day.
A screen's pass also holds it to `docs/PASSOVER.md`'s seventeen points.

## Each item, in this order

1. **Make it real.** Seed demo data if the item is empty; sign in as the
   person whose work it is (the `ui` skill's list of demo users). Read the
   code behind it before judging what it does.
2. **Look.** The screen at 1440 and at 390, in Arabic and in the dark
   theme, at 2x cropped to each part; the empty state and one error on
   purpose. For code: run it, read its tests, read what calls it.
3. **Hold it to each standard**, one at a time, writing the findings as a
   list. A finding names the place and the rule it breaks.
4. **Fix all of it**, where it is made (the renderer, the registry, the
   shared helper), never by patching this one item. A fix that only the
   user can decide is a question, asked once, with a recommendation; the
   rest of the item carries on.
5. **Look again** at what changed, the same way as step 2.
6. **Close it**: the gates (below), translations for every new string, the
   module's Help page and its pictures if what people see changed (`docs`
   skill), a version (`changelog` skill), the overrides ledger if a frappe
   method is wrapped, and for a screen its entry in `stamps.py` `PASSED`
   with today's day and this pass's name.
7. **Commit** the item, or a few small ones, with the findings and what was
   done in the message.

## Rules that keep a pass honest

- **The scope is the scope.** Something wrong outside it goes in that
  module's SCRATCHPAD, one line, not into this commit.
- **Fix, don't note,** inside the scope. A list of findings handed back
  with nothing fixed is a report, not a pass.
- **Measure what can be measured** before and after: counts of strings,
  guards, untranslated entries, warnings, files.
- **Never call an item passed from the code alone,** or from a screenshot
  of a record that already existed. Make one.
- **A guard that fails is the item failing,** not the guard. Rewriting a
  guard to pass is a decision for the user.
- **The browser suite is not a gate.** Run one spec by name only when
  asked.
- **Stop at the end of the list.** A pass that keeps finding new scope is
  two passes; finish this one and say what the next would be.

## Claude's passthrough habits, and what to do instead

- **Calling it done after looking at the desktop in English.** Phone,
  Arabic and dark find a third of the problems.
- **Fixing the symptom on one screen.** The next screen has it too; fix
  the part that draws it.
- **Forgetting the paperwork.** A changed screen with an old Help picture,
  no version and no translation is not passed.
- **Re-doing a pass that was already done** because nothing said it was.
  Read the log and the stamps first, and leave both behind.
- **Turning one pass into a redesign.** Changes the user did not ask for
  go to them as a question.

## Finishing

Every item is stamped or listed as not passed with the reason, and the
area's row in `docs/PASSOVER-LOG.md` says what this pass did and its day
(the log is kept short: a row per area, not a row per pass). Run the
gates, which take minutes between them:

    python3 -m pytest -q
    cd frontend && npx vitest run && npx eslint src && npx vite build   # when frontend source changed

Report in one or two sentences: the scope, how many items passed, the one
thing left open. The commit messages carry the detail.
