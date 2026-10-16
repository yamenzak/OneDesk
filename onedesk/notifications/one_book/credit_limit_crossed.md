---
name: Credit Limit Crossed
app: OneBook
roles: Accounts Manager, Accounts User
about: When somebody flags a customer who is over their credit limit.
to: Accounts
email_default: yes
push_default: yes
---

# {customer} is over their credit limit

{by} was stopped from going ahead with a sale to them. They owe {outstanding}
against a limit of {limit}. Raise the limit on the customer, or get paid
first.
