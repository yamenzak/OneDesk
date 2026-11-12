# The run: One, rebuilt on one registry

From 12 November 2026, Claude works through both arcs alone while Yamen
studies: `docs/ARC-FIRST-EXPERIENCE.md` and `docs/ARC-AI.md`, plus the
OneAdmin work they cause and the cleanup the survey found
(`docs/run/SURVEY.md`). This file is the plan and the ledger. `LOG.md`
beside it is what happened, one short entry per sitting. `scripts/run.py`
reads the ledger and says where the run stands and what is next.

**Whoever picks this up, after a compaction or in a new session, starts at
"Resuming" below and does nothing else first.**

## Resuming

1. `cd ~/one-bench/apps/onedesk && git status -sb`. The run works on branch
   `arcs`. If the tree is dirty, read the diff and the last LOG entry before
   touching anything: it is work in flight, not junk.
2. `python3 scripts/run.py`: the phase, the item in progress, the next open
   item, and any item marked blocked.
3. Read the last three entries of `LOG.md`, then the item's text below and
   the SURVEY sections it cites.
4. Check what is still running: background shells and agents named in the
   last LOG entry. Never start a second copy of a build, a migrate or a demo
   load beside one that runs.
5. Carry on with the item. When the run is idle and nothing is in flight,
   take the next open item.

## The rules of the road

- **Branch.** Work happens on `arcs`, pushed to `upstream arcs` at least
  daily as a backup. `main` gets the run only at a phase's gate (below), by
  merge, with every gate green. A fix production needs now is made on
  `main` alone, with the gates, and merged back into `arcs`.
- **Production.** A merge to `main` builds a release and admin.4dl.app moves
  itself onto it. Nothing else of the run reaches production. Never order a
  Lightsail box except for a signup test on the dev OneAdmin, and drop it the
  same day (`scripts/server.py drop`). Never put a Stripe live key anywhere.
- **The machine.** Never stop or restart `one-claude`. `one-bench` is
  restarted after hooks.py changes. Never run two builds, migrates or demo
  loads at once (2 cores). Never commit in apps/frappe, erpnext or hrms.
  Never print ~/.one-local, ~/.one-dev.json or a key. Never drop or
  reinstall one.4dl.dev or admin.4dl.dev unless an item says so and why.
- **One item, one commit (or a few), its id first:** `R2.3: …`. The ledger
  line is ticked in the same commit with the short hash of the work in the
  next one, or in a LOG commit. The commit message carries the detail.
- **The gates for every commit:** `../../env/bin/python scripts/quick.py
  --all` green as its own step, read before committing; `python3
  scripts/docs.py`, `scripts/close.py`; a module that changed gets its
  version (`scripts/version.py`, the changelog skill); a string changed is
  translated in the same commit (the wording skill).
