# OneHR scratchpad

What is known to be wrong and what is planned, kept short.

## The pass of 7 November 2026

Closed: every point of the passthrough but a fresh site, which waits for the
temporary site after the last module.

- **The demo stops living the day it is built.** Check-ins end then, and the
  daily job marks everybody absent from the next working day: on 7 November
  the attendance list is 61 Absent. A demo that keeps checking its people in
  each working day (a dev-only daily step) would keep Home and Attendance
  true for a showing.
- **Managers of other apps and Employee.** everybody.py lifts the Employee
  User Permission from anybody holding any app's manager role; OneHR's own
  personal records are narrowed by everybody.personal_query instead. Other
  apps' records naming an employee are not narrowed by this.
- Speed on a phone at 4x CPU (mariam): Home 3.9s, employees 6.2s, an
  employee 8.1s, leave list 7.8s, a leave 6.0s, a claim 4.8s, attendance 7.8s.
- HRMS's leave types ("Privilege Leave") are records, and read in English in
  Arabic and German, as the workspace named them.
- Payroll for Riyadh is not in the demo: it needs its salary components'
  accounts for the Saudi company.
- **Tax & Benefits** (exemption declarations and proofs, other income,
  benefit applications and claims) has no demo record, and a UAE or Saudi
  company pays no income tax: whether the rail shows it there is Yamen's
  call.
- frappe's Geolocation field throws in Leaflet ("reading 'x'") when it adds
  a circle to a map with no size yet; the map then draws. One console error
  on a Clock Place.
- A Report Builder report (Employee Information) says **Not Saved** as it
  opens with several companies: list.js adds the company filter to every
  list view, a saved report's too (one_interface).
- Income Tax Computation opens on "No employees found with selected filters
  and active salary structure": it waits on the Tax & Benefits question.
- Leaving a OneHR page whose chart is still drawing throws "removeChild ... not
  a child of this node" from frappe-charts' makeChartArea: its delayed update
  runs after the container was emptied (seen by tests/browser/routes.mjs,
  8 Nov 2026).
