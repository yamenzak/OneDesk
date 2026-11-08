"""This workspace's own nightly backup: its database, files and config,
sent to One's locked backup bucket through the keeper and signed with the
secret OneAdmin gave it (one_admin/backups.py). The keeper adds it under
this workspace's name and nothing can delete it there."""

import hashlib
import hmac
import os
import time

import frappe
import requests

PATIENCE = 900


def signed(secret: str, at: int, path: str) -> str:
	"""What the keeper checks an upload by. Pure."""
	return hmac.new(secret.encode(), f"{at}.{path}".encode(), hashlib.sha256).hexdigest()


def send(url: str, secret: str, slug: str, part: str, path: str) -> dict:
	"""One file of a backup to the keeper."""
	name = os.path.basename(path)
	at = int(time.time())
	where = f"{slug}/{part}/{name}"
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
