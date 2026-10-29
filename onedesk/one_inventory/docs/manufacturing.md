# Manufacturing

**Manufacturing** in the rail is the workshop: **Shop Floor**, **Plant
Floor**, **Work Order**, **BOM** and **Subcontracting Order**. Job cards,
subcontracting receipts and production plans are under Everything on Home,
and workstations, plant floors, operations and Manufacturing Settings under
Setup.

1. **Say how it is made.** A **BOM** (bill of materials) names what one of
   a product takes, and with **With Operations** the steps (cutting,
   assembling, glazing) and the workstation each is done at, with its
   minutes. Its page says its **Cost per Unit** in materials and time, its
   **Operations**, and how many **Work Order** use it.
2. **Make it.** A **Work Order** makes so many of a product, for stock,
   for a project or for a customer's order. Somebody who needs goods made
   asks with a **Material Request** of type Manufacture, and **Create ›
   Work Order** on it keeps who asked. Its page says the **Project**, the
   **Sales Order or Material Request** it is for, and under **Progress**
   how far it has got: Planned, Material Transferred, Operations (how many
   steps are done) and Manufactured (how many of how many).
   **Print** gives the floor its sheet: what to make, the materials and
   where they come from, and each step.
3. **Send the materials.** **Start** moves the materials from the stores to
   Work In Progress.
4. **Work each step.** Submitting the work order makes a **Job Card** for
   each step. Whoever works it logs their time and how many they did, in
   order. A job card done in part keeps the rest as still to do. Its page
   says the **Work Order**, the **Workstation**, the **Total Completed
   Qty**, the **Total Time in Mins** and the **Employee** who did it.
5. **Finish.** **Finish** on the work order puts what was made into
   Finished Goods, valued at its materials and its workshop time. Whoever
   asked for it and the project's manager are told (**Work Order Done**)
   once all of it is made.

### Shop Floor

**Shop Floor** under Manufacturing is the page for the people in the
workshop. Over it, how many **Open Work Orders** there are, how many steps
someone is on now (**Running Now**), how many are **Waiting to Start**, and
how many were **Closed Today**. **New Work Order** starts one.

- **Open** is a table of the work orders still on the floor: the item with
  its number and project, its status, the step it is at and where, how
  many are made with a bar, how many of its steps are done, and when it is
  wanted, red once that is past. **Completed** lists the finished ones.
  Each workstation has a tab of its own with its steps, the oldest first.
- **A work order** shows its steps as cards, each a job card: the operation
  and its workstation, its status, who is on it and the clock while it
  runs, how many are done of how many with a bar, what of its materials is
  short in the stores, and whether it needs a quality check before it
  closes, with one button for what comes next and the rest in its menu.
  **Finish** puts what was made into stock, as on the work order.
- **Start** asks when it started and who is on it, the reader first. A
  running step has **Pause**, and a paused one **Resume**.
- **Record Made**, in the step's menu, asks how many were made and lost and
  when the session ended. **Close Operation** closes the step, its quality
  check first when it needs one. **Carry On Later** records the session and
  leaves the step paused for the next. A step whose sessions are all
  recorded has **Close Operation** as its button.
- **Transfer Material** makes the stock entry that moves what the step
  still needs to it. **Check Quality** takes the readings of the step's
  quality check and records them. A rejected check keeps the step open.
  **Read Instructions** shows the operation's own instructions. **Open Job
  Card** opens the step's job card.
- A step that makes a part of its own (**Receive Into Stock**) puts it into
  stock once closed.

Everything on it is the job card itself, so the job card's form, its time
logs and its reports say the same. It changes as soon as somebody else
starts or closes a step.

### Plant Floor

**Plant Floor** under Manufacturing shows a floor's workstations as cards.
Over it, how many **Workstations** there are, how many are in
**Production**, how many are **Stopped** by a problem or for maintenance,
and how many **Operations Running**.

- Each card says the workstation's type, its status with its colour, each
  step running on it with who is on it and its clock, and how many steps
  wait to start there. Its name and **Operations** open the workstation's
  steps on the Shop Floor, and the gear (**Open Workstation**) opens the
  workstation.
- The status is a menu on the card (**Change Status**): Production, Off,
  Idle, Problem, Maintenance or Setup. Every open Plant Floor changes with
  it.
- **All Types** and **Any Status** narrow the cards. A workspace with more
  than one floor has a tab for each.
- **Stock Here** is a table of what the floor's warehouse holds, how much of
  it is kept for work orders, and how much is on its way, each with its
  unit. **Add Stock** and **Move Stock** make the stock entry as a draft to
  check and submit.
- A floor is set up with **New Plant Floor**: its name and its warehouse.
  **Edit Plant Floor** changes it. A workstation joins it with **Plant
  Floor** on the workstation.

### What Making Costs a Project

The materials a project's work order uses count in the project's Stock Used
on OneProject.

### Work Sent to Suppliers

A product a supplier makes from your materials, powder coating say, is a
**Subcontracting BOM** (Setup) naming the supplier's service.
**Subcontracting Order** in the rail keeps that work on one page.

- The figures say how many orders are **Open**, how many still have
  **Material to Transfer**, how many are **Late** back, and what our
  materials **With Suppliers** are worth at cost.
- **Open** is a table: what the supplier makes with its number and
  project, the supplier, where it stands, what went to them (**Supplied**),
  how much is **Received** with a bar, and when it is **Due**, red once
  late. **Received** is the same table of those done with, with when each
  went.
- **New Subcontracting Order** starts the purchase order for the
  supplier's service, marked **Is Subcontracted**. A purchase order with no
  subcontracting order yet is listed under **Not Ready to Send**, with
  **Make Subcontracting Order**.
- In an order's menu, **Transfer Material** opens the transfer of your
  materials to the supplier and **Subcontracting Receipt** the receipt of
  what they made into the stores, both as drafts to check and submit.
  **Open Purchase Order** opens the order it came from.

The supplier's bill is made from the purchase receipt the subcontracting
receipt creates. A subcontracting order's page says the **Project**, its
**Total**, and under **Progress**: Ordered, Material Transferred and
Received. OneAI answers **What is out with suppliers?** there. This is not
OneProject's subcontract, which is a package of work on a project.
