"""One conversation with OneAI, stored so it is still there tomorrow.

Nothing happens in here. It is an agent conversation's transcript, written by
`one_chat/transcript.py`; this class exists because frappe wants one, and a rule
added here would be a rule the panel could not see.
"""

from frappe.model.document import Document


class AIChat(Document):
	pass
