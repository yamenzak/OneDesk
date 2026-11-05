# OneFactory scratchpad

What is known to be wrong and what is planned, kept short.

- **A Home.** OneFactory opens on ERPNext's Manufacturing dashboard. A Home
  of its own would say what needs somebody: work orders past their date
  (OneInventory's Home said it until the split), steps waiting on
  materials, work out with suppliers and late back.
- **Work Order Late.** Nobody is told when a work order passes its date;
  only Work Order Done is a notification.
- The pass of November 2026 walks OneFactory after OneInventory; where that
  stands is in one_inventory/SCRATCHPAD.md.
- **A work order listed twice.** The Shop Floor's Open tab shows
  MFG-WO-2026-00006 on two rows (seen 5 November 2026); find whether
  ERPNext's `get_work_orders` or `floor.read` repeats it.
- **Setup.** Inventory Check still sets the workshop's cost account and the
  work order warehouses; they belong in OneFactory's own setup steps.
