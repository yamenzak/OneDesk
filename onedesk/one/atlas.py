"""Every record type, report and page the map in scripts/atlas.py cannot find
a way into, answered: where it is reached all the same, or why it is not
(docs/ATLAS.md). One a rail, a Home, a route or a form's link reaches needs no
line here. One with no line and no way in is still to be decided.
"""

#: Kept by the system as work is done; nobody opens it by hand.
ENGINE = "engine"
#: Reached from inside a page or a record, in a way the map cannot read.
INSIDE = "inside"
#: One of ours does its work, so it is not offered.
REPLACED = "replaced"
#: Not offered, and why.
LEFT_OUT = "left out"

ANSWERS = {
	# One's own
	("DocType", "AI Memory"): (INSIDE, "Workspace Settings › Privacy lists and forgets what OneAI remembers"),
	("DocType", "Cloud Drive Password"): (INSIDE, "OneCloud › Connect a Drive makes and revokes them"),
	("DocType", "Cloud File Request"): (INSIDE, "a OneCloud folder's Request Files"),
	("DocType", "Cloud File Version"): (INSIDE, "a OneCloud file's Versions"),
	("DocType", "Cloud Link"): (INSIDE, "a OneCloud file's Share"),
	("DocType", "Credit Reservation"): (ENGINE, "credits held while OneAI works, released when it is done"),
	("DocType", "Face"): (ENGINE, "the faces OneMail draws beside a sender"),
	("DocType", "File Link"): (ENGINE, "what OneIntake filed a document under"),
	("DocType", "Identifier"): (ENGINE, "numbers OneIntake recognised a party by"),
	("DocType", "Intake Lesson"): (ENGINE, "what OneIntake learnt from a correction"),
	("DocType", "Intake Settings"): (INSIDE, "Workspace Settings › OneIntake"),
	("DocType", "Interview Recording"): (INSIDE, "an interview's Recording, on the interview"),
	("DocType", "Legal Document Version"): (ENGINE, "each agreement as it was agreed to"),
	("DocType", "Reading"): (INSIDE, "a OneIntake document's Reading"),
	("DocType", "Workspace Account"): (INSIDE, "Account, from the rail's foot"),
	("DocType", "Workspace Customization"): (ENGINE, "OneStudio's ledger of what a workspace changed"),
	("Page", "item-view"): (INSIDE, "an Item opens on it"),
	("Page", "project-view"): (INSIDE, "a Project opens on it"),
	("Page", "project-template-view"): (INSIDE, "a Project Template opens on it"),
	("Page", "task-view"): (INSIDE, "a Task opens on it"),
	# OneInventory
	("DocType", "Bin"): (ENGINE, "what each warehouse holds of each item; Stock on Hand reads it"),
	("DocType", "Stock Ledger Entry"): (
		ENGINE,
		"one line per stock move; the Stock Ledger report shows them",
	),
	("DocType", "Stock Closing Balance"): (ENGINE, "balances a Stock Closing Entry keeps"),
	("DocType", "Repost Item Valuation"): (
		ENGINE,
		"ERPNext revalues stock after a back-dated move by itself",
	),
	("DocType", "BOM Update Log"): (ENGINE, "what a BOM Update Tool run changed"),
	("DocType", "Asset Activity"): (
		ENGINE,
		"an asset's history, kept as it is moved, repaired and depreciated",
	),
	("DocType", "Quick Stock Balance"): (REPLACED, "Stock on Hand"),
	("Page", "stock-balance"): (REPLACED, "Stock on Hand"),
	("Page", "shop-floor"): (REPLACED, "Shop Floor"),
	("Page", "visual-plant-floor"): (REPLACED, "Plant Floor"),
}
