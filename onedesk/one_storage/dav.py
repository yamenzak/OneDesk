"""OneCloud as a network drive: WebDAV, served from inside Frappe.

Windows (Map network drive), macOS (Connect to Server), Linux file managers,
and apps like Cyberduck all speak WebDAV. `/api/method/<name>/<anything>`
reaches a whitelisted function with the rest of the path left alone, and the
function may accept any HTTP method and return a response of its own — so
PROPFIND, MKCOL, MOVE and LOCK reach `serve`, which hands the request to
wsgidav (MIT) and gives back what it answers. There is no second process and
no second port.

**A drive has passwords of its own.** A person signs in with their email and
a drive password (`make_password`), one per computer, each shown once and
taken away on its own. It opens the drive and nothing else: `sign_in` is a
before_request hook that looks only at requests under the drive's address,
checks the password, signs the person in, and removes the header before
Frappe's own API-key check would refuse it. Anywhere else the same
password is just a wrong API key. A drive password is sixteen random
letters, so it is stored as a SHA-256 — a slow hash is for passwords people
choose, and every request a drive makes is checked. A request without one
gets a 401 asking for Basic, which is what makes the client ask.

**Every verb is the explorer's.** The provider below walks node ids with
`namespace.children`, and creates, renames, moves, copies and deletes with
`api` and `upload`, so a drive can do exactly what the explorer can, as the
same person, under the same `namespace.may`. Writing a file whose name is
there replaces it and keeps a version; deleting sends it to the Recycle Bin.

**A folder as its own drive** is the same URL with the folder's path after
it; clients mount any collection.
"""

import io
import os
import tempfile
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import get_datetime
from werkzeug.wrappers import Response

from onedesk.one_storage import api, store
from onedesk.one_storage import namespace as ns

MOUNT = "/api/method/onedesk.one_storage.dav.serve"

#: Every method a WebDAV client sends, besides the ones Frappe answers itself.
METHODS = [
	"GET", "HEAD", "PUT", "DELETE", "PROPFIND", "PROPPATCH", "MKCOL", "COPY", "MOVE", "LOCK", "UNLOCK", "POST",
]  # fmt: skip

#: Methods after which the database is kept. Frappe commits for POST, PUT,
#: DELETE and PATCH on its own and rolls everything else back.
CHANGES = frozenset(("MKCOL", "COPY", "MOVE", "PROPPATCH", "LOCK", "UNLOCK"))

#: What a drive shows at its top: the places with files of their own, not the
#: views over them (Recent, Starred) or the bin.
TOP = (ns.MY, ns.SHARED, ns.LIBRARIES, ns.COMPANY, ns.RECORDS)

#: What macOS and Windows write beside every file they touch.
LITTER = (".DS_Store", "Thumbs.db", "desktop.ini")


def litter(name: str) -> bool:
	"""Whether a name is an operating system's own bookkeeping. Pure."""
	return name in LITTER or name.startswith("._") or name.startswith("~$")


def split(path: str) -> list[str]:
	"""A DAV path's names, without empty parts or parent steps. Pure."""
	return [part for part in (path or "").strip("/").split("/") if part and part not in (".", "..")]


# ------------------------------------------------------------ the entry point


@frappe.whitelist(allow_guest=True, methods=METHODS)
def serve():
	if frappe.session.user in ("Guest", ""):
		return Response(
			status=401,
			headers={"WWW-Authenticate": 'Basic realm="OneCloud", charset="UTF-8"'},
		)
	request = frappe.request
	environ = dict(request.environ)
	environ["SCRIPT_NAME"] = MOUNT
	environ["PATH_INFO"] = request.path[len(MOUNT) :] or "/"
	# Frappe has read the whole body already (make_form_dict), so it is taken
	# from werkzeug's cache rather than a stream somebody has emptied.
	body = request.get_data(cache=True)
	environ["wsgi.input"] = io.BytesIO(body)
	environ["CONTENT_LENGTH"] = str(len(body))
	environ["wsgidav.auth.user_name"] = frappe.session.user
	environ["wsgidav.auth.realm"] = "OneCloud"
	environ["wsgidav.auth.roles"] = []
	environ["wsgidav.auth.permissions"] = []

	answer = {}

	def start_response(status, headers, exc_info=None):
		answer["status"], answer["headers"] = status, headers

	body = _app()(environ, start_response)
	# wsgidav says its status when its body is first read, not before.
	chunks = iter(body)
	first = next(chunks, b"")
	if request.method in CHANGES:
		frappe.local.flags.commit = True

	def rest():
		try:
			yield first
			yield from chunks
		finally:
			if hasattr(body, "close"):
				body.close()

	return Response(rest(), status=answer.get("status", "500"), headers=answer.get("headers", []), direct_passthrough=True)


