"""A sealed file opens with the passphrase and with nothing a server holds
(one_admin/seal.py)."""

import pytest
from cryptography.exceptions import InvalidTag

from onedesk.one_admin import seal


def test_a_sealed_file_opens_with_its_passphrase():
	public = seal.public_text("a long rescue passphrase")
	assert seal.opened(seal.sealed(b'{"keeper_secret": "x"}', public), "a long rescue passphrase") == b'{"keeper_secret": "x"}'


def test_the_wrong_passphrase_opens_nothing():
	held = seal.sealed(b"secret", seal.public_text("a long rescue passphrase"))
	with pytest.raises(InvalidTag):
		seal.opened(held, "another long passphrase")


def test_the_public_key_holds_no_way_in():
	public = seal.public_text("a long rescue passphrase")
	assert "secret" not in public and len(public.split(".")) == 2
