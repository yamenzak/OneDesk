# The demo company

**Sahara Glass & Aluminium** is a Dubai contractor that sells, designs,
fabricates, installs and maintains glazing. It is a whole year of a real
business in One, built on a new site in a few minutes, and the integration
suite reads it back as the people who work there.

## Build it

On a new site with erpnext, hrms and onedesk installed:

    bench --site <site> execute onedesk.one_demo.build.load --kwargs "{'password': '…'}"

The password is everybody's. The build runs in twelve steps, in order. Each
step that finishes is remembered, so a run that stops starts again from the
step that stopped it. One step alone runs with `'only': 'crm'`.

| Step | What it makes |
|---|---|
| setup | The company through the setup wizard, in dirhams, the years before this one, rates for dollars, euros and pounds |
| people | 18 people with their departments, managers and pay. Ten sign in, each given what People gives |
| masters | 10 customers and 9 suppliers in four currencies, 23 items, prices, activity types, asset categories |
| stock | The stock the year opened with |
| buying | Requests, requests for quotation, supplier quotations, orders, receipts, bills, payments, a return, euro orders |
| making | Bills of materials and work orders, finished, half done, started and not yet started |
| crm | Leads from every source in every status, deals at every stage in three currencies, calls, quotations won and lost, a lead turned customer |
| projects | Ten projects of every kind, with the 25-task template, contracts, progress billing, retention, advances, subcontracts, budgets, time, retainers, extra work |
| selling | Orders delivered, invoiced and paid, a return with its credit note, a sale in pounds and one in dollars, an unpaid fee |
| assets | Trucks, a CNC centre and laptops, with who holds them, depreciation and maintenance |
| books | The bank account, opening balances, rent and utilities each month |
| hr | Pay, three payroll runs, leave, attendance, check-ins, expense claims at every stage, two openings with applicants and an offer |

Every record is made the way a click makes it, through frappe's controllers,
ERPNext's mappers and One's own actions, and by the person whose work it is.
Samir runs the projects, Huda keeps the books, Karim buys, Mariam runs HR,
Omar sells, and Layla owns the workspace. Every record is tagged **Demo**.

## Who works there

| Person | Sign in | Uses |
|---|---|---|
| Layla Haddad | wsadmin@one.test | Everything, and runs the workspace |
| Samir Aoun | samir@one.test | OneProject, some of OneCRM and OneInventory |
| Omar Farouk | omar@one.test | OneCRM |
| Huda Nasser | huda@one.test | OneBook |
| Karim Mansour | karim@one.test | OneInventory |
| Mariam Saleh | mariam@one.test | OneHR |
| Rania, Nadia, Tariq | rania@, nadia@, tariq@one.test | OneProject |
| Yousef Bakr | yousef@one.test | OneInventory |

## Check it

    bench --site <site> execute onedesk.one_demo.check.run

Each check opens what a person would open, as that person, and holds it
against ERPNext's own records. It writes nothing.

- The books balance and stock never went below nothing.
- Every party is billed in its own currency, and the base amounts agree.
- Every status ERPNext has for invoices, orders, quotations, deals, leads,
  projects, work orders and expense claims is there.
- Every project page opens for its owner, its manager, the books and its
  team, and stays closed to people with no part in it.
- A project's ordered, invoiced and billed figures are the documents behind
  them.
- No hour and no retainer month is invoiced twice.
- Every report of One's runs, and every home figure reads, for its people.
- Every rail link opens for the people its app is given to.

A failed check names the records behind it. A new feature adds its records
to the step it belongs to and a check here.

## Connections

The demo is where each module's hand-offs run end to end. A deal's quotation
becomes a project's contract. The project's time and progress become
OneBook's invoices. Its purchases come from OneInventory's suppliers, and its
crew's time and claims come from OneHR.