def headers(response, request) -> None:
	"""after_request: what a client looks for on OPTIONS, which Frappe answers
	before any method runs, and on a 401, which is how it knows to ask. Set
	through response_headers, which Frappe applies last — after it has
	offered OAuth on a 401, which a drive cannot answer."""
	if not request.path.startswith(MOUNT):
		return
	extra = frappe.local.response_headers
	if request.method == "OPTIONS":
		# Frappe cannot sign anybody in on OPTIONS, and refuses credentials it
		# cannot use; macOS sends them anyway. OPTIONS only says what the
		# server speaks, so it is answered for anybody.
		if response is not None and response.status_code == 401:
			response.status_code = 200
			response.set_data(b"")
		extra["DAV"] = "1, 2"
		extra["MS-Author-Via"] = "DAV"
		extra["Allow"] = ", ".join(["OPTIONS", *METHODS])
	if response is not None and response.status_code == 401:
		extra["WWW-Authenticate"] = 'Basic realm="OneCloud", charset="UTF-8"'


_apps: dict = {}


def _app():
	"""One wsgidav app per site, since locks are kept per site."""
	site = frappe.local.site
	if site not in _apps:
		from wsgidav.wsgidav_app import WsgiDAVApp

		_apps[site] = WsgiDAVApp(
			{
				"mount_path": MOUNT,
				"provider_mapping": {"/": Provider()},
				"http_authenticator": {
					"domain_controller": "onedesk.one_storage.dav.FrappeSignIn",
					"accept_basic": True,
					"accept_digest": False,
					"default_to_digest": False,
				},
				"lock_storage": _locks(site),
				"property_manager": True,
				"hotfixes": {"emulate_win32_lastmod": True, "re_encode_path_info": True, "unquote_path_info": False},
				"dir_browser": {"enable": False},
				"add_header_MS_Author_Via": True,
				"suppress_version_info": True,
				"verbose": 1,
				"logging": {"enable": False, "enable_loggers": []},
			}
		)
	return _apps[site]


def _locks(site: str):
	"""Locks in Frappe's own cache, under this site's name, so every worker
	sees a lock another took."""
	import redis
	from wsgidav.lock_man.lock_storage_redis import LockStorageRedis

	class SiteLocks(LockStorageRedis):
		def __init__(self):
			super().__init__()
			self._redis_prefix = "wsgidav-" + site + "-{}"
			self._redis_lock_prefix = self._redis_prefix.format("lock:{}")
			self._redis_url2token_prefix = self._redis_prefix.format("URL2TOKEN:{}")

		def open(self):
			self._redis = redis.Redis.from_url(frappe.conf.redis_cache or "redis://127.0.0.1:13000")

	return SiteLocks()


def _signin_base():
	from wsgidav.dc.base_dc import BaseDomainController

	return BaseDomainController


class FrappeSignIn(_signin_base()):
	"""Frappe has signed the person in before wsgidav sees the request; this
	only tells wsgidav so."""

	def __init__(self, wsgidav_app, config):
		super().__init__(wsgidav_app, config)

	def __str__(self):
		return "FrappeSignIn"

	def get_domain_realm(self, path_info, environ):
		return "OneCloud"

	def require_authentication(self, realm, environ):
		return False

	def basic_auth_user(self, realm, user_name, password, environ):
		return False

	def supports_http_digest_auth(self):
		return False


