"""Which object a workspace is allowed to name, and whether it has room.

Nothing of Frappe or boto3 in here, because this is the module where a mistake
means one customer reading another customer's files. It has to be readable in
one sitting and testable in milliseconds.

**A tenant never names an object; it names a suffix.** Everything it asks for is
put under `tenants/<slug>/` by this module, and a key that would escape that is
refused rather than trimmed. Trimming is how you end up with two tenants sharing
a prefix because one of them sent something clever.

**A `..` segment is refused outright**, even one that would land back inside the
prefix. `a/../b` is harmless and nobody legitimate sends it, so the rule that is
easy to verify beats the rule that is merely correct.
"""

import posixpath

#: Where a workspace's objects live. One prefix per tenant inside one of two
#: buckets, never a bucket per tenant: a lifecycle rule written against one
#: bucket gets written against the next one too, and a key scoped to a bucket
#: still reaches every tenant in it.
ROOT = "tenants"

#: S3 caps a key at 1024 bytes. Ours is shorter so the prefix always fits and a
#: refusal happens here rather than as a puzzling error from R2.
LONGEST = 900

#: Never valid in a key we sign. A backslash is not a separator in S3 but is one
#: in plenty of things that later read the key back.
FORBIDDEN = ("\\", "\x00", "\n", "\r")


class Unnameable(ValueError):
	"""The key a workspace asked for is not one it may have."""


def prefix(slug: str) -> str:
	"""Everything this workspace owns, and nothing else."""
	if not slug or "/" in slug:
		raise Unnameable(f"not a workspace name: {slug!r}")
	return f"{ROOT}/{slug}/"


def under(slug: str, key: str) -> str:
	"""The full object key for what this workspace asked for.

	Raises rather than repairs. A caller sending something that needs repairing
	is a caller doing something we do not understand, and guessing what they
	meant is how a guess becomes a cross-tenant read.
	"""
	if not isinstance(key, str) or not key.strip():
		raise Unnameable("no key")
	if any(bad in key for bad in FORBIDDEN):
		raise Unnameable("a key may not contain a backslash or a control character")
	if key.startswith("/"):
		raise Unnameable("a key is relative to the workspace, so it does not start with /")
	if ".." in key.split("/"):
		raise Unnameable("a key may not contain ..")

	tidy = posixpath.normpath(key).lstrip("./")
	if not tidy or tidy == ".":
		raise Unnameable("no key")

	full = prefix(slug) + tidy
	if len(full.encode()) > LONGEST:
		raise Unnameable(f"that key is longer than {LONGEST} bytes")
	if not full.startswith(prefix(slug)):
		raise Unnameable("that key is outside the workspace")
	return full


def owns(slug: str, full: str) -> bool:
	"""Whether a key we are being asked about is this workspace's.

	The read side of `under`. A workspace asking to fetch or delete sends a key
	it was given, and this is the check that it was given it by us.
	"""
	try:
		return full.startswith(prefix(slug))
	except Unnameable:
		return False


def room_for(held: int, pending: int, limit: int, wanted: int) -> bool:
	"""Whether `wanted` more bytes fit.

	`held` is what was measured, `pending` is what has been signed for since —
	a signed URL is a promise somebody may keep, so it counts against the limit
	until the next measurement says whether it was kept. A limit of zero or less
	means unmetered rather than nothing: a plan with no storage line is a plan
	nobody thought about, and refusing every upload is a worse answer than not
	enforcing a limit that was never set.
	"""
	if limit <= 0:
		return True
	return held + pending + wanted <= limit
