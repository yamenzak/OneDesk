"""The AWS link names the template and keeps to OneAdmin's region
(one_admin/aws.py)."""

from pathlib import Path
from urllib.parse import parse_qs

from onedesk.one_admin import aws
from onedesk.one_admin.boxes import REGION

TEMPLATE = Path(__file__).resolve().parents[1] / "deploy" / "aws" / "lightsail-user.yaml"


def test_the_link_opens_quick_create_in_the_region():
	link = aws.quick_create("https://s3.eu-north-1.amazonaws.com/one/lightsail-user.yaml")
	assert link.startswith(f"https://{REGION}.console.aws.amazon.com/cloudformation/")
	query = parse_qs(link.split("review?", 1)[1])
	assert query["templateURL"] == ["https://s3.eu-north-1.amazonaws.com/one/lightsail-user.yaml"]
	assert query["stackName"] == [aws.STACK]


def test_the_template_allows_only_lightsail_in_the_region():
	text = TEMPLATE.read_text()
	assert 'Action: "lightsail:*"' in text and f"aws:RequestedRegion: {REGION}" in text
	assert "AWS::IAM::AccessKey" not in text, "no access key is left in the stack's outputs"
