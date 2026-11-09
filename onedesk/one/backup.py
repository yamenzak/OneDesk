"""This workspace's own backups: its database, files and config every night,
its database and config every four hours, in a turn of its own (`slot`). Each
is sent to One's locked backup bucket through the keeper and signed with the
secret OneAdmin gave it (one_admin/backups.py). The keeper adds it under this
workspace's name and nothing can delete it there."""

import hashlib
import hmac
import os
import time

import frappe
import requests

PATIENCE = 900
EVERY = 4 * 60 * 60
TICK = 5 * 60
STAMP = "%Y-%m-%dT%H%M"
LAST_TURN = "one_backup_last_turn"


def signed(secret: str, at: int, path: str) -> str:
	"""What the keeper checks an upload by. Pure."""
	return hmac.new(secret.encode(), f"{at}.{path}".encode(), hashlib.sha256).hexdigest()


def slot(slug: str) -> int:
	"""Which five minutes of the four hours are this workspace's: from its
	name, so it never moves and a box's workspaces fall apart. Pure."""
	return int(hashlib.sha256(slug.encode()).hexdigest(), 16) % (EVERY // TICK)


def turn(slug: str, at: int) -> int:
	"""Which of this workspace's four-hour turns `at` falls in. Pure."""
	return (at - slot(slug) * TICK) // EVERY


def send(url: str, secret: str, slug: str, part: str, path: str, stamp: str | None = None) -> dict:
	"""One file of a backup to the keeper: under today's night, or under
	`stamp` for a four-hourly one."""
	name = os.path.basename(path)
	at = int(time.time())
	where = f"{slug}/recent/{stamp}/{part}/{name}" if stamp else f"{slug}/{part}/{name}"
	with open(path, "rb") as body:
		answered = requests.put(
			f"{url.rstrip('/')}/workspace/{where}",
			data=body,
			headers={"x-one-timestamp": str(at), "x-one-signature": signed(secret, at, where)},
			timeout=PATIENCE,
		)
	answered.raise_for_status()
	return answered.json()


def nightly() -> None:
	"""Scheduled daily: a backup made and sent, if OneAdmin gave this
	workspace a secret to sign it with."""
	secret, url, slug = frappe.conf.get("one_backup_secret"), frappe.conf.get("one_keeper_url"), frappe.conf.get("one_tenant")
	if not (secret and url and slug):
		return
	frappe.enqueue("onedesk.one.backup.made", queue="long", timeout=PATIENCE * 2, job_id="one_backup_sent", deduplicate=True)


def due() -> None:
	"""Scheduled every five minutes: a four-hourly backup once this workspace's
	turn has changed. A late tick still finds the change; the first tick after
	the cache is lost only notes the turn, so a restart does not start every
	workspace on the box at once."""
	if not (frappe.conf.get("one_backup_secret") and frappe.conf.get("one_keeper_url") and frappe.conf.get("one_tenant")):
		return
	now = turn(frappe.conf.get("one_tenant"), int(time.time()))
	was = frappe.cache.get_value(LAST_TURN)
	frappe.cache.set_value(LAST_TURN, now)
	if was is not None and was != now:
		frappe.enqueue("onedesk.one.backup.recent", queue="long", timeout=PATIENCE * 2, job_id="one_backup_recent", deduplicate=True)


def recent() -> list[str]:
	"""Back up the database and config now and send them. The copies here go
	once sent: the bucket keeps them, and six a day would fill the disk."""
	from frappe.utils.backups import new_backup

	secret, url, slug = frappe.conf.get("one_backup_secret"), frappe.conf.get("one_keeper_url"), frappe.conf.get("one_tenant")
	if not (secret and url and slug):
		return []
	stamp = time.strftime(STAMP, time.gmtime())
	backup = new_backup(ignore_files=True, force=True)
	parts = {"database": backup.backup_path_db, "config": backup.backup_path_conf}
	try:
		return [send(url, secret, slug, part, path, stamp).get("kept") for part, path in parts.items() if path and os.path.exists(path)]
	finally:
		for path in parts.values():
			if path and os.path.exists(path):
				os.remove(path)


def made() -> list[str]:
	"""Back up now, with files, and send each part."""
	from frappe.utils.backups import new_backup

	secret, url, slug = frappe.conf.get("one_backup_secret"), frappe.conf.get("one_keeper_url"), frappe.conf.get("one_tenant")
	if not (secret and url and slug):
		return []
	backup = new_backup(ignore_files=False, force=True)
	parts = {
		"database": backup.backup_path_db,
		"public": backup.backup_path_files,
		"private": backup.backup_path_private_files,
		"config": backup.backup_path_conf,
	}
	return [send(url, secret, slug, part, path).get("kept") for part, path in parts.items() if path and os.path.exists(path)]
