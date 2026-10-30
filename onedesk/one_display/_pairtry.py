import frappe
from onedesk.one_demo.base import as_user
from onedesk.one_demo.people import OWNER
from onedesk.one_display import screens
from onedesk.one_display.demo import CHANNEL
def make():
	with as_user("Guest"):
		s = screens.start("browser")
	with as_user(OWNER):
		name = screens.pair(s["code"], "Browser Look", CHANNEL)
	with as_user("Guest"):
		token = screens.status(s["screen"], s["secret"])["token"]
	frappe.db.commit()
	open("/home/frappe/scratch/tvpair.json", "w").write(frappe.as_json({"screen": name, "token": token}))
	print(name)
