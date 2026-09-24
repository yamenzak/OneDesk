"""Servers as folders: an SFTP or WebDAV server shown in OneCloud.

A `Cloud Mount` is where a server is, who signs in to it and as whom, and who
in the workspace may open it. Under **Network** it is a folder like any
other: its contents are listed live from the server each time it is opened,
and nothing is copied into File unless somebody copies it — so a mount is a
window onto the server, not a sync.

**Node ids** are `@mount/<mount>/<path on the server>`, so the explorer's
verbs reach here through `api` without knowing what is behind them. Within a
server, rename and move are the server's own; between a server and OneCloud,
a move is a copy, the way it is between a record and a folder. Deleting on a
server is deleting on the server: there is no bin there to put it in.

**Who may**: a mount is its maker's unless a Workspace Administrator has
shared it with everyone on the team, and then every member of staff reads and
writes it with the credentials it was made with. So only an administrator
shares one, and the credentials are never sent to a browser.

**Where it may point**: not at this server or the network it sits in. A
mount is the workspace fetching an address somebody typed, so an address
that resolves to a private, loopback or link-local address is refused
(`reachable`), unless the bench says otherwise (`onestorage_mounts_private`,
for a developer's own machine).
"""

import io
import ipaddress
import mimetypes
import posixpath
import socket
import stat
from urllib.parse import quote, unquote, urlparse
from xml.etree import ElementTree

import frappe
import requests
from frappe import _
from frappe.utils import now_datetime
from werkzeug.wrappers import Response

from onedesk.one import roles
from onedesk.one_storage import namespace as ns

PREFIX = "@mount"

#: How long to wait on a server.
PATIENCE = 30


# ------------------------------------------------------------ node ids


def node_id(mount: str, path: str = "") -> str:
	path = path.strip("/")
	return f"{PREFIX}/{mount}/{path}" if path else f"{PREFIX}/{mount}"


def split(node: str) -> tuple[str, str]:
	"""(mount, path) of a mount node id. Pure."""
	rest = node[len(PREFIX) + 1 :]
	mount, _sep, path = rest.partition("/")
	return mount, "/".join(part for part in path.split("/") if part and part not in (".", ".."))


def is_mount(node: str | None) -> bool:
	return bool(node) and node.startswith(PREFIX + "/")


def join(root: str, path: str) -> str:
	"""A server path under the mount's own folder, which it cannot climb out
	of. Pure."""
	clean = posixpath.normpath("/" + (path or "")).lstrip("/")
	return posixpath.join(root or "/", clean) if clean and clean != "." else (root or "/")


# ------------------------------------------------------------ who may


def _mount(name: str):
	if not frappe.db.exists("Cloud Mount", name):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	return frappe.get_doc("Cloud Mount", name)