- **The gate for a phase:** every item ticked or explicitly moved; the
  quick gates; one.4dl.dev's demo built from scratch (`bench --site
  one.4dl.dev reinstall` is NOT used: the demo is rebuilt on a fresh site
  `run.localhost`, see P0.4) and `one_demo.check.run` all green; the
  browser walk the phase names, at 1440 and 390, light and dark, English and
  Arabic. Then merge to `main`, push, watch the release build, and write the
  LOG entry.
- **Delegation.** Mechanical work wide across files (a rename, a guard
  consolidation, a string sweep) goes to an agent in a worktree with a full
  brief: the item text, the SURVEY section, the rules above, and "run the
  gates; do not push". Its branch is read and its gates re-run before it is
  merged into `arcs`. At most three agents at once on this machine. An agent
  over an hour gets its worktree's files checked for movement.
- **Skills.** Before UI work load `ui`, `ux`, `wording`; before Help the
  `docs` skill; before a version `changelog`; before anything that sends
  data `legal`; a phase's closing walk is a `passthrough`.
- **Honesty.** A gate that fails is written in the LOG as failed. A thing
  skipped says so. A decision that is Yamen's goes in "Waiting for Yamen"
  below with a recommendation, and the run carries on around it.
- **Scope.** Something noticed outside the item goes in the module's
  SCRATCHPAD or "Noticed" below, one line. The run does not grow items
  silently: a new item is added to the ledger with its reason.

## Keeping Yamen posted

One push notification a day, the first sitting after 18:00 UTC: what
passed its gate, what is next, anything waiting for him. Otherwise
silent. Everything else is in LOG.md.

## What "done" means for the whole run

1. Every module, centre and engine declares itself once, in its
   `manifest.py`; no list of apps, module map, mark table or per-module hook
   list is typed anywhere else, and a guard proves it.
2. Code says the names people see; no old name survives in code.
3. One standards tool, OneLint, with every rule named, owned, explained and
   proven by an example; the whole suite under a minute here, a change's
   rules in seconds; the skills point at its rules.
4. A signup answers the wizard in OneAdmin before paying and lands in a
   configured workspace; the demo is built by the same setup job.
5. OneHub holds every centre in one frame; the tray reaches them; the rail
   is the person's own, with folders.
6. OneMarketplace sells each app with its own words, pictures and clips;
   installing lands in its setup; needs and kept hold.
7. The demo is a group of five companies in five fields; training copies
   start from OneHub; a copy never looks live.
8. An agent per module under Una, on Cloudflare, with levels, in AICenter
   and OneChat; Intake and the chat loop retired; AutomationCenter runs
   OneMail's rules.
9. OneGuard holds mail, links, files and risky actions.
10. Every screen walked against the new standard and stamped; Help and
    What's New current; CLAUDE.md files true.

## The target shape

### OneRegistry

Each folder that is an app, a centre or an engine has `manifest.py`: one
call, pure Python, importable without frappe (as `ready.py` is today).

```python
from onedesk.one.registry import App, Kept, Needs, Step

