---
name: passthrough
description: How to do a passthrough — one careful pass over a stated scope (an app, a screen, a flow, a feature just built, a set of files, the whole app) against named standards, ending with every finding fixed or written down and the scope stamped. It is also the definition of done for a new app or feature. Load it before any review, walk, audit, sweep, cleanup or "go through X" request, before calling an app or a feature finished, whatever its focus (UI, words, docs, legal, permissions, OneAI, notifications, performance, security, tests).
---

# Passthrough

One pass, not a tour: a scope you can list, a standard you can name, and an
end you can prove (every finding fixed or written down, the gates green,
the scope stamped). The same list is what "done" means for a new app or
feature: a feature answers the points it touches, a new app all twenty.

The standard is `docs/STANDARD.md`, twenty points. `python3 scripts/lint.py
--point N` lists the rules holding point N (`docs/STANDARD-RULES.md` is the
same, generated); `docs/PASSOVER.md` is how one screen is walked;
`docs/READY.md` how a module is finished and taken live.

## Before starting: three lines

- **Scope.** Item by item: the app, its screens as the stamp names them
  (`Form/Sales Invoice`, `List/Customer`, `onemail`), a flow, the feature.
  If it can't be listed it is too big; split it.
- **Standard.** The points that apply, this skill and the ones it names
  (`ui`, `ux`, `wording`, `docs`, `changelog`, `legal`), the app's AGENTS.md.
- **Done.** Usually: looked at, fixed, gates green, Help, version and
  translations written, stamped, committed.

Then read what earlier passes did: `docs/PASSOVER-LOG.md`, `git log --grep`
the scope, the app's SCRATCHPAD, `one_interface/stamps.py` `PASSED`, and
the looks on its versions. Something stamped is not passed again unless it
changed since its day.

## The rules hold what is declared; the pass finds what is not

A rule holds what is declared, not what is missing. An action with no OneAI
card, an event with no notification, a record type with no icons all pass.
So for each point, run its rules, then do what they cannot:

- **Several companies (point 4).** The app's record types with a company
  field are its manifest's `companies`; `one/company.py` then shows Company
  as a column and filter once there are two. The demo's second company is
  Sahara Glass Saudi, in riyals (`one_demo/branch.py`): give it the app's
  records and a check that a person held to one company by a User
  Permission never sees the other's in `get_list`.
- **Permissions (point 18).** Read every `@frappe.whitelist` of the app (a
  read-only agent does it well). The OneGuard rules (`guard-unchecked`,
  `guard-get-writes`, `guard-guest-fields`) catch the shapes; what slipped
  past them before: raw SQL showing purchase prices to whoever reads an
  Item, `ignore_permissions` on another module's settings, `get_all` where
  user permissions should apply.
- **Who may read what.** For each record type, try one demo user per role
  with `frappe.get_list` and `has_permission`: reading more than the rule
  says is a leak, refused what the job needs is a wall. *Found:* every
  manager of another app read everybody's leave.
- **OneAI (point 16).** `oneai-reach` holds that each write has a card in
  `agent.py` `REACH` or a `NOT_FOR_AI` reason. Ask it for real: per role,
  five questions it asks every day and three things it wants done, each a
  tool, a case in `one_ai/evals.py` `CASES` (English and Arabic), or a
  reason; run `onedesk.one_ai.evals.run` with `only`. *Found:* HR could
  not ask who is in today.
- **Notifications (point 11).** List each moment somebody waits on
  somebody (to approve, an answer, something due or late, a hand-off) per
  role, beside the module's `notifications.py` `TYPES`. A moment without a
  type is a finding, and so is a type nobody waits on.
- **Quick actions.** On a record a role opens daily, the next thing it
  makes or opens is one click (`interface.links`, Create, Connections).
- **Help and versions (points 14, 15).** Reread every page and version of
  the app against today's screens and the `docs` and `changelog` skills;
  picture each page that needs one.
- **Native apps (points 4, 6).** Statuses, checks on save, mappers,
  precision, units and `base_` amounts are ERPNext's, never redone. Found
  once: stock added across companies, a bill shared by two orders counted
  on each. A screen outside the manifest's regions becomes frappe's own
  first, its OneAI context and links carried over.
