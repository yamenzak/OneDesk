"""Automations (one/automations.py, one/automation_steps.py): a workspace's flow
tells people through the hub with One's own step, never frappe's mail, and
fills a template in as the email window does; the list and form keep One's
rail; OneAI suggests one as a card. These read the code that says so."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tree

SOURCE = (tree.APP / "one" / "automations.py").read_text()
STEPS = (tree.APP / "one" / "automation_steps.py").read_text()
HOOKS = (tree.APP / "hooks.py").read_text()


def test_tell_people_is_a_step_of_the_engine_and_goes_through_the_hub():
	assert 'automation_actions = ["onedesk.one.automation_steps.TellPeople"]' in HOOKS
	assert "class TellPeople(AutomationAction):" in STEPS
	assert 'action_type = "TellPeople"' in STEPS
	execute = STEPS.split("def execute(", 1)[1]
	assert 'notify.notify(\n\t\t\t"Automation Notice"' in execute
	assert "mail_templates.filled(" in execute
	assert "sendmail" not in STEPS


def test_a_workspace_flow_tells_people_only_through_the_hub():
	actions = SOURCE.split("ACTIONS = (", 1)[1].split(")", 1)[0]
	assert '"TellPeople"' in actions and '"SendNotification"' not in actions
	validate = SOURCE.split("def validate(", 1)[1].split("\ndef ", 1)[0]
	assert 'row.action_type == "SendNotification"' in validate


def test_a_template_is_filled_in_as_the_email_window_fills_it():
	templates = (tree.APP / "one" / "mail_templates.py").read_text()
	filled = templates.split("def filled(", 1)[1]
	assert "_shown(template" in filled


def test_the_list_and_form_keep_ones_rail():
	desk = (tree.APP / "public" / "js" / "desk.js").read_text()
	assert 'route[1] === "Automation Flow"' in desk


def test_oneai_suggests_an_automation_as_a_card():
	ai = (tree.APP / "one" / "ai.py").read_text()
	suggest = ai.split("def suggest_automation(", 1)[1].split("\ndef ", 1)[0]
	assert 'trial.run_method("validate")' in suggest and '"TellPeople"' in suggest
	assert 'suggest_approval.action = suggest_automation.action = draft_notification.action = "workspace_setup"' in ai
	for tool in ("workspace_automations", "suggest_automation"):
		assert f'"onedesk.one.ai.{tool}"' in HOOKS, tool


def test_the_step_editor_offers_what_the_workspace_may_keep():
	steps = SOURCE.split("def steps(", 1)[1].split("\ndef ", 1)[0]
	assert "get_automation_capabilities(" in steps
	assert '!= "SendNotification"' in steps and "in ACTIONS" in steps
	assert "_said(one)" in steps
	settings = (tree.APP / "public" / "js" / "doctype_settings.js").read_text()
	assert '"onedesk.one.automations.steps"' in settings
	assert "frappe.automation_engine.api.get_param_options" in settings
	assert 'frappe.ui.form.on("Automation Action"' in settings
	assert "new frappe.ui.FieldGroup(" in settings.split("onedesk.automations.draw =", 1)[1]
