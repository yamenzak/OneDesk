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

#: What a ledger check is, said once for each of them.
CHECK = "a check of ERPNext's own ledger, for when stock's worth looks wrong; Stock against the Books and the Inventory Check say what a workspace needs"

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
	("DocType", "Bin"): (ENGINE, "what each warehouse holds of each item; Stock Summary reads it"),
	("DocType", "Stock Ledger Entry"): (
		ENGINE,
		"one line per stock move; the Stock Ledger report shows them",
	),
	("DocType", "Repost Item Valuation"): (
		ENGINE,
		"ERPNext revalues stock after a back-dated move by itself",
	),
	("DocType", "BOM Update Log"): (ENGINE, "what a BOM Update Tool run changed"),
	("DocType", "Asset Activity"): (
		ENGINE,
		"an asset's history, kept as it is moved, repaired and depreciated",
	),
	("DocType", "Quick Stock Balance"): (REPLACED, "Stock Summary"),
	("Page", "stock-balance"): (REPLACED, "Stock Summary"),
	("Page", "shop-floor"): (REPLACED, "Shop Floor"),
	("Page", "visual-plant-floor"): (REPLACED, "Plant Floor"),
	("DocType", "Asset Depreciation Schedule"): (INSIDE, "an asset's form draws its schedule"),
	("DocType", "Stock Reposting Settings"): (
		LEFT_OUT,
		"how ERPNext paces revaluing stock; its defaults suit every workspace",
	),
	("Report", "Item Balance (Simple)"): (REPLACED, "Stock Summary"),
	("Report", "FIFO Queue vs Qty After Transaction Comparison"): (LEFT_OUT, CHECK),
	("Report", "Incorrect Balance Qty After Transaction"): (LEFT_OUT, CHECK),
	("Report", "Incorrect Serial No Valuation"): (LEFT_OUT, CHECK),
	("Report", "Incorrect Stock Value Report"): (LEFT_OUT, CHECK),
	("Report", "Stock Ledger Invariant Check"): (LEFT_OUT, CHECK),
	("Report", "Stock Ledger Variance"): (LEFT_OUT, CHECK),
	("Report", "Stock Valuation Comparison"): (LEFT_OUT, CHECK),
	("Report", "Stock Ledger Entries of Cancelled Vouchers"): (LEFT_OUT, CHECK),
}

#: Names kept wherever upstream says them: an outside product a workspace meets,
#: or a notice to keep. Every other brand reads One (onedesk/translations/).
OUTSIDE = {
	"Frappe Technologies": "the copyright notice the AGPL asks to be kept",
	"Frappe Cloud": "the host a workspace's site runs on",
	"Frappe Mail": "a mail service an email account can connect to",
	"Frappe CRM": "a separate CRM whose site CRM Settings can sync with",
	"Frappe School": "frappe's courses, linked from onboarding One marks complete",
	"Frappe Support": "frappe's support portal; One hides that row of the Help menu",
	"Frappe UI": "the component library a developer builds a page with",
}

#: Said in our own words where swapping the name would read badly.
SAID = {
	"Company Abbreviation (requires ERPNext to be installed)": (
		"Company Abbreviation",
		"اختصار الشركة",
		"Firmenkürzel",
	),
	"Fiscal Year (requires ERPNext to be installed)": ("Fiscal Year", "السنة المالية", "Geschäftsjahr"),
	"ERPNext Settings": ("Settings", "الإعدادات", "Einstellungen"),
	"ERPNext User ID": ("User ID", "معرف المستخدم", "Benutzer-ID"),
	"Something you bought before using ERPNext, with what you paid, where it is, and how much has already depreciated. See [Asset](https://docs.frappe.io/erpnext/user/manual/en/asset).": (
		"Something you bought before using One, with what you paid, where it is, and how much has already depreciated.",
		"شيء اشتريته قبل استخدام One، مع ما دفعته ومكانه ومقدار ما استُهلك منه.",
		"Etwas, das Sie vor One gekauft haben, mit dem Preis, dem Ort und der bereits erfolgten Abschreibung.",
	),
}

#: Documents naming a customer or supplier that are not sent to them, so need
#: no print of ours (scripts/atlas.py `goes_out`).
NOT_SENT = {
	"Purchase Invoice": "the supplier's own bill, entered as it came",
	"Supplier Quotation": "the supplier's prices, entered as they came",
	"Supplier Scorecard Period": "how a supplier scored, kept by the buyers",
	"Material Request": "goods asked for inside the company",
	"Production Plan": "what the workshop plans to make",
	"Asset": "the company's own equipment",
	"Vehicle Log": "a company car's trips and fuel",
	"Training Event": "a training the company runs for its people",
	"Shipment": "a booking with a carrier, whose label the carrier prints",
}
