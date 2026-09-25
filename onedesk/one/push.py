"""Push: a notification on the devices a person turned it on for.

Standard Web Push (docs/NOTIFICATIONS.md, stage 4). Nothing of Frappe's relay
and no Firebase account: each message is encrypted on our server for the one
browser it is for (RFC 8291, by `pywebpush`), and the browser's own push
service carries it without being able to read it: Google's for Chrome and
Edge's Chromium, Mozilla's for Firefox, Apple's for Safari, Microsoft's for
Windows. Those four are the only addresses a message is ever sent to
(`SERVICES`), because the address comes from a browser and a server that posts
wherever a browser says is a server anybody can aim.

**Who gets one.** A Notification Log is pushed when its person ticked push for
its type (Settings, Notifications writes `one_push_notification_types` on
their Notification Settings, beside frappe's own email list), the workspace
allows push for it, and they turned push on in at least one browser (a Push
Device). Pushing is queued after the log is committed, so a slow push service
never holds up whatever sent the notification.

**The keys.** One VAPID key pair per site, made the first time it is asked
for and kept in the site's config, never in the database: the private half
signs every push, and a copy of the database is not a copy of it.

**The worker** is served from a method rather than from /assets, with
`Service-Worker-Allowed: /`, so it can be registered for the whole site and a
click can bring an open tab forward instead of opening another. It handles
push and clicks, and nothing else: it never sees a request the page makes.
"""

import json
from typing import Annotated
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.utils import now_datetime, strip_html

#: The push services a browser's address may be at. Anything else is refused
#: when a device is registered.
SERVICES = (
	"fcm.googleapis.com",
	"updates.push.services.mozilla.com",
	".push.apple.com",
	".notify.windows.com",
)

#: A device that failed this many times in a row, without the service saying
#: it is gone, is forgotten anyway.
MOST_FAILURES = 5

PRIVATE, PUBLIC = "onedesk_vapid_private", "onedesk_vapid_public"


# ------------------------------------------------------------------ the keys


def _keys() -> tuple[str, str]:
	"""The site's VAPID private key (PEM) and public key (the browser's
	applicationServerKey), made once."""
	conf = frappe.get_site_config()
	if not conf.get(PRIVATE):
		from cryptography.hazmat.primitives import serialization
		from frappe.installer import update_site_config
		from py_vapid import Vapid02, b64urlencode

		vapid = Vapid02()
		vapid.generate_keys()
		private = vapid.private_pem().decode()
		public = b64urlencode(
			vapid.public_key.public_bytes(
				serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
			)
		)
		update_site_config(PRIVATE, private)
		update_site_config(PUBLIC, public)
		return private, public
	return conf[PRIVATE], conf[PUBLIC]


def allowed_service(endpoint: str) -> bool:
	"""Whether a browser's push address is at a push service we send to. Pure."""
	parsed = urlparse(endpoint or "")
	host = (parsed.hostname or "").lower()
	return parsed.scheme == "https" and any(
		host == one.lstrip(".") or (one.startswith(".") and host.endswith(one)) for one in SERVICES
	)


# ------------------------------------------------------------------ the person's devices


@frappe.whitelist()
@frappe.read_only()
def devices() -> dict:
	"""This person's devices, and the key a new one subscribes with."""
	return {
		"key": _keys()[1],
		"devices": frappe.get_all(
			"Push Device",
			filters={"user": frappe.session.user},
			fields=["name", "label", "endpoint", "last_sent", "creation"],
			order_by="creation desc",
		),
	}


@frappe.whitelist(methods=["POST"])
def register(
	endpoint: Annotated[str, "The push address the browser gave."],
	p256dh: Annotated[str, "The browser's public key for this subscription."],
	auth: Annotated[str, "The browser's secret for this subscription."],
	label: Annotated[str | None, "What the device is, as the person would say it."] = None,
) -> dict:
	"""Turn push on in this browser, for the person signed in."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Sign in first."), frappe.PermissionError)
	if not allowed_service(endpoint):
		frappe.throw(_("This browser's push service is not one One sends to."))
	name = frappe.db.get_value("Push Device", {"endpoint": endpoint})
	doc = frappe.get_doc("Push Device", name) if name else frappe.new_doc("Push Device")
	doc.update(
		{
			"user": frappe.session.user,
			"endpoint": endpoint,
			"p256dh": p256dh,
			"auth": auth,
			"label": (label or "").strip()[:140] or _("A browser"),
			"failures": 0,
		}
	)
	doc.save(ignore_permissions=True)
	return devices()


@frappe.whitelist(methods=["POST"])
def forget(
	name: Annotated[str | None, "The device to forget."] = None,
	endpoint: Annotated[str | None, "Or the push address of this browser."] = None,
) -> dict:
	"""Turn push off in one of this person's own browsers."""
	filters = {"user": frappe.session.user}
	if name:
		filters["name"] = name
	elif endpoint:
		filters["endpoint"] = endpoint
	else:
		frappe.throw(_("Which device?"))
	for one in frappe.get_all("Push Device", filters=filters, pluck="name"):
		frappe.delete_doc("Push Device", one, ignore_permissions=True, force=True)
	return devices()


