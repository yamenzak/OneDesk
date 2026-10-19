# What each old record becomes

In the order the importer runs (`rua/importer/__init__.py`, `STEPS`).

| Old | Becomes | Step |
|---|---|---|
| Party, Client | Customer, with its TRN when it is fifteen digits, and a Contact when it had a phone or an email | `parties` |
| Party, Supplier (four kinds) | Supplier, the kind as its Supplier Group | `parties` |
| Party, Consultant | A Project Contact (Consultant) on each project that names it | `projects` |
| Party no record names | Nothing | `parties` |
| Project, Tender | Opportunity for its client | `projects` |
| Project, any other | Project under its parent, numbered by One, the old name as its title; its suppliers and consultants as Project Contacts | `projects` |
| Sub-project "Original Contract" or "Original Scope" | Nothing of its own: it is the main project's own work, which One shows as the main project's Main view; its contract and records go to the main project | `projects` |
| Project's contract value | A submitted Sales Order with VAT in the price, so its total is the contract. A main project whose value is the total of its sub-projects' gets no order of its own, so no work is ordered twice | `projects` |
| Quotation | Quotation, each line under the product its words name, its mark as the line's name, its size in millimetres; the written sections as its terms | `quotations` |
| LPO | Purchase Order, submitted unless it was a draft; items made from the line names | `buying` |
| LPO, Final | And a submitted Purchase Invoice from it, on its date | `buying` |
| Purchase Receipt, Received | Purchase Receipt against its order | `buying` |
| RFQ with lines | Request for Quotation | `buying` |
| Invoice, Tax, Final | Submitted Sales Invoice against the contract, keeping its number and its claim number | `sales` |
| Invoice, Tax, not final | Draft Sales Invoice, listed | `sales` |
| Invoice, Proforma | Payment Request on the contract | `sales` |
| Payment, Receive | Payment Entry into its bank, allocated or matched (see the README) | `payments` |
| Payment entered twice | Nothing: the copy on another part of the same job, found by its bank reference or by its amount and day, is left out and listed | `payments` |
| Payment, Pay | Payment Entry against the LPO's bill, or its order | `payments` |
| Payment, Petty Cash | Purchase Invoice paid from petty cash, on its project | `payments` |
| Bank (free text) | One bank ledger and Bank Account per bank, the spellings folded; a blank one to Bank Not Recorded | `payments` |
| Employee | Employee under its branch and designation; a Salary Structure Assignment from this month | `people` |
| Leave | Approved Leave Application, Annual Leave, allocated to cover it | `people` |
| Document, an employee's | Employee Document row with One's type, its scan attached | `people`, `files` |
| Document, the company's | A file on the company | `files` |
| Document, a project's | A file on the project | `files` |
| Letter, Final | Employee Letter on the employee it was for | `people` |
| Letter, draft or template | Nothing | `people` |
| Attendance (a JSON a day) | One Attendance per person per day: Present (late when marked), Absent or On Leave | `attendance` |
| File | A private file on what its record became; logos and photos public | `files` |
| Chat, Issue, Todo, Payslip, Inventory, Company, App Update | Nothing | |

Whether a client still holds retention from invoices made outside the old
app becomes a Retention Check on each project that billed or was paid,
answered from the project's Overview (`settle`).

Numbers carry on: each record type offers Rua's old series first and the
counters start after the highest number brought over (`numbers`).

## The checks

`check` puts the old app's figure beside One's for each of these, and a
difference that is meant to be there says why:

- counts: projects, tenders, contracts, quotations, employees, leave;
- money: contract value, invoiced with and without VAT, VAT, received,
  retention held and in Retention Receivable, bills from final LPOs, paid to
  suppliers, petty cash;
- the books: debits equal credits; what clients owe, what suppliers are
  owed, what is in the banks and what petty cash spent, each as the old
  app's totals say it should be; the UAE VAT return's sales and VAT;
- people: days on the roll-call, leave days taken;
- a sample contract with 10% retention, half billed, then taken back.

A project whose invoices or receipts don't add up to the old app's is
listed for the accountant, and so is every working day nobody was marked.
