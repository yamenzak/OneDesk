"""How risky an arriving message looks, from what it carries and nothing
else: what the receiving server found of its sender (SPF, DKIM, DMARC), a
reply address or a name that is not the sender's, links whose words and
target differ or that hide where they go, attachments that can run code,
and a sender's domain that imitates one the workspace knows
(lookalike.py). Each signal has its weight (WEIGHTS) and counts once; the
score is their sum, at most 100. OneAI's own reading adds its verdict
later (held.judged). Pure, but for `known` in `of`."""

import io
import ipaddress
import re
import zipfile
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from urllib.parse import urlparse

from frappe import _

from onedesk.one import registry
from onedesk.one_mail import lookalike
from onedesk.one_mail.theirs import _aligned, _results

WEIGHTS = {
	"dmarc": 50,
	"spf": 20,
	"spf_soft": 10,
	"dkim": 15,
	"reply_to": 15,
	"name": 25,
	"link_shown": 30,
	"link_ip": 20,
	"link_short": 10,
	"program": 60,
	"double": 60,
	"archive": 60,
	"macro": 50,
	"lookalike": 40,
	"foreign": 15,
	"phishing": 50,
	"spam": 20,
}

MOST = 100

PROGRAMS = frozenset(
	(
		"exe", "scr", "com", "pif", "bat", "cmd", "vbs", "vbe", "js", "jse", "wsf", "wsh", "hta", "msi", "msp",
		"cpl", "jar", "ps1", "psm1", "lnk", "reg", "dll", "iso", "img", "vhd", "vhdx", "appx", "msix",
	)
)  # fmt: skip
MACROS = frozenset(("docm", "dotm", "xlsm", "xltm", "xlam", "xlsb", "pptm", "potm", "ppam", "ppsm", "sldm"))
OFFICE = frozenset(("docx", "dotx", "xlsx", "xltx", "pptx", "potx", "ppsx"))
OLD_OFFICE = frozenset(("doc", "dot", "xls", "xlt", "ppt", "pot", "pps"))
ARCHIVES = frozenset(("zip",))
DOCUMENTS = frozenset(("pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "jpg", "jpeg", "png", "csv", "rtf"))
SHORTENERS = frozenset(
	(
		"bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "rebrand.ly",
		"shorturl.at", "tiny.cc", "rb.gy", "t.ly", "s.id", "lnkd.in", "bl.ink", "v.gd", "qrco.de",
	)
)  # fmt: skip
TURNED = "‮"

SHOWN_HOST = re.compile(r"^\s*(?:https?://)?((?:[a-z0-9-]+\.)+[a-z]{2,})(?:[/:?#]\S*)?\s*$", re.IGNORECASE)
ADDRESS = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
URL = re.compile(r"https?://[^\s<>\"')]+", re.IGNORECASE)


class _Links(HTMLParser):
	def __init__(self):
		super().__init__(convert_charrefs=True)
		self.found, self._open = [], None

	def handle_starttag(self, tag, attrs):
		if tag == "a":
			self._open = [dict(attrs).get("href") or "", ""]

	def handle_data(self, data):
		if self._open is not None:
			self._open[1] += data

	def handle_endtag(self, tag):
		if tag == "a" and self._open is not None:
			self.found.append(tuple(self._open))
			self._open = None


def links(html: str | None, text: str | None = None) -> list[tuple[str, str]]:
	"""Every link as (target, the words it shows): the HTML's anchors, and
	bare addresses in the plain text. Pure."""
	found = []
	if html:
		reader = _Links()
		try:
			reader.feed(html)
		except Exception:
			pass
		found += reader.found
	found += [(one, one) for one in URL.findall(text or "")]
	return found


def host_of(url: str) -> str:
	try:
		return (urlparse(url.strip()).hostname or "").lower().strip(".")
	except ValueError:
		return ""


def _is_ip(host: str) -> bool:
	try:
		ipaddress.ip_address(host.strip("[]"))
		return True
	except ValueError:
		return False


def _same_site(a: str, b: str) -> bool:
	return lookalike.split(a) == lookalike.split(b)


def of_links(found: list[tuple[str, str]]) -> list[dict]:
	"""What the links say: one that shows a website's name and opens
	another, one that opens a bare numbered address, and one through a link
	shortener. Pure."""
	out = {}
	for target, words in found:
		if not target.lower().startswith(("http://", "https://")):
			continue
		host = host_of(target)
		if not host:
			continue
		if _is_ip(host):
			out.setdefault("link_ip", {"why": "link_ip", "opens": host})
		elif host in SHORTENERS:
			out.setdefault("link_short", {"why": "link_short", "via": host})
		shown = SHOWN_HOST.match(words or "")
		if shown and words.strip() != target.strip():
			named = shown.group(1).lower()
			named = named[4:] if named.startswith("www.") else named
			if not _same_site(named, host[4:] if host.startswith("www.") else host):
				out.setdefault("link_shown", {"why": "link_shown", "shows": named, "opens": host})
	return list(out.values())


def _ending(name: str) -> str:
	return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def _inside_zip(content: bytes) -> list[str]:
	try:
		with zipfile.ZipFile(io.BytesIO(content or b"")) as held:
			return held.namelist()
	except (zipfile.BadZipFile, ValueError, OSError, RuntimeError):
		return []


def of_file(name: str, content: bytes | None) -> dict | None:
	"""What one attachment says: a program, a program dressed as a document
	(`invoice.pdf.exe`, or a name turned around by a hidden character), a
	file that runs macros (by its type, or an Office file holding a macro
	project whatever it is called), or an archive holding either. Pure."""
	name = (name or "").strip()
	lowered = name.lower()
	ending = _ending(lowered)
	parts = [one.strip() for one in lowered.split(".")]
	if TURNED in name or (len(parts) >= 3 and parts[-2] in DOCUMENTS and (ending in PROGRAMS or ending in MACROS)):
		return {"why": "double", "file": name.replace(TURNED, "")}
	if ending in PROGRAMS:
		return {"why": "program", "file": name}
	if ending in MACROS:
		return {"why": "macro", "file": name}
	if ending in OFFICE and any(one.lower().endswith("vbaproject.bin") for one in _inside_zip(content)):
		return {"why": "macro", "file": name}
	if ending in OLD_OFFICE and b"_VBA_PROJECT" in (content or b""):
		return {"why": "macro", "file": name}
	if ending in ARCHIVES:
		for inner in _inside_zip(content):
			if _ending(inner) in PROGRAMS or _ending(inner) in MACROS:
				return {"why": "archive", "file": name, "holds": inner.rsplit("/", 1)[-1]}
	return None


def of_files(attachments: list[tuple[str, bytes]]) -> list[dict]:
	"""The riskiest thing each kind of attachment says, once per kind. Pure."""
	out = {}
	for name, content in attachments or []:
		said = of_file(name, content)
		if said:
			out.setdefault(said["why"], said)
	return list(out.values())


def of_authentication(headers, sender: str) -> list[dict]:
	"""What the receiving server found of the sender, from the topmost
	Authentication-Results (theirs.verified reads the same) and
	Received-SPF: DMARC failed, SPF failed or soft-failed, DKIM failed with
	no signature that passed. Nothing is said where the server said
	nothing. Pure."""
	domain = (sender or "").rsplit("@", 1)[-1].strip().lower()
	if headers is None or not domain:
		return []
	said = next(
		(str(value) for name, value in headers.items() if name.lower() in ("authentication-results", "arc-authentication-results")),
		"",
	)
	results = _results(said) if said else []
	spf = (str(headers.get("Received-SPF") or "").split() or [""])[0].lower()
	out = []
	if any(method == "dmarc" and result == "fail" for method, result, _ in results):
		out.append({"why": "dmarc", "domain": domain})
	spf_result = next((result for method, result, _ in results if method == "spf"), spf)
	if spf_result in ("fail", "permerror"):
		out.append({"why": "spf", "domain": domain})
	elif spf_result == "softfail":
		out.append({"why": "spf_soft", "domain": domain})
	dkim = [(result, props) for method, result, props in results if method == "dkim"]
	if dkim and not any(result == "pass" for result, _ in dkim) and any(result == "fail" for result, _ in dkim):
		out.append({"why": "dkim", "domain": domain})
	return out


def of_sender(headers, sender: str, name: str | None, known) -> list[dict]:
	"""What the sender's own lines say: replies going elsewhere, a name that
	holds another address, a domain imitating a known one, a domain in
	another alphabet. Pure."""
	sender = (sender or "").strip().lower()
	domain = sender.rsplit("@", 1)[-1]
	out = []
	replies = [address.lower() for _, address in getaddresses([str(headers.get("Reply-To") or "")]) if "@" in address] if headers is not None else []
	elsewhere = next((one for one in replies if not _aligned(one.rsplit("@", 1)[-1], domain)), None)
	if elsewhere:
		out.append({"why": "reply_to", "to": elsewhere})
	shown = next((one.lower() for one in ADDRESS.findall(name or "") if one.lower() != sender), None)
	if shown:
		out.append({"why": "name", "shows": shown, "from": sender})
	copied = lookalike.imitates(domain, known)
	if copied:
		out.append({"why": "lookalike", "domain": domain, "of": copied})
	elif lookalike.foreign(domain):
		out.append({"why": "foreign", "domain": lookalike.unicode_of(domain)})
	return out


def score(found: list[dict]) -> int:
	"""The signals' weights, each kind once, at most MOST. Pure."""
	return min(MOST, sum(WEIGHTS.get(kind, 0) for kind in {one["why"] for one in found}))


def signals(headers, sender: str, name: str | None, html: str | None, text: str | None, attachments, known) -> list[dict]:
	"""Every signal a message gives, the weightiest first. Pure."""
	found = (
		of_authentication(headers, sender)
		+ of_sender(headers, sender, name, known)
		+ of_links(links(html, text if not html else None))
		+ of_files(attachments)
	)
	return sorted(found, key=lambda one: -WEIGHTS.get(one["why"], 0))


def of(arrival) -> list[dict]:
	"""The signals of a message arriving (inbound.Arrival)."""
	sender = parseaddr(arrival.decode_email(arrival.mail.get("From")) or "")[1] or arrival.from_email or ""
	return signals(
		arrival.mail,
		sender,
		arrival.from_real_name,
		arrival.html_content,
		arrival.text_content,
		[(one.get("fname") or "", one.get("fcontent") or b"") for one in arrival.attachments or []],
		lookalike.known(),
	)


def words(one: dict) -> str:
	"""A signal in plain words, as the message's warning says it."""
	why = one.get("why")
	said = {
		"dmarc": lambda: _("{0} says it didn't send this message.").format(one.get("domain")),
		"spf": lambda: _("It came from a server {0} doesn't send from.").format(one.get("domain")),
		"spf_soft": lambda: _("It came from a server {0} may not send from.").format(one.get("domain")),
		"dkim": lambda: _("Its signature from {0} doesn't match, so it may have been changed.").format(one.get("domain")),
		"reply_to": lambda: _("Replies go to {0}, not to the sender.").format(one.get("to")),
		"name": lambda: _("The sender's name shows {0}, but it came from {1}.").format(one.get("shows"), one.get("from")),
		"link_shown": lambda: _("A link shows {0} but opens {1}.").format(one.get("shows"), one.get("opens")),
		"link_ip": lambda: _("A link opens a numbered address, {0}, not a website's name.").format(one.get("opens")),
		"link_short": lambda: _("A link hides where it goes behind {0}.").format(one.get("via")),
		"program": lambda: _("{0} is a program that can run on your computer.").format(one.get("file")),
		"double": lambda: _("{0} hides what kind of file it is.").format(one.get("file")),
		"archive": lambda: _("{0} holds {1}, which can run code when opened.").format(one.get("file"), one.get("holds")),
		"macro": lambda: _("{0} can run macros when it's opened.").format(one.get("file")),
		"lookalike": lambda: _("It's from {0}, which looks like {1} but isn't.").format(one.get("domain"), one.get("of")),
		"foreign": lambda: _("It's from {0}, written with letters from another alphabet.").format(one.get("domain")),
		"phishing": lambda: _("{0} read it as phishing.").format(registry.name("one_ai")),
		"spam": lambda: _("{0} read it as spam.").format(registry.name("one_ai")),
	}.get(why)
	return said() if said else ""
