# OneProject scratchpad

What is known to be wrong and what is planned, kept short.

- **Help pictures.** The pages are words only; the project page, its
  Overview for each kind and Bill Progress want a picture each.
- **Help is long.** A Project's Page and Billing the Customer are the README's
  sections as they were; each could be split by kind of project.

## Demo checks failing (5 Nov 2026, before the template moved)

- oneproject_its_invoices_suppliers_team_and_activity_read_true (checks.py:637)
- oneproject_oneai_reminds_adds_and_the_rules_stand (checks.py:680)
- oneproject_a_manager_sees_every_project_and_a_member_sees_their_own (checks.py:1301)

## Since the page went (6 Nov 2026)

- **Main only.** The page could show a parent's own work alone (All Work /
  Main). The form shows the whole tree; the server still takes `only`, and
  OneAI's `_main` uses it. Bring it back as a filter on the parts if asked.
- **Tasks.** The Tasks tab is ERPNext's own list. The page's own (grouped by
  milestone, a task panel beside it) is gone; Board and Schedule are frappe's
  views. If grouping by part of the job is missed, it is a part to add.
- **Help pictures** are still words only.
