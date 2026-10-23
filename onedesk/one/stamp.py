"""Our assets' addresses, with a hash of what is in them.

Frappe Cloud serves /assets as immutable for a year, and only its bundles have
a hash in their name. Our includes are plain files, so the address of one has
to change when the file does, or a deploy reaches nobody who has opened One
before. Nothing of frappe here: hooks.py imports it.
"""

import hashlib
from functools import cache
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "public"

ROOT = "/assets/onedesk/"

KINDS = ("js", "css")


@cache
def versions() -> dict:
	"""Every script and stylesheet we serve, by address, with its hash."""
	found = {}
	for kind in KINDS:
		for path in (PUBLIC / kind).rglob(f"*.{kind}"):
			if "dist" in path.parts or "node_modules" in path.parts:
				continue
			address = ROOT + path.relative_to(PUBLIC).as_posix()
			found[address] = hashlib.md5(path.read_bytes()).hexdigest()[:10]
	return found


def stamped(addresses):
	"""One address, or a list of them, with its hash as `?v=`."""
	if isinstance(addresses, str):
		held = versions().get(addresses)
		return f"{addresses}?v={held}" if held else addresses
	return [stamped(one) for one in addresses]
