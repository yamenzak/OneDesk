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
| setup | The company through the setup wizard, in dirhams, the years before this one, rates for dollars, euros and pounds, and a euro rate from July so a late payment gains or loses |
| people | 18 people with their departments, managers and pay. Ten sign in, each given what People gives. The owner sets the company's Brand Colour, details and letter head |
| masters | 10 customers and 11 suppliers in four currencies, 26 items, prices, activity types (Site Work among them, so a day on site costs), asset categories. Sales in the UAE and bills from UAE suppliers carry 5% VAT, the rest none |
| stock | The stock the year opened with |
| buying | Requests, requests for quotation, supplier quotations, orders, receipts, bills, payments, a return, broken glass sent back with a debit note on its bill, euro orders, an order received and not billed |
| crm | Leads from every source in every status, deals at every stage in three currencies, calls, quotations won and lost, a lead turned customer, two leads from the Get in Touch form with nobody owning them, one maybe a lead we have |
| projects | Ten projects of every kind, with the 25-task template, contracts, progress billing, retention, advances, subcontracts, budgets, time, retainers, extra work |
| making | Tariq's three workstations and the steps on them, bills of materials, and work orders for stock, the villa and the tower, finished, half done and not started. Each step is a job card worked by Arun, Ravi or Joseph, and the villa's manager is told when its order is made. Rania asks the workshop for the villa's last doors, and the villa's profile goes to Gulf Powder Coating and comes back. The Inventory Check's two workshop fixes |
| selling | Orders delivered, invoiced and paid, a return with its credit note, a sale in pounds and one in dollars, an unpaid fee, an order delivered and not invoiced |
| moving | The villa's materials sent to its site on a transfer note and used there by Tariq, and a count of the stores that finds three hinges short, posted as a loss |
| lots | Weatherproof sealant in two lots with a twelve-month shelf life, the older one expiring within the month, part of it taken to the villa |
| ordering | Rania's request for the villa's site priced by Al Noor and by Emirates Sealants on the portal, each line ordered from whoever is cheaper, Al Noor late with theirs, Al Noor's aluminium agreed for the year on a blanket order and the villa's profile ordered against it, the quotes that lost expired, the glass order Gulf Glass credited closed, and Gulf Glass and Al Noor scored each month |
| assets | Trucks, a CNC centre and laptops, with who holds them, depreciation and maintenance. Yousef and Tariq keep up the services the day after each falls due, and leave Pickup Truck 2's last one late. Karim buys Mariam a laptop on a receipt that registers it, and hands it to her. Pickup Truck 1's gearbox is mended on Emirates Fleet Motors' bill, Huda's laptop waits for a new screen, and Huda writes the CNC centre down by a tenth after a spindle crash. Sanjay, who drives Pickup Truck 1, resigns, and Mariam starts his leaving checklist, which asks the stores for the truck back |
| books | The bank account, opening balances, rent and utilities each month. A tax template brings its taxes (the Books Check) |
| hr | Pay, three payroll runs, and three more for Imran, an installer paid by the hour from his timesheets, so Profit on Billed Hours has rows. Leave, attendance, check-ins, expense claims at every stage, two openings with applicants, an offer with its terms and an appointment letter. A glazier who resigned last month, paid his gratuity |
| career | The rest of a working life: a leave policy and block days, a holiday worked and given back, days encashed and adjusted, a shift schedule, Working at Height taught and graded, goals and feedback, a promotion and a transfer, travel with an advance, the van's log, a grievance looked into, a staffing plan, a requisition and a referral, a bonus, an incentive, a retention bonus, back pay, pay held, Joseph's exit interview and final statement, the clock's place, network and phone, a salary certificate and an overtime slip. Left empty on purpose: income tax and flexible benefits, which a UAE company does not run, and a payroll correction, since nobody took unpaid leave |
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
| Khalid Mansour | khalid@mansour.example | The portal, as the villa's customer, invited by Omar. On the villa's team, he sees its files there and not its timesheets |

## Check it

    bench --site <site> execute onedesk.one_demo.check.run

The whole run takes a while, so a change runs only the checks that cover it:
one by its name, or a group by a prefix ending in `_`, such as a module's.

    bench --site <site> execute onedesk.one_demo.check.run --kwargs "{'only': 'oneproject_'}"

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
- The figures add up, as docs/SCENARIOS.md tells them. The VAT return is the
  invoices' and bills' tax, a late euro payment gains or loses, what is
  outstanding is what is left, the stock is what the books hold, prices carry
  from quote to invoice, payslips add up, leave comes off what is left, and a
  leaver's gratuity follows the UAE rule.
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
  of its own, an advance from the customer and a late invoice. It counts its
  time by attendance on its site: Bilal and Imran clock in there, and each of
  their days is a day on the tower (hr.py).
- **Fixed Price**, quoted and not ordered, in US dollars: Acme's lobby. Its
  quote is the revised one Omar's deal is waiting to send, on the deal and
  the project both.
- **Fixed Price**, finished and paid: Aisha Rahman's balcony. And one
  cancelled before work started: Palm Interiors.
- **Time and Materials** in euros, billed with Invoice Time and a markup on
  what was bought for it: Nordlicht's showroom; and a small one just started.
- **Retainer**, two of them, billed month by month with Invoice Month, one
  with hours over its allowance.
- **Internal**, with a budget and no customer: the CNC upgrade.

### history.py

A record made today for a date in spring would say it was made today, so the
Activity view and every timeline would put a year of work in one afternoon.
Once the steps are built, `history.settle` moves each document, its rows and
its versions back to its own date, keeping the time of day. A moment One
stamps as a record is saved (an expense claim's Decided On) is never later
than the record's last change. Run again, it moves nothing.

### samples.py

Each sample is a real mail or file, the answers a model gave about it, and
what Intake must make of it (the folder's README says how one is written). A
mail arrives at the owner's address through OneMail's own Arrival, a file in
the accounts team's Bank Statements folder (`intake.py`), and Intake reads,
understands and acts on it as it would, with each model call answered from
the sample.
