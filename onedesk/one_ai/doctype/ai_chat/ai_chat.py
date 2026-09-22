"""One conversation with OneAI, stored so it is still there tomorrow.

Nothing happens in here. The turns are written by `one_ai/chat.py`, which is
where the loop and the page pointer live; this class exists because frappe wants
one, and a rule added here would be a rule the panel could not see.
"""

from frappe.model.document import Document


class AIChat(Document):
	pass
