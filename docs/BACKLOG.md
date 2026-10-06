# The backlog

What One has decided to build later, or not yet, in one place. Each line says
what it is, why it waits, and where the longer note is. When one is built,
its line goes and the screen's own README says what it does.

## Products still to pass

The passover (`docs/PASSOVER.md`) has done Settings, One › Home, OneMail,
OneCloud, OneCalendar, OneTask, OneAdmin › Home, OneStudio › Extensions and
Forms, and the portal with the public Your Data page. Still to go, one
screen at a time: **OneStudio › Record Types**, **OneProject**, **OneCRM**,
**OneBook**, **OneInventory**, **OneHR**, **OneAI**, **OneIntake** and the
rest of **OneAdmin**.

## Next after the foundations: project templates

Decided, and built right after the foundations arc (`docs/PASSOVER.md`, Up
next): a template page in the OneProject rail that edits a template in the
Tasks table ("Day 12 · 5 days"); a library of presets shipped as files and
copied into a workspace on use, starting with aluminium & glazing; and OneAI
drafting a template from a description.

## Frappe that One does not reach yet (P3)

Small, or for some customers. Every other doctype frappe ships is reached in
One, runs underneath, or is the platform's.

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

- **OneStudio, not yet**: an extension behind an API call, and a table inside
  a custom collection.
- **Custom apps**: a workspace's own app in the dock, with its own icon, rail
  and Home, holding its custom collections (a Fleet app for vans, drivers and
  trips). Needs its own roles, a place in People and in the switcher. Today a
  collection sits in a group of one of One's apps.

## Stages not finished

- **The phone answer** (stage 7 of the window shell): what the dock and the
  windows become on a phone.
- **frappe-ui beta.55 to beta.76** (DESK 2b): catch the frontend up.
- **The hostname** (INFRA 1): where a workspace lives by default.

## OneProject billing (P2)

Checked against ERPNext while passing OneProject's Time tab.

- **Advance recovered by share**: an advance comes off each invoice in full
  until it is used up. Many building contracts take back a share of each
  bill, say 10%. Today the amount is changed by hand on each invoice.
- **Retainers other than monthly**: `retainer.py` bills by calendar month
  only, so a quarterly or yearly retainer is not possible.
- **Work Orders on the project**: the material a Work Order uses already
  counts in Stock Used, but the project does not list its Work Orders and
  One has no manufacturing app. Matters to firms that make what they fit.
- **Price escalation** (rare): raising a contract's prices by an index.
  Workable today as a variation or an extra invoice line.
- **Revenue by progress** (rare): recognising revenue by percent complete
  (IFRS 15). ERPNext defers revenue by time only.

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
