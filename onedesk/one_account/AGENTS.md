# OneAccount

The one file for agents, OneAI and us: what OneAccount is made of, its
rules, where each file is, and the decisions that cost something. What
people read is in `docs/`, one page per thing they do, shown in Help and
searched by OneAI's `how_to`; its versions are `docs/changelog/`. What is
known to be wrong and what is planned is `SCRATCHPAD.md` (docs/READY.md, A
module's folder). Why it exists is `docs/ONE.md`.

OneAccount is your own account and the workspace's: your profile and how you
sign in, and for administrators, the workspace's people, devices, plan and
domains. AccountCenter shows all of it.

## Connections

- **From One**: who may use which app (`one/people.py`), the record a section
  saves against as it was loaded (`one/sections.py`), the account the
  workspace holds with One (`one/account.py`), and Home's cards about the
  plan and domains, which link here.
- **From OneHR**: a person's employee record, shown on their profile, and the
  passkeys a clock-in uses (`one_hr/passkey.py`).
- **From OneAdmin**: the plan, credits, invoices, domains and closing, which
  the control plane keeps and the workspace asks for.
- **To One**: what each role of an app may do is set in AccessCenter; People
  sets which level each person holds.
- **To OneAI**: One's own tools read people, the plan and domains through
  `center.py`. OneAI changes nothing here (`ai.py`).

## Under the hood

**OneAccount has no window.** AccountCenter is a dialog
(`public/js/one_account/account_center.js`) that opens from the avatar's menu,
from a link (`/desk/one?center=account&at=plan`, desk.js `onedesk.centers`)
and from every place that used to open Settings, so it has no foot or
settings dialog of its own (`ready.MODULES["OneAccount"]["windowless"]`).

**A section is an Editor whose page is its panel.** Each tab is an
`onedesk.AccountSection` (shell.js `Editor`), so a form saves against the
records as they were loaded and is refused with frappe's own message when
somebody saved first, exactly as the Settings page did. The panel's header
stands in for the page (`onedesk.account_center.page`): the indicator after
the title, the primary action, and the record's actions as menus.

**Files**:

- `center.py`: the sections, who may open each (`_may_open`), and their
  loaders and savers, moved from `one/settings.py`.
- `signin.py`, `devices.py`, `invite.py`, `owner.py`: signing in, the
  browsers people sign in on, inviting somebody, and a new workspace's first
  administrator.
- `bills.py`, `heads.py`, `closing.py`, `private.py`: One's invoices to the
  workspace, what the account says above its fields, closing the workspace,
  and private apps.
- `doctype/`: Device, Workspace Account, Workspace Add-on, Workspace Domain.
- `abilities.py`: one ability, `plan`, so a role can read Plan and Credits
  without being an administrator.
- `notifications.py`, `legal.py`, `setup.py`, `tour.py`, `ai.py`: what it
  tells people, adds to the agreements, asks while setting up, tours, and
  leaves to people rather than OneAI.

## Decisions

- **Plan and Credits can be read without administering.** Accounts staff
  need the invoices; changing the plan, paying and closing stay an
  administrator's, and closing the person it is billed to.
- **Who may use which app is One's, not OneAccount's.** People sets it, but
  AccessCenter, the setup wizard and OneAI set it too, so it lives in
  `one/people.py`.
