"""What a workspace wrote down for OneAI to know.

Read by `one_ai/memory.py`: told to the model whenever its type is on screen,
and searched by `recall` otherwise. Everybody may read it, because OneAI reads
it as whoever is asking; only a Workspace Administrator writes it.
"""

from frappe.model.document import Document


class AIKnowledge(Document):
	pass
