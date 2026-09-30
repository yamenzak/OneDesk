"""Mail templates (one/mail_templates.py): what one written here may say, how
the composer offers one in OneMail, which has no form behind it, and how it is
filled in. These read the code that says so."""

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "mail_templates.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()
COMPOSE = (tree.APP / "public" / "js" / "mail_compose.js").read_text()


def _constant(name: str) -> str:
	for node in ast.parse(SOURCE).body:
		if isinstance(node, ast.Assign) and any(getattr(one, "id", None) == name for one in node.targets):
			return ast.literal_eval(node.value.args[0])
	raise AssertionError(name)


def test_a_field_is_named_bare():
	"""Frappe renders a template with the record's fields and no `doc`, so
	`{{ doc.customer_name }}` fails in the composer and every setting's mail."""
	field = re.compile(_constant("FIELD"))
	assert field.fullmatch("{{ customer_name }}")
	assert field.fullmatch("{{due_date}}")
	assert not field.fullmatch("{{ doc.customer_name }}")
	assert not field.fullmatch("{{ frappe.session.user }}")


def test_the_composer_is_offered_the_records_templates_form_or_none():
	assert "get_fields" in COMPOSE and "email_template" in COMPOSE
	assert "(this.doc && this.doc.doctype)" in COMPOSE


def test_a_template_is_filled_in_from_the_record():
	assert (
		'"frappe.email.doctype.email_template.email_template.get_email_template": '
		'"onedesk.one.mail_templates.get_email_template"'
	) in HOOKS
	body = SOURCE.split("def get_email_template(", 1)[1]
	assert 'check_permission("read")' in body.split("def _shown(", 1)[0]
	assert "get_formatted" in body


def test_the_apps_templates_say_what_they_are_for():
	assert "_for_what()" in SOURCE.split("def settle(", 1)[1].split("\ndef ", 1)[0]
	for kind in ("Leave Application", "Interview", "Exit Interview", "Delivery Trip", "Salary Slip"):
		assert f'"{kind}"' in SOURCE, kind


def test_oneai_writes_a_template_as_a_card():
	ai = (tree.APP / "one" / "ai.py").read_text()
	write = ai.split("def write_mail_template(", 1)[1].split("\ndef ", 1)[0]
	assert "mail_templates.check(" in write and "proposals.propose(" in write
	for tool in ("workspace_mail_templates", "write_mail_template"):
		assert f'"onedesk.one.ai.{tool}"' in HOOKS, tool
	assert '"page:workspace-settings/mail_templates"' in ai
