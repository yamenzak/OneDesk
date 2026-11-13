# OneStudio: scratchpad

Known issues and plans, kept short. Something done leaves it.

## Not built

- **An extension behind an API call**, and **a table inside a custom
  collection**. AI-written endpoints and SQL are not going to be built.
- **Still to take from frappe's Flow and Studio** (the rest went in on
  2026-11-03): a card for any submit, cancel or approval step a record
  offers (Flow's `_doc_actions`); a thumbs-down on an answer, kept as
  memory; and a page extension that draws a small block of frappe-ui parts
  rather than a note or a button (Studio's blocks).
- **Custom apps**: a workspace's own app in the dock, with its own icon, rail
  and Home, holding its custom collections (a Fleet app for vans, drivers and
  trips). Needs its own roles, a place in People and in the switcher. Today a
  collection sits in a group of one of One's apps.
- **Hiding a record tab** (Files, Mail, Activity) on one form, as a Record
  Head row. Tabs are declared by modules only (`one/tabs.py`).
- **Server scripts on every workspace**: `server_script_enabled` per bench
  group. Opening a code-execution surface is Yamen's call.
- **Pictures in Help.** No page has one yet; Extensions, Custom Collections,
  Printing and Approvals would each earn one, taken on the demo.

## Known issues

- **Server extensions on dev.** The demo check
  `onestudio_tells_the_others_and_oneai_remembers_once` needs
  `server_script_enabled` on one.4dl.dev, which is Yamen's to switch.
- **Numbering refuses manual names** for the dozen kinds `one_makes_records`
  declares. Taking them off changes Numbering for those kinds.
- **Webhooks live in One's folder** (`one/webhooks.py`, in `ready.SHARED`),
  on their way into this one.
