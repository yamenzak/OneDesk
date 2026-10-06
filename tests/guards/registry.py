"""Every guard, by the passover point it serves (docs/PASSOVER.md, The points).

A guard fails in the code on a practice a reading of the screen can miss. Each
row says which point it serves, what it fails on, and where it runs: a test
(`tests/file.py::test_name`) or a command. A point still waiting for its guard
says what is coming in PLANNED. `python3 scripts/guards.py` lists them by
point, and `--run` runs them all.
"""

from typing import NamedTuple


class Guard(NamedTuple):
	id: str
	point: int
	what: str
	runs: str


POINTS = {
	1: "Demo coverage",
	2: "Rules on the server",
	3: "Hand-offs",
	4: "Tier declared",
	5: "Our look",
	6: "Nothing lost",
	7: "Extensible",
	8: "Built from frappe",
	9: "Overrides recorded",
	10: "Notifications",
	11: "Printed",
	12: "Plain words",
	13: "Documented, and OneAI knows and does",
	14: "Intake",
	15: "Permissions and roles",
	16: "Legal",
	17: "Clean code",
}

GUARDS = [
	# 4 Tier declared
	Guard(
		"islands-declared",
		4,
		"an island not declared, built and mounted",
		"tests/guards/test_islands.py::test_every_island_is_declared_built_and_mounted",
	),
	Guard(
		"pages-on-shell",
		4,
		"a desk page neither on the shell nor named as not yet",
		"tests/guards/test_shell.py::test_every_page_is_on_the_shell_or_named_as_not_yet",
	),
	Guard(
		"heads-declared",
		4,
		"a Record Head not declared in the tier registry",
		"tests/guards/test_tiers.py::test_every_record_head_is_declared",
	),
	Guard(
		"pages-declared",
		4,
		"a page of its own not declared, or declared without why",
		"tests/guards/test_tiers.py::test_every_page_of_its_own_is_declared",
	),
	Guard(
		"collections-declared",
		4,
		"a list, calendar or tree set up and not declared",
		"tests/guards/test_tiers.py::test_every_collection_set_up_is_declared",
	),
	Guard(
		"views-kept",
		4,
		"a view frappe offers taken away",
		"tests/guards/test_tiers.py::test_no_view_frappe_offers_is_taken_away",
	),
	Guard(
		"screens-declared",
		4,
		"a desk page of ours not declared with what it is",
		"tests/guards/test_tiers.py::test_every_desk_page_of_ours_is_declared",
	),
	Guard(
		"record-tabs-declared",
		4,
		"a record tab drawn outside the one place that draws them",
		"tests/guards/test_tiers.py::test_a_record_tab_is_declared_by_its_module_and_drawn_in_one_place",
	),
	# 5 Our look
	Guard(
		"shell-styles-shell",
		5,
		"anything but the shell styling the shell",
		"tests/guards/test_shell.py::test_only_the_shell_styles_the_shell",
	),
	Guard(
		"page-draws-no-shell",
		5,
		"a page drawing a part the shell draws",
		"tests/guards/test_shell.py::test_a_page_on_the_shell_draws_none_of_its_parts",
	),
	Guard(
		"portal-look",
		5,
		"a page outside the desk without the portal",
		"tests/guards/test_shell.py::test_every_page_outside_the_desk_wears_the_portal",
	),
	# 8 Built from frappe
	Guard(
		"island-frappe-ui",
		8,
		"an island part that frappe-ui has, written by us",
		"tests/guards/test_islands.py::test_an_island_is_frappe_ui_and_nothing_of_its_own",
	),
	Guard(
		"island-tokens",
		8,
		"a colour or size in an island that is not a frappe-ui token",
		"tests/guards/test_islands.py::test_an_island_uses_frappe_ui_tokens",
	),
	Guard(
		"kit-reaches-desk",
		8,
		"an island reaching into desk other than through the kit",
		"tests/guards/test_islands.py::test_only_the_kit_reaches_into_desk",
	),
	Guard(
		"list-is-frappes",
		8,
		"a list of records not drawn as frappe's table",
		"tests/guards/test_shell.py::test_a_list_of_records_is_frappes_table",
	),
	Guard("dialog-is-frappes", 8, "a dialog not frappe's", "tests/guards/test_shell.py::test_a_dialog_is_frappes"),
	Guard(
		"record-as-docview",
		8,
		"a record opened by a page not drawn as a docview",
		"tests/guards/test_shell.py::test_a_record_a_page_opens_on_is_drawn_as_a_docview",
	),
	Guard(
		"formats-from-frappe",
		8,
		"a date, number or currency formatted by hand instead of through frappe",
		"tests/guards/test_formats.py::test_nothing_is_formatted_by_hand",
	),
	Guard(
		"hooks-exist",
		8,
		"a hook naming a function or asset that does not exist",
		"tests/guards/test_hooks.py::test_the_function_exists",
	),
	# 9 Overrides recorded
	Guard(
		"overrides-hold",
		9,
		"an upstream line we lean on that has gone",
		"cmd: python3 scripts/overrides.py --check",
	),
	Guard(
		"upstream-unmoved",
		9,
		"something upstream moved under us",
		"tests/guards/test_generated.py::test_nothing_upstream_moved_under_us",
	),
	Guard(
		"made-declared",
		9,
		"a kind of record we make that is not declared",
		"tests/guards/test_makes_records.py::test_every_kind_made_is_declared",
	),
	# 10 Notifications
	Guard(
		"one-sender",
		10,
		"a mail or notification sent around the hub",
		"tests/guards/test_notifications.py::test_nothing_else_sends",
	),
	Guard(
		"types-declared",
		10,
		"a notification sent that is not declared",
		"tests/guards/test_notifications.py::test_every_type_sent_is_declared",
	),
	Guard(
		"types-say-needs",
		10,
		"a notification that does not say what it needs",
		"tests/guards/test_notifications.py::test_every_type_says_what_it_needs",
	),
	Guard(
		"one-folder",
		10,
		"a notification declared anywhere but its own file in onedesk/notifications/",
		"tests/guards/test_notifications.py::test_nothing_declares_a_notification_anywhere_else",
	),
	Guard(
		"one-layout",
		10,
		"a notification file not named for its type or not in the one layout",
		"tests/guards/test_notifications.py::test_every_notification_is_one_file_in_one_layout",
	),
	# 12 Plain words
	Guard(
		"screen-plain",
		12,
		"screen text with a colon or semicolon clause, a coinage or narration",
		"tests/guards/test_wording.py::test_what_a_screen_says_is_plain",
	),
	Guard(
		"labels-are-names",
		12,
		"a label written as a sentence",
		"tests/guards/test_wording.py::test_every_label_is_a_name_not_a_sentence",
	),
	Guard(
		"descriptions-plain",
		12,
		"a field description longer than two plain sentences",
		"tests/guards/test_wording.py::test_every_description_is_one_or_two_plain_sentences",
	),
	Guard(
		"no-commit-voice",
		12,
		"screen text that reads like a commit message",
		"tests/guards/test_wording.py::test_no_screen_text_reads_like_a_commit_message",
	),
	Guard(
		"island-translated",
		12,
		"island text not passed through __()",
		"tests/guards/test_islands.py::test_what_an_island_says_is_translated",
	),
	Guard(
		"translated",
		12,
		"a string with no Arabic or German",
		"tests/guards/test_translations.py::test_every_string_reaches_a_reader",
	),
	Guard(
		"placeholders",
		12,
		"a translation that loses a placeholder",
		"tests/guards/test_translations.py::test_placeholders_survive_translation",
	),
	# 13 Documented, and OneAI knows and does
	Guard(
		"docs-current",
		13,
		"a README or generated reference out of date",
		"tests/guards/test_generated.py::test_docs_are_current",
	),
	Guard(
		"oneai-badge", 13, "OneAI badged by hand", "tests/guards/test_ai_look.py::test_nothing_badges_oneai_by_hand"
	),
	Guard(
		"oneai-button",
		13,
		"an OneAI button drawn by hand",
		"tests/guards/test_ai_look.py::test_no_oneai_button_is_drawn_by_hand",
	),
	Guard(
		"oneai-no-page-button",
		13,
		"an OneAI button placed on a page",
		"tests/guards/test_oneai_place.py::test_no_oneai_button_on_a_page",
	),
	# 15 Permissions and roles
	Guard(
		"no-system-manager-code",
		15,
		"code that waits for System Manager",
		"tests/guards/test_roles.py::test_no_code_waits_for_system_manager",
	),
	Guard(
		"no-system-manager-screen",
		15,
		"a screen that waits for System Manager",
		"tests/guards/test_roles.py::test_no_screen_waits_for_system_manager",
	),
	Guard(
		"operator-verbs-gated",
		15,
		"an operator verb without its gate",
		"tests/guards/test_roles.py::test_every_operator_verb_is_gated",
	),
	# 16 Legal
	Guard(
		"legal-version",
		16,
		"a clause changed without a new revision or recorded hash",
		"tests/guards/test_legal.py::test_every_document_is_at_the_version_recorded",
	),
	Guard(
		"subprocessors",
		16,
		"a company One calls that is not a declared subprocessor",
		"tests/guards/test_legal.py::test_every_company_one_calls_is_a_declared_subprocessor",
	),
	Guard(
		"legal-assembled",
		16,
		"a module's legal file left out of the documents",
		"tests/guards/test_legal.py::test_every_modules_legal_file_is_assembled",
	),
	Guard(
		"nothing-promised",
		16,
		"an agreement promising what is not built",
		"tests/guards/test_legal.py::test_nobody_is_promised_what_is_not_built",
	),
	# 6 Nothing lost
	Guard(
		"page-keeps-form",
		6,
		"a page of its own without its form's menu, sidebar or realtime",
		"tests/guards/test_frame.py::test_a_page_keeps_its_forms_menu_and_sidebar",
	),
	Guard(
		"record-handle",
		6,
		"frappe's Share, Email, Links or Remind Me reading a part of a form the page does not lend",
		"tests/guards/test_frame.py::test_the_record_handle_covers_what_frappes_dialogs_read",
	),
	Guard(
		"page-island-known",
		6,
		"a page of its own with no island the guards know",
		"tests/guards/test_frame.py::test_every_page_is_drawn_by_a_known_island",
	),
	# 7 Extensible
	Guard(
		"page-places",
		7,
		"a page of its own that declares no places or does not fire them",
		"tests/guards/test_frame.py::test_a_page_declares_its_places_and_fires_them",
	),
	Guard(
		"places-fired",
		7,
		"a place in one_studio/places.py that no page fires",
		"tests/guards/test_frame.py::test_each_page_fires_its_events_with_only_its_powers",
	),
	# 15 Permissions
	Guard(
		"answers-kept",
		15,
		"an Approve or Reject whose verdict frappe can put back for an approver without the field's level",
		"tests/guards/test_decisions.py::test_every_answer_carries_its_verdict_through_the_save",
	),
	Guard(
		"answers-set-again",
		15,
		"an answered record that does not set the verdict again before it validates",
		"tests/guards/test_decisions.py::test_every_answered_record_sets_the_verdict_again_before_it_validates",
	),
	# 1 Demo coverage
	Guard(
		"install-hidden-mandatory",
		1,
		"a shipped customization hiding a mandatory field, which stops a new site installing",
		"tests/guards/test_install.py::test_no_shipped_customization_hides_a_mandatory_field",
	),
	Guard(
		"install-after-sync",
		1,
		"setup run in after_install, before the app's custom fields exist",
		"tests/guards/test_install.py::test_install_hooks_run_after_the_custom_fields_exist",
	),
	Guard(
		"install-settled",
		1,
		"something after_migrate sets up that a new site never gets",
		"tests/guards/test_install.py::test_a_new_site_is_settled_as_a_migrated_one_is",
	),
	Guard(
		"install-after-wizard",
		1,
		"a new workspace not settled once the setup wizard has made its company",
		"tests/guards/test_install.py::test_a_new_workspace_is_settled_once_its_company_exists",
	),
	Guard(
		"demo-steps",
		1,
		"a demo step not built, or not in the demo's README",
		"tests/guards/test_demo.py::test_every_step_is_built_and_written_down",
	),
	Guard(
		"demo-apps",
		1,
		"an app People gives that nobody in the demo company is given",
		"tests/guards/test_demo.py::test_every_app_people_gives_is_given_to_somebody_in_the_demo",
	),
	Guard(
		"demo-suite",
		1,
		"an integration suite that writes, or checks next to nothing",
		"tests/guards/test_demo.py::test_the_suite_checks_and_writes_nothing",
	),
	# 2 Rules on the server
	Guard(
		"rules-hooked",
		2,
		"a rule of One's not on its record's hooks",
		"tests/guards/test_rules.py::test_every_rule_is_on_its_records_hooks",
	),
	Guard(
		"rules-every-way",
		2,
		"a rule with no demo check that changes it by bulk edit, report view and import",
		"tests/guards/test_rules.py::test_every_rule_is_changed_every_way_on_the_demo",
	),
	Guard(
		"rules-no-way-round",
		2,
		"an endpoint writing a field a rule owns with frappe.db.set_value",
		"tests/guards/test_rules.py::test_no_endpoint_writes_round_a_rule",
	),
	# 11 Printed
	Guard(
		"print-shipped",
		11,
		"a record that leaves the company with no format we ship, laid out in the builder from One's blocks",
		"tests/guards/test_print.py::test_every_record_that_leaves_has_a_format_we_ship",
	),
	Guard(
		"print-blocks",
		11,
		"a block on a shipped format that is not a field template of One's with its template",
		"tests/guards/test_print.py::test_every_block_is_a_field_template_with_its_template",
	),
	Guard(
		"print-wired",
		11,
		"the blocks not reachable from Jinja, or One's formats not made the default after migrate",
		"tests/guards/test_print.py::test_the_blocks_reach_jinja_and_settle_after_migrate",
	),
	Guard(
		"print-escaped",
		11,
		"a block showing a record's value without escaping it",
		"tests/guards/test_print.py::test_a_template_escapes_what_it_shows",
	),
	# 3 Hand-offs
	Guard(
		"handoffs-said",
		3,
		"a product README with no Connections section, or one naming no other product",
		"tests/guards/test_handoffs.py::test_every_product_says_its_connections",
	),
	Guard(
		"handoffs-run",
		3,
		"the demo suite not holding the hand-offs to the records they leave",
		"tests/guards/test_handoffs.py::test_the_suite_holds_every_hand_off",
	),
	# 14 Intake
	Guard(
		"intake-sampled",
		14,
		"a record Intake can make with no sample that makes it",
		"tests/guards/test_intake_samples.py::test_every_record_intake_makes_has_a_sample",
	),
	Guard(
		"intake-samples-whole",
		14,
		"a sample with no document, nothing it makes, or an answer to a call Intake never makes",
		"tests/guards/test_intake_samples.py::test_every_sample_is_whole",
	),
	Guard(
		"intake-samples-run",
		14,
		"the demo suite not running every sample",
		"tests/guards/test_intake_samples.py::test_the_suite_runs_every_sample",
	),
	# 17 Clean code
	Guard(
		"comments-short",
		17,
		"a comment block over 3 lines; the long form goes in the module's README",
		"tests/guards/test_source_style.py::test_no_comment_block_is_an_essay",
	),
	Guard(
		"docstrings-short",
		17,
		"a docstring over 8 lines; the long form goes in the module's README",
		"tests/guards/test_source_style.py::test_no_docstring_is_an_essay",
	),
	Guard(
		"tell-in-place",
		17,
		"a notification sent from anywhere but the module's tell.py",
		"tests/guards/test_layout.py::test_notifications_go_out_from_tell",
	),
	Guard(
		"ai-in-place",
		17,
		"a OneAI hook pointing at anything but a module's ai.py or ai_<topic>.py",
		"tests/guards/test_layout.py::test_oneai_hooks_point_at_ai_files",
	),
	Guard(
		"access-in-place",
		17,
		"a role given rights anywhere but a module's access.py",
		"tests/guards/test_layout.py::test_roles_are_given_in_access",
	),
	Guard(
		"upstream-imports",
		17,
		"an import of a name frappe, erpnext or hrms no longer has",
		"tests/guards/test_upstream_imports.py::test_every_upstream_import_is_still_there",
	),
]

#: Points whose guard is still to come, and what it will fail on.
PLANNED = {
	1: "a module with a feature and no demo record or check on it, held as each module is passed over again",
}
