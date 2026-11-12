# One's first experience: OneRegistry, OneHub, the Marketplace and setup — the plan

12 November 2026 · Yamen · written in [the live doc](https://claude.ai/artifact/WhBYm1H7HBYxuXdgUgRsMv); this copy is the one the code is held to.

## The arc

One sets itself up the way a new phone does: one guided pass, before payment, that asks about the company, its field and its apps, and leaves every app ready, so nobody has to dig for a setting later. Behind it, everything that makes One gets declared in one place, OneRegistry, so the wizard, the Marketplace, the rail, OneHub, the agents and OneLint all read the same truth.

Why now and not later: the code has been rewritten many times, and the traces show (ready, the ready registry, the passover, names on screen that differ from names in code). The AI arc's agents read the code and the registry to know what they may do, so a registry that is complete and names that match are what keep them from guessing. Doing this once, properly, costs less than the rewrite that would follow from building agents, a Marketplace and a wizard on today's foundations.

This arc and the AI arc share a foundation and then run side by side; the merged order is in the last section.

## Where things stand today

What this arc builds on exists in pieces, declared in a dozen places that don't know about each other; nothing is missing so much as scattered. Read from the code on 12 November 2026:

| Area | Today | The gap |
| --- | --- | --- |
| Registry | `ready.MODULES` holds 21 apps with readiness keys; 17 more registries live in hooks (abilities, AI tools, notifications, homes, verbs…), plus the Dock, `people.APPS`, legal's own module list and the icon fixtures | OneCloud and OneStudio aren't in it; no dependencies, setup, jurisdiction or marketing anywhere |
| Enabling apps | `one/apps.py`: a list of hidden Sidebars; off only hides | One dependency is written down (Reading needs OneAI); OneBook, OneInventory and OneHR can be switched off |
| Centres | Nine, all on frappe's settings dialog, opened from One's rail or a module's foot | No home for them; UpdateCenter is only release notes; TrustCenter mixes agreements, data companies and privacy requests |
| Rail | frappe's Dock; One hides Edit Sidebar | Nobody can reorder it; no folders; AccessCenter levels don't hide rows |
| Setup wizard | frappe's new wizard, with One's look, working day and three apps' steps (OneMail's domain, private mailboxes) | Runs on the site after signup; nothing per app beyond that; the Account Request's answers are not used; no company can be made later |
| Regions | UAE built (VAT return, papers, TRN); ERPNext ships UAE, Saudi (via UAE), Italy, France, US, Australia, South Africa, Turkey; charts for 72 countries | Germany has charts only; ACCOUNTS.md warns no national chart has payroll accounts |
| Demo | One company and a Saudi branch, 35 steps | One industry; it hadn't been built from scratch since the 3 November upstream update, and failed twice tonight on that |
| Copies | Operators can start one from OneAdmin; the workspace only agrees to them | No button for the workspace; no mark that a copy isn't live |
| Guards | 2,647 tests, 129 registered guards over 17 points; about two minutes in parallel | Several check the same thing; CLAUDE.md still says 35 seconds; some guard files police screens being retired |
| Media | 113 Help pictures | No clips at all; five apps have no pictures |

## OneRegistry

Every app, module and centre declares itself once, in a `manifest.py` in its own folder, and OneRegistry collects them; today's `ready.MODULES`, the 17 hook registries, `people.APPS`, legal's module list and the Dock all become readings of it instead of separate lists.

Written by: the app's folder (`manifest.py` beside its code), the centres and OneHub (each centre declares itself too), and private apps (the same manifest, kept apart). OneRegistry holds identity, needs, kept, setup steps, centres, roles, jurisdictions, its agent, marketing, readiness and the tests it owns; OneLint checks it and docs publish it. Read by: what people see (Marketplace, rail, OneHub, wizard), the agents (who owns what, and its tools), and OneAdmin and OneLint (plans, releases, standards).

What a manifest declares:

