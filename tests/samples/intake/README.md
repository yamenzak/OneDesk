# Intake samples

Real mail and files that arrive at the demo company, Sahara Glass &
Aluminium, one folder per app whose records they make. The demo suite
(`onedesk/one_demo/check.py`, `every_intake_sample_makes_what_it_should`) has
Intake handle each one and checks what it made. Nothing is kept.

A sample is two files with the same name:

- the document itself: a mail as it arrives (`.eml`, with its attachments), or
  a file dropped in the accounts team's Bank Statements folder;
- a `.json` saying what Intake makes of it, and what a model answered about
  it.

```json
{
  "file": "enquiry.eml",
  "answers": {
    "intake_look": {"verdict": "Action", "why": "...", "about": []},
    "intake_read": {"kind": "Inquiry", "...": "..."},
    "intake_audit": "right"
  },
  "makes": [
    {"doctype": "Lead", "values": {"company_name": "Creek View Residences LLC"}},
    {"doctype": "Task"}
  ]
}
```

- `answers` holds each model call Intake makes about the document, by its
  action, in the shape the action asks for. `"right"` for the auditor
  approves every action it is shown, and `"first"` for placing puts the
  document with the first open matter it is shown (an attachment with its
  mail). A call with no answer fails the sample, even where Intake carries on
  without it, so a sample always says everything Intake asked.
- `makes` lists what must be done: a `doctype`, its `kind` (`Create`
  unless said) and `level` (`Done` unless said, or `Proposed` for what waits
  for a person), and `values` the record must hold.

A document that is already data (an e-invoice, a bank statement, a contact
card, an invitation) needs no answers to be read.

A guard fails when Intake can make a record and no sample
makes it (`tests/guards/test_intake_samples.py`).