# ------------------------------------------------------------ the passwords


#: How a drive password looks: four groups of four letters, typed easily into
#: a Connect to Server box. About 75 bits.
GROUPS, LETTERS = 4, "abcdefghijkmnopqrstuvwxyz"


def hashed(password: str) -> str:
	import hashlib

	return hashlib.sha256((password or "").encode()).hexdigest()


def basic(header: str | None) -> tuple[str, str] | None:
	"""(user name, password) from a Basic Authorization header. Pure."""
	import base64
	import binascii

	kind, _sep, token = (header or "").partition(" ")
	if kind.lower() != "basic" or not token:
		return None
	try:
		name, colon, password = base64.b64decode(token.strip()).decode().partition(":")
	except (binascii.Error, UnicodeDecodeError, ValueError):
		return None
	return (name, password) if colon else None


def sign_in() -> None:
	"""before_request: a drive password, on the drive's address only.

	A user name with an @ is an email, which an API key never is, so a drive
	password and an API key cannot be mistaken for each other. A wrong one is
	left alone, and Frappe answers it as the wrong API key it looks like."""
	request = getattr(frappe.local, "request", None)
	if not request or not request.path.startswith(MOUNT):
		return
	found = basic(request.headers.get("Authorization"))
	if not found or "@" not in found[0]:
		return
	email, password = found
	row = frappe.db.get_value(
		"Cloud Drive Password", {"password_hash": hashed(password)}, ["name", "user", "last_used"], as_dict=True
	)
	if not row or row.user.lower() != email.strip().lower():
		return
	if not frappe.db.get_value("User", {"name": row.user, "enabled": 1, "user_type": "System User"}):
		return
	form = frappe.local.form_dict
	frappe.set_user(row.user)
	frappe.local.form_dict = form
	request.environ.pop("HTTP_AUTHORIZATION", None)
	# A drive asks many times a minute; when it was last used is kept to ten.
	now = frappe.utils.now_datetime()
	if not row.last_used or (now - get_datetime(row.last_used)).total_seconds() > 600:
		frappe.db.set_value("Cloud Drive Password", row.name, "last_used", now, update_modified=False)
		frappe.local.flags.commit = True


@frappe.whitelist(methods=["POST"])
def make_password(label: str | None = None) -> dict:
	"""A new drive password for the reader, shown this once."""
	import secrets

	user = frappe.session.user
	if not ns._staff(user):
		frappe.throw(_("Only people on the team can connect a drive."), frappe.PermissionError)
	password = "-".join("".join(secrets.choice(LETTERS) for _ in range(4)) for _ in range(GROUPS))
	frappe.get_doc(
		{
			"doctype": "Cloud Drive Password",
			"user": user,
			"label": (label or "").strip()[:140] or _("A drive"),
			"password_hash": hashed(password),
		}
	).insert(ignore_permissions=True)
	return {"user_name": user, "password": password}


@frappe.whitelist()
@frappe.read_only()
def passwords() -> list[dict]:
	"""The reader's drive passwords: what each was for and when it was used."""
	return frappe.get_all(
		"Cloud Drive Password",
		filters={"user": frappe.session.user},
		fields=["name", "label", "creation", "last_used"],
		order_by="creation desc",
	)


@frappe.whitelist(methods=["POST"])
def drop_password(name: str) -> None:
	"""Take one away: that computer is asked to sign in again."""
	if frappe.db.get_value("Cloud Drive Password", name, "user") != frappe.session.user:
		frappe.throw(_("That is no longer here."), frappe.DoesNotExistError)
	frappe.delete_doc("Cloud Drive Password", name, ignore_permissions=True)


# ------------------------------------------------------------ the provider


def _provider_base():
	from wsgidav.dav_provider import DAVCollection, DAVNonCollection, DAVProvider

	return DAVProvider, DAVCollection, DAVNonCollection


_DAVProvider, _DAVCollection, _DAVNonCollection = _provider_base()


def _error(code: int):
	from wsgidav.dav_error import DAVError

	return DAVError(code)


