# The demo company

**Sahara Glass & Aluminium** is a Dubai contractor that sells, designs,
fabricates, installs and maintains glazing. It is a whole year of a real
business in One, built on a new site in a few minutes, and the integration
suite reads it back as the people who work there.

## Build it

On a new site with every app One needs installed:

    bench --site <site> execute onedesk.one_demo.build.load --kwargs "{'password': '…'}"

The password is everybody's. The build runs in steps, in order. Each
step that finishes is remembered, so a run that stops starts again from the
step that stopped it. One step alone runs with `'only': 'crm'`.

Every record is made the way a click makes it, through the same code a
button runs: each form's own rules, the steps that turn one document into the
next, and One's own actions. Each is made by the person whose work it is.
Samir runs the projects, Huda keeps the books, Karim buys, Mariam runs HR,
Omar sells, and Layla owns the workspace. Every record is tagged **Demo**.

The steps run in the order of the five tables below.

### Demo steps: the company, its people, items, buying, leads and projects

| Step | What it makes |
|---|---|
| setup | The company through the setup wizard, in dirhams, the years before this one, rates for dollars, euros and pounds, and a euro rate from July so a late payment gains or loses |
| people | 18 people with their departments, managers and pay. Ten sign in, each given what People gives. The owner sets the company's Brand Colour, details and letter head |
| masters | 10 customers and 11 suppliers in four currencies, 26 items, prices, activity types (Site Work among them, so a day on site costs), asset categories. Sales in the UAE and bills from UAE suppliers carry 5% VAT, the rest none |
| stock | The stock the year opened with |
| buying | Requests, requests for quotation, supplier quotations, orders, receipts, bills, payments, a return, broken glass sent back with a debit note on its bill, euro orders, an order received and not billed |
| crm | Leads from every source in every status, deals at every stage in three currencies, calls, quotations won and lost, a lead turned customer, two leads from the Get in Touch form with nobody owning them, one maybe a lead we have |
| projects | Ten projects of every kind, with the 25-task template, contracts, progress billing, retention, advances, subcontracts, budgets, time, retainers, extra work |

### Demo steps: the workshop, quality, selling, service and the stores

| Step | What it makes |
|---|---|
| making | Tariq's three workstations and the steps on them, bills of materials, and work orders for stock, the villa and the tower, finished, half done and not started. Each step is a job card worked by Arun, Ravi or Joseph, and the villa's manager is told when its order is made. Rania asks the workshop for the villa's last doors, and the villa's profile goes to Gulf Powder Coating and comes back. The Inventory Check's two workshop fixes |
| quality | How a curtain wall is installed, the goal of installing it right the first time and last month's failed review of it, the corrective action Tariq owns, two bays sealed in the cold against the procedure, the monthly quality meeting, and Marina Hotels' feedback on their pool fence |
| selling | Orders delivered, invoiced and paid, a return with its credit note, a sale in pounds and one in dollars, an unpaid fee, an order delivered and not invoiced |
| service | Four issues from open to closed under a standard service level agreement, Marina Hotels' warranty claim on the pool fence and the breakdown visit that mended it, a year of quarterly glazing checks on Bayview with the first visit done, the sales line's hours and greeting, hardware cheaper by the box, and a panel made to Bayview's drawings sold to Bayview alone |
| moving | The villa's materials sent to its site on a transfer note and used there by Tariq, and a count of the stores that finds three hinges short, posted as a loss |
| lots | Weatherproof sealant in two lots with a twelve-month shelf life, the older one expiring within the month, part of it taken to the villa |

### Demo steps: ordering, assets and the books

| Step | What it makes |
|---|---|
| ordering | Rania's request for the villa's site priced by Al Noor and by Emirates Sealants on the portal, each line ordered from whoever is cheaper, Al Noor late with theirs, Al Noor's aluminium agreed for the year on a blanket order and the villa's profile ordered against it, the quotes that lost expired, the glass order Gulf Glass credited closed, and Gulf Glass and Al Noor scored each month |
| assets | Trucks, a CNC centre and laptops, with who holds them, depreciation and maintenance. Yousef and Tariq keep up the services the day after each falls due, and leave Pickup Truck 2's last one late. Karim buys Mariam a laptop on a receipt that registers it, and hands it to her. Pickup Truck 1's gearbox is mended on Emirates Fleet Motors' bill, Huda's laptop waits for a new screen, and Huda writes the CNC centre down by a tenth after a spindle crash. Sanjay, who drives Pickup Truck 1, resigns, and Mariam starts his leaving checklist, which asks the stores for the truck back |
| books | The bank account, opening balances, rent and utilities each month. A tax template brings its taxes (the Books Check) |
| ledger | Last year closed, the founders' shares issued, the dirham pegged to the dollar, Harbour Logistics both customer and supplier, Emirates NBD's cheque layout, foreign balances valued again, head office costs split sixty to forty from next year, and the corrections an accountant keeps to hand, made but not run. Left empty on purpose: an accounting dimension, which adds a field to every accounting form, and India's, Italy's and South Africa's own screens, which a UAE company never sees |

