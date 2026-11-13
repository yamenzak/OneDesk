"""A desktop app's lock on the drive is the File's lease (lease.py): a
LOCK takes the `dav` lease with the lock's token and timeout, a refresh
renews it, UNLOCK or expiry ends it. A LOCK while somebody else has the
file alone, or anybody writes in it live, is refused 423, and the file's
lock discovery names them, so Word and Excel open it read-only and say
who. AGENTS.md, Under the hood, dav_locks.py."""

from urllib.parse import unquote

import frappe
from frappe.utils import get_fullname, now_datetime

from onedesk.one_cloud import lease

LONGEST = 60 * 60
SHORTEST = 60
SEEN = "opaquelocktoken:onecloud-held"


def seconds(timeout) -> int:
	"""How long a lock and its lease last: what the app asked for, from a
	minute to an hour. Infinite and a missing timeout are an hour, so an app
	that closes without unlocking frees the file within the hour. Pure."""
	try:
		asked = float(timeout)
	except (TypeError, ValueError):
		return LONGEST
	if asked < 0:
		return LONGEST
	return int(min(max(asked, SHORTEST), LONGEST))


def owner(name: str, where: str) -> bytes:
	"""The `<owner>` of the lock an app is shown for somebody holding the file
	another way: Word reads it as "locked for editing by …". Pure."""
	from xml.sax.saxutils import escape

	return f'<D:owner xmlns:D="DAV:"><D:href>{escape(name)} ({escape(where)})</D:href></D:owner>'.encode()


def shown(why: dict | None, names: dict) -> tuple[str, str] | None:
	"""Who an app is told holds the file, from `lease.refused`, unless it is
	a lock on the drive, which wsgidav lists itself: (their name, where).
	Pure."""
	if not why or why.get("kind") == lease.DAV:
		return None
	return names.get(why["user"]) or why["user"], lease.WHERE.get(why.get("kind")) or lease.APPS.get(why.get("app")) or ""


def file_at(ref_url: str) -> str | None:
	"""The File a lock's URL names, when it names one."""
	from onedesk.one_cloud import dav

	item = dav.walk(unquote(ref_url))
	if not item or item.get("folder") or item.get("virtual") or not item.get("id"):
		return None
	return item["id"] if frappe.db.exists("File", item["id"]) else None


def refused(file: str, user: str) -> dict | None:
	"""Why `user` may not lock `file` on the drive, as `lease.refused`."""
	return lease.refused(lease.alone_of(file), lease.live_of(file), user, lease.DAV, now_datetime())


def held_lock(file: str, user: str) -> dict | None:
	"""The lock an app is shown for somebody holding `file` another way."""
	why = refused(file, user)
	found = shown(why, {why["user"]: get_fullname(why["user"])} if why else {})
	if not found:
		return None
	return {"type": "write", "scope": "exclusive", "depth": "0", "owner": owner(*found), "token": SEEN, "timeout": -1}


def discovered(found, lock: dict, href: str) -> None:
	"""`lock` added to a lockdiscovery element, as wsgidav writes its own."""
	from wsgidav import xml_tools
	from wsgidav.xml_tools import etree

	active = etree.SubElement(found, "{DAV:}activelock")
	etree.SubElement(etree.SubElement(active, "{DAV:}locktype"), "{DAV:}" + lock["type"])
	etree.SubElement(etree.SubElement(active, "{DAV:}lockscope"), "{DAV:}" + lock["scope"])
	etree.SubElement(active, "{DAV:}depth").text = lock["depth"]
	active.append(xml_tools.string_to_xml(lock["owner"]))
	etree.SubElement(active, "{DAV:}timeout").text = "Infinite"
	etree.SubElement(etree.SubElement(active, "{DAV:}locktoken"), "{DAV:}href").text = lock["token"]
	etree.SubElement(etree.SubElement(active, "{DAV:}lockroot"), "{DAV:}href").text = href


def adopt(file: str, resource) -> None:
	"""A file made under a lock its person took before it existed (Finder
	locks a name, then writes it) takes that lock as its lease."""
	import time

	manager = resource.provider.lock_manager
	if not manager or lease.holding(lease.alone_of(file), now_datetime()):
		return
	for lock in manager.get_url_lock_list(resource.get_ref_url()):
		if lock.get("principal") == frappe.session.user:
			left = seconds(float(lock.get("expire") or 0) - time.time())
			lease.take(file, lease.DAV, frappe.session.user, left, lock=lock["token"])
			return


def locked(why: dict, user: str):
	from wsgidav.dav_error import HTTP_LOCKED, DAVError

	said = lease.said(why, user)
	return DAVError(HTTP_LOCKED, context_info=f"{said['by'] or get_fullname(user)} ({said['where']})")


def joined(file: str, lock: dict) -> None:
	"""The lease for a lock just taken on `file`; refused, the lock goes and
	the LOCK is answered 423."""
	got = lease.take(file, lease.DAV, frappe.session.user, seconds(lock.get("timeout")), lock=lock["token"])
	if got.get("held"):
		raise _Refused(refused(file, frappe.session.user) or {"user": frappe.session.user})


class _Refused(Exception):
	def __init__(self, why: dict):
		super().__init__(why.get("user"))
		self.why = why


def storage(site: str):
	"""Locks in Frappe's own cache, under this site's name, so every worker
	sees a lock another took, joined to the File's lease."""
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

		def create(self, path, lock):
			lock["timeout"] = seconds(lock.get("timeout"))
			made = super().create(path, lock)
			file = file_at(made["root"])
			if not file:
				return made
			try:
				joined(file, made)
			except _Refused as no:
				super().delete(made["token"])
				raise locked(no.why, frappe.session.user) from None
			return made

		def refresh(self, token, *, timeout=None):
			lock = super().refresh(token, timeout=seconds(timeout))
			file = lease.by_lock(token)
			if not file:
				return lock
			if lease.holding(lease.alone_of(file), now_datetime()):
				lease.extend(file, token, lock["timeout"])
				return lock
			try:
				joined(file, lock)
			except _Refused as no:
				super().delete(token)
				raise locked(no.why, frappe.session.user) from None
			return lock

		def delete(self, token):
			gone = super().delete(token)
			file = lease.by_lock(token)
			if file:
				lease.release(file, token)
			return gone

	return SiteLocks()
