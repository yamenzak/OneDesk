"""Talking to an IMAP server: the protocol's details, kept in one place.

Standard library `imaplib` only, as Frappe does. What it leaves to the caller
is here, pure and tested:
- reading `LIST` lines;
- telling a folder's kind, from its RFC 6154 special-use flag or else its
  name, in the languages people's servers use;
- IMAP's modified UTF-7 folder names, both ways;
- reading `FETCH` responses into something with a uid.

`Session` is one connection, opened for one piece of work and closed. It
reports the capabilities that matter — MOVE, UIDPLUS, CONDSTORE — so a
caller can use them where a server has them and do without where it does not.
"""

import base64
import imaplib
import re
import socket
import ssl

import frappe

#: Seconds to wait on a server. A slow one must not hold a worker for long.
PATIENCE = 60

#: A LIST response line: (flags) "delimiter" name.
LISTED = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?P<delim>[^"]*)"|NIL)\s+(?P<name>.+)$')

#: RFC 6154 flags, and what each means here.
SPECIAL = {
	"\\sent": "Sent",
	"\\drafts": "Drafts",
	"\\junk": "Junk",
	"\\trash": "Trash",
	"\\archive": "Archive",
}

#: Flags on a folder that only repeats others, or holds nothing.
REPEATS = {"\\all", "\\flagged", "\\noselect", "\\nonexistent", "\\important"}

#: Names servers without special-use give these folders, lowercased, last
#: part only.
BY_NAME = {
	"Sent": {
		"sent",
		"sent items",
		"sent messages",
		"sent mail",
		"gesendet",
		"gesendete objekte",
		"المرسلة",
		"البريد المرسل",
	},
	"Drafts": {"drafts", "draft", "entwürfe", "المسودات"},
	"Junk": {"junk", "junk e-mail", "junk email", "spam", "bulk mail", "spam-verdacht", "البريد العشوائي"},
	"Trash": {
		"trash",
		"deleted items",
		"deleted messages",
		"bin",
		"papierkorb",
		"gelöschte elemente",
		"المحذوفات",
		"سلة المهملات",
	},
	"Archive": {"archive", "archives", "archiv", "الأرشيف"},
}


def parse_list(line) -> dict | None:
	"""One LIST line: {"flags", "delimiter", "path"}, the path as the server
	spells it. Pure."""
	if isinstance(line, tuple):
		# A literal name: (b'(\\HasNoChildren) "/" {12}', b'name')
		head, literal = line
		line = head.decode(errors="replace").rsplit("{", 1)[0] + '"' + literal.decode(errors="replace") + '"'
	elif isinstance(line, bytes):
		line = line.decode(errors="replace")
	found = LISTED.match(line or "")
	if not found:
		return None
	name = found.group("name").strip()
	if name.startswith('"') and name.endswith('"'):
		name = name[1:-1].replace('\\"', '"').replace("\\\\", "\\")
	flags = {one.lower() for one in found.group("flags").split()}
	return {"flags": flags, "delimiter": found.group("delim") or "", "path": name}


def kind_of(flags: set, path: str, delimiter: str = "/") -> str:
	"""Inbox, Sent, Drafts, Junk, Trash, Archive or Other. Pure."""
	if path.upper() == "INBOX":
		return "Inbox"
	for flag, kind in SPECIAL.items():
		if flag in flags:
			return kind
	last = decode(path.split(delimiter)[-1] if delimiter else path).strip().lower()
	for kind, names in BY_NAME.items():
		if last in names:
			return kind
	return "Other"


def repeats(flags: set) -> bool:
	"""Whether a folder only repeats others, or holds nothing. Pure."""
	return bool(flags & REPEATS)


def decode(name: str) -> str:
	"""IMAP's modified UTF-7 (RFC 3501 5.1.3) to text. Pure."""
	out, at = [], 0
	while at < len(name):
		start = name.find("&", at)
		if start < 0:
			out.append(name[at:])
			break
		out.append(name[at:start])
		end = name.find("-", start)
		if end < 0:
			out.append(name[start:])
			break
		chunk = name[start + 1 : end]
		if not chunk:
			out.append("&")
		else:
			padded = chunk.replace(",", "/") + "=" * (-len(chunk) % 4)
			out.append(base64.b64decode(padded).decode("utf-16-be", errors="replace"))
		at = end + 1
	return "".join(out)


