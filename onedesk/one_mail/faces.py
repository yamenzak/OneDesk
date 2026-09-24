"""Faces and logos, for everyone who writes and every organisation.

A person's picture comes from Gravatar, by a hash of their address. An
organisation's logo comes from Google's favicon service, by its domain. Both
are fetched by this server, never by anybody's browser, and only once: each
answer is a `Face` row, and each picture a File in the Logos folder in Company. So a
sender learns nothing when their message is opened, Google and Gravatar are
asked once per address or domain rather than every time a face is drawn,
and a tenant's pictures are theirs, in their own storage.

Used everywhere, not only by mail:
- a Contact without a picture gets its person's face;
- a Customer or Supplier without an image gets its website's logo;
- a Bank gets its website's logo in `one_logo`, which ERPNext's Bank lacks;
- the Mail page draws each sender's contact picture, else their face, else
  their organisation's logo.

Addresses at a mail provider (gmail.com and the like) never get the
provider's logo, since the provider is not who wrote.

Nothing is fetched while somebody waits. A face not yet looked for is
looked for in the background and appears the next time it is drawn. One not
found is looked for again after a month.
"""

import hashlib
from urllib.parse import quote, urlparse

import frappe
import requests
from frappe.utils import add_days, now_datetime

#: Where pictures are kept: the Logos folder in Company.
FOLDER, FOLDER_NAME = "Home/Logos", "Logos"

#: A picture larger than this is not kept.
LARGEST = 256 * 1024

#: Seconds each source is given to answer.
PATIENCE = 8

#: How long a face not found is left before it is looked for again.
AGAIN_AFTER = 30  # days

#: Domains that are somebody's mail provider rather than their organisation.
PROVIDERS = frozenset(
	(
		"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "live.com", "msn.com", "yahoo.com",
		"ymail.com", "icloud.com", "me.com", "mac.com", "aol.com", "gmx.net", "gmx.de", "gmx.com", "web.de",
		"proton.me", "protonmail.com", "pm.me", "mail.ru", "yandex.com", "yandex.ru", "zoho.com", "fastmail.com",
		"hey.com", "tutanota.com", "tuta.io", "qq.com", "163.com",
	)
)  # fmt: skip

EXTENSIONS = {
	"image/png": "png",
	"image/jpeg": "jpg",
	"image/gif": "gif",
	"image/webp": "webp",
	"image/x-icon": "ico",
	"image/vnd.microsoft.icon": "ico",
}


# ------------------------------------------------------------------ pure


def domain_of(address: str | None) -> str | None:
	"""The domain of an address or a website, lowercased, without `www.`.
	Pure."""
	text = (address or "").strip().lower()
	if not text:
		return None
	if "@" in text and "/" not in text:
		host = text.rsplit("@", 1)[1]
	else:
		host = urlparse(text if "//" in text else f"//{text}").hostname or ""
	host = host.strip(".")
	if host.startswith("www."):
		host = host[4:]
	return host if "." in host else None


def keys_for(address: str | None, ours: str | None = None) -> list[str]:
	"""What to look for, for a sender, in order: their face, then their
	organisation's logo, unless the domain is a mail provider's or our own
	mail domain. Pure."""
	address = (address or "").strip().lower()
	if "@" not in address:
		return []
	domain = domain_of(address)
	return [address] + ([domain] if domain and domain not in PROVIDERS and domain != ours else [])


def is_person(key: str) -> bool:
	return "@" in key


def gravatar(address: str) -> str:
	"""Gravatar's picture of an address, or a 404 when it has none. Pure."""
	digest = hashlib.sha256(address.strip().lower().encode()).hexdigest()
	return f"https://www.gravatar.com/avatar/{digest}?d=404&s=128"


def favicon(domain: str) -> str:
	"""Google's logo for a domain, or a 404 when it has none. Pure."""
	return (
		"https://t1.gstatic.com/faviconV2?client=SOCIAL&type=FAVICON&fallback_opts=TYPE,SIZE,URL"
		f"&url={quote('https://' + domain, safe='')}&size=128"
	)


def file_name(key: str, content_type: str) -> str:
	"""What a picture is called in Logos. Pure."""
	return f"{key}.{EXTENSIONS.get(content_type.split(';')[0].strip(), 'png')}"


# ------------------------------------------------------------------ reading