- **Bespoke apps (points 7, 9).** Drawn after the app ISLANDS.md names
  (`screen-modelled-on`); live, so two people on one thing see each other's
  change without a refresh; every method checks the reader's right itself.
- **Deleting:** the Recycle Bin brings it back; a doctype of ours linking
  to any record goes in `ignore_links_on_delete`.
- **Speed:** time to a usable list, form and home, before and after
  (`~/tools/browser/speed.mjs`, a phone at 4x CPU).
- **A fresh site:** it works straight after the setup wizard.

## On every screen, by eye

- **Sizes:** 1440, 820 (where frappe's `hidden-md` hides a record's
  buttons), 390, and beside an open pane.
- **Looks:** light and dark, two palettes, Arabic (right to left) and
  German (the longest words). German finds a sentence built from a name and
  a verb phrase: write one sentence with the person as `{0}`.
- **People:** each role whose work it is, and one who may not. What they
  can't do is hidden or refused, never an error; a link they may not open
  says No access, not Page not found.
- **States:** empty, one, many, loading, an error on purpose, a draft, a
  cancelled record, another currency. Make the cancelled one if the demo
  has none, from something that moves no stock or money.
- **Keys:** Escape closes, Tab reaches every control, focus shows.
- **Reach:** found in Ctrl+K and pickers; nothing the reader can't open is
  on a rail, in search or in a picker. Back returns where they were, in
  that app's rail (`tests/browser/routes.mjs`).
- **Live:** change a record elsewhere while its screen is open and see it
  follow.

## Each item, in this order

1. **Make it real:** sign in as the person whose work it is (the `ux`
   skill's demo users) and make the record. For code, run it.
2. **Look** (above), at 2x cropped to each part.
3. **Hold it to each point;** a finding names the place and the rule.
4. **Fix all of it where it is made** (the renderer, the manifest, the
   shared helper), running `../../env/bin/python scripts/lint.py`. What
   only the user can decide is one question with a recommendation.
5. **Look again.**
6. **Close it:** `python3 scripts/close.py` (docs, the overrides ledger,
   today's version, strings to translate), then the version's words, Help
   and its pictures, the Arabic and German.
7. **Stamp it** and commit, the findings as PASSOVER.md's twenty-point
   table.

## Stamping

- **A screen:** its entry in `one_interface/stamps.py` `PASSED`, named as
  frappe routes to it, with the day and the pass (`stamps-dated`).
- **An app:** `python3 scripts/close.py --looked one_mail:copy,interface`
  after the commit, only for the hand points looked at; it writes `looked:`
  on the newest version, and a minor or major makes it stale
  (`ready-looked`).
- **The area:** its row in `docs/PASSOVER-LOG.md`.
- **What waits:** anything outside the scope is one line in that app's
  SCRATCHPAD or `docs/BACKLOG.md`; the app's own SCRATCHPAD is brought up
  to date.

## Keeping it honest

- **The scope is the scope;** outside it is a SCRATCHPAD line. Inside it,
  fix, don't note: findings with nothing fixed are a report.
- **Never passed from the code alone,** or from a record that already
  existed.
- **A rule that fails is the item failing;** changing a rule is the user's
  call. A bad practice found gets a rule first, then the fix.
- **Stop at the end of the list.** A pass that keeps finding scope is two.

Claude's habits here: calling it done after the desktop in English (phone,
Arabic and dark find a third of the problems); fixing the symptom on one
screen; trusting the rules for completeness; forgetting the paperwork (an
old picture, no version, no translation, no stamp); adding a mechanism
every app must answer without a line here; turning a pass into a redesign.

## Finishing

    ../../env/bin/python scripts/lint.py --all       # every rule and test, about a minute
    bench --site <dev site> execute onedesk.one_demo.check.run
    python3 scripts/overrides.py --check && python3 scripts/docs.py --check

READY.md's **The gates** is the full list. A failure from before the pass
is named in the report, not hidden. Report in a sentence or two: the
scope, how many items passed, the one thing left open.