def may(doc, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator" or doc.owner == user:
		return True
	return bool(doc.shared) and ns._staff(user)


def _manages(doc) -> bool:
	user = frappe.session.user
	return user == "Administrator" or doc.owner == user or roles.ADMINISTRATOR in frappe.get_roles()


def _need(node: str):
	mount, path = split(node)
	doc = _mount(mount)
	if not may(doc):
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	return doc, path


def reachable(host: str) -> None:
	"""Refuse a server that is this machine or its private network."""
	if frappe.conf.get("onestorage_mounts_private"):
		return
	try:
		found = {info[4][0] for info in socket.getaddrinfo(host, None)}
	except socket.gaierror:
		frappe.throw(_("There is no server called {0}.").format(host))
	for address in found:
		ip = ipaddress.ip_address(address.split("%")[0])
		if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
			frappe.throw(_("{0} is on a private network, which OneCloud does not connect to.").format(host))


# ------------------------------------------------------------ the servers


class SFTP:
	"""A server over SSH, through paramiko."""

	def __init__(self, doc):
		import paramiko

		reachable(doc.host)
		self.root = doc.root_path or "/"
		self.transport = paramiko.Transport((doc.host, int(doc.port or 22)))
		self.transport.banner_timeout = PATIENCE
		key = doc.get_password("private_key", raise_exception=False)
		if key:
			pkey = _private_key(key)
			self.transport.connect(username=doc.username, pkey=pkey)
		else:
			self.transport.connect(username=doc.username, password=doc.get_password("password", raise_exception=False))
		self.sftp = paramiko.SFTPClient.from_transport(self.transport)
		self.sftp.get_channel().settimeout(PATIENCE)

	def close(self):
		self.sftp.close()
		self.transport.close()

	def list(self, path: str) -> list[dict]:
		return [
			{
				"name": one.filename,
				"folder": stat.S_ISDIR(one.st_mode or 0),
				"size": one.st_size or 0,
				"modified": _from_epoch(one.st_mtime),
			}
			for one in self.sftp.listdir_attr(join(self.root, path))
			if one.filename not in (".", "..")
		]

	def read(self, path: str) -> bytes:
		with self.sftp.open(join(self.root, path), "rb") as handle:
			return handle.read()

	def write(self, path: str, content: bytes) -> None:
		with self.sftp.open(join(self.root, path), "wb") as handle:
			handle.write(content)

	def make_folder(self, path: str) -> None:
		self.sftp.mkdir(join(self.root, path))

	def remove(self, path: str, folder: bool) -> None:
		full = join(self.root, path)
		if not folder:
			return self.sftp.remove(full)
		for one in self.list(path):
			self.remove(posixpath.join(path, one["name"]), one["folder"])
		self.sftp.rmdir(full)

	def rename(self, path: str, to: str) -> None:
		self.sftp.rename(join(self.root, path), join(self.root, to))


def _private_key(text: str):
	import paramiko

	for kind in (paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey):
		try:
			return kind.from_private_key(io.StringIO(text))
		except Exception:
			continue
	frappe.throw(_("That private key could not be read."))


class WebDAV:
	"""A server over WebDAV, through plain HTTP requests."""

	def __init__(self, doc):
		base = (doc.url or "").rstrip("/")
		reachable(urlparse(base).hostname or "")
		self.base = base + ("/" + doc.root_path.strip("/") if doc.root_path and doc.root_path != "/" else "")
		self.session = requests.Session()
		self.session.auth = (doc.username or "", doc.get_password("password", raise_exception=False) or "")
		self.session.max_redirects = 3

	def close(self):
		self.session.close()

	def _url(self, path: str) -> str:
		clean = posixpath.normpath("/" + (path or "")).lstrip("/")
		return self.base + "/" + quote(clean if clean != "." else "")

	def _ask(self, method: str, path: str, **kw):
		answer = self.session.request(method, self._url(path), timeout=PATIENCE, **kw)
		if answer.status_code >= 400:
			frappe.throw(_("The server said {0}.").format(f"{answer.status_code} {answer.reason}"))
		return answer

	def list(self, path: str) -> list[dict]:
		answer = self._ask("PROPFIND", path.rstrip("/") + "/", headers={"Depth": "1"})
		return parse_propfind(answer.content, urlparse(self._url(path.rstrip("/") + "/")).path)

	def read(self, path: str) -> bytes:
		return self._ask("GET", path).content

	def write(self, path: str, content: bytes) -> None:
		kind = mimetypes.guess_type(path)[0] or "application/octet-stream"
		self._ask("PUT", path, data=content, headers={"Content-Type": kind})

	def make_folder(self, path: str) -> None:
		self._ask("MKCOL", path.rstrip("/") + "/")

	def remove(self, path: str, folder: bool) -> None:
		self._ask("DELETE", path.rstrip("/") + ("/" if folder else ""))

	def rename(self, path: str, to: str) -> None:
		self._ask("MOVE", path, headers={"Destination": self._url(to), "Overwrite": "F"})


def parse_propfind(xml: bytes, here: str) -> list[dict]:
	"""A PROPFIND answer as entries, leaving out the folder asked about. Pure."""
	space = {"d": "DAV:"}
	found = []
	here = unquote(here).rstrip("/")
	for response in ElementTree.fromstring(xml).findall("d:response", space):
		href = unquote(urlparse(response.findtext("d:href", default="", namespaces=space)).path).rstrip("/")
		if href == here or not href:
			continue
		prop = response.find("d:propstat/d:prop", space)
		folder = prop is not None and prop.find("d:resourcetype/d:collection", space) is not None
		size = prop.findtext("d:getcontentlength", default="0", namespaces=space) if prop is not None else "0"
		modified = prop.findtext("d:getlastmodified", default="", namespaces=space) if prop is not None else ""
		found.append(
			{
				"name": href.rsplit("/", 1)[-1],
				"folder": folder,
				"size": int(size) if str(size).isdigit() else 0,
				"modified": _from_http_date(modified),
			}
		)
	return found


def _from_epoch(value) -> str | None:
	if not value:
		return None
	from datetime import datetime

	return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")


def _from_http_date(value: str) -> str | None:
	from email.utils import parsedate_to_datetime

	try:
		return parsedate_to_datetime(value).strftime("%Y-%m-%d %H:%M:%S")
	except Exception:
		return None


def connect(doc):
	return SFTP(doc) if doc.protocol == "SFTP" else WebDAV(doc)


class _Open:
	"""A server connection for the length of a `with`, closed either way."""

	def __init__(self, doc):
		self.doc = doc

	def __enter__(self):
		try:
			self.server = connect(self.doc)
		except frappe.ValidationError:
			raise
		except Exception as error:
			frappe.throw(_("Could not reach {0}: {1}").format(self.doc.title, str(error) or type(error).__name__))
		return self.server

	def __exit__(self, *exc):
		try:
			self.server.close()
		except Exception:
			pass
		return False


# ------------------------------------------------------------ what the explorer asks


def visible() -> list[dict]:
	"""Network: the servers the reader may open."""
	user = frappe.session.user
	rows = frappe.get_all(
		"Cloud Mount", fields=["name", "title", "protocol", "owner", "shared", "modified"], order_by="title asc"
	)
	return [
		{
			"id": node_id(one.name),
			"name": one.title,
			"folder": True,
			"virtual": True,
			"mount": True,
			"icon": "server",
			"modified": one.modified,
			"where": one.protocol,
		}
		for one in rows
		if user == "Administrator" or one.owner == user or (one.shared and ns._staff(user))
	]


def children(node: str) -> list[dict]:
	doc, path = _need(node)
	with _Open(doc) as server:
		try:
			found = server.list(path)
		except frappe.ValidationError:
			raise
		except Exception as error:
			frappe.throw(_("Could not open {0}: {1}").format(path or doc.title, str(error) or type(error).__name__))
	frappe.db.set_value("Cloud Mount", doc.name, {"last_checked": now_datetime(), "last_error": None}, update_modified=False)
	found.sort(key=lambda one: (not one["folder"], one["name"].lower()))
	return [_node(doc.name, posixpath.join(path, one["name"]), one) for one in found]


def _node(mount: str, path: str, one: dict) -> dict:
	item = node_id(mount, path)
	return {
		"id": item,
		"name": one["name"],
		"folder": one["folder"],
		"size": one.get("size") or 0,
		"modified": one.get("modified"),
		"url": None if one["folder"] else f"/api/method/onedesk.one_storage.mounts.get?node={quote(item, safe='')}",
		"remote": True,
	}


def trail(node: str) -> list[dict]:
	mount, path = split(node)
	title = frappe.db.get_value("Cloud Mount", mount, "title") or mount
	crumbs = [{"id": ns.ROOT, "name": _("OneCloud")}, {"id": ns.MOUNTS, "name": _("Network")}, {"id": node_id(mount), "name": title}]
	walked = ""
	for part in path.split("/") if path else []:
		walked = posixpath.join(walked, part)
		crumbs.append({"id": node_id(mount, walked), "name": part})
	return crumbs


@frappe.whitelist(methods=["GET", "HEAD"])
def get(node: str, download: int = 0):
	"""A file on a server, read through the workspace."""
	doc, path = _need(node)
	with _Open(doc) as server:
		content = server.read(path)
	name = posixpath.basename(path)
	from onedesk.one_admin.storage import disposition

	return Response(
		content,
		mimetype=mimetypes.guess_type(name)[0] or "application/octet-stream",
		headers={"Content-Disposition": disposition(name, inline=not int(download))},
	)


def read(node: str) -> tuple[str, bytes]:
	doc, path = _need(node)
	with _Open(doc) as server:
		return posixpath.basename(path), server.read(path)


def write(node: str, name: str, content: bytes) -> dict:
	"""A file put into a folder on a server."""
	doc, path = _need(node)
	name = " ".join((name or "file").replace("/", " ").split())
	with _Open(doc) as server:
		server.write(posixpath.join(path, name), content)
	return _node(doc.name, posixpath.join(path, name), {"name": name, "folder": False, "size": len(content)})


def make_folder(node: str, name: str) -> dict:
	doc, path = _need(node)
	name = " ".join((name or "").replace("/", " ").split())
	with _Open(doc) as server:
		taken = {one["name"] for one in server.list(path)}
		name = ns.unique_name(name, taken)
		server.make_folder(posixpath.join(path, name))
	return _node(doc.name, posixpath.join(path, name), {"name": name, "folder": True})


def rename(node: str, name: str) -> dict:
	doc, path = _need(node)
	if not path:
		frappe.throw(_("Rename the connection instead."))
	name = " ".join((name or "").replace("/", " ").split())
	to = posixpath.join(posixpath.dirname(path), name)
	with _Open(doc) as server:
		server.rename(path, to)
	return _node(doc.name, to, {"name": name, "folder": False})


def move_within(node: str, target: str) -> str:
	doc, path = _need(node)
	_mount_target, into = split(target)
	to = posixpath.join(into, posixpath.basename(path))
	with _Open(doc) as server:
		server.rename(path, to)
	return node_id(doc.name, to)


def delete(nodes: list) -> int:
	"""Off the server, for good: a server has no bin to put it in."""
	gone = 0
	for node in nodes:
		doc, path = _need(node)
		if not path:
			frappe.throw(_("Disconnect the server instead."))
		with _Open(doc) as server:
			above = {one["name"]: one["folder"] for one in server.list(posixpath.dirname(path))}
			server.remove(path, bool(above.get(posixpath.basename(path))))
		gone += 1
	return gone


# ------------------------------------------------------------ connections


@frappe.whitelist(methods=["POST"])
def save(values: str | dict, name: str | None = None) -> dict:
	"""Make or change a connection, and open it once to be sure it works."""
	values = frappe.parse_json(values) if isinstance(values, str) else values
	if not ns._staff(frappe.session.user):
		frappe.throw(_("Only people on the team can connect a server."), frappe.PermissionError)
	doc = frappe.get_doc("Cloud Mount", name) if name else frappe.new_doc("Cloud Mount")
	if name and not _manages(doc):
		frappe.throw(_("Only whoever connected {0} can change it.").format(doc.title), frappe.PermissionError)
	for field in ("title", "protocol", "host", "port", "url", "username", "root_path", "shared"):
		if field in values:
			doc.set(field, values.get(field))
	for secret in ("password", "private_key"):
		if values.get(secret):
			doc.set(secret, values[secret])
	doc.flags.ignore_permissions = True
	doc.save()
	with _Open(doc) as server:
		server.list("")
	return {"id": node_id(doc.name), "name": doc.title}


@frappe.whitelist()
@frappe.read_only()
def settings(node: str) -> dict:
	"""What the connection dialog shows: everything but the secrets."""
	doc, _path = _need(node)
	return {
		"name": doc.name,
		"can_manage": _manages(doc),
		"values": {field: doc.get(field) for field in ("title", "protocol", "host", "port", "url", "username", "root_path", "shared")},
	}


@frappe.whitelist(methods=["POST"])
def disconnect(node: str) -> None:
	doc, _path = _need(node)
	if not _manages(doc):
		frappe.throw(_("Only whoever connected {0} can remove it.").format(doc.title), frappe.PermissionError)
	frappe.delete_doc("Cloud Mount", doc.name, ignore_permissions=True)