APP = App(
    id="one_book",                 # the folder; never changes
    name="OneBook",                # what people see; marks, rail, Help
    kind="app",                    # app | centre | engine
    line="Invoices, payments and the books.",
    modules=("Accounts", "One Book"),   # Frappe modules it owns: replaces the 4 maps
    rail=40,                       # default order; the person's own order wins
    roles=Roles(user=("Accounts User",), manager=("Accounts Manager",)),
    needs=(),                      # apps it cannot run without
    kept=Kept("submitted entries are the books", when="one_book.kept.held"),
    files=Files(ai=True, legal=True, notifications=True, heads=True, ...),
    interface={...},               # what ready.MODULES[...]["interface"] holds today
    companies=("Sales Invoice", ...),
    help=(("overview", "info"), ...),
    countries={"AE": "built", "SA": "works", "*": "not checked"},
    plan=(),                       # plan features it needs, e.g. ("training_copies",)
    marketing=Marketing(pages="docs/market/", pictures=(...), clips=(...)),
    ready=Ready(...),              # today's ready / checked / hand looks
)
```

- `onedesk/one/registry/` holds the dataclasses, the loader (walks
  `onedesk/*/manifest.py`, validates, caches) and the readers. Pure.
- **Convention files stay where they are** (ai.py, legal.py, heads.py…),
  but nothing lists them: the manifest says which it has, the loader imports
  them, and hooks.py's per-module lists are built from it at import
  (`one_ai_reads = registry.hook("ai_reads")`). hooks.py keeps only what is
  not per-module.
- Generated from it and checked: the Dock fixture, Sidebar names,
  modules.txt, custom_icon.json, docs/MODULES.md, the atlas's module map.
- Read by: AccessCenter, NotificationCenter, ShortcutCenter, HelpCenter,
  UpdateCenter, SetupCenter, TrustCenter's assembly, the wizard, the
  Marketplace, the rail, OneHub, the agents, OneAdmin (plans, private apps,
  releases), OneLint.

### Folders

Frappe puts a module's folder at `onedesk/<scrub(module name)>`, so folders
stay flat. Apps are `one_<name>`; a centre that is its own module is
`<name>_center`; engines keep their names (`one`, `one_interface`,
`one_demo`). Renames: one_storage → one_cloud, one_slide → one_deck,
one_legal → trust_center, one_account → account_center. one_doc and one_sheet
keep their folders; their doctypes and frontend folders lose the old names.
Every module folder has manifest.py, AGENTS.md, SCRATCHPAD.md, docs/,
tests/ (READY.md's "A module's folder"). Module JS and CSS live in
`public/js/<folder>/` and `public/css/<folder>/`, never top level.

### OneLint

`scripts/lint.py` (and `bench`-free): rules are Python functions in
`onedesk/one/lint/` grouped by the standard's points, each with an id, an
owner (a manifest field, a folder or "everyone"), the reason, a failing
example it must catch, and a fix hint. `lint.py` runs the rules owned by
what changed; `lint.py --all` runs all. pytest stays for behaviour tests;
standards move into OneLint. OneGuard's security rules are OneLint rules
owned by OneGuard.

## The ledger

Status: `[ ]` open, `[~]` in progress, `[x]` done (hash), `[!]` blocked
(why), `[-]` dropped (why). Each item ends with its acceptance.

### P0. Rails and a green baseline

- [x] P0.1 Plan, survey, log and run.py in docs/run; CLAUDE.md points here; memory points here. — `run.py` prints the ledger.
- [x] P0.2 Wake-ups: a scheduled task that resumes this session every two hours and a daily push. — both listed; the first fires. (Scheduled tasks "Continue the arc run" trig_01DL2h4LWAuQwsMzDFAnnstx, :26 every two hours, and "Daily run update for Yamen" trig_018Xn5EaZuKLDJvx5apAD8rf, 18:17 UTC; delete both when the run ends.)
- [ ] P0.3 Prune `.claude/worktrees` whose branches are merged or empty; list the rest in LOG. — `git worktree list` shows only live ones.
- [ ] P0.4 A run site `run.localhost` (not on the domain) for from-scratch demo builds at every gate, so one.4dl.dev keeps its data. — demo builds there from nothing and its checks run.
- [ ] P0.5 The 12 demo checks failing on 12 Nov, each fixed where it is made or written down with a reason: intake samples, OneStudio record types and extensions, settings Audit Log kinds, atlas --site, the workspace's promises, OneMail's tour, OneInventory's stock bands, OneFactory making, the UAE tax invoice print, OneCRM late first answer, deleted records, Cloudflare from a master token. — `check.run` all green on run.localhost.
- [ ] P0.6 Dead code from SURVEY §3: one/_tmp_q.py, the four writer components, TaskWaits.vue, one/privacy_copy.py if nothing imports it. — files gone, gates green.

### P1. OneRegistry (foundation)

- [ ] P1.1 `onedesk/one/registry/`: dataclasses (App, Centre, Engine, Roles, Kept, Needs, Files, Marketing, Ready, Countries), the loader, validation errors that name the manifest and field; pure tests. — `registry.apps()` returns 24 from manifests.
- [ ] P1.2 A manifest for every folder, generated once from ready.MODULES, people.APPS, APP_SAID, the Dock, heirs and the hook lists, then edited by hand where the sources disagreed (SURVEY §2: the four module maps, the names). OneCloud and OneStudio get theirs. — every folder has one; a table of each disagreement and how it was settled is in the commit.
- [ ] P1.3 `ready.MODULES` read from the manifests; ready.py keeps POINTS and HAND until P3 moves them. — no `MODULES = {` literal; guards green.
- [ ] P1.4 hooks.py's per-module lists built from the registry: one_abilities, one_ai_*, one_record_heads/measures/verbs/charts, one_calendar_layers, one_portal, one_record_tabs, one_homes, one_notification_types, after_sync/after_migrate access.settle. — the 22 hand lists gone; `bench --site run.localhost migrate` and boot unchanged (diff of `frappe.get_hooks` before/after is empty).
- [ ] P1.5 One map of Frappe module → app, from manifests; heirs, one_studio/forms.MODULES, one_ai/groups.MODULES and scripts/print_formats.MODULES read it. — the four literals gone.
- [ ] P1.6 The apps list read from the registry everywhere: people.APPS/APP_SAID, lists.HOMES, one_legal/assemble.MODULES, ready.OUTSIDE, one_demo/people.APPS, apps.KEPT/NEEDS/ICONS, brand.MARK_OF. — none of those literals remains.
- [ ] P1.7 Generated and checked from the registry: the Dock fixture, modules.txt, custom_icon.json (scripts/icons.py), docs/MODULES.md. — `docs.py --check` fails on a drift.
- [ ] P1.8 Centre participation declared, not computed in four ways (one/boot.py `one_centers`, one_ai/center.PARTS, the OneMail literal). — boot reads the registry.
- [ ] P1.9 The guard: no list of app names, folder names or marks outside manifests and generated files (allow-list by reason). — it catches its example.
- [ ] P1.10 OneCloud and OneStudio get the module folder (AGENTS.md, SCRATCHPAD.md, docs/ from their READMEs; abilities, notifications, setup, tour). — test_ready covers them.
- **Gate P1:** every former registry reads manifests; hooks unchanged in effect; demo from scratch green; the guard holds.

### P2. Names (foundation)

Each rename is one item, done by an agent in a worktree and reviewed:
`git mv`, a patch renaming Module Def and every doctype's `module`, imports,
hooks, fixtures, patches, notifications folders, public and frontend paths,
routes, translations, docs. The old dotted path stays importable for one
release through a thin module, removed in P2.9.

- [ ] P2.1 one_storage → one_cloud, Module "One Cloud", shown OneCloud. — no "one_storage", "One Storage", "onestorage" in code; DAV, share links, the editors and demo checks pass.
- [ ] P2.2 one_slide → one_deck, Module "One Deck", shown OneDeck; doctypes keep "Presentation*" (a presentation is the thing). — no OneSlide/oneslide in code.
- [ ] P2.3 OneDoc: "OneWriter" leaves code; frontend/src/writer → doc; doctypes Writer Document(*) → Document(*) only if `frappe.rename_doc` on run.localhost keeps links, versions and shares (measured; else kept and noted). — no OneWriter in code.
- [ ] P2.4 OneSheet: "OneWorkbook" leaves code; doctypes Workbook* stay (a workbook is the thing). — no OneWorkbook in code.
- [ ] P2.5 one_legal → trust_center, Module "Trust Center". — legal.py files import from the new path; TrustCenter opens.
- [ ] P2.6 one_account → account_center, Module "Account Center", including the plain "one_account" strings in hooks. — AccountCenter opens; sign-in, devices, private apps pass.
- [ ] P2.7 Module JS and CSS into their folders (SURVEY §3, the 133 top-level files that belong to one module). — public/js top level holds only what is shared.
- [ ] P2.8 "Intake"/"OneIntake" leave what people see (screens, Help, notifications) in favour of OneAI's reading; code names wait for P8.3, which retires it. — no user-facing Intake string.
- [ ] P2.9 The one-release shims removed after P2's merge has shipped. — no shim module left.
- **Gate P2:** a guard holds the old names out of code; the release built and admin.4dl.app moved on it cleanly (its migrate log read).

### P3. OneLint and DRY (foundation)

- [ ] P3.1 `onedesk/one/lint/` and `scripts/lint.py`: rule, owner, reason, example, hint; `--all`; changed-files mode from registry ownership; wraps the current guards first, unchanged. — `lint.py --all` equals today's guard result.
- [ ] P3.2 One standard: READY's 14 points and PASSOVER's 17 points merged into one numbered list in `docs/STANDARD.md` (hand-written why, generated rule table). READY.md and PASSOVER.md shrink to what is not a rule (how a module is finished, how a screen is walked). — every rule names its point; no point without a rule or a hand look.
- [ ] P3.3 Guards moved into rules point by point, overlaps merged (SURVEY §4: the look/frame 13 files, the words 6 with test_wording vs test_copy settled at one sentence, the rail 5, page lists from one place, test_shell retired), the 18 unregistered files placed, test_hooks' 663 cases one rule each kind. — rule count and run time measured before and after in the commit.
- [ ] P3.4 Readiness as facts: what the manifest declares and OneLint verifies; hand looks kept only for the five HAND points, dated by commit not by close.py rewriting ready.py. — close.py no longer edits Python.
- [ ] P3.5 OneGuard's rules in OneLint: whitelisted method without a permission check, a write that is not POST, SQL built from input, a secret in code, a guest page that says too much. — each catches its example; today's code passes or is fixed.
- [ ] P3.6 Shared helpers (SURVEY §3): the reader's company from one/company.py everywhere (98 calls), one `may`, one `hashed`, `_lt` from one place, homes' `kept`, stories' months, heads' money through the kit's `money`, the editors' shared api (templates folder, titles, copied/placed/file_gone), OneHR's approve/reject. — each group gone; a lint rule catches a new copy of the commonest.
- [ ] P3.7 The biggest files split by job where it makes them clearer: one/ai.py 3783, one_demo/check.py 4590 (into the modules' checks), hooks.py (smaller after P1). — none over 1500 lines without a reason in its docstring.
- [ ] P3.8 Speed: `lint.py` on a change under 20 s, `quick.py --all` under 60 s on this machine. — measured in the commit.
- [ ] P3.9 Skills rewritten as short guides that name rules (ui, ux, wording, docs, changelog, legal, passthrough); CLAUDE.md files made true (times, counts, the guard list). — skills under 40 KB together; nothing they say contradicts a rule.
- **Gate P3:** one command; every rule with an example; under a minute; skills and CLAUDE.md current.

### P4. OneAdmin and setup

- [ ] P4.1 Release Server for a connected machine: a ticketed release script mirroring connect_script (unit, container, image, user, subuids, linger), Cloudflare `forget`, sessions on it deleted first with their routes, pilot.forget, R2 and defaults tidied, the row kept as Released; Workspace Server refuses deletion until released. Tested both ways on this Oracle machine: release, connect again, Oracle found. — the drill in LOG.
- [ ] P4.2 Plan features: `Plan.features` (training_copies, demo, own_server, …) → Offering → Tenant → proxy.hello → boot; the registry says which app needs which. Copies gated by plan and agreement. — a plan without copies can't start one.
- [ ] P4.3 The wizard in OneAdmin before payment: you and the company (name, country, language, currency, field, companies), apps (preset by field, needs honoured, kept explained), plan, region, payment; each app's steps from the registry continue while the site builds; people and access. On frappe-ui, drawn as a phone's setup is (the ux skill). — a stranger can finish it on a phone.
- [ ] P4.4 The answers on Account Request; every step reached, finished, skipped or left recorded against the signup's lead and deal; OneAdmin Home shows where people stop. Its own line in OneAdmin's privacy policy (legal skill; covers only what is typed into the wizard). — Home's funnel has the steps.
- [ ] P4.5 One setup job, `onedesk.one.setup_job`: System Settings first, frappe's setup_complete, the owner with their name, companies, apps on and off, each app's step functions, people invited. Provision gains a step between push_config and invite_owner; the demo's setup.py calls the same job. — a signup on admin.4dl.dev lands configured (box dropped after); the demo builds through it.
- [ ] P4.6 Companies in AccountCenter: make another company the way the wizard does (name, country, currency, chart, letter head). — a second company made from the screen pays payroll and invoices.
- [ ] P4.7 SetupCenter: each app's steps done and waiting, from the registry; Getting Started tabs move here; Install lands here. — every app's steps reached from it.
- [ ] P4.8 OneCredit: the currency is OneCredit and its amounts plain credits, everywhere (~200 strings, Help, notifications, doctype labels; "OneCredits" gone), translations with it. — no "OneCredits"; the words read right in ar/de.
- [ ] P4.9 Private apps declared by their manifest (title, line, mark, needs, kept) instead of upload.py reading hooks with ast. — Rua's manifest drives its card.
- **Gate P4:** a signup on the dev OneAdmin lands configured on a box that is then dropped; the demo builds from scratch through the setup job; Release Server drilled.

### P5. OneHub and the centres

- [ ] P5.1 One centre frame drawn by OneInterface (sections left, cards right, one header, search, save), from centre manifests; module_settings.Dialog and module_docs.Dialog become one; one way to draw a section body; the seven `open()` functions become declarations. — every centre opens in it; the old bases are gone.
- [ ] P5.2 OneHub: a full window of its own, every centre a tile, searchable; the reimagined One mark at the top of the rail opens it; a centre opened from a screen is a large sheet with a way up to OneHub. — reached from the rail and by address.
- [ ] P5.3 The top bar's tray: an arrow at the right opens every centre the person may open, the current screen's first. — on desktop and phone.
- [ ] P5.4 The module foot keeps the version and Help; Settings moves to the tray; the 13 copied foot snippets become one. — one place draws the foot.
- [ ] P5.5 UpdateCenter redone: the workspace's update window, Update Now, what's coming and what changed (What's New moves in). — from OneAdmin's view of the tenant.
- [ ] P5.6 TrustCenter redone: agreements, the companies that receive data, optional services, privacy requests, updates waiting for agreement, plainly. — walked as a new owner.
- [ ] P5.7 HelpCenter: only apps that are on; OneCloud and OneStudio pages. — search finds them.
- [ ] P5.8 AccessCenter levels hide rail rows and centre tiles. — a role without OneBook never sees it.
- [ ] P5.9 The rail is the person's: reorder (frappe's save_user_dock, re-enabled), folders as One's layer in user settings, the workspace's default order set in SetupCenter, reset; the app picker as a searchable launcher, recent first; on a phone the rail is the launcher. — folders survive an upgrade.
- **Gate P5:** a passthrough of OneHub, the tray and every centre at 1440/820/390, light/dark, Arabic/German; AI step 2 (P8.2) built beside it.

### P6. OneMarketplace, needs and kept, the editors as apps

- [ ] P6.1 Needs and kept from the registry, enforced in apps.save with the reason named; kept by the rule (records others need, or records the law needs reachable), each app's reason in its manifest and checked. — OneBook can't be turned off once it has an entry; OneCRM can.
- [ ] P6.2 OneDoc, OneSheet, OneDeck as apps: rail rows, their own Marketplace pages; off = no new documents, existing ones read-only. — a file never becomes unreadable.
- [ ] P6.3 OneMarketplace replaces the Apps dialog: each app's page from its manifest (words for a buyer, 3–6 pictures and clips of the demo, what it brings, the plan it needs, the credits it uses), Install → SetupCenter, private apps under the company's name. Owners only. — every app has a page.
- [ ] P6.4 The shoot: pictures and clips (scripts/clip.mjs, ≤ 9 s) of every app on the demo, the five apps with none first. — none missing; the docs skill's rules hold.
- **Gate P6:** installing an app lands in its setup steps; walked.

### P7. The demo group and training copies

- [ ] P7.1 The demo as a holding with five companies, written by hand: the glazing contractor (contracting and making), a clinic, a real estate agency, a trading company, a services firm; each with its year of records, people and documents. — builds from scratch through the setup job.
- [ ] P7.2 Field presets beside each company: apps on, setup answers, which demo company a copy loads. — the wizard's field question applies them.
- [ ] P7.3 Each release builds a ready demo database beside the template site. — a demo copy starts in about a minute.
- [ ] P7.4 Training copies from OneHub (Fresh with the workspace's own wizard answers, From the demo by field, From our data), gated by plan and agreement, through a new proxy endpoint. — started by a workspace administrator, not an operator.
- [ ] P7.5 A copy never looks live: a soft vignette and a band in the top bar on every copy and dev site ("Training copy, ends 20 Nov. Nothing here is real."). — on all looks and palettes, phone included.
- **Gate P7:** a copy from the demo opens on the chosen field's company; the band shows; walked.

### P8. The agents (ARC-AI)

Runs beside P4–P7 as the arc's order says: P8.1 after P3, P8.2 with P5,
P8.3 with P6, P8.4 and P8.5 after P7.

- [ ] P8.1 The foundation and the first two agents: an agent user per module with only its manifest's roles; levels (Do it, Draft, Ask First) declared per action beside REACH and NOT_FOR_AI, cautious defaults; act.py generalised as every agent's write door with undo; the Agents Worker in deploy/agents on the Agents SDK, deployed by Set Up Cloudflare, called back into the workspace through a signed token (the reversal of "the account never calls a workspace", written down with its reason); the privacy clause (recorded hash). OneMail's receptionist hands invoices to OneBook's accountant, which drafts the Purchase Invoice. — 50 invoice samples, at most 2 corrected; the real-use gate waits for Yamen.
- [ ] P8.2 AICenter as the agents' office on the P5 frame (a tab per agent: who, may do with record, learned, did with Undo, costs) and OneChat in Vue on frappe-ui (channels, messages, threads, agents as members, cards with Approve and Change, socket.io realtime, Raven as reference); OneAI's panel becomes a conversation; inline asks become a one-line popover. — a week of use replaces the panel (Yamen); walked.
- [ ] P8.3 An agent for every module; Intake's planners move to their owners (SURVEY §7); the Documents page becomes each agent's queue; the chat loop and group guessing retire. — nothing is left that only the Documents page does.
- [ ] P8.4 AutomationCenter: a node builder where each block writes its own safe part; OneMail's rules move in first, then OneChat's; an agent can be a block; works without AI. Rooms and the website widget. — every Mail Rule runs from it.
- [ ] P8.5 The setup agent with the wizard. — it answers a new owner's setup questions.

### P9. OneGuard

- [ ] P9.1 Mail scored, risky mail held with a reason, lookalike domains warned (from today's Spam/Phishing verdicts). — samples caught.
- [ ] P9.2 Links opened in a throwaway browser and shown before anyone clicks; attachments opened, unpacked and checked in a sandbox, macros stripped (OneOS containers). — a sample link and file shown safely.
- [ ] P9.3 Risky actions ask a second person (unusual payment, changed bank details, mass export). — each asks.
- [ ] P9.4 Decide the containers' name: OneSandbox if it reads naturally by then. — written in Decisions.

### P10. Brand

Runs beside P5 onwards. Drafts are proposals for Yamen; each lands as a
SVG in brand/ only after his look, unless it replaces nothing.

- [ ] P10.1 The One circle family: OneHub, OneCredit (gold rim, the 1 struck like the euro), SetupCenter and every centre, AICenter from OneAI's mark refined. — drafts in a page for review.
- [ ] P10.2 Apps: OneChat, OneMarketplace, OneGuard, OneDoc, OneSheet, OneDeck; redo OneFactory, OnePortal, OneQuality. — drafts for review.
- [ ] P10.3 White-label: the workspace's logo, colours and name in one setting in OneInterface. — one setting changes the shell.

### P11. The final pass

- [ ] P11.1 Every module and screen walked against docs/STANDARD.md (the passthrough skill), stamped Passed; Help pictures current; translations complete. — no screen unstamped without a reason.
- [ ] P11.2 docs/ and every AGENTS.md read for truth; the ARC docs marked done or moved to BACKLOG. — nothing stale.
- [ ] P11.3 The switchover items that were Yamen's (admin.4dl.dev retired, dev Cloudflare resources) prepared as a list for him.

## Decisions

- 12 Nov, Yamen: work on `arcs`, merged to `main` at gates; editors OneDoc,
  OneSheet, OneDeck; the product stays One; OneOS stays until OneGuard; the
  demo is one group of five companies; wizard analytics before payment with
  their own privacy line; kept by the rule (an app is kept once others'
  records need its records, or the law needs them reachable; OneCRM is not
  kept); no new country in this run; one push a day.
- 12 Nov, Claude: centres that are their own module are `<name>_center`
  folders; apps keep `one_<name>`; Presentation and Workbook doctypes keep
  their names; a demo rebuild for a gate happens on run.localhost, not on
  one.4dl.dev.

## Waiting for Yamen

- The real-use gates of P8.1 and P8.2 (50 real invoices; a week on OneChat).
- The brand drafts (P10).

## Noticed

(one line each; things outside the current item)
