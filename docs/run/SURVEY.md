# The run's survey, 12 November 2026

What the code was when the run started (HEAD 203a7458), read by six surveys.
The run's items cite it by section. Paths are under `onedesk/` unless they
start with `docs/`, `tests/`, `scripts/`, `frontend/` or `deploy/`. Counts
are from that day; a count the run lowers is re-measured, never copied.

## 1. Modules and their files

- 24 folders: `one` and 23 `one_*`, plus `notifications/`. Product modules
  22; `one_demo` and `one_interface` are not apps. `modules.txt` has 23 Module
  Defs written "One X".
- `ready.MODULES` (one/ready.py, 1668 lines, pure) has 21 entries and lacks
  OneCloud (`one_storage`) and OneStudio (`one_studio`). Keys and how many set
  them: folder, screens, names, help 21; ready 20; checked 17; interface 9;
  companies 8; windowless 6; engine 2; app 1; operators 1. Also POINTS (14),
  HAND (5), SHARED (~125 paths), OUTSIDE (15, all empty), UNSHIPPED.
- `one_storage`, `one_studio`, `one_demo` keep one long README.md instead of
  AGENTS.md, SCRATCHPAD.md and docs/; OneCloud and OneStudio have no
  abilities, notifications, setup, tour, docs.
- Convention files present (of 24): ai 23, legal 22, setup 22 (STEPS real
  only in one_mail 3, one_factory 2, one_account 1, one_slide), checks 22,
  notifications 21, tour 21, docs 21, AGENTS/SCRATCHPAD 21, page 20,
  abilities 19, permission_type 19, patches 19, sidebar 17, tell 17, custom
  14, heads 13, access 10, shortcuts 10, home 8, portal 7, calendar 7, lists
  7, control 6, demo 3. tests/ missing in 13 modules.

## 2. What a registry would own (today scattered)

- 22 custom hooks in hooks.py (1762 lines), each a hand-typed list of one
  file per module: one_abilities 19, one_ai_page 18, one_ai_suggestions 15,
  one_record_heads 13, one_measures 13, one_verbs 8, one_charts 4,
  one_calendar_layers 8, one_portal 6, one_record_tabs 4, one_homes 2,
  one_ai_reads 98 tool paths, one_ai_suggests 75, one_slide_loaded/saving/
  rows, one_record_notices, one_notification_types, one_makes_records 109,
  one_module_heirs 30, code_only_modules. `heads.py` alone feeds four hooks.
- after_sync 64 and after_migrate 58 share 58 entries; 9 are
  `<module>.access.settle`.
- Readers that import a fixed file from each module: one/setup_steps.py
  (setup.STEPS), one/tours.py (tour.TOURS), one/shortcut_center.py,
  notifications/__init__.py, one_demo/check.py (checks), one/lists.py
  (lists.LISTS via lists.HOMES), one_legal/assemble.py (its own MODULES of 22),
  one_ai/center.py (PARTS = OneHR only, OneMail written in code), one/rights.py
  (the one_abilities hook).
- The list of apps is typed in at least 9 places: ready.MODULES 21, Dock 17,
  Sidebar JSONs 17, people.APPS 8 and APP_SAID 15, lists.HOMES 7,
  assemble.MODULES 22, modules.txt 23, one_demo/people.APPS 8, ready.OUTSIDE 15.
- Four maps of Frappe module → app disagree: hooks.one_module_heirs (30),
  one_studio/forms.py MODULES (17), one_ai/groups.py MODULES (22),
  scripts/print_formats.py MODULES (6). Manufacturing and Quality go to
  OneFactory/OneQuality in one and to One Inventory in another.
- Names disagree: OneAdmin / "One Admin" (apps.KEPT lists both); OneCloud /
  One Storage / onestorage; OneWriter / one_doc / onedoc; OneWorkbook /
  one_sheet / onesheet (brand.MARK_OF patches these).