class Provider(_DAVProvider):
	def __init__(self):
		super().__init__()

	def is_readonly(self):
		return False

	def get_resource_inst(self, path, environ):
		item = walk(path)
		if item is None:
			return None
		if item.get("folder"):
			return Folder(path, environ, item)
		return Document(path, environ, item)


def walk(path: str) -> dict | None:
	"""The node a DAV path names, through the same listings the explorer
	draws; None where there is nothing, or nothing the reader may see."""
	held = _request_cache()
	if path in held:
		return held[path]
	node = {"id": ns.ROOT, "name": "", "folder": True, "virtual": True}
	for part in split(path):
		found = None
		for one in _children(node["id"]):
			if part in (one["name"], one["id"].rsplit("/", 1)[-1]):
				found = one
				break
		if not found:
			held[path] = None
			return None
		node = found
	held[path] = node
	return node


def _children(node_id: str) -> list[dict]:
	if node_id == ns.ROOT:
		return [one for one in ns.roots() if one["id"] in TOP]
	return ns.children(node_id)


def _request_cache() -> dict:
	held = getattr(frappe.local, "onecloud_dav", None)
	if held is None:
		held = {}
		frappe.local.onecloud_dav = held
	return held


def _forget() -> None:
	frappe.local.onecloud_dav = {}
	ns.forget()


def _parent_and_name(path: str) -> tuple[str, str]:
	parts = split(path)
	return "/" + "/".join(parts[:-1]), parts[-1] if parts else ""


def _stamp(value) -> float | None:
	return get_datetime(value).timestamp() if value else None


def _place_for(dest_path: str) -> tuple[dict, str]:
	"""Where a MOVE or COPY lands: the folder it goes into, and its name."""
	parent_path, name = _parent_and_name(dest_path)
	parent = walk(parent_path)
	if not parent or not parent.get("folder"):
		raise _error(409)
	return parent, name


def _move_or_copy(item: dict, dest_path: str, is_move: bool) -> None:
	parent, name = _place_for(dest_path)
	here = frappe.db.get_value("File", item["id"], "folder") if not item.get("virtual") else None
	try:
		if is_move and here == ns.folder_of(parent["id"]):
			api.rename(item["id"], name)
		elif is_move:
			moved = api.move([item["id"]], parent["id"])
			if moved and name != item["name"]:
				api.rename(moved[0], name)
		else:
			made = api.copy([item["id"]], parent["id"])
			if made and name != item["name"]:
				api.rename(made[0], name)
	except frappe.PermissionError:
		raise _error(403) from None
	except frappe.ValidationError:
		raise _error(409) from None
	_forget()


class Folder(_DAVCollection):
	def __init__(self, path, environ, item):
		super().__init__(path, environ)
		self.item = item

	def get_display_name(self):
		return self.item.get("name") or "OneCloud"

	def get_creation_date(self):
		return _stamp(self.item.get("modified"))

	def get_last_modified(self):
		return _stamp(self.item.get("modified"))

	def get_etag(self):
		return None

	def support_etag(self):
		return False

	def get_member_names(self):
		return [one["name"] for one in _children(self.item["id"]) if not litter(one["name"])]

	def get_member(self, name):
		return self.provider.get_resource_inst(self.path.rstrip("/") + "/" + name, self.environ)

	def create_empty_resource(self, name):
		if litter(name):
			raise _error(403)
		if not ns.folder_of(self.item["id"]) and not self.item["id"].startswith(ns.RECORDS + "/"):
			raise _error(403)
		return Document(self.path.rstrip("/") + "/" + name, self.environ, {"id": None, "name": name, "parent": self.item})

	def create_collection(self, name):
		if litter(name):
			raise _error(403)
		try:
			api.make_folder(self.item["id"], name)
		except frappe.PermissionError:
			raise _error(403) from None
		except frappe.ValidationError:
			raise _error(409) from None
		_forget()

	def delete(self):
		self._delete()

	def _delete(self):
		if self.item.get("virtual") or self.item.get("id") in (None, ns.ROOT):
			raise _error(403)
		try:
			api.delete([self.item["id"]])
		except frappe.PermissionError:
			raise _error(403) from None
		_forget()

	def support_recursive_delete(self):
		return True

	def support_recursive_move(self, dest_path):
		return True

	def move_recursive(self, dest_path):
		_move_or_copy(self.item, dest_path, True)

	def copy_move_single(self, dest_path, *, is_move):
		_move_or_copy(self.item, dest_path, is_move)


