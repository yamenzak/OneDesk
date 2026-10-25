"""Faces and logos, for everyone who writes and every organisation.

A person's picture comes from Gravatar and an organisation's logo from
Google's favicon service, fetched by this server once and kept as a `Face`
row and a File in Company › Logos."""

import hashlib
from urllib.parse import quote, urlparse

import frappe
import requests
from frappe.utils import add_days, now_datetime

from onedesk.one_intake.identifiers import PROVIDERS
from onedesk.one_legal import services

FOLDER, FOLDER_NAME = "Home/Logos", "Logos"

LARGEST = 256 * 1024

PATIENCE = 8

AGAIN_AFTER = 30


EXTENSIONS = {
	"image/png": "png",
	"image/jpeg": "jpg",
	"image/gif": "gif",
	"image/webp": "webp",
	"image/x-icon": "ico",
	"image/vnd.microsoft.icon": "ico",
}


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
	missing = [key for key in keys if key not in known and services.on(service_of(key))]
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


def service_of(key: str) -> str:
	"""The optional service a face or a logo comes from (legal.py). Pure."""
	return "gravatar" if is_person(key) else "logos"


def fetch(key: str) -> str | None:
	"""Look for one face or logo, keep what is found, and say where: only
	while its service is on (one_legal/services.py)."""
	key = key.strip().lower()
	url = gravatar(key) if is_person(key) else favicon(key)
	try:
		answer = services.call(service_of(key), requests.get, url, timeout=PATIENCE, headers={"User-Agent": "One"})
	except requests.RequestException:
		return None
	if answer is None:
		return None
	image = None
	kind = answer.headers.get("Content-Type", "")
	if answer.status_code == 200 and kind.startswith("image/") and 0 < len(answer.content) <= LARGEST:
		image = _keep(key, answer.content, kind)
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


DRESSED = {
	"Contact": ("image", "person"),
	"Lead": ("image", "person"),
	"User": ("user_image", "face"),
	"Employee": ("image", "face"),
	"Customer": ("image", "organisation"),
	"Supplier": ("image", "organisation"),
	"Manufacturer": ("logo", "organisation"),
	"Company": ("company_logo", "organisation"),
	"Bank": ("one_logo", "bank"),
	"Brand": ("image", "bank"),
}

NOBODY = ("Administrator", "Guest")


def sources(kind: str, email: str | None, website: str | None) -> list[str]:
	"""Where a record's picture is looked for, in order, until one has it
	(README, `sources`). Pure. A mail provider's domain is never a logo."""
	email = (email or "").strip().lower() or None
	address = email if email and "@" in email else None
	by_email = domain_of(address) if address else None
	by_site = domain_of(website)
	logos = [one for one in (by_site, by_email) if one and one not in PROVIDERS]
	if kind == "person":
		order = [
			address,
			by_email if by_email not in PROVIDERS else None,
			by_site if by_site not in PROVIDERS else None,
		]
	elif kind == "face":
		order = [address]
	elif kind == "organisation":
		order = [*logos, address]
	else:
		order = [by_site if by_site not in PROVIDERS else None]
	return list(dict.fromkeys(one for one in order if one))


def _email_of(doc) -> str | None:
	"""A record's address: its own, else its primary contact's."""
	if doc.doctype == "User":
		return None if doc.name in NOBODY else doc.get("email") or doc.name
	if doc.doctype == "Employee":
		return doc.get("prefered_email") or doc.get("company_email") or doc.get("personal_email")
	if doc.doctype == "Contact":
		return doc.get("email_id") or next(
			(row.email_id for row in doc.get("email_ids") or [] if row.email_id), None
		)
	found = doc.get("email_id")
	contact = doc.get("customer_primary_contact") or doc.get("supplier_primary_contact")
	if not found and contact:
		found = frappe.db.get_value("Contact", contact, "email_id")
	return found


def sources_of(doc) -> list[str]:
	return sources(DRESSED[doc.doctype][1], _email_of(doc), doc.get("website") or doc.get("one_website"))


def _other_record(doc) -> tuple[str, str] | None:
	"""The same person's other record: an Employee's User, a User's Employee."""
	if doc.doctype == "Employee" and doc.get("user_id"):
		return ("User", doc.user_id)
	if doc.doctype == "User" and doc.name not in NOBODY:
		employee = frappe.db.get_value("Employee", {"user_id": doc.name}, "name")
		return ("Employee", employee) if employee else None
	return None


def borrowed(doc) -> str | None:
	"""A picture the same person already has on their other record: an
	Employee's user's, a User's employee's. Uploaded there, it is theirs, and
	comes before any face looked for."""
	if doc.doctype == "Employee" and doc.get("user_id"):
		return frappe.db.get_value("User", doc.user_id, "user_image")
	if doc.doctype == "User" and doc.name not in NOBODY:
		return frappe.db.get_value("Employee", {"user_id": doc.name, "image": ["is", "set"]}, "image")
	return None


def dress_later(doc, method=None) -> None:
	"""after_insert and on_update of the records in DRESSED: one without a
	picture gets one, in the background. A person's photo put on their User
	or their Employee goes to the other one too, when it has none."""
	field = DRESSED.get(doc.doctype, (None, None))[0]
	if not field or not doc.meta.has_field(field):
		return
	if doc.get(field):
		other = _other_record(doc)
		if other and not frappe.db.get_value(*other, DRESSED[other[0]][0]):
			frappe.db.set_value(*other, DRESSED[other[0]][0], doc.get(field), update_modified=False)
		return
	if not sources_of(doc) and not _other_record(doc):
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


def picture(key: str) -> str | None:
	"""A key's picture: what was found before, or a first look now. One
	looked for and not found stays not found until `again` looks again."""
	found = frappe.db.get_value("Face", key, ["image", "found"], as_dict=True)
	if found:
		return found.image if found.found else None
	return fetch(key)


def dress(doctype: str, name: str) -> str | None:
	"""Give a record without a picture the first one its sources have."""
	doc = frappe.get_doc(doctype, name)
	field = DRESSED[doctype][0]
	if doc.get(field):
		return None
	image = borrowed(doc) or next((found for key in sources_of(doc) if (found := picture(key))), None)
	if not image:
		return None
	frappe.db.set_value(doctype, name, field, image, update_modified=False)
	if doctype == "Company":
		from onedesk.one import letter_heads

		letter_heads.redraw()
	return image


def dress_all() -> int:
	"""Every record in DRESSED without a picture, once: what existed before
	pictures were looked for, and what `dress_later` could not reach. Run in
	the background by a patch; safe to run again."""
	dressed = 0
	for doctype, (field, _kind) in DRESSED.items():
		if not frappe.db.exists("DocType", doctype) or not frappe.get_meta(doctype).has_field(field):
			continue
		for name in frappe.get_all(doctype, filters={field: ["is", "not set"]}, pluck="name", limit=5000):
			if doctype == "User" and name in NOBODY:
				continue
			try:
				dressed += int(bool(dress(doctype, name)))
				frappe.db.commit()
			except Exception:
				frappe.db.rollback()
				frappe.log_error(title=f"OneMail could not find a picture for {doctype} {name}")
	return dressed