- Marks live in 6 places: brand/*.svg (32, 11 for apps that don't exist),
  fixtures/custom_icon.json (79, by scripts/icons.py), the Dock, people.APPS,
  brand.MARK_OF, apps.ICONS.
- Nothing declares: needs (only Reading→OneAI), kept (apps.KEPT), private,
  jurisdictions, marketing (only APP_SAID one-liners), kind, rail position,
  which centres a module takes part in.
- Countries: one/countries.py (ONLY_IN 7, NO_INCOME_TAX, NOT_IN 11,
  TAX_INVOICE), hooks.company_data_to_be_ignored (12), "United Arab Emirates"
  in 8 non-demo files.

## 3. Names and layout

- Renames and what moves:
  - one_storage → OneCloud: 224 import lines in 58 files, 21 hooks lines, 5
    patches, 25 JSON module fields, notifications/one_storage (14), icon
    fixtures. 9 doctypes.
  - one_doc → OneDoc: 34 imports / 12 files, 10 hooks lines; doctypes still
    "Writer Document", frontend/src/writer, "OneWriter" 77 times in code.
  - one_sheet → OneSheet: 37 / 12, 15 hooks, 1 patch; doctypes Workbook*,
    "OneWorkbook" 72 times.
  - one_slide → OneDeck: 54 / 20, 18 hooks, own hook keys, public/slide (65
    files), frontend/src/slide (~30 own files), "OneSlide" 66 times.
  - one_legal → TrustCenter: 58 / 44 (every legal.py imports its registry).
  - one_account → AccountCenter: 54 / 23, 18 hooks, plain "one_account" in
    hooks lines 1266, 1310, 1341, 1362.
- Old names in code: Intake 141, OneIntake 21, "One Storage" 29, onestorage 35,
  oneslide 37, OneApp 2. brand/oneintake.svg, frontend/src/intake.
- Duplicated helpers (55 identical-body groups): `_lt` ×15, `_may` ×8,
  sha256 `_hash` ×7, home `_kept` ×6, default company wrappers (22 helpers;
  get_default_company called 98 times in 46 files though one/company.py
  exists), heads `_money` ×6, editors' templates.folder/_titled/titles/
  copied/placed/file_gone ×3, one_hr approve/reject ×3, story `_month(s)`
  ×4, one/privacy_copy.py repeating one/privacy.py.
- ~230 files over 400 lines: one_demo/check.py 4590, one/ai.py 3783,
  public/js/one_display/tv.js 2662, account_center.js 1776, hooks.py 1762,
  desk.css 1669, ready.py 1668.
- public/js has 133 top-level files, many belonging to one module
  (onecloud_dialogs.js, workbooks.js, text_writer.js, project_actions.js…).
- Dead: one/_tmp_q.py; frontend/src/writer/components/{ErrorPage,
  MarkdownEditor,NonCollabEditor,WriterLogo}.vue; frontend/src/task/
  TaskWaits.vue. `.claude/worktrees/` holds ~20 stale agent worktrees.

## 4. Guards, tests, skills

- 2,755 tests: 969 in tests/guards, 1,469 in tests/test_*.py, 317 in
  onedesk/*/tests. Full run ~2 minutes with xdist on this 2-core machine
  (CLAUDE.md still says 35s).
- tests/guards/registry.py: 17 points, 129 guards; 18 guard files are not in
  it. test_hooks.py is 663 parametrized tests (458 function-exists, 201
  asset-exists), 68% of guards.
- Overlaps: look/frame ~13 files; words 6 files, and test_wording (one or two
  sentences) contradicts test_copy (one); rail 5 files, "is it a frappe icon"
  three times; page lists declared in tiers.PAGES and in test_shell.py;
  test_shell polices a shell only onecalendar still uses.
- scripts: quick.py 72 (picks guards by name mention), close.py 176
  (rewrites fingerprints, re-dates looks), docs.py 244, overrides.py 3609
  (476 rows), reference.py.
- READY.md 1419 lines (19 mechanisms, 14 points), PASSOVER.md 339 (17 points);
  the two lists don't line up. Skills ~80 KB: ui 25, passthrough 23, wording
  9, ux 8, docs 7, changelog 4.5, legal 4.2, repeating READY and PASSOVER.

## 5. Shell, centres, setup, demo

- Nine centres, one router `onedesk.centers.open` (public/js/desk.js:291).
  All are frappe's SettingsDialog through two bases (module_settings.Dialog,
  module_docs.Dialog); seven `open()` functions each rebuild tabs, apps
  group, default tab, help; three ways to draw a section body (kit rows,
  CenterSection, shell.table). No SetupCenter; Getting Started is a tab in
  each ControlCenter.
- Module foot (one_interface/nav_tree.js:218): Settings, tour, Help, version;
  the same snippet copied in 13 `*_control.js` and portal.js.
- Top bar (chrome.js `bars`): workspace name, company switch, announcements,
  Search, Documents, Notifications, Background Tasks. Bottom: windows, Check
  In, Timers, Ask OneAI, weather, clock.
