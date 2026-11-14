# OneQuality

The one file for agents, OneAI and us: what OneQuality is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `help/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `updates/`. What is known to be
wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A module's
folder).

OneQuality is how the company keeps its work right: procedures, goals and
their reviews, non conformances and the actions that fix them, meetings and
feedback. It was part of OneInventory until November 2026.

## Connections

- **From OneInventory**: Checking goods (Quality Inspection) stays there, on
  the receipt or the stock it checks.
- **From OneCRM**: Quality Feedback can be a customer's.

## Under the hood

### What it is made of

ERPNext's Quality Management module: Quality Procedure, Quality Goal,
Quality Review, Quality Action, Non Conformance, Quality Meeting, Quality
Feedback and its template, and the Review report. `hooks.py`
`one_module_heirs` names OneQuality their heir.

**Why it left OneInventory.** It is not about stock: it is how a company runs
its work. A workspace turns it on or leaves it off, and People gives it to a
site supervisor without the stores. Decided with Yamen on 5 November 2026;
a OneGovernance (policies, risk, compliance) would be a separate app.

- `access.py` — ERPNext gives quality management to its Quality Manager
  alone and lets every desk user read it. `GIVEN` lets the Quality User
  (One's role, made from `access.py` DEFAULTS) work every record and use
  the feedback templates, and opens the Review report to both.
- `access.py`, `resolve.py` — Resolve Non Conformances, a Permission Type
  on Non Conformance (`permission_type/`). `resolve.guard` (validate)
  refuses setting a non conformance to Resolved without it.
- `home.py`, `page/onequality` and `frontend/src/quality/QualityHome.vue` —
  the Home, an island (`tiers`): problems open, action steps overdue
  (Quality Action Resolution's `completion_by`), goals whose latest review
  failed, meetings open, and the directory. The page's roles decide who
  reads it, since ERPNext lets everybody read a non conformance. OneStudio
  hears `onequality_home.shown`.
- `custom/quality_action.json` — `one_non_conformance` ties an action to
  the problem it fixes; Non Conformance lists them under Actions, and
  `heads.nc_actions` and `heads.action_problem` say so on each head.
  `custom/non_conformance.json` titles a problem by its subject, hides
  ERPNext's Process Owner address for the name, and asks no status of a
  new one.
- `tell.py` and `notifications.py` — Non Conformance Raised, after insert,
  to every Quality Manager but whoever raised it; Non Conformance Resolved
  to whoever raised it; Quality Step Overdue, each morning, to whoever is
  responsible for a step due yesterday.
- `agent.py` — the suggestions on Home, a non conformance, an action and a
  procedure, the Home's sentence (`page`) and `quality_now`, which reads
  what Home shows. OneAI changes nothing (`trust.py` says so), but for its
  inspector's one job (`WATCH`, `watch.rejected`): a Quality Inspection
  submitted as Rejected is an open Non Conformance with the readings that
  failed, at Draft, against the procedure of the inspection's template's
  name or the only procedure; where neither is known, against the one used
  last, as a card (one_ai/agents/work.py).
- `custom/quality_meeting.json` — the meeting list's columns.
- The demo (`one_demo/quality.py`): the curtain wall's procedure, its goal
  and last month's failed review, the action it asked for, a non conformance
  for sealant laid in the cold, the monthly meeting and Marina Hotels'
  feedback. Karim manages quality, Tariq uses it.

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, Resolve Non Conformances, is `access.py`.
- **Setup** needs nothing of its own (`setup.py`). **Its tour** is
  `tour.py`, over the rail, since its screens are frappe's own.
- **Its foot and settings** are `public/js/one_quality/quality_control.js`.
- **Its checks** are `checks.py`, run with the rest by `one_demo/check.py`.
