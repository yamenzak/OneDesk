"""What a workspace may be called, which objects it may name, and whether it fits.

Nothing of Frappe or boto3 in here: a mistake means one customer reading
another's files. A tenant names a suffix, never an object, and `..` is refused.
"""

import posixpath
import re

ROOT = "tenants"

LONGEST = 900

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

	`held` is what was measured, `pending` what has been signed for since. A
	limit of zero or less means unmetered rather than nothing.
	"""
	if limit <= 0:
		return True
	return held + pending + wanted <= limit


SHORTEST, LONGEST_SLUG = 3, 30

RESERVED = frozenset(
	"admin api app apps assets auth billing cdn dashboard dev docs files help "
	"login mail one portal press static status support www".split()
)

_ROUGH = re.compile(r"[^a-z0-9]+")


def slug(raw: str) -> str:
	"""A workspace name turned into something that can be a hostname.

	Tidies rather than refuses, because this runs on what somebody typed into a
	signup box — but it refuses what tidying cannot fix, since a silently
	renamed workspace is a customer whose link does not work.
	"""
	tidy = _ROUGH.sub("-", (raw or "").strip().lower()).strip("-")
	if len(tidy) < SHORTEST:
		raise Unnameable(f"a workspace name needs at least {SHORTEST} letters or digits")
	if len(tidy) > LONGEST_SLUG:
		raise Unnameable(f"a workspace name is at most {LONGEST_SLUG} characters")
	if tidy in RESERVED:
		raise Unnameable(f"{tidy} is reserved")
	return tidy