- Rail: Dock fixture dock/onedesk/onedesk.json (17 rows); site layer by
  one/companions.layer(); Edit Sidebar removed (shell.js:588), Manage Dock
  removed (outside.js); save_user_dock never called; AccessCenter levels
  hide nothing.
- one/apps.py: off hides only; NEEDS {Reading: OneAI}; KEPT One, OneAdmin;
  dialog public/js/apps.js (administrators).
- Wizard: public/js/setup_wizard.js (before_load: persona out, look and
  working day in, boot.one_setup_wizard slides, Standard chart forced, "Load
  the Demo Company" on dev); one/setup_wizard.py stages; one/setup_steps.py.
- Demo: one_demo/build.py 35 steps; two companies (SGA AED, SGS SAR); no
  presets; one_demo/check.py 4590 lines; start.py one click. Training copies
  are OneAdmin sessions (Fresh, Demo Data, Workspace Copy); no band or
  vignette.
- Look: look.js 973, tokens.css 408, palettes.css 194, canvas.css 1032
  (120 KB), frame.css 1366. Vue kit frontend/src/kit (18 components).

## 6. OneAdmin

- Signup: www/start.html → signup.start (Account Request; Lead and
  Opportunity by sales.signed_up; Stripe checkout) → webhook → signup.accept
  → Provision: place_it, name_is_free, create_site (rename a spare),
  site_is_up, route_it, push_config, invite_owner (site's account.wake),
  live. The form asks workspace name, email, jurisdiction, plan, time zone.
  Country is never set; the person's name is the email's local part; only
  the time zone reaches the site; the owner then meets frappe's wizard.
- Spares: spares.keep, 2 per open server, restored from the release's
  template site; nothing runs setup on claim.
- Plans: price_list.Plan (seats, storage, database, credits_a_month,
  own_server) → Offering (no features field) → Tenant quotas. No feature
  flags. Regions: jurisdiction Global/EU only.
- Training copies: Workspace Session (sessions.py), operators only, need
  Tenant.copies_agreed_on. Test workspaces: testbed.new, is_test.
- Connect Server makes: Cloudflare tunnel one-machine-N, CNAMEs pilot-/
  origin-machine-N, Access token and app, per-bench hosts; OneAdmin
  site_config keys, Workspace Server row, ticket, R2 servers/<name>/, misses
  default, Pilot webhook; on the machine podman, user one-copies, image and
  container one-box, user unit, and inside it cloudflared, Pilot, benches,
  agent, cron. Undo pieces exist: boxes.Cloudflare.forget, pilot.forget;
  servers.remove is AWS-only. Fixed 203a7458: a Connected field.
- 18 doctypes (Tenant and One Admin Settings 65 fields each); AGENTS.md 3058
  lines; setup.py 1237. "OneCredits" (the rejected form) 118 times.

## 7. OneAI

- one_ai 29,807 lines; reading/ (Intake) ~9,800 over 47 files.
- Tools: hooks one_ai_reads 98, one_ai_suggests 75; tools.hooked(); module
  ai.py REACH 64 and NOT_FOR_AI ~319. run.ask: 8-round loop on the
  workspace, model on OneAdmin; groups.chosen guesses 17 groups (173 tools)
  plus 22 CORE.
- act.py is the one write door: 9 kinds, Done/Proposed by a floor of 70,
  writes as oneai@one.invalid after the person's permission, undo per
  Reading Action. The precedent for Do it / Draft / Ask First.
- Intake planners and their owners: money.purchase/payment/bank → OneBook;
  money.goods/quotation → OneInventory; money.sales_order/extra_work and
  plans' customers, leads, contacts → OneCRM; employee, leave, expense,
  applicant → OneHR; site log, tasks → OneProject/OneTask; event →
  OneCalendar; contract → TrustCenter/OneCRM.
- Credits: OneAdmin gateway.call reserves, calls, settles; ledger.py; models
  13 kinds × 3 tiers; jobs.py 38 jobs, words/*.txt.
- Search: LanceDB on R2 per workspace.
- Workers in deploy/: edge, mail, keeper, watch, testmail; oneos and office
  are Container + Durable Object deployed by one_admin/setup.py
  (wrangler_config). No Agents SDK code yet. Today the account never calls a
  workspace; agents on Cloudflare would call workspace tools: a reversal.
- AutomationCenter seeds: OneMail Mail Rule and flow.py; OneStudio
  automations.py on frappe's Automation Flow; Extensions with guard.py and
  the studio_review second model.
- DiceBear 9.4.2 already a dependency (frontend/avatars).