| Part | What it says | Replaces |
| --- | --- | --- |
| Identity | Id, name, one line, mark, kind (app, centre, engine), rail position | `ready.MODULES` names, `people.APPS`, the Dock rows |
| Needs and kept | Apps it cannot run without; when it can never be turned off | `apps.NEEDS`, nothing for kept |
| Setup | Its steps: settings, masters, people, in order, each with what it asks and what it makes | `setup_steps.STEPS` (three apps today) |
| Centres | Which centres it has a part in, and the part | `module_settings.centers`, each centre's own list |
| Roles and agent | Its roles and levels for AccessCenter; its agent and that agent's tools | `one_abilities`, `one_ai_*` hooks |
| Jurisdictions | Countries it is built for, ready for, or not checked in: tax, papers, payroll, holidays | `one/countries.py` and scattered `if country == UAE` |
| Marketing | Its Marketplace page: paragraphs, pictures, clips, price notes | nothing |
| Readiness | Today's fourteen points and hand looks | `ready.MODULES` ready, checked |

The manifest is code, so it is checked: OneLint fails a manifest that names a file, role, step or picture that doesn't exist, the way `test_ready.py` does today but in one place. docs/MODULES.md becomes a generated view of it. Nobody has to read the registry for it to matter: every screen above reads it, so a missing line shows up as a missing card, step or permission.

## Names

Every folder, module and mark gets the name people see, so the code, the screens and the agents say the same thing; the app id `onedesk` and the GitHub repository stay, because no one sees them and changing them breaks every server. Three folders carry an old name, and the centres carry names the code never uses.

| Today in code | On screen | Size of the rename |
| --- | --- | --- |
| `one_storage`, module One Storage, mark `onestorage.svg` | OneCloud | 146 files, 12 doctypes, 5 patches, 60 imports from outside; routes already say `onecloud` |
| `one_doc`, mark `onedoc.svg` | OneWriter | 64 files, 3 doctypes |
| `one_sheet`, mark `onesheet.svg` | OneWorkbook | 66 files, 4 doctypes |
| `one_legal` | TrustCenter | a centre name over a module; decided with the centres |
| `one_account` | AccountCenter | the same |

**How a rename is done safely:** one module per commit; the folder moved with `git mv`; the Frappe module renamed with a patch that updates `Module Def` and every doctype's `module`; imports, hooks, fixtures, notification folders and docs moved; the old dotted paths kept as thin re-exports for one release so a server mid-update doesn't break, then deleted. Each rename is a release of its own, so a problem shows on one module.

**OneWriter, OneWorkbook, OneSlide.** You dislike the names; this is the moment to choose them, before their Marketplace pages and marks are made. One takes no plural, so: **OneDoc, OneSheet and OneDeck**, the last replacing OneSlide.

**The product name.** The product stays **One**; OneDesk is only the repository. Calling the whole product OneOS is tempting, but OneOS already means the desktop-in-the-browser in 635 places and 139 translated strings, and "One" is what every screen, mark and agreement says. My recommendation: keep **One**, and rename the containers from OneOS to **OneSandbox** only if OneGuard (below) makes "sandbox" the natural word for opening a risky link or file; otherwise OneOS stays as it is.

## Apps and dependencies

Turning an app off hides it and stops new records being made in it; the code, the data and every link to it stay, so turning it on again loses nothing. That is how it already works (`one/apps.py`: off only hides from the rail, search and pickers); what is new is that apps declare what they need and what can never be turned off.

What each app declares in OneRegistry:

