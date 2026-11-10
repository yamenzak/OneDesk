from email.message import EmailMessage

from onedesk.one_admin import mailing, setup, testmail


def test_a_kept_message_reads_with_its_links_once_each():
	made = EmailMessage()
	made["From"] = "noreply@4dl.app"
	made["To"] = "signup+1@test.4dl.app"
	made["Subject"] = "Sign in to One"
	made.set_content("Open https://admin.example.com/login?key=a&b=1.")
	made.add_alternative('<a href="https://admin.example.com/login?key=a&amp;b=1">Sign In</a> https://admin.example.com/login?key=a&amp;b=1', subtype="html")
	read = testmail.parsed(made.as_bytes())
	assert read["subject"] == "Sign in to One" and read["to"] == "signup+1@test.4dl.app"
	assert read["links"] == ["https://admin.example.com/login?key=a&b=1"]
	assert "Open" in read["text"]


def test_the_test_domain_and_its_bucket_are_named_apart_on_dev():
	assert setup.for_env(None, setup.TEST_LABEL) == "test" and setup.for_env("dev", setup.TEST_LABEL) == "test-dev"
	assert setup.for_env("dev", setup.TESTMAIL) == "one-testmail-dev"


def test_a_suppressed_or_bounced_recipient_is_seen_in_what_cloudflare_says():
	assert mailing.suppressed({"errors": [{"code": "email.sending.error.email.recipient_suppressed", "message": "x"}]})
	assert mailing.suppressed({"errors": [{"code": 10001, "message": "email.sending.error.email.recipient_suppressed"}]})
	assert not mailing.suppressed({"errors": [{"code": 10000, "message": "Authentication error"}]})
	assert not mailing.suppressed({})
	assert mailing.bounced({"permanent_bounces": ["Ann@Acme.com"]}, "ann@acme.com")
	assert not mailing.bounced({"delivered": ["ann@acme.com"]}, "ann@acme.com")
