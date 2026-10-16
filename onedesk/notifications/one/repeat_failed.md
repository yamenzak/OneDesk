---
name: Repeat Failed
app: One
roles: Accounts User, Accounts Manager, Projects User, Sales User, Purchase User
about: When a repeating invoice, bill, order or task stops because the next one could not be made.
to: Whoever set up the repeat, and accounts for an invoice, bill, order or entry
email_default: yes
push_default: yes
---

# The repeat of {document} stopped

The next {kind} could not be made, so the repeat is switched off. Fix what
stopped it, then switch the repeat back on.
