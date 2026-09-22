"""Whether a webhook really came from Stripe, read back without a site.

`onedesk/one_admin/signing.py` imports nothing of Frappe because the endpoint
behind it takes money on the strength of this check and anybody on the internet
can reach it.
"""

import hashlib
import hmac
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from onedesk.one_admin import signing

SECRET = "whsec_pretend"
BODY = b'{"id":"evt_1","type":"checkout.session.completed"}'
NOW = 1_700_000_000


def header_for(payload=BODY, stamp=NOW, secret=SECRET, name="v1"):
	digest = hmac.new(
		secret.encode(), b"%d.%s" % (stamp, payload), hashlib.sha256
	).hexdigest()
	return f"t={stamp},{name}={digest}"


def test_a_real_signature_passes():
	assert signing.verify(BODY, header_for(), SECRET, NOW) == NOW


def test_a_signature_for_a_different_body_fails():
	with pytest.raises(signing.Unsigned):
		signing.verify(b'{"id":"evt_2"}', header_for(), SECRET, NOW)


def test_a_signature_made_with_another_secret_fails():
	with pytest.raises(signing.Unsigned):
		signing.verify(BODY, header_for(secret="whsec_someone_else"), SECRET, NOW)


def test_an_old_delivery_is_refused_however_valid_its_signature():
	"""Otherwise a captured 'payment succeeded' provisions a workspace forever."""
	old = NOW - signing.TOLERANCE - 1
	with pytest.raises(signing.Unsigned):
		signing.verify(BODY, header_for(stamp=old), SECRET, NOW)


def test_a_delivery_from_the_future_is_refused_too():
	ahead = NOW + signing.TOLERANCE + 1
	with pytest.raises(signing.Unsigned):
		signing.verify(BODY, header_for(stamp=ahead), SECRET, NOW)


def test_a_delivery_just_inside_the_window_passes():
	signing.verify(BODY, header_for(stamp=NOW - signing.TOLERANCE), SECRET, NOW)


def test_any_of_several_signatures_matching_is_a_match():
	"""Stripe sends more than one while a secret is being rotated."""
	good = header_for().split(",")[1]
	combined = f"t={NOW},v1=deadbeef,{good}"
	assert signing.verify(BODY, combined, SECRET, NOW) == NOW


@pytest.mark.parametrize("nothing", ["", "t=123", "v1=abc", "garbage", None])
def test_a_header_with_no_signature_in_it_is_refused(nothing):
	with pytest.raises(signing.Unsigned):
		signing.verify(BODY, nothing, SECRET, NOW)


def test_an_unconfigured_endpoint_refuses_rather_than_accepts():
	"""A missing secret must never mean 'skip the check'."""
	with pytest.raises(signing.Unsigned):
		signing.verify(BODY, header_for(), "", NOW)


def test_the_comparison_is_constant_time():
	source = (Path(__file__).resolve().parent.parent / "onedesk" / "one_admin" / "signing.py").read_text()
	assert "hmac.compare_digest" in source
	assert "== one" not in source