class Document(_DAVNonCollection):
	def __init__(self, path, environ, item):
		super().__init__(path, environ)
		self.item = item
		self._spool = None

	def get_content_length(self):
		return int(self.item.get("size") or 0)

	def get_content_type(self):
		import mimetypes

		return mimetypes.guess_type(self.item.get("name") or "")[0] or "application/octet-stream"

	def get_creation_date(self):
		return _stamp(self.item.get("modified"))

	def get_last_modified(self):
		return _stamp(self.item.get("modified"))

	def get_display_name(self):
		return self.item.get("name")

	def support_etag(self):
		return True

	def get_etag(self):
		return f"{self.item.get('id')}-{int(_stamp(self.item.get('modified')) or 0)}-{self.item.get('size') or 0}"

	def support_ranges(self):
		return False

	def get_content(self):
		url = self.item.get("url") or ""
		if store.is_stored(url):
			import requests

			answer = requests.get(store.signed(store.key_of(url)), stream=True, timeout=store.PATIENCE)
			answer.raise_for_status()
			answer.raw.decode_content = True
			return answer.raw
		doc = frappe.get_doc("File", self.item["id"])
		content = doc.get_content()
		return io.BytesIO(content if isinstance(content, bytes) else content.encode())

	def begin_write(self, *, content_type=None):
		# wsgidav closes what it wrote to before end_write, so the bytes go to
		# a file on disk that end_write reads back and removes.
		handle, self._spool = tempfile.mkstemp(prefix="onecloud-dav-")
		return os.fdopen(handle, "wb")

	def end_write(self, *, with_errors):
		"""A written file: a new one, or a new version of the one there. An
		empty file first and its content after is how Finder and Explorer
		write, and the empty one is not kept as a version."""
		from onedesk.one_storage import upload

		spool, self._spool = self._spool, None
		if spool is None:
			return
		try:
			if with_errors:
				return
			with open(spool, "rb") as written:
				content = written.read()
		finally:
			os.unlink(spool)
		parent = self.item.get("parent") or walk(_parent_and_name(self.path)[0])
		try:
			upload._place(
				parent["id"],
				None,
				{"file_name": self.item["name"], "content": content},
				replace=1,
				version_of=self.item.get("id"),
			)
		except frappe.PermissionError:
			raise _error(403) from None
		_forget()

	def delete(self):
		if not self.item.get("id"):
			raise _error(404)
		try:
			api.delete([self.item["id"]])
		except frappe.PermissionError:
			raise _error(403) from None
		_forget()

	def support_recursive_move(self, dest_path):
		return True

	def move_recursive(self, dest_path):
		_move_or_copy(self.item, dest_path, True)

	def copy_move_single(self, dest_path, *, is_move):
		_move_or_copy(self.item, dest_path, is_move)


def href(path: str) -> str:
	"""The URL of a place in the drive, quoted the way a client wants it."""
	return frappe.utils.get_url(MOUNT + quote(path if path.startswith("/") else "/" + path))


def path_of(node_id: str) -> str:
	"""The drive path of a node, from the explorer's trail."""
	crumbs = ns.trail(node_id)[1:]
	return "/" + "/".join(crumb["name"] for crumb in crumbs)


@frappe.whitelist()
@frappe.read_only()
def address(node: str = ns.MY) -> dict:
	"""The address to connect a drive to, for a folder or for everything."""
	path = "/" if node == ns.ROOT else path_of(node)
	return {"url": href(path).rstrip("/") + "/", "everything": href("/"), "user_name": frappe.session.user}

