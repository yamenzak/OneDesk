"""Whether a webhook really came from Stripe.

Nothing of Frappe in here: an endpoint that takes money on this check is one
anybody can reach. Signatures are compared in constant time and the timestamp
is checked, so a captured one cannot be replayed.
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
