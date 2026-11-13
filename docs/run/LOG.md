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