### Demo steps: HR and pay

| Step | What it makes |
|---|---|
| hr | Pay, three payroll runs, and three more for Imran, an installer paid by the hour from his timesheets, so Profit on Billed Hours has rows. Leave, attendance, check-ins, expense claims at every stage, two openings with applicants, an offer with its terms and an appointment letter. A glazier who resigned last month, paid his gratuity |
| career | The rest of a working life: a leave policy and block days, a holiday worked and given back, days encashed and adjusted, a shift schedule, Working at Height taught and graded, goals and feedback, a promotion and a transfer, travel with an advance, the van's log, a grievance looked into, a staffing plan, a requisition and a referral, a bonus, an incentive, a retention bonus, back pay, pay held, Joseph's exit interview and final statement, the clock's place, network and phone, a salary certificate and an overtime slip. Left empty on purpose: income tax and flexible benefits, which a UAE company does not run, and a payroll correction, since nobody took unpaid leave |

### Demo steps: the calendar, OneStudio, files, OneIntake and mail

| Step | What it makes |
|---|---|
| calendar | The weekly site meeting, a handover walk with the customer, a supplier visit, the workshop's safety briefing and a pricing review |
| announcements | Two announcements from the office, on everybody's top bar for sixty days: a holiday closure and expenses moving into One |
| studio | Company Van, a record type of the company's own in OneInventory, with two vans. An extension on the customer's form that is on and has run into an error, and one on the lead kept off |
| storage | A Projects library Samir runs with the site team in it, the villa's elevations there with a link for the customer and a second version, Samir's site visit notes shared with Rania, a request to Al Noor for its papers, and a drive password |
| workbook | A costing workbook in the company's files: the rates behind the Bayview tower quotation, and a second sheet for labour that the first one reads |
| document | The Bayview tower scope of works in the company's files, written as HTML so it also opens the way a document made outside the editor does |
| intake | The owner's own address and the accounts team's Bank Statements folder, both read by OneAI. The samples in tests/samples/intake arrive there, and Huda matches the statement's transport debit in the reconciliation tool |
| mail | The workspace's own address, which Layla holds, with a customer's request for a price, a supplier's delivery date and a hotel's maintenance call |

## Who works there, and signing in as them

Each person signs in with their address below and the password given to the
build. Sign in as somebody to see One as they do.

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
against the records themselves. It writes nothing. A failed check names the
records behind it.

### What the demo's checks prove

- The books balance and stock never went below nothing.
- Every party is billed in its own currency, and the base amounts agree.
- Every status there is for invoices, orders, quotations, deals, leads,
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
- The figures add up, as **The stories** below tell them. The VAT return is the
  invoices' and bills' tax, a late euro payment gains or loses, what is
  outstanding is what is left, the stock is what the books hold, prices carry
  from quote to invoice, payslips add up, leave comes off what is left, and a
  leaver's gratuity follows the UAE rule.
- Every notification file is on Settings › Notifications.
- Every paper that leaves the company prints with One's format, as the owner
  prints it, under the company's letter head and in its colour.

A new feature adds its records to the step it belongs to and a check here.

## The stories

What a business does with One, each story tied to the check that proves it
on Sahara Glass & Aluminium. A story is checked (✓) when a check reads its
figures back, not only when its records exist; · is later.

### OneBook

