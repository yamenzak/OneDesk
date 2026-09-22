"""What a workspace may call itself, and what it may never claim.

Nothing of Frappe in here. A mistake in this module is a workspace claiming a
name that routes somebody else's traffic to it, so it has to be readable in one
sitting and testable in milliseconds — the same reason `keys.py` is pure.

**Two kinds of name, and they are not the same thing.** `<slug>.t.4dl.app` is
ours: it is served by a Cloudflare Worker that rewrites `Host` to the site's own
press name, and press is never told it exists. A customer's own name is theirs:
press adds it, verifies the DNS itself and issues the certificate. This module
decides only the second kind, because the first is not asked for — it is given.

**A tenant may not claim a name under a domain we operate.** Not our tenant
domain, not the admin's own host, not a bare public suffix. Nothing stops
somebody typing `admin.t.4dl.app` into the box, and the refusal belongs here
rather than in whatever press would eventually say about it.
"""

import re

#: Each label of a hostname: letters, digits and hyphens, not starting or ending
#: with one. Deliberately stricter than the RFC, which allows an underscore in
#: places nobody serving HTTP wants one.
LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

#: The longest a hostname may be, in the usual reading: 253 characters once the
#: trailing dot is dropped.
LONGEST = 253

#: The fewest labels a customer domain may have. A single label is not a domain,
#: and a two-label name is somebody's apex, which is allowed.
FEWEST_LABELS = 2

#: Labels nobody may take as the leftmost part of a name under a domain of ours.
#: This list only matters for names we serve; a customer's own `admin.acme.com`
#: is their business.
RESERVED = frozenset(
	{
		"admin",
		"api",
		"app",
		"assets",
		"billing",
		"cdn",
		"dashboard",
		"mail",
		"one",
		"portal",
		"press",
		"static",
		"status",
		"support",
		"www",
	}
)


class Unclaimable(ValueError):
	"""The name a workspace asked for is not one it may have."""


def tidy(raw: str) -> str:
	"""The name as it will be stored, or a refusal.

	Lower-cased, stripped of a trailing dot, and of a scheme and path if somebody
	pasted a URL — which they will, because the box is next to a link. Everything
	else is refused rather than repaired.
	"""
	if not isinstance(raw, str):
		raise Unclaimable("no domain")
	name = raw.strip().lower()
	for scheme in ("https://", "http://"):
		if name.startswith(scheme):
			name = name[len(scheme) :]
	name = name.split("/", 1)[0].split("?", 1)[0]
	name = name.rstrip(".")
	if not name:
		raise Unclaimable("no domain")
	if len(name) > LONGEST:
		raise Unclaimable(f"a domain is at most {LONGEST} characters")
	if ":" in name:
		raise Unclaimable("a domain does not carry a port")
	labels = name.split(".")
	if len(labels) < FEWEST_LABELS:
		raise Unclaimable(f"{name} is not a domain")
	for label in labels:
		if not LABEL.match(label):
			raise Unclaimable(f"{label!r} is not a usable part of a domain name")
	return name


def ours(name: str, *served) -> bool:
	"""Whether this name is one we operate, rather than a customer's own.

	Matches the domain itself and anything under it, so `t.4dl.app` and
	`anything.t.4dl.app` are both ours while `nott.4dl.app` is not.
	"""
	for domain in served:
		if not domain:
			continue
		# A port, because the admin's own host carries one in development and the
		# name being compared never can — `tidy` refuses a port outright. Without
		# this, `onedesk.localhost` does not match `onedesk.localhost:8002` and
		# the admin console's own hostname is claimable. Measured, not imagined.
		domain = domain.strip().lower().rstrip(".").split(":", 1)[0]
		if not domain:
			continue
		if name == domain or name.endswith(f".{domain}"):
			return True
	return False


def claimable(raw: str, *served) -> str:
	"""The name a workspace may add, or a refusal saying why not.

	`served` is every domain we operate — the tenant domain and the admin's own
	host. A name under one of those is refused here, because press would add it
	happily and then we would be serving a customer at a name we hand out.
	"""
	name = tidy(raw)
	if ours(name, *served):
		raise Unclaimable(f"{name} is a name we hand out, so it cannot be added as your own")
	return name


def under(slug: str, tenant_domain: str) -> str:
	"""The name we give a workspace, which is never asked for and never refused."""
	if not slug or not tenant_domain:
		raise Unclaimable("a workspace needs a slug and a domain")
	return f"{slug}.{tenant_domain.strip().lower().rstrip('.')}"


def reserved_here(name: str, *served) -> bool:
	"""Whether this is a reserved label under a domain of ours.

	Only consulted for the names we hand out. It exists so that a slug nobody
	should have cannot arrive by a second route once custom domains are open.
	"""
	if not ours(name, *served):
		return False
	return name.split(".", 1)[0] in RESERVED
