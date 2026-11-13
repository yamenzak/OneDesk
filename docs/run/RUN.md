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
  merge, with every gate green, and only by Yamen: a merge moves
  production, and the permission check refuses it unattended. A passed
  gate goes on "Waiting for Yamen" as ready to merge. A fix production needs now is made on
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
- **The gates for every commit:** the scoped checks only,
  `../../env/bin/python scripts/quick.py` (OneLint's changed-files mode once
  P3.1 lands), read before committing. The whole suite (`--all`) runs at a
  phase gate and before any merge to main, not every few changes; `python3
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
  skipped says so.
- **Decide, don't wait (Yamen, 12 Nov).** The run never stops for a
  decision. It takes the most scalable, modular, future-proof choice, one
  that holds for any number of companies and any region, writes it under
  Decisions with its reason, and goes on. Modularity is what makes a wrong
  call cheap to change later. A rewrite is never skipped because it is big.
  Only what needs Yamen's own hands (real-use gates, a production key) waits.
- **Deferred.** Putting something off is allowed only as a line under
  "Deferred" below, `- [ ] Dn <what> — at P<phase>.<item>: <why>`; run.py
  lists the ones due when their item comes up, and that item is not ticked
  until they are done or moved on with a reason.
- **Names are code (Yamen, 12 Nov).** No product, app or centre name is
  typed as a raw string anywhere: code reads `registry.name("one_cloud")`,
  JS `onedesk.names.of("one_cloud")`, Vue `name("one_cloud")`, words take it
  as `{0}`. A OneLint rule fails a literal outside manifests and generated
  files, so any name can be changed in one place.
- **The three ways a screen is made (Yamen, standing rule).** An app on
  ERPNext or HRMS stays as native as it can: frappe's own lists and forms,
  customised only in regions its manifest declares (`ui="native"`,
  `regions=…`; most were settled by the passover, check them before
  changing any). An app that depends on nothing upstream gets bespoke
  screens (`ui="bespoke"`), built from frappe desk and frappe-ui parts for
  consistency. Some are mixed (`ui="mixed"`) and say which screens are
  which. OneLint holds each to its declaration.
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

**An app is one self-contained folder** (decided 12 Nov, Yamen asked for a
choice). Each part a centre reads is named for that centre, so the folder
reads like One itself: `help/` (HelpCenter's pages, today `docs/`),
`updates/` (UpdateCenter's versions, today `docs/changelog/`),
`notifications.py` (NotificationCenter), `access.py` (AccessCenter, today
abilities.py and access.py together), `trust.py` (TrustCenter, today
legal.py), `agent.py` (AICenter and the app's agent, today ai.py),
`shortcuts.py`, `setup.py` (SetupCenter), `control.py` (ControlCenter),
`tour.py`, `checks.py`, `market/` (OneMarketplace's page, pictures, clips).
The other way round (a centre folder holding a directory per app) was
rejected: an app, a private one most of all, must be addable and removable
as one unit, and Frappe puts an app's doctypes in its own folder anyway.
Centres are engines that read their parts from the registry and own no
app's content.

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
- [x] P0.3 Prune `.claude/worktrees` whose branches are merged or empty; list the rest in LOG. — `git worktree list` shows only live ones. (29 removed 12 Nov; two left, see D1.)
- [x] P0.4 A run site `run.localhost` (not on the domain) for from-scratch demo builds at every gate, so one.4dl.dev keeps its data. — demo builds there from nothing and its checks run. (13 Nov: built from nothing, 310 of 314 on its first run.)
- [x] P0.5 The 12 demo checks failing on 12 Nov, each fixed where it is made or written down with a reason: intake samples, OneStudio record types and extensions, settings Audit Log kinds, atlas --site, the workspace's promises, OneMail's tour, OneInventory's stock bands, OneFactory making, the UAE tax invoice print, OneCRM late first answer, deleted records, Cloudflare from a master token. — `check.run` all green on run.localhost. (13 Nov: 313 of 314 on a site built from nothing; the atlas check fails only inside a full run, D3.)
- [x] P0.6 Dead code from SURVEY §3: one/_tmp_q.py, the four writer components, TaskWaits.vue, one/privacy_copy.py if nothing imports it. — files gone, gates green. (privacy_copy.py serves download requests and stays; its copied helpers are P3.6's.)

### P1. OneRegistry (foundation)

- [x] P1.1 `onedesk/one/registry/`: dataclasses (App, Centre, Engine, Roles, Kept, Needs, Files, Marketing, Ready, Countries), the loader, validation errors that name the manifest and field; pure tests. — `registry.apps()` returns 24 from manifests. (A module may be one folder's own and another's to show, as the editors are OneCloud's until P6.2.)
- [x] P1.2 A manifest for every folder, generated once from ready.MODULES, people.APPS, APP_SAID, the Dock, heirs and the hook lists, then edited by hand where the sources disagreed (SURVEY §2: the four module maps, the names). OneCloud and OneStudio get theirs. — every folder has one; a table of each disagreement and how it was settled is in the commit. (Written from ready.py's source so its _lt markers stay; names are today's, P2 changes them. ui, needs, kept and countries wait for P2.12, P6.1 and P4.)
- [x] P1.3 `ready.MODULES` read from the manifests; ready.py keeps POINTS and HAND until P3 moves them. — no `MODULES = {` literal; guards green.
- [x] P1.4 hooks.py's per-module lists built from the registry: one_abilities, one_ai_*, one_record_heads/measures/verbs/charts, one_calendar_layers, one_portal, one_record_tabs, one_homes, one_notification_types, after_sync/after_migrate access.settle. — the 22 hand lists gone; `bench --site run.localhost migrate` and boot unchanged (diff of `frappe.get_hooks` before/after is empty). (13 Nov: every hook the same set, only order differs; settles run One first and its three last.)
- [x] P1.5 One map of Frappe module → app, from manifests; heirs, one_studio/forms.MODULES, one_ai/groups.MODULES and scripts/print_formats.MODULES read it. — the four literals gone. (13 Nov: heirs from `owns`; OneStudio's forms now file manufacturing and quality under OneFactory and OneQuality, where the old map said One Inventory; OneAI keeps an app-to-tool-group map until P8.)
- [x] P1.6 The apps list read from the registry everywhere: people.APPS/APP_SAID, lists.HOMES, one_legal/assemble.MODULES, ready.OUTSIDE, one_demo/people.APPS, apps.KEPT/NEEDS/ICONS, brand.MARK_OF. — none of those literals remains. (13 Nov: OUTSIDE was fifteen empty lists and is gone; apps.NEEDS and ICONS keep Reading, OneAI's switch, until P8.3; KEPT is the manifests' `kept` with no condition, One and OneAdmin.)
- [x] P1.7 Generated and checked from the registry: the Dock fixture, modules.txt, custom_icon.json (scripts/icons.py), docs/MODULES.md. — `docs.py --check` fails on a drift. (13 Nov: the Dock and modules.txt are written by docs.py; custom_icon.json stays scripts/icons.py's from brand/, and a test holds every manifest's mark to a file there. The centres and engines have no mark until P10.1.)
- [x] P1.8 Centre participation declared, not computed in four ways (one/boot.py `one_centers`, one_ai/center.PARTS, the OneMail literal). — boot reads the registry. (13 Nov: AccessCenter and NotificationCenter already follow a module's abilities.py and its notification types; AICenter's PARTS come from an ai.py that declares JOBS, and OneMail says `centres=("ai",)` in its manifest.)
- [x] P1.9 The guard: no list of app names, folder names or marks outside manifests and generated files (allow-list by reason). — it catches its example. (13 Nov: tests/test_one_registry.py; it found one_makes_records, 109 record types each naming their makers, which moved into the manifests as `makes`.)
- [x] P1.10 OneCloud and OneStudio get the module folder (AGENTS.md, SCRATCHPAD.md, docs/ from their READMEs; abilities, notifications, setup, tour). — test_ready covers them. (13 Nov, two agents: OneCloud 15 Help pages, OneStudio 13; both 1.0.0, not ready; no roles of their own, said in `no_roles`; Help has no pictures yet, listed in their SCRATCHPADs. ready.MODULES is every app and centre and every engine with Help, so the demo stays out by rule.)
- **Gate P1:** every former registry reads manifests; hooks unchanged in effect; demo from scratch green; the guard holds.

### P2. Names (foundation)

Each rename is one item, done by an agent in a worktree and reviewed:
`git mv`, a patch renaming Module Def and every doctype's `module`, imports,
hooks, fixtures, patches, notifications folders, public and frontend paths,
routes, translations, docs. The old dotted path stays importable for one
release through a thin module, removed in P2.9.

- [x] P2.1 one_storage → one_cloud, Module "One Cloud", shown OneCloud. — no "one_storage", "One Storage", "onestorage" in code; DAV, share links, the editors and demo checks pass. (13 Nov, an agent, 3865a5b8: 228 files; storage_is_cloud merges the Module Def and moves what holds it as text; R2 file URLs and DAV keep their address through override_whitelisted_methods, site-config keys keep theirs; run.localhost and one.4dl.dev migrated, 313 of 314.)
- [x] P2.2 one_slide → one_deck, Module "One Deck", shown OneDeck; doctypes keep "Presentation*" (a presentation is the thing). — no OneSlide/oneslide in code. (13 Nov, an agent, a82dc957: slide_is_deck renames the Module Def and roles; stored URLs, HMAC salts and /assets/onedesk/slide keep their names for good. JSON whose words changed without `modified` moving never reached sites: fixed for P2.1 and P2.2 (D8). Looked at on run.localhost, linked to the dev OneAdmin for it: the editor opens a presentation at 1440 and 390.)
- [x] P2.3 OneDoc: "OneWriter" leaves code; frontend/src/writer → doc; doctypes Writer Document(*) → Document(*) only if `frappe.rename_doc` on run.localhost keeps links, versions and shares (measured; else kept and noted). — no OneWriter in code. (13 Nov, an agent, a3569d8d: OneDoc; the doctypes keep their names and read Document through translations; roles renamed by writer_is_doc through one/renaming.app_renamed; looked at on run.localhost at 1440 and 390; the editors' 16 checks green.)
- [x] P2.4 OneSheet: "OneWorkbook" leaves code; doctypes Workbook* stay (a workbook is the thing). — no OneWorkbook in code. (13 Nov, the same agent and commit: OneSheet, workbook_is_sheet; looked at likewise.)
- [x] P2.5 one_legal → trust_center, Module "Trust Center". — legal.py files import from the new path; TrustCenter opens. (13 Nov, an agent, 5bf4373f: legal_is_trust merges the Module Def and renames roles to TrustCenter User/Manager; no agreement hash moved; guards and scripts that looked only at one_* folders now see *_center too. Migrated on run.localhost; its four checks and /legal/terms pass.)
- [x] P2.6 one_account → account_center, Module "Account Center", including the plain "one_account" strings in hooks. — AccountCenter opens; sign-in, devices, private apps pass. (13 Nov, an agent, 83653dfe: account_is_center; roles AccountCenter User/Manager; old invite links answer through override_whitelisted_methods; OneAdmin never calls a one_account path, so D11 is dropped. Fresh gate 309 of 314, the rest D3's or the check's own Error Log reading, fixed.)
- [x] P2.7 Module JS and CSS into their folders (SURVEY §3, the 133 top-level files that belong to one module). — public/js top level holds only what is shared. (13 Nov, an agent, d010a95f: 106 moved, 25 shared with reasons, a guard. After the build, 19 desk pages and the sign-in open with no missing asset or script error. The build found the portal's Tailwind and the release's template.py still reading hooks.py's text: both read the registry now.)
- [x] P2.8 "Intake"/"OneIntake" leave what people see (screens, Help, notifications) in favour of OneAI's reading; code names wait for P8.3, which retires it. — no user-facing Intake string. (13 Nov, an agent, f74660e2: on screen it is Reading, and "OneAI reads …"; nine strings were left to change; code names wait for P8.3.)
- [x] P2.10 The app folder's parts named for their centres (Folders, above): docs/ → help/, docs/changelog/ → updates/, legal.py → trust.py, ai.py → agent.py, abilities.py + access.py → access.py; the readers and guards follow. — every app reads the same. (13 Nov, an agent, 3e296b3b: 239 Help pages, 398 versions, 23 trust.py, 24 agent.py, 19 access.py of which 10 merged; R2 keys are by content so pictures stay; old ai.py paths kept for queued jobs, D13. Migrated, built, 313 of 314; Help and What's New show their pictures.)
- [x] P2.11 Names as code: `registry.name()`, `onedesk.names.of()`, Vue `name()`; every product, app and centre name in code, JSON labels, Help and notifications reads it ({0} in words); the OneLint rule that fails a literal. — renaming an app in its manifest renames it everywhere, proven on a throwaway name on run.localhost. (13 Nov: registry.names/filled, boot one_names, onedesk.names.of/mark/sidebar, the kit's name(); `{one_doc}` placeholders in Help, versions and notifications; synced labels from registry/labels.py; rule names-are-code under point 13 with a count per file that only falls: py 687→98, js 239→9, vue 85→4, Help 1044→6, json 135→101; renaming OneDoc to OneWrite in its manifest followed through Help, notifications and screens; 263 strings translated.)
- [x] P2.12 The three ways a screen is made, declared: each manifest says `ui` and, for native and mixed apps, its regions (from tiers.SCREENS, ready.MODULES interface and the passover's decisions); the rule that holds a native app's screens to them. — every screen is in exactly one declaration. (13 Nov: native OneBook, OneInventory, OneFactory, OneQuality, OneCRM, OneHR; mixed One, OneProject, OneTask, OneAdmin, OneAI, OneStudio; bespoke the rest; each desk page a region of the app whose folder holds it, tiers.SCREENS read from them.)
- [ ] P2.9 The one-release shims removed after P2's merge has shipped. — no shim module left.
- **Gate P2:** a guard holds the old names out of code; the release built and admin.4dl.app moved on it cleanly (its migrate log read). (13 Nov: a fresh run.localhost, demo from nothing, 314 of 314 checks; the release half waits for the merge to main, with P2.9.)

### P3. OneLint and DRY (foundation)

- [x] P3.1 `onedesk/one/lint/` and `scripts/lint.py`: rule, owner, reason, example, hint; `--all`; changed-files mode from registry ownership; wraps the current guards first, unchanged. — `lint.py --all` equals today's guard result. (13 Nov: scripts/lint.py, quick.py its alias until P3.9 rewrites what names it; a change also runs its module's tests and those naming its folder; rules listed from tests/guards/registry.py until P3.3.)
- [x] P3.2 One standard: READY's 14 points and PASSOVER's 17 points merged into one numbered list in `docs/STANDARD.md` (hand-written why, generated rule table). READY.md and PASSOVER.md shrink to what is not a rule (how a module is finished, how a screen is walked). — every rule names its point; no point without a rule or a hand look. (13 Nov, an agent, 885dc9f2: twenty points in onedesk/one/standard.py, read by ready.py and tests/guards/registry.py; 139 rules, every point at least two; docs/STANDARD.md the why, STANDARD-RULES.md generated; READY.md 1,419 to 991 lines, PASSOVER.md 339 to 29.)
- [x] P3.3 Guards moved into rules point by point, overlaps merged (SURVEY §4: the look/frame 13 files, the words 6 with test_wording vs test_copy settled at one sentence, the rail 5, page lists from one place, test_shell retired), the 18 unregistered files placed, test_hooks' 663 cases one rule each kind. — rule count and run time measured before and after in the commit. (13 Nov, an agent, b7aa0c57: 150 rules to 302, every test a rule or a rule's proof (Guard.proof, test_registry fails one that is neither); 2,819 tests to 2,146, 160 s to 131 s on two cores; test_hooks one test per kind; frappe icons in tests/bench.icons(); rail in test_rail; test_copy into test_wording at one sentence, 227 two-sentence descriptions counted in wording_allowed.py; test_shell into test_frame, a page's kind read from its code. test_layers stays its own.)
- [x] P3.4 Readiness as facts: what the manifest declares and OneLint verifies; hand looks kept only for the five HAND points, dated by commit not by close.py rewriting ready.py. — close.py no longer edits Python. (13 Nov: a look is `looked:`/`looked_by:` in a version's front matter, holding until the next major or minor; manifests hold no looks, so manifest.py counts toward the version again: D2.)
- [x] P3.5 OneGuard's rules in OneLint: whitelisted method without a permission check, a write that is not POST, SQL built from input, a secret in code, a guest page that says too much. — each catches its example; today's code passes or is fixed. (13 Nov, an agent, 4e9ad21e: five rules in tests/guards/test_oneguard.py, each case allowed with its reason and only falling; no real secret. The fourteen to fix are fixed: thirteen writes POST-only, OneHR's shift approvers checked; each module says why OneAI doesn't make those calls.)
- [x] P3.6 Shared helpers (SURVEY §3): the reader's company from one/company.py everywhere (98 calls), one `may`, one `hashed`, `_lt` from one place, homes' `kept`, stories' months, heads' money through the kit's `money`, the editors' shared api (templates folder, titles, copied/placed/file_gone), OneHR's approve/reject. — each group gone; a lint rule catches a new copy of the commonest. (13 Nov, an agent, a2083730: reader_company (133 callers), workspace_company, company_currency, rights.can, frappe's sha256_hash, one _lt, needs_you.kept, story months, head.money, decision.answer, privacy's shared query; two rules under point 20. The editors' shared api waits for its own pass. The module checks named moved constants: fixed, D12.)
- [x] P3.7 The biggest files split by job where it makes them clearer: one/ai.py 3783, one_demo/check.py 4590 (into the modules' checks), hooks.py (smaller after P1). — none over 1500 lines without a reason in its docstring. (13 Nov, an agent, 53eb1380: one_demo/check.py 4,603 to 103, the runner; each module's checks in its own checks.py, the shared helpers in one_demo/checking.py; one/agent.py 3,823 to 735 with its tools in one/ai_*.py; one_inventory/agent.py 1,510 to 1,352. Left whole with a reason: one/checks.py, one_project/checks.py, one_inventory/heads.py, scripts/overrides.py, scripts/print_formats.py. The new order found the importer leaving in_import on: 4ccc8f29, 314 of 314.)
- [x] P3.8 Speed: `lint.py` on a change under 20 s, `quick.py --all` under 60 s on this machine. — measured in the commit. (13 Nov, two agents, 968cba62 and 2b0d262d: sources parsed once per worker in scripts/tree.py, one node for every desk script, the slow scans rewritten; in change mode ONELINT_CHANGED scopes the guards that judge each file alone to the changed files (oneguard reads them and what they import). --all 160 s to 58 s; a one-file change 36–44 s to 11–14 s; the same test ids and outcomes.)
- [x] P3.9 Skills rewritten as short guides that name rules (ui, ux, wording, docs, changelog, legal, passthrough); CLAUDE.md files made true (times, counts, the guard list). — skills under 40 KB together; nothing they say contradicts a rule. (13 Nov, an agent, b74667bc: the seven skills 81 KB to 40 KB, each naming rules by id and point; untrue in CLAUDE.md: quick.py and 35 s, OneWorkbook/OneWriter, READMEs moving to AGENTS.md, ready.py as the list, the generated docs, onedesk.localhost; CLAUDE.bench.md on dev's OneAdmin until P11.3.)
- **Gate P3:** one command; every rule with an example; under a minute; skills and CLAUDE.md current. (13 Nov: passed. `lint.py --all`: 2,239 tests in 58 s under load; 303 rules, each with its proof (09aba923, test_registry fails one without); a change 11–14 s; skills 40 KB and CLAUDE.md true.)

### P4. OneAdmin and setup

- [ ] P4.1 Release Server for a connected machine: a ticketed release script mirroring connect_script (unit, container, image, user, subuids, linger), Cloudflare `forget`, sessions on it deleted first with their routes, pilot.forget, R2 and defaults tidied, the row kept as Released; Workspace Server refuses deletion until released. Tested both ways on this Oracle machine: release, connect again, Oracle found. — the drill in LOG.
- [ ] P4.2 Plan features: `Plan.features` (training_copies, demo, own_server, …) → Offering → Tenant → proxy.hello → boot; the registry says which app needs which. Copies gated by plan and agreement. — a plan without copies can't start one.
- [ ] P4.3 The wizard in OneAdmin before payment: you and the company (name, country, language, currency, field, companies), apps (preset by field, needs honoured, kept explained), plan, region, payment; each app's steps from the registry continue while the site builds; people and access. On frappe-ui, drawn as a phone's setup is (the ux skill). — a stranger can finish it on a phone.
- [ ] P4.4 The answers on Account Request; every step reached, finished, skipped or left recorded against the signup's lead and deal; OneAdmin Home shows where people stop. Its own line in OneAdmin's privacy policy (legal skill; covers only what is typed into the wizard). — Home's funnel has the steps.
- [ ] P4.5 One setup job, `onedesk.one.setup_job`: System Settings first, frappe's setup_complete, the owner with their name, companies, apps on and off, each app's step functions, people invited. Provision gains a step between push_config and invite_owner; the demo's setup.py calls the same job. — a signup on admin.4dl.dev lands configured (box dropped after); the demo builds through it.
- [ ] P4.6 Companies in AccountCenter: make another company the way the wizard does (name, country, currency, chart, letter head). — a second company made from the screen pays payroll and invoices.
- [ ] P4.7 SetupCenter: each app's steps done and waiting, from the registry; Getting Started tabs move here; Install lands here. — every app's steps reached from it.
- [ ] P4.8 OneCredit: the currency is OneCredit and its amounts plain credits, everywhere (~200 strings, Help, notifications, doctype labels; "OneCredits" gone), translations with it. — no "OneCredits"; the words read right in ar/de.
- [ ] P4.10 OneAdmin again: its setup sessions (each signup's wizard as a record operators can follow, resume and help), the funnel analytics, and its own agent (OneAdmin's operator assistant, on the P8 foundation, with the same levels). — an operator sees each signup's place in the wizard and can ask the agent about the fleet.
- [ ] P4.11 The price calculator counts what agents cost: Durable Object requests, duration and storage, Workers, the Agents SDK's database, per agent per workspace; OneCredit's price reconsidered against it, with the margin kept (price_list.ONECREDIT, margins.py). — Plan Calculator and Price Check show agent cost; the decision on OneCredit's price is in Decisions.
- [x] P4.9 Private apps declared by their manifest (title, line, mark, needs, kept) instead of upload.py reading hooks with ast. — Rua's manifest drives its card. (13 Nov, an agent, 67645387: a private app is `APP = App(...)` in its manifest.py, read with ast by onedesk/one/registry/private.py, literals only, through registry._check; the build, upload and AccountCenter read it; upload.py's hooks reading gone with no fallback; Rua's card from private/rua/rua/manifest.py. Records already in OneAdmin keep their words until their next release.)
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
- [x] P9.4 Decide the containers' name. — Decided 12 Nov: OneOS keeps opening and presenting files ("Open in OneOS"); OneGuard is only the protection and uses OneOS's containers behind the scenes; nobody opens a file "in OneGuard". Names are code (P2.11), so this can change in one place.

### P10. Brand

Runs beside P5 onwards. Marks are made and shipped like any other
decision; Yamen can redraw any later, since marks are read from the
registry.

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
- 12 Nov, Yamen (second message): start without waiting; decide every
  open question for scale and modularity and record it; track deferrals;
  names are code; OneAdmin gains setup sessions, analytics and its own
  agent, and the calculator counts Durable Objects and re-prices OneCredit;
  scoped checks while working, the whole suite at gates; the three ways a
  screen is made.
- 13 Nov, Claude: doctypes keep their names through the renames (Writer
  Document, Workbook, Presentation): a doctype's name is an id, and renaming
  one risks every link, version and share; where people see one, it reads
  in One's words through onedesk/translations, as upstream names do.
- 13 Nov, Claude: OneCloud's and OneStudio's clauses split into sentences
  of 30 words or fewer, saying the same, are recorded as new hashes, not a
  new revision: nobody has agreed to anything yet, so nobody is asked again.
- 13 Nov, Claude: the optional services, the People screen and every other
  list of apps follow the rail's order.
- 13 Nov, Claude (P4.11): a OneCredit stays AED 0.04 and the 20,000-credit
  pack is AED 769, from 749. Cloudflare's Workers Paid prices read that day
  (one_admin/agent_costs.py) put the agents at AED 0.79 a month for a
  10-person workspace, about 0.04 an agent, 7.70 for Scale's 100; plans keep
  53-64%. A credit spent on an agent's message carries its Cloudflare cost,
  1.1% on the model's cost at the usual tier and 2.2% at Fast, the worst, and
  with it the 20,000 pack at 749 fell from 40.9% to 39.7%, under the 40%
  floor. Lowering the credit to 0.039 would have held it too, but would have
  charged every use 2.6% more credits and moved a round number people learn;
  repricing the one pack that broke keeps a credit at four fils. Nothing is
  sold yet: the packs are their launch versions (@2026-12).
- 12 Nov, Claude: an app is one self-contained folder whose parts are named
  for their centres (Folders); OneOS keeps its name for opening files and
  OneGuard is protection only (P9.4).

## Waiting for Yamen

Only what needs his own hands:

- **Merging `arcs` into `main`.** A merge moves production, and the
  permission check refuses it unattended (13 Nov). Each passed gate is
  listed here, ready to merge; until then everything lives on `arcs`,
  pushed daily. Ready: **P0** (gate passed 13 Nov 00:03, 313 of 314; the
  merge brings the queue fix that matters most to every workspace's
  migrate). **P1** (gate passed 13 Nov 02:40, 312 of 314, both D3's; the
  registry, every list of apps read from it, OneCloud and OneStudio as
  modules).
- The real-use gates of P8.1 and P8.2 (50 real invoices; a week on OneChat).

## Deferred

(`- [ ] Dn <what> — at P<phase>.<item>: <why>`; run.py shows those due)

- [-] D11 OneAdmin calls workspaces' account_center paths — at P2.9: until every workspace runs the rename, only the old paths are on all of them. Dropped 13 Nov (P2.6): OneAdmin names no account path on a workspace; it posts to `onedesk.one.account.wake` (steps.py, releases.py), which keeps its path and calls owner.arrive inside the workspace.
- [ ] D13 Remove the ai.py/legal.py/abilities.py re-exports left by P2.10 — at P2.9: they stay one release so old dotted paths run (one_deck/ai.py, account_center/ai.py, and media.moved for a picture's old docs/ path)
- [x] D14 ControlCenter, NotificationCenter, AccessCenter, AICenter, ShortcutCenter, HelpCenter, UpdateCenter, OneOS and OneCredits get a manifest each, so their names are code and the names rule reads them — at P3.3: the rules are reworked there, and P4 renames OneCredits. (13 Nov, 3065de21: the nine are PARTS in their owners' manifests, read by registry.parts() and name(); Help names them through slots, 161 replaced.)
- [x] D15 brand.js's NAME pattern (the wordmark) is built from boot's one_names, not typed — at P3.3: the rules are reworked there. (13 Nov, 3065de21.)
- [ ] D10 Remove the one_account shim — at P2.9: it stays one release so old dotted paths run
- [ ] D9 Remove the one_legal shim — at P2.9: it stays one release so old dotted paths run
- [x] D12 A rule that every name a checks.py reads from one of our modules (module.NAME) exists: checks never run under pytest, and P3.6 moved story.MONTHS and home.FEW from under three checks — at P3.3: the checks are reworked there.
- [x] D8 A rule that a synced JSON (doctype, page, sidebar, report, print format, notification, fixture) whose content changed also moved its `modified`, or frappe never syncs it to sites — at P3.3: the P2 renames changed titles without it and sites kept the old words.
- [x] D6 OneCloud's checks move out of one_demo/check.py into its own checks.py, as every other module's are; check.py imports a module's checks only where the file exists until then — at P3.7: check.py is split there. (OneCloud's folder is one_cloud since P2.1.) (13 Nov, 53eb1380: one_cloud/checks.py.)
- [ ] D7 Remove the one_slide shim — at P2.9: it stays one release so old dotted paths run
- [ ] D4 Remove the one_storage shim — at P2.9: it stays one release so old dotted paths run
- [ ] D5 OneAdmin's post to a workspace's `oneos.stopped` names `onedesk.one_cloud` again — at P2.9: until every workspace runs the rename, only the old path is on all of them (the shim answers it on the new)
- [x] D3 Two demo checks pass alone and fail inside a full run (one_atlas_knows_who_may_open_what, onecloud_a_document_of_ones_own_is_edited_in_oneos, one_oneai_turned_off_asks_nothing_and_oneintake_reads_nothing): an earlier check leaves state a rollback doesn't undo (frappe's SQLite logs, or a commit inside a check); find which and make each check leave the site as it found it — at P3.3: the checks are reworked there. (13 Nov: none was order: atlas-site.json was stale since P2.10's migrate (File Link); the OneCloud check built its Word file twice and a .docx carries the second it was made in, so a second boundary made the same save two; the OneAI one passed in the last gates.)
- [x] D2 A manifest's shipped fields (interface, help, roles, companies) count toward its module's fingerprint again; manifest.py is left out while P1 moves ready.MODULES into manifests, since that moved no module's version before — at P3.4: readiness is reworked there.
- [ ] D1 Remove the locked worktree agent-ae3e27f8 once its agent process has ended, and the dirty worktree agent-af46cdf5 (uncommitted OneAdmin work of 9 Nov; its diff saved first) and any left after P0.3 — at P11.3: removing worktrees was stopped by the permission check on 12 Nov; ask nothing, retry without force, and if still refused leave it.

## Noticed
- 13 Nov: the tunnel routes only one.4dl.dev since dev's OneAdmin was retired, so a site linked to https://admin.4dl.dev (run.localhost) gets 404 on every live OneAdmin call; the checks fake those answers. P4's gate (a signup on the dev OneAdmin, a box calling back) needs admin.4dl.dev routed again for the drill, or the drill against production's OneAdmin: decide at the P4 gate.

(one line each; things outside the current item)
