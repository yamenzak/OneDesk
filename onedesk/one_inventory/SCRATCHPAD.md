# OneInventory scratchpad

What is known to be wrong and what is planned, kept short.

## Pages to hand back to frappe

Each of these stands in for a doctype's own form or list. One at a time, as
OneTask's page and My Tasks were (one_task/heads.py, one_task/board.py): a
head and verbs on the form, a list, report or Kanban for the collection, and
only the one thing frappe lacks kept as ours.

- **Item** (page item_view, `src/inventory/item`): the form with a head.
  First, as it is the same job Task was.
- **Lots** (`lots`, Batch and Serial No): two lists.
- **Sent Out** (`sent_out`, Subcontracting Order): the list.
- **Quotes** (`quotes`, Request for Quotation and Supplier Quotation): the
  lists; ERPNext's Supplier Quotation Comparison report for the side by side.
- **Upkeep** (`upkeep`, Asset Maintenance Log and Asset Repair): the lists.
- **Shop Floor** (`floor`, Work Order and Job Card): the lists or a Kanban.
- **Plant Floor** (`plant`, Plant Floor and Workstation): ERPNext's own
  Plant Floor form.
- **Supplier Items** (`supplier_items`, on a supplier): a head on Supplier.
- **Stock on Hand** (`stock`, Bin) and **To Order** (`to_order`, Material
  Request and low stock): last, as they do the most frappe's screens do not.