| | Story | Check |
|---|---|---|
| ✓ | Every entry in the books balances | `the_books_balance` |
| ✓ | What we are owed on the books' home is what the invoices still have outstanding | `the_books_home_tells_the_truth` |
| ✓ | Each party is billed in its own currency, and the dirham amounts agree | `every_party_is_billed_in_its_own_currency` |
| ✓ | A year ended is closed into Retained Earnings and locked, by the closers alone | `onebook_keeps_the_books_rules` |
| ✓ | A payment taken against an invoice in one step settles it | `onebook_home_and_payments_for_the_accounts_team` |
| ✓ | A sale in the UAE carries 5% VAT, a sale abroad none, and the VAT return's tax on sales is the invoices' tax less the credit notes' | `onebook_vat_is_charged_and_returned` |
| ✓ | A supplier's bill carries the VAT it was charged, and the return's tax on purchases is the bills' and claims' tax | `onebook_vat_is_charged_and_returned` |
| ✓ | A customer pays a euro invoice after the rate moved, and the difference is a gain or a loss in the books | `onebook_a_foreign_payment_gains_or_loses_at_its_rate` |
| ✓ | Broken glass goes back to its supplier, a debit note is made against the bill, and what we owe falls by it | `oneinventory_broken_glass_goes_back_and_the_bill_is_debited` |
| ✓ | What every invoice and bill still has outstanding is its total less what was paid and credited against it | `onebook_what_is_outstanding_is_what_is_left` |
| ✓ | The bank statement is matched to the payments it shows | `onebook_the_statement_is_matched_to_what_it_shows` |
| ✓ | Profit and loss shows each month's rent in that month | `onebook_profit_and_loss_shows_each_month_in_its_month` |
| ✓ | A late invoice ages into the right column of what is owed | `onebook_a_late_invoice_ages_into_its_column` |
| · | A bill from a supplier abroad is charged VAT by reverse charge, not zero | |

### OneInventory

| | Story | Check |
|---|---|---|
| ✓ | Stock never goes below nothing | `stock_never_goes_below_nothing` |
| ✓ | Assets lose value month by month, and each is with somebody | `the_assets_depreciate`, `oneinventory_assets_items_and_orders_for_the_stores` |
| ✓ | A reorder row becomes a purchase order | `oneinventory_assets_items_and_orders_for_the_stores` |
| ✓ | A supplier answers a request for quotation on the portal | `a_supplier_is_invited_to_the_portal_and_answers_a_quote_request` |
| ✓ | What the stock is worth in the books is what the warehouses hold | `oneinventory_the_stock_in_the_books_is_what_the_warehouses_hold` |
| ✓ | An order's price is what is received and billed, quantity for quantity | `oneinventory_what_was_ordered_is_received_and_billed_price_for_price` |
| ✓ | Orders reach every state a buyer meets, to receive, to bill, both and completed | `erpnext_statuses_are_all_there` |
| ✓ | Freight on imported hardware raises what the hardware cost | `oneinventory_goods_arrive_as_the_receipt_says` |
| ✓ | A finished work order's product is worth its materials and the workshop's time | `oneinventory_making_from_bill_to_finished_goods` |

### OneCRM and selling

| | Story | Check |
|---|---|---|
| ✓ | Leads reach every stage, deals every stage from New to Lost, in three currencies | `erpnext_statuses_are_all_there`, `onecrm_leads_and_deals_as_omar_works_them` |
| ✓ | A lead from the web form is taken, a duplicate cleared or merged | `onecrm_leads_and_deals_as_omar_works_them` |
| ✓ | A won quotation becomes an order, and the deal Won | `every_hand_off_left_its_records` |
| ✓ | What was quoted is what is ordered, delivered and invoiced, price for price | `onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price` |
| ✓ | A window sent back is credited at what it was sold for | `onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price` |
| ✓ | Orders reach every state a seller meets, to deliver, to bill, both and completed | `erpnext_statuses_are_all_there` |

### OneProject

