app_name = "onedesk"
app_title = "One"
app_publisher = "One"
app_description = "Every One product, as modules on the Frappe desk"
app_email = "hello@4dl.app"
app_license = "agpl-3.0"

# `setup_wizard_url` is ignored while erpnext or hrms are installed.
setup_wizard_requires = "assets/onedesk/js/setup_wizard.js"
setup_wizard_stages = "onedesk.one.setup_wizard.get_setup_stages"

app_include_css = ["/assets/onedesk/css/theme.css", "/assets/onedesk/css/desk.css"]
app_include_js = "/assets/onedesk/js/theme.js"
