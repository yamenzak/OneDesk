# The demo company

**Sahara Glass & Aluminium** is a Dubai contractor that sells, designs,
fabricates, installs and maintains glazing. It is a whole year of a real
business in One, built on a new site in a few minutes, and the integration
suite reads it back as the people who work there.

## Build it

On a new site with erpnext, hrms and onedesk installed:

    bench --site <site> execute onedesk.one_demo.build.load --kwargs "{'password': '…'}"

The password is everybody's. The build runs in steps, in order. Each
step that finishes is remembered, so a run that stops starts again from the
step that stopped it. One step alone runs with `'only': 'crm'`.

| Step | What it makes |
|---|---|
| setup | The company through the setup wizard, in dirhams, the years before this one, rates for dollars, euros and pounds |
| people | 18 people with their departments, managers and pay. Ten sign in, each given what People gives. The owner sets the company's Brand Colour, details and letter head |
| masters | 10 customers and 9 suppliers in four currencies, 23 items, prices, activity types, asset categories |
| stock | The stock the year opened with |
| buying | Requests, requests for quotation, supplier quotations, orders, receipts, bills, payments, a return, euro orders |
| making | Bills of materials and work orders, finished, half done, started and not yet started |
| crm | Leads from every source in every status, deals at every stage in three currencies, calls, quotations won and lost, a lead turned customer, two leads from the Get in Touch form with nobody owning them, one maybe a lead we have |
| projects | Ten projects of every kind, with the 25-task template, contracts, progress billing, retention, advances, subcontracts, budgets, time, retainers, extra work |
| selling | Orders delivered, invoiced and paid, a return with its credit note, a sale in pounds and one in dollars, an unpaid fee |
| assets | Trucks, a CNC centre and laptops, with who holds them, depreciation and maintenance |
| books | The bank account, opening balances, rent and utilities each month. A tax template brings its taxes (the Books Check) |
| hr | Pay, three payroll runs, leave, attendance, check-ins, expense claims at every stage, two openings with applicants, an offer with its terms and an appointment letter |
| calendar | The weekly site meeting, a handover walk with the customer, a supplier visit, the workshop's safety briefing and a pricing review |
| studio | Company Van, a record type of the company's own in OneInventory, with two vans. An extension on the customer's form that is on and has run into an error, and one on the lead kept off |
| storage | A Projects library Samir runs with the site team in it, the villa's elevations there with a link for the customer and a second version, Samir's site visit notes shared with Rania, a request to Al Noor for its papers, and a drive password |
| intake | The owner's own address and the accounts team's Bank Statements folder, both read by OneAI. The samples in tests/samples/intake arrive there |
| mail | The workspace's own address, which Layla holds, with a customer's request for a price, a supplier's delivery date and a hotel's maintenance call |

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
- Every rule of One's holds when a record is changed by a bulk edit, a
  report view cell or a Data Import row, as the person who would change it.
  A project with open work is not closed, an internal project bills nobody,
  the books lock up to today at most, and nobody is turned on past the seats.
- Every notification file is on Settings › Notifications.
- Every paper that leaves the company prints with One's format, as the owner
  prints it, under the company's letter head and in its colour.

A failed check names the records behind it. A new feature adds its records
to the step it belongs to and a check here.

## Connections

The demo is where each module's hand-offs run end to end. A deal's quotation
becomes a project's contract. The project's time and progress become
OneBook's invoices. Its purchases come from OneInventory's suppliers, and its
crew's time and claims come from OneHR.

## Under the hood

### build.py

Each step makes its records the way a person's click makes them: frappe's
controllers, ERPNext's mappers and One's own actions, never rows written
straight into tables, so what the demo shows is what a workspace would. A
step that has run is remembered and not run twice; a step that fails stops
the build with what it tripped on, and the next run starts from it.

### check.py

Each check opens what a person would open, as that person, and holds what it
shows against ERPNext's own records: the books balance, stock never went
below nothing, every party is billed in its own currency, every project page
opens for its team and its figures are the documents behind them, every
report of One's runs, and every rail link opens for the app's people.
`check.run` prints a line a check and the count that failed. Nothing is
written: each check is rolled back.

### projects.py

- **Fixed Price**, ordered: the Mansour villa, built from the Aluminium &
  Glazing template, with a bill of quantities billed in progress, retention,
  a subcontract billed the same way, cost types, stock issued, time, extra
  work ordered as a sub-project, and milestones billed on completion.
- **Fixed Price**, large and in parts: the Bayview tower, with sub-projects
  of its own, an advance from the customer and a late invoice.
- **Fixed Price**, quoted and not ordered, in US dollars: Acme's lobby.
- **Fixed Price**, finished and paid: Aisha Rahman's balcony. And one
  cancelled before work started: Palm Interiors.
- **Time and Materials** in euros, billed with Invoice Time and a markup on
  what was bought for it: Nordlicht's showroom; and a small one just started.
- **Retainer**, two of them, billed month by month with Invoice Month, one
  with hours over its allowance.
- **Internal**, with a budget and no customer: the CNC upgrade.

### samples.py

Each sample is a real mail or file, the answers a model gave about it, and
what Intake must make of it (the folder's README says how one is written). A
mail arrives at the owner's address through OneMail's own Arrival, a file in
the accounts team's Bank Statements folder (`intake.py`), and Intake reads,
understands and acts on it as it would, with each model call answered from
the sample.
