"""The link that makes OneAdmin's Lightsail-only IAM user in the AWS console:
CloudFormation's quick-create page, with deploy/aws/lightsail-user.yaml filled
in. AWS reads a template only from S3, so its address is a setting (README,
Settings)."""

from urllib.parse import urlencode

import frappe
from frappe import _

from onedesk.one_admin import site
from onedesk.one_admin.boxes import REGION

STACK = "one-admin-lightsail"


def quick_create(template_url: str) -> str:
	"""The quick-create page for `template_url`, in OneAdmin's region. Pure."""
	query = urlencode({"templateURL": template_url, "stackName": STACK})
	return f"https://{REGION}.console.aws.amazon.com/cloudformation/home?region={REGION}#/stacks/create/review?{query}"


@frappe.whitelist(methods=["POST"])
def link() -> str:
	"""The button on One Admin Settings."""
	frappe.only_for(site.OPERATOR)
	site.require_admin()
	template = (frappe.db.get_single_value("One Admin Settings", "aws_template_url") or "").strip()
	if not template.startswith("https://") or ".amazonaws.com/" not in template:
		frappe.throw(_("Enter the AWS Template URL first. It must be the template's address on Amazon S3."))
	return quick_create(template)
