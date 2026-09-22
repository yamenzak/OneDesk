"""What a press failure is, and whether it is worth trying again.

Nothing of Frappe in here on purpose. Retrying a permanent failure forever is
how a provisioning queue quietly stops working while looking busy, and the
decision that prevents it is four lines of arithmetic over a status code — so it
is four lines that can be read back in milliseconds rather than against a site.

Two exceptions, and `Again` is a subclass of `Refused` so that a caller who does
not care about the difference does not have to name both.
"""


class Refused(Exception):
	"""Press said no and will say no again. Do not retry."""

	def __init__(self, message: str, status: int | None = None, detail: str | None = None):
		super().__init__(message)
		self.status = status
		self.detail = detail


class Again(Refused):
	"""Press could not answer right now. Worth another attempt."""


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
	return kind(f"{endpoint}: {detail}", status, detail)


#: Where Frappe puts the readable part of a failure, in the order that prefers a
#: thrown message over a traceback. A press error is a Frappe error underneath.
SAYS = ("_server_messages", "message", "exception", "exc")

#: Enough of a failure to act on. A traceback in a log is useful; a traceback in
#: a Provisioning Job's error field is a record nobody scrolls.
KEPT = 500


def detail(body: dict | None, text: str) -> str:
	"""The most useful sentence in a press error body."""
	if not isinstance(body, dict):
		return text[:KEPT]
	for key in SAYS:
		if body.get(key):
			return str(body[key])[:KEPT]
	return str(body)[:KEPT]
