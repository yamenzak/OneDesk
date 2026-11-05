# OneQuality

The one file for agents, OneAI and us: what OneQuality is made of, its rules,
where each file is, and the decisions that cost something. What people read
is in `docs/`, one page per thing they do, shown in Help and searched by
OneAI's `how_to`; its versions are `docs/changelog/`. What is known to be
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
  (One's role, made from `abilities.py` DEFAULTS) work every record and use
  the feedback templates, and opens the Review report to both.
- `abilities.py`, `resolve.py` — Resolve Non Conformances, a Permission Type
  on Non Conformance (`permission_type/`). `resolve.guard` (validate)
  refuses setting a non conformance to Resolved without it.
- `tell.py` and `notifications.py` — Non Conformance Raised, after insert,
  to every Quality Manager but whoever raised it.
- `ai.py` — the suggestions on a non conformance, an action and a
  procedure. OneAI reads quality through the generic tools and changes
  nothing (`legal.py` says so).
- `custom/quality_meeting.json` — the meeting list's columns.
- The demo (`one_demo/quality.py`): the curtain wall's procedure, its goal
  and last month's failed review, the action it asked for, a non conformance
  for sealant laid in the cold, the monthly meeting and Marina Hotels'
  feedback. Karim manages quality, Tariq uses it.

### What READY asks of it

- **Notifications** are `notifications.py`, sent by `tell.py`.
- **Its one ability**, Resolve Non Conformances, is `abilities.py`.
- **Setup** needs nothing of its own (`setup.py`). **Its tour** is
  `tour.py`, over the rail, since its screens are frappe's own.
- **Its foot and settings** are `public/js/one_quality/quality_control.js`.
- **Its checks** are `checks.py`, run with the rest by `one_demo/check.py`.
