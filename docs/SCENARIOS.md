# Business scenarios

What a business does with One, as stories, each tied to the demo check that
proves it on Sahara Glass & Aluminium (`onedesk/one_demo`). A story is
**checked** when a check reads its figures back, not only when its records
exist.

Written 2026-10-10 after asking whether the demo covers the business. It
mostly proved that records exist and connect. These stories ask whether the
numbers come out right.

| Mark | Meaning |
|---|---|
| ✓ | Checked, by the check named |
| · | Later |

## OneBook

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
| · | The bank statement is matched to the payments it shows | |
| · | Profit and loss shows each month's rent and wages in that month | |
| · | A late invoice ages into the right column of what is owed | |
| · | A bill from a supplier abroad is charged VAT by reverse charge, not zero | |

## OneInventory

| | Story | Check |
|---|---|---|
| ✓ | Stock never goes below nothing | `stock_never_goes_below_nothing` |
| ✓ | Assets lose value month by month, and each is with somebody | `the_assets_depreciate`, `oneinventory_assets_items_and_orders_for_the_stores` |
| ✓ | A reorder row becomes a purchase order | `oneinventory_assets_items_and_orders_for_the_stores` |
| ✓ | A supplier answers a request for quotation on the portal | `a_supplier_is_invited_to_the_portal_and_answers_a_quote_request` |
| ✓ | What the stock is worth in the books is what the warehouses hold | `oneinventory_the_stock_in_the_books_is_what_the_warehouses_hold` |
| ✓ | An order's price is what is received and billed, quantity for quantity | `oneinventory_what_was_ordered_is_received_and_billed_price_for_price` |
| ✓ | Orders reach every state a buyer meets, to receive, to bill, both and completed | `erpnext_statuses_are_all_there` |
| · | Freight on imported hardware raises what the hardware cost | |
| · | A finished work order's product is worth its materials and the workshop's time | |

## OneCRM and selling

| | Story | Check |
|---|---|---|
| ✓ | Leads reach every stage, deals every stage from New to Lost, in three currencies | `erpnext_statuses_are_all_there`, `onecrm_leads_and_deals_as_omar_works_them` |
| ✓ | A lead from the web form is taken, a duplicate cleared or merged | `onecrm_leads_and_deals_as_omar_works_them` |
| ✓ | A won quotation becomes an order, and the deal Won | `every_hand_off_left_its_records` |
| ✓ | What was quoted is what is ordered, delivered and invoiced, price for price | `onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price` |
| ✓ | A window sent back is credited at what it was sold for | `onecrm_what_was_quoted_is_ordered_delivered_and_invoiced_price_for_price` |
| ✓ | Orders reach every state a seller meets, to deliver, to bill, both and completed | `erpnext_statuses_are_all_there` |

## OneProject

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
| · | Somebody paid from their timesheets, so Profit on Billed Hours has rows | |

## OneTask

| | Story | Check |
|---|---|---|
| ✓ | My Tasks and the Inbox are the reader's own | `onetask_my_tasks_and_the_inbox_are_the_readers_own` |
| ✓ | A task is its people's, and ends as they say | `onetask_a_task_is_its_peoples_and_ends_as_they_say` |
| ✓ | Work from Intake and OneHR lands with the right person | `onetask_takes_work_from_intake_and_onehr` |
| ✓ | Timers start, pause, resume and stop | `onetask_works_for_whoever_has_tasks` |

## OneHR

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

## The workspace

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

## Found while writing this

- No invoice and no bill in the demo carried VAT. The UAE templates were
  there, none was the default, so the VAT return read nothing.
- Every foreign payment was taken at the invoice's own rate, so no gain or
  loss ever reached the books.
- Nobody had left the company, so gratuity was never worked out.
- Glass went back to its supplier on the receipt, and the bill was never
  debited.
- ERPNext's default tax template only reaches an invoice made in its form.
  Invoice Time, Bill Progress, OneAI, Intake and imports made invoices with no
  VAT. The Books Check now makes a Tax Rule with the template it sets.
- HRMS's UAE gratuity rules ship with no pay that counts towards them, so
  every gratuity stopped with an error. The demo names Basic Salary. OneHR
  should ask (above, later).
- Suppliers abroad are zero-rated in the demo. UAE law charges VAT on them
  by reverse charge, which ERPNext does not do by itself (above, later).
- HRMS lets nobody submit a Gratuity, and the accounts team could not open
  one to pay it. End of Service is now in OneHR's rail, HR may submit it and
  accounts read it.
- A backdated invoice in another currency took today's rate. The demo now
  prices it at its own day's rate, as ERPNext's form does when the date
  changes.
- Draw Up Contract on an extra-work sub-project stopped, since it read only
  the sub-project's own terms. It takes them from the job it is part of now.
- A customer's contact listed on a project stood for the project too, so
  Intake could not tell whose payment advice it read and made no payment.
  A contact now stands for its parties, not the projects it speaks on.
- A sub-project started with terms of its own, so it no longer billed on the
  job it is part of. It starts with none now.
- Intake's task about a bill for the villa never went in the villa's project.
  The task pass now looks the project up too.
