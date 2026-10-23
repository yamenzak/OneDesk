"""What a workspace may call itself, and what it may never claim.

Nothing of Frappe in here: a mistake is a workspace claiming a name that routes
somebody else's traffic to it. It decides only a customer's own names.
"""

import re

LABEL = re.compile(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$")

LONGEST = 253

FEWEST_LABELS = 2

RESERVED = frozenset(
	{
		"admin",
		"api",
		"app",
		"assets",
		"billing",
		"cdn",
		"dashboard",
		"fallback",
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


def _(text: str) -> str:
	"""Marks a sentence for translation without importing Frappe. The caller
	translates it (`Unclaimable.translated`)."""
	return text


class Unclaimable(ValueError):
	"""The name a workspace asked for is not one it may have: a sentence and
	what goes into its `{0}`."""

	def __init__(self, sentence: str, *values) -> None:
		super().__init__(sentence.format(*values))
		self.sentence, self.values = sentence, values

	def translated(self, translate) -> str:
		return translate(self.sentence).format(*self.values)


def tidy(raw: str) -> str:
	"""The name as it will be stored, or a refusal.

	Lower-cased, stripped of a trailing dot, and of a scheme and path if somebody
	pasted a URL — which they will, because the box is next to a link. Everything
	else is refused rather than repaired.
	"""
	if not isinstance(raw, str):
		raise Unclaimable(_("Enter a domain, such as office.example.com."))
	name = raw.strip().lower()
	for scheme in ("https://", "http://"):
		if name.startswith(scheme):
			name = name[len(scheme) :]
	name = name.split("/", 1)[0].split("?", 1)[0]
	name = name.rstrip(".")
	if not name:
		raise Unclaimable(_("Enter a domain, such as office.example.com."))
	if len(name) > LONGEST:
		raise Unclaimable(_("A domain is at most {0} characters."), LONGEST)
	if ":" in name:
		raise Unclaimable(_("Remove the port from the domain."))
	labels = name.split(".")
	if len(labels) < FEWEST_LABELS:
		raise Unclaimable(_("{0} is not a domain."), name)
	for label in labels:
		if not LABEL.match(label):
			raise Unclaimable(_("{0} cannot be part of a domain name."), label)
	return name


def ours(name: str, *served) -> bool:
	"""Whether this name is one we operate, rather than a customer's own.

	Matches the domain itself and anything under it, so `t.4dl.app` and
	`anything.t.4dl.app` are both ours while `nott.4dl.app` is not.
	"""
	for domain in served:
		if not domain:
			continue
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
		raise Unclaimable(_("{0} is a One address and can't be added."), name)
	return name


def under(slug: str, tenant_domain: str) -> str:
	"""The name we give a workspace, which is never asked for and never refused."""
	if not slug or not tenant_domain:
		raise Unclaimable(_("A workspace needs a slug and a domain."))
	return f"{slug}.{tenant_domain.strip().lower().rstrip('.')}"


def reserved_here(name: str, *served) -> bool:
	"""Whether this is a reserved label under a domain of ours.

	Only consulted for the names we hand out. It exists so that a slug nobody
	should have cannot arrive by a second route once custom domains are open.
	"""
	if not ours(name, *served):
		return False
	return name.split(".", 1)[0] in RESERVED


STUCK = frozenset({"blocked", "moved", "deleted", "pending_deletion", "test_blocked", "test_failed"})
GAVE_UP = frozenset(
	{"expired", "deleted", "initializing_timed_out", "validation_timed_out", "issuance_timed_out", "deployment_timed_out"}
)


PROOF = "_one"


def proof_name(name: str) -> str:
	"""Where a TXT record proves a name is its customer's to give."""
	return f"{PROOF}.{name}"


def proven(answers: list | None, target: str) -> bool:
	"""Whether DNS says the name's owner meant it for this workspace: an
	answer (a TXT at `_one.<name>`, or the name's own CNAME) that is the
	workspace's own address. Only whoever runs a domain's DNS can write
	either, which is what stops one workspace claiming another's name."""
	want = (target or "").strip().lower().rstrip(".")
	if not want:
		return False
	for one in answers or []:
		said = str((one or {}).get("data") or "").strip().strip('"').strip().lower().rstrip(".")
		if said == want:
			return True
	return False


def standing(said: dict | None) -> tuple[str, str | None]:
	"""A custom hostname as Cloudflare answers it, in our three words, with
	Cloudflare's own sentence about what is stopping it when there is one.

	Active only when both halves are: Cloudflare routes the name (its
	ownership is verified) and the certificate is live. Anything still on its
	way is Pending, because Cloudflare keeps checking by itself.
	"""
	if not said:
		return "Gone", None
	ssl = said.get("ssl") or {}
	status, certificate = said.get("status"), ssl.get("status")
	problems = [str(one) for one in said.get("verification_errors") or []]
	problems += [str(one.get("message") if isinstance(one, dict) else one) for one in ssl.get("validation_errors") or []]
	problem = problems[0] if problems else None
	if status == "active" and certificate == "active":
		return "Active", None
	if status in STUCK or certificate in GAVE_UP:
		return "Broken", problem
	return "Pending", problem
