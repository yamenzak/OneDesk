"""What a press failure is, and whether it is worth trying again.

Nothing of Frappe in here, so the decision reads back in milliseconds.
`Again` is a subclass of `Refused`, so a caller may name only the one.
"""


class Refused(Exception):
	"""Press said no and will say no again. Do not retry."""

	def __init__(self, message: str, status: int | None = None, detail: str | None = None, said: str | None = None):
		super().__init__(message)
		self.status = status
		self.detail = detail
		self.said = said


class Again(Refused):
	"""Press could not answer right now. Worth another attempt."""


class Busy(Again):
	"""A server is doing something else to this site. Not a failure: wait."""


class Blank(Again):
	"""A model answered, and said nothing.

	Gemini does this now and then: a 200, a candidate that finished normally,
	no parts in it and no output tokens. The same request a moment later
	answers. It is a blip rather than a refusal, so it is worth another attempt
	— and the gateway makes one before it tells anybody.
	"""


class Malformed(Again):
	"""A model wrote a tool call its own provider could not read back.

	Gemini's MALFORMED_FUNCTION_CALL: it writes the call as code and a long
	argument spread over lines (a layout, a stylesheet) breaks it. Asked again
	with that said, it writes the arguments on one line and the call reads.
	"""


def worth_retrying(status: int) -> bool:
	"""Whether this status will plausibly answer differently in two minutes.

	429 is a rate limit and 5xx is press having a bad moment; both pass. Every
	other 4xx is our request being wrong, and a wrong request is wrong forever.
	"""
	return status == 429 or status >= 500


def raised(endpoint: str, status: int, detail: str, said: str | None = None) -> Refused:
	"""The exception this failure deserves, ready to raise.

	`said` is the other side's own `exc_type` where it sent one, and it wins
	over the status. Frappe answers every thrown exception with a 500, so a
	permanent refusal — a model that is not offered, a conversation that has run
	too long — arrives looking like a server having a bad moment, and the caller
	retries something that will refuse exactly the same way for ever.
	"""
	if said in ("Refused", "Again"):
		kind = Again if said == "Again" else Refused
	else:
		kind = Again if worth_retrying(status) else Refused
	if said == "NotEnough" or "NotEnough" in (detail or ""):
		try:
			from onedesk.one import account

			account.ran_out()
		except Exception:
			import frappe

			frappe.log_error(title="telling the credits ran out")
	return kind(f"{endpoint}: {detail}", status, detail, said)


SAYS = ("_server_messages", "message", "exception", "exc")

KEPT = 500


def detail(body: dict | None, text: str) -> str:
	"""The most useful sentence in a press error body."""
	if not isinstance(body, dict):
		return text[:KEPT]
	for key in SAYS:
		if body.get(key):
			if key == "_server_messages":
				return _messages(body[key])[:KEPT]
			return str(body[key])[:KEPT]
	return str(body)[:KEPT]


def _messages(said) -> str:
	"""What `frappe.throw` said: `_server_messages` is a JSON list of JSON
	objects, each with its sentence under `message`. Anything else as it came."""
	import json

	try:
		sentences = [json.loads(one).get("message") if isinstance(one, str) else None for one in json.loads(said)]
	except (TypeError, ValueError, AttributeError):
		return str(said)
	return " ".join(one for one in sentences if one) or str(said)
