"""What OneAI can do in OneHR.

The tools and suggestions this module adds to the panel, named in `hooks.py`
under `one_ai_suggests` and `one_ai_suggestions`. The rules are OneAI's: a tool
runs as the person asking, and anything that would write is a card somebody
approves. What this module adds is what HR knows — whose employee record a
receipt belongs to, what a claim needs, which expense types this workspace has.

**A receipt becomes a claim, never a payment.** `claim_expense` reads nothing
the person could not, and writes nothing: it suggests an Expense Claim in their
own name with one row, and the receipt goes on the claim when it is approved.
The claim then goes through this workspace's approval like any other, which is
where a wrong amount is caught — by the person who approves expenses, not by the
model that read the paper.
"""

from typing import Annotated

import frappe

from onedesk.one_ai import proposals
from onedesk.one_hr import own

#: What the panel offers, by doctype, when it opens on one. `file` means the
#: chip asks for a file first and then says `ask` with it. `can` is the verb the
#: reader must hold on the doctype for the chip to be offered at all.
SUGGESTIONS = {
	"Expense Claim": [
		{
			"label": "Claim a receipt",
			"ask": "Make an expense claim from this receipt.",
			"file": True,
			"can": "create",
		},
	],
}


def claim_expense(
	expense_date: Annotated[str, "The date on the receipt, as YYYY-MM-DD."],
	amount: Annotated[float, "The total paid, as printed on the receipt."],
	expense_type: Annotated[str, "What kind of expense it is, in a word or two, such as taxi, meal or hotel."],
	description: Annotated[str, "The vendor and what was bought, in a few words."],
	currency: Annotated[str, "The currency code on the receipt, such as AED."] | None = None,
) -> dict:
	"""Suggest an expense claim, in the asker's own name, from one receipt.

	Nothing is claimed until the person approves it, and then it goes through
	the workspace's own approval like any claim.
	"""
	employee = own.employee_of()
	if not employee:
		return {"error": "The person asking has no employee record here, so there is nobody to claim for."}

	types = frappe.get_all("Expense Claim Type", pluck="name")
	chosen = kind(expense_type, description, types)
	if not chosen:
		return {"error": "This workspace has no expense types yet, so there is nothing to claim under."}

	company = frappe.db.get_value("Employee", employee, "company")
	ours = frappe.db.get_value("Company", company, "default_currency") if company else None
	said = (currency or "").strip().upper()
	if said and ours and said != ours:
		# Claimed in the company's currency or not at all. A converted amount
		# would be a rate the model made up; the approver sees the receipt.
		return {
			"error": f"The receipt is in {said} and claims here are in {ours}. "
			"Say so to the person rather than converting it."
		}

	name = proposals.propose(
		"Create",
		"Expense Claim",
		changes={
			"employee": employee,
			"posting_date": frappe.utils.today(),
			"expenses": [
				{
					"expense_date": expense_date,
					"expense_type": chosen,
					"description": (description or "").strip()[:140],
					"amount": float(amount or 0),
				}
			],
		},
		why=frappe._("From a receipt: {0}, {1}.").format((description or "").strip()[:80], amount),
		files=frappe.flags.get("one_ai_files") or [],
	)
	return {
		"proposal": name,
		"state": "Proposed",
		"said": frappe._("Suggested. It happens when somebody approves it."),
	}


#: Words on a receipt, and the kind of expense they usually are. Only used when
#: the workspace has a type of that name; a workspace's own types are the list.
KINDS = {
	"Travel": ("taxi", "cab", "uber", "careem", "flight", "airline", "train", "metro", "bus",
			   "hotel", "fuel", "petrol", "parking", "toll", "travel", "transport", "trip"),
	"Food": ("meal", "food", "lunch", "dinner", "breakfast", "restaurant", "cafe", "coffee", "snack"),
	"Calls": ("phone", "mobile", "call", "sim", "internet", "data"),
	"Medical": ("medical", "pharmacy", "clinic", "doctor", "hospital", "medicine"),
}


def kind(said: str | None, description: str | None, types: list[str]) -> str | None:
	"""The workspace's expense type closest to what the model read.

	Decided here rather than by the model, because a model told a type does not
	exist asks the person which one — a question the approver answers better,
	later, on the claim. Its own word first, then what the receipt says, then
	whatever is closest by name, then Others: a claim filed under the wrong type
	is corrected by an approver, and a claim never suggested is not.
	"""
	if not types:
		return None
	by_name = {one.lower(): one for one in types}
	said = (said or "").strip().lower()
	if said in by_name:
		return by_name[said]

	words = f"{said} {(description or '').lower()}"
	for name, clues in KINDS.items():
		if name.lower() in by_name and any(clue in words for clue in clues):
			return by_name[name.lower()]

	import difflib

	near = difflib.get_close_matches(said, list(by_name), n=1, cutoff=0.6)
	if near:
		return by_name[near[0]]
	return by_name.get("others") or by_name.get("other") or types[0]
