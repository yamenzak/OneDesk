"""Something a model suggested doing, waiting for a person.

Read-only to everybody, including the person it was written for. There is no
field here anybody edits: a proposal is applied, refused, or left alone, and all
three are `one_ai/proposals.py` setting a state — because a proposal somebody
could edit before applying is a proposal that no longer says what the model
suggested, and the whole point of the card is that it does.
"""

from frappe.model.document import Document


class AIProposal(Document):
	pass
