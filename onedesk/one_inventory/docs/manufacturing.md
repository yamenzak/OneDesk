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
  wanted, red once that is past. A work order whose steps are all closed
  stays here until its goods are made, so someone presses **Finish**.
  **Completed** lists the finished ones.
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

**Plant Floor** under Manufacturing lists the floors; open one to see its
workstations as cards, each with its status, and the stock its warehouse
holds.

- Each workstation's card changes as soon as its status does, anywhere.
  **Create Workstation** adds one to the floor.
- The stock part says what the floor's warehouse holds, how much is kept
  for work orders and how much is on its way. **Add** and **Move** on an
  item make the stock entry as a draft to check and submit.
- A floor is set up with **New Plant Floor**: its name and its warehouse.
  A workstation joins it with **Plant Floor** on the workstation.

OneAI answers **What are the machines doing?** on a plant floor.

### What Making Costs a Project

The materials a project's work order uses count in the project's Stock Used
on OneProject.

### Work Sent to Suppliers

A product a supplier makes from your materials, powder coating say, is a
**Subcontracting BOM** (Setup) naming the supplier's service.
**Subcontracting Order** in the rail lists that work: what each order
makes, for which supplier, and where it stands.

- Start with the purchase order for the supplier's service, marked **Is
  Subcontracted**; **Create › Subcontracting Order** on it makes the order
  that says what the supplier makes and from what.
- On the subcontracting order, **Transfer › Material to Supplier** sends
  your materials to them, and **Create › Subcontracting Receipt** takes in
  what they made, both as drafts to check and submit.

The supplier's bill is made from the purchase receipt the subcontracting
receipt creates. A subcontracting order's page says the **Project**, its
**Total**, and under **Progress**: Ordered, Material Transferred and
Received. OneAI answers **What is out with suppliers?** there. This is not
OneProject's subcontract, which is a package of work on a project.
