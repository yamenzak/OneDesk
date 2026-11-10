"""Sign In to Cloudflare: OAuth's authorization code flow, in place of a master
token. The access token is held for one run of Set Up Cloudflare and revoked
when it ends; the master-token path is unchanged (README, Keys)."""

import base64
import hashlib
import secrets
from urllib.parse import urlencode

import frappe
import requests
from frappe import _
from frappe.utils.password import decrypt, encrypt

from onedesk.one_admin import site, vault

AUTHORIZE = "https://dash.cloudflare.com/oauth2/auth"
TOKEN = "https://dash.cloudflare.com/oauth2/token"
REVOKE = "https://dash.cloudflare.com/oauth2/revoke"
SETTINGS = "One Admin Settings"
CLIENT_SECRET = "cloudflare_oauth_client_secret"
RETURN_TO = "onedesk.one_admin.cloudflare_signin.back"
STATE_FOR = 600
TOKEN_FOR = 900
BACK_TO = "/desk/oneadmin?center=settings&module=OneAdmin&at=cloudflare"
TIMEOUT = 30


def _client() -> tuple[str, str]:
	client_id = frappe.db.get_single_value(SETTINGS, "cloudflare_oauth_client_id")
	secret = vault.get(CLIENT_SECRET)
	if not (client_id and secret):
		frappe.throw(_("Enter the OAuth Client ID and Secret first."))
	return client_id, secret


def _scopes() -> str:
	scopes = " ".join((frappe.db.get_single_value(SETTINGS, "cloudflare_oauth_scopes") or "").split())
	if not scopes:
		frappe.throw(_("Enter the OAuth Scopes first."))
	return scopes


def _redirect() -> str:
	return frappe.utils.get_url(f"/api/method/{RETURN_TO}")


def _state_key(state: str) -> str:
	return f"one_cloudflare_signin_state:{state}"


def _token_key() -> str:
	return "one_cloudflare_signin_token"


def challenge_of(verifier: str) -> str:
	"""PKCE's S256 challenge. Pure."""
	return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


def authorize_url(client_id: str, redirect: str, scopes: str, state: str, challenge: str) -> str:
	"""Where the operator is sent to approve. Pure."""
	return f"{AUTHORIZE}?" + urlencode(
		{
			"response_type": "code",
			"client_id": client_id,
			"redirect_uri": redirect,
			"scope": scopes,
			"state": state,
			"code_challenge": challenge,
			"code_challenge_method": "S256",
		}
	)


@frappe.whitelist(methods=["POST"])
def start() -> str:
	"""The button on One Admin Settings: the address to send the operator to."""
	frappe.only_for(site.OPERATOR)
	site.require_admin()
	client_id, _secret = _client()
	state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(64)
	frappe.cache.set_value(_state_key(state), {"verifier": verifier, "user": frappe.session.user}, expires_in_sec=STATE_FOR)
	return authorize_url(client_id, _redirect(), _scopes(), state, challenge_of(verifier))


@frappe.whitelist(methods=["GET"])
def back(code: str | None = None, state: str | None = None, error: str | None = None) -> None:
	"""Where Cloudflare sends the operator back: the code changed for a token,
	which waits for the run in the cache, encrypted, and the run started."""
	frappe.only_for(site.OPERATOR)
	site.require_admin()
	if error:
		frappe.throw(_("Cloudflare did not sign in: {0}").format(error))
	held = frappe.cache.get_value(_state_key(state)) if state else None
	if not held or held.get("user") != frappe.session.user or not code:
		frappe.throw(_("The sign-in has expired. Press Sign In to Cloudflare again."))
	frappe.cache.delete_value(_state_key(state))
	token = _exchanged(code, held["verifier"])
	frappe.cache.set_value(_token_key(), encrypt(token), expires_in_sec=TOKEN_FOR)
	from onedesk.one_admin.setup import LOCK, LOCKED_FOR

	frappe.enqueue(
		"onedesk.one_admin.setup.run",
		queue="long",
		timeout=LOCKED_FOR,
		job_id=LOCK,
		deduplicate=True,
		user=frappe.session.user,
		signed_in=True,
	)
	frappe.local.response["type"] = "redirect"
	frappe.local.response["location"] = BACK_TO


def _exchanged(code: str, verifier: str) -> str:
	client_id, secret = _client()
	answered = requests.post(
		TOKEN,
		data={"grant_type": "authorization_code", "code": code, "redirect_uri": _redirect(), "code_verifier": verifier},
		auth=(client_id, secret),
		timeout=TIMEOUT,
	)
	token = answered.json().get("access_token") if answered.ok else None
	if not token:
		frappe.throw(_("Cloudflare refused the sign-in: {0}").format(answered.text[:300]))
	return token


def taken() -> str | None:
	"""The token the sign-in left, taken from the cache so it is read once."""
	held = frappe.cache.get_value(_token_key())
	if not held:
		return None
	frappe.cache.delete_value(_token_key())
	return decrypt(held)


def discard(token: str | None) -> None:
	"""The run is over: Cloudflare revokes the token."""
	if not token:
		return
	try:
		client_id, secret = _client()
		requests.post(REVOKE, data={"token": token, "token_type_hint": "access_token"}, auth=(client_id, secret), timeout=TIMEOUT)
	except (frappe.ValidationError, requests.RequestException):
		frappe.log_error(title="Cloudflare sign-in", message="The sign-in token could not be revoked; it expires by itself.")
