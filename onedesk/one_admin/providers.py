"""Which cloud a connected machine is on, and where, from what that cloud's
own metadata service told it. deploy/server/connect.sh asks each service and
sends back what answered; nothing here reaches the network. AGENTS.md,
Servers."""

import base64
import binascii
import json
import re

OTHER = "Other"
HELD = 65536
REGION = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


def _at(text: str, *path: str) -> str:
	"""The value at `path` in a JSON answer, or nothing. Pure."""
	try:
		read = json.loads(text)
	except (ValueError, RecursionError):
		return ""
	for key in path:
		read = read.get(key) if isinstance(read, dict) else None
	return read if isinstance(read, str) else ""


def _google(text: str) -> str:
	return text.strip().rsplit("/", 1)[-1].rsplit("-", 1)[0]


READERS = (
	("oracle", "Oracle", lambda text: text.strip()),
	("aws", "AWS", lambda text: _at(text, "region")),
	("google", "Google Cloud", _google),
	("azure", "Azure", lambda text: _at(text, "location")),
	("digitalocean", "DigitalOcean", lambda text: text.strip()),
	("hetzner", "Hetzner", lambda text: text.strip().split("-dc", 1)[0]),
	("vultr", "Vultr", lambda text: _at(text, "region", "regioncode")),
	("akamai", "Akamai", lambda text: _at(text, "region")),
	("scaleway", "Scaleway", lambda text: _at(text, "zone") or _at(text, "location", "zone_id")),
)


def where(found: dict) -> tuple[str, str]:
	"""The provider and region the first service that answered sensibly names,
	or Other and no region. Pure."""
	for key, provider, read in READERS:
		text = found.get(key)
		if not isinstance(text, str) or not text.strip():
			continue
		region = read(text).strip().lower()
		if REGION.match(region):
			return provider, region
	return OTHER, ""


def decoded(sent: dict) -> dict:
	"""What connect.sh sends, each answer in base64, as text. Pure."""
	out = {}
	for key, value in (sent or {}).items():
		if not isinstance(value, str) or len(value) > HELD:
			continue
		try:
			out[key] = base64.b64decode(value, validate=True).decode("utf-8", "replace")
		except (binascii.Error, ValueError):
			continue
	return out
