"""Connect GitHub: a GitHub App made by GitHub's manifest flow, in place of a
personal token. GitHub makes the app from the manifest the button posts and
hands back its private key, which goes to the config; the app is installed on
the repository; and whatever needs the code is given a token minted for one
hour that reads that repository only. The personal token is still used until
the app is installed. Production's OneAdmin also writes the repository's
Actions secrets through it, so nobody pastes one (AGENTS.md, Under the hood,
GitHub)."""

import base64
import json
import re
import secrets
import time
from urllib.parse import urlencode, urlparse

import frappe
import requests
from frappe import _
from frappe.rate_limiter import rate_limit

from onedesk.one_admin import boxes, faults, pilot, site, vault

GITHUB = "https://github.com"
API = "https://api.github.com"
VERSION = "2022-11-28"
SETTINGS = "One Admin Settings"
PRIVATE_KEY = "github_app_private_key"
PERSONAL = "github_token"
RETURN_TO = "onedesk.one_admin.github_app.back"
INSTALLED = "onedesk.one_admin.github_app.installed"
BACK_TO = "/desk/oneadmin?center=settings&module=OneAdmin&at=servers"
STATE_FOR = 3600
SIGNED_FOR = 300
NAME_LONGEST = 34
TIMEOUT = 30
WRITTEN = "one_github_secrets"
SECRET_NAME = re.compile(r"^(?!GITHUB_)[A-Z_][A-Z0-9_]*$")
FIELDS = ("github_app_name", "github_app_slug", "github_app_id", "github_installation_id", "github_installed_on")


def name_for(host: str) -> str:
	"""The app's name on GitHub, which must be unique there. Pure."""
	return f"One {host}"[:NAME_LONGEST].strip()


def manifest(name: str, admin_url: str) -> dict:
	"""What GitHub makes the app from: reading the code and writing the
	Actions secrets, nothing else. Pure."""
	base = admin_url.rstrip("/")
	return {
		"name": name,
		"url": base,
		"description": "Reads One's code for the servers OneAdmin builds, and writes the secrets its workflows use.",
		"redirect_url": f"{base}/api/method/{RETURN_TO}",
		"setup_url": f"{base}/api/method/{INSTALLED}",
		"setup_on_update": True,
		"public": False,
		"default_permissions": {"contents": "read", "metadata": "read", "secrets": "write"},
		"default_events": [],
		"hook_attributes": {"url": base, "active": False},
	}


def new_app_url(state: str) -> str:
	"""Where the manifest is posted. Pure."""
	return f"{GITHUB}/settings/apps/new?" + urlencode({"state": state})


def install_url(slug: str) -> str:
	"""Where the app is installed on a repository. Pure."""
	return f"{GITHUB}/apps/{slug}/installations/new"


def conversion_url(code: str) -> str:
	"""Where the code GitHub sent back becomes the app. Pure."""
	if not code or not code.replace("_", "").replace("-", "").isalnum():
		raise ValueError("That is not a code from GitHub.")
	return f"{API}/app-manifests/{code}/conversions"


def made_of(answered: dict) -> dict:
	"""The app GitHub made, split into what Settings shows and the private
	key, which only the config holds. Pure."""
	if not (answered.get("id") and answered.get("slug") and answered.get("pem")):
		raise ValueError("GitHub did not return the app.")
	shown = {"github_app_name": answered.get("name") or answered["slug"], "github_app_slug": answered["slug"], "github_app_id": str(answered["id"])}
	return {"shown": shown, "private_key": answered["pem"]}


def claims(app_id: str, now: int) -> dict:
	"""The app's JWT: issued a minute back for clock drift, good for nine
	minutes, GitHub allowing ten. Pure."""
	return {"iat": now - 60, "exp": now + 540, "iss": str(app_id)}


def app_jwt(app_id: str, private_key: str, now: int | None = None) -> str:
	import jwt

	return jwt.encode(claims(app_id, int(time.time()) if now is None else now), private_key, algorithm="RS256")


def headers(bearer: str) -> dict:
	"""Pure."""
	return {"Accept": "application/vnd.github+json", "Authorization": f"Bearer {bearer}", "X-GitHub-Api-Version": VERSION}


def installation_url(repository: str) -> str:
	"""Where GitHub says which installation of the app reaches a repository. Pure."""
	return f"{API}/repos/{repository}/installation"


def token_asked(installation: str, repository: str, permissions: dict | None = None) -> tuple[str, dict]:
	"""The installation token's request: one repository, read only unless
	other permissions are named. Pure."""
	return f"{API}/app/installations/{installation}/access_tokens", {"repositories": [repository.split("/")[-1]], "permissions": permissions or {"contents": "read"}}


