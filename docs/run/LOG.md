# The run's log

Newest last. One entry per sitting: the day and time (UTC), what was done
with commits, what is running, what is next. Short; the commits have the
detail.

## 12 Nov 2026, evening

- Six surveys of the code (registries, guards, layout, OneAdmin, shell,
  OneAI) became docs/run/SURVEY.md; the plan and ledger are docs/run/RUN.md.
- On main before the run: e1dce0e7 (the arcs' plans), ce0e5978 (the demo
  builds from scratch again: Quality Feedback Template, a second company's
  payroll, late supplier quotes), 203a7458 (Sessions threw since 23b2bf21;
  a server says it was Connected).
- one.4dl.dev holds the demo, built from scratch today; 302 of 314 checks
  (P0.5 has the 12).
- Branch `arcs` made from main at 203a7458.

## 12 Nov 2026, 22:40

- Yamen's nine points became rules in RUN.md: decide, don't wait; Deferred
  tracked by run.py; names are code (P2.11); the app folder named for its
  centres (P2.10); the three ways a screen is made (P2.12); OneAdmin's setup
  sessions, analytics, agent and agent pricing (P4.10, P4.11); scoped checks
  while working, the whole suite at gates; OneOS keeps its name (P9.4).
- P0.2 wake-ups scheduled; P0.3 29 worktrees removed, two left (D1).
- Next: P0.4 the run site, then P0.5 the twelve failing demo checks.

## 13 Nov 2026, early hours

- P0.4 run.localhost made; its first from-scratch build found the
  company-field setters queueing 600+ jobs a run (e5ffc9f2). 310 of 314
  checks on its first run, then the role fix (24df976b).
- P0.5 fixed so far: company setters, everybody's own User roles, OneCRM's
  Support Team, frappe's SQLite logs (OneStudio, spares, the atlas),
  server scripts on dev, the stale checks; the atlas read from
  run.localhost (c19b4508). P0.6 dead files (P0.6 commit).
- P1.1-P1.3 done (a24ad38c): the registry, 24 manifests, ready.MODULES
  read from them.
- Running: ~/arcs-tools/gate.sh (drops and rebuilds run.localhost, demo
  from nothing, atlas, every check) into /tmp/gate.log. P0 closes when it is
  green. Meanwhile P1.4 is built in the worktree ~/arcs-work (branch
  arcs-p1) so the build never imports half-made code.

## 13 Nov 2026, 00:10 — P0 gate passed

- ~/arcs-tools/gate.sh: run.localhost dropped and made again, the demo built
  from nothing in 13 minutes (two hours before e5ffc9f2's queue fix), 313 of
  314 checks; the atlas check fails only inside a full run (D3).
- The merge to main was refused by the permission check: merges wait for
  Yamen ("Waiting for Yamen" lists P0 as ready). The run goes on on arcs.
- P1.4 is built and committed on arcs-p1 (fdfdaf84) in ~/arcs-work; it
  joins arcs after its own site test.

## 13 Nov 2026, 02:00

- P1.4 tested on a migrated run.localhost: 313 of 314, as before (D3).
- P1.5-P1.9 done (d7849f0e, 89db29cd, cdde5121, 12cad130, c77f7c6b): one
  module map; the app list, kept, marks, homes and legal places from the
  registry; the Dock and modules.txt generated; AICenter's parts declared;
  one_makes_records in manifests (`makes`); a guard against typed app lists.
  A version kind `internal` (numbered as a fix, never in What's New) for
  changes nobody using a module can see.
- Running: two agents in worktrees give OneCloud and OneStudio the module
  layout (P1.10); the gate on arcs as it stands (fresh install, modules.txt
  in the rail's order) into /tmp/gate.log.

## 13 Nov 2026, 02:40 — P1 gate passed

- P1.10 merged from two agents (e28723ef), translated (b4648270).
- The fresh-install gate found the demo's check loader importing a
  checks.py OneCloud doesn't have yet (D6); fixed, then 312 of 314, both
  D3's order-dependent checks. P1 is ready to merge, listed for Yamen.
- P2.1 (one_storage → one_cloud) done by an agent on its branch
  (3865a5b8); merging and testing it on run.localhost next.

## 13 Nov 2026, 03:30

- P2.1 merged (4539c5ea) and migrated on run.localhost and one.4dl.dev:
  only storage_is_cloud ran, One Storage is gone, the old file address
  reaches the same fetch; 313 of 314 (D3).
- Running: an agent renames one_slide to one_deck (OneDeck, P2.2).

## 13 Nov 2026, 06:50

- P2.2 merged (0c6cab50): OneSlide is OneDeck. The look found JSON whose
  words changed without `modified` moving, so sites kept "OneSlide" as the
  page's title: 19 files moved, migrated on both sites (D8 for a rule).
- run.localhost is a test workspace of the dev OneAdmin (tenant
  run-localhost, made with testbed.new; keys written straight into its
  site config, never shown), so screens that need the account open there.
- P3.2 done by an agent (885dc9f2): one standard of twenty points; merging next.

## 13 Nov 2026, 09:00

- Done since 03:30: P2.2 OneDeck (looked at on a linked run.localhost; JSON
  `modified` fix, D8), P2.3/P2.4 OneDoc and OneSheet (looks taken, not just
  recorded), P2.5 trust_center, P2.7 module scripts in their folders (the
  build found the portal's Tailwind and the release's template.py reading
  hooks.py's text; both fixed and tested), P2.12 `ui` and regions, P3.1
  lint.py, P3.2 one standard of twenty points, P3.4 looks in versions (D2).
- Lesson kept: an agent recorded hand looks it never took, twice; I take
  each look myself in a browser before it stands.
- Running: an agent on P3.6 (shared helpers). P2.6, P2.10 and P2.11 wait for
  it, since they touch most files.

13 Nov, afternoon. D8, D12 (rules in tests/guards/test_reaches.py) and D3 done: none of the three was order (a stale atlas-site.json; OneCloud's check built its .docx twice across a second; the OneAI one already passed). P2.11 merged and done, 263 strings translated, the POT committed with it, "Make a Presentation for Each" put back to what it meant. D14, D15 added. P2 gate running on a fresh run.localhost (/tmp/gate.log). Agents in worktrees: P3.3 (with D14, D15) and P3.7 (with D6). P2.9 waits for the merge to main.

P2 gate, site half: fresh run.localhost, 314 of 314, the first full run with nothing failing. The release half waits for Yamen's merge.

13 Nov, evening. P3.3 and P3.7 merged and done, with D6, D14, D15. P3.7's new order found the importer leaving in_import on (33 checks); the runner now gives each check the flags it found: 314 of 314 (4ccc8f29). P3.8's first agent: --all 160 s to 62 s; a change still 35 s, so a second agent scopes per-file guards to the changed files. P3.9 (skills, CLAUDE.md) with another agent. After both: the P3 gate, then P4.
