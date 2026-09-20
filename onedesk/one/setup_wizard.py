import frappe

#: What the wizard's Appearance field offers, against `User.desk_theme`.
THEMES = {"Automatic": "Automatic", "Light": "Light", "Dark": "Dark"}


def get_setup_stages(args=None):
	return [
		{
			"status": frappe._("Setting up One"),
			"fail_msg": frappe._("Failed to set up One"),
			"tasks": [
				{
					"fn": set_appearance,
					"args": args,
					"fail_msg": frappe._("Failed to set the appearance"),
				}
			],
		}
	]


def set_appearance(args):
	chosen = THEMES.get((args or {}).get("onedesk_theme", ""))
	if not chosen:
		return
	frappe.db.set_value("User", frappe.session.user, "desk_theme", chosen)