def public_key_url(repository: str) -> str:
	"""Where GitHub gives the key a repository's Actions secrets are sealed
	to. Pure."""
	return f"{API}/repos/{repository}/actions/secrets/public-key"


def secret_url(repository: str, name: str) -> str:
	"""Where one Actions secret is written. Pure."""
	if not SECRET_NAME.match(name or ""):
		raise ValueError(f"{name} is not a name GitHub takes for a secret.")
	return f"{API}/repos/{repository}/actions/secrets/{name}"


def sealed(public_key: str, value: str) -> str:
	"""A value sealed to the repository's key with libsodium's sealed box, as
	GitHub asks, in base64. Pure."""
	from nacl.public import PublicKey, SealedBox

	return base64.b64encode(SealedBox(PublicKey(base64.b64decode(public_key))).encrypt(value.encode())).decode()


def secret_body(key: dict, value: str) -> dict:
	"""The body that writes a secret, from what `public_key_url` answered. Pure."""
	if not (key.get("key") and key.get("key_id")):
		raise ValueError("GitHub did not return the repository's key.")
	return {"encrypted_value": sealed(key["key"], value), "key_id": key["key_id"]}


def token_of(answered: dict) -> dict:
	"""Pure."""
	if not answered.get("token"):
		raise ValueError("GitHub did not return a token.")
	return {"token": answered["token"], "expires_at": answered.get("expires_at")}


def fresh(at, now: int) -> bool:
	"""A box's request is believed only within five minutes of being made. Pure."""
	return isinstance(at, int) and abs(now - at) <= SIGNED_FOR


def _held() -> dict:
	return {name: frappe.db.get_single_value(SETTINGS, name) for name in FIELDS}


def status() -> dict:
	"""What the AWS and GitHub tab shows."""
	held = _held()
	return {
		"app": held["github_app_name"],
		"slug": held["github_app_slug"],
		"installed": bool(held["github_installation_id"]),
		"repository": held["github_installed_on"] or boxes.REPOSITORY,
		"install_url": install_url(held["github_app_slug"]) if held["github_app_slug"] else None,
		"personal": bool(vault.get(PERSONAL)),
		"production": production(),
		"secrets": sorted(written()),
	}


def production() -> bool:
	"""Whether this is production's OneAdmin, which leaves Environment empty.
	Only it writes the repository's secrets: dev shares the repository."""
	return not (frappe.db.get_single_value(SETTINGS, "environment") or "").strip()


def written() -> dict:
	"""The secrets written to the repository, each with when."""
	return json.loads(frappe.db.get_default(WRITTEN) or "{}")


def _only() -> None:
	frappe.only_for(site.OPERATOR)
	site.require_admin()


def _state_key(state: str) -> str:
	return f"one_github_app_state:{state}"


def _host() -> str:
	return urlparse(frappe.utils.get_url()).hostname or "admin"


@frappe.whitelist(methods=["POST"])
def start() -> dict:
	"""Connect GitHub: the address the manifest is posted to, and the manifest."""
	_only()
	state = secrets.token_urlsafe(32)
	frappe.cache.set_value(_state_key(state), frappe.session.user, expires_in_sec=STATE_FOR)
	return {"action": new_app_url(state), "manifest": json.dumps(manifest(name_for(_host()), frappe.utils.get_url()))}


@frappe.whitelist(methods=["GET"])
def back(code: str | None = None, state: str | None = None) -> None:
	"""Where GitHub sends the operator once the app is made: the app kept,
	then the operator sent on to install it."""
	_only()
	if not state or frappe.cache.get_value(_state_key(state)) != frappe.session.user or not code:
		frappe.throw(_("The request has expired. Press Connect GitHub again."))
	frappe.cache.delete_value(_state_key(state))
	answered = requests.post(conversion_url(code), headers={"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": VERSION}, timeout=TIMEOUT)
	if not answered.ok:
		frappe.throw(_("GitHub refused to make the app: {0}").format(answered.text[:300]))
	made = made_of(answered.json())
	vault.keep(PRIVATE_KEY, made["private_key"])
	frappe.db.set_single_value(SETTINGS, {**made["shown"], "github_installation_id": None, "github_installed_on": None})
	frappe.db.commit()
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = install_url(made["shown"]["github_app_slug"])


@frappe.whitelist(methods=["GET"])
def installed(installation_id: str | None = None, setup_action: str | None = None, state: str | None = None) -> None:
	"""Where GitHub sends the operator once the app is installed. Which
	installation reaches the repository is asked of GitHub, not taken from
	the address."""
	_only()
	_found()
	frappe.db.commit()
	if production():
		try:
			write_release()
		except (faults.Refused, requests.RequestException):
			frappe.log_error(title="Writing the release secrets to GitHub")
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = BACK_TO