| | Story | Check |
|---|---|---|
| ✓ | A project's ordered, invoiced and billed figures are its documents' sums | `a_projects_figures_are_its_documents` |
| ✓ | No hour and no retainer month is invoiced twice | `no_time_is_invoiced_twice`, `every_retainer_month_is_invoiced_once` |
| ✓ | Progress billing keeps the order's prices and sets advances off | `oneproject_money_reads_as_its_documents_and_its_people_are_told` |
| ✓ | Retention is held on both sides, dated, and released in one payment | `oneproject_a_new_retention_date_reaches_the_receivables`, `oneproject_retention_is_released_and_its_people_follow_the_work` |
| ✓ | Terms travel from quotation to order to invoice | `oneproject_its_terms_travel_from_quotation_to_invoice` |
| ✓ | Milestones bill at most the whole contract | `oneproject_its_overview_keeps_its_rules_and_tells_its_people` |
| ✓ | A day on site is a day on the project | `oneproject_a_day_on_site_and_the_projects_pictures` |
| ✓ | A cost type passing its budget is told | `oneproject_money_reads_as_its_documents_and_its_people_are_told` |
| ✓ | A project's invoices carry VAT like any other sale, retention included | `onebook_vat_is_charged_and_returned` |
| ✓ | Somebody paid from their timesheets, so Profit on Billed Hours has rows, each the invoice less his share of the month's pay | `oneproject_profit_on_billed_hours` |
| ✓ | A day on site costs what Site Work costs an hour | `oneproject_a_day_on_site_and_the_projects_pictures` |
| ✓ | Time Billed on an invoice in euros is its time lines to the cent | `oneproject_the_books_invoice_time_a_month_and_progress` |
| ✓ | The client sees the project's files on the portal, and its hours only when the team shows them | `oneproject_what_a_member_sees_on_the_portal` |
| ✓ | A site log, a subcontractor's timesheet and a request for extra work, mailed in, land on the project | `every_intake_sample_left_what_it_should` |

### OneTask

| | Story | Check |
|---|---|---|
| ✓ | My Tasks and the Inbox are the reader's own | `onetask_my_tasks_and_the_inbox_are_the_readers_own` |
| ✓ | A task is its people's, and ends as they say | `onetask_a_task_is_its_peoples_and_ends_as_they_say` |
| ✓ | Work from Intake and OneHR lands with the right person | `onetask_takes_work_from_intake_and_onehr` |
| ✓ | Timers start, pause, resume and stop | `onetask_works_for_whoever_has_tasks` |

### OneHR

| | Story | Check |
|---|---|---|
| ✓ | Leave, shift and attendance requests are answered by who answers them | `onehr_requests_are_answered_by_who_answers_them` |
| ✓ | Overtime is written, capped and collected for the slip | `onehr_the_crews_days_overtime_and_pay_add_up` |
| ✓ | A payroll posts to the books | `every_hand_off_left_its_records` |
| ✓ | Clocking in needs the person's phone and a known network | `onehr_tariq_clocks_in_with_his_phone` |
| ✓ | An interview is recorded, an applicant ranked | `onehr_an_interview_is_recorded_and_its_people_read_again` |
| · | OneHR asks which pay counts towards gratuity, so the UAE rules work without a hand in the desk | |
| ✓ | Each payslip's net pay is its earnings less its deductions, and the payroll posts their sum | `onehr_each_payslip_adds_up_and_the_payroll_posts_it` |
| ✓ | Leave taken comes off what is left | `onehr_leave_taken_comes_off_what_is_left` |
| ✓ | A worker who leaves after years is owed gratuity by the UAE rule, and it is paid | `onehr_a_leaver_is_paid_their_end_of_service` |
| ✓ | An expense claim paid is what the books and the project carry | `onehr_an_expense_claim_paid_is_what_the_books_and_project_carry` |

### The workspace

| | Story | Check |
|---|---|---|
| ✓ | Everybody signs in to what they were given, only the owner administers | `everybody_signs_in_to_what_they_were_given` |
| ✓ | Every rail link and report opens for its people, and no further | `every_rail_link_opens_for_its_app`, `every_report_of_ones_runs` |
| ✓ | Rules hold under bulk edit, report edit and Data Import | `a_project_with_open_work_is_not_closed_by_hand`, `an_internal_project_bills_nobody`, `the_books_lock_up_to_today_at_most`, `nobody_is_turned_on_past_the_seats` |
| ✓ | Every paper prints in the company's look | `every_paper_prints_in_the_companys_look` |
| ✓ | Privacy requests, the bin, webhooks and the audit log are the administrators' | `privacy_*`, `the_bin_*`, `webhooks_and_the_audit_log_are_the_administrators` |

Mail, files, Intake, the calendar, OneStudio and OneAI each have their checks
(`onemail_*`, `onecloud_*`, `oneintake_*`, `onecalendar_*`, `onestudio_*`,
`oneai_*`). Their stories are about people and permissions more than figures,
and are left as the checks say them.

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
