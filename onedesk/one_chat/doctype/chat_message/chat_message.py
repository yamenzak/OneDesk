"""One message. Whoever may read its conversation reads it (one_chat/channels.py); it is written through one_chat/messages.py."""

from frappe.model.document import Document


class ChatMessage(Document):
	pass
