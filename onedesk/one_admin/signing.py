"""Whether a webhook really came from Stripe.

Nothing of Frappe in here, because an endpoint that takes money on the strength
of this check is an endpoint anybody on the internet can reach. It has to be
readable in one sitting and testable in milliseconds, and the two ways to get it
wrong are both silent:

* **comparing signatures with `==`** leaks how much of a guess was right, one
  byte at a time, to anybody willing to measure;
* **ignoring the timestamp** means a signature captured once is good forever, so
  an old "payment succeeded" can be replayed to provision another workspace.

Stripe's scheme, for the record: the header is `t=<unix>,v1=<hex>,v1=<hex>…`,
the signed payload is `<t>.<raw body>`, and the signature is HMAC-SHA256 of that
with the endpoint's own secret. More than one `v1` appears while a secret is
being rotated, so any of them matching is a match.
"""

import hashlib
import hmac

#: How far out of step a delivery may be. Stripe's own default, and it is a
#: replay window rather than a clock allowance: shorter is safer and starts
#: rejecting real deliveries from a server whose clock has drifted.
TOLERANCE = 300


class Unsigned(ValueError):
	"""This did not come from Stripe, or did not come from Stripe recently."""


def parts(header: str) -> tuple[int, list[str]]:
	"""The timestamp and every candidate signature in the header."""
	stamp, signatures = 0, []
	for piece in (header or "").split(","):
		name, _, value = piece.strip().partition("=")
		if name == "t" and value.isdigit():
			stamp = int(value)
		elif name == "v1":
			signatures.append(value)
	if not stamp or not signatures:
		raise Unsigned("no signature")
	return stamp, signatures


def expected(payload: bytes, stamp: int, secret: str) -> str:
	return hmac.new(
		secret.encode(), b"%d.%s" % (stamp, payload), hashlib.sha256
	).hexdigest()


def verify(payload: bytes, header: str, secret: str, now: int, tolerance: int = TOLERANCE) -> int:
	"""Raise unless this is a signature Stripe made, recently.

	Returns the timestamp so a caller that wants to record it does not have to
	parse the header a second time.
	"""
	if not secret:
		raise Unsigned("no endpoint secret is configured")
	stamp, offered = parts(header)
	if abs(now - stamp) > tolerance:
		raise Unsigned(f"that delivery is {abs(now - stamp)} seconds out of step")
	want = expected(payload, stamp, secret)
	if not any(hmac.compare_digest(want, one) for one in offered):
		raise Unsigned("the signature does not match")
	return stamp
