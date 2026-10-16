---
name: Invoice Overdue
app: OneBook
roles: Accounts User, Accounts Manager, Sales User, Sales Manager
about: On the morning after one of your invoices goes past its due date unpaid.
to: Whoever made the invoice and the customer's account manager
email_default: yes
push_default: yes
---

# {invoice} for {customer} is overdue

{outstanding} is still owed. It was due on {date}. Send a reminder, or record
the payment if it has come in.
