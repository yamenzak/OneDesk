"""The signed, short-lived token an agent's call carries between the Agents
Worker and this workspace (deploy/agents/README.md, The token). Its twin is
deploy/agents/token.ts; tests/test_agents.py holds them to each other. Pure:
whether a token was seen before is the caller's to say (`seen`)."""

import base64
import hashlib
import hmac
import json
import uuid

from frappe.utils import sha256_hash

LONGEST = 120
EARLY = 5
WAYS = ("workspace", "agents")


class Refused(ValueError):
	"""Not a token this workspace's secret signed, for this way, this body and now."""


def secret_for(master: str, workspace: str) -> str:
	"""A workspace's own secret, made from the Worker's: OneAdmin hands it to
	the workspace, the Worker makes it again from the workspace's slug."""
	return _hmac(master, f"agents:{workspace}")


def mint(secret: str, claims: dict, body: str, now: int, lasts: int = 60) -> str:
	full = {**claims, "sum": sha256_hash(body or ""), "iat": now, "exp": now + min(lasts, LONGEST), "jti": str(uuid.uuid4())}
	said = base64.urlsafe_b64encode(json.dumps(full, separators=(",", ":")).encode()).decode().rstrip("=")
	return f"{said}.{_hmac(secret, said)}"


def verify(secret: str, token: str, way: str, body: str, now: int, seen=lambda jti, until: False) -> dict:
	"""The claims of a token signed with `secret` for `way` over exactly this
	body, inside its two minutes and never seen before, or Refused. `seen`
	answers whether a jti was already used, and remembers it until it lapses."""
	said, _, signed = (token or "").partition(".")
	if not secret or not said or not signed or not hmac.compare_digest(_hmac(secret, said), signed):
		raise Refused("not signed by this workspace's secret")
	try:
		claims = json.loads(base64.urlsafe_b64decode(said + "=" * (-len(said) % 4)))
	except ValueError as raised:
		raise Refused("not a token") from raised
	if claims.get("aud") != way or way not in WAYS:
		raise Refused("signed for the other way")
	if claims.get("exp", 0) < now or claims.get("iat", 0) > now + EARLY or claims["exp"] - claims["iat"] > LONGEST:
		raise Refused("out of its time")
	if claims.get("sum") != sha256_hash(body or ""):
		raise Refused("signed for another body")
	if not claims.get("jti") or seen(claims["jti"], claims["exp"]):
		raise Refused("used before")
	return claims


def _hmac(secret: str, text: str) -> str:
	return hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest()
