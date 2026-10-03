# The backlog

What One has decided to build later, or not yet, in one place. Each line says
what it is, why it waits, and where the longer note is. When one is built,
its line goes and the screen's own README says what it does.

## Products still to pass

The passover (`docs/PASSOVER.md`) has done Settings, One › Home, OneMail,
OneCloud, OneCalendar, OneTask and OneAdmin › Home. Still to go, one screen at
a time: **OneProject**, **OneCRM**, **OneBook**, **OneInventory**, **OneHR**,
**OneAI**, **OneIntake** and the rest of **OneAdmin**.

## Frappe's desk that One has not replaced yet

Gaps 7 to 11 in `docs/DESK-COVERAGE.md` (The desk around the doctypes):
erpnext's Help, the Communication inbox, search's pages and reports, frappe's
error pages, and four of frappe's reports. Gaps 1 to 6 are done
(`one/outside.py`, `public/js/outside.js`).

## Frappe that One does not reach yet (P3)

Small, or for some customers. Each row in `docs/DESK-COVERAGE.md` says the
same in a line.

- **A Lists page** for Salutation, Gender, Address Template and Print Heading
  (Tax Invoice, Proforma): small lists only reachable through a field today.
- **SMS** (SMS Settings, SMS Log): notifications by text message, which some
  markets expect. Needs a provider and its own subprocessor line.
- **Translation**: a workspace's own words for ours, such as calling a Lead a
  Prospect. Needs to stay out of what OneAI and the READMEs say.
- **Prefilled new records** (Document Template): a standard quote, a standard
  job opening.
- **Following a record** (Document Follow): a digest of a record's changes.
  The bell already tells a record's people; this is for anybody else.
- **Session defaults** (Session Default Settings): the values a person works
  under. One has a single company, so little is left of it.
- **What happens after saving** (Success Action).
- **Slack** (Slack Webhook URL): notifications into a channel. Webhooks
  already reach Slack through Zapier or n8n.
- **UTM Campaign and Medium**: OneCRM has Lead Source, not the other two.
- **A form sent to one person** (Web Form Request), with OneForms.
- **LDAP**: enterprise sign-in.

## Decided against for now (Later)

- **Import and Export** (Data Import, Data Export): bringing customers, items,
  employees and balances in from a spreadsheet. The first thing a new
  workspace needs, and its own feature, not a door to frappe's.
- **Signing in with Google or Microsoft** (Social Login Key).
- **Another app acting for a person** (OAuth Client, OAuth Provider Settings,
  OAuth Settings).
- **One reaching into an outside service** (Connected App).

Webhooks are the integration One offers today (Workspace › Webhooks).

- **OneStudio, not yet**: an extension behind an API call, a table inside a
  custom collection, and a collection's own numbering.

## Stages not finished

- **The phone answer** (stage 7 of the window shell): what the dock and the
  windows become on a phone.
- **frappe-ui beta.55 to beta.76** (DESK 2b): catch the frontend up.
- **The hostname** (INFRA 1): where a workspace lives by default.

## Noticed along the way

- **Sign-in** says "288 sessions" for the administrator: it counts every
  session ever left open, not the devices a person uses.
- **Profile**: whether HR is told when a person changes their address or
  emergency contact. A OneAI button, Check My Profile, and Write It With
  OneAI under Bio. A proof of address Intake reads could offer to update it.
- **Agreements**: whether administrators are told by mail when their
  organisation's agreements change. `gate.require()` when an application is
  turned on.
- **Audit Log**: telling the administrators of a sudden large export.
- **OneBook › Bank**: erpnext's reconciliation tool shows a banner for its
  newer Banking app, which One does not carry.