@frappe.whitelist(methods=["POST"])
def check() -> dict:
	"""Check Connection: the installation looked up again and a token minted."""
	_only()
	_found()
	repository_token()
	return status()


def _jwt() -> str:
	app_id, private_key = frappe.db.get_single_value(SETTINGS, "github_app_id"), vault.get(PRIVATE_KEY)
	if not (app_id and private_key):
		frappe.throw(_("Connect GitHub first."))
	return app_jwt(app_id, private_key)


def _found() -> None:
	answered = requests.get(installation_url(boxes.REPOSITORY), headers=headers(_jwt()), timeout=TIMEOUT)
	if answered.status_code == 404:
		frappe.db.set_single_value(SETTINGS, {"github_installation_id": None, "github_installed_on": None})
		frappe.db.commit()
		frappe.throw(_("The GitHub App is not installed on {0}.").format(boxes.REPOSITORY))
	if not answered.ok:
		frappe.throw(_("GitHub did not answer: {0}").format(answered.text[:300]))
	frappe.db.set_single_value(SETTINGS, {"github_installation_id": str(answered.json()["id"]), "github_installed_on": boxes.REPOSITORY})


def connected() -> bool:
	return bool(frappe.db.get_single_value(SETTINGS, "github_installation_id"))


def repository_token(repository: str = boxes.REPOSITORY, permissions: dict | None = None) -> dict | None:
	"""A token for the repository for an hour, reading it unless other
	permissions are named, or None while the app is not installed."""
	installation = frappe.db.get_single_value(SETTINGS, "github_installation_id")
	if not installation:
		return None
	url, body = token_asked(installation, repository, permissions)
	answered = requests.post(url, json=body, headers=headers(_jwt()), timeout=TIMEOUT)
	if not answered.ok:
		raise faults.Refused(f"GitHub gave no token for {repository}: {answered.text[:300]}", status=answered.status_code)
	return token_of(answered.json())


def put_secret(name: str, value: str, repository: str = boxes.REPOSITORY) -> None:
	"""One Actions secret written to the repository with a token that may
	write its secrets and nothing else, sealed to the repository's key."""
	try:
		minted = repository_token(repository, {"secrets": "write"})
	except faults.Refused as refused:
		if refused.status == 422:
			raise faults.Refused(
				_("The GitHub App may not write secrets yet. On GitHub, give it Secrets: Read and write, accept the change on its installation, then set up again.")
			) from refused
		raise
	if not minted:
		raise faults.Refused(_("Connect GitHub first."))
	asked = headers(minted["token"])
	key = requests.get(public_key_url(repository), headers=asked, timeout=TIMEOUT)
	if not key.ok:
		raise faults.Refused(f"GitHub gave no key for {repository}'s secrets: {key.text[:300]}")
	put = requests.put(secret_url(repository, name), json=secret_body(key.json(), value), headers=asked, timeout=TIMEOUT)
	if not put.ok:
		raise faults.Refused(f"GitHub did not take {name}: {put.text[:300]}")
	frappe.db.set_default(WRITTEN, json.dumps({**written(), name: frappe.utils.now()}))
	frappe.db.commit()


def write_release() -> list[str]:
	"""The release workflow's two secrets: this site's address, and the secret
	it signs `releases.released` with, made here when there is none."""
	from onedesk.one_admin.releases import RELEASE_SECRET

	secret = frappe.conf.get(RELEASE_SECRET) or secrets.token_urlsafe(32)
	vault.keep(RELEASE_SECRET, secret)
	put_secret("ONE_RELEASE_SECRET", secret)
	put_secret("ONE_ADMIN_URL", frappe.utils.get_url().rstrip("/"))
	return ["ONE_RELEASE_SECRET", "ONE_ADMIN_URL"]


def for_boxes(keys: dict) -> str:
	"""The token a new box starts with: the app's, for an hour, or the
	personal one while the app is not installed."""
	minted = repository_token()
	if minted:
		return minted["token"]
	return vault.get(PERSONAL) or keys.get(PERSONAL) or ""


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=60, seconds=3600)
def for_box() -> dict:
	"""A box's agent asks for a token before it fetches the code. Believed
	only when signed with that box's own secret and made in the last five
	minutes."""
	from onedesk.one_admin.servers import signed

	site.require_admin()
	body = frappe.request.get_data(as_text=True)
	said = json.loads(body or "{}")
	try:
		secret = pilot.held(said.get("server") or "").get("agent") or ""
	except faults.Refused:
		secret = ""
	if not secret or not fresh(said.get("at"), int(time.time())) or not secrets.compare_digest(signed(secret, body), frappe.get_request_header("X-One-Agent") or ""):
		raise frappe.PermissionError
	return repository_token() or {}