def lookup(addresses: list[str]) -> dict[str, str]:
	"""The picture to draw for each address, where there is one: its
	Contact's, else its person's face, else its organisation's logo. Those
	never looked for are looked for in the background."""
	addresses = sorted({(one or "").strip().lower() for one in addresses if one and "@" in one})
	if not addresses:
		return {}
	out = {}
	C, E = frappe.qb.DocType("Contact"), frappe.qb.DocType("Contact Email")
	for row in (
		frappe.qb.from_(E)
		.join(C)
		.on(E.parent == C.name)
		.where(E.email_id.isin(addresses))
		.where(C.image.isnotnull())
		.where(C.image != "")
		.select(E.email_id, C.image)
		.run(as_dict=True)
	):
		out.setdefault(row.email_id.lower(), row.image)
	from onedesk.one_mail import addresses as ours

	wanted = {address: keys_for(address, ours.domain()) for address in addresses if address not in out}
	keys = sorted({key for keys in wanted.values() for key in keys})
	known = {
		row.name: row
		for row in frappe.get_all(
			"Face", filters={"name": ["in", keys or [""]]}, fields=["name", "image", "found"]
		)
	}
	for address, keys in wanted.items():
		for key in keys:
			if key in known and known[key].found and known[key].image:
				out[address] = known[key].image
				break
	missing = [key for key in keys if key not in known]
	if missing:
		frappe.enqueue(
			"onedesk.one_mail.faces.fetch_many",
			queue="short",
			job_id=f"one_faces:{hashlib.sha1(','.join(missing).encode()).hexdigest()[:16]}",
			deduplicate=True,
			enqueue_after_commit=True,
			keys=missing[:50],
		)
	return out


# ------------------------------------------------------------------ fetching


def folder() -> str:
	"""the Logos folder in Company, made the first time it is needed."""
	if not frappe.db.exists("File", FOLDER):
		doc = frappe.get_doc({"doctype": "File", "is_folder": 1, "file_name": FOLDER_NAME, "folder": "Home"})
		doc.flags.ignore_permissions = True
		doc.insert()
	return FOLDER


def fetch_many(keys: list[str]) -> None:
	for key in keys:
		try:
			fetch(key)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(title=f"OneMail could not look for a picture of {key}")


def fetch(key: str) -> str | None:
	"""Look for one face or logo, keep what is found, and say where."""
	key = key.strip().lower()
	url = gravatar(key) if is_person(key) else favicon(key)
	image = None
	try:
		answer = requests.get(url, timeout=PATIENCE, headers={"User-Agent": "One"})
		kind = answer.headers.get("Content-Type", "")
		if answer.status_code == 200 and kind.startswith("image/") and 0 < len(answer.content) <= LARGEST:
			image = _keep(key, answer.content, kind)
	except requests.RequestException:
		# Unreachable is not "has none": look again on the next pass.
		return None
	values = {
		"kind": "Person" if is_person(key) else "Organisation",
		"image": image,
		"found": int(bool(image)),
		"checked_on": now_datetime(),
	}
	if frappe.db.exists("Face", key):
		frappe.db.set_value("Face", key, values, update_modified=False)
	else:
		frappe.get_doc({"doctype": "Face", "key": key, **values}).insert(ignore_permissions=True)
	return image


def _keep(key: str, content: bytes, kind: str) -> str:
	name = file_name(key, kind)
	old = frappe.db.get_value("File", {"folder": folder(), "file_name": name}, "name")
	if old:
		frappe.delete_doc("File", old, ignore_permissions=True, force=True)
	doc = frappe.get_doc(
		{"doctype": "File", "file_name": name, "folder": FOLDER, "is_private": 0, "content": content}
	)
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.file_url


def again() -> None:
	"""Daily: faces not found a month ago are looked for again."""
	stale = frappe.get_all(
		"Face",
		filters={"found": 0, "checked_on": ["<", add_days(now_datetime(), -AGAIN_AFTER)]},
		pluck="name",
		limit=200,
	)
	if stale:
		fetch_many(stale)


# ------------------------------------------------------------------ records

#: Which image field each kind of record is dressed in, and where its
#: address or website is.
DRESSED = {
	"Contact": ("image", None),
	"Customer": ("image", "website"),
	"Supplier": ("image", "website"),
	"Bank": ("one_logo", "website"),
}


def dress_later(doc, method=None) -> None:
	"""after_insert and on_update of the records in DRESSED: one without a
	picture gets one, in the background."""
	field, _source = DRESSED.get(doc.doctype, (None, None))
	if not field or doc.get(field) or not doc.meta.has_field(field):
		return
	if not _source_of(doc):
		return
	frappe.enqueue(
		"onedesk.one_mail.faces.dress",
		queue="short",
		job_id=f"one_dress:{doc.doctype}:{doc.name}",
		deduplicate=True,
		enqueue_after_commit=True,
		doctype=doc.doctype,
		name=doc.name,
	)


def _source_of(doc) -> str | None:
	"""The key a record's picture is found by."""
	_field, source = DRESSED[doc.doctype]
	if doc.doctype == "Contact":
		address = doc.get("email_id") or next(
			(row.email_id for row in doc.get("email_ids") or [] if row.email_id), None
		)
		return (address or "").strip().lower() or None
	domain = domain_of(doc.get(source))
	return domain if domain and domain not in PROVIDERS else None


def dress(doctype: str, name: str) -> str | None:
	doc = frappe.get_doc(doctype, name)
	field = DRESSED[doctype][0]
	key = _source_of(doc)
	if doc.get(field) or not key:
		return None
	found = frappe.db.get_value("Face", key, ["image", "found"], as_dict=True)
	image = found.image if found and found.found else None if found else fetch(key)
	if image:
		frappe.db.set_value(doctype, name, field, image, update_modified=False)
	return image