def encode(text: str) -> str:
	"""Text to IMAP's modified UTF-7. Pure."""
	out, pending = [], []

	def flush():
		if pending:
			raw = "".join(pending).encode("utf-16-be")
			out.append("&" + base64.b64encode(raw).decode().rstrip("=").replace("/", ",") + "-")
			pending.clear()

	for char in text:
		if 0x20 <= ord(char) <= 0x7E:
			flush()
			out.append("&-" if char == "&" else char)
		else:
			pending.append(char)
	flush()
	return "".join(out)


def quoted(path: str) -> str:
	"""A path as a command argument. Pure."""
	return '"' + path.replace("\\", "\\\\").replace('"', '\\"') + '"'


FETCHED = re.compile(rb"UID (\d+)")
FLAGS = re.compile(rb"FLAGS \(([^)]*)\)")
MODSEQ = re.compile(rb"MODSEQ \((\d+)\)")


def parse_fetch(data: list) -> dict[int, dict]:
	"""A FETCH response as {uid: {"flags", "body", "modseq"}}. Pure."""
	out: dict[int, dict] = {}
	for part in data or []:
		head, body = (part[0], part[1]) if isinstance(part, tuple) else (part, None)
		if not isinstance(head, bytes):
			continue
		uid = FETCHED.search(head)
		if not uid:
			continue
		row = out.setdefault(int(uid.group(1)), {"flags": set(), "body": None, "modseq": None})
		flags = FLAGS.search(head)
		if flags:
			row["flags"] = {one.lower() for one in flags.group(1).decode(errors="replace").split()}
		modseq = MODSEQ.search(head)
		if modseq:
			row["modseq"] = int(modseq.group(1))
		if body is not None:
			row["body"] = body
	return out