@frappe.whitelist(methods=["POST"])
def test() -> dict:
	"""A push to this person's own devices, to see that it arrives."""
	sent = _send_to(
		frappe.session.user,
		{
			"title": _("Push works"),
			"body": _("This is how One tells you something on this device."),
			"url": "/app/settings?section=notifications",
		},
	)
	return {"sent": sent}


# ------------------------------------------------------------------ sending


def pushed(doc, method=None) -> None:
	"""Notification Log after_insert: queue a push if its person wants one."""
	if not doc.for_user or not _wants(doc.for_user, doc.type):
		return
	frappe.enqueue("onedesk.one.push.send", log=doc.name, enqueue_after_commit=True, now=frappe.in_test)


def _wants(user: str, kind: str | None) -> bool:
	from onedesk.one import notify

	if not kind or not frappe.db.exists("Push Device", {"user": user}):
		return False
	# Frappe's own kinds carry no switch of ours, and may always be pushed.
	if kind not in notify.FRAPPE_KINDS and not frappe.db.get_value(
		"Notification Type", kind, "one_allow_push"
	):
		return False
	return bool(
		frappe.db.exists(
			"Notification Type Preference",
			{
				"parenttype": "Notification Settings",
				"parentfield": "one_push_notification_types",
				"parent": user,
				"notification_type": kind,
			},
		)
	)


def send(log: str) -> None:
	"""One Notification Log to each of its person's devices."""
	doc = frappe.get_doc("Notification Log", log)
	link = doc.link or (
		frappe.utils.get_url_to_form(doc.document_type, doc.document_name)
		if doc.document_type and doc.document_name
		else "/app"
	)
	_send_to(
		doc.for_user,
		{
			"title": strip_html(doc.subject or "")[:200],
			"body": strip_html(doc.email_content or "")[:300],
			"url": link,
			"tag": doc.name,
		},
	)


def _send_to(user: str, message: dict) -> int:
	from pywebpush import WebPushException, webpush

	private, _public = _keys()
	sent = 0
	for device in frappe.get_all(
		"Push Device", filters={"user": user}, fields=["name", "endpoint", "p256dh", "auth", "failures"]
	):
		if not allowed_service(device.endpoint):
			continue
		try:
			webpush(
				subscription_info={
					"endpoint": device.endpoint,
					"keys": {"p256dh": device.p256dh, "auth": device.auth},
				},
				data=json.dumps(message),
				vapid_private_key=_vapid(private),
				vapid_claims={"sub": _contact()},
				ttl=24 * 60 * 60,
				timeout=10,
			)
		except WebPushException as e:
			status = getattr(e.response, "status_code", None)
			# 404 and 410 are the service saying the browser unsubscribed.
			if status in (404, 410) or (device.failures or 0) + 1 >= MOST_FAILURES:
				frappe.delete_doc("Push Device", device.name, ignore_permissions=True, force=True)
			else:
				frappe.db.set_value(
					"Push Device", device.name, "failures", (device.failures or 0) + 1, update_modified=False
				)
			continue
		frappe.db.set_value(
			"Push Device", device.name, {"last_sent": now_datetime(), "failures": 0}, update_modified=False
		)
		sent += 1
	return sent


def _contact() -> str:
	"""Who a push service may write to about our pushes: the site, where it is
	https, as it is in production; a mailbox on its host where it is not."""
	url = frappe.utils.get_url()
	return url if url.startswith("https://") else f"mailto:notifications@{urlparse(url).hostname}"


def _vapid(private_pem: str):
	from py_vapid import Vapid02

	return Vapid02.from_pem(private_pem.encode())


# ------------------------------------------------------------------ the worker


WORKER = """
self.addEventListener("push", (event) => {
	let said = {};
	try { said = event.data ? event.data.json() : {}; } catch (e) { said = { title: event.data.text() }; }
	event.waitUntil(self.registration.showNotification(said.title || "One", {
		body: said.body || "",
		tag: said.tag,
		data: { url: said.url || "/app" },
		icon: "/assets/onedesk/images/one.svg",
	}));
});
self.addEventListener("notificationclick", (event) => {
	event.notification.close();
	const url = new URL(event.notification.data.url, self.location.origin).href;
	event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then((open) => {
		const tab = open.find((one) => one.url.startsWith(self.location.origin));
		// A tab this worker controls can be sent there; any other gets a new one.
		if (tab) return tab.navigate(url).then((one) => (one || tab).focus()).catch(() => clients.openWindow(url));
		return clients.openWindow(url);
	}));
});
"""


@frappe.whitelist(allow_guest=True, methods=["GET"])
def worker():
	"""The service worker, for the whole site."""
	from werkzeug.wrappers import Response

	return Response(
		WORKER,
		mimetype="text/javascript",
		headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
	)