- **Needs:** apps it cannot run without. OneFactory needs OneInventory (a work order's materials are stock); OneDisplay needs OneSlide (a playlist plays a presentation); a private app such as Rua needs whatever its hooks use. Turning an app on turns on what it needs, and says so; turning off something another app needs is refused, naming that app. Today only "Reading needs OneAI" is written down.
- **Kept:** apps that cannot be turned off once they hold records: OneBook once there is a submitted entry, OneInventory once there is stock, OneHR once there is an employee. They can be hidden from the rail for people who don't use them, never switched off for the workspace.
- **Private:** a private app is never uninstalled once claimed, because it may have changed record types and fields. It can be hidden; removing it is a support job, not a switch.

**The editors become apps of their own.** OneWriter, OneWorkbook and OneSlide are already full modules (`one_doc`, `one_sheet`, `one_slide`), reached only through OneCloud. They get their own entries in the Marketplace and rail. Off means nobody can make a new document of that kind; existing ones still open, read-only, so a file never becomes unreadable. Their names are part of the naming decision below.

ERPNext and HRMS stay required underneath (`required_apps`), invisible: One's apps are how people reach them.

## OneMarketplace

OneMarketplace replaces the Apps dialog with a store a workspace's owner browses: every app sells itself with its own words, pictures and short clips, and installing one opens its setup straight away. Only owners see it, as only administrators see the Apps dialog today.

An app's page in the Marketplace:

- **What it is:** its mark, name, one line, and a few paragraphs on what it does for the company, written for a buyer, not a manual.
- **Shown, not told:** three to six pictures and clips of the app working on the demo company, shot with `scripts/clip.mjs` (clips of at most nine seconds). Today there are 113 Help pictures and **no clips at all**, and OneFactory, OneQuality, OnePortal, OneCloud and OneStudio have none of either, so every app needs a shoot.
- **What it needs and costs:** the apps it brings with it, the plan it needs, the credits it uses.
- **Install:** turns it on (with what it needs), then opens its steps in SetupCenter. **Turn off** follows the rules above.

All of this is declared by the app in OneRegistry (its marketing block) and lives beside its code; the Marketplace only draws it. Private apps show in the same store, under the company's name, once claimed. Later, the same pages become the public site's app pages.

## OneHub and the centres

OneHub becomes the home of every centre, a full window of its own like a phone's Settings app, and the centres leave the module foot for the top bar. Opening a centre from a screen still opens it on that screen's part, as a large sheet with a way up to OneHub, so nobody loses their place.

**How a centre is reached:**

- **The top bar's tray.** An arrow at the right of the top bar, as Windows shows hidden icons, opens a popover of every centre the person may open, with the one for the current screen first. Notifications and OneAI's place stay where they are.
- **OneHub on the rail.** The One mark, reimagined, at the top of the rail opens OneHub: every centre as a tile, searchable, each opening as a page with its sections down the side.
- **From a screen.** The module foot keeps only the version and Help; Settings moves to the tray, opening that app's part of ControlCenter.

**One look for all of them.** Today all nine are frappe's settings dialog with different insides. They become one layout drawn by OneInterface: sections on the left, the section's content as cards on the right, the same header, search and save, inside OneHub or the sheet. Each centre declares itself in OneRegistry like an app.

| Centre | What it is for | What changes |
| --- | --- | --- |
| SetupCenter | Each app's setup steps, done and waiting; where Install lands | New; ControlCenter's sibling |
| ControlCenter | Each app's settings | Moves into OneHub; ERPNext's settings reached from here |
| UpdateCenter | Your update window, Update Now, what's coming and what changed | Today only release notes; What's New moves inside it |
| TrustCenter | Agreements, the companies that receive data, optional services, privacy requests, and updates waiting for your agreement | The approvals that hold an update move here, plainly |
| AccessCenter | Who may open which app and at what level; the rail follows it | Its levels also hide rail rows |
| AccountCenter | Plan, add-ons, credits, invoices, your companies | Gains company management (below) |
| AICenter | The agents (AI plan) | Per the AI plan |
| NotificationCenter | What reaches whom, how | Unchanged inside |
| HelpCenter | Help for the apps that are on, searchable | Hides apps that are off; OneCloud and OneStudio get pages |
| ShortcutCenter | Keys | Unchanged inside |

Each centre gets its own redesign pass inside the shared layout, starting with the three that confuse most today: UpdateCenter, TrustCenter and HelpCenter.

## The rail and the app picker

Each person arranges their own rail like a phone's home screen: drag to reorder, drop one app on another to make a folder, rename the folder, and the rail shows only the apps they may open. It builds on frappe's Dock, which already keeps a layer per person (`save_user_dock`), so the arrangement is stored where frappe stores it and survives upgrades.

- **What appears:** the apps that are on for the workspace, minus those AccessCenter gives this person no level in. Today only frappe's module blocks and a few hand rules hide rows; AccessCenter's levels will decide it.
- **Folders:** a folder is a rail row that opens a small grid of its apps, with a name the person types. Frappe's Dock has no folders, so this is One's own layer over it, kept in the person's settings.
- **Defaults:** a new person gets the workspace's order, which an administrator sets once in SetupCenter; their own changes sit on top and can be reset.
- **The app picker:** with dozens of apps, the grid button opens a searchable launcher of every app the person may open, grouped like the Marketplace, with recent ones first.
- **On a phone:** the rail becomes the launcher; folders open the same way.

## The setup wizard

The wizard runs in OneAdmin, starting on the public site before anyone pays, and the workspace arrives already set up: payment is the last question, the build starts then, and the person keeps answering each app's steps while their site is being built. Today the owner lands on an empty site and meets frappe's wizard there; the Account Request's country and name are thrown away.

In OneAdmin, before and during the build:

1. You and the company: country, field, companies.
2. Apps: preset by field, with needs.
3. Plan, region, payment: the build starts on payment.
4. Each app's steps, while the site is being built.
5. People and access: who joins, at what level.
6. Answers applied: one setup job on the site.

In the new workspace:

7. You land in One, configured, people invited.
8. SetupCenter: what was skipped waits here.

**What it asks, in order:**

1. **You and the company:** name, country, language, currency, the company's **field** (clinic, real estate, manufacturer, trading, contracting, services, retail, other), and, if there is more than one, each company.
2. **Apps:** preset by the field, each with one line and what it brings with it; the person adds and removes. Needs are honoured; kept apps are explained.
3. **Plan, region and payment:** the plan, where the data lives (the region, which today is only Global or EU storage), and payment. On a paid plan with its own server, which server.
4. **Each app's steps:** read from OneRegistry, in the order the apps need them (OneBook's chart and fiscal year before OneHR's payroll), as thorough as each needs: OneMail's domain and mailboxes, OneHR's working week and leave, OneInventory's warehouses, Home's news sources and weather city. Any step can be skipped and waits in SetupCenter.
5. **People and access:** who to invite, and their level in each app.

**How answers reach a prebuilt site.** A site comes from a spare, already made from the template, so the wizard cannot run on it. The answers are kept in OneAdmin and handed to the site as one setup job right after it is claimed: it runs frappe's own `setup_complete` with them, then each app's step functions, as the demo's builder does. Tonight showed the traps this job must handle: frappe refills answers from System Settings when its own part counts as done, its wizard no longer makes a user, and One's roles must exist first. The demo and this job become the same code, so the demo tests it every build.

**Regions.** The wizard follows frappe and ERPNext: country picks currency, time zone, number and date formats, holidays and taxes. The chart of accounts stays One's Standard chart with the country's taxes, never the country's own chart by default, as docs/ACCOUNTS.md explains. Each app's manifest says, per country, whether it is **built** (UAE today: VAT return, papers, TRN), **works** (ERPNext's regional code: Saudi, Italy, France, US, Australia, South Africa, Turkey) or **not checked**, and the wizard says so plainly when a country isn't built.

**Companies.** Today there is no way to make a second company. The wizard makes the first ones, and AccountCenter gains a Companies section that makes more later the same way: name, country, currency, chart, its own letter head.

**Analytics.** Each step a person reaches, finishes, skips or leaves is recorded in OneAdmin against their signup, which is already a lead and a deal in our own OneCRM, so OneAdmin's Home shows where people stop. Before payment nobody has agreed to anything, so this needs its own line in the privacy policy and only covers what they type into the wizard, never the site afterwards.

## Demo data and training copies

The demo grows from one glazing contractor into a group of companies in different fields, written by hand rather than generated, so a clinic, an agency or a factory each finds itself in it. It keeps doing its second job, being the data every check and end-to-end test runs on.

**One group, several companies first.** A holding company with five companies, each its own field: the glazing contractor that exists today (contracting and manufacturing), a clinic, a real estate agency, a trading company, and a services firm. One build covers five fields and also exercises the several-companies work every module owes. Separate single-company demos per field come later, only if sales needs a clinic to show nothing but a clinic.

**Each field has a preset.** The wizard's field question applies that field's preset: which apps are on, the setup answers it suggests, and, for a training copy, which demo company to load. The preset is declared beside the demo company it matches, so the two can't drift.

**Training copies from OneHub.** Training copies become a feature a plan includes or not, beside storage and seats (plans carry only quotas today). A workspace on a plan that includes them, having agreed to the service, starts a copy itself from OneHub: **Fresh**, **From the demo** (pick a field), or **From our data** (a snapshot of last night). Today only operators can start one. It runs on a connected server, lasts as long as chosen, mails nothing, runs no schedules, and is deleted when it ends. A fresh copy runs the same setup job with the workspace's own wizard answers, so it is set up like theirs and empty. A copy from the demo starts in about a minute: each release builds a ready demo database beside the template site, and the copy opens on the company of the field picked. A copy of their data restores last night's backup, as today.

**A copy never looks live.** Every copy and dev site wears a soft vignette around the window and a band in the top bar: "Training copy, ends 20 Nov. Nothing here is real." Tonight one.4dl.dev nearly became that test: a site rebuilt three times, with no visible way to tell it from a live one.

## OneLint

OneLint is One's coding standard as one tool: it reads OneRegistry and each app's code, runs the checks that apply to what changed in seconds, and is the only thing the skills point at. Today the standard is spread over 2,647 tests, 129 registered guards, seven skills, a 77 KB READY.md, a 20 KB PASSOVER.md and a `close.py` that repairs what the guards would fail.

**What it keeps from today:** the idea that a rule is a check with an example proving it still catches (the guards' best habit), the generated docs, the overrides ledger, and every rule that has caught a real mistake.

**What it changes:**

- **One rule, one place.** Today the frame and look are policed by six files, words by three, the rail by two, page lists by two. Each rule lives once, named, with its reason and its example.
- **Rules are owned.** A rule says which manifest field or folder it reads, so a change to OneMail runs OneMail's rules and the shared ones, not the 677 parametrized asset tests. Target: under 20 seconds for what changed, under a minute for everything.
- **Facts, not fingerprints.** Readiness becomes what the manifest declares and OneLint verifies, not hand-looks re-dated after every version.
- **Skills read it.** The seven skills and the frappe skills (cloned by `setup.sh`) are rewritten as short guides that defer to OneLint's rules by name, so the agents in the AI arc follow the same standard we do.
- **Tests run on the demo.** End-to-end checks run on the demo group, which is why the demo must build from scratch every release.

Done as a migration, not a rewrite in one go: OneLint first wraps the existing guards, then each point moves into it and its old files are deleted, with the count of tests and the run time measured before and after.

**Its name.** OneLint says what it does to developers; nobody outside sees it. OneLint is standards; security is OneGuard's. OneGuard's rules for exploitable code run inside OneLint before a release ships, so there is one tool to run and two owners of what it checks.

## OneGuard

OneGuard protects a workspace while it runs, the way Defender or Knox protects a device: it stands between the outside world and the workspace's mail, files, links and the actions people and agents take. It comes after OneLint and the agents, because it is built from both.

| Threat | What OneGuard does | Built on |
| --- | --- | --- |
| Spam, phishing, a sender pretending to be the boss | Scores every mail; holds risky ones with a reason; warns on a lookalike domain | Intake's sorting today (Spam, Phishing verdicts) becomes OneMail's agent's first job |
| A link in a mail or chat | Opens it in a throwaway browser in a sandbox and shows what it leads to before anyone clicks | OneOS containers, a browser image |
| An attachment or uploaded file | Opens, unpacks and checks it in a sandbox; strips macros; shows a safe preview | OneOS containers, the office image |
| A risky action | An unusual payment, a supplier's bank details changing, a mass export: asks for a second person | The agents' Ask First level and audit trail |
| Code a workspace runs | Automations are built from AutomationCenter's blocks, each writing only its own safe part; agents' scripts are read before they run | OneStudio's `guard.py` and the second-model review |

OneGuard also owns security in One's own code: a whitelisted method without its permission check, SQL built from input, a secret in the code, a guest page that says too much. Those are OneGuard's rules, run inside OneLint before a release ships.

**OneStudio is out of this arc.** Most server scripts move to AutomationCenter (in the AI plan): a node builder like n8n, where each block writes its own part of the script, so an automation is predictable and safe and needs no review. Client scripts and deeper customisation become paid work, and later perhaps a redesigned OneStudio sold as an add-on, in an arc of its own.

**On the name of the containers.** Once OneGuard opens links and files in throwaway machines, "sandbox" is the word people already know. That is the moment to rename the containers from OneOS to **OneSandbox**, if you still want OneOS free for something bigger.

## Brand

Two families of marks: One's own places (OneHub, OneCredit and every centre) wear the One circle with the 1 reimagined for each, and apps keep their own picture marks, held to the standard of OneDisplay and OneMobility. OneInterface owns both, and owns each workspace's own branding on top (its logo, colours and name in the shell), so white-labelling is one setting in one place.

| Family | Marks to make | Marks to redo |
| --- | --- | --- |
| One circle | OneHub, OneCredit (gold rim, the 1 struck like the euro), SetupCenter, UpdateCenter, TrustCenter, AccessCenter, AccountCenter, ControlCenter, NotificationCenter, HelpCenter, ShortcutCenter | AICenter, taking OneAI's mark refined |
| Apps | OneChat, OneOS (or OneSandbox), OneMarketplace, OneGuard, OneDoc, OneSheet, OneDeck | OneFactory, OnePortal, OneQuality and OneSheet, which today are a sawtooth roof, three ellipses, a shield with a tick and a sigma |

Today every mark shares one kit (`chassis-edge`, `beacon-grad`), which keeps them a family; OneFactory and OneQuality even share a gradient id. The redo keeps the kit and gives each its own idea. Marks for the eleven apps that exist only in `brand/` (OneCode, OneDB, OneMarket and others) wait until each app is planned.

## Build order, risks and decisions

The foundation goes first and alone, because it is cheapest now: no customer workspace exists yet, so renames and a new registry break nothing outside our own servers. After it, this arc and the AI arc run side by side, each step proving one thing before the next. The brand marks are a design track that runs alongside from step 3.

1. **Foundation:** OneRegistry, the renames, OneLint around today's guards. Before any workspace exists, while renames cost the least. *Gate: every list reads the registry; checks in a minute.*
2. **Setup:** one setup job for signups and the demo, SetupCenter, companies. The wizard moves into OneAdmin, before payment; AI step 1 starts beside it. *Gate: a signup lands configured, and the demo builds from scratch.*
3. **OneHub,** the centres in one look, the tray, the rail. UpdateCenter, TrustCenter and HelpCenter redone first; AI step 2 (OneChat). *Gate: every centre reached from OneHub and the tray.*
4. **OneMarketplace,** needs and kept, the editors as apps. Each app's page and clips shot on the demo; agents for every module. *Gate: installing an app lands in its setup steps.*
5. **The demo group,** field presets, training copies from OneHub. Five companies in five fields; the vignette on every copy.
6. **OneGuard and the sandbox.** Links and files opened in throwaway machines; risky actions held.

**Risks worth naming:**

- **Renames under live sites.** Each rename keeps its old paths working for one release; the first customer arrives after them, not during.
- **Keeping upgrades free.** ERPNext and HRMS screens stay desk-native with small islands, as the passover set; only One's own apps get bespoke screens. OneHub and the centres are ours, so frappe's settings pages are reached from ControlCenter, not redrawn.
- **The setup job is a single point of failure.** It is the demo's code too, so it runs on every release build; a broken setup breaks the build before it reaches a customer.
- **Scope.** Six steps across both arcs is months of work. Each step is shippable on its own, so a pause after any of them leaves One better, not half-built.

**Decisions for you:**

- [ ] The editors' names: OneDoc, OneSheet, OneDeck.
- [ ] The product stays **One**; OneOS stays the containers' name until OneGuard, then perhaps OneSandbox.
- [ ] The demo as one group of five companies in five fields first, separate field demos later if sales needs them.
- [ ] Wizard analytics before payment, with their own privacy line.
- [ ] Which country is built next after the UAE: Germany (charts exist, no VAT return or payroll yet) or Saudi Arabia (ERPNext's regional code reuses UAE's).
- [ ] OneBook, OneInventory and OneHR kept once they hold records (can be hidden, never switched off).
- [ ] Start with step 1, the foundation, alone.