class Session:
	"""One connection to one account's server, for one piece of work."""

	def __init__(self, account, patience: int | None = None):
		self.account = account
		self.patience = patience or PATIENCE
		self.imap = None
		self.capabilities: set[str] = set()
		self.selected = None

	def __enter__(self):
		account = self.account
		host, port = account.email_server, int(account.incoming_port or (993 if account.use_ssl else 143))
		if account.use_ssl:
			self.imap = imaplib.IMAP4_SSL(
				host, port, ssl_context=ssl.create_default_context(), timeout=self.patience
			)
		else:
			self.imap = imaplib.IMAP4(host, port, timeout=self.patience)
			if account.use_starttls:
				self.imap.starttls(ssl_context=ssl.create_default_context())
		login = account.login_id or account.email_id
		self.imap.login(login, account.get_password("password", raise_exception=False) or "")
		# Servers say more after login than before it; imaplib keeps the first.
		status, said = self.imap.capability()
		spoken = said[0] if status == "OK" and said else b""
		self.capabilities = {one.upper() for one in spoken.decode(errors="replace").split()} or {
			one.upper() for one in self.imap.capabilities
		}
		if "CONDSTORE" in self.capabilities:
			self.imap.enable("CONDSTORE")
		return self

	def __exit__(self, *exc):
		try:
			if self.imap:
				self.imap.logout()
		except (imaplib.IMAP4.error, OSError):
			pass

	def can(self, capability: str) -> bool:
		return capability.upper() in self.capabilities

	def folders(self) -> list[dict]:
		status, data = self.imap.list()
		if status != "OK":
			raise imaplib.IMAP4.error(f"LIST failed: {data}")
		return [one for one in (parse_list(line) for line in data or []) if one]

	def select(self, path: str, readonly: bool = True) -> dict:
		"""Open a folder: what the server says of it now."""
		status, data = self.imap.select(quoted(path), readonly=readonly)
		if status != "OK":
			raise imaplib.IMAP4.error(f"SELECT {path} failed: {data}")
		self.selected = path

		def number(code):
			said = self.imap.untagged_responses.get(code) or [None]
			try:
				return int(said[-1])
			except (TypeError, ValueError):
				return None

		return {
			"exists": int(data[0] or 0),
			"uidvalidity": str(number("UIDVALIDITY") or ""),
			"uidnext": number("UIDNEXT") or 0,
			"modseq": number("HIGHESTMODSEQ"),
		}

	def uids(self, criteria: str = "ALL") -> list[int]:
		status, data = self.imap.uid("SEARCH", None, criteria)
		if status != "OK":
			raise imaplib.IMAP4.error(f"SEARCH failed: {data}")
		return sorted(int(one) for one in (data[0] or b"").split())

	def fetch(self, uids: list[int], parts: str, changed_since: int | None = None) -> dict[int, dict]:
		if not uids:
			return {}
		ranges = ",".join(str(one) for one in uids)
		if changed_since is not None:
			status, data = self.imap.uid("FETCH", ranges, parts, f"(CHANGEDSINCE {changed_since})")
		else:
			status, data = self.imap.uid("FETCH", ranges, parts)
		if status != "OK":
			raise imaplib.IMAP4.error(f"FETCH failed: {data}")
		return parse_fetch(data)

	def store(self, uids: list[int], change: str, flags: str) -> None:
		if uids:
			self.imap.uid("STORE", ",".join(map(str, uids)), change, f"({flags})")

	def move(self, uids: list[int], target: str) -> dict[int, int]:
		"""Move messages; the uids they have in `target`, where the server
		says (UIDPLUS's COPYUID)."""
		if not uids:
			return {}
		ranges = ",".join(map(str, uids))
		self.imap.untagged_responses.pop("COPYUID", None)
		if self.can("MOVE"):
			status, data = self.imap.uid("MOVE", ranges, quoted(target))
		else:
			status, data = self.imap.uid("COPY", ranges, quoted(target))
			if status == "OK":
				self.store(uids, "+FLAGS.SILENT", "\\Deleted")
				if self.can("UIDPLUS"):
					self.imap.uid("EXPUNGE", ranges)
				else:
					self.imap.expunge()
		if status != "OK":
			raise imaplib.IMAP4.error(f"MOVE to {target} failed: {data}")
		# COPYUID comes untagged on a MOVE and in the tagged answer on a COPY;
		# imaplib files the untagged one under its code, without the code.
		coded = [
			b"COPYUID " + one
			for one in self.imap.untagged_responses.pop("COPYUID", [])
			if isinstance(one, bytes)
		]
		return copied(coded + list(data or []))

	def expunge(self, uids: list[int]) -> None:
		if not uids:
			return
		self.store(uids, "+FLAGS.SILENT", "\\Deleted")
		if self.can("UIDPLUS"):
			self.imap.uid("EXPUNGE", ",".join(map(str, uids)))
		else:
			self.imap.expunge()

	def append(self, path: str, raw: bytes, flags: str = "\\Seen") -> None:
		self.imap.append(quoted(path), f"({flags})", None, raw)

	def _ok(self, what: str, answer) -> None:
		status, data = answer
		if status != "OK":
			raise imaplib.IMAP4.error(f"{what} failed: {data}")

	def create(self, path: str) -> None:
		self._ok(f"CREATE {path}", self.imap.create(quoted(path)))
		self.imap.subscribe(quoted(path))

	def rename(self, path: str, to: str) -> None:
		self._ok(f"RENAME {path}", self.imap.rename(quoted(path), quoted(to)))
		self.imap.subscribe(quoted(to))

	def delete(self, path: str) -> None:
		self._ok(f"DELETE {path}", self.imap.delete(quoted(path)))


COPYUID = re.compile(rb"COPYUID \d+ ([\d:,]+) ([\d:,]+)")


def _expand(ranges: bytes) -> list[int]:
	out = []
	for part in ranges.decode().split(","):
		if ":" in part:
			low, high = (int(one) for one in part.split(":"))
			out += list(range(low, high + 1)) if low <= high else list(range(low, high - 1, -1))
		else:
			out.append(int(part))
	return out


def copied(said: list) -> dict[int, int]:
	"""Old uid to new uid, from a COPYUID response code. Pure."""
	for one in said or []:
		one = one if isinstance(one, bytes) else str(one).encode()
		found = COPYUID.search(one)
		if found:
			return dict(zip(_expand(found.group(1)), _expand(found.group(2)), strict=False))
	return {}


def refused(error: Exception) -> str:
	"""What to tell a person about a failure, without a traceback."""
	text = str(error)
	if isinstance(error, (socket.timeout, TimeoutError)):
		return frappe._("The server did not answer in time.")
	if isinstance(error, ssl.SSLError):
		return frappe._("The server's certificate could not be checked.")
	if isinstance(error, ConnectionRefusedError | socket.gaierror):
		return frappe._("The server could not be reached.")
	if "AUTHENTICATIONFAILED" in text.upper() or "LOGIN" in text.upper():
		return frappe._("The server did not accept the address and password.")
	return text[:300]
