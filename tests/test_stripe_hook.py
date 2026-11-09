"""Stripe's webhook, made once, through its API (one_admin/stripe.py)."""

from unittest import mock

from onedesk.one_admin import stripe

URL = "https://admin.example/api/method/onedesk.one_admin.stripe.webhook"


def _run(endpoints, secret, kept_id):
	conf = {"stripe_webhook_id": kept_id} if kept_id else {}
	with (
		mock.patch.object(stripe.site, "require_admin"),
		mock.patch.object(stripe, "hook_url", return_value=URL),
		mock.patch.object(stripe, "fetch", return_value={"data": endpoints}),
		mock.patch.object(stripe, "_post", return_value={"id": "we_new", "secret": "whsec_new"}) as post,
		mock.patch.object(stripe, "_delete") as delete,
		mock.patch.object(stripe.vault, "get", return_value=secret),
		mock.patch.object(stripe.vault, "keep") as keep,
		mock.patch.object(stripe.frappe, "conf", conf),
	):
		said = stripe.hook_made()
	return said, post, delete, keep


def test_the_form_names_the_five_events():
	form = stripe.hook_form(URL)
	assert form["url"] == URL and sorted(v for k, v in form.items() if k != "url") == sorted(stripe.HEARD)


def test_none_there_is_made_and_its_secret_kept():
	said, post, delete, keep = _run([], None, None)
	assert said["made"] and post.call_args.args[0] == stripe.HOOK and not delete.called
	keep.assert_any_call("stripe_webhook_secret", "whsec_new")


def test_one_there_with_its_secret_is_left():
	held = {"id": "we_1", "url": URL, "enabled_events": list(stripe.HEARD), "status": "enabled"}
	said, post, delete, _keep = _run([held], "whsec_held", "we_1")
	assert said == {"id": "we_1", "made": False} and not post.called and not delete.called


def test_one_added_by_hand_is_adopted():
	held = {"id": "we_1", "url": URL, "enabled_events": list(stripe.HEARD), "status": "enabled"}
	said, _post, delete, keep = _run([held], "whsec_typed", None)
	assert not said["made"] and not delete.called
	keep.assert_called_once_with(stripe.HOOK_ID, "we_1")


def test_one_whose_secret_is_lost_is_replaced():
	held = {"id": "we_1", "url": URL, "enabled_events": list(stripe.HEARD), "status": "enabled"}
	said, _post, delete, keep = _run([held], None, "we_1")
	assert said["made"]
	delete.assert_called_once_with(f"{stripe.HOOK}/we_1")
	keep.assert_any_call("stripe_webhook_secret", "whsec_new")


def test_a_key_from_the_other_mode_makes_its_own():
	held = {"id": "we_live", "url": URL, "enabled_events": list(stripe.HEARD), "status": "enabled"}
	said, _post, delete, keep = _run([held], "whsec_test", "we_test")
	assert said["made"]
	delete.assert_called_once_with(f"{stripe.HOOK}/we_live")
	keep.assert_any_call(stripe.HOOK_ID, "we_new")


def test_events_that_drifted_are_put_back():
	held = {"id": "we_1", "url": URL, "enabled_events": ["invoice.paid"], "status": "enabled"}
	said, post, delete, _keep = _run([held], "whsec_held", "we_1")
	assert not said["made"] and not delete.called
	assert post.call_args.args[0] == f"{stripe.HOOK}/we_1"
